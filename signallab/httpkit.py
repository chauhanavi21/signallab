"""Small loopback-only JSON/static HTTP boundary used by this standalone demo."""
import json
import mimetypes
import traceback
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

@dataclass
class Reply:
    body: object
    status: int = 200
    headers: dict = field(default_factory=dict)

class Fault(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)

class Handler(BaseHTTPRequestHandler):
    server_version = "LocalLab/1.0"
    def log_message(self, fmt, *args):
        pass
    def do_GET(self): self.handle_request("GET")
    def do_POST(self): self.handle_request("POST")
    def handle_request(self, method):
        try:
            target = urlsplit(self.path)
            query = parse_qs(target.query, keep_blank_values=True)
            if any(len(v) != 1 for v in query.values()):
                raise Fault(400, "Repeated query parameters are not supported.")
            if method == "GET" and target.path in {"/", "/app.js", "/studio.js", "/style.css"}:
                name = "index.html" if target.path == "/" else target.path[1:]
                path = self.server.web / name
                content = path.read_bytes()
                kind = "text/html" if name.endswith(".html") else "text/javascript" if name.endswith(".js") else "text/css"
                self.respond(content, 200, {}, kind + "; charset=utf-8")
                return
            if not target.path.startswith("/api/"):
                raise Fault(404, "Route not found.")
            if method == "POST":
                try: size = int(self.headers.get("Content-Length", "0"))
                except ValueError: raise Fault(400, "Invalid content length.") from None
                if not 0 < size <= 1000000:
                    raise Fault(413, "JSON request must be between 1 byte and 1 MB.")
                # Drain bounded bodies before rejecting their metadata. Closing
                # a Windows socket with unread input can discard the response.
                raw = self.rfile.read(size)
                allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
                if self.headers.get("Origin") and self.headers["Origin"] not in allowed:
                    raise Fault(403, "Cross-origin writes are not allowed.")
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise Fault(415, "Use application/json.")
                def reject_constant(value): raise ValueError("Non-finite JSON values are not allowed.")
                try: body = json.loads(raw, parse_constant=reject_constant)
                except (ValueError, UnicodeError): raise Fault(400, "Invalid JSON; non-finite numbers are not supported.") from None
                if not isinstance(body, dict): raise Fault(400, "Expected a JSON object.")
                result = self.post_api(target.path, body)
            else:
                result = self.get_api(target.path, {k:v[0] for k,v in query.items()})
            reply = result if isinstance(result, Reply) else Reply(result)
            self.respond(json.dumps(reply.body, allow_nan=False, ensure_ascii=False).encode("utf-8"), reply.status, reply.headers)
        except Fault as exc:
            self.respond(json.dumps({"error": exc.message}).encode(), exc.status, {})
        except (ValueError, KeyError) as exc:
            self.respond(json.dumps({"error": str(exc)}).encode(), 400, {})
        except Exception:
            traceback.print_exc()
            self.respond(b'{"error":"Unexpected server error."}', 500, {})
    def respond(self, content, status, headers, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        for key, value in headers.items(): self.send_header(key, value)
        try:
            self.end_headers()
            self.wfile.write(content)
        except ConnectionError:
            pass  # A closed browser tab no longer has a response destination.

class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, port, handler, root, store=None):
        self.web, self.store = Path(root) / "web", store
        super().__init__(("127.0.0.1", port), handler)

def serve(server):
    print(f"Ready: http://127.0.0.1:{server.server_port}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
