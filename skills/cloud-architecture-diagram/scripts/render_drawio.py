#!/usr/bin/env python3
"""Render a cloud inventory JSON into an editable draw.io (.drawio) diagram.

Usage:
    python render_drawio.py inventory.json -o diagram.drawio
    python render_drawio.py inventory.json --format mermaid

No third-party dependencies. Python 3.8+.
See ../references/inventory-schema.md for the input format.
"""

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

# ---------------------------------------------------------------- style table
# fillColor / strokeColor / fontColor per kind. Unknown kinds fall back to
# "default". Keep this provider-neutral: CSP-specific shape libraries are
# documented in references/layout-and-style.md instead of hardcoded here.
GROUP_STYLE = {
    "region":   ("#F5F5F5", "#9E9E9E", "#424242"),
    "vpc":      ("#E8F0FE", "#4285F4", "#1A5FB4"),
    "zone":     ("#FFFFFF", "#BDBDBD", "#616161"),
    "subnet":   ("#E8F5E9", "#43A047", "#1B5E20"),
    "public":   ("#E8F5E9", "#43A047", "#1B5E20"),
    "private":  ("#FFF3E0", "#FB8C00", "#E65100"),
    "onprem":   ("#EDE7F6", "#7E57C2", "#4527A0"),
    "external": ("#FAFAFA", "#9E9E9E", "#616161"),
    "default":  ("#FFFFFF", "#9E9E9E", "#424242"),
}

NODE_STYLE = {
    "server":     ("#DAE8FC", "#6C8EBF", "#1A237E"),
    "k8s":        ("#DAE8FC", "#6C8EBF", "#1A237E"),
    "container":  ("#DAE8FC", "#6C8EBF", "#1A237E"),
    "db":         ("#FFE6CC", "#D79B00", "#7F4F00"),
    "cache":      ("#FFE6CC", "#D79B00", "#7F4F00"),
    "lb":         ("#D5E8D4", "#82B366", "#1B5E20"),
    "gateway":    ("#D5E8D4", "#82B366", "#1B5E20"),
    "storage":    ("#FFF2CC", "#D6B656", "#7F6000"),
    "security":   ("#F8CECC", "#B85450", "#7F1D1D"),
    "monitoring": ("#E1D5E7", "#9673A6", "#4A148C"),
    "network":    ("#F5F5F5", "#666666", "#333333"),
    "client":     ("#FFFFFF", "#666666", "#333333"),
    "external":   ("#FFFFFF", "#666666", "#333333"),
    "default":    ("#FFFFFF", "#666666", "#333333"),
}

# Rounded rectangle for nodes, sharp for groups, cylinder for datastores.
SHAPE = {
    "db": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;",
    "storage": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;",
    "cache": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;",
    "client": "ellipse;",
    "external": "ellipse;",
}

# ------------------------------------------------------------------- geometry
NODE_W, NODE_H = 170, 60
LINE_H = 16
GAP = 20
PAD = 20
HEADER = 34
MAX_COLS_LEAF = 3   # leaf children per row
MAX_COLS_GROUP = 2  # group children per row
MAX_COLS_ROOT = 2   # top-level boxes per row


class Box:
    __slots__ = ("id", "label", "kind", "children", "x", "y", "w", "h", "is_group")

    def __init__(self, id_, label, kind, children=None):
        self.id = id_
        self.label = label
        self.kind = kind
        self.children = children or []
        self.is_group = bool(children)
        self.x = self.y = 0
        self.w = self.h = 0


def build(spec, seq):
    """Turn a dict from the inventory JSON into a Box tree."""
    children = spec.get("children") or []
    node_id = spec.get("id") or "n%d" % next(seq)
    label = spec.get("label") or node_id
    kind = (spec.get("kind") or ("group" if children else "default")).lower()
    box = Box(node_id, label, kind, [build(c, seq) for c in children])
    return box


def label_height(label):
    lines = str(label).count("\n") + 1
    return max(NODE_H, 28 + lines * LINE_H)


