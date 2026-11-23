"""Command line: the headless way to use a wireframe file (R1-R4).

    python -m wireframe new FILE [--name NAME] [--example [NAME]]
    python -m wireframe examples [NAME] [--part wireframe|coder|image|check|svg|viewer]
                                 [--state ID] [--build DIR]
    python -m wireframe validate FILE
    python -m wireframe check FILE
    python -m wireframe export FILE [--mode coder|image] [--data debug|live]
    python -m wireframe guide
    python -m wireframe op FILE '{"op": "add_block", ...}'
    python -m wireframe walk FILE [EVENT[=TRANSITION_ID] ...]
    python -m wireframe render FILE [--state ID | --after EVENT[=ID] ...] [--format svg|html]
                                    [--data debug|live] [--out PATH]
    python -m wireframe viewer FILE [--out PATH]
    python -m wireframe start [FILE] [--port N] [--idle-timeout SECONDS] [--state-file PATH]
    python -m wireframe stop [--state-file PATH]
    python -m wireframe status [--state-file PATH]

`start` runs the editor server in the background (R12); `stop` ends it. Everything
else here needs no server at all.

Exit codes: 0 success, 1 a problem was found or the command failed.
"""

import argparse
import json
import os
import sys

from . import checks, data, examples, model, ops, play, render, serverctl, spec, viewer


EXAMPLE_PARTS = ("wireframe", "coder", "image", "check", "svg", "viewer")


def _examples(args):
    """R14(g). Returns the exit code; prints nothing to stdout on failure."""
    if args.build:
        examples.write_files(args.build)
        print(f"Wrote {len(examples.build_files())} files under {args.build}")
        return 0
    if not args.name:
        for e in examples.list_examples():
            print(f"{e['name']:10} {e['summary']}")
        return 0
    io = examples.example_io(args.name)          # unknown name: WireframeError -> exit 1
    if args.part == "svg":
        state_id = args.state or next(iter(io["svg"]))
        if state_id not in io["svg"]:
            return _fail([f"unknown screen '{state_id}'; use one of: {', '.join(io['svg'])}"])
        print(io["svg"][state_id], end="")
    else:
        print(io[args.part], end="")
    return 0


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
    p.add_argument("--example", nargs="?", const="checkout", metavar="NAME",
                   help="start from an example (R14); a bare --example means checkout")

    for name, text in (("validate", "check the file's format (R3)"),
                       ("check", "check the design for conflicts and duplicate info (R4, R5)")):
        p = sub.add_parser(name, help=text)
        p.add_argument("file")

    p = sub.add_parser("export", help="print a spec sheet (R2)")
    p.add_argument("file")
    p.add_argument("--mode", choices=spec.MODES, default="coder")
    p.add_argument("--data", choices=data.MODES, default="debug",
                   help="debug shows {{tokens}} as written, live shows sample text (image brief only)")

    sub.add_parser("guide", help="print the guide an AI follows to write a wireframe (R3)")

    p = sub.add_parser("op", help="apply one edit, given as JSON, to the file (R1)")
    p.add_argument("file")
    p.add_argument("op", help='e.g. \'{"op": "delete_block", "state": "cart", "id": "b1"}\'')

    p = sub.add_parser("walk", help="walk the wireframe like a real UI, one event at a time (R9)")
    p.add_argument("file")
    p.add_argument("events", nargs="*", metavar="EVENT[=TRANSITION_ID]",
                   help="events to raise in order; add =ID to pick one of several guarded transitions")

    p = sub.add_parser("render", help="write a picture file (SVG or HTML) of one screen (R10)")
    p.add_argument("file")
    p.add_argument("--state", help="the screen to draw (default: the first screen)")
    p.add_argument("--after", nargs="+", metavar="EVENT[=ID]",
                   help="draw the screen reached after these events, like walk")
    p.add_argument("--format", choices=render.FORMATS, default="svg")
    p.add_argument("--data", choices=data.MODES, default="debug")
    p.add_argument("--out", help="write here instead of printing (an existing file is replaced)")

    p = sub.add_parser("viewer", help="write a clickable HTML file that shows the wireframe, no server needed (R13)")
    p.add_argument("file")
    p.add_argument("--out", help="write here instead of printing (an existing file is replaced)")

    p = sub.add_parser("examples", help="list the example wireframes, or print one part of one (R14)")
    p.add_argument("name", nargs="?", help="an example name; leave out to list them all")
    p.add_argument("--part", choices=EXAMPLE_PARTS, default="wireframe",
                   help="which part to print (default wireframe, the input)")
    p.add_argument("--state", help="with --part svg: the screen to print (default: the first)")
    p.add_argument("--build", metavar="DIR", help="write every example's files into DIR instead")

    p = sub.add_parser("start", help="start the editor server in the background (R12)")
    p.add_argument("file", nargs="?", default="wireframe.json")
    p.add_argument("--port", type=int, default=0, help="0 (default) picks any free port")
    p.add_argument("--idle-timeout", type=float, default=serverctl.DEFAULT_IDLE_TIMEOUT, metavar="SECONDS",
                   help="the server stops itself after this long without a request (default 600)")
    p.add_argument("--state-file", default=serverctl.DEFAULT_STATE_FILE,
                   help=f"where the server records itself (default {serverctl.DEFAULT_STATE_FILE})")
    for name, text in (("stop", "stop the background server (R12)"),
                       ("status", "say whether a background server is running (R12)")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--state-file", default=serverctl.DEFAULT_STATE_FILE,
                       help=f"where the server records itself (default {serverctl.DEFAULT_STATE_FILE})")
    return parser


