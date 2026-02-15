class Request:

    def __init__(self, request: bytes):
        # TODO: parse the bytes of the request and populate the following instance variables

        parts = request.split(b'\r\n\r\n', 1) 
        a = (parts[0]).split(b'\r\n')     
        request_line = (a[0]).split()
        headers = a[1:]

        if len(parts) > 1:
            self.body = parts[1].lstrip(b"\r\n")
        else: 
            self.body = b''
        self.method = request_line[0].decode()
        self.path = request_line[1].decode()  
        self.http_version = request_line[2].decode()

        self.headers = {}
        for header in headers:
            if (not header.strip()) or (b":" not in header):
                continue
            x = header.split(b':', 1)    
            key = x[0].decode().strip()
            value = x[1].decode().strip()  
            parts = []
            for x in key.lower().split('-'):
                parts.append(x.capitalize())
            capitalizedKey = '-'.join(parts)
            self.headers[capitalizedKey] = value   

        self.cookies = {}
        if "Cookie" in self.headers:
            cookies = self.headers["Cookie"].split(';')
            for header in cookies:
                y = header.split('=', 1)
                if len(y) != 2:
                    continue
                key = y[0].lower().strip()
                value = y[1].strip()  
                self.cookies[key] = value



def test1():
    request = Request(b'GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\n\r\n')
    assert request.method == "GET"
    assert request.path == "/"
    assert request.http_version == "HTTP/1.1"
    assert "Host" in request.headers
    assert request.headers["Host"] == "localhost:8080"  # note: The leading space in the header value must be removed
    assert "Connection" in request.headers
    assert request.headers["Connection"] == "keep-alive"
    assert request.body == b""  # There is no body for this request.
    #print("test 1 good")
    # When parsing POST requests, the body must be in bytes, not str

    # This is the start of a simple way (ie. no external libraries) to test your code.
    # It's recommended that you complete this test and add others, including at least one
    # test using a POST request. Also, ensure that the types of all values are correct

def test2():  # test case on a lot of cookies
    request = Request(b"GET /big HTTP/1.1\r\nHost: example.com\r\nCookie: k0=v0; k1=v1; k2=v2; k3=v3; k4=v4; k5=v5; k6=v6; k7=v7; k8=v8; " 
                      + b"k9=v9; k10=v10; k11=v11; k12=v12; k13=v13; k14=v14; k15=v15; k16=v16; k17=v17; k18=v18; k19=v19; k20=v20; "
                      + b"k21=v21; k22=v22; k23=v23; k24=v24; k25=v25; k26=v26; k27=v27; k28=v28; k29=v29; k30=v30\r\n\r\n")
    assert request.method == "GET"
    assert request.path == "/big"
    assert request.headers["Host"] == "example.com"
    assert request.cookies["k0"] == "v0"
    assert request.cookies["k13"] == "v13"
    assert request.cookies["k25"] == "v25"
    assert request.cookies["k30"] == "v30"
    assert request.body == b''
    #print("test 2 good")

def test3():  # test case on json post request
    request = Request(b'POST /test HTTP/1.1\r\nHost: example.com\r\nContent-Type: application/json\r\nContent-Length: 38\r\n\r\n' 
                      + b'{"username":"random","peabrain":"123"}')
    assert request.method == "POST"
    assert request.path == "/test"
    assert request.http_version == "HTTP/1.1"
    assert "Host" in request.headers
    assert request.headers["Host"] == "example.com"  
    assert "Content-Type" in request.headers
    assert request.headers["Content-Type"] == "application/json" 
    assert request.body == b'{"username":"random","peabrain":"123"}'  
    assert "Content-Length" in request.headers 
    assert int(request.headers["Content-Length"]) == len(request.body)
    #print("test 3 good")

def test4():  # test case on headers with weird casing
    request = Request(b'GET /testing HTTP/1.1\r\nhOsT: example.com\r\npJO-seASOn-3: titanscurse\r\ncOnTeNt-TyPe: text/plain; charset=utf-8'
                      + b'\r\n\r\n')
    assert request.method == "GET"
    assert request.path == "/testing"
    assert request.http_version == "HTTP/1.1"
    assert "Host" in request.headers
    assert request.headers["Host"] == "example.com"  
    assert "Pjo-Season-3" in request.headers
    assert request.headers["Pjo-Season-3"] == "titanscurse"  
    assert "Content-Type" in request.headers
    assert request.headers["Content-Type"] == "text/plain; charset=utf-8" 
    assert request.body == b''
    #print("test 4 good")

def test5():  # test case on header value with a lot of colons
    request = Request(b'GET / HTTP/1.1\r\nRandom: value:with:many:colons:inside\r\n\r\n')
    assert request.method == "GET"
    assert request.path == "/"
    assert request.http_version == "HTTP/1.1"
    assert "Random" in request.headers
    assert request.headers["Random"] == "value:with:many:colons:inside"  
    assert request.body == b''
    #print("test 5 good")

def test6():  # case of extra CRLF at the end
    req = Request(b"GET / HTTP/1.1\r\nHost: localhost:8080\r\n\r\n\r\n")
    assert "Host" in req.headers
    assert req.headers["Host"] == "localhost:8080"
    assert req.body == b''
    #print("test 6 good")

def test7():  # case of cookie value with = in it
    req = Request(b"GET /cookie HTTP/1.1\r\nHost: example.com\r\nCookie: lotofequal=abc=123==; theme=dark=; id=67\r\n\r\n")
    assert req.cookies["lotofequal"] == "abc=123=="
    assert req.cookies["theme"] == "dark="
    assert req.cookies["id"] == "67"
    #print("test 7 good")

def test8():  # case of extra spaces around cookie names and values
    req = Request(b"GET /cookie HTTP/1.1\r\nHost: example.com\r\nCookie: a=1;  b=2 ; c = three;    d=four\r\n\r\n")
    assert req.cookies["a"] == "1"
    assert req.cookies["b"] == "2"
    assert req.cookies["c"] == "three"
    assert req.cookies["d"] == "four"
    #print("test 8 good") 

if __name__ == '__main__':
    test1()
    test2()
    test3()
    test4()
    test5()
    test6()
    test7()
    test8()
