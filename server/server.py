import http.server
import socketserver
import threading
import time
import logging
import os

class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        # logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        if self.path == '/':
            self.path = '/index.html'

        # Check if the requested file exists
        file_path = os.path.join(os.getcwd(), self.path[1:])
        if os.path.exists(file_path):
            super().do_GET()
        else:
            self.send_error(404, 'File Not Found')

    def do_POST(self):
        # logging.info("POST request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        # Handle POST data as needed
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"Received POST data: {post_data}".encode('utf-8'))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

def start_server():
    HOST_NAME = "localhost"
    PORT_NUMBER = 8000
    server_address = (HOST_NAME, PORT_NUMBER)

    httpd = ThreadedHTTPServer(server_address, CustomRequestHandler)

    try:
        print("Starting HTTP server on", server_address)
        logging.basicConfig(level=logging.INFO)
        http_thread = threading.Thread(target=httpd.serve_forever)
        http_thread.start()

        http_thread.join()

    except KeyboardInterrupt:
        print("Shutting down the server.")
        print(time.asctime(), 'Server DOWN - %s:%s' % (HOST_NAME, PORT_NUMBER))
        httpd.shutdown()

if __name__ == "__main__":
    start_server()