def grid_place(items, cols, gap):
    """Position `items` (objects with .w/.h) on a grid, mutating .x/.y as
    offsets from (0, 0). Each item is centered within its column/row cell,
    and an incomplete last row is centered under the full grid width instead
    of hugging the left edge. Returns the grid's (content_w, content_h)."""
    n = len(items)
    rows = math.ceil(n / cols)
    col_w = [0] * cols
    row_h = [0] * rows
    for i, item in enumerate(items):
        r, c = divmod(i, cols)
        col_w[c] = max(col_w[c], item.w)
        row_h[r] = max(row_h[r], item.h)

    content_w = sum(col_w) + gap * (cols - 1)
    last_row_n = n - (rows - 1) * cols
    last_row_w = sum(col_w[:last_row_n]) + gap * (last_row_n - 1)
    last_row_offset = (content_w - last_row_w) / 2 if last_row_n < cols else 0

    for i, item in enumerate(items):
        r, c = divmod(i, cols)
        col_x = sum(col_w[:c]) + gap * c
        row_y = sum(row_h[:r]) + gap * r
        extra = last_row_offset if r == rows - 1 else 0
        item.x = round(col_x + extra + (col_w[c] - item.w) / 2)
        item.y = round(row_y + (row_h[r] - item.h) / 2)

    content_h = sum(row_h) + gap * (rows - 1)
    return content_w, content_h


def layout(box):
    """Bottom-up sizing. Child x/y are relative to the parent box."""
    if not box.children:
        box.w, box.h = NODE_W, label_height(box.label)
        return

    for child in box.children:
        layout(child)

    all_leaves = all(not c.children for c in box.children)
    max_cols = MAX_COLS_LEAF if all_leaves else MAX_COLS_GROUP
    cols = min(max_cols, len(box.children))

    content_w, content_h = grid_place(box.children, cols, GAP)
    for child in box.children:
        child.x += PAD
        child.y += HEADER

    box.w = PAD * 2 + content_w
    box.h = HEADER + PAD + content_h


def absolute_positions(box, offset_x=0, offset_y=0, out=None):
    """Map every box id to its absolute (x, y, w, h) on the canvas."""
    if out is None:
        out = {}
    ax, ay = box.x + offset_x, box.y + offset_y
    out[box.id] = (ax, ay, box.w, box.h)
    for child in box.children:
        absolute_positions(child, ax, ay, out)
    return out


def style_for(box):
    if box.is_group:
        fill, stroke, font = GROUP_STYLE.get(box.kind, GROUP_STYLE["default"])
        return (
            "rounded=0;whiteSpace=wrap;html=1;container=1;collapsible=0;"
            "verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;"
            "fontSize=13;fontStyle=1;dashed=0;"
            "fillColor=%s;strokeColor=%s;fontColor=%s;" % (fill, stroke, font)
        )
    fill, stroke, font = NODE_STYLE.get(box.kind, NODE_STYLE["default"])
    shape = SHAPE.get(box.kind, "rounded=1;arcSize=12;")
    return (
        "%swhiteSpace=wrap;html=1;fontSize=12;"
        "fillColor=%s;strokeColor=%s;fontColor=%s;" % (shape, fill, stroke, font)
    )


def html_label(label):
    """draw.io cells use html=1, and XML attribute normalization would collapse a
    raw newline into a space, so line breaks have to travel as <br>."""
    return str(label).replace("\r\n", "\n").replace("\n", "<br>")


def emit(box, parent_id, root):
    cell = ET.SubElement(
        root, "mxCell",
        {"id": box.id, "value": html_label(box.label), "style": style_for(box),
         "vertex": "1", "parent": parent_id},
    )
    ET.SubElement(
        cell, "mxGeometry",
        {"x": str(box.x), "y": str(box.y), "width": str(box.w),
         "height": str(box.h), "as": "geometry"},
    )
    for child in box.children:
        emit(child, box.id, root)


EDGE_STYLE = {
    "solid": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;jumpStyle=arc;",
    "dashed": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;dashed=1;",
    "thick": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth=3;",
    "none": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=none;",
}


def connection_style(abs_pos, src, dst):
    """Fix the edge's exit/entry side to whichever cardinal direction points
    from source to target, instead of leaving it to draw.io's free-floating
    connection (which tends to cut straight through boxes sitting between
    them). Not a full obstacle-avoiding router, just a bias toward the
    natural side."""
    if src not in abs_pos or dst not in abs_pos:
        return ""
    sx, sy, sw, sh = abs_pos[src]
    tx, ty, tw, th = abs_pos[dst]
    dx = (tx + tw / 2) - (sx + sw / 2)
    dy = (ty + th / 2) - (sy + sh / 2)
    if abs(dx) >= abs(dy):
        ex, ey = (1, 0.5) if dx >= 0 else (0, 0.5)
        nx, ny = (0, 0.5) if dx >= 0 else (1, 0.5)
    else:
        ex, ey = (0.5, 1) if dy >= 0 else (0.5, 0)
        nx, ny = (0.5, 0) if dy >= 0 else (0.5, 1)
    return (
        "exitX=%g;exitY=%g;exitDx=0;exitDy=0;"
        "entryX=%g;entryY=%g;entryDx=0;entryDy=0;"
    ) % (ex, ey, nx, ny)


