import socketserver

from util.request import Request
from util.router import Router
from util.auth import Authentication


class AuthTCPHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.router = Router()

        self.router.add_route("POST", "/register", Authentication.register, True)
        self.router.add_route("POST", "/login", Authentication.login, True)
        self.router.add_route("GET", "/logout", Authentication.logout, True)
        self.router.add_route("POST", "/api/users/settings", Authentication.update_login, True)

        super().__init__(request, client_address, server)

    def handle(self):
        received_data = self.request.recv(2048)

        header_end_index = received_data.find(b"\r\n\r\n")
        raw_headers = received_data[:header_end_index]
        body = received_data[header_end_index + 4:]

        headers_text = raw_headers.decode()
        content_length = 0

        for line in headers_text.split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
                break

        while len(body) < content_length:
            chunk = self.request.recv(2048)
            if not chunk:
                break
            body += chunk

        full_data = raw_headers + b"\r\n\r\n" + body

        request = Request(full_data)
        self.router.route_request(request, self)


def main():
    host = "0.0.0.0"
    port = 8081

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((host, port), AuthTCPHandler)

    print("Auth server listening on port " + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()