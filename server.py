import socketserver
from util.request import Request
from util.router import Router
from util.hello_path import hello_path
from util.public_paths import PublicPaths
from util.chat_api import ChatApi
from util.auth import Authentication
from util.multipart import Multipart

class MyTCPHandler(socketserver.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.router = Router()
        self.router.add_route("GET", "/hello", hello_path, True)

        # TODO: Add your routes here
        def render_index(req, handler):
            PublicPaths.render_page(req, handler, "index.html")
        def render_chat(req, handler):
            PublicPaths.render_page(req, handler, "chat.html")

        self.router.add_route("GET", "/", render_index, True)
        self.router.add_route("GET", "/chat", render_chat, True)
        self.router.add_route("GET", "/public", PublicPaths.serve_from_public, False)

        # routes for chat functionality
        self.router.add_route("GET", "/api/chats", ChatApi.get_chats, True)
        self.router.add_route("POST", "/api/chats", ChatApi.post_chat, True)
        self.router.add_route("PATCH", "/api/chats", ChatApi.patch_chat, False)
        self.router.add_route("DELETE", "/api/chats", ChatApi.delete_chat, False)

        # routes for HW1 AO1 and AO2
        self.router.add_route("PATCH", "/api/reaction", ChatApi.add_reaction, False)
        self.router.add_route("DELETE", "/api/reaction", ChatApi.delete_reaction, False)
        self.router.add_route("PATCH", "/api/nickname", ChatApi.change_nickname, True)

        # routes for authentication LO
        def register(req, handler):
            PublicPaths.render_page(req, handler, "register.html")
        def login(req, handler):
            PublicPaths.render_page(req, handler, "login.html")
        def settings(req, handler):
            PublicPaths.render_page(req, handler, "settings.html")
        def search_users(req, handler):
            PublicPaths.render_page(req, handler, "search-users.html")

        self.router.add_route("GET", "/register", register, True)
        self.router.add_route("GET", "/login", login, True)
        self.router.add_route("GET", "/settings", settings, True)
        self.router.add_route("GET", "/search-users", search_users, True)

        self.router.add_route("POST", "/register", Authentication.register, True)
        self.router.add_route("POST", "/login", Authentication.login, True)
        self.router.add_route("GET", "/logout", Authentication.logout, True)
        self.router.add_route("GET", "/api/users/@me", Authentication.display_profile, True)
        self.router.add_route("GET", "/api/users/search", Authentication.search_users, False)
        self.router.add_route("POST", "/api/users/settings", Authentication.update_login, True)

        # routes for file uploads
        def change_avatar(req, handler):
            PublicPaths.render_page(req, handler, "change-avatar.html")
        def videotube(req, handler):
            PublicPaths.render_page(req, handler, "videotube.html")
        def upload(req, handler):
            PublicPaths.render_page(req, handler, "upload.html")
        def view_video(req, handler):
            PublicPaths.render_page(req, handler, "view-video.html")

        self.router.add_route("GET", "/change-avatar", change_avatar, True)
        self.router.add_route("POST", "/api/users/avatar", Multipart.upload_avatar, True)
        self.router.add_route("GET", "/videotube", videotube, True)
        self.router.add_route("GET", "/videotube/upload", upload, True)
        self.router.add_route("GET", "/videotube/videos", view_video, False)
        self.router.add_route("POST", "/api/videos", Multipart.upload_video, True)
        self.router.add_route("GET", "/api/videos", Multipart.get_videos, True)
        self.router.add_route("GET", "/api/videos", Multipart.get_video, False)

        # HW3 AO1
        def set_thumbnail(req, handler):
            PublicPaths.render_page(req, handler, "set-thumbnail.html")
        
        self.router.add_route("GET", "/videotube/set-thumbnail", set_thumbnail, False)
        self.router.add_route("PUT", "/api/thumbnails", Multipart.change_thumbnail, False)

        super().__init__(request, client_address, server)

    def handle(self):
        received_data = self.request.recv(2048)
        # no need to check if its valid since headers are included in first 2048 bytes
        header_end_index = received_data.find(b"\r\n\r\n")  
        raw_headers = received_data[:header_end_index]
        body = received_data[header_end_index + 4:]  # +4 to remove the \r\n\r\n

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

        # print(self.client_address)
        # print("--- received data ---")
        # print(full_data)
        # print("--- end of data ---\n\n")

        request = Request(full_data)
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
