import json
import uuid
from util.response import Response
from util.database import chat_collection
from util.database import user_collection
from util.auth import get_user_info
import hashlib


def escape_html(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#x27;")

def read_json(request) -> dict:
    if request.body is None or request.body == b"":
        return {}
    return json.loads(request.body.decode())

def get_id_from_path(path: str):  # "/api/chats/<id>"
    prefixes = ["/api/chats/","/api/reaction/","/api/nickname"]
    path_prefix = ""
    path_found = False
    for prefix in prefixes:
        if path.startswith(prefix):
            path_found = True
            path_prefix = prefix
    if not path_found:
        return None
    msg_id = path[len(path_prefix):]
    if msg_id:
        return msg_id
    else:
        return None

# does the preliminary checks for msg_id, the message, username
def check_details(request, handler):
    msg_id = get_id_from_path(request.path)
    if msg_id is None:
        res = Response().set_status(404, "Not Found").text("404 Not Found")
        handler.request.sendall(res.to_data())
        return False
        
    username = get_username(request)
    if username is None:
        res = Response().set_status(401, "Unauthorized").text("401 Unauthorized, Please Log In")
        handler.request.sendall(res.to_data())
        return False

    chat_details = chat_collection.find_one({"id": msg_id})
    if chat_details is None:
        res = Response().set_status(404, "Not Found").text("404 Not Found")
        handler.request.sendall(res.to_data())
        return False

    return True 

def get_username(request):
    given_token = request.cookies.get("auth_token")
    if not given_token:
        return None
    given_token_hash = hashlib.sha256(given_token.encode()).hexdigest()
    user_info = user_collection.find_one({"auth_token_hash": given_token_hash})
    if not user_info:
        return None
    return user_info.get("username")

class ChatApi:

    def get_chats(request, handler):
        messages = []
        for chat_details in chat_collection.find({}):  # each entry = details for one chat msg
            messages.append({
                "author": chat_details.get("author", ""),
                "id": chat_details.get("id", ""),
                "content": chat_details.get("content", ""),
                "reactions": chat_details.get("reactions", {}),
                "nickname": chat_details.get("nickname", ""),
                "updated": bool(chat_details.get("updated", False)),
                "imageURL": chat_details.get("imageURL", "")
            })
        res = Response()
        res.json({"messages": messages})
        handler.request.sendall(res.to_data())

    def post_chat(request, handler):
        data = read_json(request)
        content = str(data.get("content", ""))
        res = Response()

        author = get_username(request)
        if not author:
            res = Response().set_status(401, "Unauthorized").text("Not Logged in")
            handler.request.sendall(res.to_data())
            return

        msg_id = uuid.uuid4().hex

        chat_detail = chat_collection.find_one({"author": author})
        nickname = ""
        if chat_detail is not None:
            nickname = chat_detail.get("nickname", "")
        
        imageURL = ""
        user_detail = get_user_info(request)
        if user_detail is not None:
            imageURL = user_detail.get("imageURL", "")

        chat_collection.insert_one({
            "id": msg_id,
            "author": author,
            "content": escape_html(content),  # prevent HTML injection
            "updated": False,
            "nickname": nickname,
            "reactions": {},
            "imageURL": imageURL
        })

        handler.request.sendall(res.to_data())

    def patch_chat(request, handler):
        msg_id = get_id_from_path(request.path)
        if not check_details(request, handler):
            return
        chat_details = chat_collection.find_one({"id": msg_id})
        username = get_username(request)
        if chat_details.get("author") != username: 
            res = Response().set_status(403, "Forbidden").text("403 Forbidden")
            handler.request.sendall(res.to_data())
            return 

        data = read_json(request)
        new_content = str(data.get("content", ""))
        chat_collection.update_one({"id": msg_id},{"$set": {"content": escape_html(new_content), "updated": True}})

        response = Response().text("message updated")
        handler.request.sendall(response.to_data())

    def delete_chat(request, handler):
        msg_id = get_id_from_path(request.path)
        if not check_details(request, handler):
            return
        chat_details = chat_collection.find_one({"id": msg_id})
        username = get_username(request)
        if chat_details.get("author") != username: 
            res = Response().set_status(403, "Forbidden").text("403 Forbidden")
            handler.request.sendall(res.to_data())
            return 

        chat_collection.delete_one({"id": msg_id})

        response = Response().text("message deleted")
        handler.request.sendall(response.to_data())

    def add_reaction(request, handler):
        msg_id = get_id_from_path(request.path)
        username = get_username(request)
        data = read_json(request)
        emoji = data.get("emoji")

        if not check_details(request, handler):
            return
        
        reactions = chat_collection.find_one({"id": msg_id}).get("reactions")
        if not reactions:
            reactions = {emoji: [username]}
        elif(emoji not in reactions):
            reactions[emoji] = [username]
        else: 
            if username in reactions[emoji]:
                res = Response().set_status(403, "Forbidden").text("403 Forbidden")
                handler.request.sendall(res.to_data())
                return 
            else: 
                reactions[emoji].append(username)
        
        chat_collection.update_one({"id": msg_id}, {"$set": {"reactions": reactions}})

        response = Response().text("reaction added")
        handler.request.sendall(response.to_data())


    def delete_reaction(request, handler):
        msg_id = get_id_from_path(request.path)
        username = get_username(request)
        data = read_json(request)
        emoji = data.get("emoji")
        
        if not check_details(request, handler):
            return
        
        reactions = chat_collection.find_one({"id": msg_id}).get("reactions")
        if (not reactions) or (emoji not in reactions) or (username not in reactions[emoji]):
            res = Response().set_status(403, "Forbidden").text("403 Forbidden")
            handler.request.sendall(res.to_data())
            return
        
        reactions[emoji].remove(username)
        if not reactions[emoji]:
            reactions.pop(emoji)
        
        chat_collection.update_one({"id": msg_id}, {"$set": {"reactions": reactions}})

        response = Response().text("reaction deleted")
        handler.request.sendall(response.to_data())
    
    def change_nickname(request, handler):
        username = get_username(request)
        data = read_json(request)
        nickname = data.get("nickname")

        if username is None:
            res = Response().set_status(403, "Forbidden").text("403 Forbidden")
            handler.request.sendall(res.to_data())
            return
        
        chat_collection.update_many({"author": username},{"$set": {"nickname": nickname}})

        response = Response().text("nickname changed")
        handler.request.sendall(response.to_data())