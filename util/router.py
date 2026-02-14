import util.request as request
import util.response as response

class Router:

    def __init__(self):
        self.routes = []

    def add_route(self, method, path, action, exact_path=False):
        self.routes.append((method, path, action, exact_path))

    def route_request(self, request, handler):
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
        
        error_response = (b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 13\r\n\r\n404 Not Found")
        handler.request.sendall(error_response)

            
