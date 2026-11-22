"""2026-11-21 Export fabrication files from ultim_carrier.kicad_pcb into fab/.

Gerbers and drill files (also zipped), a component position file, an
IPC-D-356 netlist and a bill of materials.

Needs KiCad 10 (kicad-cli and its bundled Python).
Usage: python3 2026-11-21_export_fab.py
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "ultim_carrier.kicad_pcb")
FAB = os.path.join(HERE, "fab")
KC = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KP = "/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
DATE = "2026-11-22"
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts"

DUMP = r"""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
rows = [dict(ref=f.GetReference(), value=f.GetValue(), footprint=f.GetFPID().GetUniStringLibItemName(),
             lib=f.GetFPID().GetUniStringLibNickname(), back=f.IsFlipped(), pads=f.GetPadCount())
        for f in b.GetFootprints()]
json.dump(rows, open(sys.argv[2], "w"))
"""


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"{' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def group(ref):
    """What a footprint is, for the bill of materials."""
    if ref[0] == "T" and ref[1:].isdigit():
        return None                                   # tile terminal holes, no part
    if ref[0] == "H" and ref[1:].isdigit():
        return None                                   # perimeter screw holes
    if ref.startswith("TP"):
        return None                                   # bare test pads
    if ref[0] == "T" and ("In" in ref or "Out" in ref):
        return "do not populate"
    return "always fitted"


# Sourcing, keyed by the first reference of a BOM line: (part to buy, LCSC number, buy qty, note).
# Every LCSC number was looked up on lcsc.com on 2026-11-22 and matches the description.
SOURCE = {
    "A1": ("Hong Cheng HC-PM254-8.5H-1x20PZ, 1x20 socket, 8.5 mm tall", "C22373906", 2,
           "two sockets for one Pico 2 W; the Pico itself is not on this list"),
    "C1": ("Econd 1000uF10V10x13GF", "C55565640", 1, "10 mm diameter, 13 mm tall, 5 mm lead pitch"),
    "D1": ("TWGMC 1N5819W", "C727115", 1, "40 V 1 A Schottky"),
    "D4": ("LGE SS54", "C330398", 1, "40 V 5 A Schottky"),
    "F1": ("Keystone 3568", "C5249699", 1,
           "LCSC stock was 0 on 2026-11-22. Possible substitute XFCN XF-508P-B-B (C19727305): pins "
           "9.80 x 3.40 mm against this footprint's 9.92 x 3.40 mm, a tight fit in the 1.78 mm holes, not tried"),
    "J2": ("Phoenix Contact 1715721 (MKDS 1,5/2-5,08)", "C480516", 1, ""),
}
# Parts with no footprint of their own.
EXTRA = [("always fitted", 1, "in F1", "3 A mini blade fuse", "", "any 3 A mini (ATM) blade fuse", "", 1,
          "no LCSC number chosen")]


def main():
    if not os.path.exists(BOARD):
        fail(f"missing {BOARD}")
    gerb = os.path.join(FAB, "gerbers")
    shutil.rmtree(gerb, ignore_errors=True)
    os.makedirs(gerb)
    run([KC, "pcb", "export", "gerbers", "-o", gerb + "/", "--layers", LAYERS,
         "--subtract-soldermask", "--check-zones", BOARD])
    run([KC, "pcb", "export", "drill", "-o", gerb + "/", "--excellon-separate-th",
         "--generate-map", "--map-format", "pdf", BOARD])
    files = sorted(os.listdir(gerb))
    zpath = os.path.join(FAB, f"{DATE}_ultim_carrier_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if not f.endswith(".pdf"):
                z.write(os.path.join(gerb, f), f)
    print(f"{len(files)} files in fab/gerbers, zipped to {os.path.basename(zpath)}")

    run([KC, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "-o", os.path.join(FAB, f"{DATE}_positions.csv"), BOARD])
    run([KC, "pcb", "export", "ipcd356", "-o", os.path.join(FAB, f"{DATE}_netlist.d356"), BOARD])

    tmp = os.path.join(FAB, "footprints.json")
    run([KP, "-c", DUMP, BOARD, tmp])
    rows = json.load(open(tmp))
    os.remove(tmp)
    parts = {}
    for r in rows:
        g = group(r["ref"])
        if g is None:
            continue
        key = (g, r["value"], r["footprint"] or "drawn in the build script")
        parts.setdefault(key, []).append(r["ref"])
    order = {"always fitted": 0, "do not populate": 1}
    bom = os.path.join(FAB, f"{DATE}_bom.csv")
    with open(bom, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "qty", "references", "value", "footprint", "part to buy", "LCSC", "buy qty", "note"])
        for (g, value, fp), refs in sorted(parts.items(), key=lambda kv: (order[kv[0][0]], kv[1])):
            refs = sorted(refs, key=lambda x: (len(x), x))
            shown = ", ".join(refs) if len(refs) <= 8 else f"{refs[0]} ... {refs[-1]} ({len(refs)} headers)"
            if g == "do not populate":
                src = ("", "", 0, "pads for v2 tile headers, left empty")
            elif refs[0] in SOURCE:
                src = SOURCE[refs[0]]
            else:
                fail(f"no sourcing entry for {refs[0]}")
            w.writerow([g, len(refs), shown, value, fp, *src])
            if refs[0] == "F1":
                for row in EXTRA:
                    w.writerow(row)
    print(f"{len(parts)} BOM lines -> {os.path.basename(bom)}")


if __name__ == "__main__":
    main()
