"""A small local web server for the wireframe editor (standard library only).

    python server.py [FILE] [--port 8000] [--idle-timeout 300] [--state-file PATH]

FILE (default wireframe.json) is the wireframe. It is the same file the
command line uses, so the browser and headless tools always agree.

API (JSON unless noted):
    GET  /api/wireframe        the wireframe
    PUT  /api/wireframe        replace it (an AI's proposal); 400 + errors if invalid
    POST /api/op               apply one edit, e.g. {"op": "add_block", ...}
    GET  /api/check            {"findings": [...], "has_errors": bool}
    GET  /api/spec?mode=coder  spec sheet as Markdown ("image" for image generators; data=live)
    GET  /api/guide            the AI authoring guide as Markdown
    GET  /api/play?state=ID    what a user sees on a screen (default: the first)
    POST /api/play             {"state", "event", "choice"?} -> where the event leads; read-only
    GET  /api/resolved         "stateId/blockId" -> the block's full resolved style
    GET  /api/lines?state=ID&data=debug|live   "blockId" -> the text lines the block shows
    GET  /api/render?state=ID | after=EVENT...&format=svg|html&data=&download=1
                               a picture file of a screen (read-only)
    GET  /api/ping             {"ok": true, "idle_timeout": N}; any request counts as a ping
    POST /api/shutdown         stop the server after replying (R12)
    GET  /api/viewer?download=1  the clickable viewer .html for this wireframe (R13)
    GET  /api/examples           the example library: name, title, summary (R14)
    GET  /api/example?name=N     one example with its expected output (R14); read-only
Everything else is a static file from static/.

Lifetime (R12): if no request arrives for --idle-timeout seconds (default 300, five
minutes) the server stops itself. `python -m wireframe start|stop|status` run it in
the background and end it again.

Safety: this tool has no login, so it only listens on 127.0.0.1, only accepts
local Host headers, only accepts writes sent as application/json, and only
serves files from inside static/.
"""

import argparse
import json
import mimetypes
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from wireframe import checks, data, examples, model, ops, play, render, serverctl, spec, styles, viewer
from wireframe.serverctl import DEFAULT_IDLE_TIMEOUT  # seconds: five minutes (R12); defined once, there

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


