"""v2 detail maps, made from maths (numpy) inside Blender. No downloaded textures.

Run:  blender -b --factory-startup --python blender/v2_textures.py
Writes PNGs to blender/tex/:
  ribbon_h.png      height (debug / preview)
  ribbon_n.png      tangent-space normal map (OpenGL / glTF convention, +Y = +V)
  ribbon_orm.png    R = circuit-trace mask, G = roughness, B = metalness (glTF packs G/B)
  ribbon_e.png      emissive traces (green on black), used only by the dark core material
  plate_n.png / plate_e.png   fine engraved grid + traces for the glass plates
  brushed_n.png     generic brushed / machined micro detail for props (tileable)

Layout of the ribbon trim sheet (it tiles in U and in V):
  U (columns, 2048 px) = 2.4 units of length along the loop
  V (rows, 1024 px)    = half the cross-section, right-edge middle -> top face -> left-edge middle.
  The other half of the section uses the same rows again, so the Moebius seam (which swaps the
  two halves) lines up exactly.
  Rows 0.00-0.04 side, 0.04-0.10 rounded edge, 0.10-0.90 flat face, 0.90-0.96 edge, 0.96-1.00 side.
"""
import os
import numpy as np

try:
    import bpy
except ImportError:  # allows a quick syntax check outside Blender
    bpy = None

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tex")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20261031)


# ------------------------------------------------------------------ helpers
def save(name, rgb, alpha=None):
    """rgb: float array (H, W, 3) in 0..1, row 0 = bottom (Blender / UV convention)."""
    h, w, _ = rgb.shape
    a = np.ones((h, w, 1), np.float32) if alpha is None else alpha[..., None]
    px = np.concatenate([rgb.astype(np.float32), a.astype(np.float32)], axis=2)
    path = os.path.join(OUT, name)
    if bpy is None:
        np.save(path + ".npy", px)
        return path
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("wrote", path)
    return path


def box_blur(a, r, axis):
    if r < 1:
        return a
    n = 2 * r + 1
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="wrap"), axis=axis)
    hi = np.take(c, np.arange(n, n + a.shape[axis]), axis=axis)
    lo = np.take(c, np.arange(0, a.shape[axis]), axis=axis)
    return (hi - lo) / n


def blur(a, r, passes=2):
    for _ in range(passes):
        a = box_blur(box_blur(a, r, 0), r, 1)
    return a


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def stamp_segment(mask, x0, y0, x1, y1, rad):
    """Draw a thick line into a wrapping mask (pixel coordinates)."""
    H, W = mask.shape
    L = max(abs(x1 - x0), abs(y1 - y0), 1)
    yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    disk = (xx * xx + yy * yy) <= rad * rad
    dy_, dx_ = yy[disk], xx[disk]
    for i in range(int(L) + 1):
        t = i / L
        cx, cy = int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t))
        mask[(cy + dy_) % H, (cx + dx_) % W] = 1.0


def stamp_ring(mask, cx, cy, r_out, r_in):
    H, W = mask.shape
    R = int(r_out) + 1
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    d = np.sqrt(xx * xx + yy * yy)
    sel = (d <= r_out) & (d >= r_in)
    mask[(cy + yy[sel]) % H, (cx + xx[sel]) % W] = 1.0


def value_noise_1d(n, cells, octaves=4):
    out = np.zeros(n)
    amp, c = 1.0, cells
    for _ in range(octaves):
        pts = rng.random(c)
        x = np.arange(n) * c / n
        i = np.floor(x).astype(int)
        f = x - i
        f = f * f * (3 - 2 * f)
        out += amp * (pts[i % c] * (1 - f) + pts[(i + 1) % c] * f)
        amp *= 0.5
        c *= 2
    return out / out.max()


def circuit(mask, pads, x_range, y_lanes, rnd, count, step):
    """Random-walk traces on lanes: run along U, jog 45 degrees to a neighbour lane, end in a via pad."""
    H, W = mask.shape
    for _ in range(count):
        lane = rnd.integers(0, len(y_lanes))
        x = rnd.integers(x_range[0], x_range[1])
        y = y_lanes[lane]
        length = rnd.integers(3, 9)
        pts = [(x, y)]
        for _s in range(length):
            if rnd.random() < 0.35:
                nl = int(np.clip(lane + rnd.choice([-1, 1]), 0, len(y_lanes) - 1))
                dyl = y_lanes[nl] - y
                x += abs(dyl)
                y = y_lanes[nl]
                lane = nl
            else:
                x += step * rnd.integers(1, 4)
            pts.append((x, y))
        for (a, b), (c, d) in zip(pts, pts[1:]):
            stamp_segment(mask, a, b, c, d, 2)
        for (px, py) in (pts[0], pts[-1]):
            stamp_ring(pads, int(px), int(py), 7, 3.2)
            stamp_ring(mask, int(px), int(py), 7, 3.2)


