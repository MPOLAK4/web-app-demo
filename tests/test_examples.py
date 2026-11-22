"""R14: the example library and its expected I/O (the module, the files, the command line).

An example's *input* is a wireframe; its *expected I/O* is what the tool prints for
it. These tests do not hard-code those outputs. They check that each stored output
is exactly what the real command produces, so an example can never go stale.
"""
import os
import re
import tempfile
import unittest

from wireframe import checks, examples, model, render, spec, viewer
from wireframe.example import example_wireframe
from wireframe.model import WireframeError
from test_cli import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ["checkout", "login", "dashboard", "settings", "flawed"]
CLEAN = ["checkout", "login", "dashboard", "settings"]


def types_in(doc):
    return {b["type"] for s in doc["states"] for b in s["blocks"]}


class LibraryTests(unittest.TestCase):
    def test_R14_list_has_the_five_examples_in_order(self):
        """R14(a)."""
        listed = examples.list_examples()
        self.assertEqual([e["name"] for e in listed], NAMES)
        for e in listed:
            self.assertEqual(set(e), {"name", "title", "summary"})
            self.assertTrue(e["title"].strip() and e["summary"].strip())

    def test_R14_every_example_is_a_valid_wireframe(self):
        """R14(b): validate finds nothing wrong with any example."""
        for name in NAMES:
            self.assertEqual(model.validate(examples.get_example(name)), [], name)

    def test_R14_get_example_returns_a_fresh_copy(self):
        """R14(b): editing what you got must not change the library."""
        first = examples.get_example("login")
        first["name"] = "Changed"
        first["states"].clear()
        again = examples.get_example("login")
        self.assertNotEqual(again["name"], "Changed")
        self.assertTrue(again["states"])

    def test_R14_unknown_example_is_an_error_listing_the_valid_names(self):
        """R14(b)."""
        with self.assertRaises(WireframeError) as ctx:
            examples.get_example("nope")
        message = " ".join(ctx.exception.errors)
        for name in NAMES:
            self.assertIn(name, message)

    def test_R14_checkout_is_the_round_1_worked_example(self):
        """R14(c)."""
        self.assertEqual(examples.get_example("checkout"), example_wireframe())

    def test_R14_the_clean_examples_have_no_findings_at_all(self):
        """R14(c): no errors and no warnings, so they are safe to copy from."""
        for name in CLEAN:
            self.assertEqual(checks.check(examples.get_example(name)), [], name)

    def test_R14_login_shows_inputs_a_checkbox_and_a_guarded_split(self):
        """R14(c): one event leads to two screens, told apart by guards."""
        d = examples.get_example("login")
        self.assertTrue({"input", "checkbox", "button"} <= types_in(d))
        by_event = {}
        for t in d["transitions"]:
            by_event.setdefault((t["source"], t["event"]), []).append(t)
        self.assertTrue(any(len(ts) == 2 and all(t["guard"].strip() for t in ts) for ts in by_event.values()))

    def test_R14_dashboard_shows_nav_card_and_table(self):
        """R14(c)."""
        self.assertTrue({"nav", "card", "table"} <= types_in(examples.get_example("dashboard")))

    def test_R14_settings_shows_toggle_select_and_slider(self):
        """R14(c)."""
        self.assertTrue({"toggle", "select", "slider"} <= types_in(examples.get_example("settings")))

    def test_R14_examples_use_live_data_tokens_with_sample_data(self):
        """R14(c): the examples teach R11 too: a token with a sample in `data`."""
        d = examples.get_example("login")
        self.assertTrue(d.get("data"))
        text = render.render_screen(d, d["initial"], "svg", "live")
        self.assertNotIn("{{", text)


class FlawedExampleTests(unittest.TestCase):
    WANTED = {"duplicate-info", "duplicate-label", "dead-control", "button-without-event",
              "overlap", "unreachable-state", "dead-end"}

    def test_R14_flawed_is_valid_but_the_checker_finds_every_planned_flaw(self):
        """R14(d)."""
        d = examples.get_example("flawed")
        self.assertEqual(model.validate(d), [])
        found = {f["code"] for f in checks.check(d)}
        self.assertTrue(self.WANTED <= found, f"missing: {self.WANTED - found}")

    def test_R14_each_flaw_is_explained_in_a_note(self):
        """R14(d): notes starting with FLAW: let a reader match a note to a finding."""
        d = examples.get_example("flawed")
        notes = [b["note"] for s in d["states"] for b in s["blocks"] if b["note"].startswith("FLAW:")]
        self.assertGreaterEqual(len(notes), 4)
        for note in notes:
            self.assertGreater(len(note), len("FLAW: "))

    def test_R14_flawed_is_the_only_example_with_flaw_notes(self):
        """R14(d): the clean examples must not carry FLAW notes."""
        for name in CLEAN:
            for s in examples.get_example(name)["states"]:
                for b in s["blocks"]:
                    self.assertFalse(b["note"].startswith("FLAW:"), name)


