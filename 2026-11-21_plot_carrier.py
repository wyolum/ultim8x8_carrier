"""2026-11-21 Check picture for the carrier PCB: every pad read back from the
saved board, colored by net, seen from the LED side.

Usage: python3 2026-11-21_plot_carrier.py PADS.json OUT.png
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def color(net):
    if net == "+5V":
        return "#d0312d"
    if net == "GND":
        return "#16181c"
    if net.startswith("CLK"):
        return "#e0a800"
    if net.startswith("DAT"):
        return "#1f77b4"
    return "#9aa0a6"


def main():
    if len(sys.argv) != 3:
        fail(__doc__)
    d = json.load(open(sys.argv[1]))
    tile, outer = d["tile"], d["outer"]
    # tile terminals (T0..T8) and perimeter screw holes (H0..H7) only
    pads = [p for p in d["pads"] if p["ref"][0] in "TH" and p["ref"][1:].isdigit()]
    plated = [p for p in pads if p["plated"]]
    if len(plated) != 72:
        fail(f"expected 72 plated tile holes, found {len(plated)}")

    fig, ax = plt.subplots(figsize=(11, 11))
    h = outer / 2
    ax.add_patch(plt.Rectangle((-h, -h), outer, outer, fill=False, lw=1.5, color="0.3"))
    for n, (col, row) in enumerate(d["chain"]):
        ax.add_patch(plt.Rectangle((col * tile - tile / 2, row * tile - tile / 2), tile, tile,
                                   fill=False, lw=0.8, ls="--", color="0.6"))
        turned = ", turned 180" if row == 0 else ""
        ax.text(col * tile, row * tile, f"T{n}{turned}", ha="center", va="center",
                fontsize=10, color="0.35")
    for p in pads:
        if p["plated"]:
            ax.add_patch(plt.Circle((p["x"], p["y"]), p["size"] / 2, color=color(p["net"])))
            ax.add_patch(plt.Circle((p["x"], p["y"]), p["drill"] / 2, color="white"))
            ax.text(p["x"], p["y"] - 5.4, p["net"], ha="center", va="center", fontsize=6.5)
        else:
            ax.add_patch(plt.Circle((p["x"], p["y"]), p["drill"] / 2, fill=False, color="0.3"))
    # signal order: arrows from each tile's outputs to the next tile's inputs
    by = {(p["ref"], p["pad"]): p for p in pads}
    for n in range(len(d["chain"]) - 1):
        for o, i in (("CO", "CI"), ("DO", "DI")):
            a, b = by[(f"T{n}", o)], by[(f"T{n + 1}", i)]
            if a["net"] != b["net"]:
                fail(f"T{n}.{o} is on {a['net']} but T{n + 1}.{i} is on {b['net']}")
            ax.annotate("", xy=(b["x"], b["y"]), xytext=(a["x"], a["y"]),
                        arrowprops=dict(arrowstyle="->", color=color(a["net"]), lw=1.2,
                                        shrinkA=9, shrinkB=9))
    ax.set_xlim(-h - 6, h + 6)
    ax.set_ylim(-h - 6, h + 6)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("Tile terminals read back from the board, LED-side view: red 5 V, black GND, yellow clock, blue data\n"
                 f"board edge {d['edge_w']:.2f} x {d['edge_h']:.2f} mm, "
                 "arrows show the signal order")
    fig.tight_layout()
    fig.savefig(sys.argv[2], dpi=150)
    print(f"{len(plated)} tile holes, {len(pads) - len(plated)} screw holes -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
