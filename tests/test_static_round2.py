"""Round 2 editor files (R7(e), R8, R9(g)).

As in test_static.py, unittest cannot click, so these check what can be checked
from the files: the page has the new controls, the script sends only real ops,
the preset list matches the model, and Play mode contains no editing code.
Dragging, resizing, shift-click and Play must still be tried by hand.
"""
import os
import re
import unittest

from wireframe import model, ops
from test_static import read


def play_section():
    js = read("app.js")
    start = js.index("// ---------- play mode")
    end = js.index("// ---------- end play mode")
    return js[start:end]


class EditorControlsTests(unittest.TestCase):
    def test_R8_page_has_the_new_controls(self):
        """R8(c)/(e), R9(g): preset, background, grid size and Play button exist."""
        html = read("index.html")
        for ident in ("doc-preset", "state-bg", "grid-size", "btn-play", "play-panel",
                      "block-tools", "style-list", "add-style-form"):
            self.assertIn(f'id="{ident}"', html, ident)

    def test_R8_editor_sends_the_new_ops(self):
        """R7(e)/R8(d)/(e): each new op is used by some editor control, and exists."""
        sent = set(re.findall(r'op: "([a-z_]+)"', read("app.js")))
        for name in ("duplicate_block", "reorder_block", "move_blocks", "add_style",
                     "update_style", "delete_style", "set_style", "update_wireframe"):
            self.assertIn(name, sent, name)
            self.assertIn(name, ops.OPS)

    def test_R8_preset_choices_match_the_model(self):
        """R8(c): the dropdown must offer exactly the presets the server knows."""
        listed = re.search(r"PRESETS = \[(.*?)\];", read("app.js"), re.S).group(1)
        self.assertEqual(set(re.findall(r'"(\w+)"', listed)), set(model.DEVICE_PRESETS))

    def test_R7_the_editor_draws_from_resolved_styles_not_its_own_table(self):
        """R6(b): one source of truth for what a block looks like."""
        self.assertIn("/api/resolved", read("app.js"))

    def test_R8_reorder_buttons_cover_all_four_directions(self):
        """R8(d)/(e)."""
        js = read("app.js")
        for where in ("front", "forward", "backward", "back"):
            self.assertIn(f'"{where}"', js, where)

    def test_R8_resize_handles_on_all_four_corners_and_shift_select(self):
        """R8(e)."""
        js = read("app.js")
        for corner in ("nw", "ne", "sw", "se"):
            self.assertIn(f'"{corner}"', js, corner)
        self.assertIn("shiftKey", js)


class PlayModeTests(unittest.TestCase):
    def test_R9_play_mode_uses_the_play_api(self):
        """R9(g): the flow rules live in Python, not in JavaScript."""
        self.assertIn("/api/play", play_section())

    def test_R9_play_mode_never_sends_an_edit(self):
        """R9(g): Play never changes the wireframe file, so it must not call send()."""
        code = "\n".join(line.split("//")[0] for line in play_section().splitlines())
        self.assertNotIn("send(", code)
        self.assertNotIn('"/api/op"', code)
        self.assertNotIn('"PUT"', code)

    def test_R9_play_mode_has_back_restart_and_a_final_notice(self):
        """R9(g)."""
        html = read("index.html")
        for ident in ("play-back", "play-restart", "play-log", "play-chooser",
                      "play-system", "play-final"):
            self.assertIn(f'id="{ident}"', html, ident)

    def test_R9_play_mode_writes_text_only(self):
        """R1(f) still applies to the new code."""
        code = "\n".join(line.split("//")[0] for line in play_section().splitlines())
        self.assertNotIn("innerHTML", code)


if __name__ == "__main__":
    unittest.main()
