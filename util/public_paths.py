import os
from util.response import Response
from util.request import Request

class PublicPaths:
    MIME = {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".jpg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".ico": "image/x-icon"
    }

    # check if path is valid
    def safe_public_path(requestPath: str):
        if not requestPath.startswith("/public"):
            return None
        relativePath = requestPath[7:]   # remove /public
        if relativePath.startswith("/"):
            relativePath = relativePath[1:]
        # remove unnecessary stuff from the path
        relativePath = os.path.normpath(relativePath) 
        # check path doesn't start from root even though its supposed to be relative
        if (relativePath.startswith("..")) or (os.path.isabs(relativePath)):  
            return None
        return os.path.join("public", relativePath)
    
    def send_404_response(handler):
        res = Response().set_status(404, "Not Found")
        res.text("content not found")
        handler.request.sendall(res.to_data())

    def serve_from_public(request: Request, handler):
        path = PublicPaths.safe_public_path(request.path)
        if (path is None) or (not os.path.isfile(path)):
            PublicPaths.send_404_response(handler)
            return
        x = os.path.splitext(path.lower())
        fileExtension = x[1]
        mimeType = PublicPaths.MIME.get(fileExtension)
        if mimeType is None:
            PublicPaths.send_404_response(handler)
            return

        with open(path, "rb") as f:  #rb to read as bytes
            data = f.read()

        res = Response()
        res.headers({"Content-Type": mimeType})
        res.bytes(data)
        handler.request.sendall(res.to_data())

    def render_page(request: Request, handler, page_filename: str):
        layout_path = os.path.join("public", "layout", "layout.html")
        page_path = os.path.join("public", page_filename)
        if not os.path.isfile(page_path):
            PublicPaths.send_404_response(handler)
            return

        with open(layout_path, "r", encoding="utf-8") as f:
            layout = f.read()
        with open(page_path, "r", encoding="utf-8") as f:
            page = f.read()

        html_page = layout.replace("{{content}}", page)

        res = Response()
        res.headers({"Content-Type": "text/html; charset=utf-8"})
        res.text(html_page)
        handler.request.sendall(res.to_data())