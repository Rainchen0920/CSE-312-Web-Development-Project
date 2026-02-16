import json
import uuid
from util.response import Response
from util.database import chat_collection


def escape_html(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#x27;")


def read_json(request) -> dict:
    if request.body is None or request.body == b"":
        return {}
    return json.loads(request.body.decode())

def remove_query_string(path: str) -> str: 
    return path.split("?", 1)[0]

def get_session_id(request):
    return request.cookies.get("session")

def new_session_id():
    return uuid.uuid4().hex

session_to_author = {}
next_guest_num = 1

def author_from_session(session_id):
    global next_guest_num
    if session_id not in session_to_author:
        session_to_author[session_id] = f"guest{next_guest_num}"
        next_guest_num += 1
    return session_to_author[session_id]

def get_id_from_path(path: str):  # "/api/chats/<id>"
    path = remove_query_string(path)
    prefix = "/api/chats/"
    if not path.startswith(prefix):
        return None
    msg_id = path[len(prefix):]
    if msg_id:
        return msg_id
    else:
        return None


class ChatApi:

    def get_chats(request, handler):
        messages = []
        for chat_details in chat_collection.find({}):  # each entry = details for one chat msg
            messages.append({
                "author": chat_details.get("author", ""),
                "id": chat_details.get("id", ""),
                "content": chat_details.get("content", ""),
                "updated": bool(chat_details.get("updated", False)),
            })
        res = Response()
        res.json({"messages": messages})
        handler.request.sendall(res.to_data())

    def post_chat(request, handler):
        data = read_json(request)
        content = str(data.get("content", ""))
        session_id = get_session_id(request)
        res = Response()

        # set cookie when user send their first message
        if session_id is None:
            session_id = new_session_id()
            res.cookies({"session": session_id})

        author = author_from_session(session_id)
        msg_id = uuid.uuid4().hex

        chat_collection.insert_one({
            "id": msg_id,
            "author": author,
            "session": session_id,
            "content": escape_html(content),  # prevent HTML injection
            "updated": False
        })

        res.text("message sent")
        handler.request.sendall(res.to_data())

    def patch_chat(request, handler):
        msg_id = get_id_from_path(request.path)
        if msg_id is None:
            res = Response().set_status(404, "Not Found").text("404 Not Found")
            handler.request.sendall(res.to_data())
            return

        session_id = get_session_id(request)
        if session_id is None:
            res = Response().set_status(403, "Forbidden").text("403 Forbidden")
            handler.request.sendall(res.to_data())
            return

        chat_details = chat_collection.find_one({"id": msg_id})
        if chat_details is None:
            res = Response().set_status(404, "Not Found").text("404 Not Found")
            handler.request.sendall(res.to_data())
            return

        if chat_details.get("session") != session_id:
            res = Response().set_status(403, "Forbidden").text("403 Forbidden")
            handler.request.sendall(res.to_data())
            return

        data = read_json(request)
        new_content = str(data.get("content", ""))

        chat_collection.update_one(
            {"id": msg_id},
            {"$set": {"content": escape_html(new_content), "updated": True}}
        )

        res = Response().text("updated")
        handler.request.sendall(res.to_data())

    def delete_chat(request, handler):
        msg_id = get_id_from_path(request.path)
        if msg_id is None:
            res = Response().set_status(404, "Not Found").text("Not Found")
            handler.request.sendall(res.to_data())
            return

        session_id = get_session_id(request)
        if session_id is None:
            res = Response().set_status(403, "Forbidden").text("Forbidden")
            handler.request.sendall(res.to_data())
            return

        chat_details = chat_collection.find_one({"id": msg_id})
        if chat_details is None:
            res = Response().set_status(404, "Not Found").text("Not Found")
            handler.request.sendall(res.to_data())
            return

        if chat_details.get("session") != session_id:
            res = Response().set_status(403, "Forbidden").text("Forbidden")
            handler.request.sendall(res.to_data())
            return

        chat_collection.delete_one({"id": msg_id})

        res = Response().text("deleted")
        handler.request.sendall(res.to_data())