import cgi
import http.server
import socketserver
import logging
import os

ROOT_DIR = os.path.dirname(__file__)
SUBDIRECTORIES = []
for root, dirs, files in os.walk(ROOT_DIR):
    for dir in dirs:
        SUBDIRECTORIES.append(dir)

class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = '/' if self.path == '/' else str(self.path).lstrip('/').rstrip('/')
        legal = (path == '/')
        if not legal:
            for subdir in SUBDIRECTORIES:
                if path.startswith(subdir):
                    legal = True
                    break
        if not legal:
            self.send_error(403, 'Unauthorized Access')
        else:
            super().do_GET()

    def do_POST(self):
        # logging.info("POST request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        if self.path == '/upload':
            self.handle_file_upload()
        else:
            self.handle_post()

    def handle_post(self):
        # logging.info("POST request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
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


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    pass

def start_server():
    server_address = ('localhost', 8000)
    httpd = ThreadedHTTPServer(server_address, CustomRequestHandler)
    try:
        print(f"Server started at http://{server_address[0]}:{server_address[1]}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
        httpd.shutdown()
        httpd.server_close()
        print("Server successfully shut down.")

if __name__ == "__main__":
    start_server()
