"""The HTTP API (R1, R2, R3, R4) and the server's safety rules (R1(f)).

Each test starts a real server on a free port in a background thread, with its
own temporary wireframe file and static folder, and talks to it over HTTP.
"""
import http.client
import json
import os
import tempfile
import threading
import unittest

import server
from wireframe import model
from wireframe.example import example_wireframe
from helpers import block, doc, state


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "w.json")
        self.static = os.path.join(self.dir.name, "static")
        os.mkdir(self.static)
        with open(os.path.join(self.static, "index.html"), "w", encoding="utf-8") as f:
            f.write("<h1>hi</h1>")
        with open(os.path.join(self.static, "app.css"), "w", encoding="utf-8") as f:
            f.write("body{}")
        with open(os.path.join(self.static, "app.js"), "w", encoding="utf-8") as f:
            f.write("1;")
        with open(os.path.join(self.dir.name, "secret.txt"), "w", encoding="utf-8") as f:
            f.write("TOP SECRET")
        self.httpd = server.make_server(self.path, port=0, static_dir=self.static, quiet=True)
        self.port = self.httpd.server_address[1]
        # poll_interval is how often the loop checks for shutdown (default 0.5 s,
        # which would add half a second to every test).
        thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.01},
                                  daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def call(self, method, url, body=None, headers=None, raw=None):
        """Return (status, headers, body-bytes). `body` is JSON-encoded unless `raw` is given."""
        headers = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, url, body=data, headers=headers)
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def jcall(self, method, url, body=None, **kw):
        status, headers, data = self.call(method, url, body, **kw)
        return status, json.loads(data)

    def stored(self):
        return model.load(self.path)


