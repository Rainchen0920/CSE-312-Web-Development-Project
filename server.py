import socketserver
from util.request import Request
from util.router import Router
from util.hello_path import hello_path
from util.public_paths import PublicPaths
from util.chat_api import ChatApi

class MyTCPHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.router = Router()

        def render_index(req, handler):
            PublicPaths.render_page(req, handler, "index.html")

        def render_chat(req, handler):
            PublicPaths.render_page(req, handler, "chat.html")

        self.router.add_route("GET", "/hello", hello_path, True)
        # TODO: Add your routes here
        self.router.add_route("GET", "/", render_index, True)
        self.router.add_route("GET", "/chat", render_chat, True)
        self.router.add_route("GET", "/public", PublicPaths.serve_from_public, False)

        # routes for chat functionality
        self.router.add_route("GET", "/api/chats", ChatApi.get_chats, True)
        self.router.add_route("POST", "/api/chats", ChatApi.post_chat, True)
        self.router.add_route("PATCH", "/api/chats", ChatApi.patch_chat, False)
        self.router.add_route("DELETE", "/api/chats", ChatApi.delete_chat, False)

        # routes for AO1 and AO2
        self.router.add_route("PATCH", "/api/reaction", ChatApi.add_reaction, False)
        self.router.add_route("DELETE", "/api/reaction", ChatApi.delete_reaction, False)
        self.router.add_route("PATCH", "/api/nickname", ChatApi.change_nickname, True)

        super().__init__(request, client_address, server)

    def handle(self):
        received_data = self.request.recv(2048)
        print(self.client_address)
        print("--- received data ---")
        print(received_data)
        print("--- end of data ---\n\n")
        request = Request(received_data)
        self.router.route_request(request, self)

def main():
    host = "0.0.0.0"
    port = 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    server = socketserver.ThreadingTCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
