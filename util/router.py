from util.request import Request
from util.response import Response

class Router:

    def __init__(self):
        self.routes = []

    def add_route(self, method, path, action, exact_path=False):
        self.routes.append((method, path, action, exact_path))

    def route_request(self, request: Request, handler):
        req_method = request.method
        req_path = request.path

        for method, path, action, exact_path in self.routes:
            if method != req_method:
                continue

            if exact_path:
                if req_path != path:
                    continue
            else:
                if not req_path.startswith(path):
                    continue

            action(request, handler)
            return
        
        res = Response().set_status(404, "Not Found")
        res.text("content Not Found")  
        handler.request.sendall(res.to_data())

            
