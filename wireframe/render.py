"""Picture files of one screen (R10): SVG, or the same SVG inside an HTML page.

    render_screen(doc, state_id, "svg" | "html", data="debug" | "live")

This only reads the document and returns text. Colours and sizes come from
`styles.resolve_style` (through `play.screen`), and the text shown in a block
comes from `content_lines` below, so the editor, Play and these files agree.

Safety: every piece of user text goes through `html.escape`, the file contains
no script and no link to anything else, and colours were already checked to be
hex by validation.
"""

from html import escape

from . import data as datamod
from .model import WireframeError
from .play import screen

FORMATS = ("svg", "html")
_TRUE = ("true", "on", "yes", "checked", "1")


def content_lines(doc, b, mode="debug"):
    """What a block says: its text lines, with per-type decoration, in `mode`."""
    def fill(text):
        return datamod.fill(doc, str(text), mode)

    label = fill(b.get("label", ""))
    options = [fill(o) for o in b.get("options", [])]
    value = fill(b["value"]) if b.get("value") is not None else ""
    placeholder = fill(b.get("placeholder", ""))
    on = value.lower() in _TRUE
    kind = b.get("type")
    if kind in ("input", "textarea"):
        return [label, value or placeholder]
    if kind == "checkbox":
        return [f"{'[x]' if on else '[ ]'} {label}"]
    if kind == "toggle":
        return [f"{label}  {'(ON o)' if on else '(o OFF)'}"]
    if kind == "radio":
        return [label] + [f"{'(o)' if o == value else '( )'} {o}" for o in options]
    if kind == "select":
        return [label, f"{value or (options[0] if options else '')}  v"]
    if kind == "slider":
        return [label, f"-----o----- {value}"]
    if kind == "tabs":
        if not options:
            return [label]
        return ["  |  ".join(f"[{o}]" if o == value else o for o in options)]
    if kind == "table":
        return [label] + options
    if kind == "divider":
        return []
    if kind == "icon":
        return [f"({label})"]
    return [label]


def _block_svg(doc, b, mode):
    """One block as a nested <svg>, which clips its text to the block's box."""
    r = b["resolved"]
    w, h = b["w"], b["h"]
    bw = r.get("border_width", 1)
    fill = r.get("fill", "none")
    attrs = [f'x="{b["x"]}"', f'y="{b["y"]}"', f'width="{w}"', f'height="{h}"']
    opacity = r.get("opacity", 1)
    if b.get("disabled"):
        opacity = round(opacity * 0.5, 3)
    if opacity != 1:
        attrs.append(f'opacity="{opacity}"')
    if r.get("shadow"):
        attrs.append('filter="url(#shadow)"')
    rect = (f'<rect x="{bw / 2}" y="{bw / 2}" width="{max(w - bw, 0)}" height="{max(h - bw, 0)}" '
            f'rx="{r.get("radius", 0)}" fill="{fill}" stroke="{r.get("border_color", "none")}" '
            f'stroke-width="{bw}"/>')
    size = r.get("font_size", 14)
    pad = r.get("padding", 0)
    align = r.get("align", "left")
    anchor, tx = {"left": ("start", pad), "center": ("middle", w / 2), "right": ("end", w - pad)}[align]
    weight = r.get("font_weight", "normal")
    texts = []
    for i, line in enumerate(content_lines(doc, b, mode)):
        y = pad + size * 1.2 * (i + 1) - size * 0.2
        texts.append(f'<text x="{tx}" y="{y:g}" text-anchor="{anchor}" font-size="{size}" '
                     f'font-weight="{weight}" fill="{r.get("text_color", "#000")}" '
                     f'xml:space="preserve">{escape(line)}</text>')
    return f'<svg {" ".join(attrs)}>{rect}{"".join(texts)}</svg>'


def _svg(doc, scr, mode):
    cw, ch = doc["canvas"]["width"], doc["canvas"]["height"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw}" height="{ch}" '
             f'viewBox="0 0 {cw} {ch}" font-family="Arial, Helvetica, sans-serif">',
             '<defs><filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
             '<feDropShadow dx="0" dy="3" stdDeviation="4" flood-opacity="0.3"/></filter></defs>',
             f'<rect width="{cw}" height="{ch}" fill="{scr["background"]}"/>']
    parts += [_block_svg(doc, b, mode) for b in scr["blocks"]]
    parts.append("</svg>")
    return "\n".join(parts)


def render_screen(doc, state_id, fmt, data="debug"):
    if fmt not in FORMATS:
        raise WireframeError(f"unknown format '{fmt}'; use one of: {', '.join(FORMATS)}")
    datamod.check_mode(data)
    scr = screen(doc, state_id)          # raises for an unknown screen
    svg = _svg(doc, scr, data)
    if fmt == "svg":
        return svg
    title = escape(f'{doc["name"]}: {scr["title"]} ({data} data)')
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<title>{title}</title>\n"
            "<style>body{margin:16px;background:#eee}svg{display:block;box-shadow:0 1px 6px rgba(0,0,0,.3)}"
            "</style>\n</head>\n<body>\n" + svg + "\n</body>\n</html>\n")
