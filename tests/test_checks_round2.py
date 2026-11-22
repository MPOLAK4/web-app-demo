"""Round 2 design checks: styles (R6(f), R7(c)) and the new block types (R8)."""
import unittest

from wireframe import checks
from helpers import block, codes, doc, state, transition


def one(blocks, styles=None):
    d = doc([state("s", blocks, final=True)])
    if styles is not None:
        d["styles"] = styles
    return d


def styled(**kw):
    b = block(**kw)
    b["look"] = {"fill": "#ffffff"}
    return b


class StyleCheckTests(unittest.TestCase):
    def test_R6_missing_style_is_a_warning(self):
        """R6(f): no named style and no look."""
        found = [f for f in checks.check(one([block("a")])) if f["code"] == "missing-style"]
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["severity"], found[0]["blocks"]), ("warning", ["a"]))

    def test_R6_look_or_style_silences_missing_style(self):
        """R6(f)."""
        b = block("b")
        b["style"] = "p"
        d = one([styled(id="a"), b], styles={"p": {}})
        self.assertNotIn("missing-style", codes(checks.check(d)))

    def test_R6_an_empty_look_still_counts_as_missing(self):
        """R6(f): `look: {}` states no choice."""
        b = block("a")
        b["look"] = {}
        self.assertIn("missing-style", codes(checks.check(one([b]))))

    def test_R7_unknown_style_is_an_error(self):
        """R7(c)."""
        b = block("a")
        b["style"] = "ghost"
        found = [f for f in checks.check(one([b])) if f["code"] == "unknown-style"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "error")
        self.assertEqual(found[0]["blocks"], ["a"])

    def test_R7_unknown_style_is_not_also_reported_as_missing(self):
        """R7(c): one problem, one finding."""
        b = block("a")
        b["style"] = "ghost"
        self.assertNotIn("missing-style", codes(checks.check(one([b]))))

    def test_R7_unused_style_is_a_warning(self):
        """R7(c)."""
        found = [f for f in checks.check(one([styled(id="a")], styles={"p": {}}))
                 if f["code"] == "unused-style"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "warning")
        self.assertIn("p", found[0]["message"])

    def test_R7_used_style_is_not_unused(self):
        """R7(c): use on any screen counts."""
        b = block("a", event="go")
        b["style"] = "p"
        d = doc([state("s", [b]), state("t", final=True)], [transition("t1", "s", "t", "go")])
        d["styles"] = {"p": {}}
        self.assertNotIn("unused-style", codes(checks.check(d)))

    def test_R7_new_codes_are_in_the_rule_table(self):
        """The guide is generated from RULES, so the codes must be listed."""
        self.assertEqual(checks.RULES["missing-style"][0], "warning")
        self.assertEqual(checks.RULES["unknown-style"][0], "error")
        self.assertEqual(checks.RULES["unused-style"][0], "warning")


class NewTypeCheckTests(unittest.TestCase):
    def test_R8_hidden_blocks_do_not_overlap(self):
        """R8(b): a hidden block is not drawn, so it cannot collide."""
        a, b = styled(id="a", x=0, y=0), styled(id="b", x=10, y=10)
        b["hidden"] = True
        self.assertNotIn("overlap", codes(checks.check(one([a, b]))))
        b["hidden"] = False
        self.assertIn("overlap", codes(checks.check(one([a, b]))))

    def test_R8_card_and_modal_may_hold_blocks_like_a_container(self):
        """R8(a)."""
        for t in ("container", "card", "modal"):
            with self.subTest(type=t):
                outer = styled(id="o", type=t, x=0, y=0, w=300, h=200)
                inner = styled(id="i", x=10, y=10)
                self.assertNotIn("overlap", codes(checks.check(one([outer, inner]))))

    def test_R8_other_types_still_overlap(self):
        """R8(a): only holder types are allowed to contain others."""
        outer = styled(id="o", type="table", x=0, y=0, w=300, h=200)
        self.assertIn("overlap", codes(checks.check(one([outer, styled(id="i", x=10, y=10)]))))

    def test_R8_link_without_event_is_like_a_button_without_event(self):
        """R8(a): a link is clickable, so it must go somewhere."""
        self.assertIn("button-without-event", codes(checks.check(one([styled(id="l", type="link")]))))

    def test_R8_card_modal_divider_need_no_info(self):
        """R8(a): they are structure, like a container."""
        for t in ("card", "modal", "divider", "container"):
            with self.subTest(type=t):
                b = styled(id="x", type=t, info=())
                self.assertNotIn("missing-info", codes(checks.check(one([b]))))

    def test_R8_text_without_info_is_still_reported(self):
        """R8(a): the exemption is not for everything."""
        self.assertIn("missing-info", codes(checks.check(one([styled(id="x", type="text", info=())]))))


if __name__ == "__main__":
    unittest.main()
