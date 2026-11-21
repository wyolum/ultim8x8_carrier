"""2026-11-21 Render the review images in docs/ from ultim_carrier.kicad_pcb.

Needs kicad-cli (KiCad 10), rsvg-convert and Pillow.
Usage: python3 2026-11-21_render_docs.py
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "ultim_carrier.kicad_pcb")
DOCS = os.path.join(HERE, "docs")
KC = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
DATE = "2026-11-21"
HALF = 104.05                      # half the exported page: 208 mm board plus the outline stroke
Image.MAX_IMAGE_PIXELS = None


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"{' '.join(cmd)}\n{r.stdout}\n{r.stderr}")


def strip_fills(src, dst):
    """Copy the board without zone fills so traces are visible."""
    s = open(src).read()
    out, i = [], 0
    while True:
        j = s.find("(filled_polygon", i)
        if j < 0:
            out.append(s[i:])
            break
        out.append(s[i:j])
        depth, k = 0, j
        while True:
            if s[k] == "(":
                depth += 1
            elif s[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        i = k + 1
    open(dst, "w").write("".join(out))


def export(board, layers, png, width, mirror=False, bw=False):
    svg = png[:-4] + ".svg"
    cmd = [KC, "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "2",
           "--exclude-drawing-sheet", "-o", svg, board]
    if mirror:
        cmd.insert(4, "--mirror")
    if bw:
        cmd.insert(4, "--black-and-white")
    run(cmd)
    run(["rsvg-convert", "-w", str(width), "-b", "white", svg, "-o", png])
    os.remove(svg)
    return Image.open(png).convert("RGB")


def crop(im, box, mirror, name):
    """box = (x0, y0, x1, y1) in board mm, LED-side view, y up."""
    s = im.size[0] / (2 * HALF)
    x0, y0, x1, y1 = box
    if mirror:
        px = ((HALF - x1) * s, (HALF - x0) * s)
    else:
        px = ((HALF + x0) * s, (HALF + x1) * s)
    out = im.crop((int(px[0]), int((HALF - y1) * s), int(px[1]), int((HALF - y0) * s)))
    path = os.path.join(DOCS, f"{DATE}_{name}.png")
    out.save(path, optimize=True)
    print(f"{out.size[0]} x {out.size[1]} -> {path}")


def main():
    os.makedirs(DOCS, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        # pours as the fab will see them, one layer each, LED-side view
        for layer, name in (("F.Cu", "front_copper_filled"), ("B.Cu", "back_copper_filled")):
            im = export(BOARD, f"{layer},Edge.Cuts", os.path.join(tmp, name + ".png"), 1600, bw=True)
            im.save(os.path.join(DOCS, f"{DATE}_{name}.png"), optimize=True)
            print(f"-> {name}")
        nofill = os.path.join(tmp, "nofill.kicad_pcb")
        strip_fills(BOARD, nofill)
        # back of the board as you hold it to solder (mirrored), pours hidden
        back = export(nofill, "F.Cu,B.Cu,B.SilkS,B.Fab,Edge.Cuts", os.path.join(tmp, "back.png"),
                      7000, mirror=True)
        small = back.resize((2000, 2000), Image.LANCZOS)
        small.save(os.path.join(DOCS, f"{DATE}_back_overview.png"), optimize=True)
        crop(back, (-93, -72, -36, -24), True, "back_pico_shifter")
        crop(back, (-22, -44, 22, -18), True, "back_power_entry")
        crop(back, (-24, 66, 34, 86), True, "back_alamode_header")
        crop(back, (28, 20, 104, 84), True, "back_uno")
        # front of the board (tile side), pours hidden
        front = export(nofill, "B.Cu,F.Cu,F.SilkS,Edge.Cuts", os.path.join(tmp, "front.png"), 7000)
        crop(front, (40, -76, 95, 15), False, "front_row_turn")
        crop(front, (-31, -92, 31, -30), False, "front_tile_T1_diamonds")


if __name__ == "__main__":
    main()