# ------------------------------------------------------------------ ribbon trim sheet
def ribbon():
    W, H = 2048, 1024
    v = (np.arange(H) + 0.5) / H
    u = (np.arange(W) + 0.5) / W
    V, U = np.meshgrid(v, u, indexing="ij")
    face = (V > 0.10) & (V < 0.90)
    height = np.zeros((H, W))

    # 1. two machined chamfer grooves running along the loop, just inside each edge
    for vc in (0.125, 0.875):
        height -= 0.9 * np.exp(-((V - vc) / 0.0035) ** 2)
    # a raised hairline land between the grooves and the edge
    for vc in (0.112, 0.888):
        height += 0.25 * np.exp(-((V - vc) / 0.002) ** 2)

    # 2. panel lines across the face, 4 panels per repeat, with countersunk screw dimples
    panel = np.zeros((H, W))
    for k in range(4):
        x = int((k + 0.5) * W / 4)
        stamp_segment(panel, x, int(0.14 * H), x, int(0.86 * H), 2)
        for vy in (0.165, 0.835):
            for dx in (-22, 22):
                stamp_ring(panel, x + dx, int(vy * H), 7, 0)
    panel = blur(panel, 1)
    height -= 0.8 * panel

    # 3. engraved circuit traces on alternate panels (also the glow mask for the dark core)
    tr = np.zeros((H, W))
    pads = np.zeros((H, W))
    lanes = [int(H * y) for y in np.linspace(0.22, 0.78, 15)]
    rnd = np.random.default_rng(7)
    for k in (0, 2):
        x0 = int(k * W / 4) + 40
        circuit(tr, pads, (x0, x0 + W // 4 - 200), lanes, rnd, 22, 24)
    # a finer trace field on the other two panels (fainter)
    tr2 = np.zeros((H, W))
    lanes2 = [int(H * y) for y in np.linspace(0.25, 0.75, 9)]
    for k in (1, 3):
        x0 = int(k * W / 4) + 60
        circuit(tr2, pads, (x0, x0 + W // 4 - 220), lanes2, rnd, 9, 32)
    tr = np.clip(tr * face, 0, 1)
    tr2 = np.clip(tr2 * face, 0, 1)
    trs = blur(tr, 1)
    trace_h = 0.55 * trs + 0.3 * blur(tr2, 1)
    height_core = height - trace_h
    height = height - 0.12 * trace_h  # on the polished chrome the traces are only a faint engraving

    # 4. micro layer: brushed streaks along U (roughness) + very fine cross-hatch (normal)
    streak = np.stack([value_noise_1d(W, 64, 5) for _ in range(1)], 0)
    rowvar = value_noise_1d(H, 300, 3)[:, None]
    brushed = 0.6 * rowvar + 0.4 * np.roll(rowvar, 37, 0) * streak
    fine = rng.normal(0, 1, (H, W))
    fine = box_blur(fine, 24, 1)  # long along U = brushed look
    fine = box_blur(fine, 0, 0)
    height += 0.06 * fine / (np.abs(fine).max() + 1e-6)
    height_core += 0.06 * fine / (np.abs(fine).max() + 1e-6)

    n = normal_from_height(height, 6.0)
    save("ribbon_n.png", n)
    save("ribbon_core_n.png", normal_from_height(height_core, 6.0))
    save("ribbon_h.png", np.repeat(((height - height.min()) / np.ptp(height))[..., None], 3, 2))

    # roughness: polished body, satin face with brushed variation, rougher grooves and traces,
    # slight "edge wear" (brighter + rougher) on the rounded edges
    rough = 0.16 + 0.07 * brushed + 0.05 * (fine / (np.abs(fine).max() + 1e-6))
    edge = ((V > 0.04) & (V < 0.10)) | ((V > 0.90) & (V < 0.96))
    rough = np.where(edge, 0.11 + 0.05 * brushed, rough)
    rough = np.where(face, rough + 0.03, rough)
    rough += 0.22 * panel + 0.05 * trs + 0.03 * blur(tr2, 1)
    rough = np.clip(rough, 0.05, 0.6)
    trace_mask = np.clip(trs * 1.6 + blur(pads, 1) * 1.2 + 0.5 * blur(tr2, 1), 0, 1)
    orm = np.stack([trace_mask, rough, np.ones_like(rough)], 2)
    save("ribbon_orm.png", orm)
    glow = trace_mask[..., None] * np.array([0.25, 1.0, 0.55])[None, None, :]
    save("ribbon_e.png", np.clip(glow, 0, 1))


# ------------------------------------------------------------------ plates: fine engraved grid + traces
def plate():
    S = 1024
    h = np.zeros((S, S))
    g = np.zeros((S, S))
    for k in range(0, S, 64):
        stamp_segment(g, k, 0, k, S, 1)
        stamp_segment(g, 0, k, S, k, 1)
    t = np.zeros((S, S))
    pads = np.zeros((S, S))
    rnd = np.random.default_rng(3)
    circuit(t, pads, (0, S), [int(y) for y in np.linspace(80, S - 80, 12)], rnd, 26, 32)
    h -= 0.6 * blur(g, 1) + 0.8 * blur(t, 1)
    save("plate_n.png", normal_from_height(h, 5.0))
    m = np.clip(blur(t, 1) * 1.5 + blur(pads, 1), 0, 1)
    save("plate_e.png", m[..., None] * np.array([0.3, 1.0, 0.6])[None, None, :])


# ------------------------------------------------------------------ brushed / machined micro detail
def brushed():
    S = 1024
    f = rng.normal(0, 1, (S, S))
    f = box_blur(f, 40, 1)
    f = box_blur(f, 1, 0)
    f /= np.abs(f).max()
    save("brushed_n.png", normal_from_height(f * 0.4, 4.0))


if __name__ == "__main__" or bpy is not None:
    ribbon()
    plate()
    brushed()
    print("textures done")
