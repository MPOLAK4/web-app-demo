import copy
import unittest

from wireframe import ops
from wireframe.model import WireframeError, validate
from helpers import block, doc, state, transition


def sample():
    return doc(
        [state("a", [block("b1", label="One"), block("b2", label="Two")]), state("b")],
        [transition("t1", "a", "b", "go"), transition("t2", "b", "a", "back")],
    )


def find_block(d, state_id, block_id):
    st = next(s for s in d["states"] if s["id"] == state_id)
    return next(b for b in st["blocks"] if b["id"] == block_id)


class BlockOpsTests(unittest.TestCase):
    def test_R1_add_block_creates_it_with_a_fresh_id(self):
        """R1(b): add_block puts a new block in the chosen state."""
        d = ops.add_block(sample(), "a", "button", x=5, y=6, w=70, h=30, label="Go")
        blocks = next(s for s in d["states"] if s["id"] == "a")["blocks"]
        self.assertEqual(len(blocks), 3)
        new = blocks[-1]
        self.assertNotIn(new["id"], ("b1", "b2"))
        self.assertEqual((new["type"], new["x"], new["y"], new["w"], new["h"], new["label"]),
                         ("button", 5, 6, 70, 30, "Go"))
        self.assertEqual(validate(d), [])

    def test_R1_add_block_gets_an_empty_info_list_by_default(self):
        d = ops.add_block(sample(), "a", "text")
        self.assertEqual(d["states"][0]["blocks"][-1]["info"], [])

    def test_R1_moving_a_block_changes_only_x_and_y(self):
        """R1(b): 'move' is update_block with x and y."""
        d = ops.update_block(sample(), "a", "b1", x=300, y=200)
        b = find_block(d, "a", "b1")
        self.assertEqual((b["x"], b["y"], b["w"], b["h"], b["label"]), (300, 200, 100, 40, "One"))

    def test_R1_resizing_a_block_changes_only_w_and_h(self):
        d = ops.update_block(sample(), "a", "b1", w=250, h=90)
        b = find_block(d, "a", "b1")
        self.assertEqual((b["x"], b["y"], b["w"], b["h"]), (0, 0, 250, 90))

    def test_R1_renaming_and_retyping_a_block(self):
        d = ops.update_block(sample(), "a", "b1", label="Pay now", type="button", event="pay")
        b = find_block(d, "a", "b1")
        self.assertEqual((b["label"], b["type"], b["event"]), ("Pay now", "button", "pay"))

    def test_R5_info_and_note_can_be_edited(self):
        """R5(a): info keys and the note are editable."""
        d = ops.update_block(sample(), "a", "b1", info=["cart.total"], note="Sum of items")
        b = find_block(d, "a", "b1")
        self.assertEqual((b["info"], b["note"]), (["cart.total"], "Sum of items"))

    def test_R1_delete_block(self):
        d = ops.delete_block(sample(), "a", "b1")
        self.assertEqual([b["id"] for b in d["states"][0]["blocks"]], ["b2"])

    def test_R1_input_document_is_never_modified(self):
        """R1(b): ops return a new document and leave the old one untouched."""
        original = sample()
        snapshot = copy.deepcopy(original)
        ops.update_block(original, "a", "b1", x=999)
        ops.add_block(original, "a", "text")
        ops.delete_block(original, "a", "b2")
        self.assertEqual(original, snapshot)

    def test_R1_invalid_edit_raises_and_changes_nothing(self):
        """R1(b): a width of 0 is rejected; the original is unchanged."""
        original = sample()
        snapshot = copy.deepcopy(original)
        with self.assertRaises(WireframeError):
            ops.update_block(original, "a", "b1", w=0)
        self.assertEqual(original, snapshot)

    def test_R1_unknown_state_or_block_raises(self):
        with self.assertRaises(WireframeError):
            ops.update_block(sample(), "nope", "b1", x=1)
        with self.assertRaises(WireframeError):
            ops.update_block(sample(), "a", "nope", x=1)
        with self.assertRaises(WireframeError):
            ops.delete_block(sample(), "a", "nope")

    def test_R1_the_id_of_a_block_cannot_be_changed(self):
        """'id' names WHICH block to edit, so no op can express an id change."""
        with self.assertRaises(WireframeError):
            ops.apply_op(sample(), {"op": "update_block", "state": "a", "id": "b1", "new_id": "other"})

    def test_R1_unknown_field_is_rejected(self):
        with self.assertRaises(WireframeError):
            ops.update_block(sample(), "a", "b1", colour="red")


