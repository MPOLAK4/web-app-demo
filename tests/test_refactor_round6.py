"""R16: the Round 6 cleanup. Behaviour must not change (the older tests prove that);
these tests check the structure the cleanup promises, so it cannot quietly drift back."""
import os
import unittest

import server
from wireframe import cli, data, serverctl
from test_server import ServerTestCase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def source_of(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class RouteTableTests(ServerTestCase):
    def test_R16_c_the_route_table_covers_every_documented_route(self):
        """R16(c): every path in the module docstring is in the table, and the reverse."""
        paths = {path for _, path in server.ROUTES}
        for path in paths:
            self.assertIn(path, server.__doc__, f"{path} is not documented")
        self.assertGreaterEqual(len(paths), 14)

    def test_R16_c_a_known_path_with_another_method_is_405(self):
        """R16(c): the 405 answer comes from the table, for every route and method."""
        for method, path in server.ROUTES:
            for other in ("GET", "POST", "PUT"):
                if (other, path) in server.ROUTES:
                    continue
                status, _, _ = self.call(other, path, {} if other != "GET" else None)
                self.assertEqual(status, 405, f"{other} {path}")

    def test_R16_c_an_unknown_api_path_is_404(self):
        """R16(c)."""
        for method in ("GET", "POST"):
            status, _, _ = self.call(method, "/api/nope", {} if method == "POST" else None)
            self.assertEqual(status, 404)

    def test_R16_c_there_is_no_second_hand_written_list_of_paths(self):
        """R16(c): the old `known = {...}` set is gone."""
        self.assertNotIn("known = {", source_of("server.py"))


class SingleDefinitionTests(unittest.TestCase):
    def test_R16_b_one_body_discarding_loop(self):
        """R16(b): the 'read and throw away' loop exists once (in drain_body)."""
        self.assertEqual(source_of("server.py").count("5 * MAX_BODY"), 1)

    def test_R16_d_download_names_come_from_one_helper(self):
        """R16(d): same names as before."""
        self.assertEqual(server.download_name("My App", "b", "html"), "My-App-b.html")
        self.assertEqual(server.download_name("My App", "viewer", "html"), "My-App-viewer.html")
        self.assertEqual(server.download_name("a/b", "s1", "svg"), "a-b-s1.svg")
        self.assertEqual(source_of("server.py").count('"-_"'), 1)

    def test_R16_e_the_idle_timeout_default_is_defined_once(self):
        """R16(e)."""
        self.assertEqual(serverctl.DEFAULT_IDLE_TIMEOUT, 300)
        self.assertEqual(server.DEFAULT_IDLE_TIMEOUT, serverctl.DEFAULT_IDLE_TIMEOUT)
        self.assertNotIn("DEFAULT_IDLE_TIMEOUT =", source_of("server.py"))

    def test_R16_f_data_does_not_re_export_is_data_key(self):
        """R16(f)."""
        self.assertFalse(hasattr(data, "is_data_key"))

    def test_R16_f_the_cli_writes_files_through_one_helper(self):
        """R16(f)."""
        self.assertEqual(source_of("wireframe", "cli.py").count('newline="' + chr(92) + 'n"'), 1)
        self.assertTrue(callable(cli._write_or_print))


if __name__ == "__main__":
    unittest.main()
