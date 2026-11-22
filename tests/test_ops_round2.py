"""Round 2 edit operations: shared styles (R7), screen/canvas options and block
tools (R8). All of them go through `apply_op`, like every edit (decision 0001).
"""
import copy
import unittest

from wireframe import ops, styles
from wireframe.model import WireframeError, validate
from helpers import block, doc, state


def base():
    return doc([state("s", [block("a", "button", label="A", info=("x.a",)),
                            block("b", "button", label="B", info=("x.b",)),
                            block("c", "text", label="C", info=("x.c",))]),
                state("t")])


def blocks(d, sid="s"):
    return next(s for s in d["states"] if s["id"] == sid)["blocks"]


def by_id(d, bid, sid="s"):
    return next(b for b in blocks(d, sid) if b["id"] == bid)


class StyleOpsTests(unittest.TestCase):
    def test_R7_ops_are_registered_for_every_front_end(self):
        """R7(b): CLI, HTTP and browser see the same op table."""
        for name in ("add_style", "update_style", "delete_style", "set_style",
                     "duplicate_block", "reorder_block", "move_blocks"):
            self.assertIn(name, ops.OPS)

    def test_R7_add_style_creates_a_named_style(self):
        """R7(b)."""
        d = ops.apply_op(base(), {"op": "add_style", "name": "primary", "style": {"fill": "#2a6cf0"}})
        self.assertEqual(d["styles"], {"primary": {"fill": "#2a6cf0"}})
        self.assertEqual(validate(d), [])

    def test_R7_add_style_without_fields_makes_an_empty_style(self):
        """R7(b)."""
        self.assertEqual(ops.add_style(base(), "plain")["styles"], {"plain": {}})

    def test_R7_add_style_refuses_duplicates_and_empty_names(self):
        """R7(b): names are the identity; two styles cannot share one."""
        d = ops.add_style(base(), "primary")
        with self.assertRaises(WireframeError):
            ops.add_style(d, "primary")
        with self.assertRaises(WireframeError):
            ops.add_style(base(), "  ")

    def test_R7_add_style_with_bad_field_changes_nothing(self):
        """R7(b)/R6(a): invalid edit raises and the old document is untouched."""
        d = base()
        before = copy.deepcopy(d)
        with self.assertRaises(WireframeError):
            ops.add_style(d, "bad", {"fill": "blue"})
        self.assertEqual(d, before)

    def test_R7_update_style_replaces_the_fields(self):
        """R7(b)."""
        d = ops.add_style(base(), "primary", {"fill": "#111", "radius": 4})
        d = ops.update_style(d, "primary", {"radius": 9})
        self.assertEqual(d["styles"]["primary"], {"radius": 9})

    def test_R7_update_unknown_style_is_an_error(self):
        """R7(b)."""
        with self.assertRaises(WireframeError):
            ops.update_style(base(), "ghost", {})

    def test_R7_changing_a_style_changes_every_block_that_uses_it(self):
        """R7(a)/(b): this is the point of sharing."""
        d = ops.add_style(base(), "primary", {"fill": "#111111"})
        d = ops.set_style(d, "s", ["a", "b"], "primary")
        d = ops.update_style(d, "primary", {"fill": "#222222"})
        self.assertEqual(styles.resolve_style(d, by_id(d, "a"))["fill"], "#222222")
        self.assertEqual(styles.resolve_style(d, by_id(d, "b"))["fill"], "#222222")
        self.assertNotEqual(styles.resolve_style(d, by_id(d, "c"))["fill"], "#222222")

    def test_R7_set_style_marks_several_blocks_at_once(self):
        """R7(b)."""
        d = ops.add_style(base(), "primary")
        d = ops.set_style(d, "s", ["a", "b"], "primary")
        self.assertEqual([b.get("style") for b in blocks(d)], ["primary", "primary", None])

    def test_R7_set_style_empty_name_clears_it(self):
        """R7(b)."""
        d = ops.add_style(base(), "primary")
        d = ops.set_style(d, "s", ["a"], "primary")
        d = ops.set_style(d, "s", ["a"], "")
        self.assertEqual(by_id(d, "a")["style"], "")

    def test_R7_set_style_refuses_unknown_style_or_block(self):
        """R7(b): an explicit 'mark these' that names nothing is a mistake worth stopping."""
        d = ops.add_style(base(), "primary")
        with self.assertRaises(WireframeError):
            ops.set_style(d, "s", ["a"], "ghost")
        with self.assertRaises(WireframeError):
            ops.set_style(d, "s", ["a", "zzz"], "primary")

    def test_R7_set_style_is_all_or_nothing(self):
        """R7(b): if one id is bad, the good ones must not be marked either."""
        d = ops.add_style(base(), "primary")
        before = copy.deepcopy(d)
        with self.assertRaises(WireframeError):
            ops.set_style(d, "s", ["a", "zzz"], "primary")
        self.assertEqual(d, before)

    def test_R7_delete_style_keeps_the_look_of_its_blocks(self):
        """R7(b): deleting a style must not silently restyle blocks."""
        d = ops.add_style(base(), "primary", {"fill": "#123456", "radius": 7})
        d = ops.update_block(d, "s", "a", look={"radius": 2})
        d = ops.set_style(d, "s", ["a", "b"], "primary")
        before_a = styles.resolve_style(d, by_id(d, "a"))
        before_b = styles.resolve_style(d, by_id(d, "b"))
        d = ops.delete_style(d, "primary")
        self.assertNotIn("primary", d["styles"])
        self.assertEqual(by_id(d, "a")["style"], "")
        self.assertEqual(styles.resolve_style(d, by_id(d, "a")), before_a)   # own look still wins
        self.assertEqual(styles.resolve_style(d, by_id(d, "b")), before_b)

    def test_R7_delete_unknown_style_is_an_error(self):
        """R7(b)."""
        with self.assertRaises(WireframeError):
            ops.delete_style(base(), "ghost")

    def test_R7_block_can_override_one_field_of_its_style(self):
        """R7(a): `look` through update_block."""
        d = ops.add_style(base(), "primary", {"fill": "#111111", "radius": 8})
        d = ops.set_style(d, "s", ["a"], "primary")
        d = ops.update_block(d, "s", "a", look={"radius": 1})
        resolved = styles.resolve_style(d, by_id(d, "a"))
        self.assertEqual((resolved["fill"], resolved["radius"]), ("#111111", 1))

    def test_R7_style_ops_work_through_apply_op_with_json_only(self):
        """R7(b)/(c) of R1: the op messages are plain JSON."""
        d = ops.apply_op(base(), {"op": "add_style", "name": "p", "style": {"radius": 3}})
        d = ops.apply_op(d, {"op": "set_style", "state": "s", "ids": ["a"], "style": "p"})
        self.assertEqual(by_id(d, "a")["style"], "p")

    def test_R7_ops_do_not_change_their_input(self):
        """R1(b) still holds for the new ops."""
        d = ops.add_style(base(), "primary")
        before = copy.deepcopy(d)
        ops.set_style(d, "s", ["a"], "primary")
        ops.delete_style(d, "primary")
        ops.update_style(d, "primary", {"radius": 1})
        self.assertEqual(d, before)


