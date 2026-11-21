"""2026-11-21 Build the carrier PCB for the 3x3 ULTiM8x8 light box.

Step 1: board outline, the eight perimeter screw holes and the 72 tile
terminal holes with their nets.
Step 2: GND pour on the front (tile side), +5V pour on the back, and the
clock and data traces from tile to tile on the front.
Step 3: the input block on the back: J2 screw terminal for the 5 V supply
and C1 bulk capacitor in the pad-free square between tiles T1 and T4; a
Pico 2 W on two 1x20 sockets (A1) behind tile T0; D1 Schottky from +5V to
VSYS so USB cannot back-feed the LED rail; U1 74AHCT125 level shifter with
C2 under the Pico.
  clock: Pico GP6 (pin 9, SPI0 SCK) -> U1 pin 9  -> pin 8  -> tile T0 CI
  data:  Pico GP3 (pin 5, SPI0 TX)  -> U1 pin 12 -> pin 11 -> tile T0 DI
Without U1, bridge its pins 8-9 and 11-12 with solder.
Step 4: two alternative controllers on the same clock and data lines (fit
one controller only):
  A2  Arduino UNO, plugged face down on male headers, USB end overhanging
      toward the +x edge. D13 = clock, D11 = data. D2 feeds its 5V pin.
  J3  2x13 male header laid out like a Raspberry Pi P1, for a WyoLum AlaMode.
      Pin 23 (SCK) = clock, pin 19 (MOSI) = data. The AlaMode's TXS0108
      translator needs 3.3 V on pin 1, made here by U2 (MCP1700-3302) with
      C3 and C4. D3 feeds 5 V to pins 2 and 4.
Step 6: protection and test points. F1 mini blade fuse holder between J2
and the +5V pour, D4 across the supply after the fuse (cathode on +5V) so a
reversed supply blows the fuse, and test pads TP1 CLK_IN, TP2 DAT_IN,
TP3 GND, TP4 +5V on the clock/data pair.
Step 5: the v2 tile's four 2x2 "diamond" headers (In1, In2, Out1, Out2)
under every tile, except three that a controller header sits on. Every
tile keeps at least one In and one Out.

Run with KiCad's own Python:
  KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
  $KP 2026-11-21_build_carrier.py OUT.kicad_pcb [PADS.json]
With PADS.json it also reads the saved board back and dumps every pad, for
the check picture (2026-11-21_plot_carrier.py).
"""
import json
import sys

import pcbnew

MM = pcbnew.FromMM

# --- geometry, in mm. Must match scad/2026-11-15_lightbox.scad ---
TILE = 60.96
OUTER = 208.0
CORNER_R = 4.0
ROD_C = 98.0                       # perimeter screw circle
P1, P3 = 7.62, 22.86
CENTER = (150.0, 150.0)            # board center on the KiCad page

# Tile terminals, LED-side view, x right and y up, tile not turned.
# name: (x, y, net role)
TILE_PADS = {
    "5VA": (-P3, P3, "5V"), "5VB": (P3, P3, "5V"),
    "GNDA": (-P3, -P3, "GND"), "GNDB": (P3, -P3, "GND"),
    "CI": (-P1, P1, "CI"), "CO": (P1, P1, "CO"),
    "DI": (-P1, -P1, "DI"), "DO": (P1, -P1, "DO"),
}
# Signal order: in at the lower-left tile, along the bottom row, back along
# the middle row (turned 180 degrees), then along the top row.
CHAIN = [(-1, -1), (0, -1), (1, -1), (1, 0), (0, 0), (-1, 0), (-1, 1), (0, 1), (1, 1)]

# The v2 tile also has four 2x2 pin headers turned 45 degrees ("diamonds"),
# 15.24 from the tile center. Pin positions and roles read from the v2 layout
# (ultim8x8.kicad_pcb, P1 In1, P2 Out1, P5 In2, P6 Out2), LED-side view:
D = 1.796
# Left out: the Pico's lower pin row crosses T0 Out1, the AlaMode header
# crosses T7 Out1, the clock/data pair to that header crosses T7 In2, and the
# UNO power header crosses T8 Out1.
DIAMOND_SKIP = {(0, "Out1"), (7, "Out1"), (7, "In2"), (8, "Out1")}
DIAMONDS = {
    "In1":  ((-15.24, 0.0), {"CI": (D, 0), "GND": (-D, 0), "5V": (0, D), "DI": (0, -D)}),
    "Out2": ((15.24, 0.0),  {"CO": (-D, 0), "GND": (D, 0), "5V": (0, D), "DO": (0, -D)}),
    "Out1": ((0.0, 15.24),  {"CO": (0, -D), "GND": (0, D), "5V": (-D, 0), "DO": (D, 0)}),
    "In2":  ((0.0, -15.24), {"CI": (0, D), "GND": (0, -D), "5V": (-D, 0), "DI": (D, 0)}),
}
TILE_DRILL = 3.2                   # M3 clearance
TILE_PAD = 7.0                     # seat for a 5.5 mm hex standoff (6.35 across corners)
SCREW_DRILL = 3.2                  # perimeter holes, not plated
INNER = 184.0                      # frame opening; the walls and screws sit outside it
POUR = INNER - 2.0                 # copper stays 1 mm inside the frame opening, so no
                                   # copper lies under a wall or a perimeter screw head
SIG_W = 0.5                        # clock and data trace width
POUR_CLEAR = 0.4                   # pour to other copper
FINE_W = 0.25                      # traces at the level shifter
VIA_D, VIA_DRILL = 0.8, 0.4
FPD = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
# Supply entry, board mm, LED-side view, parts on the back: J2 and C1 in the
# square between tiles T1 and T4 that has no tile pad, screw head or diamond.
FREE_BOX = (-19.3, -42.2, 19.3, -18.7)     # x0, y0, x1, y1
J2_AT = (-9.0, -35.0)               # every through-hole pad here stays off the tile seam at
C1_AT = (9.5, -34.5)                # y = -30.48, where the front silkscreen outlines run
F1_AT = (-9.0, -23.0)
D4_AT = (10.5, -23.0)
VIN_W = 3.0                        # J2 to fuse, on both layers
TEST_POINTS = (("TP1", "CLK_IN", "CLK", (-33.0, 10.0), (-30.9, 10.0), False),
               ("TP2", "DAT_IN", "DAT", (-28.0, 14.0), (-30.05, 14.0), False),
               ("TP3", "GND", "GND", (-33.0, 18.0), None, True),
               ("TP4", "+5V", "5V", (-28.0, 6.0), None, False))
