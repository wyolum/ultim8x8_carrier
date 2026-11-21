"""2026-11-21 Build the carrier PCB for the 3x3 ULTiM8x8 light box.

Step 1: board outline, the eight perimeter screw holes and the 72 tile
terminal holes with their nets.
Step 2: GND pour on the front (tile side), +5V pour on the back, and the
clock and data traces from tile to tile on the front.
Step 3: the input block on the back, behind the lower-left tile: J2 screw
terminal for the 5 V supply, C1 bulk capacitor, a Pico 2 W on two 1x20
sockets (A1), D1 Schottky from +5V to VSYS so USB cannot back-feed the LED
rail, and U1 74AHCT125 level shifter with C2 under the Pico.
  clock: Pico GP2 (pin 4, SPI0 SCK) -> U1 pin 5 -> pin 6 -> tile T0 CI
  data:  Pico GP3 (pin 5, SPI0 TX)  -> U1 pin 12 -> pin 11 -> tile T0 DI
Without U1, bridge its pins 5-6 and 11-12 with solder.
Step 4: two alternative controllers on the same clock and data lines (fit
one controller only):
  A2  Arduino UNO, plugged face down on male headers, USB end overhanging
      toward the +x edge. D13 = clock, D11 = data. D2 feeds its 5V pin.
  J3  2x13 male header laid out like a Raspberry Pi P1, for a WyoLum AlaMode.
      Pin 23 (SCK) = clock, pin 19 (MOSI) = data. The AlaMode's TXS0108
      translator needs 3.3 V on pin 1, made here by U2 (MCP1700-3302) with
      C3 and C4. D3 feeds 5 V to pins 2 and 4.

The tile data is the 8 holes that the tile in hand has (an outer and an inner
square). They are a subset of the 16 holes in the v2 layout, with the same
nets, so the board fits both revisions.

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
# Input block, board mm, LED-side view, all parts on the back.
# J2 and C1 sit in the pad-free square between tiles T0 and T5.
FREE_BOX = (-80.3, -49.8, -41.6, -11.1)    # x0, y0, x1, y1: no tile pad or screw head inside
J2_AT = (-52.0, -24.54)
C1_AT = (-66.0, -24.0)
# Pico 2 W: USB end toward the -x wall, top facing the rear cover. Tile holes
# lie on a 15.24 grid; a Pico centered on a grid line puts its two pin rows
# 6.35 and 8.89 from the nearest hole rows, so no pin meets a tile pad.
PICO_Y = -53.34                    # centerline, on the T0 CI/CO hole row
PICO_ROW = 17.78                   # between the pin rows
PICO_X1 = -92.0 + 1.5 + 1.37       # pin 1: board end 1.5 from the wall, pin 1.37 from the end
PICO_SIZE = (51.0, 21.0)
PICO_GND = (3, 8, 13, 18, 23, 28, 38)
U1_AT = (-79.5, PICO_Y)            # under the Pico, between its pin rows
C2_AT = (-86.2, -54.7)
D1_AT = (-86.59, -66.6)
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
    column, so the longer one steps half a tile-hole pitch outward around the
    shorter one's pads."""
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
        out = P1 if a[0] > 0 else -P1          # away from the board center
        up = 1 if b[1] > a[1] else -1
        add_track(board, net, [a, (a[0] + out, a[1] + up * P1),
                               (b[0] + out, b[1] - up * P1), b])


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
    net_of.update({4: nets["CLK_IN"], 5: nets["DAT_IN"], 39: nets["VSYS"]})
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
    x1, y0, y1 = x0 + PICO_SIZE[0], PICO_Y - PICO_SIZE[1] / 2, PICO_Y + PICO_SIZE[1] / 2
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        line = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        line.SetStart(pt(*a))
        line.SetEnd(pt(*b))
        line.SetLayer(pcbnew.B_SilkS)
        line.SetWidth(MM(0.15))
        board.Add(line)
    back_label(board, "Pico 2 W, socketed", -52.0, PICO_Y - 5.8, 1.1)
    back_label(board, "USB", x0 + 2.6, PICO_Y + 6.3, 1.0)
    back_label(board, "1", x0 + 1.4, y1 + 1.0, 1.0)
    return fp


