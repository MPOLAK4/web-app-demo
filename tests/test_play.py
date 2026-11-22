"""Walking the wireframe like a real UI (R9): the play module and the `walk` command."""
import contextlib
import io
import os
import tempfile
import unittest

from wireframe import cli, model, play
from wireframe.model import WireframeError
from helpers import block, doc, state, transition


def flow():
    go = block("go", "button", label="Go", event="go", info=("a",))
    hid = block("ghost", "button", label="Ghost", event="boo", info=("b",), y=50)
    hid["hidden"] = True
    off = block("off", "button", label="Off", event="nope", info=("c",), y=100)
    off["disabled"] = True
    pick = block("pick", "button", label="Pick", event="pick", info=("d",), y=150)
    return doc(
        [state("home", [go, hid, off, pick]),
         state("next", [block("back", "button", label="Back", event="back", info=("e",))]),
         state("a", final=True), state("b", final=True), state("end", final=True)],
        [transition("t1", "home", "next", "go"),
         transition("t2", "next", "home", "back"),
         transition("t3", "home", "a", "pick", guard="user is member"),
         transition("t4", "home", "b", "pick", guard="user is guest"),
         transition("t5", "home", "end", "sys:timeout")],
        initial="home")


class ScreenTests(unittest.TestCase):
    def test_R9_screen_shows_what_a_user_would_see(self):
        """R9(a): hidden blocks are left out, everything else is there with its resolved style."""
        scr = play.screen(flow(), "home")
        ids = [b["id"] for b in scr["blocks"]]
        self.assertEqual(ids, ["go", "off", "pick"])
        self.assertEqual(set(scr["blocks"][0]["resolved"]), set(__import__("wireframe.styles", fromlist=["x"]).STYLE_FIELDS))
        self.assertEqual((scr["state"], scr["final"]), ("home", False))

    def test_R9_screen_lists_usable_events_but_not_disabled_ones(self):
        """R9(b): a disabled button cannot be pressed in play."""
        scr = play.screen(flow(), "home")
        self.assertEqual(scr["events"], ["go", "pick"])

    def test_R9_screen_lists_system_events_separately(self):
        """R9(c): the user cannot press `sys:` events, but a walker can trigger them."""
        self.assertEqual(play.screen(flow(), "home")["system_events"], ["sys:timeout"])

    def test_R9_unknown_state_is_an_error(self):
        """R9(a)."""
        with self.assertRaises(WireframeError):
            play.screen(flow(), "zzz")

    def test_R9_final_screens_are_marked(self):
        """R9(e)."""
        self.assertTrue(play.screen(flow(), "end")["final"])


class StepTests(unittest.TestCase):
    def test_R9_event_moves_to_the_target(self):
        """R9(b)."""
        r = play.step(flow(), "home", "go")
        self.assertEqual((r["status"], r["state"], r["transition"]), ("moved", "next", "t1"))

    def test_R9_event_with_no_transition_is_stuck(self):
        """R9(b): nothing happens and the state stays."""
        r = play.step(flow(), "home", "back")
        self.assertEqual((r["status"], r["state"]), ("stuck", "home"))

    def test_R9_guarded_alternatives_ask_the_walker_to_choose(self):
        """R9(c): guards are conditions in words; the tool cannot evaluate them."""
        r = play.step(flow(), "home", "pick")
        self.assertEqual(r["status"], "choose")
        self.assertEqual(r["state"], "home")
        self.assertEqual([(o["transition"], o["guard"], o["target"]) for o in r["options"]],
                         [("t3", "user is member", "a"), ("t4", "user is guest", "b")])

    def test_R9_choice_selects_one_of_the_options(self):
        """R9(c)."""
        r = play.step(flow(), "home", "pick", choice="t4")
        self.assertEqual((r["status"], r["state"]), ("moved", "b"))

    def test_R9_a_choice_that_is_not_an_option_is_an_error(self):
        """R9(c): t1 exists but does not belong to this event."""
        with self.assertRaises(WireframeError):
            play.step(flow(), "home", "pick", choice="t1")

    def test_R9_system_events_can_be_triggered(self):
        """R9(c)."""
        self.assertEqual(play.step(flow(), "home", "sys:timeout")["state"], "end")

    def test_R9_step_from_unknown_state_is_an_error(self):
        """R9(a)."""
        with self.assertRaises(WireframeError):
            play.step(flow(), "zzz", "go")

    def test_R9_step_does_not_change_the_document(self):
        """R9(d): play never edits the file."""
        d = flow()
        import copy
        before = copy.deepcopy(d)
        play.step(d, "home", "go")
        play.screen(d, "home")
        self.assertEqual(d, before)


class WalkCommandTests(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "w.json")
        model.save(flow(), self.path)

    def test_R9_walk_without_events_shows_the_first_screen(self):
        """R9(f)."""
        code, out, _ = self.run_cli("walk", self.path)
        self.assertEqual(code, 0)
        self.assertIn("home", out)
        self.assertIn("go", out)

    def test_R9_walk_follows_events_in_order(self):
        """R9(f)."""
        code, out, _ = self.run_cli("walk", self.path, "go", "back", "go")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("--go-->"), 2)
        self.assertEqual(out.count("--back-->"), 1)
        self.assertIn("Now on: next", out)

    def test_R9_walk_stops_with_exit_1_when_stuck(self):
        """R9(f)."""
        code, out, err = self.run_cli("walk", self.path, "back")
        self.assertEqual(code, 1)
        self.assertIn("back", out + err)

    def test_R9_walk_needs_a_choice_where_guards_compete(self):
        """R9(f): `pick` alone is ambiguous; `pick=t3` is not."""
        code, out, _ = self.run_cli("walk", self.path, "pick")
        self.assertEqual(code, 1)
        self.assertIn("t3", out)
        self.assertIn("user is guest", out)
        code, out, _ = self.run_cli("walk", self.path, "pick=t3")
        self.assertEqual(code, 0)
        self.assertIn("Now on: a", out)

    def test_R9_walk_reports_the_final_screen(self):
        """R9(e)."""
        code, out, _ = self.run_cli("walk", self.path, "sys:timeout")
        self.assertEqual(code, 0)
        self.assertIn("final", out)

    def test_R9_walk_never_changes_the_file(self):
        """R9(d)."""
        with open(self.path, "rb") as f:
            before = f.read()
        self.run_cli("walk", self.path, "go")
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_R9_walk_reports_a_bad_choice_as_an_error(self):
        """R9(f)."""
        code, _, err = self.run_cli("walk", self.path, "pick=t1")
        self.assertEqual(code, 1)
        self.assertIn("t1", err)


if __name__ == "__main__":
    unittest.main()