class WireframeApiTests(ServerTestCase):
    def test_R1_server_listens_on_localhost_only(self):
        """R1(f)."""
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")

    def test_R1_get_creates_a_blank_wireframe_when_the_file_is_missing(self):
        """R1(a)."""
        status, d = self.jcall("GET", "/api/wireframe")
        self.assertEqual(status, 200)
        self.assertEqual(d, model.new_wireframe())
        self.assertTrue(os.path.exists(self.path))

    def test_R1_the_api_and_the_file_are_the_same_wireframe(self):
        """R1: a headless edit to the file (CLI/script) shows up in the API."""
        model.save(example_wireframe(), self.path)
        status, d = self.jcall("GET", "/api/wireframe")
        self.assertEqual(d, example_wireframe())

    def test_R1_op_edits_and_persists(self):
        """R1(c): the message the browser sends changes the stored file."""
        model.save(example_wireframe(), self.path)
        status, d = self.jcall("POST", "/api/op",
                               {"op": "update_block", "state": "cart", "id": "total", "x": 600})
        self.assertEqual(status, 200)
        self.assertEqual(d["states"][0]["blocks"][2]["x"], 600)
        self.assertEqual(self.stored(), d)

    def test_R1_invalid_op_returns_400_with_errors_and_changes_nothing(self):
        """R1(b)/(c)."""
        model.save(example_wireframe(), self.path)
        status, d = self.jcall("POST", "/api/op",
                               {"op": "update_block", "state": "cart", "id": "total", "w": 0})
        self.assertEqual(status, 400)
        self.assertTrue(d["errors"])
        self.assertEqual(self.stored(), example_wireframe())

    def test_R1_unknown_op_returns_400(self):
        status, d = self.jcall("POST", "/api/op", {"op": "explode"})
        self.assertEqual(status, 400)
        self.assertIn("explode", d["errors"][0])

    def test_R3_put_replaces_the_wireframe_with_a_valid_proposal(self):
        """R3(d): an AI-written wireframe is accepted and stored."""
        status, d = self.jcall("PUT", "/api/wireframe", example_wireframe())
        self.assertEqual(status, 200)
        self.assertEqual(self.stored(), example_wireframe())
        self.assertEqual(self.jcall("GET", "/api/wireframe")[1], example_wireframe())

    def test_R3_put_rejects_an_invalid_proposal_and_keeps_the_stored_file(self):
        """R3(d): HTTP 400, readable errors, file unchanged."""
        model.save(doc([state("keep")]), self.path)
        bad = example_wireframe()
        bad["states"][1]["blocks"][0]["w"] = -5
        status, d = self.jcall("PUT", "/api/wireframe", bad)
        self.assertEqual(status, 400)
        self.assertTrue(any("states[1].blocks[0].w" in e for e in d["errors"]), d)
        self.assertEqual(self.stored(), doc([state("keep")]))

    def test_R3_put_with_malformed_json_returns_400(self):
        status, d = self.jcall("PUT", "/api/wireframe", raw=b"{nope",
                               headers={"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertIn("JSON", d["errors"][0])

    def test_R1_a_request_body_that_is_too_large_is_refused(self):
        big = b" " * (server.MAX_BODY + 1)
        status, d = self.jcall("PUT", "/api/wireframe", raw=big,
                               headers={"Content-Type": "application/json"})
        self.assertEqual(status, 413)

    def test_R1_writes_must_be_application_json(self):
        """R1(f): blocks cross-site form posts (CSRF) from other web pages."""
        model.save(doc([state("keep")]), self.path)
        body = json.dumps(example_wireframe()).encode()
        for ctype in ("text/plain", "application/x-www-form-urlencoded", None):
            headers = {"Content-Type": ctype} if ctype else {}
            status, _, _ = self.call("PUT", "/api/wireframe", raw=body, headers=headers)
            self.assertEqual(status, 415, ctype)
        self.assertEqual(self.stored(), doc([state("keep")]))

    def test_R1_requests_with_a_foreign_host_header_are_refused(self):
        """R1(f): blocks DNS-rebinding, where a web page reaches localhost under another name."""
        status, _, _ = self.call("GET", "/api/wireframe", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)
        status, _, _ = self.call("GET", "/api/wireframe", headers={"Host": "localhost:1234"})
        self.assertEqual(status, 200)

    def test_R1_unknown_paths_404_and_wrong_methods_405(self):
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)
        self.assertEqual(self.call("DELETE", "/api/wireframe")[0], 405)
        self.assertEqual(self.call("POST", "/api/check", {})[0], 405)


class CheckSpecGuideApiTests(ServerTestCase):
    def test_R4_check_reports_findings_for_the_stored_wireframe(self):
        """R4(k)."""
        model.save(example_wireframe(), self.path)
        status, d = self.jcall("GET", "/api/check")
        self.assertEqual((status, d["findings"], d["has_errors"]), (200, [], False))

    def test_R4_check_reports_errors_after_an_edit_breaks_the_flow(self):
        """R4(k): the editor refreshes this after every edit."""
        model.save(example_wireframe(), self.path)
        self.jcall("POST", "/api/op", {"op": "delete_block", "state": "cart", "id": "checkout"})
        status, d = self.jcall("GET", "/api/check")
        self.assertTrue(d["has_errors"])
        self.assertIn("no-trigger", {f["code"] for f in d["findings"]})

    def test_R5_check_reports_duplicate_information(self):
        """R5(b) through the API."""
        model.save(doc([state("a", [block("b1", y=0, label="Total", info=("cart.total",)),
                                    block("b2", y=100, label="Sum", info=("cart.total",))], final=True)]),
                   self.path)
        d = self.jcall("GET", "/api/check")[1]
        self.assertIn("duplicate-info", {f["code"] for f in d["findings"]})

    def test_R2_spec_endpoint_serves_both_modes_as_markdown(self):
        """R2(e)."""
        model.save(example_wireframe(), self.path)
        status, headers, body = self.call("GET", "/api/spec?mode=coder")
        self.assertEqual(status, 200)
        self.assertIn("text/markdown", headers["Content-Type"])
        self.assertIn(b"for a coding AI", body)
        status, _, body = self.call("GET", "/api/spec?mode=image")
        self.assertEqual(status, 200)
        self.assertIn(b"Image brief", body)

    def test_R2_spec_defaults_to_coder_mode_and_rejects_unknown_modes(self):
        model.save(example_wireframe(), self.path)
        self.assertIn(b"for a coding AI", self.call("GET", "/api/spec")[2])
        self.assertEqual(self.call("GET", "/api/spec?mode=poem")[0], 400)

    def test_R2_non_ascii_labels_survive_the_round_trip(self):
        """Labels may contain any language; the response must be UTF-8."""
        model.save(doc([state("a", [block("b1", label="Zahlung überprüfen ✓")], final=True)]),
                   self.path)
        body = self.call("GET", "/api/spec?mode=image")[2]
        self.assertIn("Zahlung überprüfen ✓", body.decode("utf-8"))

    def test_R3_guide_endpoint(self):
        """R3(e)."""
        status, headers, body = self.call("GET", "/api/guide")
        self.assertEqual(status, 200)
        self.assertIn(b"How to write a wireframe", body)

    def test_R3_the_whole_ai_loop_over_http(self):
        """R3: read the guide, submit a proposal, get it checked, all via the API."""
        guide = self.call("GET", "/api/guide")[2].decode()
        example = json.loads(guide.split("```json\n")[1].split("\n```")[0])
        self.assertEqual(self.jcall("PUT", "/api/wireframe", example)[0], 200)
        self.assertFalse(self.jcall("GET", "/api/check")[1]["has_errors"])


class StaticFileTests(ServerTestCase):
    def test_R1_root_serves_index_html(self):
        """R1(e)."""
        status, headers, body = self.call("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertEqual(body, b"<h1>hi</h1>")

    def test_R1_static_files_have_the_right_content_types(self):
        """Browsers refuse scripts served with the wrong type."""
        self.assertIn("text/css", self.call("GET", "/static/app.css")[1]["Content-Type"])
        self.assertIn("javascript", self.call("GET", "/static/app.js")[1]["Content-Type"])

    def test_R1_missing_static_file_is_404(self):
        self.assertEqual(self.call("GET", "/static/nope.js")[0], 404)

    def test_R1_paths_cannot_escape_the_static_folder(self):
        """R1(f): ../secret.txt sits next to the static folder and must stay private."""
        for url in ("/static/../secret.txt", "/static/%2e%2e/secret.txt", "/static/..%2fsecret.txt",
                    "/static/..%5csecret.txt", "/static//../secret.txt", "/../secret.txt"):
            status, _, body = self.call("GET", url)
            self.assertNotEqual(status, 200, url)
            self.assertNotIn(b"TOP SECRET", body, url)


if __name__ == "__main__":
    unittest.main()
