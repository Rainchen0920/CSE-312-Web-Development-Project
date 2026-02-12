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
            if key.strip().lower() == 'set-cookie':
                name_and_value = headers[key].split('=', 1)
                name = name_and_value[0].strip()
                value = name_and_value[1].strip()
                self.cookiesDict[name] = value
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
        self.body = json.dumps(data).encode()
        self.headers["content-type"] = "application/json"
        self.headers["content-length"] = str(len(self.body))
        return self

    def to_data(self):    
        if 'content-type' not in self.headersDict:   
            self.headersDict['content-type'] = 'text/plain; charset=utf-8'
        self.headersDict["content-length"] = str(len(self.body))   

        responseLine = b'HTTP/1.1 ' + self.status + b' ' + self.message + b'\r\n'

        headersBytes = b'' 
        for key in self.headersDict.keys(): # need to fix, everything else looks good
            if key == 'set-cookie':
                cookieBytes = b''
                for cookiekey in self.headersDict['set-cookie'].keys():
                    cookie = cookiekey.encode() + b'=' + (self.headersDict['set-cookie'][cookiekey]).encode() + b'; '
                    cookieBytes = cookieBytes + cookie
                cookieBytes = cookieBytes[:-2]
                headersBytes = headersBytes + 'Set-Cookie: ' + cookieBytes + b'\r\n'
            else:
                header = key.encode() + b': ' + (self.headersDict[key]).encode() + b'\r\n'
                headersBytes = headersBytes + header

        self.fullResponse = responseLine + headersBytes + b'\r\n\r\n' + self.body
        return self.fullResponse


def test1():
    res = Response()
    res.text("hello")
    expected = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 5\r\n\r\nhello'
    actual = res.to_data()


if __name__ == '__main__':
    test1()
