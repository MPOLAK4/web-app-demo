import contextlib
import io
import json
import os
import tempfile
import unittest

from wireframe import cli, model
from wireframe.example import example_wireframe
from helpers import block, doc, state


def run(*argv):
    """Run the command line in-process; return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exc:  # argparse exits on bad usage
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "w.json")

    def write(self, d):
        model.save(d, self.path)

    def read(self):
        with open(self.path, encoding="utf-8") as f:
            return f.read()

    def test_R1_new_creates_a_valid_blank_file(self):
        """R1(a)."""
        code, out, err = run("new", self.path, "--name", "Mine")
        self.assertEqual(code, 0, err)
        d = model.load(self.path)
        self.assertEqual(d["name"], "Mine")

    def test_R1_new_with_example_creates_the_worked_example(self):
        code, _, err = run("new", self.path, "--example")
        self.assertEqual(code, 0, err)
        self.assertEqual(model.load(self.path), example_wireframe())

    def test_R1_new_refuses_to_overwrite_an_existing_file(self):
        """Safety: never destroy someone's wireframe by accident."""
        self.write(example_wireframe())
        before = self.read()
        code, _, err = run("new", self.path)
        self.assertEqual(code, 1)
        self.assertIn("exists", err)
        self.assertEqual(self.read(), before)

    def test_R1_op_edits_the_file_headlessly(self):
        """R1(c): the same op the browser sends works from the command line."""
        self.write(example_wireframe())
        op = json.dumps({"op": "update_block", "state": "cart", "id": "total", "x": 600})
        code, _, err = run("op", self.path, op)
        self.assertEqual(code, 0, err)
        total = next(b for b in model.load(self.path)["states"][0]["blocks"] if b["id"] == "total")
        self.assertEqual(total["x"], 600)

    def test_R1_a_bad_op_exits_1_and_leaves_the_file_alone(self):
        """R1(b)/(c)."""
        self.write(example_wireframe())
        before = self.read()
        code, _, err = run("op", self.path, json.dumps({"op": "update_block", "state": "cart", "id": "total", "w": 0}))
        self.assertEqual(code, 1)
        self.assertIn("w", err)
        self.assertEqual(self.read(), before)

    def test_R1_op_with_malformed_json_exits_1(self):
        self.write(example_wireframe())
        code, _, err = run("op", self.path, "{not json")
        self.assertEqual(code, 1)
        self.assertIn("JSON", err)

    def test_R3_validate_accepts_a_good_file(self):
        """R3(e)."""
        self.write(example_wireframe())
        code, out, _ = run("validate", self.path)
        self.assertEqual(code, 0)
        self.assertIn("valid", out.lower())

    def test_R3_validate_lists_every_error_for_a_bad_file(self):
        """R3(c)/(e): errors go to stderr, one per line, with their paths."""
        bad = example_wireframe()
        bad["states"][0]["blocks"][0]["w"] = 0
        bad["name"] = 3
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(bad, f)
        code, _, err = run("validate", self.path)
        self.assertEqual(code, 1)
        self.assertIn("states[0].blocks[0].w", err)
        self.assertIn("name", err)

    def test_R3_validate_reports_a_missing_file_without_a_traceback(self):
        code, _, err = run("validate", os.path.join(self.dir.name, "nope.json"))
        self.assertEqual(code, 1)
        self.assertIn("cannot read", err)

    def test_R4_check_exits_0_when_there_are_no_errors(self):
        """R4(k)."""
        self.write(example_wireframe())
        code, out, _ = run("check", self.path)
        self.assertEqual(code, 0)
        self.assertIn("No problems", out)

    def test_R4_check_exits_1_and_prints_findings_when_there_are_errors(self):
        """R4(k)."""
        d = example_wireframe()
        d["states"][0]["blocks"] = [b for b in d["states"][0]["blocks"] if b["id"] != "checkout"]
        self.write(d)
        code, out, _ = run("check", self.path)
        self.assertEqual(code, 1)
        self.assertIn("no-trigger", out)

    def test_R4_warnings_alone_do_not_fail_the_check(self):
        """R4(k): only errors set the exit code."""
        d = doc([state("a", [block("b1", label="Mystery", info=())], final=True)])
        self.write(d)
        code, out, _ = run("check", self.path)
        self.assertEqual(code, 0)
        self.assertIn("missing-info", out)

    def test_R2_export_prints_the_spec_in_each_mode(self):
        """R2(e)."""
        self.write(example_wireframe())
        code, coder, _ = run("export", self.path, "--mode", "coder")
        self.assertEqual(code, 0)
        self.assertIn("for a coding AI", coder)
        code, image, _ = run("export", self.path, "--mode", "image")
        self.assertEqual(code, 0)
        self.assertIn("Image brief", image)

    def test_R2_export_defaults_to_coder_mode(self):
        self.write(example_wireframe())
        self.assertIn("for a coding AI", run("export", self.path)[1])

    def test_R2_export_rejects_an_unknown_mode(self):
        self.write(example_wireframe())
        code, _, _ = run("export", self.path, "--mode", "poem")
        self.assertNotEqual(code, 0)

    def test_R3_guide_prints_the_authoring_guide(self):
        """R3(e)."""
        code, out, _ = run("guide")
        self.assertEqual(code, 0)
        self.assertIn("How to write a wireframe", out)


