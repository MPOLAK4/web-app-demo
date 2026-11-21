"""Command line: the headless way to use a wireframe file (R1-R4).

    python -m wireframe new FILE [--name NAME] [--example]
    python -m wireframe validate FILE
    python -m wireframe check FILE
    python -m wireframe export FILE [--mode coder|image]
    python -m wireframe guide
    python -m wireframe op FILE '{"op": "add_block", ...}'

Exit codes: 0 success, 1 a problem was found or the command failed.
"""

import argparse
import json
import os
import sys

from . import checks, model, ops, spec
from .example import example_wireframe


def _fail(errors):
    for line in errors:
        print(line, file=sys.stderr)
    return 1


def _build_parser():
    parser = argparse.ArgumentParser(prog="python -m wireframe", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create a wireframe file")
    p.add_argument("file")
    p.add_argument("--name", default="Untitled")
    p.add_argument("--example", action="store_true", help="start from the worked checkout example")

    for name, text in (("validate", "check the file's format (R3)"),
                       ("check", "check the design for conflicts and duplicate info (R4, R5)")):
        p = sub.add_parser(name, help=text)
        p.add_argument("file")

    p = sub.add_parser("export", help="print a spec sheet (R2)")
    p.add_argument("file")
    p.add_argument("--mode", choices=spec.MODES, default="coder")

    sub.add_parser("guide", help="print the guide an AI follows to write a wireframe (R3)")

    p = sub.add_parser("op", help="apply one edit, given as JSON, to the file (R1)")
    p.add_argument("file")
    p.add_argument("op", help='e.g. \'{"op": "delete_block", "state": "cart", "id": "b1"}\'')
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "new":
            if os.path.exists(args.file):
                return _fail([f"{args.file} already exists; refusing to overwrite it"])
            doc = example_wireframe() if args.example else model.new_wireframe(args.name)
            model.save(doc, args.file)
            print(f"Created {args.file}")
        elif args.command == "validate":
            model.load(args.file)
            print("The wireframe is valid.")
        elif args.command == "check":
            findings = checks.check(model.load(args.file))
            print(checks.format_findings(findings))
            return 1 if checks.has_errors(findings) else 0
        elif args.command == "export":
            print(spec.export_spec(model.load(args.file), args.mode), end="")
        elif args.command == "guide":
            print(spec.authoring_guide(), end="")
        elif args.command == "op":
            try:
                op = json.loads(args.op)
            except json.JSONDecodeError as exc:
                return _fail([f"the op is not valid JSON: {exc}"])
            model.save(ops.apply_op(model.load(args.file), op), args.file)
            print("ok")
    except model.WireframeError as exc:
        return _fail(exc.errors)
    return 0