# Pico 2 W: USB end toward the -x wall, top facing the rear cover. Tile holes
# lie on a 15.24 grid; a Pico centered on a hole row puts its two pin rows
# 6.35 and 8.89 from the nearest hole rows, so no pin meets a tile pad.
# Centered on y = -38.1 the upper row runs beside a tile seam, where there
# are no diamond headers, and the lower row only crosses T0 Out1.
PICO_Y = -38.1
PICO_ROW = 17.78                   # between the pin rows
PICO_X1 = -92.0 + 1.5 + 1.37       # pin 1: board end 1.5 from the old wall line, pin 1.37 from the end
PICO_SIZE = (51.0, 21.0)
PICO_GND = (3, 8, 13, 18, 23, 28, 38)
PICO_CLK, PICO_DAT = 9, 5          # GP6 = SPI0 SCK, GP3 = SPI0 TX
U1_AT = (-72.0, PICO_Y)            # under the Pico, between its pin rows
C2_AT = (-78.7, -39.6)
D1_AT = (-86.59, -51.4)
TURN_JOG = 4.27                    # row-turn side step: between the hole column and the diamond pins
# Arduino UNO, face down. In the LED-side view that is the UNO's top view,
# here turned 180 degrees so the USB end points at +x. Standard UNO
# coordinates (u from the USB edge, v from the power-header edge, mm):
UNO_X0 = 100.0                     # USB edge; the connectors overhang past the outer tile screws
UNO_Y0 = 78.51                     # power-header edge. Rows land 4.85 and 7.85 from the hole rows.
UNO_SIZE = (68.58, 53.34)
UNO_POWER = [("NC", 27.94), ("IOREF", 30.48), ("RESET", 33.02), ("3V3", 35.56), ("5V", 38.1),
             ("GND1", 40.64), ("GND2", 43.18), ("VIN", 45.72)] + \
            [(f"A{i}", 50.8 + 2.54 * i) for i in range(6)]
UNO_DIGITAL = [(f"D{i}", 63.5 - 2.54 * i) for i in range(8)] + \
              [(f"D{8 + i}", 41.656 - 2.54 * i) for i in range(6)] + \
              [("GND3", 26.416), ("AREF", 23.876), ("SDA", 21.336), ("SCL", 18.796)]
D2_AT = (61.9, 79.6)
# AlaMode on a Pi-style 2x13 header. Seen from the back it is the AlaMode's
# top view: socket at its top-left corner. Pin 21 sits on x = 0 so the clock
# and data pins straddle the column between the tile holes.
ALA_TOP = 79.756                   # AlaMode top edge; rows land 6.35 and 8.89 above a hole row
ALA_X1 = 25.4                      # pins 1 and 2
ALA_SIZE = (85.09, 55.88)
ALA_GND = (6, 14, 20, 25)           # pin 9 is boxed in by the 3.3 V track; the AlaMode only uses pin 6
D3_AT = (28.0, 74.35)
U2_AT = (-12.0, 76.3)
C3_AT = (-17.5, 75.6)
C4_AT = (-13.978, 79.3)



def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def pt(x, y):
    """Board mm (center origin, y up) to KiCad page coordinates."""
    return pcbnew.VECTOR2I(MM(CENTER[0] + x), MM(CENTER[1] - y))


def net_name(role, n):
    """Net for a tile terminal. CLKn and DATn feed tile n; n = 9 leaves the last tile."""
    if role == "5V":
        return "+5V"
    if role == "GND":
        return "GND"
    return {"CI": f"CLK{n}", "CO": f"CLK{n + 1}", "DI": f"DAT{n}", "DO": f"DAT{n + 1}"}[role]


