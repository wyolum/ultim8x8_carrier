"""2026-11-21 Draw a KiCad schematic of the carrier from the board itself.

Reads PADS.json (written by 2026-11-21_build_carrier.py from the saved
board) and writes one flat sheet: every footprint becomes a box symbol and
every connected pin gets a global label with its net name. Pins with no
net get a no-connect mark.

This is a drawing of the board's netlist, not an independent design
source: it cannot disagree with the board. Its use is to let a person read
the circuit.

Usage: python3 2026-11-21_build_schematic.py PADS.json OUT.kicad_sch
"""
import json
import sys
import uuid

G = 1.27                           # schematic grid
PIN = 2.54
ROOT = str(uuid.uuid5(uuid.NAMESPACE_DNS, "ultim_carrier.root"))

PICO = {1: "GP0", 2: "GP1", 3: "GND", 4: "GP2", 5: "GP3", 6: "GP4", 7: "GP5", 8: "GND", 9: "GP6",
        10: "GP7", 11: "GP8", 12: "GP9", 13: "GND", 14: "GP10", 15: "GP11", 16: "GP12", 17: "GP13",
        18: "GND", 19: "GP14", 20: "GP15", 21: "GP16", 22: "GP17", 23: "GND", 24: "GP18", 25: "GP19",
        26: "GP20", 27: "GP21", 28: "GND", 29: "GP22", 30: "RUN", 31: "GP26", 32: "GP27", 33: "AGND",
        34: "GP28", 35: "ADC_VREF", 36: "3V3", 37: "3V3_EN", 38: "GND", 39: "VSYS", 40: "VBUS"}
PI = {1: "3V3", 2: "5V", 3: "SDA", 4: "5V", 5: "SCL", 6: "GND", 7: "GPIO4", 8: "TXD", 9: "GND",
      10: "RXD", 11: "GPIO17", 12: "GPIO18", 13: "GPIO27", 14: "GND", 15: "GPIO22", 16: "GPIO23",
      17: "3V3", 18: "GPIO24", 19: "MOSI", 20: "GND", 21: "MISO", 22: "GPIO25", 23: "SCLK",
      24: "CE0", 25: "GND", 26: "CE1"}
HCT125 = {1: "/OE1", 2: "A1", 3: "Y1", 4: "/OE2", 5: "A2", 6: "Y2", 7: "GND", 8: "Y3", 9: "A3",
          10: "/OE3", 11: "Y4", 12: "A4", 13: "/OE4", 14: "VCC"}
NAMES = {"A1": {str(k): v for k, v in PICO.items()}, "J3": {str(k): v for k, v in PI.items()},
         "U1": {str(k): v for k, v in HCT125.items()}, "U2": {"1": "GND", "2": "VOUT", "3": "VIN"},
         "C1": {"1": "+", "2": "-"}, "J2": {"1": "1", "2": "2"}}
for d in ("D1", "D2", "D3", "D4"):
    NAMES[d] = {"1": "K", "2": "A"}


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, "ultim_carrier." + ".".join(str(p) for p in parts)))


def snap(v):
    return round(round(v / G) * G, 4)


FONT = "(effects (font (size 1.27 1.27)))"
HIDE = "(effects (font (size 1.27 1.27)) (hide yes))"


def order_pins(ref, pins):
    """Pins in drawing order: numeric where possible, tiles and diamonds by role."""
    role = ["5VA", "GNDA", "CI", "DI", "5VB", "GNDB", "CO", "DO", "5V", "GND"]
    def key(n):
        if n in role:
            return (0, role.index(n), "")
        return (1, int(n), "") if n.isdigit() else (2, 0, n)
    if ref == "A2":
        return list(pins)                      # keep header order from the board
    return sorted(pins, key=key)


