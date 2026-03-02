import bcrypt
import hashlib
import uuid
from util.response import Response
from util.database import user_collection

def percent_decode(s: str):
    decoded_str = ""
    i = 0
    while i < len(s):
        if s[i] == '%':
            decoded_str += chr(int(s[i+1:i+3], 16))
            i += 3
        else:
            decoded_str += s[i]
            i += 1
    return decoded_str

def extract_credentials(request):
    name, pw = request.body.decode().split('&')
    username = name.split('=', 1)[1]
    password = percent_decode(pw.split('=', 1)[1])
    return [username, password]

def validate_password(password: str):
    special_chars = {'!', '@', '#', '$', '%', '^', '&', '(', ')', '-', '_', '='}
    if len(password) < 8:
        return False
    has_upper = False
    has_lower = False
    has_digit = False
    has_special = False
    for char in password:
        if char.isupper():
            has_upper = True
        elif char.islower():
            has_lower = True
        elif char.isdigit():
            has_digit = True
        elif char in special_chars:
            has_special = True
        else:
            return False
    return has_digit and has_lower and has_upper and has_special

def get_user_info(request):
    token = request.cookies.get("auth_token")
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return user_collection.find_one({"auth_token_hash": token_hash})

def get_query_param(path: str, key: str):
    if "?" not in path:
        return None
    query = path.split("?", 1)[1]
    for part in query.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k == key:
                return v
    return None

class Authentication:

    def register(request, handler):
        username, password = extract_credentials(request)
        if not validate_password(password):
            res = Response().set_status(400, "Bad Request").text("Better Password Please")
            handler.request.sendall(res.to_data())
            return 
        if user_collection.find_one({"username": username}) is not None:
            res = Response().set_status(400, "Bad Request").text("Username Already Exists")
            handler.request.sendall(res.to_data())
            return 
        salt = bcrypt.gensalt()
        pw_hash = bcrypt.hashpw(password.encode(), salt)
        user_collection.insert_one({
            "id": uuid.uuid4().hex,
            "username": username, 
            "auth_token_hash": "", 
            "password_hash": pw_hash # password + salt cuz bcrypt
        })
        res = Response().set_status(200, "OK").text("Registered")
        handler.request.sendall(res.to_data())
        
    def login(request, handler):
        username, password = extract_credentials(request)
        given_password = password
        user_info = user_collection.find_one({"username": username})
        if not user_info:
            res = Response().set_status(400, "Bad Request").text("Wrong Username")
            handler.request.sendall(res.to_data())
            return 
        if not bcrypt.checkpw(given_password.encode(), user_info.get("password_hash")):
            res = Response().set_status(400, "Bad Request").text("Incorrect Password")
            handler.request.sendall(res.to_data())
            return 
        auth_token = uuid.uuid4().hex
        auth_token_hash = hashlib.sha256(auth_token.encode()).hexdigest()
        user_collection.update_one({"username": username}, {"$set": {"auth_token_hash": auth_token_hash}})
        res = Response().set_status(200, "OK").text("Logged In, Authentication Token generated")
        res.cookies({"auth_token": f"{auth_token}; HttpOnly; Max-Age=3600"})
        handler.request.sendall(res.to_data())

    def logout(request, handler):
        token = request.cookies.get("auth_token")
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            # clear out token hash server side
            user_collection.update_one({"auth_token_hash": token_hash}, {"$set": {"auth_token_hash": ""}})

        res = Response().set_status(302, "Found")
        res.headersDict["Location"] = "/"  # redirect to homepage

        res.cookies({"auth_token": "deleted; HttpOnly; Max-Age=0"})
        handler.request.sendall(res.to_data())

    def display_profile(request, handler):
        user_info = get_user_info(request)
        if not user_info:
            res = Response().set_status(401, "Unauthorized").json({})
            handler.request.sendall(res.to_data())
            return

        profile = dict(user_info)
        profile.pop("password_hash", None)
        profile.pop("auth_token_hash", None)

        res = Response().set_status(200, "OK").json(profile)
        handler.request.sendall(res.to_data())

    def search_users(request, handler):
        prefix = get_query_param(request.path, "user")
        if prefix is None:
            prefix = ""

        if prefix == "":
            res = Response().set_status(200, "OK").json({"users": []})
            handler.request.sendall(res.to_data())
            return

        list_of_results = []
        for user_info in user_collection.find({}):
            username = user_info.get("username", "")
            if username.startswith(prefix):
                list_of_results.append({"id": user_info.get("id"), "username": username})

        res = Response().set_status(200, "OK").json({"users": list_of_results})
        handler.request.sendall(res.to_data())

    def update_login(request, handler):
        user_info = get_user_info(request)
        if not user_info:
            res = Response().set_status(401, "Unauthorized").text("Not Logged In")
            handler.request.sendall(res.to_data())
            return

        new_username, new_password = extract_credentials(request)    

        if (new_password != "") and (not validate_password(new_password)):
            res = Response().set_status(400, "Bad Request").text("Invalid Password")
            handler.request.sendall(res.to_data())
            return

        if new_username != user_info.get("username"):   # in case of duplicate username
            if user_collection.find_one({"username": new_username}) is not None:
                res = Response().set_status(400, "Bad Request").text("Username Already Taken")
                handler.request.sendall(res.to_data())
                return

        pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        user_collection.update_one({"id": user_info.get("id")}, {"$set": {"username": new_username, "password_hash": pw_hash}})

        res = Response().set_status(200, "OK").text("Login Updated")
        handler.request.sendall(res.to_data())