class CliRenderTests(unittest.TestCase):
    """R10(g), R11(e): the render command and export --data."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "w.json")
        run("new", self.path, "--example")

    def read(self):
        with open(self.path, encoding="utf-8") as f:
            return f.read()

    def test_R10_render_prints_svg_of_the_initial_screen_by_default(self):
        """R10(g)."""
        code, out, err = run("render", self.path)
        self.assertEqual(code, 0, err)
        self.assertTrue(out.startswith("<svg"))
        self.assertIn("Your cart", out)

    def test_R10_render_state_and_after_pick_the_screen(self):
        """R10(g): --state names a screen; --after follows events like walk."""
        _, by_state, _ = run("render", self.path, "--state", "payment")
        _, by_events, _ = run("render", self.path, "--after", "checkout")
        self.assertIn("Card number", by_state)
        self.assertEqual(by_state, by_events)

    def test_R10_render_html_and_data_mode(self):
        """R10(g), R11(e)."""
        _, debug, _ = run("render", self.path, "--format", "html")
        self.assertIn("<!DOCTYPE html>", debug)
        self.assertIn("{{cart.total}}", debug)
        _, live, _ = run("render", self.path, "--format", "html", "--data", "live")
        self.assertIn("Total: $42.00", live)

    def test_R10_render_out_writes_a_file_instead_of_printing(self):
        """R10(g)."""
        target = os.path.join(self.dir.name, "pic.svg")
        code, out, err = run("render", self.path, "--out", target)
        self.assertEqual(code, 0, err)
        self.assertNotIn("<svg", out)
        with open(target, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("<svg"))

    def test_R10_render_problems_exit_1_and_write_nothing(self):
        """R10(g): both selectors, an unknown screen, a stuck event."""
        target = os.path.join(self.dir.name, "pic.svg")
        for argv in (("--state", "cart", "--after", "checkout"), ("--state", "zzz"), ("--after", "nope")):
            with self.subTest(argv=argv):
                code, out, err = run("render", self.path, *argv, "--out", target)
                self.assertEqual(code, 1)
                self.assertTrue(err)
                self.assertFalse(os.path.exists(target))

    def test_R11_export_image_data_live_fills_tokens(self):
        """R11(e)."""
        _, debug, _ = run("export", self.path, "--mode", "image")
        _, live, _ = run("export", self.path, "--mode", "image", "--data", "live")
        self.assertIn("{{cart.total}}", debug)
        self.assertIn("Total: $42.00", live)
        self.assertNotIn("{{", live)

    def test_R11_render_does_not_change_the_file(self):
        """R10(g): rendering only reads."""
        before = self.read()
        run("render", self.path, "--data", "live")
        self.assertEqual(self.read(), before)


if __name__ == "__main__":
    unittest.main()
