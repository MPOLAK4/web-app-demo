"""R12: start, stop and status for a background server.

These tests start REAL server processes (a few hundred milliseconds each) because
the thing under test is exactly "a separate process that can be started and stopped".
Each test uses its own temporary folder and state file, port 0 (any free port), and
stops what it started, even when it fails.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

from wireframe import cli, model, serverctl
from wireframe.example import example_wireframe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class ServerCtlTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.wire = os.path.join(self.dir.name, "w.json")
        self.state = os.path.join(self.dir.name, "state.json")
        model.save(example_wireframe(), self.wire)
        self.addCleanup(self.cleanup_server)

    def cleanup_server(self):
        serverctl.stop(self.state)

    def start(self, *extra):
        return run("start", self.wire, "--state-file", self.state, *extra)

    def test_R12_start_runs_in_the_background_and_prints_a_working_url(self):
        """R12(e): the command returns while the server keeps answering."""
        code, out, err = self.start()
        self.assertEqual(code, 0, err)
        url = [w for w in out.split() if w.startswith("http://")][0]
        self.assertTrue(serverctl.ping(url), "the printed URL does not answer /api/ping")

    def test_R12_start_writes_the_state_file(self):
        """R12(d): pid, port, url and file are recorded."""
        self.start()
        with open(self.state, encoding="utf-8") as f:
            info = json.load(f)
        self.assertEqual(set(info), {"pid", "port", "url", "file"})
        self.assertEqual(info["file"], os.path.abspath(self.wire))
        self.assertEqual(info["url"], f"http://127.0.0.1:{info['port']}")
        self.assertGreater(info["port"], 0)      # port 0 was replaced by the real port

    def test_R12_start_twice_does_not_start_a_second_server(self):
        """R12(e): the second call reports the same URL."""
        _, out1, _ = self.start()
        _, out2, _ = self.start()
        with open(self.state, encoding="utf-8") as f:
            url = json.load(f)["url"]
        self.assertIn(url, out1)
        self.assertIn(url, out2)
        self.assertIn("already running", out2)

    def test_R12_stop_shuts_the_server_down_and_removes_the_state_file(self):
        """R12(f)."""
        self.start()
        url = serverctl.status(self.state)
        code, out, err = run("stop", "--state-file", self.state)
        self.assertEqual(code, 0, err)
        self.assertFalse(os.path.exists(self.state))
        self.assertFalse(serverctl.ping(url), "the server still answers after stop")

    def test_R12_stop_with_nothing_running_is_not_an_error(self):
        """R12(f)."""
        code, out, _ = run("stop", "--state-file", self.state)
        self.assertEqual(code, 0)
        self.assertIn("not running", out)

    def test_R12_a_stale_state_file_is_handled_by_stop_status_and_start(self):
        """R12(e), R12(f), R12(g): the file names a server that is gone."""
        stale = {"pid": 1, "port": 1, "url": "http://127.0.0.1:1", "file": self.wire}
        for command in ("stop", "status"):
            with open(self.state, "w", encoding="utf-8") as f:
                json.dump(stale, f)
            code, out, _ = run(command, "--state-file", self.state)
            self.assertEqual(code, 0, command)
            self.assertIn("not running", out, command)
            self.assertFalse(os.path.exists(self.state), command)
        with open(self.state, "w", encoding="utf-8") as f:
            json.dump(stale, f)
        code, out, err = self.start()
        self.assertEqual(code, 0, err)
        self.assertNotIn("http://127.0.0.1:1\n", out)

    def test_R12_a_garbled_state_file_does_not_crash(self):
        """R12(f): treated like a stale file."""
        with open(self.state, "w", encoding="utf-8") as f:
            f.write("not json")
        code, out, _ = run("status", "--state-file", self.state)
        self.assertEqual(code, 0)
        self.assertIn("not running", out)

    def test_R12_status_reports_the_url_while_running(self):
        """R12(g)."""
        self.start()
        code, out, _ = run("status", "--state-file", self.state)
        self.assertEqual(code, 0)
        self.assertIn(serverctl.status(self.state), out)

    def test_R12_server_edits_the_file_it_was_started_with(self):
        """R12(d): the background server serves that wireframe, not some other one."""
        self.start()
        url = serverctl.status(self.state)
        import urllib.request
        with urllib.request.urlopen(url + "/api/wireframe", timeout=5) as resp:
            self.assertEqual(json.load(resp)["name"], example_wireframe()["name"])

    def test_R12_background_server_shuts_itself_down_when_idle(self):
        """R12(a), R12(e): --idle-timeout reaches the real process, and the state file goes."""
        self.start("--idle-timeout", "1")
        deadline = time.monotonic() + 10
        while os.path.exists(self.state) and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertFalse(os.path.exists(self.state), "the server did not remove its state file when idle")

    def test_R12_bad_idle_timeout_is_refused_before_starting(self):
        """R12(a)."""
        code, _, err = self.start("--idle-timeout", "0")
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(self.state))

    def test_R12_start_reports_a_server_that_cannot_start(self):
        """R12(e): a missing/invalid wireframe is reported, not left hanging."""
        with open(self.wire, "w", encoding="utf-8") as f:
            f.write("{not json")
        t0 = time.monotonic()
        code, _, err = self.start()
        self.assertEqual(code, 1)
        self.assertLess(time.monotonic() - t0, 15)

    def test_R12_foreground_server_writes_and_removes_its_state_file(self):
        """R12(d): `python server.py --state-file` records itself, and Ctrl+C-style exit cleans up."""
        proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "server.py"), self.wire, "--port", "0",
                                 "--idle-timeout", "1", "--state-file", self.state],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(proc.kill)
        deadline = time.monotonic() + 10
        while not os.path.exists(self.state) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(os.path.exists(self.state))
        proc.wait(timeout=10)       # idle timeout ends it
        self.assertFalse(os.path.exists(self.state))


if __name__ == "__main__":
    unittest.main()
