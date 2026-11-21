"""R5: blocks carry information, so duplicated information can be detected."""
import unittest

from wireframe import checks
from helpers import block, codes, doc, state


def one_state(*blocks):
    return doc([state("a", blocks, final=True)])


def findings_with(code, findings):
    return [f for f in findings if f["code"] == code]


class DuplicateInfoTests(unittest.TestCase):
    def test_R5_same_info_key_twice_on_one_screen_is_flagged(self):
        """R5(b): the order total is shown in two places."""
        d = one_state(
            block("t1", x=0, y=0, label="Total", info=("cart.total",)),
            block("t2", x=0, y=100, label="Amount due", info=("cart.total",)),
        )
        found = findings_with("duplicate-info", checks.check(d))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "warning")
        self.assertEqual(found[0]["blocks"], ["t1", "t2"])
        self.assertIn("cart.total", found[0]["message"])

    def test_R5_different_keys_are_not_duplicates(self):
        d = one_state(
            block("t1", x=0, y=0, label="Total", info=("cart.total",)),
            block("t2", x=0, y=100, label="Tax", info=("cart.tax",)),
        )
        self.assertNotIn("duplicate-info", codes(checks.check(d)))

    def test_R5_info_keys_compare_ignoring_case_and_whitespace(self):
        """R5(f)."""
        d = one_state(
            block("t1", x=0, y=0, label="Total", info=("Cart.Total",)),
            block("t2", x=0, y=100, label="Sum", info=("  cart.total ",)),
        )
        self.assertIn("duplicate-info", codes(checks.check(d)))

    def test_R5_same_key_on_different_screens_is_fine(self):
        """R5(e): those screens are never visible together."""
        d = doc([
            state("a", [block("t1", label="Total", info=("cart.total",))], final=True),
            state("b", [block("t2", label="Total", info=("cart.total",))], final=True),
        ])
        found = checks.check(d)
        self.assertNotIn("duplicate-info", codes(found))
        self.assertNotIn("duplicate-label", codes(found))

    def test_R5_three_blocks_sharing_a_key_give_one_finding_naming_all(self):
        d = one_state(
            block("t1", x=0, y=0, label="A", info=("k",)),
            block("t2", x=0, y=100, label="B", info=("k",)),
            block("t3", x=0, y=200, label="C", info=("k",)),
        )
        found = findings_with("duplicate-info", checks.check(d))
        self.assertEqual([f["blocks"] for f in found], [["t1", "t2", "t3"]])

    def test_R5_one_block_listing_a_key_twice_is_not_a_duplicate(self):
        """Duplication means two *blocks*, not a repeated entry in one list."""
        d = one_state(block("t1", label="A", info=("k", "k")))
        self.assertNotIn("duplicate-info", codes(checks.check(d)))


class DuplicateLabelTests(unittest.TestCase):
    def test_R5_same_label_twice_on_one_screen_is_flagged(self):
        """R5(c): two 'Submit' buttons."""
        d = one_state(
            block("b1", x=0, y=0, type="button", label="Submit", info=("a.one",), event="x"),
            block("b2", x=0, y=100, type="button", label="Submit", info=("a.two",), event="y"),
        )
        found = findings_with("duplicate-label", checks.check(d))
        self.assertEqual([f["blocks"] for f in found], [["b1", "b2"]])

    def test_R5_labels_compare_ignoring_case_spacing_and_punctuation(self):
        """R5(c)."""
        d = one_state(
            block("b1", x=0, y=0, label="Please sign in!", info=("a",)),
            block("b2", x=0, y=100, label="  please   SIGN in ", info=("b",)),
        )
        self.assertIn("duplicate-label", codes(checks.check(d)))

    def test_R5_empty_labels_are_ignored(self):
        """R5(c): lots of unlabeled containers are not 'duplicates'."""
        d = one_state(
            block("c1", type="container", x=0, y=0, label=""),
            block("c2", type="container", x=0, y=200, label=""),
            block("c3", type="text", x=0, y=400, label="!!!", info=("a",)),
            block("c4", type="text", x=0, y=500, label="???", info=("b",)),
        )
        self.assertNotIn("duplicate-label", codes(checks.check(d)))


class MissingInfoTests(unittest.TestCase):
    def test_R5_block_with_no_info_and_no_note_is_flagged(self):
        """R5(d): a reader cannot tell what it conveys."""
        d = one_state(block("t1", label="Mystery", info=()))
        found = findings_with("missing-info", checks.check(d))
        self.assertEqual([f["blocks"] for f in found], [["t1"]])
        self.assertEqual(found[0]["severity"], "warning")

    def test_R5_a_note_alone_is_enough(self):
        d = one_state(block("t1", label="Mystery", info=(), note="Explains the refund policy"))
        self.assertNotIn("missing-info", codes(checks.check(d)))

    def test_R5_info_keys_alone_are_enough(self):
        d = one_state(block("t1", label="Total", info=("cart.total",)))
        self.assertNotIn("missing-info", codes(checks.check(d)))

    def test_R5_a_whitespace_only_note_does_not_count(self):
        d = one_state(block("t1", label="Mystery", info=(), note="   "))
        self.assertIn("missing-info", codes(checks.check(d)))

    def test_R5_containers_are_exempt(self):
        """R5(d): a container groups things; it conveys nothing itself."""
        d = one_state(block("c1", type="container", label="", info=()))
        self.assertNotIn("missing-info", codes(checks.check(d)))


if __name__ == "__main__":
    unittest.main()
