"""A small local web server for the wireframe editor (standard library only).

    python server.py [FILE] [--port 8000]

FILE (default wireframe.json) is the wireframe. It is the same file the
command line uses, so the browser and headless tools always agree.

API (JSON unless noted):
    GET  /api/wireframe        the wireframe
    PUT  /api/wireframe        replace it (an AI's proposal); 400 + errors if invalid
    POST /api/op               apply one edit, e.g. {"op": "add_block", ...}
    GET  /api/check            {"findings": [...], "has_errors": bool}
    GET  /api/spec?mode=coder  spec sheet as Markdown ("image" for image generators)
    GET  /api/guide            the AI authoring guide as Markdown
    GET  /api/play?state=ID    what a user sees on a screen (default: the first)
    POST /api/play             {"state", "event", "choice"?} -> where the event leads; read-only
    GET  /api/resolved         "stateId/blockId" -> the block's full resolved style
Everything else is a static file from static/.

Safety: this tool has no login, so it only listens on 127.0.0.1, only accepts
local Host headers, only accepts writes sent as application/json, and only
serves files from inside static/.
"""

import argparse
import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from wireframe import checks, model, ops, play, spec, styles

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BODY = 1_000_000  # bytes; a wireframe is a few KB, so this is generous

# mimetypes reads the Windows registry, which can map .js to the wrong type.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}
LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def make_server(path, host="127.0.0.1", port=8000, static_dir=None, quiet=False):
    """Build (but do not start) a server for the wireframe file at `path`."""
    static_root = os.path.realpath(static_dir or os.path.join(HERE, "static"))
    lock = threading.Lock()  # one edit at a time: load -> change -> save

    class Handler(BaseHTTPRequestHandler):
        server_version = "WireframeServer"

        # ---- helpers ----
        def log_message(self, fmt, *args):
            if not quiet:
                super().log_message(fmt, *args)

        def send_bytes(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, payload):
            self.send_bytes(status, json.dumps(payload).encode("utf-8"), "application/json")

        def send_errors(self, status, errors):
            self.send_json(status, {"errors": errors})

        def host_is_local(self):
            host = self.headers.get("Host", "")
            return host.rsplit(":", 1)[0] in LOCAL_HOSTS if ":" in host else host in LOCAL_HOSTS

        def drain_body(self):
            """Read and discard an unwanted request body (up to a cap) before replying.
            Replying while the client is still sending makes Windows reset the connection."""
            try:
                remaining = min(int(self.headers.get("Content-Length", "0")), 5 * MAX_BODY)
            except ValueError:
                remaining = 0
            while remaining > 0:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
            self.close_connection = True

        def read_json_body(self):
            """Return the parsed body, or None after sending an error response."""
            ctype = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if ctype != "application/json":
                self.drain_body()
                self.send_errors(415, ["send the body with Content-Type: application/json"])
                return None
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self.send_errors(400, ["Content-Length is required"])
                return None
            if length > MAX_BODY:
                # Read and throw away the body (up to a cap) before replying. If we
                # answer and close while the client is still sending, the operating
                # system resets the connection and the client never sees the 413.
                remaining = min(length, 5 * MAX_BODY)
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                self.close_connection = True
                self.send_errors(413, [f"body too large (limit {MAX_BODY} bytes)"])
                return None
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.send_errors(400, [f"the body is not valid JSON ({exc})"])
                return None

        # ---- routing ----
        def dispatch(self, method):
            if not self.host_is_local():
                self.drain_body()
                return self.send_errors(403, ["requests must use a local Host name"])
            url = urlsplit(self.path)
            route = (method, url.path)
            try:
                if route == ("GET", "/api/wireframe"):
                    with lock:
                        return self.send_json(200, model.load_or_create(path))
                if route == ("PUT", "/api/wireframe"):
                    body = self.read_json_body()
                    if body is None:
                        return
                    with lock:
                        model.save(body, path)
                    return self.send_json(200, body)
                if route == ("POST", "/api/op"):
                    body = self.read_json_body()
                    if body is None:
                        return
                    with lock:
                        new = ops.apply_op(model.load_or_create(path), body)
                        model.save(new, path)
                    return self.send_json(200, new)
                if route == ("GET", "/api/check"):
                    with lock:
                        findings = checks.check(model.load_or_create(path))
                    return self.send_json(200, {"findings": findings,
                                                "has_errors": checks.has_errors(findings)})
                if route == ("GET", "/api/spec"):
                    mode = parse_qs(url.query).get("mode", ["coder"])[0]
                    with lock:
                        text = spec.export_spec(model.load_or_create(path), mode)
                    return self.send_bytes(200, text.encode("utf-8"), "text/markdown; charset=utf-8")
                if route == ("GET", "/api/play"):
                    with lock:
                        doc = model.load_or_create(path)
                    state_id = parse_qs(url.query).get("state", [doc["initial"]])[0]
                    return self.send_json(200, play.screen(doc, state_id))
                if route == ("POST", "/api/play"):
                    body = self.read_json_body()
                    if body is None:
                        return
                    if not isinstance(body, dict) or not isinstance(body.get("state"), str) \
                            or not isinstance(body.get("event"), str) \
                            or not isinstance(body.get("choice", ""), str):
                        return self.send_errors(400, ["send {\"state\": text, \"event\": text, "
                                                      "\"choice\": text (optional)}"])
                    with lock:
                        doc = model.load_or_create(path)
                    return self.send_json(200, play.step(doc, body["state"], body["event"],
                                                         body.get("choice") or None))
                if route == ("GET", "/api/resolved"):
                    with lock:
                        doc = model.load_or_create(path)
                    return self.send_json(200, {f"{st['id']}/{b['id']}": styles.resolve_style(doc, b)
                                                for st in doc["states"] for b in st["blocks"]})
                if route == ("GET", "/api/guide"):
                    return self.send_bytes(200, spec.authoring_guide().encode("utf-8"),
                                           "text/markdown; charset=utf-8")
            except model.WireframeError as exc:
                return self.send_errors(400, exc.errors)

            if url.path.startswith("/api/"):
                self.drain_body()      # we are about to refuse; do not leave a body unread
                known = {"/api/wireframe", "/api/op", "/api/check", "/api/spec", "/api/guide",
                         "/api/play", "/api/resolved"}
                if url.path in known:
                    return self.send_errors(405, [f"{method} is not allowed on {url.path}"])
                return self.send_errors(404, [f"no such endpoint {url.path}"])
            if method == "GET":
                return self.send_static(url.path)
            self.drain_body()
            return self.send_errors(405, [f"{method} is not allowed here"])

        def send_static(self, url_path):
            if url_path == "/":
                name = "index.html"
            elif url_path.startswith("/static/"):
                name = unquote(url_path[len("/static/"):])
            else:
                return self.send_errors(404, ["not found"])
            # Resolve symlinks and '..' first, THEN require the result to still
            # be inside the static folder. Checking the text of the URL is not enough.
            full = os.path.realpath(os.path.join(static_root, name))
            inside = os.path.commonpath([static_root, full]) == static_root if \
                os.path.splitdrive(full)[0] == os.path.splitdrive(static_root)[0] else False
            if not inside or not os.path.isfile(full):
                return self.send_errors(404, ["not found"])
            ext = os.path.splitext(full)[1].lower()
            ctype = CONTENT_TYPES.get(ext) or mimetypes.guess_type(full)[0] or "application/octet-stream"
            with open(full, "rb") as f:
                self.send_bytes(200, f.read(), ctype)

        def do_GET(self):
            self.dispatch("GET")

        def do_PUT(self):
            self.dispatch("PUT")

        def do_POST(self):
            self.dispatch("POST")

        def do_DELETE(self):
            self.dispatch("DELETE")

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd


def main():
    parser = argparse.ArgumentParser(description="Local wireframe editor server")
    parser.add_argument("file", nargs="?", default="wireframe.json", help="wireframe JSON file")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    httpd = make_server(args.file, port=args.port)
    print(f"Editing {os.path.abspath(args.file)}")
    print(f"Open http://localhost:{args.port}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
