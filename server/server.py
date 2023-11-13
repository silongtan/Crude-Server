import cgi
import http.server
import socketserver
import ssl
import os
import time
import threading

ROOT_DIR = os.path.dirname(__file__)
SUBDIRECTORIES = ['favicon.ico']
for root, dirs, files in os.walk(ROOT_DIR):
    for dir in dirs:
        if dir != 'certificates':
            SUBDIRECTORIES.append(dir)

CLIENT_LAST_REQUEST_TIME = dict()

RATE_LIMIT_LOCK = threading.Lock()

class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):

    RATE_LIMIT_PERIOD = 1
    RATE_LIMIT_REQUESTS = 5

    MAX_GET_URL_LENGTH = 1024

    def __init__(self, *args, **kwargs):
        self.client_last_request_time = {}
        super().__init__(*args, **kwargs)

    def can_process_request(self, client_address):
        print(CLIENT_LAST_REQUEST_TIME)
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
        client_address = self.client_address[0]
        if not self.can_process_request(client_address):
            self.send_response(429)  # HTTP 429 Too Many Requests
            self.end_headers()
            self.wfile.write(b"Rate limit exceeded. Please wait and try again.")
            return
        if len(self.path) > self.MAX_GET_URL_LENGTH:
            self.send_error(414, "URI Too Long")
            self.end_headers()
            return
        path = '/' if self.path == '/' else str(self.path).lstrip('/').rstrip('/')
        legal = (path == '/')
        if not legal:
            for subdir in SUBDIRECTORIES:
                if path.startswith(subdir):
                    legal = True
                    break
        if not legal:
            self.send_error(403, 'Unauthorized Access')
            self.end_headers()
        else:
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

    def handle_post(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        # Handle POST data as needed
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"Received POST data: {post_data}".encode('utf-8'))
        
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
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: No file uploaded.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Invalid content type for file upload.")

    # disable some http methods which will not be implemented for this project
    def do_PUT(self):
        self.send_error(405)

    def do_DELETE(self):
        self.send_error(405)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    pass

def start_server():
    server_address = ('localhost', 8000)
    httpd = ThreadedHTTPServer(server_address, CustomRequestHandler)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('certificates/certificate.pem', 'certificates/key.pem')
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    try:
        print(f"Server started at https://{server_address[0]}:{server_address[1]}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
        httpd.shutdown()
        httpd.server_close()
        print("Server successfully shut down.")

if __name__ == "__main__":
    start_server()
