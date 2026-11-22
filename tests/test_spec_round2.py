"""Round 2 exports: detailed style in the coder and image specs (R6, R7) and the guide."""
import unittest

from wireframe import ops, spec, styles
from wireframe.example import example_wireframe
from helpers import block, doc, state


def styled_doc():
    a = block("a", "button", label="Pay", event="pay", info=("x.a",))
    b = block("b", "button", label="Cancel", event="no", info=("x.b",), y=100)
    c = block("c", "input", label="Name", info=("x.c",), y=200)
    d = doc([state("s", [a, b, c]), state("t", [block("d", "button", label="Again", info=("x.d",))])])
    d = ops.add_style(d, "primary", {"fill": "#2a6cf0", "radius": 8})
    d = ops.set_style(d, "s", ["a", "b"], "primary")
    d = ops.set_style(d, "t", ["d"], "primary")
    d = ops.update_block(d, "s", "c", look={"opacity": 0.5, "shadow": True},
                         placeholder="Your name", required=True)
    d = ops.update_block(d, "s", "b", options=["Yes", "No"], hidden=True)
    d = ops.update_state(d, "s", background="#eef2ff")
    return d


class CoderSpecStyleTests(unittest.TestCase):
    def setUp(self):
        self.text = spec.export_spec(styled_doc(), "coder")

    def test_R6_every_block_gets_all_eleven_resolved_fields(self):
        """R6(c): a table header with every style field."""
        header = next(l for l in self.text.splitlines() if l.startswith("| id | style |"))
        for field in styles.STYLE_FIELDS:
            self.assertIn(field, header)

    def test_R6_resolved_values_come_from_the_named_style_and_look(self):
        """R6(b)/(c): the row for `a` shows the style's fill, and `c` its own look."""
        row_a = next(l for l in self.text.splitlines() if l.startswith("| `a` | primary"))
        self.assertIn("#2a6cf0", row_a)
        row_c = next(l for l in self.text.splitlines() if l.startswith("| `c` | -"))
        self.assertIn("0.5", row_c)
        self.assertIn("true", row_c)

    def test_R6_properties_and_background_are_listed(self):
        """R6(c)."""
        self.assertIn('placeholder="Your name"', self.text)
        self.assertIn("required", self.text)
        self.assertIn("options=Yes / No", self.text)
        self.assertIn("Background: `#eef2ff`", self.text)
        self.assertIn("Background: `#ffffff`", self.text)        # screen t: the default

    def test_R7_styles_section_lists_fields_and_users(self):
        """R7(d)."""
        line = next(l for l in self.text.splitlines() if l.startswith("- **primary**"))
        self.assertIn("fill=#2a6cf0", line)
        self.assertIn("`s.a`", line)
        self.assertIn("`t.d`", line)

    def test_R7_a_document_without_styles_says_none(self):
        """R7(d): Round 1 file still exports."""
        text = spec.export_spec(doc([state("s", [block("a")])]), "coder")
        self.assertIn("## Styles\n\n(none)", text)

    def test_R6_coder_spec_still_lists_events_and_guards(self):
        """R2 still holds: the coder needs the behaviour too."""
        self.assertIn("pay", self.text)

    def test_R6_output_is_deterministic(self):
        """R6(e)."""
        self.assertEqual(self.text, spec.export_spec(styled_doc(), "coder"))
        self.assertEqual(spec.export_spec(styled_doc(), "image"), spec.export_spec(styled_doc(), "image"))


class ImageSpecStyleTests(unittest.TestCase):
    def setUp(self):
        self.text = spec.export_spec(styled_doc(), "image")

    def test_R6_style_is_written_in_visual_words(self):
        """R6(d)."""
        line = next(l for l in self.text.splitlines() if "Pay" in l and l.startswith("-"))
        for word in ("fill #2a6cf0", "corners rounded 8px", "bold", "center-aligned"):
            self.assertIn(word, line)
        line_c = next(l for l in self.text.splitlines() if '"Name"' in l)
        self.assertIn("soft drop shadow", line_c)
        self.assertIn("50% opacity", line_c)
        self.assertIn('placeholder text "Your name"', line_c)

    def test_R6_screen_background_is_stated(self):
        """R6(d)."""
        self.assertIn("Screen background #eef2ff.", self.text)

    def test_R8_hidden_blocks_are_not_drawn(self):
        """R8(b): a hidden block is not on the picture."""
        self.assertNotIn("Cancel", self.text)

    def test_R7_blocks_sharing_a_style_are_said_to_look_identical(self):
        """R7(d): the image generator must draw them the same way."""
        self.assertIn("## Blocks that must look identical", self.text)
        line = self.text.split("## Blocks that must look identical")[1]
        self.assertIn('"Pay" button on screen 1', line)
        self.assertIn('"Again" button on screen 2', line)

    def test_R7_no_identical_section_without_sharing(self):
        """R7(d)."""
        self.assertNotIn("must look identical", spec.export_spec(doc([state("s", [block("a")])]), "image"))

    def test_R2_image_spec_still_hides_behaviour(self):
        """R2(b)/R6(d): style names, events, guards and info keys stay out of the brief."""
        for secret in ("x.a", "event", "primary", "guard"):
            self.assertNotIn(secret, self.text)


class GuideStyleTests(unittest.TestCase):
    def test_R6_guide_teaches_the_style_fields_and_new_properties(self):
        """R6(a)/R8: an AI can only use fields the guide mentions."""
        guide = spec.authoring_guide()
        for word in list(styles.STYLE_FIELDS) + ["styles", "look", "placeholder", "options",
                                                  "hidden", "disabled", "required", "background",
                                                  "390x844", "820x1180", "1280x800",
                                                  "missing-style", "unknown-style", "unused-style"]:
            self.assertIn(word, guide, word)

    def test_R7_the_example_in_the_guide_uses_shared_styles(self):
        """R7: the worked example shows the feature."""
        self.assertTrue(example_wireframe()["styles"])


if __name__ == "__main__":
    unittest.main()
