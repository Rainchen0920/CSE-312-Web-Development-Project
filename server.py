import socketserver
from util.request import Request
from util.response import Response
from util.router import Router
from util.hello_path import hello_path
from util.public_paths import PublicPaths
from util.chat_api import ChatApi
from util.auth import Authentication, get_user_info
from util.multipart import Multipart
import json
from util.websockets import compute_accept, parse_ws_frame, parse_ws_frame_buffered, generate_ws_frame
from util.database import drawing_collection, room_collection
import uuid

active_ws_connections = []

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
        # self.router.add_route("GET", "/public", PublicPaths.serve_from_public, False)

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

        self.router.add_route("GET", "/api/users/@me", Authentication.display_profile, True)
        self.router.add_route("GET", "/api/users/search", Authentication.search_users, False)

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

        # HW4
        def test_websocket(req, handler):
            PublicPaths.render_page(req, handler, "test-websocket.html")
        def drawing_board(req, handler):
            PublicPaths.render_page(req, handler, "drawing-board.html")
        def video_call(req, handler):
            PublicPaths.render_page(req, handler, "video-call.html")
        def video_call_room(req, handler):
            PublicPaths.render_page(req, handler, "video-call-room.html")
        def websocket_route(req, handler):
            handler.handle_websocket(req)
        def create_video_call(req, handler):
            user_info = get_user_info(req)
            if not user_info:
                res = Response().set_status(401, "Unauthorized").text("Not Logged In")
                handler.request.sendall(res.to_data())
                return

            body = json.loads(req.body.decode())
            room_name = body.get("name", "").strip()

            if room_name == "":
                res = Response().set_status(400, "Bad Request").text("Missing Room Name")
                handler.request.sendall(res.to_data())
                return

            room_id = uuid.uuid4().hex

            room_collection.insert_one({
                "id": room_id,
                "name": room_name
            })

            res = Response().json({"id": room_id})
            handler.request.sendall(res.to_data())

        self.router.add_route("GET", "/test-websocket", test_websocket, True)
        self.router.add_route("GET", "/drawing-board", drawing_board, True)
        self.router.add_route("GET", "/video-call", video_call, True)
        self.router.add_route("GET", "/video-call", video_call_room, False)
        self.router.add_route("GET", "/websocket", websocket_route, True)
        self.router.add_route("POST", "/api/video-calls", create_video_call, True)

        super().__init__(request, client_address, server)

    def handle_websocket(self, request):
        key = request.headers.get("Sec-WebSocket-Key")
        if key is None:
            res = Response().set_status(400, "Bad Request").text("Missing WebSocket Key")
            self.request.sendall(res.to_data())
            return

        user_info = get_user_info(request)
        if not user_info:
            res = Response().set_status(401, "Unauthorized").text("Not Logged In")
            self.request.sendall(res.to_data())
            return

        accept = compute_accept(key)

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        self.request.sendall(response.encode())

        socket_id = uuid.uuid4().hex
        active_ws_connections.append({
            "handler": self,
            "username": user_info.get("username"),
            "socketId": socket_id,
            "callId": None
        })

        existing_strokes = list(drawing_collection.find({}, {"_id": 0}))
        init_message = {
            "messageType": "init_strokes",
            "strokes": existing_strokes
        }
        self.send_ws(init_message)
        self.broadcast_users()

        connected = True
        buffer = request.body
        partial_frame_in_progress = False
        partial_payload = b""

        while connected:
            if len(buffer) == 0:
                data = self.request.recv(2048)
                if not data:
                    connected = False
                    break
                buffer += data

            parsing = True
            while parsing:
                frame, bytes_used = parse_ws_frame_buffered(buffer)

                if frame is None:
                    data = self.request.recv(2048)
                    if not data:
                        connected = False
                        parsing = False
                        break
                    buffer += data
                    continue

                buffer = buffer[bytes_used:]

                if frame.opcode == 8:
                    connected = False
                    parsing = False
                    break

                # for case where new frame starts while there is a fragmented frame still
                if frame.opcode == 1 and partial_frame_in_progress:
                    partial_frame_in_progress = False
                    partial_payload = b""

                # Regular single-frame message
                if frame.opcode == 1 and frame.fin_bit == 1:
                    if len(frame.payload) == 0:
                        continue

                    message = json.loads(frame.payload.decode())
                    connected = self.handle_ws_message(message)

                    if not connected:
                        parsing = False
                        break

                    continue

                # back to back
                if frame.opcode == 1 and frame.fin_bit == 0:
                    partial_frame_in_progress = True
                    partial_payload = frame.payload
                    continue

                # Continuation frame
                if frame.opcode == 0:
                    if not partial_frame_in_progress:
                        continue

                    partial_payload += frame.payload

                    if frame.fin_bit == 1:
                        complete_payload = partial_payload

                        partial_frame_in_progress = False
                        partial_payload = b""

                        if len(complete_payload) == 0:
                            continue

                        message = json.loads(complete_payload.decode())
                        connected = self.handle_ws_message(message)

                        if not connected:
                            parsing = False
                            break

                    continue
    
                continue    

            current_connection = self.get_active_connection()
            if current_connection is not None and current_connection["callId"] is not None:
                self.broadcast_call_room(
                    current_connection["callId"],
                    {
                        "messageType": "user_left",
                        "socketId": current_connection["socketId"]
                    },
                    exclude_self=True
                )

            self.remove_active_connection()
            self.broadcast_users()
            self.request.close()

    def handle_ws_message(self, message):
        msg_type = message.get("messageType")

        if msg_type == "echo_client":
            response = {
                "messageType": "echo_server",
                "text": message.get("text", "")
            }
            self.send_ws(response)
            return True

        if msg_type == "drawing":
            drawing_details = {
                "startX": message.get("startX"),
                "startY": message.get("startY"),
                "endX": message.get("endX"),
                "endY": message.get("endY"),
                "color": message.get("color")
            }
            drawing_collection.insert_one(drawing_details)
            self.broadcast(message)
            return True
        
        if msg_type == "get_calls":
            rooms = list(room_collection.find({}, {"_id": 0}))
            self.send_ws({
                "messageType": "call_list",
                "calls": rooms
            })
            return True
        
        if msg_type == "join_call":
            call_id = message.get("callId")
            if not call_id:
                return True 

            room = room_collection.find_one({"id": call_id}, {"_id": 0})
            if not room:
                return True

            current_connection = self.get_active_connection()
            if current_connection is None:
                return True

            current_connection["callId"] = call_id

            self.send_ws({
                "messageType": "call_info",
                "name": room.get("name", "")
            })

            participants = []
            for connection in active_ws_connections:
                if connection["handler"] != self and connection["callId"] == call_id:
                    participants.append({
                        "socketId": connection["socketId"],
                        "username": connection["username"]
                    })

            self.send_ws({
                "messageType": "existing_participants",
                "participants": participants
            })

            self.broadcast_call_room(call_id, {
                "messageType": "user_joined",
                "socketId": current_connection["socketId"],
                "username": current_connection["username"]
            }, exclude_self=True)

            return True
        
        if msg_type == "offer" or msg_type == "answer" or msg_type == "ice_candidate":
            target_socket_id = message.get("socketId")
            if not target_socket_id:
                return True

            sender = self.get_active_connection()
            if sender is None:
                return True

            forwarded_message = message.copy()
            forwarded_message["socketId"] = sender["socketId"]
            forwarded_message["username"] = sender["username"]

            self.send_to_socket_id(target_socket_id, forwarded_message)
            return True

        return True

    def send_ws(self, message_dict):
        payload = json.dumps(message_dict).encode()
        frame = generate_ws_frame(payload)
        self.request.sendall(frame)

    def get_active_connection(self):
        for connection in active_ws_connections:
            if connection["handler"] == self:
                return connection
        return None

    def send_to_socket_id(self, socket_id, message_dict):
        payload = json.dumps(message_dict).encode()
        frame = generate_ws_frame(payload)

        for connection in active_ws_connections:
            if connection["socketId"] == socket_id:
                connection["handler"].request.sendall(frame)
                return

    def broadcast_call_room(self, call_id, message_dict, exclude_self=False):
        payload = json.dumps(message_dict).encode()
        frame = generate_ws_frame(payload)

        i = 0
        while i < len(active_ws_connections):
            connection = active_ws_connections[i]
            handler = connection["handler"]

            if handler.request.fileno() == -1:
                active_ws_connections.pop(i)
                continue

            if connection["callId"] != call_id:
                i += 1
                continue

            if exclude_self and handler == self:
                i += 1
                continue

            handler.request.sendall(frame)
            i += 1

    def broadcast(self, message_dict):
        payload = json.dumps(message_dict).encode()
        frame = generate_ws_frame(payload)

        i = 0
        while i < len(active_ws_connections):
            connection = active_ws_connections[i]
            handler = connection["handler"]

            if handler.request.fileno() == -1:
                active_ws_connections.pop(i)
                continue

            handler.request.sendall(frame)
            i += 1

    def broadcast_users(self):
        users_message = {
            "messageType": "active_users_list",
            "users": []
        }

        i = 0
        while i < len(active_ws_connections):
            connection = active_ws_connections[i]
            handler = connection["handler"]

            if handler.request.fileno() == -1:
                active_ws_connections.pop(i)
                continue

            users_message["users"].append({
                "username": connection["username"]
            })
            i += 1

        payload = json.dumps(users_message).encode()
        frame = generate_ws_frame(payload)

        i = 0
        while i < len(active_ws_connections):
            connection = active_ws_connections[i]
            handler = connection["handler"]

            if handler.request.fileno() == -1:
                active_ws_connections.pop(i)
                continue

            handler.request.sendall(frame)
            i += 1

    def remove_active_connection(self):
        global active_ws_connections
        active_ws_connections = [
            connection for connection in active_ws_connections
            if connection["handler"] != self
        ]

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

        request = Request(full_data)
        self.router.route_request(request, self)

def main():
    host = "0.0.0.0"
    port = 8080
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    drawing_collection.delete_many({})

    server = socketserver.ThreadingTCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))
    server.serve_forever()


if __name__ == "__main__":
    main()
