"""R10: picture files (SVG, HTML) of any screen, and play.follow.

The tests read the output as text. We cannot look at a picture in a unit test,
so we check the facts that make it right: sizes, colours, order, escaping.
"""
import re
import unittest

from wireframe import play, render
from wireframe.model import WireframeError
from helpers import block, doc, state, transition


def two_screens():
    a = state("a", [block("b1", "button", 10, 20, 120, 40, label="Go", event="go")])
    b = state("b", [block("b2", "text", 0, 0, 100, 30, label="Hello {{user.name}}")])
    d = doc([a, b], [transition("t1", "a", "b", "go")])
    d["data"] = {"user.name": "Sam"}
    return d


class ContentLinesTests(unittest.TestCase):
    def lines(self, d, b, mode="debug"):
        return render.content_lines(d, b, mode)

    def test_R10_each_type_adds_its_decoration(self):
        """R10(d): the same per-type text the editor used to work out in JS."""
        d = doc([state("s")])
        self.assertEqual(self.lines(d, block(type="checkbox", label="Agree", **{}) | {"value": "true"}), ["[x] Agree"])
        self.assertEqual(self.lines(d, block(type="checkbox", label="Agree")), ["[ ] Agree"])
        self.assertEqual(self.lines(d, block(type="divider", label="x")), [])
        self.assertEqual(self.lines(d, block(type="icon", label="star")), ["(star)"])
        radio = block(type="radio", label="Size") | {"options": ["S", "M"], "value": "M"}
        self.assertEqual(self.lines(d, radio), ["Size", "( ) S", "(o) M"])

    def test_R10_input_shows_value_else_placeholder(self):
        """R10(d)."""
        d = doc([state("s")])
        inp = block(type="input", label="Name") | {"placeholder": "Your name"}
        self.assertEqual(self.lines(d, inp), ["Name", "Your name"])
        self.assertEqual(self.lines(d, inp | {"value": "Sam"}), ["Name", "Sam"])

    def test_R11_mode_applies_to_label_placeholder_value_and_options(self):
        """R11(e): live replaces tokens in every text field; debug leaves them."""
        d = doc([state("s")])
        d["data"] = {"a": "AA"}
        b = block(type="select", label="L {{a}}") | {"options": ["{{a}}", "x"], "value": "{{a}}"}
        self.assertEqual(self.lines(d, b, "debug"), ["L {{a}}", "{{a}}  v"])
        self.assertEqual(self.lines(d, b, "live"), ["L AA", "AA  v"])
        inp = block(type="input") | {"placeholder": "{{a}}"}
        self.assertEqual(self.lines(d, inp, "live"), ["", "AA"])
        tbl = block(type="table", label="T") | {"options": ["{{a}} | 1"]}
        self.assertEqual(self.lines(d, tbl, "live"), ["T", "AA | 1"])


class FollowTests(unittest.TestCase):
    def test_R10_no_events_gives_the_initial_screen(self):
        """R10(f)."""
        self.assertEqual(play.follow(two_screens(), []), "a")

    def test_R10_events_are_followed_in_order(self):
        """R10(f)."""
        self.assertEqual(play.follow(two_screens(), ["go"]), "b")

    def test_R10_stuck_event_is_an_error_naming_it(self):
        """R10(f)."""
        with self.assertRaises(WireframeError) as ctx:
            play.follow(two_screens(), ["nope"])
        self.assertIn("nope", str(ctx.exception))

    def test_R10_choice_must_be_resolved_with_an_id(self):
        """R10(f): EVENT=ID picks one of several competing transitions."""
        d = two_screens()
        d["states"].append(state("c"))
        d["transitions"].append(transition("t2", "a", "c", "go"))
        with self.assertRaises(WireframeError) as ctx:
            play.follow(d, ["go"])
        self.assertIn("go", str(ctx.exception))
        self.assertEqual(play.follow(d, ["go=t2"]), "c")


