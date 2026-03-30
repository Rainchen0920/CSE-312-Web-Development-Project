import os
import uuid
from util.auth import get_user_info
from util.database import user_collection
from util.database import video_collection
from util.response import Response
import datetime
import subprocess
import json

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
        
        thumbnails = generate_thumbnails(video_id, full_path)
        thumbnail_url = thumbnails[0]  # first frame is default thumbnail 

        hls_path = generate_hls(video_id, full_path)

        video_path = "/public/videos/" + saved_filename
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        video_collection.insert_one({
            "id": video_id,
            "author_id": user_info["id"],
            "title": title,
            "description": description,
            "video_path": video_path,
            "created_at": created_at, 
            "thumbnails": thumbnails,
            "thumbnailURL": thumbnail_url,
            "hls_path": hls_path
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
                "id": video.get("id", ""),
                "thumbnails": video.get("thumbnails", []),
                "thumbnailURL": video.get("thumbnailURL", ""),
                "hls_path": video.get("hls_path", "")
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
                "id": video.get("id", ""),
                "thumbnails": video.get("thumbnails", []),
                "thumbnailURL": video.get("thumbnailURL", ""),
                "hls_path": video.get("hls_path", "")
            }
        })
        handler.request.sendall(res.to_data())

    @staticmethod
    def change_thumbnail(request, handler):
        video_id = request.path.split("/api/thumbnails/", 1)[1]

        if not request.body:
            res = Response().set_status(400, "Bad Request").text("Empty request body")
            handler.request.sendall(res.to_data())
            return
        body = json.loads(request.body.decode())

        thumbnail_url = body.get("thumbnailURL", "")
        if thumbnail_url == "":
            res = Response().set_status(400, "Bad Request").text("Thumbnail URL does not exist")
            handler.request.sendall(res.to_data())
            return

        video = video_collection.find_one({"id": video_id})
        if video is None:
            res = Response().set_status(404, "Not Found").text("Video not found")
            handler.request.sendall(res.to_data())
            return

        if thumbnail_url not in video.get("thumbnails", []):
            res = Response().set_status(400, "Bad Request").text("Thumbnail does not belong to this video")
            handler.request.sendall(res.to_data())
            return

        video_collection.update_one(
            {"id": video_id},
            {"$set": {"thumbnailURL": thumbnail_url}}
        )
        res = Response().set_status(200, "OK").text("Thumbnail updated successfully")
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

def get_video_duration(video_file_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file_path],
        capture_output=True,
        text=True
    )
    duration_text = result.stdout.strip()
    return float(duration_text)

def generate_thumbnails(video_id, video_file_path):
    os.makedirs("public/imgs/thumbnails", exist_ok=True)
    duration = get_video_duration(video_file_path)
    timestamps = [0, duration * 0.25, duration * 0.50, duration * 0.75, max(duration * 0.98, 0)]
    thumbnail_urls = []

    for i, timestamp in enumerate(timestamps):
        saved_filename = f"{video_id}_{i}.jpg"
        output_path = os.path.join("public", "imgs", "thumbnails", saved_filename)
        subprocess.run(  # -q:v for video quality
            ["ffmpeg", "-ss", str(timestamp), "-i", video_file_path, "-frames:v", "1", "-q:v", "2", "-y", output_path],  
            capture_output=True
        )
        thumbnail_urls.append(f"public/imgs/thumbnails/{saved_filename}")

    return thumbnail_urls

def generate_hls(video_id, input_video_path):
    output_dir = os.path.join("public", "videos", video_id)
    os.makedirs(output_dir, exist_ok=True)
    low_playlist = os.path.join(output_dir, "360p.m3u8")
    high_playlist = os.path.join(output_dir, "720p.m3u8")

    subprocess.run(
        ["ffmpeg", "-i", input_video_path, "-vf", "scale=-2:360",
            "-c:v", "libx264", "-b:v", "800k", "-c:a", "aac", "-b:a", "96k",
            "-f", "hls", 
            "-hls_list_size", "0", 
            "-hls_segment_filename", os.path.join(output_dir, "360p_%03d.ts"),
            "-y", low_playlist], 
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    subprocess.run(
        ["ffmpeg", "-i", input_video_path, "-vf", "scale=-2:720",
            "-c:v", "libx264", "-b:v", "2500k", "-c:a", "aac", "-b:a", "128k",
            "-f", "hls",
            "-hls_list_size", "0",
            "-hls_segment_filename", os.path.join(output_dir, "720p_%03d.ts"),
            "-y", high_playlist],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    index_path = os.path.join(output_dir, "master.m3u8")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-STREAM-INF:BANDWIDTH=896000,RESOLUTION=640x360\n")
        f.write("360p.m3u8\n")
        f.write("#EXT-X-STREAM-INF:BANDWIDTH=2628000,RESOLUTION=1280x720\n")
        f.write("720p.m3u8\n")

    return f"/public/videos/{video_id}/master.m3u8"