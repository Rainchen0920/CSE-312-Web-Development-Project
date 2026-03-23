import os
import uuid
from util.auth import get_user_info
from util.database import user_collection
from util.database import video_collection
from util.response import Response
import datetime

class Part:
    def __init__(self):
        self.name = ""
        self.headers = {}
        self.content = b""  

class Multipart:
    def __init__(self):
        self.boundary = ""
        self.parts = []

    @staticmethod
    def upload_avatar(request, handler):
        user_info = get_user_info(request)
        if not user_info:
            res = Response().set_status(401, "Unauthorized").text("Not Logged in")
            handler.request.sendall(res.to_data())
            return

        multipart_data = parse_multipart(request)

        avatar_part = get_part_by_name(multipart_data, "avatar")
        if avatar_part is None:
            res = Response().set_status(400, "Bad Request").text("No avatar image file uploaded")
            handler.request.sendall(res.to_data())
            return

        filename = get_filename_from_part(avatar_part)
        if not filename:
            res = Response().set_status(400, "Bad Request").text("Missing Filename")
            handler.request.sendall(res.to_data())
            return

        extension = os.path.splitext(filename)[1].lower()
        if extension not in [".jpg", ".png", ".gif"]:
            res = Response().set_status(400, "Bad Request").text("Invalid File Type")
            handler.request.sendall(res.to_data())
            return

        os.makedirs("public/imgs/profile-pics", exist_ok=True)  # makes directory if it doesn't exist already

        avatar_dir = os.path.join("public", "imgs", "profile-pics")
        old_image_url = user_info.get("imageURL", "")

        if old_image_url.startswith("/public/imgs/profile-pics/"):
            old_path = old_image_url.lstrip("/")
            old_path = os.path.normpath(old_path)
            expected_dir = os.path.normpath(avatar_dir)
            if old_path.startswith(expected_dir) and os.path.exists(old_path):
                os.remove(old_path)

        saved_filename = uuid.uuid4().hex + extension
        full_path = os.path.join("public", "imgs", "profile-pics", saved_filename)

        with open(full_path, "wb") as f:
            f.write(avatar_part.content)

        image_url = "/public/imgs/profile-pics/" + saved_filename

        user_collection.update_one(
            {"id": user_info["id"]},
            {"$set": {"imageURL": image_url}}
        )

        res = Response().set_status(200, "OK").text("Avatar uploaded successfully")
        handler.request.sendall(res.to_data())

    @staticmethod
    def upload_video(request, handler):
        user_info = get_user_info(request)
        if not user_info:
            res = Response().set_status(401, "Unauthorized").text("Not Logged in")
            handler.request.sendall(res.to_data())
            return

        multipart_data = parse_multipart(request)

        title_part = get_part_by_name(multipart_data, "title")
        description_part = get_part_by_name(multipart_data, "description")
        video_part = get_part_by_name(multipart_data, "video")

        title = get_part_content(title_part)
        description = get_part_content(description_part)

        if video_part is None:
            res = Response().set_status(400, "Bad Request").text("Missing video file")
            handler.request.sendall(res.to_data())
            return

        filename = get_filename_from_part(video_part)
        if not filename:
            res = Response().set_status(400, "Bad Request").text("Missing filename")
            handler.request.sendall(res.to_data())
            return

        extension = os.path.splitext(filename)[1].lower()
        if extension != ".mp4":
            res = Response().set_status(400, "Bad Request").text("Only .mp4 files allowed")
            handler.request.sendall(res.to_data())
            return

        os.makedirs("public/videos", exist_ok=True)  # makes directory if it doesn't exist already

        video_id = uuid.uuid4().hex
        saved_filename = video_id + ".mp4"
        full_path = os.path.join("public", "videos", saved_filename)

        with open(full_path, "wb") as f:
            f.write(video_part.content)

        video_path = "/public/videos/" + saved_filename
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        video_collection.insert_one({
            "id": video_id,
            "author_id": user_info["id"],
            "title": title,
            "description": description,
            "video_path": video_path,
            "created_at": created_at
        })
        res = Response().set_status(200, "OK").json({"id": video_id})
        handler.request.sendall(res.to_data())
    
    @staticmethod
    def get_videos(request, handler):
        videos = []
        for video in video_collection.find():
            videos.append({
                "author_id": video.get("author_id", ""),
                "title": video.get("title", ""),
                "description": video.get("description", ""),
                "video_path": video.get("video_path", ""),
                "created_at": video.get("created_at", ""),
                "id": video.get("id", "")
            })

        res = Response().set_status(200, "OK").json({"videos": videos})
        handler.request.sendall(res.to_data())
    
    @staticmethod
    def get_video(request, handler):
        video_id = request.path.split("/api/videos/", 1)[1]

        video = video_collection.find_one({"id": video_id})
        if video is None:
            res = Response().set_status(404, "Not Found").json({})
            handler.request.sendall(res.to_data())
            return

        res = Response().set_status(200, "OK").json({
            "video": {
                "author_id": video.get("author_id", ""),
                "title": video.get("title", ""),
                "description": video.get("description", ""),
                "video_path": video.get("video_path", ""),
                "created_at": video.get("created_at", ""),
                "id": video.get("id", "")
            }
        })
        handler.request.sendall(res.to_data())


# can assume request is valid multipart request               
def parse_multipart(request):
    multipart_object = Multipart()
    multipart_object.boundary = request.headers["Content-Type"].split('boundary=')[1]

    delimiter = b"--" + multipart_object.boundary.encode() + b"\r\n"
    end_delimiter = b"--" + multipart_object.boundary.encode() + b"--" # last boundary has extra --
    raw_parts = request.body.split(end_delimiter)[0].split(delimiter)

    for part in raw_parts:
        if not part: # for handling the first element of raw_parts, which should be empty by the splitting
            continue
        if b"\r\n\r\n" not in part: # invalid part format
            continue

        object_part = Part()

        raw_headers, content = part.split(b"\r\n\r\n", 1)

        if content.endswith(b"\r\n"):
            content = content[:-2]
        object_part.content = content

        headers = raw_headers.split(b"\r\n")
        for header in headers:
            if (not header.strip()) or (b":" not in header):  # badly formed headers
                continue
            header_parts = header.split(b":", 1)
            name = header_parts[0].decode().strip()
            value = header_parts[1].decode().strip()
            object_part.headers[name] = value
        
        if "Content-Disposition" in object_part.headers:
            input_headers = object_part.headers["Content-Disposition"].split(";")
            for input_header in input_headers:
                input_header_parts = input_header.split("=", 1)
                if (len(input_header_parts) == 2) and (input_header_parts[0].strip() == "name"):
                    object_part.name = input_header_parts[1].strip().strip('"')
                    break
            if not object_part.name: # no 'name' header found
                continue  
        else:
            continue  # invalid part, Content-Disposition header missing
        
        multipart_object.parts.append(object_part)
    
    return multipart_object
    
def get_part_by_name(multipart_data, name):
    for part in multipart_data.parts:
        if part.name == name:
            return part
    return None

def get_part_content(part):
    if part is None:
        return ""
    return part.content.decode()
    

def get_filename_from_part(part):
    content_disposition = part.headers.get("Content-Disposition", "")
    for header in content_disposition.split(";"):
        header = header.strip()
        key_and_value = header.split("=", 1)
        if len(key_and_value) != 2:
            continue
        key = key_and_value[0].strip()
        value = key_and_value[1].strip().strip('"')
        if key == "filename":
            return value
    return "" 