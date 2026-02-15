import os
from util.response import Response

class PublicPaths:
    MIME = {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".jpg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".ico": "image/x-icon"
    }

    def safe_public_path(file_path:str):  #check for valid file path from "public" directory
        if not file_path.startswith("/public"):
            return "error"
        file_path = file_path.lstrip('/')
        return file_path

    def serve_public(request, handler):
        path_on_disk = safe_public_path(request.path)
        if (path_on_disk is None) or (not os.path.isfile(path_on_disk)):
            handler.request.sendall(Response().set_status(404, "Not Found").text("Not Found").to_data())
            return

        _, ext = os.path.splitext(path_on_disk.lower())
        mime = MIME.get(ext, "application/octet-stream")

        with open(path_on_disk, "rb") as f:
            data = f.read()

        res = Response()
        res.headers({"Content-Type": mime})
        res.bytes(data)
        handler.request.sendall(res.to_data())

    def render_page(page_filename: str):
        def action(req, handler):
            layout_path = os.path.join("public", "layout", "layout.html")
            page_path = os.path.join("public", page_filename)

            if (not os.path.isfile(layout_path)) or (not os.path.isfile(page_path)):
                handler.request.sendall(
                    Response().set_status(404, "Not Found").text("Not Found").to_data()
                )
                return

            # UTF-8 so emojis work
            with open(layout_path, "r", encoding="utf-8") as f:
                layout = f.read()
            with open(page_path, "r", encoding="utf-8") as f:
                page = f.read()

            full_html = layout.replace("{{content}}", page)

            res = Response()
            res.headers({"Content-Type": "text/html; charset=utf-8"})
            res.text(full_html)
            handler.request.sendall(res.to_data())
        return action

