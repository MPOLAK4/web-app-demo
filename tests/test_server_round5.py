"""R14(h): the read-only example routes."""
import json
import os
import unittest

from wireframe import checks, examples
from test_server import ServerTestCase


class ExampleRouteTests(ServerTestCase):
    def test_R14_examples_route_lists_the_library(self):
        """R14(h)."""
        status, body = self.jcall("GET", "/api/examples")
        self.assertEqual(status, 200)
        self.assertEqual(body, examples.list_examples())

    def test_R14_example_route_returns_input_and_expected_output(self):
        """R14(h): wireframe, coder, image, check and svg for one example."""
        status, body = self.jcall("GET", "/api/example?name=flawed")
        self.assertEqual(status, 200)
        io = examples.example_io("flawed")
        meta = [e for e in examples.list_examples() if e["name"] == "flawed"][0]
        self.assertEqual({k: body[k] for k in ("name", "title", "summary")}, meta)
        self.assertEqual(body["wireframe"], examples.get_example("flawed"))
        self.assertEqual(body["coder"], io["coder"])
        self.assertEqual(body["image"], io["image"])
        self.assertEqual(body["svg"], io["svg"])
        findings = checks.check(examples.get_example("flawed"))
        self.assertEqual(body["check"], {"findings": findings, "has_errors": checks.has_errors(findings)})
        self.assertTrue(body["check"]["has_errors"])

    def test_R14_missing_or_unknown_name_is_http_400(self):
        """R14(h)."""
        for url in ("/api/example", "/api/example?name=", "/api/example?name=nope"):
            status, body = self.jcall("GET", url)
            self.assertEqual(status, 400, url)
            self.assertTrue(body["errors"], url)

    def test_R14_example_routes_never_touch_the_servers_wireframe_file(self):
        """R14(h): looking at an example must not replace the user's work."""
        self.call("GET", "/api/examples")
        self.call("GET", "/api/example?name=login")
        self.assertFalse(os.path.exists(self.path))

    def test_R14_wrong_method_is_405_not_404(self):
        """R14(h): the routes are in the `known` set (CLAUDE.md rule)."""
        for url in ("/api/examples", "/api/example?name=login"):
            status, _, _ = self.call("POST", url, {})
            self.assertEqual(status, 405, url)


if __name__ == "__main__":
    unittest.main()