def add_outline(board):
    h, r = OUTER / 2, CORNER_R
    k = r * (1 - 2 ** -0.5)        # arc midpoint inset from the square corner
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        # straight edge leaving this corner, going counter-clockwise
        a = (sx * h, sy * (h - r)) if sx * sy > 0 else (sx * (h - r), sy * h)
        nx, ny = (-sy, sx)         # next corner, counter-clockwise
        b = (nx * h, ny * (h - r)) if nx * ny < 0 else (nx * (h - r), ny * h)
        seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        if sx * sy > 0:
            seg.SetStart(pt(sx * (h - r), sy * h))
            seg.SetEnd(pt(nx * (h - r), ny * h))
        else:
            seg.SetStart(pt(sx * h, sy * (h - r)))
            seg.SetEnd(pt(nx * h, ny * (h - r)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(MM(0.1))
        board.Add(seg)
        arc = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        arc.SetArcGeometry(pt(sx * h, sy * (h - r)), pt(sx * (h - k), sy * (h - k)),
                           pt(sx * (h - r), sy * h))
        arc.SetLayer(pcbnew.Edge_Cuts)
        arc.SetWidth(MM(0.1))
        board.Add(arc)
        del a, b


def add_text(fp, text, x, y, size=1.5, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(fp)
    t.SetText(text)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(-y)))
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    t.SetLayer(layer)
    fp.Add(t)


def add_tile(board, nets, n, col, row):
    """One footprint per tile: 8 plated terminal holes. Built unturned at the
    origin, then turned 180 degrees for the middle row and moved into place."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(f"T{n}")
    fp.SetValue("ULTiM8x8")
    fp.Reference().SetPosition(pcbnew.VECTOR2I(0, MM(-27)))
    fp.Value().SetVisible(False)
    for name, (x, y, role) in TILE_PADS.items():
        pad = pcbnew.PAD(fp)
        pad.SetNumber(name)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(MM(TILE_PAD), MM(TILE_PAD)))
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(TILE_DRILL), MM(TILE_DRILL)))
        pad.SetLayerSet(pad.PTHMask())
        pad.SetPosition(pcbnew.VECTOR2I(MM(x), MM(-y)))
        pad.SetNet(nets[net_name(role, n)])
        fp.Add(pad)
        t = -1 if row == 0 else 1
        lx, ly = col * TILE + t * x, row * TILE + t * (y - 5.2)    # where the label lands
        headers = [pico_pin(k) for k in range(1, 41)] + list(uno_pins().values()) + \
                  [ala_pin(k) for k in range(1, 27)]
        headers += [(col * TILE + t * (ox + dx), row * TILE + t * (oy + dy))
                    for (ox, oy), pins in DIAMONDS.values() for dx, dy in pins.values()]
        if all(abs(lx - px) > 2.5 or abs(ly - py) > 1.8 for px, py in headers):
            add_text(fp, name.rstrip("AB"), x, y - 5.2, size=1.2)   # skip one that would sit on a header pin
    s = TILE / 2 - 0.3
    for a, b in (((-s, -s), (s, -s)), ((s, -s), (s, s)), ((s, s), (-s, s)), ((-s, s), (-s, -s))):
        line = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
        line.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(-a[1])))
        line.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(-b[1])))
        line.SetLayer(pcbnew.F_SilkS)
        line.SetWidth(MM(0.15))
        fp.Add(line)
    if row == 0:
        fp.SetOrientationDegrees(180)
    fp.SetPosition(pt(col * TILE, row * TILE))
    board.Add(fp)


def pad_xy(n, name):
    """Board position of a tile terminal, mm, y up."""
    col, row = CHAIN[n]
    t = -1 if row == 0 else 1
    x, y, _ = TILE_PADS[name]
    return (col * TILE + t * x, row * TILE + t * y)


def add_track(board, net, pts, layer=pcbnew.F_Cu, w=SIG_W):
    for a, b in zip(pts[:-1], pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(MM(w))
        t.SetLayer(layer)
        t.SetNet(net)
        board.Add(t)


def add_signals(board, nets):
    """Clock and data from each tile's outputs to the next tile's inputs.
    Along a row the hop is a straight line. At a row turn both hops share one
    column, so the longer one steps TURN_JOG outward around the shorter one's
    pads, inside the diamond headers."""
    for n in range(len(CHAIN) - 1):
        hops = []
        for sig, o, i in (("CLK", "CO", "CI"), ("DAT", "DO", "DI")):
            hops.append((nets[f"{sig}{n + 1}"], pad_xy(n, o), pad_xy(n + 1, i)))
        if CHAIN[n][1] == CHAIN[n + 1][1]:
            for net, a, b in hops:
                if abs(a[1] - b[1]) > 1e-6:
                    fail(f"row hop into tile {n + 1} is not horizontal")
                add_track(board, net, [a, b])
            continue
        if any(abs(a[0] - b[0]) > 1e-6 for _, a, b in hops):
            fail(f"row turn into tile {n + 1} is not vertical")
        hops.sort(key=lambda h: abs(h[1][1] - h[2][1]))
        net, a, b = hops[0]
        add_track(board, net, [a, b])
        net, a, b = hops[1]
        out = TURN_JOG if a[0] > 0 else -TURN_JOG      # away from the board center
        up = 1 if b[1] > a[1] else -1
        add_track(board, net, [a, (a[0] + out, a[1] + up * TURN_JOG),
                               (b[0] + out, b[1] - up * TURN_JOG), b])


def add_pour(board, net, layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    o = z.Outline()
    o.NewOutline()
    h = POUR / 2
    for x, y in ((-h, -h), (h, -h), (h, h), (-h, h)):
        p = pt(x, y)
        o.Append(p.x, p.y)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # screw contacts, nothing soldered
    z.SetLocalClearance(MM(POUR_CLEAR))
    z.SetMinThickness(MM(0.25))
    z.SetThermalReliefGap(MM(0.4))
    z.SetThermalReliefSpokeWidth(MM(0.6))
    board.Add(z)


def add_via(board, net, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(pcbnew.F_Cu, MM(VIA_D))
    v.SetDrill(MM(VIA_DRILL))
    v.SetNet(net)
    board.Add(v)


def xy(pad):
    """Pad position in board mm, y up."""
    p = pad.GetPosition()
    return (pcbnew.ToMM(p.x) - CENTER[0], CENTER[1] - pcbnew.ToMM(p.y))


def place_back(board, lib, name, ref, value, at, rot):
    """Load a library footprint, put it on the back, and move it so the
    centroid of its pads is at `at`."""
    fp = pcbnew.FootprintLoad(FPD + lib + ".pretty", name)
    if fp is None:
        fail(f"footprint {lib}:{name} not found")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(pt(0, 0))
    board.Add(fp)                  # Flip crashes on a footprint that is not on a board
    fp.Flip(pt(0, 0), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    pads = [xy(p) for p in fp.Pads()]
    cx = sum(p[0] for p in pads) / len(pads)
    cy = sum(p[1] for p in pads) / len(pads)
    fp.Move(pcbnew.VECTOR2I(MM(at[0] - cx), MM(-(at[1] - cy))))
    return fp


def near(a, b, tol=0.01):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def relief(pad):
    """Thermal relief for a soldered pad that sits in a pour."""
    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_THERMAL)


def back_label(board, text, x, y, size=1.0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pt(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    t.SetLayer(pcbnew.B_SilkS)
    t.SetMirrored(True)
    board.Add(t)


def pico_pin(n):
    """Pico pin position, board mm. Pins 1-20 on the upper row from the USB
    end, pins 40-21 on the lower row from the USB end."""
    if n <= 20:
        return (PICO_X1 + 2.54 * (n - 1), PICO_Y + PICO_ROW / 2)
    return (PICO_X1 + 2.54 * (40 - n), PICO_Y - PICO_ROW / 2)


def add_pico(board, nets):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("A1")
    fp.SetValue("Pico 2 W on 1x20 sockets")
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    net_of = {n: nets["GND"] for n in PICO_GND}
    net_of.update({PICO_CLK: nets["CLK_IN"], PICO_DAT: nets["DAT_IN"], 39: nets["VSYS"]})
    for n in range(1, 41):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(n))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT if n == 1 else pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(MM(1.7), MM(1.7)))
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        pad.SetLayerSet(pad.PTHMask())
        pad.SetPosition(pt(*pico_pin(n)))
        if n in net_of:
            pad.SetNet(net_of[n])
        if n in PICO_GND:
            relief(pad)
        fp.Add(pad)
    board.Add(fp)
    x0 = PICO_X1 - 1.37
    fab_box(board, x0, PICO_Y - PICO_SIZE[1] / 2, x0 + PICO_SIZE[0], PICO_Y + PICO_SIZE[1] / 2)
    y1 = PICO_Y + PICO_SIZE[1] / 2
    back_label(board, "Pico 2 W, socketed", -55.0, PICO_Y + 3.6, 1.1)
    back_label(board, "USB", x0 + 2.6, PICO_Y + 6.3, 1.0)
    back_label(board, "1", x0 + 1.4, y1 + 1.0, 1.0)
    return fp


def add_input_block(board, nets):
    B = pcbnew.B_Cu
    gnd, v5 = nets["GND"], nets["+5V"]
    add_pico(board, nets)

    # U1 under the Pico: pins 1-7 along the top with pin 1 at the left, so
    # pins 14-8 run left to right along the bottom, facing tile T0.
    u1 = place_back(board, "Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm", "U1", "74AHCT125", U1_AT, 0)
    cx, cy = U1_AT
    for rot in (0, 90, 180, 270):  # the pads are symmetric about the origin, so it turns in place
        u1.SetOrientationDegrees(rot)
        if near(xy(u1.FindPadByNumber("1")), (cx - 3.81, cy + 2.475)):
            break
    else:
        fail("no rotation puts U1 pin 1 at the upper left")
    pin = {n: xy(u1.FindPadByNumber(str(n))) for n in range(1, 15)}
    # gate 4 (12 in, 11 out) buffers the data and gate 3 (9 in, 8 out) the
    # clock; gates 1 and 2 are parked with inputs and enables grounded
    u1_nets = {1: gnd, 2: gnd, 4: gnd, 5: gnd, 7: gnd, 8: nets["CLK0"], 9: nets["CLK_IN"],
               10: gnd, 11: nets["DAT0"], 12: nets["DAT_IN"], 13: gnd, 14: v5}
    for n, net in u1_nets.items():
        u1.FindPadByNumber(str(n)).SetNet(net)
    relief(u1.FindPadByNumber("14"))
    # ground: a strip under the body, a stub from each grounded pin, two vias to the front pour
    add_track(board, gnd, [(cx - 3.81, cy), (cx + 3.81, cy)], B, 0.5)
    for n in (1, 2, 4, 5, 7, 10, 13):
        add_track(board, gnd, [pin[n], (pin[n][0], cy)], B, 0.4)
    for dx in (-3.4, 0.63):                              # clear of the two input tracks on the front
        add_via(board, gnd, cx + dx, cy)

    # inputs: from the Pico pins on the front, under U1, to a via below each input pin
    yv = pin[12][1] - 2.6
    for src, dst, net in ((PICO_DAT, 12, nets["DAT_IN"]), (PICO_CLK, 9, nets["CLK_IN"])):
        a, b = pico_pin(src), pin[dst]
        add_track(board, net, [a, (a[0], a[1] - 1.8), (b[0], a[1] - 1.8 - abs(a[0] - b[0])), (b[0], yv)],
                  pcbnew.F_Cu, FINE_W)
        add_via(board, net, b[0], yv)
        add_track(board, net, [(b[0], yv), b], B, FINE_W)
    # outputs: down between two pins of the Pico's lower row, then into tile T0
    ci, di = pad_xy(0, "CI"), pad_xy(0, "DI")
    row_y = pico_pin(40)[1]
    lower_x = sorted(pico_pin(n)[0] for n in range(21, 41))

    def gap_near(x):
        mids = [(a + b) / 2 for a, b in zip(lower_x[:-1], lower_x[1:])]
        return min(mids, key=lambda m: abs(m - x))
    x, y = pin[11]                                       # data: past the left side of the CI pad to DI
    xg = gap_near(x - 0.5)
    yd = di[1] + abs(di[0] - xg)
    add_track(board, nets["DAT0"], [(x, y), (x, row_y + 2.6), (xg, row_y + 2.6 - abs(xg - x)),
                                    (xg, yd), di], B, FINE_W)
    x, y = pin[8]                                        # clock: straight down into CI
    xg = gap_near(x + 0.5)
    add_track(board, nets["CLK0"], [(x, y), (x, row_y + 2.6), (xg, row_y + 2.6 - abs(xg - x)),
                                    (xg, ci[1] + abs(ci[0] - xg)), ci], B, FINE_W)

    # C2: decoupling at U1 pin 14, lower pad level with the pin
    c2 = place_back(board, "Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder",
                    "C2", "100n", C2_AT, 90)
    c2_pads = sorted(c2.Pads(), key=lambda p: xy(p)[1])
    c2_pads[0].SetNet(v5)
    c2_pads[1].SetNet(gnd)
    relief(c2_pads[0])
    c2.Reference().SetPosition(pt(C2_AT[0] + 0.2, C2_AT[1] - 3.3))
    add_track(board, v5, [pin[14], xy(c2_pads[0])], B, 0.4)
    g = xy(c2_pads[1])
    add_track(board, gnd, [g, (g[0], g[1] + 2.1)], B, 0.4)
    add_via(board, gnd, g[0], g[1] + 2.1)

    # D1: +5V -> VSYS, cathode toward Pico pin 39
    d1 = place_back(board, "Diode_SMD", "D_SOD-123", "D1", "MBR120 / 1N5819W", D1_AT, 90)
    for rot in (90, 270):
        d1.SetOrientationDegrees(rot)
        if xy(d1.FindPadByNumber("1"))[1] > xy(d1.FindPadByNumber("2"))[1]:
            break
    else:
        fail("D1 cathode does not point at the Pico")
    d1.FindPadByNumber("1").SetNet(nets["VSYS"])
    d1.FindPadByNumber("2").SetNet(v5)
    relief(d1.FindPadByNumber("2"))
    add_track(board, nets["VSYS"], [xy(d1.FindPadByNumber("1")), pico_pin(39)], B, 0.5)

    # J2: supply in, then F1, then the +5V pour. Solid pour connections on
    # this path, it carries the full current.
    vin = nets["VIN"]
    j2 = place_back(board, "TerminalBlock_Phoenix",
                    "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
                    "J2", "5V in", J2_AT, 90)
    j2_pads = sorted(j2.Pads(), key=lambda p: -xy(p)[1])
    j2_pads[0].SetNet(vin)
    j2_pads[1].SetNet(gnd)
    for pad, text in zip(j2_pads, ("+5V", "GND")):
        back_label(board, text, J2_AT[0] - 8.0, xy(pad)[1], 1.0)
    f1 = place_back(board, "Fuse", "Fuseholder_Blade_Mini_Keystone_3568", "F1",
                    "mini blade fuse, rating to suit the supply", F1_AT, 0)
    f_in = sorted((p for p in f1.Pads() if p.GetNumber() == "1"), key=lambda p: xy(p)[1])
    for pad in f1.Pads():
        pad.SetNet(vin if pad.GetNumber() == "1" else v5)
    a, lo, hi = xy(j2_pads[0]), xy(f_in[0]), xy(f_in[1])
    for layer in (pcbnew.F_Cu, B):
        add_track(board, vin, [a, (lo[0], a[1] + abs(lo[0] - a[0])), lo, hi], layer, VIN_W)
    f1.Reference().SetPosition(pt(F1_AT[0], F1_AT[1] + 4.6))
    # D4: across the supply after the fuse, cathode on +5V. Reversed supply
    # forward-biases it and blows F1. Anode to the ground pour through four vias.
    d4 = place_back(board, "Diode_SMD", "D_SMC", "D4", "SS54 or S5B", D4_AT, 0)
    d4.FindPadByNumber("1").SetNet(v5)
    d4.FindPadByNumber("2").SetNet(gnd)
    relief(d4.FindPadByNumber("1"))
    an = xy(d4.FindPadByNumber("2"))
    out = 1 if an[0] > D4_AT[0] else -1
    for dy in (-1.8, -0.6, 0.6, 1.8):
        add_via(board, gnd, an[0] + out * 2.6, an[1] + dy)
    add_track(board, gnd, [an, (an[0] + out * 2.6, an[1])], B, 3.0)
    d4.Reference().SetPosition(pt(D4_AT[0], D4_AT[1] + 4.6))

    # C1: bulk capacitor, pad 1 is the positive lead
    c1 = place_back(board, "Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm", "C1", "1000u 10V", C1_AT, 0)
    c1.FindPadByNumber("1").SetNet(v5)
    c1.FindPadByNumber("2").SetNet(gnd)
    for pad in c1.Pads():
        relief(pad)

    # the tall parts must stay inside the pad-free square
    for fp in (j2, c1, f1, d4):
        box = fp.GetCourtyard(pcbnew.B_CrtYd).BBox()
        x0, x1 = pcbnew.ToMM(box.GetLeft()) - CENTER[0], pcbnew.ToMM(box.GetRight()) - CENTER[0]
        y0, y1 = CENTER[1] - pcbnew.ToMM(box.GetBottom()), CENTER[1] - pcbnew.ToMM(box.GetTop())
        print(f"  {fp.GetReference()}: x {x0:.2f} to {x1:.2f}, y {y0:.2f} to {y1:.2f}")
        if x0 < FREE_BOX[0] or y0 < FREE_BOX[1] or x1 > FREE_BOX[2] or y1 > FREE_BOX[3]:
            fail(f"{fp.GetReference()} leaves the pad-free square {FREE_BOX}")
    back_label(board, "ULTiM8x8 3x3 carrier  2026-11-21  wyolum.com", 45.0, -95.5, 1.5)


def uno_pins():
    """UNO header pins: name -> board mm."""
    pins = {name: (UNO_X0 - u, UNO_Y0 - 2.54) for name, u in UNO_POWER}
    pins.update({name: (UNO_X0 - u, UNO_Y0 - 50.8) for name, u in UNO_DIGITAL})
    return pins


def ala_pin(n):
    """Pi-header pin position. Odd pins on the lower row, pin 1 at +x."""
    k = (n - 1) // 2
    return (ALA_X1 - 2.54 * k, ALA_TOP - (4.826 if n % 2 else 2.286))


def header_footprint(board, ref, value, pins, net_of, reliefs):
    """A footprint of plain 1.0 mm drilled header pads. pins: name -> (x, y)."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    for i, (name, (x, y)) in enumerate(pins.items()):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(name))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT if i == 0 else pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(MM(1.7), MM(1.7)))
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        pad.SetLayerSet(pad.PTHMask())
        pad.SetPosition(pt(x, y))
        if name in net_of:
            pad.SetNet(net_of[name])
        if name in reliefs:
            relief(pad)
        fp.Add(pad)
    board.Add(fp)
    return fp


def fab_box(board, x0, y0, x1, y1):
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        line = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        line.SetStart(pt(*a))
        line.SetEnd(pt(*b))
        line.SetLayer(pcbnew.B_Fab)
        line.SetWidth(MM(0.15))
        board.Add(line)


def diode(board, ref, at, cathode_up, k_net, a_net):
    """SOD-123 Schottky on the back, vertical. Returns the cathode position."""
    d = place_back(board, "Diode_SMD", "D_SOD-123", ref, "MBR120 / 1N5819W", at, 90)
    for rot in (90, 270):
        d.SetOrientationDegrees(rot)
        if (xy(d.FindPadByNumber("1"))[1] > xy(d.FindPadByNumber("2"))[1]) == cathode_up:
            break
    else:
        fail(f"{ref} cathode does not point the right way")
    d.FindPadByNumber("1").SetNet(k_net)
    d.FindPadByNumber("2").SetNet(a_net)
    relief(d.FindPadByNumber("2"))
    return xy(d.FindPadByNumber("1"))


def add_uno(board, nets):
    pins = uno_pins()
    net_of = {"GND1": nets["GND"], "GND2": nets["GND"], "GND3": nets["GND"],
              "5V": nets["UNO_5V"], "D13": nets["CLK_IN"], "D11": nets["DAT_IN"]}
    header_footprint(board, "A2", "Arduino UNO, face down on male headers", pins, net_of,
                     ("GND1", "GND2", "GND3"))
    k = diode(board, "D2", D2_AT, False, nets["UNO_5V"], nets["+5V"])
    add_track(board, nets["UNO_5V"], [k, pins["5V"]], pcbnew.B_Cu, 0.5)
    fab_box(board, UNO_X0 - UNO_SIZE[0], UNO_Y0 - UNO_SIZE[1], UNO_X0, UNO_Y0)
    fab_box(board, UNO_X0 - 10.0, UNO_Y0 - 44.5, UNO_X0 + 6.35, UNO_Y0 - 32.4)     # USB-B
    fab_box(board, UNO_X0 - 12.5, UNO_Y0 - 12.2, UNO_X0 + 1.8, UNO_Y0 - 3.2)      # DC jack
    back_label(board, "UNO, face down, USB at this edge", 60.96, 41.4, 1.2)
    return pins


def add_alamode(board, nets):
    B = pcbnew.B_Cu
    gnd, v5, v33 = nets["GND"], nets["+5V"], nets["ALA_3V3"]
    pins = {n: ala_pin(n) for n in range(1, 27)}
    net_of = {n: gnd for n in ALA_GND}
    net_of.update({1: v33, 2: nets["ALA_5V"], 4: nets["ALA_5V"],
                   19: nets["DAT_IN"], 23: nets["CLK_IN"]})
    header_footprint(board, "J3", "2x13 male, Pi P1 layout, for AlaMode", pins, net_of, ALA_GND)
    # 5 V to pins 2 and 4 through D3
    k = diode(board, "D3", D3_AT, True, nets["ALA_5V"], v5)
    for fp in board.GetFootprints():
        if fp.GetReference() == "D3":
            fp.Reference().SetPosition(pt(D3_AT[0], D3_AT[1] - 4.0))
    add_track(board, nets["ALA_5V"], [k, pins[2], pins[4]], B, 0.5)
    # U2: 3.3 V for the AlaMode's translator. SOT-23: 1 GND, 2 VOUT, 3 VIN.
    u2 = place_back(board, "Package_TO_SOT_SMD", "SOT-23", "U2", "MCP1700-3302", U2_AT, 0)
    p1, p2, p3 = (xy(u2.FindPadByNumber(n)) for n in "123")
    if not (p3[0] > p1[0] and p2[1] > p1[1]):
        fail("U2 is not oriented as the routing expects")
    u2.FindPadByNumber("1").SetNet(gnd)
    u2.FindPadByNumber("2").SetNet(v33)
    u2.FindPadByNumber("3").SetNet(v5)
    relief(u2.FindPadByNumber("3"))
    gv = (p1[0] - 1.96, p1[1])
    add_track(board, gnd, [p1, gv], B, 0.4)
    add_via(board, gnd, *gv)
    # C3 on the input: lower pad to ground through U2's via, upper pad in the +5V pour
    c3 = place_back(board, "Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder",
                    "C3", "1u", C3_AT, 90)
    lo, hi = sorted(c3.Pads(), key=lambda p: xy(p)[1])
    lo.SetNet(gnd)
    hi.SetNet(v5)
    relief(hi)
    a = xy(lo)
    add_track(board, gnd, [a, (gv[0] - 0.8, a[1]), gv], B, 0.4)
    # C4 on the output, above U2
    c4 = place_back(board, "Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder",
                    "C4", "1u", C4_AT, 0)
    left, right = sorted(c4.Pads(), key=lambda p: xy(p)[0])
    left.SetNet(gnd)
    right.SetNet(v33)
    a, b = xy(left), xy(right)
    add_track(board, gnd, [a, (a[0] - 2.0, a[1])], B, 0.4)
    add_via(board, gnd, a[0] - 2.0, a[1])
    add_track(board, v33, [p2, b, (b[0] + 2.4, b[1])], B, 0.4)
    add_via(board, v33, b[0] + 2.4, b[1])
    # 3.3 V on the front, under the odd pin row, to pin 1
    yf = 73.1
    add_track(board, v33, [(b[0] + 2.4, b[1]), (b[0] + 2.4, yf),
                           (pins[1][0] - (pins[1][1] - yf), yf), pins[1]], pcbnew.F_Cu, 0.3)
    for ref, fp, dx, dy in (("U2", u2, 3.2, -1.6), ("C3", c3, -2.6, 0.0), ("C4", c4, -1.0, 1.9)):
        c = fp.GetPosition()
        fp.Reference().SetPosition(pcbnew.VECTOR2I(c.x + MM(dx), c.y - MM(dy)))
    x0 = ALA_X1 + 1.778 - ALA_SIZE[0]
    fab_box(board, x0, ALA_TOP - ALA_SIZE[1], x0 + ALA_SIZE[0], ALA_TOP)
    back_label(board, "AlaMode on Pi header", -20.0, 45.72, 1.2)
    return pins


def add_bus(board, nets, uno, ala):
    """Clock and data from the Pico pins to the AlaMode header and on to the
    UNO, as one pair on the back. The pair follows tile seams, where there
    are no tile pads and no diamond headers. The clock leaves its Pico pin
    on the front for 2.5 mm so it can start on the far side of the data
    track; after that the order never swaps, so nothing crosses."""
    B = pcbnew.B_Cu
    clk, dat = nets["CLK_IN"], nets["DAT_IN"]
    c0, d0 = pico_pin(PICO_CLK), pico_pin(PICO_DAT)
    cA, dA = ala[23], ala[19]
    yc, yd = -26.75, -27.6             # east along the T0/T5 seam: clock above data
    xc, xd = -30.9, -30.05             # north along the seam between tile columns
    yc2, yd2 = 49.45, 48.85            # east again above T7 In2
    add_track(board, clk, [c0, (c0[0], yc)], pcbnew.F_Cu, FINE_W)
    add_via(board, clk, c0[0], yc)
    add_track(board, clk, [(c0[0], yc), (xc, yc), (xc, yc2), (cA[0], yc2), cA], B, FINE_W)
    add_track(board, dat, [d0, (d0[0], yd), (xd, yd), (xd, yd2), (dA[0], yd2), dA], B, FINE_W)
    # AlaMode pins -> between the even-row pins -> east above the header -> south on x = 30.48
    # -> east above the UNO digital row -> down into D13 and D11
    for net, a, yh, xv, dst in ((clk, cA, 79.6, 30.88, uno["D13"]), (dat, dA, 79.0, 30.08, uno["D11"])):
        xt = a[0] - 1.27                               # midway between two pin columns
        add_track(board, net, [a, (xt, a[1] + 1.27), (xt, yh), (xv, yh), (xv, xv),
                               (dst[0], xv), dst], B, FINE_W)


# Tracks from each diamond signal pin to the tile's own terminal pad, in
# tile coordinates. Clock pins route on the front. Data pins route on the
# back: on the front they would wall the ground pour in between the clock
# and data traces and cut off the diamonds' ground pins.
E = 5.82                           # 7.62 - D
DIAMOND_ROUTES = {
    ("In1", "CI"):  ("F", [(-15.24 + D, 0), (-15.24 + D, D), (-P1, P1)]),
    ("In1", "DI"):  ("B", [(-15.24, -D), (-P1 - D, -P1), (-P1, -P1)]),
    ("Out2", "CO"): ("F", [(15.24 - D, 0), (15.24 - D, D), (P1, P1)]),
    ("Out2", "DO"): ("B", [(15.24, -D), (P1 + D, -P1), (P1, -P1)]),
    ("Out1", "CO"): ("F", [(0, 15.24 - D), (E, P1), (P1, P1)]),
    ("Out1", "DO"): ("B", [(D, 15.24), (8.0, 15.24), (11.88, 11.36), (11.88, -3.36), (P1, -P1)]),
    ("In2", "CI"):  ("F", [(0, -15.24 + D), (0, 0), (-P1, P1)]),
    ("In2", "DI"):  ("B", [(D, -15.24), (3.0, -14.04), (3.0, -11.9), (-3.34, -11.9), (-P1, -P1)]),
}


def turn_info():
    """At each row turn the two hops share a hole column and the longer one
    steps out by TURN_JOG. Returns {(tile, connector): (jog signal, jog x)}
    for the Out2 and In1 diamonds that face a turn."""
    info = {}
    for n in range(len(CHAIN) - 1):
        if CHAIN[n][1] == CHAIN[n + 1][1]:
            continue
        span = {sig: abs(pad_xy(n, o)[1] - pad_xy(n + 1, i)[1])
                for sig, o, i in (("C", "CO", "CI"), ("D", "DO", "DI"))}
        sig = max(span, key=span.get)
        x = pad_xy(n, "CO")[0]
        jog_x = x + (TURN_JOG if x > 0 else -TURN_JOG)
        info[(n, "Out2")] = (sig, jog_x)
        info[(n + 1, "In1")] = (sig, jog_x)
    return info


def add_diamonds(board, nets):
    """2x2 diamond header pads under every tile, with their signal pins tied
    to the tile's terminal pads. Power pins connect through the pours."""
    placed = {n: [] for n in range(len(CHAIN))}
    turns = turn_info()
    for n, (col, row) in enumerate(CHAIN):
        t = -1 if row == 0 else 1

        def at(p):
            return (col * TILE + t * p[0], row * TILE + t * p[1])
        for cname, ((ox, oy), pins) in DIAMONDS.items():
            if (n, cname) in DIAMOND_SKIP:
                continue
            placed[n].append(cname)
            fp = pcbnew.FOOTPRINT(board)
            fp.SetReference(f"T{n}{cname}")
            fp.SetValue("2x2 diamond")
            fp.Reference().SetVisible(False)
            fp.Value().SetVisible(False)
            for role, (dx, dy) in pins.items():
                pad = pcbnew.PAD(fp)
                pad.SetNumber(role)
                pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
                pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
                pad.SetSize(pcbnew.VECTOR2I(MM(1.6), MM(1.6)))
                pad.SetDrillSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
                pad.SetLayerSet(pad.PTHMask())
                pad.SetPosition(pt(*at((ox + dx, oy + dy))))
                pad.SetNet(nets[net_name(role, n)])
                if role in ("5V", "GND"):
                    relief(pad)
                fp.Add(pad)
                if (cname, role) in DIAMOND_ROUTES:
                    side, path = DIAMOND_ROUTES[(cname, role)]
                    net = nets[net_name(role, n)]
                    if (cname, role) == ("Out1", "DO") and turns.get((n, "Out2"), ("",))[0] == "D":
                        # this tile's data output is the stepped-out trace of a row
                        # turn: join it through a via instead of running down the
                        # back, where the Out2 clock track crosses
                        jog_x = turns[(n, "Out2")][1]
                        pts = [at(path[0]), at(path[1]), (jog_x, at(path[2])[1]),
                               (jog_x, at((0, 10.3))[1])]
                        add_track(board, net, pts, pcbnew.B_Cu, FINE_W)
                        add_via(board, net, *pts[-1])
                        continue
                    if (n, cname) in turns:
                        # facing a row turn: the pin on the stepped-out trace joins it
                        # directly; the other pin's track has to cross that trace, so
                        # it goes on the back
                        sig, jog_x = turns[(n, cname)]
                        if role[0] == sig:
                            a = at((ox + dx, oy + dy))
                            add_track(board, net, [a, (jog_x, a[1])], pcbnew.F_Cu, FINE_W)
                            continue
                        side = "B"
                    add_track(board, net, [at(q) for q in path],
                              pcbnew.F_Cu if side == "F" else pcbnew.B_Cu, FINE_W)
            board.Add(fp)
    for n, names in placed.items():
        if not any(c.startswith("In") for c in names) or not any(c.startswith("Out") for c in names):
            fail(f"tile T{n} has no input or no output diamond: {names}")
    print("  diamonds:", sum(len(v) for v in placed.values()), "placed,",
          ", ".join(f"T{n} {c}" for n, c in sorted(DIAMOND_SKIP)), "left out")


def add_test_points(board, nets):
    """Test pads on the back. Signal pads hang off the clock/data pair on a
    short stub; the ground one is a plated hole into the front pour."""
    for ref, net, text, at, tap, tht in TEST_POINTS:
        name = "TestPoint_THTPad_D2.0mm_Drill1.0mm" if tht else "TestPoint_Pad_D1.5mm"
        tp = place_back(board, "TestPoint", name, ref, net, at, 0)
        pad = list(tp.Pads())[0]
        pad.SetNet(nets[net])
        tp.Reference().SetVisible(False)
        tp.Value().SetVisible(False)
        if tap is not None:
            add_track(board, nets[net], [tap, at], pcbnew.B_Cu, FINE_W)
        side = -1 if at[0] < -30.48 else 1
        back_label(board, text, at[0] + side * 2.9, at[1], 0.9)


def add_notes(board):
    """Assembly notes on the silkscreen."""
    back_label(board, "FIT ONE CONTROLLER ONLY: PICO, UNO OR ALAMODE", -47.0, -93.2, 1.3)
    back_label(board, "NO U1: BRIDGE PINS 8-9 AND 11-12", -47.0, -96.2, 1.3)
    for n, (col, row) in enumerate(CHAIN):
        lines = ["OUT << IN", "TURNED 180"] if row == 0 else ["IN >> OUT"]
        for i, text in enumerate(lines):
            t = pcbnew.PCB_TEXT(board)
            t.SetText(text)
            t.SetPosition(pt(col * TILE, row * TILE + 0.3 - 2.5 * i))   # between the pad labels
            t.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
            t.SetTextThickness(MM(0.15))
            t.SetLayer(pcbnew.F_SilkS)
            board.Add(t)


def add_screws(board):
    pos = [(x * ROD_C, y * ROD_C) for x in (-1, 1) for y in (-1, 1)]
    pos += [(ROD_C, 0), (-ROD_C, 0), (0, ROD_C), (0, -ROD_C)]
    for i, (x, y) in enumerate(pos):
        fp = pcbnew.FOOTPRINT(board)
        fp.SetReference(f"H{i}")
        fp.SetValue("M3")
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        pad = pcbnew.PAD(fp)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.VECTOR2I(MM(SCREW_DRILL), MM(SCREW_DRILL)))
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(SCREW_DRILL), MM(SCREW_DRILL)))
        pad.SetLayerSet(pad.UnplatedHoleMask())
        fp.Add(pad)
        fp.SetPosition(pt(x, y))
        board.Add(fp)


