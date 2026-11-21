"""R4: the state machine is checked against the blocks drawn on each screen.

Each test builds a tiny wireframe with ONE problem and asserts that exactly
the expected finding code appears (and, for the good case, that no errors do).
"""
import copy
import unittest

from wireframe import checks
from helpers import block, codes, doc, state, transition


def btn(id, event, label=None, **kw):
    return block(id, type="button", label=label or id.title(), event=event, info=(f"action.{event}",), **kw)


def good():
    """cart --pay--> done. The Pay button exists, the transition exists."""
    return doc(
        [state("cart", [btn("pay", "pay", x=10, y=10)]), state("done", final=True)],
        [transition("t1", "cart", "done", "pay")],
    )


def severities(findings, code):
    return {f["severity"] for f in findings if f["code"] == code}


class FlowTests(unittest.TestCase):
    def test_R4_sound_wireframe_has_no_errors(self):
        """R4(j): a consistent design is not flagged."""
        findings = checks.check(good())
        self.assertEqual([f for f in findings if f["severity"] == "error"], [])

    def test_R4_missing_initial_state(self):
        """R4(a)."""
        d = good()
        d["initial"] = ""
        self.assertIn("no-initial", codes(checks.check(d)))
        d["initial"] = "ghost"
        self.assertIn("no-initial", codes(checks.check(d)))

    def test_R4_transition_to_unknown_state(self):
        """R4(b): target missing."""
        d = good()
        d["transitions"].append(transition("t2", "cart", "ghost", "x"))
        f = checks.check(d)
        self.assertIn("unknown-state", codes(f))
        self.assertEqual(severities(f, "unknown-state"), {"error"})

    def test_R4_transition_from_unknown_state(self):
        """R4(b): source missing."""
        d = good()
        d["transitions"].append(transition("t2", "ghost", "cart", "x"))
        self.assertIn("unknown-state", codes(checks.check(d)))

    def test_R4_unreachable_state(self):
        """R4(c): 'island' has no path from the initial state."""
        d = good()
        d["states"].append(state("island", final=True))
        f = checks.check(d)
        self.assertIn("unreachable-state", codes(f))
        self.assertEqual(severities(f, "unreachable-state"), {"warning"})
        self.assertEqual([x["state"] for x in f if x["code"] == "unreachable-state"], ["island"])

    def test_R4_reachability_follows_chains_of_transitions(self):
        """R4(c): a -> b -> c makes all three reachable."""
        d = doc(
            [state("a", [btn("go", "go")]), state("b", [btn("go2", "go2")]), state("c", final=True)],
            [transition("t1", "a", "b", "go"), transition("t2", "b", "c", "go2")],
        )
        self.assertNotIn("unreachable-state", codes(checks.check(d)))

    def test_R4_dead_end_state(self):
        """R4(d): a non-final state with no way out traps the user."""
        d = good()
        d["states"][1]["final"] = False
        f = checks.check(d)
        self.assertIn("dead-end", codes(f))
        self.assertEqual([x["state"] for x in f if x["code"] == "dead-end"], ["done"])

    def test_R4_final_state_is_not_a_dead_end(self):
        """R4(d): final=true says the flow is meant to stop here."""
        self.assertNotIn("dead-end", codes(checks.check(good())))

    def test_R4_same_event_same_guard_is_nondeterministic(self):
        """R4(e): two identical triggers; the app cannot know which to take."""
        d = good()
        d["states"].append(state("other", final=True))
        d["transitions"].append(transition("t2", "cart", "other", "pay"))
        f = checks.check(d)
        self.assertIn("nondeterministic", codes(f))
        self.assertEqual(severities(f, "nondeterministic"), {"error"})

    def test_R4_same_event_with_different_guards_is_fine(self):
        """R4(e): guards are what tells the two apart."""
        d = good()
        d["states"].append(state("other", final=True))
        d["transitions"][0]["guard"] = "logged in"
        d["transitions"].append(transition("t2", "cart", "other", "pay", guard="logged out"))
        f = checks.check(d)
        self.assertNotIn("nondeterministic", codes(f))
        self.assertNotIn("unguarded-overlap", codes(f))

    def test_R4_one_guarded_one_unguarded_is_a_warning(self):
        """R4(e): the unguarded one also matches when the guard holds."""
        d = good()
        d["states"].append(state("other", final=True))
        d["transitions"][0]["guard"] = "logged in"
        d["transitions"].append(transition("t2", "cart", "other", "pay"))
        f = checks.check(d)
        self.assertEqual(severities(f, "unguarded-overlap"), {"warning"})
        self.assertNotIn("nondeterministic", codes(f))

    def test_R4_dead_control_button_with_no_transition(self):
        """R4(f): the UI shows a Pay button but the flow never handles 'pay'."""
        d = good()
        d["transitions"] = []
        d["states"][1]["final"] = True
        f = checks.check(d)
        self.assertIn("dead-control", codes(f))
        self.assertEqual([x["blocks"] for x in f if x["code"] == "dead-control"], [["pay"]])

    def test_R4_dead_control_ignores_transitions_from_other_states(self):
        """R4(f): handling 'pay' on a different screen does not help this one."""
        d = good()
        d["transitions"] = [transition("t1", "done", "cart", "pay")]
        d["states"][1]["final"] = False
        self.assertIn("dead-control", codes(checks.check(d)))

    def test_R4_transition_event_that_no_block_can_raise(self):
        """R4(g): the flow has a path the user has no control for."""
        d = good()
        d["states"][0]["blocks"] = []
        f = checks.check(d)
        self.assertIn("no-trigger", codes(f))
        self.assertEqual(severities(f, "no-trigger"), {"error"})

    def test_R4_system_events_need_no_block(self):
        """R4(g): 'sys:' events come from the system (a timer, a response)."""
        d = good()
        d["states"][0]["blocks"] = []
        d["transitions"][0]["event"] = "sys:timeout"
        self.assertNotIn("no-trigger", codes(checks.check(d)))

    def test_R4_button_without_event(self):
        """R4(h): a button that raises nothing is suspicious."""
        d = good()
        d["states"][0]["blocks"].append(block("dud", type="button", label="Dud", info=("a.b",)))
        self.assertIn("button-without-event", codes(checks.check(d)))

    def test_R4_overlapping_blocks(self):
        """R4(i): two blocks on top of each other."""
        d = good()
        d["states"][0]["blocks"] = [
            block("p", x=0, y=0, w=100, h=100, label="P", info=("p",)),
            block("q", x=50, y=50, w=100, h=100, label="Q", info=("q",)),
        ]
        d["transitions"][0]["event"] = "sys:go"
        f = checks.check(d)
        self.assertEqual(severities(f, "overlap"), {"warning"})
        self.assertEqual([x["blocks"] for x in f if x["code"] == "overlap"], [["p", "q"]])

    def test_R4_blocks_that_only_touch_do_not_overlap(self):
        """R4(i): sharing an edge is not overlapping."""
        d = good()
        d["states"][0]["blocks"] = [
            block("p", x=0, y=0, w=100, h=100, label="P", info=("p",)),
            block("q", x=100, y=0, w=100, h=100, label="Q", info=("q",)),
        ]
        d["transitions"][0]["event"] = "sys:go"
        self.assertNotIn("overlap", codes(checks.check(d)))

    def test_R4_a_container_may_hold_other_blocks(self):
        """R4(i): a container that fully holds a block is not an overlap."""
        d = good()
        d["states"][0]["blocks"] = [
            block("box", type="container", x=0, y=0, w=300, h=300),
            block("in", x=10, y=10, w=50, h=50, label="In", info=("in",)),
        ]
        d["transitions"][0]["event"] = "sys:go"
        self.assertNotIn("overlap", codes(checks.check(d)))

    def test_R4_a_container_only_partly_holding_a_block_is_an_overlap(self):
        d = good()
        d["states"][0]["blocks"] = [
            block("box", type="container", x=0, y=0, w=100, h=100),
            block("half", x=80, y=80, w=100, h=100, label="Half", info=("h",)),
        ]
        d["transitions"][0]["event"] = "sys:go"
        self.assertIn("overlap", codes(checks.check(d)))

    def test_R4_block_outside_the_canvas(self):
        """R4(i): the canvas is 800x600 in the helper."""
        for x, y, w, h in [(-1, 0, 10, 10), (0, -1, 10, 10), (791, 0, 10, 10), (0, 595, 10, 10)]:
            d = good()
            d["states"][0]["blocks"] = [block("o", x=x, y=y, w=w, h=h, label="O", info=("o",))]
            d["transitions"][0]["event"] = "sys:go"
            self.assertIn("out-of-canvas", codes(checks.check(d)), (x, y, w, h))

    def test_R4_block_exactly_filling_the_canvas_is_inside(self):
        d = good()
        d["states"][0]["blocks"] = [block("o", x=0, y=0, w=800, h=600, label="O", info=("o",))]
        d["transitions"][0]["event"] = "sys:go"
        self.assertNotIn("out-of-canvas", codes(checks.check(d)))

    def test_R4_findings_have_the_documented_shape(self):
        """R4: severity, code, state, blocks and message are always present."""
        d = good()
        d["states"][0]["blocks"] = []
        for f in checks.check(d):
            self.assertEqual(set(f), {"severity", "code", "state", "blocks", "message"})
            self.assertIn(f["severity"], ("error", "warning"))
            self.assertTrue(f["message"])

    def test_R4_errors_are_listed_before_warnings(self):
        d = good()
        d["states"].append(state("island", final=True))  # warning
        d["states"][0]["blocks"] = []                    # no-trigger error
        severities_in_order = [f["severity"] for f in checks.check(d)]
        self.assertEqual(severities_in_order, sorted(severities_in_order, key=lambda s: s != "error"))

    def test_R4_check_does_not_modify_the_document(self):
        d = good()
        snapshot = copy.deepcopy(d)
        checks.check(d)
        self.assertEqual(d, snapshot)

    def test_R4_has_errors_and_format_for_the_command_line(self):
        """R4(k): the CLI exits 1 when has_errors() is true and prints format_findings()."""
        d = good()
        d["states"][0]["blocks"] = []
        findings = checks.check(d)
        self.assertTrue(checks.has_errors(findings))
        self.assertIn("no-trigger", checks.format_findings(findings))
        self.assertFalse(checks.has_errors(checks.check(good())))
        self.assertIn("no problems", checks.format_findings([]).lower())


if __name__ == "__main__":
    unittest.main()