def make_server(path, host="127.0.0.1", port=8000, static_dir=None, quiet=False,
                idle_timeout=DEFAULT_IDLE_TIMEOUT):
    """Build (but do not start) a server for the wireframe file at `path`.

    `idle_timeout` is how many seconds without any request `run()` waits before
    it stops the server (R12). Only `run()` enforces it."""
    if isinstance(idle_timeout, bool) or not isinstance(idle_timeout, (int, float)) or idle_timeout <= 0:
        raise ValueError("idle_timeout must be a number of seconds greater than 0")
    static_root = os.path.realpath(static_dir or os.path.join(HERE, "static"))
    lock = threading.Lock()  # one edit at a time: load -> change -> save

    class Handler(BaseHTTPRequestHandler):
        server_version = "WireframeServer"

        # ---- helpers ----
        def log_message(self, fmt, *args):
            if not quiet:
                super().log_message(fmt, *args)

        def send_bytes(self, status, body, content_type, extra_headers=()):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            for name, value in extra_headers:
                self.send_header(name, value)
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
                # Read and throw away the body before replying, or the operating system
                # may reset the connection and the client never sees the 413.
                self.drain_body()
                self.send_errors(413, [f"body too large (limit {MAX_BODY} bytes)"])
                return None
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.send_errors(400, [f"the body is not valid JSON ({exc})"])
                return None

        # ---- routing ----
        def dispatch(self, method):
            httpd.last_request = time.monotonic()   # any request, even a refused one, is a ping
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
                    query = parse_qs(url.query)
                    mode = query.get("mode", ["coder"])[0]
                    with lock:
                        text = spec.export_spec(model.load_or_create(path), mode,
                                                query.get("data", ["debug"])[0])
                    return self.send_bytes(200, text.encode("utf-8"), "text/markdown; charset=utf-8")
                if route == ("GET", "/api/play"):
                    with lock:
                        doc = model.load_or_create(path)
                    query = parse_qs(url.query)
                    mode = query.get("data", ["debug"])[0]
                    data.check_mode(mode)
                    scr = play.screen(doc, query.get("state", [doc["initial"]])[0])
                    for b in scr["blocks"]:
                        b["lines"] = render.content_lines(doc, b, mode)
                    return self.send_json(200, scr)
                if route == ("GET", "/api/lines"):
                    with lock:
                        doc = model.load_or_create(path)
                    query = parse_qs(url.query)
                    mode = query.get("data", ["debug"])[0]
                    data.check_mode(mode)
                    wanted = query.get("state", [doc["initial"]])[0]
                    for st in doc["states"]:
                        if st["id"] == wanted:
                            return self.send_json(200, {b["id"]: render.content_lines(doc, b, mode)
                                                        for b in st["blocks"]})
                    raise model.WireframeError(f"no state with id '{wanted}'")
                if route == ("GET", "/api/render"):
                    with lock:
                        doc = model.load_or_create(path)
                    query = parse_qs(url.query)
                    if "state" in query and "after" in query:
                        raise model.WireframeError("use state or after, not both")
                    state_id = query["state"][0] if "state" in query else play.follow(doc, query.get("after", []))
                    fmt = query.get("format", ["svg"])[0]
                    text = render.render_screen(doc, state_id, fmt, query.get("data", ["debug"])[0])
                    # No script, no network: if a label ever held markup, the browser still would not run it.
                    headers = [("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; "
                                                           "img-src data:"),
                               ("X-Content-Type-Options", "nosniff")]
                    if query.get("download", [""])[0] == "1":
                        stem = "".join(c if c.isalnum() or c in "-_" else "-" for c in f"{doc['name']}-{state_id}")
                        headers.append(("Content-Disposition", f'attachment; filename="{stem}.{fmt}"'))
                    ctype = "image/svg+xml" if fmt == "svg" else "text/html; charset=utf-8"
                    return self.send_bytes(200, text.encode("utf-8"), ctype, headers)
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
                if route == ("GET", "/api/ping"):
                    return self.send_json(200, {"ok": True, "idle_timeout": httpd.idle_timeout})
                if route == ("POST", "/api/shutdown"):
                    body = self.read_json_body()
                    if body is None:
                        return
                    self.send_json(200, {"ok": True})
                    # shutdown() waits for serve_forever() to return, so it must not run on
                    # the thread that is answering this request.
                    threading.Thread(target=httpd.shutdown, daemon=True).start()
                    return
                if route == ("GET", "/api/viewer"):
                    with lock:
                        doc = model.load_or_create(path)
                    headers = [("X-Content-Type-Options", "nosniff")]
                    if parse_qs(url.query).get("download", [""])[0] == "1":
                        stem = "".join(c if c.isalnum() or c in "-_" else "-" for c in f"{doc['name']}-viewer")
                        headers.append(("Content-Disposition", f'attachment; filename="{stem}.html"'))
                    return self.send_bytes(200, viewer.build_viewer(doc).encode("utf-8"),
                                           "text/html; charset=utf-8", headers)
                if route == ("GET", "/api/examples"):
                    return self.send_json(200, examples.list_examples())
                if route == ("GET", "/api/example"):
                    # Read-only: never touches the lock or the server's wireframe file.
                    name = parse_qs(url.query).get("name", [""])[0]
                    doc = examples.get_example(name)       # unknown or empty: WireframeError -> 400
                    io = examples.example_io(name)
                    meta = [e for e in examples.list_examples() if e["name"] == name][0]
                    findings = checks.check(doc)
                    return self.send_json(200, {**meta, "wireframe": doc, "coder": io["coder"],
                                                "image": io["image"], "svg": io["svg"],
                                                "check": {"findings": findings,
                                                          "has_errors": checks.has_errors(findings)}})
                if route == ("GET", "/api/guide"):
                    return self.send_bytes(200, spec.authoring_guide().encode("utf-8"),
                                           "text/markdown; charset=utf-8")
            except model.WireframeError as exc:
                return self.send_errors(400, exc.errors)

            if url.path.startswith("/api/"):
                self.drain_body()      # we are about to refuse; do not leave a body unread
                known = {"/api/wireframe", "/api/op", "/api/check", "/api/spec", "/api/guide",
                         "/api/play", "/api/resolved", "/api/lines", "/api/render", "/api/ping",
                         "/api/shutdown", "/api/viewer", "/api/examples", "/api/example"}
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
    httpd.idle_timeout = idle_timeout
    httpd.last_request = time.monotonic()
    return httpd


def run(httpd):
    """Serve until Ctrl+C, a /api/shutdown request, or `idle_timeout` seconds with no
    request at all. Always closes the socket before returning (R12)."""
    done = threading.Event()

    def watch():
        # Check often enough to stop close to the deadline, but never busy-loop.
        interval = min(1.0, httpd.idle_timeout / 4)
        while not done.wait(interval):
            if time.monotonic() - httpd.last_request >= httpd.idle_timeout:
                httpd.shutdown()      # makes serve_forever() below return
                return

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        httpd.serve_forever(poll_interval=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        done.set()
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="Local wireframe editor server")
    parser.add_argument("file", nargs="?", default="wireframe.json", help="wireframe JSON file")
    parser.add_argument("--port", type=int, default=8000, help="0 means any free port")
    parser.add_argument("--idle-timeout", type=float, default=DEFAULT_IDLE_TIMEOUT, metavar="SECONDS",
                        help="stop after this many seconds without a request (default 300)")
    parser.add_argument("--state-file", help="write {pid, port, url, file} here while running (used by `start`)")
    args = parser.parse_args()
    if args.idle_timeout <= 0:
        parser.error("--idle-timeout must be greater than 0")
    if os.path.exists(args.file):
        try:
            model.load(args.file)      # refuse to start on a broken file, so `start` can report it
        except model.WireframeError as exc:
            for line in exc.errors:
                print(line, file=sys.stderr)
            sys.exit(1)
    httpd = make_server(args.file, port=args.port, idle_timeout=args.idle_timeout)
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}"
    if args.state_file:
        serverctl.write_state(args.state_file, {"pid": os.getpid(), "port": port, "url": url,
                                                "file": os.path.abspath(args.file)})
    print(f"Editing {os.path.abspath(args.file)}")
    print(f"Open {url}  (Ctrl+C or `python -m wireframe stop` to stop; "
          f"stops itself after {args.idle_timeout:g}s with no requests)", flush=True)
    try:
        run(httpd)
    finally:
        if args.state_file:
            serverctl.remove_state(args.state_file)
        print("Stopped.")


if __name__ == "__main__":
    main()