def _describe_screen(doc, state_id):
    scr = play.screen(doc, state_id)
    print(f"Screen {scr['state']}: {scr['title']}" + (" (final)" if scr["final"] else ""))
    for b in scr["blocks"]:
        label = f' "{b["label"]}"' if b["label"] else ""
        do = f" -> raises {b['event']}" if b["event"] and not b.get("disabled") else ""
        print(f"  {b['type']}{label}{do}")
    if scr["events"]:
        print("  Events you can use: " + ", ".join(scr["events"]))
    if scr["system_events"]:
        print("  System events: " + ", ".join(scr["system_events"]))


def _walk(doc, tokens):
    """Returns the exit code. Prints each step; never writes the file."""
    here = doc["initial"]
    _describe_screen(doc, here)
    for token in tokens:
        event, _, choice = token.partition("=")
        result = play.step(doc, here, event, choice or None)
        if result["status"] == "stuck":
            print(f"Stuck: nothing on '{here}' handles '{event}'.")
            return 1
        if result["status"] == "choose":
            print(f"'{event}' on '{here}' could go several ways; repeat it as {event}=ID:")
            for o in result["options"]:
                print(f"  {o['transition']}: if {o['guard'] or '(no guard)'} -> {o['target']}")
            return 1
        print(f"{here} --{event}--> {result['state']}")
        here = result["state"]
        _describe_screen(doc, here)
    print(f"Now on: {here}" + (" (final)" if play.screen(doc, here)["final"] else ""))
    return 0


def _render(args):
    doc = model.load(args.file)
    if args.state and args.after:
        return _fail(["use --state or --after, not both"])
    state_id = args.state or play.follow(doc, args.after or [])
    _write_or_print(render.render_screen(doc, state_id, args.format, args.data), args.out)
    return 0


def _write_or_print(text, out):
    if out:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"Wrote {out}")
    else:
        print(text, end="")


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "new":
            if os.path.exists(args.file):
                return _fail([f"{args.file} already exists; refusing to overwrite it"])
            doc = examples.get_example(args.example) if args.example else model.new_wireframe(args.name)
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
            print(spec.export_spec(model.load(args.file), args.mode, args.data), end="")
        elif args.command == "guide":
            print(spec.authoring_guide(), end="")
        elif args.command == "op":
            try:
                op = json.loads(args.op)
            except json.JSONDecodeError as exc:
                return _fail([f"the op is not valid JSON: {exc}"])
            model.save(ops.apply_op(model.load(args.file), op), args.file)
            print("ok")
        elif args.command == "render":
            return _render(args)
        elif args.command == "examples":
            return _examples(args)
        elif args.command == "viewer":
            _write_or_print(viewer.build_viewer(model.load(args.file)), args.out)
        elif args.command == "start":
            info, already = serverctl.start(args.file, args.port, args.idle_timeout, args.state_file)
            print(f"Server {'already running' if already else 'running'} at {info['url']} "
                  f"(editing {info['file']}).")
            print("It stops itself after a quiet spell; to stop it now run: python -m wireframe stop")
        elif args.command == "stop":
            print(serverctl.stop(args.state_file))
        elif args.command == "status":
            url = serverctl.status(args.state_file)
            print(f"Server running at {url}" if url else "No server is running (not running).")
        elif args.command == "walk":
            return _walk(model.load(args.file), args.events)
    except model.WireframeError as exc:
        return _fail(exc.errors)
    return 0
