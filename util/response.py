import json

class Response:
    def __init__(self):
        self.status = b'200'
        self.message = b'OK'
        self.body = b''
        self.headersDict = {}
        self.cookiesDict = {}
        self.fullResponse = b''

    def set_status(self, code:int, text:str):
        self.status = str(code).encode()
        self.message = text.encode()
        return self

    def headers(self, headers:dict): 
        new_headers = {}
        for key in headers.keys(): 
            if key.strip().lower() == "set-cookie":
                cookies = headers[key].strip()
                if "=" in cookies:
                    name = cookies.split("=", 1)[0]
                    rest = cookies.split("=", 1)[1]
                    self.cookiesDict[name.strip()] = rest.strip()
            else:
                new_headers[key.strip().lower()] = headers[key].strip()
        self.headersDict.update(new_headers)
        return self

    # cookies: each key-value pair is a cookie
    def cookies(self, cookies:dict): 
        self.cookiesDict.update(cookies)
        return self

    def bytes(self, data:bytes):
        self.body = self.body + data
        return self

    def text(self, data:str):
        dataInBytes = data.encode()
        self.body = self.body + dataInBytes
        return self

    def json(self, data):
        self.body = json.dumps(data, separators=(",", ":")).encode()
        self.headersDict["content-type"] = "application/json"
        self.headersDict["content-length"] = str(len(self.body))
        return self

    def to_data(self):    
        if 'content-type' not in self.headersDict:   
            self.headersDict['content-type'] = 'text/plain; charset=utf-8'
        self.headersDict["content-length"] = str(len(self.body))   

        responseLine = b'HTTP/1.1 ' + self.status + b' ' + self.message + b'\r\n'

        headersBytes = b'' 
        for key in self.headersDict.keys(): 
            parts = []
            for part in key.split('-'):
                parts.append(part.capitalize())
            capitalizedKey = '-'.join(parts)
            header = capitalizedKey.encode() + b': ' + (self.headersDict[key]).encode() + b'\r\n'
            headersBytes = headersBytes + header
        
        cookieBytes = b''
        for key in self.cookiesDict.keys():
            cookie = b'Set-Cookie: ' + key.encode() + b'=' + (self.cookiesDict[key]).encode() + b'\r\n'
            cookieBytes = cookieBytes + cookie

        self.fullResponse = responseLine + headersBytes + cookieBytes + b'\r\n' + self.body
        return self.fullResponse


def test1():
    res = Response()
    res.text("hello")
    actual = res.to_data()
    expected = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 5\r\n\r\nhello'
    assert actual == expected

    # testing .json(data)
    res2 = Response()
    res2.json([1,2,3,4])
    actual2 = res2.to_data()
    expected2 = b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 9\r\n\r\n[1,2,3,4]'
    #print(actual2)
    assert actual2 == expected2

    # testing the cookies function
    res3 = Response()
    res3.text("ok")
    res3.cookies({"session": "abc123; Path=/; HttpOnly; Secure"})
    actual3 = res3.to_data()
    expected3 = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 2\r\nSet-Cookie: session=abc123; Path=/; HttpOnly; Secure\r\n\r\nok'
    #print(actual3)
    assert actual3 == expected3

    # testing case of multiple cookies
    res4 = Response()
    res4.bytes(b'ok\r\n\r\n')
    res4.cookies({"session": "abc123; Path=/; HttpOnly; Secure", "theme": "dark; Max-Age=3600; SameSite=Lax", "mood": "happy; Path=/; HttpOnly"})
    actual4 = res4.to_data()
    expected4 = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 6\r\nSet-Cookie: session=abc123; Path=/; HttpOnly; Secure\r\nSet-Cookie: theme=dark; Max-Age=3600; SameSite=Lax\r\nSet-Cookie: mood=happy; Path=/; HttpOnly\r\n\r\nok\r\n\r\n'
    #print(actual4)
    assert actual4 == expected4

    # testing set-status function
    res5 = Response()
    res5.set_status(404,"Not Found")
    actual5 = res5.to_data()
    expected5 = b'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 0\r\n\r\n'
    #print(actual5)
    assert actual5 == expected5



if __name__ == '__main__':
    test1()
