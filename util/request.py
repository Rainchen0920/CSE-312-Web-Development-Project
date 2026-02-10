class Request:

    def __init__(self, request: bytes):
        # TODO: parse the bytes of the request and populate the following instance variables

        parts = request.split(b'\r\n\r\n')  # split request line and headers apart from body
        a = (parts[0]).split(b'\r\n')       # split apart request line and headers
        request_line = (a[0]).split(' ')
        headers = a[1:]
            

        self.body = parts[1]
        self.method = request_line[0].decode()
        self.path = request_line[1].decode()
        self.http_version = request_line[2][5:].decode()   # cut off at 5 for 'HTTP/'

        self.headers = {}
        for header in headers:
            x = header.split(b': ')    ## ask in office hour if i can assume there's a space after colon
            key = x[0].decode().lower()   # turn into lower case for case insensitive
            value = x[1].decode()
            self.headers[key] = value   ## ask if i have to remove trailing spaces 
                                        ## from names and values in headers dictionary

        self.cookies = {}
        if "cookie" in self.headers:
            cookie_headers = self.headers["cookie"].split('; ')
            for header in cookie_headers:
                y = header.split(': ')
                key = y[0].lower().strip()
                value = y[1].strip()  
                self.cookies[key] = value



def test1():
    request = Request(b'GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\n\r\n')
    assert request.method == "GET"
    assert "Host" in request.headers
    assert request.headers["Host"] == "localhost:8080"  # note: The leading space in the header value must be removed
    assert request.body == b""  # There is no body for this request.
    # When parsing POST requests, the body must be in bytes, not str

    # This is the start of a simple way (ie. no external libraries) to test your code.
    # It's recommended that you complete this test and add others, including at least one
    # test using a POST request. Also, ensure that the types of all values are correct


if __name__ == '__main__':
    test1()
