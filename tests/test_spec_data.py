"""R11(e), R11(h): data standins in the spec sheets and the authoring guide."""
import unittest

from wireframe import checks, example, model, spec
from wireframe.model import WireframeError
from helpers import block, doc, state


def tokened():
    b = block("b1", "text", label="Total {{cart.total}}") | {"placeholder": "{{ph}}", "value": "{{v}}",
                                                              "options": ["{{o}}"]}
    d = doc([state("s", [b])])
    d["data"] = {"cart.total": "$42.00", "ph": "PH", "v": "VV"}
    return d


class ImageSpecTests(unittest.TestCase):
    def test_R11_debug_keeps_tokens_and_live_fills_every_text_field(self):
        """R11(e): label, placeholder, value and options."""
        d = tokened()
        debug = spec.export_spec(d, "image")
        self.assertIn("{{cart.total}}", debug)
        live = spec.export_spec(d, "image", data="live")
        for text in ("Total $42.00", "PH", "VV", "O"):
            self.assertIn(text, live)
        self.assertNotIn("{{", live)

    def test_R11_default_mode_is_debug(self):
        """R11(e): old callers get old output."""
        d = tokened()
        self.assertEqual(spec.export_spec(d, "image"), spec.export_spec(d, "image", data="debug"))

    def test_R11_unknown_mode_is_an_error(self):
        """R11(e)."""
        with self.assertRaises(WireframeError):
            spec.export_spec(tokened(), "image", data="fancy")


class CoderSpecTests(unittest.TestCase):
    def test_R11_coder_spec_keeps_tokens_even_in_live_mode(self):
        """R11(e): a coder needs the key, not the sample."""
        d = tokened()
        for mode in ("debug", "live"):
            out = spec.export_spec(d, "coder", data=mode)
            self.assertIn("Total {{cart.total}}", out)

    def test_R11_coder_spec_lists_sample_data_only_when_there_is_some(self):
        """R11(e)."""
        out = spec.export_spec(tokened(), "coder")
        self.assertIn("## Sample data", out)
        self.assertIn("`cart.total`", out)
        self.assertIn("$42.00", out)
        self.assertNotIn("## Sample data", spec.export_spec(doc([state("s")]), "coder"))


class GuideAndExampleTests(unittest.TestCase):
    def test_R11_guide_explains_tokens_and_data(self):
        """R11(h)."""
        guide = spec.authoring_guide()
        self.assertIn("{{", guide)
        self.assertIn("`data`", guide)
        self.assertIn("live", guide)

    def test_R11_example_uses_a_token_and_is_still_clean(self):
        """R11(h): the example stays valid and finding-free."""
        ex = example.example_wireframe()
        self.assertTrue(ex.get("data"))
        self.assertTrue(any("{{" in b["label"] for s in ex["states"] for b in s["blocks"]))
        self.assertEqual(model.validate(ex), [])
        self.assertEqual(checks.check(ex), [])


if __name__ == "__main__":
    unittest.main()
