import http.server
import socketserver
import threading

class CustomRequestHandler(http.server.SimpleHTTPRequestHandler):
    def handle_GET(self):
        super().handle_GET()

    def handle_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        # Handle POST data as needed
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"Received POST data: {post_data}".encode('utf-8'))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

def start_server():
    server_address = ('localhost', 8000)
    num_threads = 4

    httpd = ThreadedHTTPServer(server_address, CustomRequestHandler)
    httpd.num_threads = num_threads

    try:
        print("Starting HTTP server on", server_address)
        http_thread = threading.Thread(target=httpd.serve_forever)
        http_thread.start()

        http_thread.join()

    except KeyboardInterrupt:
        print("Shutting down the server.")
        httpd.shutdown()

if __name__ == "__main__":
    start_server()
