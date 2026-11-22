"""Styles and the new block fields (R6, R7, R8): shape checks and resolution.

These tests only look at the data layer. A "style" is a small dict such as
{"fill": "#ff0000", "radius": 8}; a block can name a shared one (`style`) and
override fields (`look`).
"""
import copy
import unittest

from wireframe import model, styles
from helpers import block, doc, state


def with_block(**fields):
    b = block("b1", "button", label="Go")
    b.update(fields)
    return doc([state("s", [b])])


def errors_for(**fields):
    return model.validate(with_block(**fields))


class StyleFieldTests(unittest.TestCase):
    def test_R6_style_has_exactly_eleven_fields(self):
        """R6(a): the style vocabulary is fixed, so every spec sheet uses the same words."""
        self.assertEqual(set(styles.STYLE_FIELDS), {
            "fill", "text_color", "border_color", "border_width", "radius", "padding",
            "font_size", "font_weight", "align", "opacity", "shadow"})

    def test_R6_valid_look_is_accepted(self):
        """R6(a)."""
        look = {"fill": "#fff", "text_color": "#112233", "border_color": "#000", "border_width": 0,
                "radius": 8, "padding": 4, "font_size": 16, "font_weight": "bold",
                "align": "right", "opacity": 0.5, "shadow": True}
        self.assertEqual(errors_for(look=look), [])

    def test_R6_bad_values_are_reported_with_their_path(self):
        """R6(a): each bad value is named by its path."""
        cases = {
            "fill": "red",              # only hex colours
            "text_color": "#12",        # wrong length
            "border_width": -1,
            "radius": 1.5,
            "font_size": 0,
            "font_weight": "heavy",
            "align": "middle",
            "opacity": 2,
            "shadow": "yes",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                errs = errors_for(look={field: value})
                self.assertEqual(len(errs), 1, errs)
                self.assertIn(f"states[0].blocks[0].look.{field}:", errs[0])

    def test_R6_booleans_are_not_numbers(self):
        """R6(a): in Python True == 1, so `radius: true` must be refused explicitly."""
        self.assertTrue(errors_for(look={"radius": True}))
        self.assertTrue(errors_for(look={"opacity": True}))

    def test_R6_unknown_style_field_is_rejected(self):
        """R6(a): a typo like `colour` is an error, not silently ignored."""
        errs = errors_for(look={"colour": "#fff"})
        self.assertIn("states[0].blocks[0].look: unknown field 'colour'", errs)

    def test_R6_look_must_be_an_object(self):
        """R6(a)."""
        self.assertTrue(errors_for(look=[1]))

    def test_R6_opacity_accepts_whole_and_fractional_numbers(self):
        """R6(a)."""
        for value in (0, 1, 0.25):
            self.assertEqual(errors_for(look={"opacity": value}), [], value)


class ResolveTests(unittest.TestCase):
    def test_R6_block_with_no_style_fields_still_resolves_fully(self):
        """R6(b): a Round 1 block gets all eleven fields from the defaults."""
        resolved = styles.resolve_style(with_block(), block("b1", "text"))
        self.assertEqual(set(resolved), set(styles.STYLE_FIELDS))

    def test_R6_defaults_depend_on_block_type(self):
        """R6(b): a button looks different from plain text by default."""
        d = with_block()
        self.assertNotEqual(styles.resolve_style(d, {"type": "button"}),
                            styles.resolve_style(d, {"type": "text"}))

    def test_R7_layers_apply_in_order_default_then_named_then_look(self):
        """R7(a)/R6(b): later layers win."""
        d = with_block()
        d["styles"] = {"primary": {"fill": "#111111", "radius": 10}}
        b = {"type": "button", "style": "primary", "look": {"radius": 3}}
        resolved = styles.resolve_style(d, b)
        self.assertEqual(resolved["fill"], "#111111")                 # from the named style
        self.assertEqual(resolved["radius"], 3)                       # look beats the style
        self.assertEqual(resolved["font_size"], styles.default_style("button")["font_size"])

    def test_R7_unknown_style_name_resolves_without_crashing(self):
        """R7(c): the checker reports it; resolving must still work."""
        resolved = styles.resolve_style(with_block(), {"type": "text", "style": "nope"})
        self.assertEqual(resolved, styles.default_style("text"))

    def test_R6_resolve_does_not_change_its_inputs(self):
        """R6(b): pure function."""
        d = with_block(look={"radius": 2})
        before = copy.deepcopy(d)
        styles.resolve_style(d, d["states"][0]["blocks"][0])
        self.assertEqual(d, before)

    def test_R6_default_style_returns_a_copy(self):
        """R6(b): changing the result must not corrupt the built-in table."""
        styles.default_style("button")["fill"] = "#000000"
        self.assertNotEqual(styles.default_style("button")["fill"], "#000000")


class DocumentStylesTests(unittest.TestCase):
    def test_R7_named_styles_validate(self):
        """R7(a)."""
        d = with_block()
        d["styles"] = {"primary": {"fill": "#2a6cf0"}}
        self.assertEqual(model.validate(d), [])

    def test_R7_bad_named_style_reports_its_path(self):
        """R7(a)."""
        d = with_block()
        d["styles"] = {"primary": {"fill": "blue"}, "": {}}
        errs = model.validate(d)
        self.assertIn("styles.primary.fill: must be a colour like #fff or #2a6cf0", errs)
        self.assertTrue(any(e.startswith("styles:") and "name" in e for e in errs))

    def test_R7_styles_must_be_an_object(self):
        """R7(a)."""
        d = with_block()
        d["styles"] = ["primary"]
        self.assertEqual(model.validate(d), ["styles: must be an object of name -> style"])

    def test_R7_block_style_must_be_a_string(self):
        """R7(a)."""
        self.assertTrue(errors_for(style=3))

    def test_R7_round1_files_without_new_fields_stay_valid(self):
        """Compatibility rule: every Round 2 field is optional."""
        self.assertEqual(model.validate(model.new_wireframe()), [])
        d = doc([state("s", [block("b1", "button")])])
        for field in ("style", "look", "placeholder", "options", "value", "disabled", "hidden", "required"):
            self.assertNotIn(field, d["states"][0]["blocks"][0])
        self.assertEqual(model.validate(d), [])


class NewBlockFieldTests(unittest.TestCase):
    def test_R8_new_block_types_are_valid(self):
        """R8(a)."""
        new = ("textarea", "checkbox", "radio", "toggle", "select", "slider", "tabs", "card",
               "table", "modal", "icon", "divider", "link", "badge", "avatar")
        self.assertEqual(len(model.BLOCK_TYPES), 8 + len(new))
        for t in new:
            with self.subTest(type=t):
                self.assertIn(t, model.BLOCK_TYPES)
                self.assertEqual(model.validate(doc([state("s", [block("b1", t)])])), [])

    def test_R8_every_type_has_a_default_style(self):
        """R6(b)/R8(a): a new type without defaults would crash the exports."""
        for t in model.BLOCK_TYPES:
            with self.subTest(type=t):
                self.assertEqual(set(styles.default_style(t)), set(styles.STYLE_FIELDS))

    def test_R8_block_properties_validate(self):
        """R8(b)."""
        self.assertEqual(errors_for(placeholder="Search", options=["a", "b"], value="a",
                                    disabled=True, hidden=False, required=True), [])

    def test_R8_bad_block_properties_are_reported(self):
        """R8(b)."""
        for field, value in (("placeholder", 1), ("value", None), ("options", "a,b"),
                             ("options", [""]), ("disabled", "no"), ("hidden", 0), ("required", None)):
            with self.subTest(field=field, value=value):
                errs = errors_for(**{field: value})
                self.assertEqual(len(errs), 1, errs)
                self.assertIn(f"states[0].blocks[0].{field}:", errs[0])

    def test_R8_screen_background_validates(self):
        """R8(c)."""
        d = with_block()
        d["states"][0]["background"] = "#eeeeee"
        self.assertEqual(model.validate(d), [])
        d["states"][0]["background"] = "grey"
        self.assertEqual(model.validate(d), ["states[0].background: must be a colour like #fff or #2a6cf0"])

    def test_R8_device_presets(self):
        """R8(c)."""
        self.assertEqual(model.DEVICE_PRESETS["phone"], (390, 844))
        self.assertEqual(model.DEVICE_PRESETS["tablet"], (820, 1180))
        self.assertEqual(model.DEVICE_PRESETS["desktop"], (1280, 800))


if __name__ == "__main__":
    unittest.main()
