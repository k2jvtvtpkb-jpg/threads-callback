from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests, json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        code = params.get("code", [None])[0]
        r = requests.post("https://graph.threads.net/oauth/access_token", data={"client_id":"1198812552100358","client_secret":"e9c5beae8518a559957d424490b8e009","code":code,"grant_type":"authorization_code","redirect_uri":"https://threads-callback-k2jvtvtpkb-jpg.vercel.app/callback"})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(r.json()).encode())
