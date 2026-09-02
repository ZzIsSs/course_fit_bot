import os, sys, json
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.interactions import verify_signature, handle_interaction

DATABASE_URL = os.environ.get('DATABASE_URL')


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        sig = self.headers.get('X-Signature-Ed25519', '')
        ts = self.headers.get('X-Signature-Timestamp', '')

        if not verify_signature(sig, ts, body):
            self.send_response(401)
            self.end_headers()
            return

        interaction = json.loads(body)
        result = {"type": 1} if interaction.get('type') == 1 else handle_interaction(interaction, DATABASE_URL)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))
