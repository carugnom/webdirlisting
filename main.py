import os
import socket

class DirListing:
    def __init__(self, url_path):
        self.dir_path = self.__url_path_to_dir_path(url_path)
        if not os.path.exists(self.dir_path):
            raise FileNotFoundError

        self.is_root_dir = (url_path == '')
        self.parent_dir = os.path.dirname(self.dir_path) if not self.is_root_dir else ''

    def __url_path_to_dir_path(self, url_path):
        # url_path: /path/to/resource/
        # output: <getcwd>/path/to/resource/    > using platform's path separator
        if url_path:
            url_path += os.path.sep
        dir_path = os.path.dirname(os.path.join(os.getcwd(), url_path))
        return dir_path
    
    def __dir_path_to_url_path(self, dir_path):
        # dir_path: <getcwd>/path/to/resource/  ... using platform's path separator
        # output: /path/to/resource
        url_path = ''

        # remove base directory prefix
        prefix = os.getcwd()

        if dir_path.startswith(prefix):
            url_path = dir_path[len(prefix):].replace(os.sep, '/')
        
        if not url_path:
            url_path = '/'
        
        return url_path

    def get_hyperlinked_dir_listing(self):
        """Get directory listing with hyperlinked directories."""

        html = "<html><body>"

        if not self.is_root_dir:
            parent_url = self.__dir_path_to_url_path(self.parent_dir)
            html += f'<a href="{parent_url}">[parent directory]</a><br>'

        files = [f for f in os.listdir(self.dir_path)]

        for f in files:
            # bypass hidden files
            if f.startswith('.'):
                continue
            
            if os.path.isdir(os.path.join(self.dir_path, f)):
                subdir_path = os.path.join(self.dir_path, f)
                url_path_sub = self.__dir_path_to_url_path(subdir_path)
                f = f'<a href="{url_path_sub}">{f}/</a>'

            f += '<br>'
            html += f

        html += "</body></html>"
        return html


class TCPServer:
    """Base server class for handling TCP connections. 
    The HTTP server will inherit from this class.
    """
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(5)

        print("Listening at", s.getsockname())

        while True:
            conn, addr = s.accept()
            print("Connected by", addr)
            
            data = conn.recv(1024) 
            response = self.handle_request(data)
            conn.sendall(response)
            conn.close()

    def handle_request(self, data):
        """Override this for handling incoming data."""
        return data


class HTTPServer(TCPServer):
    """HTTP server class."""

    headers = {
        'Server': 'CrudeServer',
        'Content-Type': 'text/html',
    }

    status_codes = {
        200: 'OK',
        404: 'Not Found',
        501: 'Not Implemented',
    }

    def handle_request(self, data):
        """Handles incoming requests"""

        request = HTTPRequest(data)

        try:
            handler = getattr(self, 'handle_%s' % request.method)
        except AttributeError:
            handler = self.HTTP_501_handler

        response = handler(request)
        return response

    def response_line(self, status_code):
        """Returns response line (as bytes)"""

        reason = self.status_codes[status_code]
        response_line = 'HTTP/1.1 %s %s\r\n' % (status_code, reason)

        return response_line.encode() # convert from str to bytes

    def response_headers(self, extra_headers=None):
        """Returns headers (as bytes)."""

        headers_copy = self.headers.copy() # make a local copy of headers

        if extra_headers:
            headers_copy.update(extra_headers)

        headers = ''

        for h in headers_copy:
            headers += '%s: %s\r\n' % (h, headers_copy[h])

        return headers.encode() # convert str to bytes

    def handle_GET(self, request):
        """Handler for GET HTTP method"""

        url_path = request.uri.strip('/')

        try:
            dl = DirListing(url_path)

            response_line = self.response_line(200)
            response_headers = self.response_headers({'Content-Type': 'text/html'})
            response_body = dl.get_hyperlinked_dir_listing().encode()

        except FileNotFoundError:
            response_line = self.response_line(404)
            response_headers = self.response_headers()
            response_body = b'<h1>404 Not Found</h1>'

        blank_line = b'\r\n'
        response = b''.join([response_line, response_headers, blank_line, response_body])

        return response

    def HTTP_501_handler(self, request):
        """Returns 501 HTTP response if the requested method hasn't been implemented."""

        response_line = self.response_line(status_code=501)
        response_headers = self.response_headers()
        blank_line = b'\r\n'
        response_body = b'<h1>501 Not Implemented</h1>'

        return b"".join([response_line, response_headers, blank_line, response_body])


class HTTPRequest:
    """Parser for HTTP requests.""" 

    def __init__(self, data):
        self.method = None
        self.uri = None
        self.http_version = '1.1'

        self.parse(data)

    def parse(self, data):
        lines = data.split(b'\r\n')
        request_line = lines[0]
        words = request_line.split(b' ')
        self.method = words[0].decode()

        # needed because some browsers don't send uri for homepage
        if len(words) > 1:
            self.uri = words[1].decode() # call decode to convert bytes to string

        # needed because some browsers don't send http version
        if len(words) > 2:
            self.http_version = words[2]


if __name__ == '__main__':
    server = HTTPServer()
    server.start()