def dump_pads(path, out_json):
    """Read the saved board back and list every pad, in board mm (y up)."""
    board = pcbnew.LoadBoard(path)
    rows = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            p = pad.GetPosition()
            rows.append(dict(
                ref=fp.GetReference(), value=fp.GetValue(), pad=pad.GetNumber(), net=pad.GetNetname(),
                x=round(pcbnew.ToMM(p.x) - CENTER[0], 4), y=round(CENTER[1] - pcbnew.ToMM(p.y), 4),
                drill=pcbnew.ToMM(pad.GetDrillSize().x), size=pcbnew.ToMM(pad.GetSize().x),
                plated=pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH))
    box = board.GetBoardEdgesBoundingBox()
    json.dump(dict(pads=rows, tile=TILE, outer=OUTER, chain=CHAIN,
                   edge_w=pcbnew.ToMM(box.GetWidth()), edge_h=pcbnew.ToMM(box.GetHeight())),
              open(out_json, "w"), indent=1)
    return rows


def main():
    if len(sys.argv) not in (2, 3):
        fail(__doc__)
    out = sys.argv[1]
    board = pcbnew.BOARD()
    nets = {}
    for name in ["+5V", "GND", "CLK_IN", "DAT_IN", "VSYS", "UNO_5V", "ALA_5V", "ALA_3V3", "VIN"] + [f"{s}{i}" for s in ("CLK", "DAT") for i in range(len(CHAIN) + 1)]:
        nets[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(nets[name])
    add_outline(board)
    add_screws(board)
    for n, (col, row) in enumerate(CHAIN):
        add_tile(board, nets, n, col, row)
    add_signals(board, nets)
    add_input_block(board, nets)
    uno = add_uno(board, nets)
    ala = add_alamode(board, nets)
    add_bus(board, nets, uno, ala)
    add_diamonds(board, nets)
    add_test_points(board, nets)
    add_notes(board)
    add_pour(board, nets["GND"], pcbnew.F_Cu)
    add_pour(board, nets["+5V"], pcbnew.B_Cu)
    # The pours are saved unfilled: filling from this script crashes KiCad 10's
    # Python (it needs a wxApp). Fill them with
    #   kicad-cli pcb drc --refill-zones --save-board OUT.kicad_pcb
    if not pcbnew.SaveBoard(out, board):
        fail(f"could not save {out}")
    print(f"{len(CHAIN)} tiles, {len(CHAIN) * len(TILE_PADS)} terminal holes, 8 screw holes, "
          f"{len(nets)} nets -> {out}")
    if len(sys.argv) == 3:
        rows = dump_pads(out, sys.argv[2])
        print(f"read back {len(rows)} pads -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
