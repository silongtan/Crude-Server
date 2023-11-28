import cgi
import http.server
import socketserver
import ssl
import os
import time
import threading
import hashlib
import mimetypes
import argparse
from collections import OrderedDict
import logging

ROOT_DIR = os.path.dirname(__file__)
SUBDIRECTORIES = ['favicon.ico']
for root, dirs, files in os.walk(ROOT_DIR):
    for dir in dirs:
        if dir != 'certificates':
            SUBDIRECTORIES.append(dir)

CLIENT_LAST_REQUEST_TIME = dict()

RATE_LIMIT_LOCK = threading.Lock()
CACHE_LOCK = threading.Lock()

class LRUCache:
    def __init__(self, capacity: int = 100):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        with CACHE_LOCK:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key, value):
        with CACHE_LOCK:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
            self.cache[key] = value

    def generate_key(self, path):
        return hashlib.md5(path.encode()).hexdigest()

CACHE = LRUCache(capacity=3)
USE_CACHE = True

class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):

    RATE_LIMIT_PERIOD = 1
    RATE_LIMIT_REQUESTS = 7

    MAX_GET_URL_LENGTH = 1024

    def __init__(self, *args, **kwargs):
        self.client_last_request_time = {}
        super().__init__(*args, **kwargs)

    def send_head(self):
        if USE_CACHE:
            path = self.translate_path(self.path)
            # divided by 1024 as getsize() returns values in bytes
            if os.path.isfile(path) and ((os.path.getsize(path) / 1024) > 500):
                cache_key = CACHE.generate_key(self.path)
                if not CACHE.get(cache_key):
                    with open(path, 'rb') as f:
                        content = f.read()
                        mime_type, _ = mimetypes.guess_type(path)
                        CACHE.set(cache_key, {'data': content, 'mime': mime_type})
        return super().send_head()

    def can_process_request(self, client_address):
        current_time = time.time()
        with RATE_LIMIT_LOCK:
            if client_address not in CLIENT_LAST_REQUEST_TIME:
                CLIENT_LAST_REQUEST_TIME[client_address] = []

            # Filter out requests outside the time window
            CLIENT_LAST_REQUEST_TIME[client_address] = [timestamp for timestamp in CLIENT_LAST_REQUEST_TIME[client_address] 
                                                        if current_time - timestamp < self.RATE_LIMIT_PERIOD]

            if len(CLIENT_LAST_REQUEST_TIME[client_address]) < self.RATE_LIMIT_REQUESTS:
                CLIENT_LAST_REQUEST_TIME[client_address].append(current_time)
                return True
            else:
                return False

    def do_GET(self):
        # logging.debug("Detailed information about the incoming request")
        client_address = self.client_address[0]
        if not self.can_process_request(client_address):
            self.send_response(429)  # HTTP 429 Too Many Requests
            self.end_headers()
            self.wfile.write(b"Rate limit exceeded. Please wait and try again.")
            logging.error(f"429: Too many GET requests, sender: {self.client_address}, path: {self.path}")
            return
        if len(self.path) > self.MAX_GET_URL_LENGTH:
            self.send_error(414, "URL Too Long")
            logging.error(f"414: URL Too Long, sender: {self.client_address}, path: {self.path}")
            self.end_headers()
            return
        path = '/' if self.path == '/' else str(self.path).lstrip('/').rstrip('/')
        if not os.path.exists(path):
            self.send_error(404, "File Not Found")
            logging.error(f"404: File Not Found, sender: {self.client_address}, path: {self.path}")
            return
        legal = (path == '/')
        if not legal:
            for subdir in SUBDIRECTORIES:
                if path.startswith(subdir):
                    legal = True
                    break
        if not legal:
            self.send_error(403, 'Unauthorized Access')
            logging.error(f"403: Unauthorized Access, sender: {self.client_address}, path: {self.path}")
            self.end_headers()
            return
        if USE_CACHE:
            cache_key = CACHE.generate_key(self.path)
            cached_response = CACHE.get(cache_key)

            if cached_response:
                self.send_response(200)
                self.send_header('Content-type', cached_response['mime'])
                self.end_headers()
                self.wfile.write(cached_response['data'])
                return
        logging.info(f"200: Received GET request from {self.client_address}, path: {self.path}")
        super().do_GET()

    def do_POST(self):
        client_address = self.client_address[0]
        if self.can_process_request(client_address):
            if self.path == '/upload':
                self.handle_file_upload()
            else:
                self.handle_post()
        else:
            self.send_response(429)  # HTTP 429 Too Many Requests
            self.end_headers()
            self.wfile.write(b"Rate limit exceeded. Please wait and try again.")
            logging.error(f"429: Too many POST requests, sender: {self.client_address}, path: {self.path}")

    def handle_post(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        # Handle POST data as needed
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"Received POST data: {post_data}".encode('utf-8'))
        logging.info(f"200: Received POST request from {self.client_address}, data: {post_data}, path: {self.path}")
        
    def handle_file_upload(self):
        UPLOAD_DIR = os.path.join(ROOT_DIR, 'assets')
        content_type, _ = cgi.parse_header(self.headers.get('Content-Type'))
        if content_type == 'multipart/form-data':
            form_data = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST',
                        'CONTENT_TYPE': self.headers['Content-Type'],
                        }
            )

            uploaded_file = form_data['file']

            # Check if the file was uploaded
            if uploaded_file.filename:
                # Save the uploaded file
                file_path = os.path.join(UPLOAD_DIR, uploaded_file.filename)
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.file.read())

                self.send_response(200)
                self.end_headers()
                self.wfile.write(f"File '{uploaded_file.filename}' uploaded successfully.".encode('utf-8'))
                logging.info(f"200: File '{uploaded_file.filename}' uploaded successfully, sender: {self.client_address}, path: {self.path}")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: No file uploaded.")
                logging.error(f"400: No file uploaded, sender: {self.client_address}, path: {self.path}")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Invalid content type for file upload.")
            logging.error(f"400: Invalid content type for file upload, sender: {self.client_address}, path: {self.path}")

    # disable some http methods which will not be implemented for this project
    def do_PUT(self):
        self.send_error(405)
        logging.error(f"405: Not supported (PUT), sender: {self.client_address}, path: {self.path}")

    def do_DELETE(self):
        self.send_error(405)
        logging.error(f"405: Not supported (DELETE), sender: {self.client_address}, path: {self.path}")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    pass

def config_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler('server.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def start_server(cached: bool = True):
    USE_CACHE = cached
    config_logging()
    server_address = ('localhost', 8000)
    httpd = ThreadedHTTPServer(server_address, CustomRequestHandler)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('certificates/certificate.pem', 'certificates/key.pem')
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    try:
        print(f"Server started at https://{server_address[0]}:{server_address[1]}")
        logging.info(f"Server started at https://{server_address[0]}:{server_address[1]}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
        httpd.shutdown()
        httpd.server_close()
        print("Server successfully shut down.")
        logging.info("Server shut down.")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Start a multi-threaded HTTP server.')
    parser.add_argument('--cached', action='store_true', help='Enable cache support.')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    start_server(args.cached)
