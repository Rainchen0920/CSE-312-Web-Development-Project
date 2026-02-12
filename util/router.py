import util.request
import util.response

class Router:

    def __init__(self):
        # routes are identified by paths and each path correspond to a function that takes a request object and handler
        # like a dictionary with paths as keys and its values are a bunch functions
        pass

    def add_route(self, method, path, action, exact_path=False):
        pass

    def route_request(self, request, handler):
        pass