def render_drawio(inv):
    seq = iter(range(1, 100000))
    roots = [build(n, seq) for n in inv.get("nodes", [])]
    roots += [build(g, seq) for g in inv.get("groups", [])]
    if not roots:
        raise SystemExit("inventory has no 'groups' and no 'nodes'")

    for box in roots:
        layout(box)

    # Top-level boxes sit on the same centered grid as any other container.
    cols = min(MAX_COLS_ROOT, len(roots))
    grid_place(roots, cols, 40)
    for box in roots:
        box.x += 40
        box.y += 40

    abs_pos = {}
    for box in roots:
        absolute_positions(box, 0, 0, abs_pos)

    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diagram = ET.SubElement(
        mxfile, "diagram", {"name": inv.get("title", "architecture"), "id": "d0"})
    model = ET.SubElement(
        diagram, "mxGraphModel",
        {"dx": "1400", "dy": "900", "grid": "1", "gridSize": "10",
         "page": "1", "pageWidth": "1654", "pageHeight": "1169", "math": "0"},
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    for box in roots:
        emit(box, "1", root)

    known = set()
    dupes = []

    def collect(b):
        if b.id in known:
            dupes.append(b.id)
        known.add(b.id)
        for c in b.children:
            collect(c)
    for b in roots:
        collect(b)
    if dupes:
        raise SystemExit("duplicate id(s) in inventory: %s" % ", ".join(sorted(set(dupes))))

    for i, edge in enumerate(inv.get("edges", [])):
        src, dst = edge.get("from"), edge.get("to")
        for end in (src, dst):
            if end not in known:
                print("warning: edge endpoint %r not found in the diagram" % end,
                      file=sys.stderr)
        style = EDGE_STYLE.get(edge.get("style", "solid"), EDGE_STYLE["solid"])
        style += connection_style(abs_pos, src, dst)
        cell = ET.SubElement(
            root, "mxCell",
            {"id": "e%d" % i, "value": html_label(edge.get("label", "")), "style": style,
             "edge": "1", "parent": "1", "source": str(src), "target": str(dst)},
        )
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})

    raw = ET.tostring(mxfile, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ")


# ------------------------------------------------------------------- mermaid
def render_mermaid(inv):
    """Quick preview for chat / markdown. Not the deliverable."""
    out = ["flowchart TB"]
    seq = iter(range(1, 100000))

    def walk(spec, depth):
        ind = "    " * (depth + 1)
        box = build(spec, seq)
        if box.children:
            out.append('%ssubgraph %s["%s"]' % (ind, box.id, box.label))
            out.append("%s    direction TB" % ind)
            for child in spec.get("children", []):
                walk(child, depth + 1)
            out.append("%send" % ind)
        else:
            label = str(box.label).replace("\n", "<br/>")
            out.append('%s%s["%s"]' % (ind, box.id, label))

    for group in inv.get("groups", []):
        walk(group, 0)
    for node in inv.get("nodes", []):
        walk(node, 0)
    for edge in inv.get("edges", []):
        arrow = "-.->" if edge.get("style") == "dashed" else "-->"
        label = edge.get("label")
        if label:
            out.append('    %s %s|"%s"| %s' % (edge["from"], arrow, label, edge["to"]))
        else:
            out.append("    %s %s %s" % (edge["from"], arrow, edge["to"]))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inventory", help="path to inventory JSON")
    ap.add_argument("-o", "--out", help="output file (default: stdout)")
    ap.add_argument("-f", "--format", choices=["drawio", "mermaid"],
                    default="drawio")
    args = ap.parse_args()

    with open(args.inventory, encoding="utf-8") as fh:
        inv = json.load(fh)

    text = render_drawio(inv) if args.format == "drawio" else render_mermaid(inv)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s" % args.out, file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