class ExpectedIoTests(unittest.TestCase):
    def test_R14_io_parts_equal_what_the_real_functions_give(self):
        """R14(e): wireframe, coder, image (live), check and viewer match direct calls."""
        for name in NAMES:
            d = examples.get_example(name)
            io = examples.example_io(name)
            self.assertEqual(set(io), {"wireframe", "coder", "image", "check", "svg", "viewer"})
            self.assertEqual(io["coder"], spec.export_spec(d, "coder"), name)
            self.assertEqual(io["image"], spec.export_spec(d, "image", data="live"), name)
            self.assertEqual(io["check"], checks.format_findings(checks.check(d)) + "\n", name)
            self.assertEqual(io["viewer"], viewer.build_viewer(d), name)

    def test_R14_svg_has_one_live_picture_per_screen(self):
        """R14(e)."""
        d = examples.get_example("login")
        svg = examples.example_io("login")["svg"]
        self.assertEqual(list(svg), [s["id"] for s in d["states"]])
        for state_id, text in svg.items():
            self.assertEqual(text, render.render_screen(d, state_id, "svg", "live"))

    def test_R14_wireframe_text_loads_back_to_the_same_example(self):
        """R14(e): the stored JSON is a real wireframe file."""
        import json
        for name in NAMES:
            self.assertEqual(json.loads(examples.example_io(name)["wireframe"]),
                             examples.get_example(name), name)

    def test_R14_io_is_deterministic_and_leaves_the_library_alone(self):
        """R14(e)."""
        self.assertEqual(examples.example_io("flawed"), examples.example_io("flawed"))
        self.assertEqual(examples.get_example("flawed"), examples.get_example("flawed"))

    def test_R14_io_of_an_unknown_example_is_an_error(self):
        """R14(e)."""
        with self.assertRaises(WireframeError):
            examples.example_io("nope")


