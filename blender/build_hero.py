"""Build the RISK/ENGINE hero model and card props procedurally.

Run inside Blender (Text Editor > Run Script, or through the MCP add-on socket, or
`blender -b --python build_hero.py`). It creates two scenes, "Hero" and "Props",
and never deletes anything in other scenes.

Hero: a thick silver Moebius "infinity" ribbon. The cross-section is a thin lens that is
point-symmetric, so after a half twist the tube closes onto itself (index k -> k+K/2) and
the solid stays watertight and orientable. Part of the surface breaks into a grid of
extruded metal tiles, and a small cluster of green glass cubes sits beside it.
Props: rings + green sphere, stacked slabs, Monte Carlo dice cloud, stress bar chart.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

TAU = math.tau


# ------------------------------------------------------------------ helpers
def get_scene(name):
    scn = bpy.data.scenes.get(name) or bpy.data.scenes.new(name)
    for o in list(scn.collection.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return scn


def link(scn, name, bm, mat_list, smooth=False):
    me = bpy.data.meshes.get(name)
    if me:
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for m in mat_list:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = smooth
    if smooth:
        me.set_sharp_from_angle(angle=math.radians(32))
    ob = bpy.data.objects.new(name, me)
    scn.collection.objects.link(ob)
    return ob


def mat(name, color, metallic=1.0, rough=0.25, transmission=0.0, ior=1.45, emission=None, coat=0.0, aniso=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    b.inputs["Coat Weight"].default_value = coat
    if "Anisotropic" in b.inputs:
        b.inputs["Anisotropic"].default_value = aniso
    if emission:
        b.inputs["Emission Color"].default_value = (*emission[0], 1)
        b.inputs["Emission Strength"].default_value = emission[1]
    m.diffuse_color = (*color, 1)
    if transmission > 0 and hasattr(m, "use_raytrace_refraction"):
        m.use_raytrace_refraction = True
    return m


def add_box(bm, center, axes, size, mat_index=0):
    """Box at center with orthonormal axes (ax, ay, az) and half sizes (sx, sy, sz)."""
    ax, ay, az = axes
    sx, sy, sz = size
    vs = []
    for dz in (-1, 1):
        for dy in (-1, 1):
            for dx in (-1, 1):
                vs.append(bm.verts.new(center + ax * (dx * sx) + ay * (dy * sy) + az * (dz * sz)))
    idx = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    for f in idx:
        face = bm.faces.new([vs[i] for i in f])
        face.material_index = mat_index


def lathe(bm, profile, segs, mat_index=0, z0=0.0):
    """Revolve a closed (r, z) profile around Z."""
    rings = []
    for i in range(segs):
        a = TAU * i / segs
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * ca, r * sa, z + z0)) for r, z in profile])
    n = len(profile)
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % segs]
        for k in range(n):
            f = bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
            f.material_index = mat_index


def add_sphere(bm, center, radius, mat_index=0, u=32, v=16):
    prof = []
    for j in range(v + 1):
        a = math.pi * j / v - math.pi / 2
        prof.append((radius * math.cos(a), radius * math.sin(a)))
    rings = []
    for i in range(u):
        t = TAU * i / u
        rings.append([bm.verts.new(Vector((r * math.cos(t), r * math.sin(t), z)) + center) for r, z in prof])
    for i in range(u):
        a, b = rings[i], rings[(i + 1) % u]
        for j in range(v):
            f = bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
            f.material_index = mat_index
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)


def rounded_rect(w, h, r, n=4):
    """Closed (x, y) outline of a rounded rectangle, counter-clockwise."""
    pts = []
    for cx, cy, a0 in ((w - r, h - r, 0), (-w + r, h - r, 90), (-w + r, -h + r, 180), (w - r, -h + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def extrude_outline(bm, pts, z0, z1, mat_index=0, transform=Matrix()):
    bot = [bm.verts.new(transform @ Vector((x, y, z0))) for x, y in pts]
    top = [bm.verts.new(transform @ Vector((x, y, z1))) for x, y in pts]
    n = len(pts)
    for i in range(n):
        f = bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
        f.material_index = mat_index
    f = bm.faces.new(list(reversed(bot))); f.material_index = mat_index
    f = bm.faces.new(top); f.material_index = mat_index


# ------------------------------------------------------------------ materials
M_SILVER = mat("RE_Silver", (0.86, 0.89, 0.93), 1.0, 0.2, aniso=0.5)
M_TILE = mat("RE_TileMetal", (0.72, 0.76, 0.82), 1.0, 0.3)
M_EMERALD = mat("RE_Emerald", (0.02, 0.36, 0.17), 0.0, 0.06, transmission=0.85, ior=1.55, coat=1.0)
M_GREEN = mat("RE_GreenGloss", (0.02, 0.32, 0.17), 0.3, 0.12, coat=1.0)
M_ORANGE = mat("RE_TailOrange", (1.0, 0.32, 0.08), 0.0, 0.3, emission=((1.0, 0.3, 0.04), 0.35))
M_MATTE = mat("RE_SatinWhite", (0.86, 0.88, 0.91), 0.0, 0.45)
M_SATIN = mat("RE_SatinMetal", (0.8, 0.83, 0.88), 1.0, 0.34)


# ------------------------------------------------------------------ hero ribbon
def centre(t):
    return Vector((2.4 * math.sin(t), 0.55 * math.cos(t), 1.22 * math.sin(2 * t)))


def frame(t, eps=1e-4):
    T = (centre(t + eps) - centre(t - eps)).normalized()
    nin = T.cross(Vector((0, 1, 0))).normalized()
    B = nin.cross(T).normalized()
    phi = math.pi / 2 + t / 2 + 0.35 * math.sin(2 * t)  # half twist overall = Moebius
    W = (B * math.cos(phi) + nin * math.sin(phi)).normalized()
    N = T.cross(W).normalized()
    return T, W, N


def half_width(t):
    return 0.46 + 0.16 * math.cos(2 * t) ** 2


HALF_T = 0.045  # half thickness
TILE_T0, TILE_T1 = 3.55, 5.05  # part of the loop that breaks into tiles


def build_ribbon(scn, seg=420, M=14):
    bm = bmesh.new()
    # lens profile; P[k + M] == -P[k] so the twisted ends meet
    prof = []
    for k in range(M):
        u = 1 - 2 * k / (M - 1)
        prof.append((u, HALF_T * (1 - 0.35 * u * u)))
    for k in range(M):
        u = -1 + 2 * k / (M - 1)
        prof.append((u, -HALF_T * (1 - 0.35 * u * u)))
    K = len(prof)
    rings = []
    for i in range(seg):
        t = TAU * i / seg
        c = centre(t)
        T, W, N = frame(t)
        hw = half_width(t)
        # sink the surface a little where the tiles sit, so they read as inlaid
        sink = 0.0
        if TILE_T0 < t < TILE_T1:
            s = math.sin(math.pi * (t - TILE_T0) / (TILE_T1 - TILE_T0))
            sink = 0.018 * s
        rings.append([bm.verts.new(c + W * (u * hw) + N * (v - math.copysign(sink, v))) for u, v in prof])
    for i in range(seg):
        a = rings[i]
        if i + 1 < seg:
            b = rings[i + 1]
            for k in range(K):
                bm.faces.new((a[k], a[(k + 1) % K], b[(k + 1) % K], b[k]))
        else:  # seam: frame has flipped, k joins k + K/2
            b = rings[0]
            for k in range(K):
                bm.faces.new((a[k], a[(k + 1) % K], b[((k + 1) + K // 2) % K], b[(k + K // 2) % K]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return link(scn, "RE_Ribbon", bm, [M_SILVER], smooth=True)


def build_tiles(scn, cell=0.062, seed=7):
    rnd = random.Random(seed)
    bm = bmesh.new()
    # arc length of the tile region, to space the rows evenly
    steps, length = 400, 0.0
    for i in range(steps):
        t0 = TILE_T0 + (TILE_T1 - TILE_T0) * i / steps
        t1 = TILE_T0 + (TILE_T1 - TILE_T0) * (i + 1) / steps
        length += (centre(t1) - centre(t0)).length
    rows = int(length / cell)
    count = 0
    for r in range(rows):
        f = (r + 0.5) / rows
        t = TILE_T0 + (TILE_T1 - TILE_T0) * f
        edge = min(f, 1 - f) / 0.22  # density fades in at both ends of the region
        T, W, N = frame(t)
        hw = half_width(t)
        cols = int(2 * hw * 0.92 / cell)
        for side in (1, -1):  # tiles on both faces (it is one face on a Moebius band)
            for cidx in range(cols):
                u = (-cols / 2 + cidx + 0.5) * cell
                if rnd.random() > min(1.0, edge) * (0.92 - 0.35 * abs(u / hw) ** 3):
                    continue
                lift = rnd.uniform(0.008, 0.06) * (1.6 if rnd.random() < 0.15 else 1.0)
                float_off = rnd.uniform(0.05, 0.22) if (edge < 0.6 and rnd.random() < 0.18) else 0.0
                base = centre(t) + W * u + N * side * (HALF_T * (1 - 0.35 * (u / hw) ** 2) - 0.012)
                ctr = base + N * side * (lift / 2 + float_off)
                add_box(bm, ctr, (T, W, N * side), (cell * 0.42, cell * 0.42, lift / 2 + 0.006), 0)
                count += 1
    ob = link(scn, "RE_Tiles", bm, [M_TILE])
    print("tiles", count)
    return ob


def build_emerald(scn, seed=3):
    rnd = random.Random(seed)
    bm = bmesh.new()
    n, s, gap = 4, 0.058, 0.128
    I = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    for x in range(n):
        for y in range(n):
            for z in range(n):
                outer = min(x, y, z) == 0 or max(x, y, z) == n - 1
                if outer and rnd.random() < 0.28:
                    continue
                c = Vector(((x - 1.5) * gap, (y - 1.5) * gap, (z - 1.5) * gap))
                add_box(bm, c, I, (s, s, s), 0)
    ob = link(scn, "RE_EmeraldCluster", bm, [M_EMERALD])
    ob.location = (1.72, -0.55, -0.08)
    ob.rotation_euler = (math.radians(28), math.radians(18), math.radians(36))
    return ob


# ------------------------------------------------------------------ props
def prop_rings(scn):
    bm = bmesh.new()
    for i, R in enumerate((0.42, 0.68, 0.94, 1.2)):
        w, h = 0.07, 0.05 + 0.025 * i
        prof = [(R - w, 0), (R + w, 0), (R + w, h), (R - w, h)]
        lathe(bm, prof, 128, 0)
        rnd = random.Random(i)
        for k in range(1 + i % 3):
            a = rnd.uniform(0, TAU)
            add_sphere(bm, Vector((R * math.cos(a), R * math.sin(a), h + 0.06)), 0.06 + 0.02 * k, 0, 24, 12)
    add_sphere(bm, Vector((0, 0, 0.16)), 0.16, 1, 48, 24)
    lathe(bm, [(0.001, -0.06), (1.36, -0.06), (1.36, 0.0), (0.001, 0.0)], 128, 2)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    return link(scn, "RE_Prop_Rings", bm, [M_SILVER, M_GREEN, M_MATTE], smooth=True)


def prop_stack(scn):
    bm = bmesh.new()
    rnd = random.Random(11)
    z = 0.0
    for i in range(11):
        h = 0.055
        rot = Matrix.Rotation(math.radians(rnd.uniform(-9, 9) + i * 2.5), 4, "Z")
        tr = Matrix.Translation((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), 0)) @ rot
        extrude_outline(bm, rounded_rect(0.72, 0.5, 0.08), z, z + h, 1 if i == 10 else 0, tr)
        z += h + 0.018
    return link(scn, "RE_Prop_Stack", bm, [M_SATIN, M_EMERALD], smooth=True)


def prop_dice(scn):
    bm = bmesh.new()
    rnd = random.Random(5)
    for i in range(46):
        g = Vector((rnd.gauss(0, 0.42), rnd.gauss(0, 0.42), abs(rnd.gauss(0, 0.32)) + 0.09))
        tail = g.length > 1.12
        R = (Matrix.Rotation(rnd.uniform(0, TAU), 3, "X") @ Matrix.Rotation(rnd.uniform(0, TAU), 3, "Z"))
        axes = tuple(R.col[i_] for i_ in range(3))
        s = rnd.uniform(0.05, 0.085)
        add_box(bm, g, axes, (s, s, s), 2 if tail else (1 if i % 9 == 0 else 0))
    return link(scn, "RE_Prop_Dice", bm, [M_SATIN, M_GREEN, M_ORANGE])


def prop_bars(scn):
    bm = bmesh.new()
    extrude_outline(bm, rounded_rect(1.25, 0.42, 0.12), -0.08, 0.0, 3)
    heights = [0.55, 0.42, 0.62, 0.3, 0.75, 1.05]
    for i, h in enumerate(heights):
        x = -0.95 + i * 0.38
        idx = 2 if i == len(heights) - 1 else 0
        extrude_outline(bm, rounded_rect(0.13, 0.13, 0.03), 0.0, h, idx, Matrix.Translation((x, 0, 0)))
    # a green "safe" marker: the calm-day level as a thin rail across the bars
    extrude_outline(bm, rounded_rect(1.2, 0.012, 0.006), 0.27, 0.29, 1, Matrix.Translation((0, 0.16, 0)))
    return link(scn, "RE_Prop_Bars", bm, [M_SATIN, M_GREEN, M_ORANGE, M_MATTE], smooth=True)


def build():
    hero = get_scene("Hero")
    ribbon = build_ribbon(hero)
    tiles = build_tiles(hero)
    em = build_emerald(hero)
    root = bpy.data.objects.new("RE_Hero", None)
    hero.collection.objects.link(root)
    for o in (ribbon, tiles, em):
        o.parent = root

    props = get_scene("Props")
    made = [prop_rings(props), prop_stack(props), prop_dice(props), prop_bars(props)]
    for i, o in enumerate(made):
        o.location.x = i * 4.0
    for o in list(hero.collection.all_objects) + made:
        if o.type == "MESH":
            print(o.name, len(o.data.vertices), "verts", len(o.data.polygons), "faces")


build()
if bpy.app.background:  # stage save so later steps (render/export) start from a file
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hero.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("saved", out)