class StateOpsTests(unittest.TestCase):
    def test_R1_add_state_with_generated_id(self):
        d = ops.add_state(sample(), "Settings")
        self.assertEqual(len(d["states"]), 3)
        new = d["states"][-1]
        self.assertEqual((new["title"], new["blocks"], new["final"]), ("Settings", [], False))
        self.assertNotIn(new["id"], ("a", "b"))

    def test_R1_add_state_with_a_chosen_id(self):
        d = ops.add_state(sample(), "Done", id="done", final=True)
        self.assertEqual((d["states"][-1]["id"], d["states"][-1]["final"]), ("done", True))

    def test_R1_add_state_with_a_taken_id_raises(self):
        with self.assertRaises(WireframeError):
            ops.add_state(sample(), "Again", id="a")

    def test_R1_update_state_title_and_final(self):
        d = ops.update_state(sample(), "b", title="Receipt", final=True)
        self.assertEqual((d["states"][1]["title"], d["states"][1]["final"]), ("Receipt", True))

    def test_R1_state_id_cannot_be_changed(self):
        """Spec: a state's id is fixed at creation (change its title instead)."""
        with self.assertRaises(WireframeError):
            ops.apply_op(sample(), {"op": "update_state", "id": "b", "new_id": "c"})

    def test_R1_deleting_a_state_deletes_its_transitions(self):
        """R1(d): no transition may be left pointing into or out of a deleted state."""
        d = ops.delete_state(sample(), "b")
        self.assertEqual([s["id"] for s in d["states"]], ["a"])
        self.assertEqual(d["transitions"], [])

    def test_R1_deleting_the_initial_state_picks_another_or_clears_it(self):
        d = ops.delete_state(sample(), "a")
        self.assertEqual(d["initial"], "b")
        d = ops.delete_state(d, "b")
        self.assertEqual(d["initial"], "")
        self.assertEqual(validate(d), [])

    def test_R1_update_wireframe_name_initial_and_canvas(self):
        d = ops.update_wireframe(sample(), name="Shop", initial="b", width=1024, height=768)
        self.assertEqual((d["name"], d["initial"], d["canvas"]), ("Shop", "b", {"width": 1024, "height": 768}))


class TransitionOpsTests(unittest.TestCase):
    def test_R1_add_transition(self):
        d = ops.add_transition(sample(), "a", "b", "other", guard="logged in")
        new = d["transitions"][-1]
        self.assertEqual((new["source"], new["target"], new["event"], new["guard"]),
                         ("a", "b", "other", "logged in"))
        self.assertNotIn(new["id"], ("t1", "t2"))

    def test_R4_a_transition_to_a_missing_state_is_allowed_so_it_can_be_checked(self):
        """R4: the editor must be able to create the mistake the checker finds."""
        d = ops.add_transition(sample(), "a", "ghost", "x")
        self.assertEqual(d["transitions"][-1]["target"], "ghost")

    def test_R1_update_transition(self):
        d = ops.update_transition(sample(), "t1", event="next", guard="valid")
        self.assertEqual((d["transitions"][0]["event"], d["transitions"][0]["guard"]), ("next", "valid"))

    def test_R1_delete_transition(self):
        d = ops.delete_transition(sample(), "t1")
        self.assertEqual([t["id"] for t in d["transitions"]], ["t2"])

    def test_R1_unknown_transition_raises(self):
        with self.assertRaises(WireframeError):
            ops.delete_transition(sample(), "zzz")


class ApplyOpTests(unittest.TestCase):
    """apply_op is the single entry point used by the CLI and the HTTP API (R1(c))."""

    def test_R1_apply_op_runs_a_named_edit(self):
        d = ops.apply_op(sample(), {"op": "update_block", "state": "a", "id": "b1", "x": 42})
        self.assertEqual(find_block(d, "a", "b1")["x"], 42)

    def test_R1_apply_op_add_block(self):
        d = ops.apply_op(sample(), {"op": "add_block", "state": "b", "type": "text", "label": "Hi"})
        self.assertEqual(d["states"][1]["blocks"][0]["label"], "Hi")

    def test_R1_apply_op_unknown_op_raises(self):
        with self.assertRaises(WireframeError) as ctx:
            ops.apply_op(sample(), {"op": "explode"})
        self.assertIn("explode", str(ctx.exception))

    def test_R1_apply_op_without_op_name_raises(self):
        with self.assertRaises(WireframeError):
            ops.apply_op(sample(), {"state": "a"})

    def test_R1_apply_op_with_missing_or_extra_arguments_raises_a_readable_error(self):
        with self.assertRaises(WireframeError):
            ops.apply_op(sample(), {"op": "delete_block", "state": "a"})  # no id
        with self.assertRaises(WireframeError):
            ops.apply_op(sample(), {"op": "delete_block", "state": "a", "id": "b1", "bogus": 1})

    def test_R1_apply_op_does_not_modify_its_inputs(self):
        original, op = sample(), {"op": "delete_block", "state": "a", "id": "b1"}
        snap = (copy.deepcopy(original), copy.deepcopy(op))
        ops.apply_op(original, op)
        self.assertEqual((original, op), snap)


if __name__ == "__main__":
    unittest.main()
