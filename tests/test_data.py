"""R11: data standins. {{key}} tokens, the `data` table, debug and live mode.

`fill` is the one function that turns text with tokens into display text, so
most of these tests call it directly with plain strings.
"""
import unittest

from wireframe import data, model, ops
from wireframe.model import WireframeError
from helpers import block, doc, state


def with_data(table):
    d = doc([state("s", [block("b1", label="Total {{cart.total}}")])])
    d["data"] = table
    return d


class FindTokensTests(unittest.TestCase):
    def test_R11_finds_keys_in_order(self):
        """R11(b): every {{key}} is listed, in the order written."""
        self.assertEqual(data.find_tokens("Hi {{user.name}}, total {{cart.total}}"),
                         ["user.name", "cart.total"])

    def test_R11_spaces_inside_the_braces_are_allowed(self):
        """R11(b)."""
        self.assertEqual(data.find_tokens("{{ file.value }}"), ["file.value"])

    def test_R11_unclosed_or_non_key_braces_are_plain_text(self):
        """R11(b): `{{` without `}}`, or braces around a non-key, are not tokens."""
        for text in ("{{oops", "}} {{", "{{}}", "{{a b}}", "{{1abc}}", "{single}", "plain"):
            with self.subTest(text=text):
                self.assertEqual(data.find_tokens(text), [])


class FillTests(unittest.TestCase):
    def test_R11_debug_mode_returns_the_text_unchanged(self):
        """R11(c): debug shows tokens as written."""
        d = with_data({"cart.total": "$42"})
        self.assertEqual(data.fill(d, "Total {{cart.total}}", "debug"), "Total {{cart.total}}")

    def test_R11_live_mode_uses_the_table(self):
        """R11(c)."""
        d = with_data({"cart.total": "$42.00"})
        self.assertEqual(data.fill(d, "Total {{cart.total}}", "live"), "Total $42.00")

    def test_R11_live_mode_makes_a_standin_for_a_missing_key(self):
        """R11(c): `file.value` becomes 'File value' when the table has nothing for it."""
        d = doc([state("s")])
        self.assertEqual(data.fill(d, "{{file.value}}", "live"), "File value")
        self.assertEqual(data.fill(d, "{{user.email_address}}", "live"), "User email address")
        self.assertEqual(data.fill(d, "{{ship-to}}", "live"), "Ship to")

    def test_R11_text_without_tokens_is_never_changed(self):
        """R11(c)."""
        d = with_data({"a": "b"})
        for mode in data.MODES:
            self.assertEqual(data.fill(d, "Just text {not a token}", mode), "Just text {not a token}")

    def test_R11_replaced_text_is_not_searched_again(self):
        """R11(c): a sample that itself contains a token must not loop or expand."""
        d = with_data({"a": "{{b}}", "b": "BOOM"})
        self.assertEqual(data.fill(d, "{{a}}", "live"), "{{b}}")

    def test_R11_the_same_key_twice_is_replaced_twice(self):
        """R11(c)."""
        d = with_data({"k": "X"})
        self.assertEqual(data.fill(d, "{{k}}-{{k}}", "live"), "X-X")

    def test_R11_unknown_mode_is_an_error(self):
        """R11(c)."""
        with self.assertRaises(WireframeError) as ctx:
            data.fill(doc([state("s")]), "x", "fancy")
        self.assertIn("fancy", str(ctx.exception))

    def test_R11_a_document_without_data_still_works(self):
        """R11(a): Round 1 and 2 files have no `data` field."""
        self.assertNotIn("data", doc([state("s")]))
        self.assertEqual(data.fill(doc([state("s")]), "{{a.b}}", "live"), "A b")


class ValidationTests(unittest.TestCase):
    def test_R11_a_valid_table_is_accepted(self):
        """R11(a)."""
        self.assertEqual(model.validate(with_data({"cart.total": "$42", "user.name": ""})), [])

    def test_R11_old_files_without_data_are_valid(self):
        """R11(a): ADR 0006, new fields are optional."""
        self.assertEqual(model.validate(doc([state("s")])), [])

    def test_R11_errors_name_the_path(self):
        """R11(a)."""
        self.assertTrue(any("data" in e and "object" in e for e in model.validate(with_data([1]))))
        bad_key = model.validate(with_data({"cart total": "x"}))
        self.assertTrue(any(e.startswith("data.cart total") for e in bad_key), bad_key)
        bad_value = model.validate(with_data({"cart.total": 42}))
        self.assertTrue(any(e.startswith("data.cart.total") and "text" in e for e in bad_value), bad_value)


class DataOpsTests(unittest.TestCase):
    def test_R11_set_data_adds_then_replaces_a_key(self):
        """R11(d)."""
        d = ops.set_data(doc([state("s")]), "cart.total", "$1")
        self.assertEqual(d["data"], {"cart.total": "$1"})
        d = ops.set_data(d, "cart.total", "$2")
        self.assertEqual(d["data"], {"cart.total": "$2"})

    def test_R11_set_data_rejects_a_bad_key_and_changes_nothing(self):
        """R11(d)."""
        before = doc([state("s")])
        with self.assertRaises(WireframeError):
            ops.set_data(before, "not a key", "x")
        self.assertNotIn("data", before)

    def test_R11_delete_data_removes_the_key_and_then_the_field(self):
        """R11(d): the last delete takes `data` out, so an unused file keeps its old shape."""
        d = ops.set_data(ops.set_data(doc([state("s")]), "a", "1"), "b", "2")
        d = ops.delete_data(d, "a")
        self.assertEqual(d["data"], {"b": "2"})
        d = ops.delete_data(d, "b")
        self.assertNotIn("data", d)

    def test_R11_delete_data_unknown_key_is_an_error(self):
        """R11(d)."""
        with self.assertRaises(WireframeError) as ctx:
            ops.delete_data(doc([state("s")]), "nope")
        self.assertIn("nope", str(ctx.exception))

    def test_R11_data_ops_do_not_change_the_input(self):
        """R1(b) still holds: every op works on a copy."""
        before = with_data({"a": "1"})
        ops.set_data(before, "b", "2")
        ops.delete_data(before, "a")
        self.assertEqual(before["data"], {"a": "1"})

    def test_R11_the_ops_are_registered_for_cli_http_and_browser(self):
        """CLAUDE.md: every edit is an op in OPS."""
        d = ops.apply_op(doc([state("s")]), {"op": "set_data", "key": "a.b", "value": "x"})
        self.assertEqual(d["data"], {"a.b": "x"})
        d = ops.apply_op(d, {"op": "delete_data", "key": "a.b"})
        self.assertNotIn("data", d)


if __name__ == "__main__":
    unittest.main()