class RenderTests(unittest.TestCase):
    def test_R10_svg_has_canvas_size_and_background(self):
        """R10(c)."""
        d = two_screens()
        d["states"][0]["background"] = "#abcdef"
        out = render.render_screen(d, "a", "svg")
        self.assertTrue(out.startswith("<svg"))
        self.assertIn('width="800"', out)
        self.assertIn('height="600"', out)
        self.assertIn("#abcdef", out)

    def test_R10_block_is_drawn_at_its_position_and_size(self):
        """R10(c)."""
        out = render.render_screen(two_screens(), "a", "svg")
        self.assertRegex(out, r'<svg x="10" y="20" width="120" height="40"')

    def test_R10_style_fields_reach_the_picture(self):
        """R10(c): fill, border, radius, text colour, bold, opacity."""
        d = two_screens()
        d["states"][0]["blocks"][0]["look"] = {
            "fill": "#112233", "border_color": "#445566", "border_width": 3, "radius": 9,
            "text_color": "#778899", "font_weight": "bold", "opacity": 0.5}
        out = render.render_screen(d, "a", "svg")
        for needle in ("#112233", "#445566", 'stroke-width="3"', 'rx="9"', "#778899", "bold", 'opacity="0.5"'):
            self.assertIn(needle, out)

    def test_R10_hidden_blocks_are_skipped_and_disabled_ones_faded(self):
        """R10(c)."""
        d = two_screens()
        d["states"][0]["blocks"] += [
            block("h", "text", label="SECRET") | {"hidden": True},
            block("d", "button", label="Faded") | {"disabled": True}]
        out = render.render_screen(d, "a", "svg")
        self.assertNotIn("SECRET", out)
        self.assertIn("Faded", out)
        self.assertRegex(out, r'<svg[^>]*opacity="0\.5"[^>]*>(?:(?!</svg>).)*Faded')

    def test_R10_later_blocks_are_drawn_after_earlier_ones(self):
        """R10(c): file order is z-order."""
        d = two_screens()
        d["states"][0]["blocks"] = [block("one", label="FIRST"), block("two", label="SECOND")]
        out = render.render_screen(d, "a", "svg")
        self.assertLess(out.index("FIRST"), out.index("SECOND"))

    def test_R10_user_text_is_escaped(self):
        """R10(b): a label is text, never markup."""
        d = two_screens()
        d["states"][0]["blocks"][0]["label"] = '<script>alert("x")</script> & co'
        for fmt in ("svg", "html"):
            out = render.render_screen(d, "a", fmt)
            self.assertNotIn("<script", out)
            self.assertIn("&lt;script&gt;", out)
            self.assertIn("&amp; co", out)

    def test_R10_output_is_self_contained(self):
        """R10(b): no scripts, no external links or images."""
        for fmt in ("svg", "html"):
            out = render.render_screen(two_screens(), "b", fmt, "live")
            self.assertNotIn("<script", out)
            self.assertNotRegex(out, r"(?:src|href)\s*=\s*[\"']?(?:https?:)?//")
            self.assertNotIn("<img", out)

    def test_R10_html_wraps_the_drawing_in_a_page(self):
        """R10(a)."""
        out = render.render_screen(two_screens(), "a", "html")
        self.assertTrue(out.lstrip().lower().startswith("<!doctype html>"))
        self.assertIn("<svg", out)
        self.assertIn("<title>", out)

    def test_R10_same_input_gives_the_same_text(self):
        """R10(e)."""
        d = two_screens()
        for fmt in ("svg", "html"):
            self.assertEqual(render.render_screen(d, "a", fmt), render.render_screen(d, "a", fmt))

    def test_R11_debug_shows_tokens_and_live_shows_standins(self):
        """R11(e): the picture follows the data mode."""
        d = two_screens()
        self.assertIn("Hello {{user.name}}", render.render_screen(d, "b", "svg", "debug"))
        live = render.render_screen(d, "b", "svg", "live")
        self.assertIn("Hello Sam", live)
        self.assertNotIn("{{", live)

    def test_R10_bad_input_is_an_error(self):
        """R10(a): unknown screen, format or mode."""
        d = two_screens()
        for args in (("zzz", "svg"), ("a", "png"), ("a", "svg", "fancy")):
            with self.subTest(args=args), self.assertRaises(WireframeError):
                render.render_screen(d, *args)

    def test_R10_drawing_does_not_change_the_document(self):
        """R10(a): rendering only reads."""
        import copy
        d = two_screens()
        before = copy.deepcopy(d)
        render.render_screen(d, "a", "html", "live")
        self.assertEqual(d, before)


if __name__ == "__main__":
    unittest.main()
