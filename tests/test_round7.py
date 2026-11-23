"""R17 (changes R12): the idle timeout is 10 minutes (600 seconds), not 5.

These check that the number was changed everywhere a person or an AI reads it,
and that it is still defined in one place (R16(e)).
"""
import os
import unittest

import server
from wireframe import cli, serverctl, spec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class IdleTimeoutRound7Tests(unittest.TestCase):
    def test_R17_a_default_is_600_seconds_defined_once(self):
        """R17(a): 600 in serverctl, and server.py reuses it."""
        self.assertEqual(serverctl.DEFAULT_IDLE_TIMEOUT, 600)
        self.assertEqual(server.DEFAULT_IDLE_TIMEOUT, 600)

    def test_R17_a_command_line_defaults_are_600(self):
        """R17(a): `start` uses the serverctl default."""
        args = cli._build_parser().parse_args(["start"])
        self.assertEqual(args.idle_timeout, 600)

    def test_R17_d_texts_say_ten_minutes_not_five(self):
        """R17(d): the AI guide, README and help text agree with the number."""
        guide = spec.authoring_guide()
        self.assertIn("10 minutes", guide)
        self.assertNotIn("5 minutes", guide)
        self.assertIn("600 seconds", read("README.md"))
        self.assertNotIn("300 seconds", read("README.md"))
        self.assertIn("default 600", read("server.py"))
        self.assertIn("default 600", read(os.path.join("wireframe", "cli.py")))
