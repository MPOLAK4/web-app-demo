import copy
import json
import re
import unittest

from wireframe import checks, model, spec
from wireframe.example import example_wireframe
from helpers import block, doc, state, transition

# Every finding code listed in spec.md (R4 and R5).
SPEC_CODES = {
    "no-initial", "unknown-state", "unreachable-state", "dead-end", "nondeterministic",
    "unguarded-overlap", "dead-control", "no-trigger", "button-without-event", "overlap",
    "out-of-canvas", "duplicate-info", "duplicate-label", "missing-info",
}


def small():
    """Two screens. The event/guard/info words are distinctive so tests can
    look for them (or for their absence) in the output."""
    return doc(
        [
            state("home", [
                block("zeta", type="text", x=500, y=500, w=200, h=40, label="Bottom right text",
                      info=("secret.infokey",)),
                block("alpha", type="heading", x=0, y=0, w=200, h=40, label="Welcome", info=("home.title",),
                      note="Greets the visitor"),
                block("beta", type="button", x=300, y=0, w=100, h=40, label="Go", info=("action.go",),
                      event="launch_event"),
            ]),
            state("end", [], final=True, title="The End"),
        ],
        [transition("t1", "home", "end", "launch_event", guard="user_is_adult")],
        name="Demo",
    )


class ExportCoderTests(unittest.TestCase):
    def test_R2_coder_spec_lists_every_block_attribute(self):
        """R2(a)."""
        text = spec.export_spec(small(), "coder")
        for needle in ("Demo", "home", "alpha", "heading", "Welcome", "home.title",
                       "Greets the visitor", "beta", "button", "launch_event",
                       "secret.infokey", "800", "600"):
            self.assertIn(needle, text)

    def test_R2_coder_spec_lists_transitions_with_guards(self):
        """R2(a)."""
        text = spec.export_spec(small(), "coder")
        self.assertIn("user_is_adult", text)
        # source, event and target all appear on the transition's own line
        line = next(l for l in text.splitlines() if "user_is_adult" in l)
        for needle in ("home", "launch_event", "end"):
            self.assertIn(needle, line)

    def test_R2_blocks_are_listed_top_to_bottom_then_left_to_right(self):
        """R2(c): alpha (y=0,x=0), beta (y=0,x=300), zeta (y=500)."""
        text = spec.export_spec(small(), "coder")
        positions = [text.index(f"`{name}`") for name in ("alpha", "beta", "zeta")]
        self.assertEqual(positions, sorted(positions))

    def test_R2_final_screens_are_marked(self):
        self.assertIn("final", spec.export_spec(small(), "coder").lower())

    def test_R2_table_cells_escape_pipes_and_newlines(self):
        """A label containing | or a newline must not break the Markdown table."""
        d = doc([state("a", [block("b1", label="a|b\nc")], final=True)])
        text = spec.export_spec(d, "coder")
        self.assertIn("a\\|b c", text)


class ExportImageTests(unittest.TestCase):
    def test_R2_image_spec_describes_labels_and_rough_positions(self):
        """R2(b)."""
        text = spec.export_spec(small(), "image")
        self.assertIn("Welcome", text)
        self.assertIn("Bottom right text", text)
        self.assertIn("top-left", text)
        self.assertIn("bottom-right", text)

    def test_R2_image_spec_has_no_events_guards_or_info_keys(self):
        """R2(b): an image generator should see only what is visible."""
        text = spec.export_spec(small(), "image")
        for forbidden in ("launch_event", "user_is_adult", "secret.infokey", "home.title",
                          "Greets the visitor"):
            self.assertNotIn(forbidden, text)

    def test_R2_image_spec_mentions_each_screen_title(self):
        text = spec.export_spec(small(), "image")
        self.assertIn("Home", text)
        self.assertIn("The End", text)

    def test_R2_image_spec_places_blocks_by_their_centre(self):
        """A block spanning the whole canvas is 'center', not a corner."""
        d = doc([state("a", [block("b1", x=0, y=0, w=800, h=600, label="Everything")], final=True)])
        text = spec.export_spec(d, "image")
        line = next(l for l in text.splitlines() if "Everything" in l)
        self.assertIn("center", line)