class NewFieldEditTests(unittest.TestCase):
    def test_R8_update_block_edits_the_new_properties(self):
        """R8(b)."""
        d = ops.update_block(base(), "s", "a", placeholder="p", options=["x", "y"], value="x",
                             disabled=True, hidden=True, required=True)
        b = by_id(d, "a")
        self.assertEqual((b["placeholder"], b["options"], b["value"], b["disabled"], b["hidden"], b["required"]),
                         ("p", ["x", "y"], "x", True, True, True))

    def test_R8_bad_property_value_is_refused(self):
        """R8(b)."""
        with self.assertRaises(WireframeError):
            ops.update_block(base(), "s", "a", hidden="yes")

    def test_R8_add_block_accepts_a_style_name(self):
        """R7(b): an AI or script can create a styled block in one op."""
        d = ops.add_style(base(), "primary")
        d = ops.add_block(d, "s", "button", style="primary")
        self.assertEqual(blocks(d)[-1]["style"], "primary")

    def test_R8_add_block_without_style_adds_no_new_fields(self):
        """Compatibility: a plain add_block still produces a Round 1 shaped block."""
        b = blocks(ops.add_block(base(), "s", "text"))[-1]
        self.assertNotIn("style", b)

    def test_R8_state_background(self):
        """R8(c)."""
        d = ops.update_state(base(), "s", background="#ddeeff")
        self.assertEqual(d["states"][0]["background"], "#ddeeff")
        with self.assertRaises(WireframeError):
            ops.update_state(base(), "s", background="blue")

    def test_R8_device_presets_set_the_canvas(self):
        """R8(c)."""
        for name, (w, h) in (("phone", (390, 844)), ("tablet", (820, 1180)), ("desktop", (1280, 800))):
            with self.subTest(preset=name):
                d = ops.apply_op(base(), {"op": "update_wireframe", "preset": name})
                self.assertEqual(d["canvas"], {"width": w, "height": h})

    def test_R8_unknown_preset_is_an_error_that_lists_the_choices(self):
        """R8(c)."""
        with self.assertRaises(WireframeError) as ctx:
            ops.update_wireframe(base(), preset="watch")
        self.assertIn("phone", str(ctx.exception))

    def test_R8_preset_then_explicit_width_wins(self):
        """R8(c): an explicit number given in the same op is more specific than a preset."""
        d = ops.update_wireframe(base(), preset="phone", width=500)
        self.assertEqual(d["canvas"], {"width": 500, "height": 844})


