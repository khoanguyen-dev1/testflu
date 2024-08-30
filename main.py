import logging
from flask import Flask, request, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import requests
import time
import re
app = Flask(__name__)
key_regex = r'let content = \("([^"]+)"\);'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
port = int(os.getenv('PORT', 8080))


# Cấu hình logging
logger = logging.getLogger('api_usage')
logger.setLevel(logging.INFO)

# Sử dụng thư mục tạm cho logs
log_file_path = '/tmp/api_usage.log'  # Đường dẫn lưu log cho Vercel
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

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

key_regex = r'let content = \("([^"]+)"\);'

def fetch(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch URL: {url}. Error: {e}")

def bypass_link(url):
    try:
        hwid = url.split("HWID=")[-1]
        if not hwid:
            raise Exception("Invalid HWID in URL")

        time_taken = time.time()
        endpoints = [
            {
                "url": f"https://flux.li/android/external/start.php?HWID={hwid}",
                "referer": ""
            },
            {
                "url": "https://flux.li/android/external/check1.php?hash={hash}",
                "referer": "https://linkvertise.com"
            },
            {
                "url": "https://flux.li/android/external/main.php?hash={hash}",
                "referer": "https://linkvertise.com"
            }
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x66) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
            }
            response_text = fetch(url, headers)
            if endpoint == endpoints[-1]:
                match = re.search(key_regex, response_text)
                 if match:
                    end_time = time.time()
                    time_taken = end_time - start_time
                    if 0.1 <= time_taken <= 0.2:
                        return match.group(1), time_taken
                else:
                    raise Exception("Failed to find content key")
    except Exception as e:
        raise Exception(f"Failed to bypass link. Error: {e}")

@app.route("/")
def home():
    return jsonify({"message": "Invalid Endpoint"})

@app.route("/api/fluxus")
def bypass():
    url = request.args.get("url")
    if url.startswith("https://flux.li/android/external/start.php?HWID="):
        try:
            content, time_taken = bypass_link(url)
            return jsonify({"key": content, "time_taken": time_taken, "credit": "UwU"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"message": "Please Enter Fluxus Link!"})


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Đảm bảo rằng debug=False trong môi trường sản xuất
    )