def add_input_block(board, nets):
    B = pcbnew.B_Cu
    gnd, v5 = nets["GND"], nets["+5V"]
    add_pico(board, nets)

    # U1 under the Pico: pins 1-7 along the top with pin 1 at the left.
    u1 = place_back(board, "Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm", "U1", "74AHCT125", U1_AT, 0)
    cx, cy = U1_AT
    for rot in (0, 90, 180, 270):  # the pads are symmetric about the origin, so it turns in place
        u1.SetOrientationDegrees(rot)
        if near(xy(u1.FindPadByNumber("1")), (cx - 3.81, cy + 2.475)):
            break
    else:
        fail("no rotation puts U1 pin 1 at the upper left")
    pin = {n: xy(u1.FindPadByNumber(str(n))) for n in range(1, 15)}
    # gate 2 buffers the clock, gate 4 the data; gates 1 and 3 are parked
    u1_nets = {1: gnd, 2: gnd, 4: gnd, 5: nets["CLK_IN"], 6: nets["CLK0"], 7: gnd,
               9: gnd, 10: gnd, 11: nets["DAT0"], 12: nets["DAT_IN"], 13: gnd, 14: v5}
    for n, net in u1_nets.items():
        u1.FindPadByNumber(str(n)).SetNet(net)
    relief(u1.FindPadByNumber("14"))
    # ground: a strip under the body, a stub from each grounded pin, two vias to the front pour
    add_track(board, gnd, [(cx - 3.81, cy), (cx + 3.81, cy)], B, 0.5)
    for n in (1, 2, 4, 7, 9, 10, 13):
        add_track(board, gnd, [pin[n], (pin[n][0], cy)], B, 0.4)
    for dx in (1.27, 3.17):
        add_via(board, gnd, cx + dx, cy)

    ci, di = pad_xy(0, "CI"), pad_xy(0, "DI")
    # clock in: Pico pin 4 down the back to U1 pin 5
    a, b = pico_pin(4), pin[5]
    add_track(board, nets["CLK_IN"], [a, (a[0], -47.6), (b[0], -47.6), b], B, FINE_W)
    # clock out: U1 pin 6 over pin 7, then 45 degrees into T0 CI
    x, y = pin[6]
    yt = -49.3
    add_track(board, nets["CLK0"], [(x, y), (x, yt), (ci[0] - (yt - ci[1]), yt), ci], B, FINE_W)
    # data in: Pico pin 5 on the front, under U1, to a via below U1 pin 12
    a, b = pico_pin(5), pin[12]
    yv = -58.4
    add_track(board, nets["DAT_IN"], [a, (a[0], -46.3), (b[0], -46.3 - (a[0] - b[0])), (b[0], yv)],
              pcbnew.F_Cu, FINE_W)
    add_via(board, nets["DAT_IN"], b[0], yv)
    add_track(board, nets["DAT_IN"], [(b[0], yv), b], B, FINE_W)
    # data out: U1 pin 11 down between Pico pins 36 and 35, then into T0 DI
    x, y = pin[11]
    xg = (pico_pin(36)[0] + pico_pin(35)[0]) / 2
    yg, yr = -58.0, -64.2
    add_track(board, nets["DAT0"], [(x, y), (x, yg), (xg, yg - (xg - x)), (xg, yr),
                                    (di[0] - (yr - di[1]), yr), di], B, FINE_W)

    # C2: decoupling at U1 pin 14. The Pico pin rows and U1 wall this corner
    # off from the +5V pour, so a track feeds it between Pico pins 39 and 38.
    c2 = place_back(board, "Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder",
                    "C2", "100n", C2_AT, 90)
    c2_pads = sorted(c2.Pads(), key=lambda p: xy(p)[1])
    c2_pads[0].SetNet(v5)                                # lower pad, level with pin 14
    c2_pads[1].SetNet(gnd)
    relief(c2_pads[0])
    c2.Reference().SetPosition(pt(C2_AT[0] - 1.9, C2_AT[1] + 3.6))
    lo = xy(c2_pads[0])
    add_track(board, v5, [pin[14], lo], B, 0.4)
    xf = (pico_pin(39)[0] + pico_pin(38)[0]) / 2
    add_track(board, v5, [lo, (lo[0], -59.5), (xf, -59.5 - (xf - lo[0])), (xf, -65.6)], B, 0.3)
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

    # J2: supply in. Solid pour connections here, it carries the full current.
    j2 = place_back(board, "TerminalBlock_Phoenix",
                    "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
                    "J2", "5V in", J2_AT, 90)
    j2_pads = sorted(j2.Pads(), key=lambda p: -xy(p)[1])
    j2_pads[0].SetNet(v5)
    j2_pads[1].SetNet(gnd)
    for pad, text in zip(j2_pads, ("+5V", "GND")):
        back_label(board, text, FREE_BOX[2] - 2.4, xy(pad)[1], 1.0)

    # C1: bulk capacitor, pad 1 is the positive lead
    c1 = place_back(board, "Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm", "C1", "1000u 10V", C1_AT, 0)
    c1.FindPadByNumber("1").SetNet(v5)
    c1.FindPadByNumber("2").SetNet(gnd)
    for pad in c1.Pads():
        relief(pad)

    # the tall parts must stay inside the pad-free square
    for fp in (j2, c1):
        box = fp.GetCourtyard(pcbnew.B_CrtYd).BBox()
        x0, x1 = pcbnew.ToMM(box.GetLeft()) - CENTER[0], pcbnew.ToMM(box.GetRight()) - CENTER[0]
        y0, y1 = CENTER[1] - pcbnew.ToMM(box.GetBottom()), CENTER[1] - pcbnew.ToMM(box.GetTop())
        print(f"  {fp.GetReference()}: x {x0:.2f} to {x1:.2f}, y {y0:.2f} to {y1:.2f}")
        if x0 < FREE_BOX[0] or y0 < FREE_BOX[1] or x1 > FREE_BOX[2] or y1 > FREE_BOX[3]:
            fail(f"{fp.GetReference()} leaves the pad-free square {FREE_BOX}")
    back_label(board, "ULTiM8x8 3x3 carrier  2026-11-21  wyolum.com", 0, -30.48, 1.5)


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
    back_label(board, "UNO, face down, USB at this edge", 60.96, 45.72, 1.2)
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
    UNO, as one pair on the back. The pair runs on the lines midway between
    tile hole rows. Seen along the direction of travel the order never
    swaps, so nothing crosses."""
    B = pcbnew.B_Cu
    clk, dat = nets["CLK_IN"], nets["DAT_IN"]
    c0, d0 = pico_pin(4), pico_pin(5)
    cA, dA = ala[23], ala[19]
    # Pico -> north on the column x = -76.2 -> east on the row y = -30.48 -> north on x = 0
    add_track(board, clk, [c0, (c0[0], -43.2), (-77.0, -43.2 + (-77.0 - c0[0])), (-77.0, -30.08),
                           (cA[0], -30.08), cA], B, FINE_W)
    add_track(board, dat, [d0, (d0[0], -43.2), (-76.2, -43.2 + (-76.2 - d0[0])), (-76.2, -30.88),
                           (dA[0], -30.88), dA], B, FINE_W)
    # AlaMode pins -> between the even-row pins -> east above the header -> south on x = 30.48
    # -> east above the UNO digital row -> down into D13 and D11
    for net, a, yh, xv, dst in ((clk, cA, 79.6, 30.88, uno["D13"]), (dat, dA, 79.0, 30.08, uno["D11"])):
        xt = a[0] - 1.27                               # midway between two pin columns
        add_track(board, net, [a, (xt, a[1] + 1.27), (xt, yh), (xv, yh), (xv, xv),
                               (dst[0], xv), dst], B, FINE_W)


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
                ref=fp.GetReference(), pad=pad.GetNumber(), net=pad.GetNetname(),
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
    for name in ["+5V", "GND", "CLK_IN", "DAT_IN", "VSYS", "UNO_5V", "ALA_5V", "ALA_3V3"] + [f"{s}{i}" for s in ("CLK", "DAT") for i in range(len(CHAIN) + 1)]:
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