class BlockToolTests(unittest.TestCase):
    def test_R8_duplicate_block_copies_and_offsets(self):
        """R8(d): +20, +20, new id, same style, appended on top."""
        d = ops.add_style(base(), "primary")
        d = ops.set_style(d, "s", ["a"], "primary")
        d = ops.update_block(d, "s", "a", look={"radius": 5}, x=10, y=10)
        d = ops.duplicate_block(d, "s", "a")
        copy_ = blocks(d)[-1]
        orig = by_id(d, "a")
        self.assertNotIn(copy_["id"], {"a", "b", "c"})
        self.assertEqual((copy_["x"], copy_["y"]), (30, 30))
        self.assertEqual(copy_["style"], "primary")
        self.assertEqual(copy_["look"], {"radius": 5})
        self.assertIsNot(copy_["look"], orig["look"])          # a real copy, not shared
        self.assertEqual(len(blocks(d)), 4)

    def test_R8_duplicate_unknown_block_is_an_error(self):
        """R8(d)."""
        with self.assertRaises(WireframeError):
            ops.duplicate_block(base(), "s", "zzz")

    def test_R8_reorder_block_moves_in_the_stacking_order(self):
        """R8(d): the list order is the stacking order, last on top."""
        order = lambda d: [b["id"] for b in blocks(d)]
        self.assertEqual(order(ops.reorder_block(base(), "s", "a", "front")), ["b", "c", "a"])
        self.assertEqual(order(ops.reorder_block(base(), "s", "c", "back")), ["c", "a", "b"])
        self.assertEqual(order(ops.reorder_block(base(), "s", "b", "forward")), ["a", "c", "b"])
        self.assertEqual(order(ops.reorder_block(base(), "s", "b", "backward")), ["b", "a", "c"])

    def test_R8_reorder_at_the_edge_is_a_harmless_no_op(self):
        """R8(d): 'forward' on the top block is not an error."""
        order = lambda d: [b["id"] for b in blocks(d)]
        self.assertEqual(order(ops.reorder_block(base(), "s", "c", "forward")), ["a", "b", "c"])
        self.assertEqual(order(ops.reorder_block(base(), "s", "a", "backward")), ["a", "b", "c"])

    def test_R8_reorder_rejects_unknown_direction(self):
        """R8(d)."""
        with self.assertRaises(WireframeError) as ctx:
            ops.reorder_block(base(), "s", "a", "sideways")
        self.assertIn("front", str(ctx.exception))

    def test_R8_move_blocks_moves_several_together(self):
        """R8(d)."""
        d = base()
        for bid, (x, y) in {"a": (10, 10), "b": (50, 60)}.items():
            d = ops.update_block(d, "s", bid, x=x, y=y)
        d = ops.move_blocks(d, "s", ["a", "b"], 5, -3)
        self.assertEqual((by_id(d, "a")["x"], by_id(d, "a")["y"]), (15, 7))
        self.assertEqual((by_id(d, "b")["x"], by_id(d, "b")["y"]), (55, 57))
        self.assertEqual((by_id(d, "c")["x"], by_id(d, "c")["y"]), (0, 0))      # untouched

    def test_R8_move_blocks_needs_whole_numbers_and_real_ids(self):
        """R8(d): all-or-nothing, and a float is refused like everywhere else."""
        d = base()
        before = copy.deepcopy(d)
        with self.assertRaises(WireframeError):
            ops.move_blocks(d, "s", ["a", "zzz"], 5, 5)
        with self.assertRaises(WireframeError):
            ops.move_blocks(d, "s", ["a"], 1.5, 0)
        with self.assertRaises(WireframeError):
            ops.move_blocks(d, "s", "a", 1, 0)     # ids must be a list
        self.assertEqual(d, before)

    def test_R8_new_ops_keep_the_document_valid(self):
        """R8(d)."""
        d = ops.duplicate_block(base(), "s", "a")
        d = ops.reorder_block(d, "s", "a", "front")
        d = ops.move_blocks(d, "s", ["a"], 1, 1)
        self.assertEqual(validate(d), [])


if __name__ == "__main__":
    unittest.main()