def symbol(ref, value, pins, x, y, out):
    """pins: {number: net}. Half the pins on the left, half on the right."""
    order = order_pins(ref, pins)
    half = (len(order) + 1) // 2
    left, right = order[:half], order[half:]
    names = NAMES.get(ref, {})
    longest = max(len(names.get(n, n)) for n in order)
    w = snap(max(10.16, 2 * (longest * 1.1 + 2.5)))
    h = max(len(left), len(right)) * PIN
    top = snap(h / 2 - PIN / 2 + 0.0)
    x, y = snap(x), snap(y)
    lib = f"carrier:{ref}"
    pins_lib, inst_pins = [], []
    for side, group in ((-1, left), (1, right)):
        for i, n in enumerate(group):
            ly = snap(top - i * PIN)
            lx = snap(side * (w / 2 + PIN))
            ang = 0 if side < 0 else 180
            nm = names.get(n, n)
            pins_lib.append(
                f'(pin passive line (at {lx} {ly} {ang}) (length {PIN}) '
                f'(name "{nm}" {FONT}) (number "{n}" {FONT}))')
            inst_pins.append(f'(pin "{n}" (uuid "{uid(ref, "pin", n)}"))')
            px, py = snap(x + lx), snap(y - ly)
            net = pins[n]
            if net:
                just, a = ("right", 180) if side < 0 else ("left", 0)
                out["items"].append(
                    f'(global_label "{net}" (shape passive) (at {px} {py} {a}) '
                    f'(effects (font (size 1.27 1.27)) (justify {just})) '
                    f'(uuid "{uid(ref, "lab", n)}") '
                    f'(property "Intersheetrefs" "" (at {px} {py} 0) {HIDE}))')
            else:
                out["items"].append(f'(no_connect (at {px} {py}) (uuid "{uid(ref, "nc", n)}"))')
    body = (f'(rectangle (start {-w / 2} {snap(top + PIN)}) (end {w / 2} {snap(top - h)}) '
            f'(stroke (width 0.254) (type default)) (fill (type background)))')
    out["libs"].append(
        f'(symbol "{lib}" (pin_names (offset 0.762)) (exclude_from_sim no) (in_bom yes) (on_board yes)\n'
        f'  (property "Reference" "{ref[0]}" (at 0 {snap(top + 2 * PIN)} 0) {FONT})\n'
        f'  (property "Value" "" (at 0 {snap(top - h - PIN)} 0) {FONT})\n'
        f'  (property "Footprint" "" (at 0 0 0) {HIDE})\n'
        f'  (property "Datasheet" "" (at 0 0 0) {HIDE})\n'
        f'  (property "Description" "" (at 0 0 0) {HIDE})\n'
        f'  (symbol "{ref}_0_1" {body})\n'
        f'  (symbol "{ref}_1_1" {" ".join(pins_lib)})\n'
        f'  (embedded_fonts no))')
    val = value.replace('"', "'")
    out["items"].append(
        f'(symbol (lib_id "{lib}") (at {x} {y} 0) (unit 1) (exclude_from_sim no) (in_bom yes) '
        f'(on_board yes) (dnp no) (uuid "{uid(ref, "sym")}")\n'
        f'  (property "Reference" "{ref}" (at {x} {snap(y - top - 2 * PIN)} 0) {FONT})\n'
        f'  (property "Value" "{val}" (at {x} {snap(y - top + h + PIN)} 0) {FONT})\n'
        f'  (property "Footprint" "" (at {x} {y} 0) {HIDE})\n'
        f'  (property "Datasheet" "" (at {x} {y} 0) {HIDE})\n'
        f'  (property "Description" "" (at {x} {y} 0) {HIDE})\n'
        f'  {" ".join(inst_pins)}\n'
        f'  (instances (project "ultim_carrier" (path "/{ROOT}" (reference "{ref}") (unit 1)))))')
    return h


def text(s, x, y, size, out):
    out["items"].append(
        f'(text "{s}" (exclude_from_sim no) (at {snap(x)} {snap(y)} 0) '
        f'(effects (font (size {size} {size})) (justify left)) (uuid "{uid("text", s)}"))')


def main():
    if len(sys.argv) != 3:
        fail(__doc__)
    d = json.load(open(sys.argv[1]))
    parts, values = {}, {}
    for p in d["pads"]:
        ref = p["ref"]
        if ref[0] == "H" and ref[1:].isdigit():
            continue                               # bare screw holes
        pins = parts.setdefault(ref, {})
        if p["pad"] in pins and pins[p["pad"]] != p["net"]:
            fail(f"{ref} pad {p['pad']} is on two nets")
        pins[p["pad"]] = p["net"]
        values[ref] = p.get("value", "")
    out = dict(libs=[], items=[])
    placed = set()

    def put(ref, x, y, value=None):
        if ref not in parts:
            fail(f"{ref} is not on the board")
        placed.add(ref)
        return symbol(ref, value if value is not None else values[ref], parts[ref], x, y, out)

    text("ULTiM8x8 3x3 carrier, drawn from the board netlist 2026-11-22", 30, 20, 5.0, out)
    text("Every label is a net. Same label = same net. Generated by 2026-11-21_build_schematic.py; "
         "do not edit by hand.", 30, 30, 2.5, out)
    # supply
    text("Supply", 30, 50, 3.5, out)
    y = 70
    for ref in ("J2", "F1", "D4", "C1"):
        y += put(ref, 70, y) + 25
    # controller
    text("Pico 2 W", 150, 50, 3.5, out)
    put("A1", 185, 105)
    put("D1", 185, 160)
    # tiles in their physical arrangement, top row at the top
    text("Tiles as arranged on the board, LED-side view. Signal order T0 -> T8. "
         "Small boxes are the optional 2x2 diamond headers for v2 tiles.", 290, 50, 3.5, out)
    for n, (col, row) in enumerate(d["chain"]):
        cx, cy = 390 + (col + 1) * 210, 120 + (1 - row) * 140
        put(f"T{n}", cx, cy, "ULTiM8x8 tile" + (", turned 180" if row == 0 else ""))
        for name, dx, dy in (("In1", -70, -25), ("In2", -70, 25), ("Out1", 70, -25), ("Out2", 70, 25)):
            ref = f"T{n}{name}"
            if ref in parts:
                put(ref, cx + dx, cy + dy, name)
    missing = sorted(set(parts) - placed)
    if missing:
        fail(f"not drawn: {missing}")
    sch = (f'(kicad_sch (version 20250114) (generator "ultim_carrier_script") (generator_version "9.0")\n'
           f' (uuid "{ROOT}") (paper "User" 900 480)\n'
           f' (title_block (title "ULTiM8x8 3x3 carrier") (date "2026-11-22") (rev "0.2 draft") (company "WyoLum")\n'
           f'  (comment 1 "Draft for review. Not fabricated. Do not order.")\n'
           f'  (comment 2 "Label-only schematic derived from the board: same label, same net")\n'
           f'  (comment 3 "github.com/wyolum/ultim8x8_carrier")\n'
           f'  (comment 4 "CERN OHL v1.2. Generated by 2026-11-21_build_schematic.py"))\n'
           f' (lib_symbols\n  ' + "\n  ".join(out["libs"]) + '\n )\n '
           + "\n ".join(out["items"])
           + f'\n (sheet_instances (path "/" (page "1")))\n (embedded_fonts no))\n')
    open(sys.argv[2], "w").write(sch)
    print(f"{len(placed)} symbols, {sum(len(v) for v in parts.values())} pins -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
