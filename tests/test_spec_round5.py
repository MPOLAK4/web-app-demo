"""R15: iteration guidance in the authoring guide and both spec sheets.

R15 is guidance only. These tests check the *text* an AI is given, and that
nothing else about the wireframe changed (no new field, no new check).
"""
import unittest
from unittest import mock

from wireframe import checks, model, spec
from wireframe.example import example_wireframe
from helpers import block, doc, state, transition


def section(text, heading):
    """The text under a '## heading' up to the next '## ' (or the end)."""
    start = text.index(f"## {heading}")
    rest = text[start + 3:]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def tricky_doc():
    """A wireframe whose events, guards and info keys we can look for in the image brief."""
    return doc(
        [state("home", [block("go", "button", label="Go", info=("secret.infokey",), event="launch_event")]),
         state("end", final=True)],
        [transition("t1", "home", "end", "launch_event", guard="user_is_adult")])


class GuideIterationTests(unittest.TestCase):
    def setUp(self):
        self.guide = spec.authoring_guide()
        self.text = section(self.guide, "Iterating on one UI piece")

    def test_R15_guide_has_an_iteration_section(self):
        """R15(a): the guide has the section."""
        self.assertIn("## Iterating on one UI piece", self.guide)

    def test_R15_guide_says_to_settle_the_number_of_passes_and_to_ask(self):
        """R15(a): use the user's number; ask if none was given."""
        low = self.text.lower()
        self.assertIn("number of passes", low)
        self.assertIn("ask", low)

    def test_R15_guide_gives_the_default_when_it_cannot_ask(self):
        """R15(a): with no way to ask, use 2 and say so."""
        self.assertIn(f"use {spec.DEFAULT_ITERATIONS}", self.text)
        self.assertIn("say so", self.text.lower())

    def test_R15_guide_requires_a_named_change_each_pass_and_allows_stopping_early(self):
        """R15(a)."""
        low = self.text.lower()
        for word in ("position", "size", "label", "style", "duplicated information"):
            self.assertIn(word, low)
        self.assertIn("stop early", low)

    def test_R15_guide_asks_for_validate_check_and_a_pass_log_line(self):
        """R15(a): validate + check each pass, stable ids / op, and a one-line log."""
        self.assertIn("validate", self.text)
        self.assertIn("check", self.text)
        self.assertIn("Pass k of N", self.text)
        self.assertIn("`op`", self.text)

    def test_R15_guide_says_the_app_does_not_enforce_the_count(self):
        """R15(a): the reader must not think the tool tracks passes."""
        self.assertIn("does not store or enforce", self.text)

    def test_R15_a_piece_is_defined(self):
        """R15: 'piece' means one screen or one group of blocks on it."""
        self.assertIn("one screen", self.text)


class ExportIterationTests(unittest.TestCase):
    def test_R15_both_exports_end_with_an_iterations_section(self):
        """R15(b)."""
        for mode in spec.MODES:
            text = spec.export_spec(example_wireframe(), mode)
            self.assertIn("## Iterations", text, mode)
            self.assertNotIn("\n## ", text[text.index("## Iterations") + 3:], mode)  # it is last

    def test_R15_image_iterations_section_names_no_events_guards_or_info_keys(self):
        """R15(b) with R2(b): the image brief stays visual-only."""
        text = spec.export_spec(tricky_doc(), "image")
        for forbidden in ("launch_event", "user_is_adult", "secret.infokey", "`op`", "validate"):
            self.assertNotIn(forbidden, text)
        self.assertIn("layout", section(text, "Iterations").lower())

    def test_R15_coder_iterations_section_asks_to_ask_and_to_log(self):
        """R15(b)."""
        low = section(spec.export_spec(tricky_doc(), "coder"), "Iterations").lower()
        self.assertIn("ask", low)
        self.assertIn("what changed", low)

    def test_R15_default_is_one_constant_used_everywhere(self):
        """R15(c): change the constant and the guide and both exports follow it."""
        self.assertEqual(spec.DEFAULT_ITERATIONS, 2)
        with mock.patch.object(spec, "DEFAULT_ITERATIONS", 7):
            self.assertIn("use 7", spec.authoring_guide())
            for mode in spec.MODES:
                self.assertIn("7", section(spec.export_spec(tricky_doc(), mode), "Iterations"), mode)

    def test_R15_exports_stay_deterministic(self):
        """R15(d) with R2(c)."""
        for mode in spec.MODES:
            self.assertEqual(spec.export_spec(tricky_doc(), mode), spec.export_spec(tricky_doc(), mode))


class NothingElseChangedTests(unittest.TestCase):
    def test_R15_there_is_no_iterations_field_in_a_wireframe(self):
        """R15(d): guidance only, so an `iterations` field is still an unknown field."""
        d = example_wireframe()
        d["iterations"] = 3
        self.assertTrue(any("iterations" in e for e in model.validate(d)))

    def test_R15_the_worked_example_still_has_no_findings(self):
        """R15(d): the guide's own example still passes the checker cleanly."""
        self.assertEqual(checks.check(example_wireframe()), [])


if __name__ == "__main__":
    unittest.main()
