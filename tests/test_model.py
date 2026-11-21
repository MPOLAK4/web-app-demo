import copy
import json
import os
import tempfile
import unittest

from wireframe import model
from helpers import block, doc, state, transition


class ValidateTests(unittest.TestCase):
    """validate() checks the *shape* of a document (types, ids, unknown fields).
    It does not judge the flow; that is checks.py (R4)."""

    def test_R1_new_wireframe_is_valid(self):
        """R1(a): a freshly created wireframe passes validation."""
        self.assertEqual(model.validate(model.new_wireframe("Demo")), [])

    def test_R1_a_normal_document_is_valid(self):
        """R1(a): a hand-built document in the spec's shape is accepted."""
        d = doc([state("a", [block()])], [transition("t1", "a", "a", "go")])
        self.assertEqual(model.validate(d), [])

    def test_R3_errors_say_where_the_problem_is(self):
        """R3(c): each error starts with a path such as states[0].blocks[0].w."""
        d = doc([state("a", [block(w=0)])])
        errors = model.validate(d)
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("states[0].blocks[0].w:"), errors)

    def test_R3_reports_every_error_not_just_the_first(self):
        """R3(c): an AI fixing its output needs the full list in one go."""
        d = doc([state("a", [block(w=0, type="sparkle")])])
        d["name"] = 5
        self.assertGreaterEqual(len(model.validate(d)), 3)

    def test_R3_unknown_field_is_rejected(self):
        """Spec: a typo like 'lable' must be an error, not silently ignored."""
        b = block()
        b["lable"] = "oops"
        errors = model.validate(doc([state("a", [b])]))
        self.assertTrue(any("lable" in e for e in errors), errors)

    def test_R3_unknown_block_type_is_rejected(self):
        errors = model.validate(doc([state("a", [block(type="carousel")])]))
        self.assertTrue(any("type" in e for e in errors), errors)

    def test_R3_booleans_are_not_accepted_as_numbers(self):
        """In Python True == 1, so this needs an explicit check."""
        errors = model.validate(doc([state("a", [block(x=True)])]))
        self.assertTrue(any(".x:" in e for e in errors), errors)

    def test_R3_duplicate_state_ids_are_rejected(self):
        errors = model.validate(doc([state("a"), state("a")]))
        self.assertTrue(any("duplicate" in e for e in errors), errors)

    def test_R3_duplicate_block_ids_in_one_state_are_rejected(self):
        errors = model.validate(doc([state("a", [block("b1"), block("b1")])]))
        self.assertTrue(any("duplicate" in e for e in errors), errors)

    def test_R3_same_block_id_in_different_states_is_fine(self):
        d = doc([state("a", [block("b1")]), state("b", [block("b1")])])
        self.assertEqual(model.validate(d), [])

    def test_R3_duplicate_transition_ids_are_rejected(self):
        d = doc([state("a")], [transition("t1", "a", "a", "x"), transition("t1", "a", "a", "y")])
        self.assertTrue(any("duplicate" in e for e in model.validate(d)))

    def test_R5_info_must_be_a_list_of_nonempty_strings(self):
        """R5(a): info is validated."""
        b = block()
        b["info"] = ["ok", ""]
        self.assertTrue(any("info" in e for e in model.validate(doc([state("a", [b])]))))
        b["info"] = "cart.total"  # a bare string, a likely AI mistake
        self.assertTrue(any("info" in e for e in model.validate(doc([state("a", [b])]))))

    def test_R5_note_must_be_a_string(self):
        """R5(a): note is validated."""
        b = block()
        b["note"] = 7
        self.assertTrue(any("note" in e for e in model.validate(doc([state("a", [b])]))))

    def test_R3_a_non_object_document_is_rejected(self):
        self.assertTrue(model.validate([1, 2]))

    def test_R4_dangling_references_are_not_a_shape_error(self):
        """R4: a transition to a missing state must be *saveable* so the
        checker can report it (spec: validate is shape only)."""
        d = doc([state("a")], [transition("t1", "a", "ghost", "go")])
        self.assertEqual(model.validate(d), [])


class FileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "w.json")

    def test_R1_save_then_load_round_trips(self):
        """R1(a): what we save is exactly what we load."""
        d = doc([state("a", [block(label="Hi")])])
        model.save(d, self.path)
        self.assertEqual(model.load(self.path), d)

    def test_R1_load_rejects_malformed_json(self):
        """R1(a): bad JSON gives a WireframeError, not a raw traceback."""
        with open(self.path, "w") as f:
            f.write("{not json")
        with self.assertRaises(model.WireframeError):
            model.load(self.path)

    def test_R1_load_rejects_an_invalid_document_with_its_errors(self):
        d = doc([state("a", [block(w=-1)])])
        with open(self.path, "w") as f:
            json.dump(d, f)
        with self.assertRaises(model.WireframeError) as ctx:
            model.load(self.path)
        self.assertTrue(ctx.exception.errors)

    def test_R1_save_never_writes_an_invalid_document(self):
        """R1(a): a refused save leaves the existing file untouched."""
        good = doc([state("a")])
        model.save(good, self.path)
        bad = copy.deepcopy(good)
        bad["states"][0]["id"] = ""
        with self.assertRaises(model.WireframeError):
            model.save(bad, self.path)
        self.assertEqual(model.load(self.path), good)

    def test_R1_load_or_create_makes_a_blank_file_when_missing(self):
        """R1(a): the server can start with no file yet."""
        d = model.load_or_create(self.path)
        self.assertTrue(os.path.exists(self.path))
        self.assertEqual(d, model.load(self.path))


if __name__ == "__main__":
    unittest.main()