class BuiltFilesTests(unittest.TestCase):
    def test_R14_build_writes_the_documented_files(self):
        """R14(f)."""
        files = examples.build_files()
        self.assertIn("README.md", files)
        for name in NAMES:
            for part in ("wireframe.json", "coder.md", "image-live.md", "check.txt", "viewer.html"):
                self.assertIn(f"{name}/{part}", files)
            for state in examples.get_example(name)["states"]:
                self.assertIn(f"{name}/screens/{state['id']}.svg", files)

    def test_R14_readme_mentions_every_example_and_file_kind(self):
        """R14(f)."""
        readme = examples.build_files()["README.md"]
        for name in NAMES:
            self.assertIn(name, readme)
        for part in ("wireframe.json", "coder.md", "image-live.md", "check.txt", "viewer.html", "screens"):
            self.assertIn(part, readme)

    def test_R14_write_files_creates_them_with_lf_endings_and_can_run_twice(self):
        """R14(f): `--build` replaces files it owns; running again changes nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            examples.write_files(tmp)
            examples.write_files(tmp)
            for rel, text in examples.build_files().items():
                with open(os.path.join(tmp, *rel.split("/")), "rb") as f:
                    raw = f.read()
                self.assertNotIn(b"\r", raw, rel)
                self.assertEqual(raw.decode("utf-8"), text, rel)

    def test_R14_the_examples_folder_in_the_repository_is_up_to_date(self):
        """R14(f): the committed folder is what the current code builds."""
        for rel, text in examples.build_files().items():
            path = os.path.join(ROOT, "examples", *rel.split("/"))
            self.assertTrue(os.path.exists(path), f"missing examples/{rel}; run: python -m wireframe examples --build examples")
            with open(path, encoding="utf-8", newline="") as f:
                self.assertEqual(f.read().replace("\r\n", "\n"), text, f"examples/{rel} is stale")

    def test_R14_the_examples_folder_has_no_files_the_build_does_not_make(self):
        """R14(f): a deleted or renamed example must not leave an orphan behind."""
        expected = {os.path.normpath(r) for r in examples.build_files()}
        found = set()
        base = os.path.join(ROOT, "examples")
        for folder, _, names in os.walk(base):
            for n in names:
                found.add(os.path.normpath(os.path.relpath(os.path.join(folder, n), base)))
        self.assertEqual(found, expected)

    def test_R14_example_viewers_are_self_contained(self):
        """R14(f) with R13(a): double-clickable, no outside links."""
        for name in NAMES:
            text = examples.example_io(name)["viewer"]
            # "http-equiv" (the CSP meta tag) and the SVG xmlns name are not links.
            text = text.replace("http://www.w3.org/2000/svg", "")
            self.assertIsNone(re.search(r"https?://", text), name)


class GuideExamplesTests(unittest.TestCase):
    def test_R14_guide_has_an_examples_section_naming_the_command_and_every_example(self):
        """R14(i)."""
        guide = spec.authoring_guide()
        self.assertIn("## Examples", guide)
        part = guide[guide.index("## Examples"):]
        part = part[:part.find("\n## ", 3)] if "\n## " in part[3:] else part
        self.assertIn("python -m wireframe examples", part)
        for name in NAMES:
            self.assertIn(name, part)

    def test_R14_guides_embedded_example_is_still_checkout(self):
        """R14(i)."""
        import json
        guide = spec.authoring_guide()
        self.assertIn(json.dumps(example_wireframe(), indent=2), guide)


class ExamplesCliTests(unittest.TestCase):
    def test_R14_examples_lists_every_example(self):
        """R14(g)."""
        code, out, err = run("examples")
        self.assertEqual(code, 0, err)
        for e in examples.list_examples():
            self.assertIn(e["name"], out)
            self.assertIn(e["summary"], out)

    def test_R14_examples_name_prints_the_wireframe_by_default(self):
        """R14(g)."""
        import json
        code, out, _ = run("examples", "login")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), examples.get_example("login"))

    def test_R14_each_part_prints_what_example_io_holds(self):
        """R14(g)."""
        io = examples.example_io("flawed")
        for part, key in (("coder", "coder"), ("image", "image"), ("check", "check"), ("viewer", "viewer")):
            code, out, _ = run("examples", "flawed", "--part", part)
            self.assertEqual(code, 0, part)
            self.assertEqual(out.rstrip("\n"), io[key].rstrip("\n"), part)

    def test_R14_svg_part_defaults_to_the_first_screen_and_takes_state(self):
        """R14(g)."""
        io = examples.example_io("login")
        first, other = list(io["svg"])[0], list(io["svg"])[1]
        _, out, _ = run("examples", "login", "--part", "svg")
        self.assertEqual(out, io["svg"][first])
        _, out, _ = run("examples", "login", "--part", "svg", "--state", other)
        self.assertEqual(out, io["svg"][other])

    def test_R14_unknown_name_part_or_screen_is_exit_1_with_empty_stdout(self):
        """R14(g)."""
        for argv in (("examples", "nope"),
                     ("examples", "login", "--part", "svg", "--state", "nowhere")):
            code, out, err = run(*argv)
            self.assertEqual((code, out), (1, ""), argv)
            self.assertTrue(err.strip(), argv)
        code, out, _ = run("examples", "login", "--part", "bogus")
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")

    def test_R14_new_with_a_named_example_starts_from_it(self):
        """R14(g)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.json")
            code, _, err = run("new", path, "--example", "settings")
            self.assertEqual(code, 0, err)
            self.assertEqual(model.load(path), examples.get_example("settings"))

    def test_R14_new_with_a_bare_example_flag_still_means_checkout(self):
        """R14(g): Round 1 behaviour is kept."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.json")
            self.assertEqual(run("new", path, "--example")[0], 0)
            self.assertEqual(model.load(path), example_wireframe())

    def test_R14_new_with_an_unknown_example_fails_and_writes_nothing(self):
        """R14(g)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.json")
            code, _, err = run("new", path, "--example", "nope")
            self.assertEqual(code, 1)
            self.assertIn("login", err)
            self.assertFalse(os.path.exists(path))

    def test_R14_build_writes_the_folder(self):
        """R14(f), R14(g): `examples --build DIR`."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run("examples", "--build", tmp)
            self.assertEqual(code, 0, err)
            self.assertTrue(os.path.exists(os.path.join(tmp, "README.md")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "login", "screens")))


if __name__ == "__main__":
    unittest.main()
