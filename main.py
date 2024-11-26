import logging
from flask import Flask, request, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS
import os
import requests
import time
import re
import random

app = Flask(__name__)
CORS(app)
key_regex = r'let content = \("([^"]+)"\);'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
port = int(os.getenv('PORT', 8080))

# Cấu hình logging
logger = logging.getLogger('api_usage')
logger.setLevel(logging.INFO)

log_file_path = '/tmp/api_usage.log'
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Path to the file that stores request count
count_file_path = '/tmp/request_count.txt'

def read_request_count():
    """Read the current request count from file."""
    if os.path.exists(count_file_path):
        with open(count_file_path, 'r') as f:
            return int(f.read().strip())
    return 0

def write_request_count(count):
    """Write the request count to file."""
    with open(count_file_path, 'w') as f:
        f.write(str(count))

def get_client_ip():
    """Hàm để lấy địa chỉ IP của client, xem xét cả trường hợp đằng sau proxy."""
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
        # Giả lập thời gian phản hồi từ 0.1 đến 0.2 giây
        fake_time = random.uniform(0.1, 0.2)
        time.sleep(fake_time)

        # Thực hiện yêu cầu HTTP
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text, fake_time
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch URL: {url}. Error: {e}")

def bypass_link(url):
    try:
        hwid = url.split("HWID=")[1]
        if not hwid:
            raise ValueError("Invalid HWID in URL")

        start_time = time.time()
        steps = [
            {"url": "https://flux.li/android/external/check1.php?hash={hash}", "referer": "https://linkvertise.com"},
            {"url": "https://flux.li/android/external/main.php?hash={hash}", "referer": "https://linkvertise.com"},
        ]

        for step in steps:
            step_url = step["url"]
            referer = step["referer"]
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "DNT": "1",
                "Connection": "close",
                "Referer": referer,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x66) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            }

            html = fetchs(step_url, headers)

            # Check for temporary ban or block message
            if "You have been temporarily banned" in html:
                return {
                    "status": "error",
                    "key": "You have been temporarily banned from using Fluxus.",
                }

            if "Trying to bypass the Fluxus key system will get you banned" in html:
                return {
                    "status": "error",
                    "key": "Failed to bypass.",
                }

            # If we are at the last step, extract the key
            if step == steps[-1]:
                match = re.search(key_regex, html)
                if match:
                    time_taken = round(time.time() - start_time, 2)
                    return {"status": "success", "result": match.group(1), "timeTaken": time_taken}
                else:
                    raise Exception("Failed to bypass")

    except Exception as e:
        raise Exception(f"Failed to bypass link. Error: {e}")

@app.route('/bypass', methods=['GET'])
def api_bypass():
    # Get the HWID parameter from the query string
    url = request.args.get('url')
    
    if not url:
        return jsonify({"status": "error", "message": "URL parameter is required."}), 400

    try:
        result = bypass_link(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/check")
def check():
    request_count = read_request_count()
    return jsonify({"request": request_count, "credit": "UwU"})

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Đảm bảo rằng debug=False trong môi trường sản xuất
    )