class ExportCommonTests(unittest.TestCase):
    def test_R2_output_is_deterministic(self):
        """R2(c)."""
        for mode in ("coder", "image"):
            self.assertEqual(spec.export_spec(small(), mode), spec.export_spec(copy.deepcopy(small()), mode))

    def test_R2_block_input_order_does_not_change_the_output(self):
        d = small()
        reordered = copy.deepcopy(d)
        reordered["states"][0]["blocks"].reverse()
        for mode in ("coder", "image"):
            self.assertEqual(spec.export_spec(d, mode), spec.export_spec(reordered, mode))

    def test_R2_unknown_mode_is_an_error(self):
        """R2(d)."""
        with self.assertRaises(model.WireframeError):
            spec.export_spec(small(), "poem")

    def test_R2_export_does_not_modify_the_document(self):
        d = small()
        snapshot = copy.deepcopy(d)
        spec.export_spec(d, "coder")
        spec.export_spec(d, "image")
        self.assertEqual(d, snapshot)


class GuideTests(unittest.TestCase):
    def test_R3_guide_states_the_format_types_and_event_rule(self):
        """R3(a)."""
        text = spec.authoring_guide()
        for block_type in model.BLOCK_TYPES:
            self.assertIn(f"`{block_type}`", text)
        for field in ("canvas", "initial", "states", "transitions", "source", "target",
                      "guard", "info", "note", "event", "final"):
            self.assertIn(f"`{field}`", text)
        self.assertIn("sys:", text)

    def test_R3_guide_documents_every_checker_rule(self):
        """R3(a): the guide is generated from checks.RULES, so none is missing."""
        text = spec.authoring_guide()
        for code in checks.RULES:
            self.assertIn(f"`{code}`", text)

    def test_R3_rules_table_matches_the_codes_in_the_spec(self):
        """Guards against adding a check but forgetting to document it (or vice versa)."""
        self.assertEqual(set(checks.RULES), SPEC_CODES)

    def test_R3_check_never_emits_a_code_missing_from_the_rules(self):
        """Run check() over a deliberately messy wireframe touching many rules."""
        messy = doc(
            [state("a", [block("b1", type="button", x=-5, y=0, label="Dup", info=()),
                         block("b2", type="button", x=0, y=0, label="Dup", info=("k",), event="e"),
                         block("b3", x=0, y=0, label="Z", info=("k",))]),
             state("island")],
            [transition("t1", "a", "ghost", "x"), transition("t2", "a", "a", "y"),
             transition("t3", "a", "a", "y")],
            initial="nowhere",
        )
        emitted = {f["code"] for f in checks.check(messy)}
        self.assertTrue(emitted)
        self.assertLessEqual(emitted, set(checks.RULES))

    def test_R3_example_in_the_guide_is_valid_and_clean(self):
        """R3(b): extract the JSON the guide shows an AI and test *that*."""
        text = spec.authoring_guide()
        match = re.search(r"```json\n(.*?)\n```", text, re.S)
        self.assertIsNotNone(match, "guide has no ```json example")
        example = json.loads(match.group(1))
        self.assertEqual(model.validate(example), [])
        self.assertFalse(checks.has_errors(checks.check(example)))

    def test_R3_the_example_has_no_findings_at_all(self):
        """The example teaches by being a good design, so it has no warnings either."""
        self.assertEqual(checks.check(example_wireframe()), [])

    def test_R3_guide_tells_the_ai_how_to_submit(self):
        text = spec.authoring_guide()
        self.assertIn("PUT /api/wireframe", text)
        self.assertIn("python -m wireframe validate", text)


if __name__ == "__main__":
    unittest.main()
