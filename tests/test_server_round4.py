"""R12: server lifetime. Ping, shutdown request, and the idle timeout.

The idle tests use a very short timeout (a fraction of a second) instead of the
real 300 seconds, so the suite stays fast. They check behaviour, not the number.
"""
import http.client
import json
import threading
import time
import unittest

import server
from test_server import ServerTestCase


def get(port, path="/api/ping"):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        resp.read()
        return resp.status
    finally:
        conn.close()


class PingAndShutdownTests(ServerTestCase):
    def test_R12_ping_answers_and_reports_the_timeout(self):
        """R12(b)."""
        status, body = self.jcall("GET", "/api/ping")
        self.assertEqual(status, 200)
        self.assertEqual(body["ok"], True)
        self.assertEqual(body["idle_timeout"], 300)

    def test_R12_ping_changes_nothing(self):
        """R12(b): no wireframe file is created or written by a ping."""
        self.call("GET", "/api/ping")
        import os
        self.assertFalse(os.path.exists(self.path))

    def test_R12_shutdown_replies_then_the_server_stops(self):
        """R12(c): the reply arrives, and afterwards the port is closed."""
        # ServerTestCase runs serve_forever in a thread; shutdown() must make it return.
        status, body = self.jcall("POST", "/api/shutdown", {})
        self.assertEqual((status, body), (200, {"ok": True}))
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                get(self.port)
            except OSError:
                return          # connection refused: the server is gone
            time.sleep(0.05)
        self.fail("the server still answered 3 seconds after /api/shutdown")

    def test_R12_shutdown_needs_a_json_body_and_a_local_host(self):
        """R12(c): same rules as every other write; a refused call leaves the server running."""
        status, _, _ = self.call("POST", "/api/shutdown", raw=b"x", headers={"Content-Type": "text/plain"})
        self.assertEqual(status, 415)
        status, _, _ = self.call("POST", "/api/shutdown", {}, headers={"Host": "evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.jcall("GET", "/api/ping")[0], 200)

    def test_R12_shutdown_is_post_only(self):
        """R12(c): a GET (for example a link or an image tag) cannot stop the server."""
        status, _, _ = self.call("GET", "/api/shutdown")
        self.assertEqual(status, 405)
        self.assertEqual(self.jcall("GET", "/api/ping")[0], 200)


class IdleTimeoutTests(unittest.TestCase):
    def make(self, timeout):
        import os
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        static = os.path.join(tmp.name, "static")
        os.mkdir(static)
        httpd = server.make_server(os.path.join(tmp.name, "w.json"), port=0, static_dir=static,
                                   quiet=True, idle_timeout=timeout)
        thread = threading.Thread(target=server.run, args=(httpd,), daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        return httpd, thread

    def test_R12_default_idle_timeout_is_five_minutes(self):
        """R12(a): the number the requirement asks for."""
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            httpd = server.make_server(os.path.join(tmp, "w.json"), port=0, quiet=True)
            self.addCleanup(httpd.server_close)
            self.assertEqual(httpd.idle_timeout, 300)

    def test_R12_idle_timeout_must_be_positive(self):
        """R12(a): zero, negative or non-number values are refused."""
        for bad in (0, -1, "5", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                server.make_server("w.json", port=0, quiet=True, idle_timeout=bad)

    def test_R12_server_stops_itself_when_nothing_pings_it(self):
        """R12(a)."""
        httpd, thread = self.make(0.3)
        thread.join(5)
        self.assertFalse(thread.is_alive(), "server was still running long after its idle timeout")

    def test_R12_any_request_restarts_the_clock(self):
        """R12(a): keep asking for 3x the timeout and it must stay up; stop, and it goes."""
        httpd, thread = self.make(0.5)
        port = httpd.server_address[1]
        end = time.monotonic() + 1.5
        while time.monotonic() < end:
            self.assertEqual(get(port, "/api/guide"), 200)     # not /api/ping: any request counts
            time.sleep(0.1)
        self.assertTrue(thread.is_alive())
        thread.join(5)
        self.assertFalse(thread.is_alive())

    def test_R12_a_refused_request_still_counts_as_a_ping(self):
        """R12(a): even a 404 shows that someone is there."""
        httpd, thread = self.make(0.5)
        port = httpd.server_address[1]
        end = time.monotonic() + 1.2
        while time.monotonic() < end:
            self.assertEqual(get(port, "/api/nothing-here"), 404)
            time.sleep(0.1)
        self.assertTrue(thread.is_alive())
        thread.join(5)

    def test_R12_run_closes_the_socket(self):
        """R12(a): after it stops, the port can no longer be connected to."""
        httpd, thread = self.make(0.2)
        port = httpd.server_address[1]
        thread.join(5)
        with self.assertRaises(OSError):
            get(port)


if __name__ == "__main__":
    unittest.main()
