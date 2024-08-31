import logging
import os
import requests
import time
import re
import random
from flask import Flask, request, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
key_regex = r'let content = \("([^"]+)"\);'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
port = int(os.getenv('PORT', 8080))

# Configure logging
logger = logging.getLogger('api_usage')
logger.setLevel(logging.INFO)

log_file_path = '/tmp/api_usage.log'
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Path to the file that stores request count
count_file_path = '/path/to/your/persistent/request_count.txt'

def read_request_count():
    """Read the current request count from file."""
    try:
        if os.path.exists(count_file_path):
            with open(count_file_path, 'r') as f:
                return int(f.read().strip())
        return 0
    except Exception as e:
        logger.error(f"Error reading request count: {e}")
        return 0

def write_request_count(count):
    """Write the request count to file."""
    try:
        with open(count_file_path, 'w') as f:
            f.write(str(count))
    except Exception as e:
        logger.error(f"Error writing request count: {e}")

def get_client_ip():
    """Get the client IP address considering proxy headers."""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr
    return ip

@app.route('/')
def index():
    return render_template('index.html')

def fetch(url, headers):
    try:
        # Simulate response time from 0.1 to 0.2 seconds
        fake_time = random.uniform(0.1, 0.2)
        time.sleep(fake_time)

        # Make the HTTP request
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text, fake_time
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch URL: {url}. Error: {e}")
        raise

def bypass_link(url):
    try:
        hwid = url.split("HWID=")[-1]
        if not hwid:
            raise ValueError("Invalid HWID in URL")

        start_time = time.time()

        endpoints = [
            {"url": f"https://flux.li/android/external/start.php?HWID={hwid}", "referer": ""},
            {"url": "https://flux.li/android/external/check1.php?hash={hash}", "referer": "https://linkvertise.com"},
            {"url": "https://flux.li/android/external/main.php?hash={hash}", "referer": "https://linkvertise.com"}
        ]

        for endpoint in endpoints:
            url = endpoint["url"]
            referer = endpoint["referer"]
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'close',
                'Referer': referer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
            }
            response_text, fake_time = fetch(url, headers)
            if endpoint == endpoints[-1]:  # Only check the last endpoint
                match = re.search(key_regex, response_text)
                if match:
                    end_time = time.time()
                    time_taken = end_time - start_time
                    return match.group(1), time_taken
                else:
                    raise ValueError("Failed to find content key")
    except Exception as e:
        logger.error(f"Failed to bypass link. Error: {e}")
        raise

@app.route("/api/fluxus")
def bypass():
    try:
        request_count = read_request_count() + 1
        write_request_count(request_count)

        url = request.args.get("url")
        if url and url.startswith("https://flux.li/android/external/start.php?HWID="):
            try:
                content, fake_time = bypass_link(url)
                return jsonify({"key": content, "time_taken": "0.1", "credit": "UwU"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"message": "Please Enter a Valid Fluxus Link!"})
    except Exception as e:
        logger.error(f"Error in bypass endpoint: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/check")
def check():
    try:
        request_count = read_request_count()
        return jsonify({"request": request_count, "credit": "UwU"})
    except Exception as e:
        logger.error(f"Error in check endpoint: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Ensure debug=False in production
    )

