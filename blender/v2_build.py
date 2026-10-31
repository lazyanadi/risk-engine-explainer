"""RISK/ENGINE v2 models, built procedurally (no downloaded meshes or textures).

Run (background only, never in the open GUI):
  blender -b --factory-startup --python blender/v2_textures.py
  blender -b --factory-startup --python blender/v2_build.py      -> blender/v2_models.blend

Everything lives in the default scene, one top-level collection per asset:
  A_Hero    thick bevelled Moebius loop, dissolving tile field, emerald glass cube cluster
  A_Rings   machined concentric rings + green sphere on an orbit   ("Three ways")
  A_Plates  stacked glass / brushed metal plates                  ("Report card")
  A_Bars    crisis bar-chart sculpture                            ("Crises")
  A_Coin    engraved coin + dice                                  (footer / Monte Carlo)
"""
import bpy, bmesh, math, random, os, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2_lib as L
from v2_lib import TAU

HERE = L.HERE

# ------------------------------------------------------------------ clean factory scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
scene = bpy.context.scene

# ------------------------------------------------------------------ materials
M = {}
M["chrome"] = L.principled("RE2_Chrome", (0.93, 0.945, 0.965), 1.0, 0.16, coat=0.35, coat_rough=0.04,
                           normal="ribbon_n.png", normal_strength=0.8, orm="ribbon_orm.png")
M["core"] = L.principled("RE2_Core", (0.07, 0.08, 0.085), 0.9, 0.32, normal="ribbon_core_n.png",
                         emission_img="ribbon_e.png", emission_strength=3.0)
M["tileA"] = L.principled("RE2_TileBright", (0.95, 0.96, 0.975), 1.0, 0.09, coat=0.5)
M["tileB"] = L.principled("RE2_TileSatin", (0.80, 0.83, 0.87), 1.0, 0.27)
M["tileC"] = L.principled("RE2_TileGunmetal", (0.30, 0.32, 0.35), 1.0, 0.22, coat=0.3)
M["emerald"] = L.principled("RE2_EmeraldGlass", (0.16, 0.78, 0.45), 0.0, 0.025, transmission=1.0, ior=1.52)
M["clear"] = L.principled("RE2_ClearGlass", (0.93, 0.98, 0.96), 0.0, 0.02, transmission=1.0, ior=1.5)
M["dkgreen"] = L.principled("RE2_DarkGreenGloss", (0.01, 0.16, 0.08), 0.2, 0.08, coat=1.0, coat_rough=0.02)
M["glow"] = L.principled("RE2_GlowGreen", (0.2, 1.0, 0.55), 0.0, 0.3, emission=(0.25, 1.0, 0.55), emission_strength=8.0)
M["lattice"] = L.principled("RE2_Lattice", (0.18, 0.2, 0.22), 1.0, 0.25)
M["brushed"] = L.principled("RE2_Brushed", (0.86, 0.88, 0.91), 1.0, 0.24, coat=0.2,
                            normal="brushed_n.png", normal_strength=0.6)
M["polished"] = L.principled("RE2_Polished", (0.95, 0.955, 0.965), 1.0, 0.07, coat=0.4)
M["dark"] = L.principled("RE2_DarkSatin", (0.11, 0.12, 0.13), 0.8, 0.34, coat=0.25,
                         normal="brushed_n.png", normal_strength=0.4)
M["ceramic"] = L.principled("RE2_Ceramic", (0.9, 0.91, 0.92), 0.0, 0.32, coat=0.6, coat_rough=0.06)
M["green"] = L.principled("RE2_GreenLacquer", (0.02, 0.36, 0.19), 0.15, 0.12, coat=1.0, coat_rough=0.02)
M["orange"] = L.principled("RE2_TailOrange", (0.95, 0.16, 0.015), 0.0, 0.2, coat=1.0, coat_rough=0.03,
                           emission=(1.0, 0.2, 0.02), emission_strength=0.15)
M["plate_glass"] = L.principled("RE2_PlateGlass", (0.16, 0.78, 0.45), 0.0, 0.03, transmission=1.0, ior=1.5,
                                normal="plate_n.png", normal_strength=0.45, emission_img="plate_e.png",
                                emission_strength=0.9)

# ------------------------------------------------------------------ hero: Moebius loop
HT = 0.075     # half thickness of the band
RB = 0.038     # bevel (corner) radius of the cross-section
SEG = 1100     # rings along the loop
NTOP = 22      # points across each flat face
NC = 6         # points per rounded corner
U_REPEAT = 2.4  # units of length per texture repeat (adjusted to an integer count below)


def centre(t):
    return Vector((2.5 * math.sin(t), 0.72 * math.cos(t), 1.24 * math.sin(2 * t)))


def frame(t, eps=1e-4):
    T = (centre(t + eps) - centre(t - eps)).normalized()
    nin = T.cross(Vector((0, 1, 0))).normalized()
    B = nin.cross(T).normalized()
    phi = math.pi / 2 + t / 2 + 0.35 * math.sin(2 * t)  # half twist overall = Moebius
    W = (B * math.cos(phi) + nin * math.sin(phi)).normalized()
    N = T.cross(W).normalized()
    return T, W, N


def half_width(t):
    return 0.47 + 0.21 * math.sin(t) ** 2


# --- the dissolve zone: an organic mask over (t, across) on the left loop
ZC, ZS = 5.02, 0.98


def _h(ix, iy):
    n = (ix * 374761393 + iy * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n & 0xFFFF) / 65535.0


def vnoise(x, y):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _h(ix, iy), _h(ix + 1, iy)
    c, d = _h(ix, iy + 1), _h(ix + 1, iy + 1)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(x, y):
    return 0.55 * vnoise(x, y) + 0.3 * vnoise(2.1 * x + 7, 2.1 * y + 3) + 0.15 * vnoise(4.3 * x + 1, 4.3 * y + 9)


def zone(t, a, side=1):
    """0 = solid metal, 1 = fully dissolved. a = across the band, -1..1."""
    d = (t - ZC) / ZS
    core = 1 - d * d
    # spreads further along one edge than the other, plus noise for an organic front
    core += 0.28 * a * side - 0.12 * abs(a) ** 3
    core += 0.55 * (fbm(t * 3.1, a * 1.7 + (0 if side > 0 else 5)) - 0.5)
    return max(0.0, min(1.0, core))


def profile_half(hw):
    """Right-edge middle -> top face -> left-edge middle, with fixed V fractions for the trim sheet."""
    pts, vs = [], []
    # right side, upper half
    for j in range(2):
        pts.append((hw, (HT - RB) * j / 2)); vs.append(0.04 * j / 2)
    for j in range(NC):  # right rounded edge
        a = math.radians(90 * j / NC)
        pts.append((hw - RB + RB * math.cos(a), HT - RB + RB * math.sin(a))); vs.append(0.04 + 0.06 * j / NC)
    for j in range(NTOP):  # flat face
        pts.append(((hw - RB) - 2 * (hw - RB) * j / NTOP, HT)); vs.append(0.10 + 0.80 * j / NTOP)
    for j in range(NC):  # left rounded edge
        a = math.radians(90 + 90 * j / NC)
        pts.append((-hw + RB + RB * math.cos(a), HT - RB + RB * math.sin(a))); vs.append(0.90 + 0.06 * j / NC)
    for j in range(2):
        pts.append((-hw, (HT - RB) * (1 - j / 2))); vs.append(0.96 + 0.04 * j / 2)
    return pts, vs


def build_ribbon(coll):
    _, vhalf = profile_half(0.5)
    H = len(vhalf)
    K = 2 * H
    vfull = vhalf + [1.0 + v for v in vhalf] + [2.0]
    # arc length for U
    ts = [TAU * i / SEG for i in range(SEG)]
    cs = [centre(t) for t in ts]
    s = [0.0]
    for i in range(SEG):
        s.append(s[-1] + (cs[(i + 1) % SEG] - cs[i]).length)
    total = s[-1]
    reps = max(1, round(total / U_REPEAT))
    verts, zones = [], []
    for i, t in enumerate(ts):
        T, W, N = frame(t)
        hw = half_width(t)
        pts, _ = profile_half(hw)
        full = pts + [(-x, -y) for x, y in pts]
        for k, (x, y) in enumerate(full):
            a = x / hw
            side = 1 if (k < H) else -1
            z = zone(t, a * side, side)
            # sink the faces where tiles sit, so the tile tops land near the original surface
            sink = 0.62 * min(1.0, z / 0.35) if z > 0.12 else 0.0
            yy = y * (1 - sink)
            verts.append(cs[i] + W * x + N * yy)
            zones.append(z)
    faces, uvs, fmat = [], [], []
    for i in range(SEG):
        last = i == SEG - 1
        u0 = s[i] / total * reps
        u1 = s[i + 1] / total * reps
        for k in range(K):
            k1 = (k + 1) % K
            a0, a1 = i * K + k, i * K + k1
            if not last:
                b0, b1 = (i + 1) * K + k, (i + 1) * K + k1
                vb0, vb1 = vfull[k], vfull[k + 1]
            else:  # Moebius seam: profile index k meets k + K/2 (the other half of the section)
                b0, b1 = (k + H) % K, (k1 + H) % K
                vb0, vb1 = vfull[k] , vfull[k + 1]
            faces.append((a0, a1, b1, b0))
            uvs.append([(u0, vfull[k]), (u0, vfull[k + 1]), (u1, vb1), (u1, vb0)])
            zf = (zones[a0] + zones[a1] + zones[b0] + zones[b1]) / 4
            on_face = (k % H) >= 2 + NC - 1 and (k % H) < 2 + NC + NTOP
            fmat.append(1 if (zf > 0.2 and on_face) else 0)
    ob = L.mesh_obj("RE2_Ribbon", verts, faces, coll, [M["chrome"], M["core"]], fmat, uvs, smooth=True)
    # second UV: (t, zone) for the web shader (glow pulse along the loop)
    lay = ob.data.uv_layers.new(name="Zone")
    zarr = []
    for f in faces:
        for vi in f:
            zarr.append(((vi // K) / SEG, zones[vi]))
    lay.data.foreach_set("uv", np.asarray(zarr, np.float32).ravel())
    ob.data.uv_layers.active_index = 0
    print("ribbon", len(verts), "verts", len(faces), "faces, repeats", reps, "length", round(total, 2))
    return ob


# ------------------------------------------------------------------ hero: tiles
TILE_CELL = 0.052


def tile_variants(coll):
    """Bevelled box meshes (one per height ratio and material), shared by linked duplicates."""
    out = {}
    for hk, hr in (("flat", 0.35), ("mid", 0.7), ("cube", 1.0), ("tall", 1.6)):
        for mk in ("tileA", "tileB", "tileC", "emerald"):
            if mk == "emerald" and hk != "cube":
                continue
            bm = L.cube_bm(0.5, 0.5, 0.5 * hr)
            ob = L.bm_obj(f"RE2_Tile_{hk}_{mk}", bm, coll, [M[mk]], smooth=True)
            L.bevel(ob, 0.09 if hk != "flat" else 0.07, segments=2 if mk != "emerald" else 3, angle=40)
            L.apply_mods(ob)
            ob.data.name = f"RE2_TileMesh_{hk}_{mk}"
            out[(hk, mk)] = ob.data
            ob.hide_render = True
            ob.hide_viewport = True
            coll.objects.unlink(ob)
    return out


def build_tiles(coll, variants, seed=11):
    rnd = random.Random(seed)
    tiles = L.collection("Hero_Tiles", coll)
    placed = []

    def add(mesh_key, loc, rot3, scale, z=0.0, nrm=(0, 0, 1), kind="tile"):
        me = variants[mesh_key]
        ob = bpy.data.objects.new("t", me)
        ob["zone"], ob["nrm"], ob["kind"] = float(z), tuple(nrm), kind  # used by the loop animation
        ob.matrix_world = Matrix.LocRotScale(loc, rot3.to_quaternion(), scale)
        tiles.objects.link(ob)
        placed.append(ob)

    t = ZC - ZS * 1.25
    t_end = ZC + ZS * 1.25
    rows = 0
    while t < t_end:
        T, W, N = frame(t)
        hw = half_width(t)
        cols = int(2 * (hw - RB * 0.6) / TILE_CELL)
        for side in (1, -1):
            for ci in range(cols):
                u = (-cols / 2 + ci + 0.5) * TILE_CELL
                a = u / hw
                z = zone(t, a * side, side)
                if z < 0.12:
                    continue
                sink = 0.62 * min(1.0, z / 0.35)
                core_top = HT * (1 - sink)
                Nn = N * side
                axes = Matrix((T, W, Nn)).transposed()  # columns = local x, y, z
                w = TILE_CELL * rnd.uniform(0.84, 0.9)
                if z < 0.45:
                    # flush tiles: the solid surface turns into a tight grid
                    if rnd.random() < 0.04 + 0.2 * (z - 0.12):
                        continue
                    top = HT + rnd.uniform(-0.008, 0.006)
                elif z < 0.78:
                    k = (z - 0.45) / 0.33
                    if rnd.random() < 0.08 + 0.32 * k:
                        continue  # gaps reveal the glowing core
                    top = HT + rnd.choice([-1, 1, 1]) * rnd.uniform(0.0, 0.07) * (0.3 + k)
                else:
                    if rnd.random() < 0.55:
                        continue
                    top = HT + rnd.uniform(0.0, 0.02)
                h = max(0.008, top - core_top + 0.004)
                hr = h / w
                hk = "flat" if hr < 0.5 else "mid" if hr < 0.85 else "cube" if hr < 1.25 else "tall"
                base_hr = {"flat": 0.35, "mid": 0.7, "cube": 1.0, "tall": 1.6}[hk]
                mk = rnd.choices(["tileA", "tileB", "tileC"], [0.5, 0.4, 0.08 + 0.22 * z])[0]
                lift, spin = 0.0, Matrix.Identity(3)
                if z >= 0.78:
                    k = (z - 0.78) / 0.22
                    lift = rnd.uniform(0.02, 0.35) * (0.4 + k)
                    ax = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()
                    spin = Matrix.Rotation(rnd.uniform(0.1, 0.9) * k, 3, ax)
                    w *= rnd.uniform(0.7, 1.0)
                    hk, base_hr, h = "cube", 1.0, w
                    if rnd.random() < 0.12:
                        mk = "emerald"
                centre_pt = centre(t) + W * u + Nn * (core_top + h / 2 + lift)
                rot = axes @ spin
                add((hk, mk), centre_pt, rot, Vector((w, w, h / base_hr)), z, Nn, "float" if z >= 0.78 else "tile")
        rows += 1
        t += TILE_CELL / (centre(t + 1e-3) - centre(t - 1e-3)).length * 2e-3

    # floating cubes drifting away from the dissolved part (the "breaking apart" cloud)
    for i in range(520):
        tt = rnd.gauss(ZC + 0.1, ZS * 0.45)
        a = rnd.uniform(-1, 1)
        side = rnd.choice([1, -1])
        z = zone(tt, a * side, side)
        if z < 0.55:
            continue
        T, W, N = frame(tt)
        hw = half_width(tt)
        k = rnd.random() ** 1.6
        dist = 0.12 + 0.75 * k
        drift = (N * side * dist + W * (a * 0.35 * dist) + T * rnd.uniform(-0.12, 0.12)
                 + Vector((0, 0, rnd.uniform(-0.15, 0.15))))
        loc = centre(tt) + W * (a * hw) + drift
        s = TILE_CELL * rnd.uniform(0.35, 0.95) * (1.0 - 0.45 * k)
        ax = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()
        rot = Matrix((T, W, N)).transposed() @ Matrix.Rotation(rnd.uniform(0, 1.2), 3, ax)
        mk = rnd.choices(["tileA", "tileB", "tileC", "emerald"], [0.38, 0.3, 0.14, 0.18])[0]
        add(("cube", mk), loc, rot, Vector((s, s, s)), z, N * side, "cloud")
    print("tiles placed", len(placed))
    return tiles


# ------------------------------------------------------------------ hero: emerald glass cube cluster
def build_cluster(coll, seed=5):
    rnd = random.Random(seed)
    cl = L.collection("Hero_Cluster", coll)
    n, pitch, hs = 5, 0.122, 0.05
    root = bpy.data.objects.new("RE2_ClusterRoot", None)
    cl.objects.link(root)
    meshes = {}
    for mk, segs in (("emerald", 3), ("clear", 3), ("dkgreen", 3), ("glow", 2), ("lattice", 1)):
        if mk == "glow":
            bm = L.cube_bm(0.4, 0.4, 0.4)
        elif mk == "lattice":
            bm = L.cube_bm(0.5, 0.5, 0.5)
        else:
            bm = L.cube_bm(0.5, 0.5, 0.5)
        ob = L.bm_obj("tmp_" + mk, bm, cl, [M[mk]])
        if mk != "lattice":
            L.bevel(ob, 0.08, segments=segs, angle=40)
            L.apply_mods(ob)
        meshes[mk] = ob.data
        cl.objects.unlink(ob)
    off = (n - 1) / 2
    count = 0
    for x in range(n):
        for y in range(n):
            for z in range(n):
                outer = min(x, y, z) == 0 or max(x, y, z) == n - 1
                p = Vector(((x - off) * pitch, (y - off) * pitch, (z - off) * pitch))
                r = rnd.random()
                if outer and r < 0.22:
                    continue
                mk = "emerald" if r < 0.72 else "clear" if r < 0.87 else "dkgreen"
                s = hs * 2 * rnd.uniform(0.92, 1.0)
                ob = bpy.data.objects.new("c", meshes[mk])
                ob.matrix_world = Matrix.LocRotScale(p, Quaternion(), Vector((s, s, s)))
                ob.parent = root
                cl.objects.link(ob)
                count += 1
                if mk != "dkgreen" and rnd.random() < 0.3:  # emissive inner crystal
                    g = bpy.data.objects.new("g", meshes["glow"])
                    q = Quaternion(Vector((1, 1, 0)).normalized(), math.radians(45))
                    gs = s * 0.42
                    g.matrix_world = Matrix.LocRotScale(p, q, Vector((gs, gs, gs)))
                    g.parent = root
                    cl.objects.link(g)
    # internal lattice: thin rods along the gaps between cubes
    for axis in range(3):
        for i in range(n - 1):
            for j in range(n - 1):
                c = [0, 0, 0]
                o = [a for a in range(3) if a != axis]
                c[o[0]] = (i - off + 0.5) * pitch
                c[o[1]] = (j - off + 0.5) * pitch
                sc = [0.007, 0.007, 0.007]
                sc[axis] = pitch * (n - 0.6)
                rod = bpy.data.objects.new("r", meshes["lattice"])
                rod.matrix_world = Matrix.LocRotScale(Vector(c), Quaternion(), Vector(sc))
                rod.parent = root
                cl.objects.link(rod)
    root.location = (1.62, -0.5, -0.05)
    root.rotation_euler = (math.radians(28), math.radians(16), math.radians(38))
    print("cluster cubes", count)
    return root


# ------------------------------------------------------------------ props
def prop_rings(coll):
    """Machined concentric rings, each a lathe with chamfers and grooves, slightly tilted (gimbal feel)."""
    objs = []
    base_prof = [(0.001, -0.16), (1.52, -0.16), (1.56, -0.12), (1.56, -0.07), (1.5, -0.04),
                 (1.32, -0.04), (1.3, -0.03), (1.0, -0.03), (0.98, -0.02), (0.001, -0.02)]
    v, f, uv = L.lathe_mesh(base_prof, 256)
    objs.append(L.mesh_obj("RE2_RingsBase", v, f, coll, [M["brushed"]], None, uv))
    tilts = [(0, 0), (9, 20), (-13, 75), (17, 140), (-7, 210)]
    for i, R in enumerate((0.36, 0.6, 0.86, 1.1, 1.34)):
        w = 0.055 + 0.01 * (i % 2)
        h = 0.07 + 0.03 * i
        c = 0.012
        g = 0.006
        prof = [(R - w, 0), (R + w, 0), (R + w, h - c), (R + w - c, h), (R + 0.012, h), (R + 0.006, h - g),
                (R - 0.006, h - g), (R - 0.012, h), (R - w + c, h), (R - w, h - c)]
        v, f, uv = L.lathe_mesh(prof, 320)
        ob = L.mesh_obj(f"RE2_Ring{i}", v, f, coll, [[M["polished"], M["dark"], M["brushed"], M["polished"], M["dark"]][i]], None, uv)
        L.bevel(ob, 0.004, segments=2, angle=30, weighted=False)
        L.apply_mods(ob)
        ob.location.z = 0.08 + 0.14 * i
        ob.rotation_euler = (math.radians(tilts[i][0]), 0, math.radians(tilts[i][1]))
        objs.append(ob)
        if i in (1, 3):  # glowing green inlay sitting in the machined groove
            v2, f2, uv2 = L.lathe_mesh([(R - 0.005, h - g - 0.001), (R + 0.005, h - g - 0.001), (R + 0.005, h - 0.002), (R - 0.005, h - 0.002)], 320)
            inl = L.mesh_obj(f"RE2_RingInlay{i}", v2, f2, coll, [M["glow"]], None, uv2)
            inl.parent = ob
    # tick marks on the outer base rim, every 3 degrees (longer every 30)
    bm = bmesh.new()
    for k in range(120):
        a = TAU * k / 120
        long = k % 10 == 0
        l = 0.07 if long else 0.035
        r0 = 1.42
        rot = Matrix.Rotation(a, 4, "Z")
        L.extrude_bm(bm, [(r0, -0.005), (r0 + l, -0.005), (r0 + l, 0.005), (r0, 0.005)], -0.045, -0.028, rot)
    objs.append(L.bm_obj("RE2_RingsTicks", bm, coll, [M["dark"]], smooth=False))
    # green core sphere + orbiter
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=0.2, location=(0, 0, 0.32))
    core = bpy.context.active_object
    core.name = "RE2_RingsCore"
    for c in core.users_collection:
        c.objects.unlink(core)
    coll.objects.link(core)
    core.data.materials.append(M["green"])
    for p in core.data.polygons:
        p.use_smooth = True
    pivot = bpy.data.objects.new("RE2_OrbitPivot", None)
    coll.objects.link(pivot)
    pivot.location = (0, 0, 0.62)
    pivot.rotation_euler = (math.radians(12), math.radians(-6), 0)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.085, location=(0, 0, 0))
    orb = bpy.context.active_object
    orb.name = "RE2_Orbiter"
    for c in orb.users_collection:
        c.objects.unlink(orb)
    coll.objects.link(orb)
    orb.data.materials.append(M["green"])
    for p in orb.data.polygons:
        p.use_smooth = True
    orb.parent = pivot
    orb.location = (1.22, 0, 0)
    return objs


def prop_plates(coll):
    rnd = random.Random(4)
    z = 0.0
    bm_m, bm_g, bm_s, bm_e = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    layers = ["m", "g", "m", "g", "m", "e", "g", "m", "G"]
    for i, kind in enumerate(layers):
        h = {"m": 0.06, "g": 0.045, "e": 0.012, "G": 0.07}[kind]
        rot = Matrix.Rotation(math.radians(rnd.uniform(-4, 4) + i * 3.2), 4, "Z")
        tr = Matrix.Translation((rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), 0)) @ rot
        w, d = (0.9, 0.62) if kind != "e" else (0.86, 0.58)
        bm = {"m": bm_m, "g": bm_g, "e": bm_e, "G": bm_g}[kind]
        L.extrude_bm(bm, L.rounded_rect(w, d, 0.1, 8), z, z + h, tr)
        z += h
        if i < len(layers) - 1:  # corner standoffs
            gap = 0.05
            for sx in (-1, 1):
                for sy in (-1, 1):
                    p = tr @ Vector((sx * (w - 0.12), sy * (d - 0.12), 0))
                    circ = [(0.032 * math.cos(a), 0.032 * math.sin(a)) for a in np.linspace(0, TAU, 25)[:-1]]
                    L.extrude_bm(bm_s, circ, z, z + gap, Matrix.Translation((p.x, p.y, 0)))
            z += gap
    out = []
    for name, bm, mk in (("RE2_PlatesMetal", bm_m, "brushed"), ("RE2_PlatesGlass", bm_g, "plate_glass"),
                         ("RE2_PlatesPosts", bm_s, "polished"), ("RE2_PlatesGlow", bm_e, "glow")):
        ob = L.bm_obj(name, bm, coll, [M[mk]])
        L.bevel(ob, 0.012 if mk != "glow" else 0.003, segments=3, angle=40)
        L.apply_mods(ob)
        L.box_uv(ob, 0.9)
        out.append(ob)
    return out


CRISES = [12.1, 4.6, 14.2, 22.9]


def prop_bars(coll):
    out = []
    bm = bmesh.new()
    L.extrude_bm(bm, L.rounded_rect(1.25, 0.5, 0.14, 8), -0.14, 0.0)
    plinth = L.bm_obj("RE2_BarsPlinth", bm, coll, [M["dark"]])
    L.bevel(plinth, 0.025, segments=4, angle=40)
    L.apply_mods(plinth)
    L.box_uv(plinth, 0.8)
    out.append(plinth)
    # raised tick ruler along the front edge
    bm = bmesh.new()
    for k in range(41):
        x = -1.1 + 2.2 * k / 40
        l = 0.06 if k % 5 == 0 else 0.03
        L.extrude_bm(bm, [(x - 0.004, -0.46), (x + 0.004, -0.46), (x + 0.004, -0.46 + l), (x - 0.004, -0.46 + l)], 0.0, 0.006)
    out.append(L.bm_obj("RE2_BarsTicks", bm, coll, [M["polished"]], smooth=False))
    # segmented bars: stacked bevelled blocks, height proportional to the real crisis losses
    seg_h, gap = 0.075, 0.014
    bm_s, bm_o = bmesh.new(), bmesh.new()
    rnd = random.Random(9)
    for i, v in enumerate(CRISES):
        x = -0.78 + i * 0.52
        H = v / 22.9 * 1.75
        nseg = max(1, int(H / (seg_h + gap)))
        worst = v == max(CRISES)
        for s in range(nseg):
            z0 = 0.01 + s * (seg_h + gap)
            bmx = bm_o if worst else bm_s
            L.extrude_bm(bmx, L.rounded_rect(0.17, 0.17, 0.03, 4), z0, z0 + seg_h, Matrix.Translation((x, 0, 0)))
        if worst:  # the top breaks into floating cubes
            top = 0.01 + nseg * (seg_h + gap)
            for c in range(10):
                s = rnd.uniform(0.04, 0.075)
                p = Vector((x + rnd.uniform(-0.2, 0.2), rnd.uniform(-0.15, 0.15), top + 0.05 + c * 0.05 + rnd.uniform(0, 0.08)))
                rot = Matrix.Rotation(rnd.uniform(0, 1), 4, Vector((rnd.random(), rnd.random(), rnd.random())).normalized())
                L.extrude_bm(bm_o, L.rounded_rect(s, s, s * 0.2, 2), -s, s, Matrix.Translation(p) @ rot)
    for name, bmx, mk in (("RE2_BarsBlocks", bm_s, "brushed"), ("RE2_BarsWorst", bm_o, "orange")):
        ob = L.bm_obj(name, bmx, coll, [M[mk]])
        L.bevel(ob, 0.008, segments=2, angle=40)
        L.apply_mods(ob)
        L.box_uv(ob, 1.2)
        out.append(ob)
    # green glass blade at the size of a normal bad day (99% VaR 2.12%) on the same scale
    bm = bmesh.new()
    zv = 2.12 / 22.9 * 1.75
    L.extrude_bm(bm, L.rounded_rect(1.12, 0.36, 0.06, 6), zv - 0.006, zv + 0.006)
    blade = L.bm_obj("RE2_BarsVaR", bm, coll, [M["emerald"]])
    L.bevel(blade, 0.004, segments=2, angle=40)
    L.apply_mods(blade)
    out.append(blade)
    return out


def prop_coin(coll):
    out = []
    R, Hc = 0.9, 0.085
    # reeded edge: radius dips in 150 grooves around the rim
    prof = [(0.001, -Hc), (R - 0.02, -Hc), (R, -Hc + 0.02), (R, Hc - 0.02), (R - 0.02, Hc),
            (R - 0.06, Hc), (R - 0.075, Hc - 0.02), (R - 0.14, Hc - 0.025), (0.001, Hc - 0.025)]

    def reed(a, k):
        return -0.008 * (0.5 + 0.5 * math.cos(150 * a)) if k in (2, 3) else 0.0
    v, f, uv = L.lathe_mesh(prof, 900, wobble=reed)
    coin = L.mesh_obj("RE2_Coin", v, f, coll, [M["brushed"], M["polished"]], [1 if (k % len(prof)) < 6 else 0 for k in range(len(f))], uv)
    # mirrored back face (same profile flipped) is implied by the closed lathe: front only has relief
    # embossed relief on the face: a fat-tailed histogram, tail bars in orange, plus two engraved rings
    bm, bmo = bmesh.new(), bmesh.new()
    zf = Hc - 0.025
    for i in range(23):
        x = -0.55 + i * 0.05
        hgt = 0.55 * math.exp(-0.5 * ((x + 0.02) / 0.17) ** 2) + 0.03 + (0.04 if i < 3 else 0)
        tgt = bmo if i < 4 else bm
        L.extrude_bm(tgt, [(x - 0.018, -0.3), (x + 0.018, -0.3), (x + 0.018, -0.3 + hgt), (x - 0.018, -0.3 + hgt)], zf, zf + 0.022)
    rings = []
    for rr, w in ((0.66, 0.008), (0.7, 0.004)):
        circ_o = [((rr + w) * math.cos(a), (rr + w) * math.sin(a)) for a in np.linspace(0, TAU, 257)[:-1]]
        rings.append(circ_o)
    relief = L.bm_obj("RE2_CoinRelief", bm, coll, [M["brushed"]])
    tail = L.bm_obj("RE2_CoinTail", bmo, coll, [M["orange"]])
    for ob in (relief, tail):
        L.bevel(ob, 0.004, segments=2, angle=40, weighted=False)
        L.apply_mods(ob)
        ob.parent = coin
    # a thin raised ring on the face
    v, f, uv = L.lathe_mesh([(0.68, zf), (0.7, zf), (0.7, zf + 0.012), (0.68, zf + 0.012)], 256)
    ring = L.mesh_obj("RE2_CoinRing", v, f, coll, [M["polished"]], None, uv)
    ring.parent = coin
    # engraved text: RISK/ENGINE below the histogram
    cu = bpy.data.curves.new("RE2_CoinText", "FONT")
    cu.body = "RISK/ENGINE"
    cu.size = 0.085
    cu.align_x = "CENTER"
    cu.extrude = 0.008
    cu.bevel_depth = 0.002
    cu.space_character = 1.25
    txt = bpy.data.objects.new("RE2_CoinTextObj", cu)
    coll.objects.link(txt)
    txt.location = (0, -0.42, zf + 0.004)
    dg = bpy.context.evaluated_depsgraph_get()
    tm = bpy.data.meshes.new_from_object(txt.evaluated_get(dg), depsgraph=dg)
    coll.objects.unlink(txt)
    tob = bpy.data.objects.new("RE2_CoinText", tm)
    tm.materials.append(M["dark"])
    coll.objects.link(tob)
    tob.location = (0, -0.42, zf + 0.004)
    tob.parent = coin
    coin.rotation_euler = (math.radians(62), 0, math.radians(-18))
    coin.location = (0, 0, 0.95)
    out.append(coin)
    # dice with real sunken pips (boolean)
    rnd = random.Random(2)
    pip_layout = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
                  4: [(-1, -1), (1, -1), (-1, 1), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
                  6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}
    faces_dir = [((0, 0, 1), 1), ((0, 0, -1), 6), ((1, 0, 0), 2), ((-1, 0, 0), 5), ((0, 1, 0), 3), ((0, -1, 0), 4)]
    for di, (pos, mk) in enumerate((((-1.0, -0.35, 0.16), "ceramic"), ((0.98, -0.2, 0.16), "ceramic"),
                                     ((0.55, -0.85, 0.13), "orange"))):
        s = 0.16 if mk != "orange" else 0.13
        bm = L.cube_bm(s, s, s)
        die = L.bm_obj(f"RE2_Die{di}", bm, coll, [M[mk], M["dark"]])
        L.bevel(die, s * 0.28, segments=5, angle=40, weighted=False)
        L.apply_mods(die)
        pb = bmesh.new()
        for d, nP in faces_dir:
            d = Vector(d)
            a1 = Vector((d.y, d.z, d.x)) if d.z == 0 else Vector((1, 0, 0))
            a2 = d.cross(a1)
            for px, py in pip_layout[nP]:
                c = d * s * 1.02 + a1 * px * s * 0.5 + a2 * py * s * 0.5
                bmesh.ops.create_uvsphere(pb, u_segments=20, v_segments=12, radius=s * 0.17,
                                          matrix=Matrix.Translation(c))
        pob = L.bm_obj("tmp_pips", pb, coll, [M["dark"]])
        mod = die.modifiers.new("Pips", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = pob
        mod.material_mode = "TRANSFER"
        L.apply_mods(die)
        bpy.data.objects.remove(pob, do_unlink=True)
        die.location = pos
        die.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, TAU))
        out.append(die)
    return out


# ------------------------------------------------------------------ build all
def build():
    hero = L.collection("A_Hero")
    rib = build_ribbon(hero)
    variants = tile_variants(hero)
    build_tiles(hero, variants)
    build_cluster(hero)
    for name, fn in (("A_Rings", prop_rings), ("A_Plates", prop_plates), ("A_Bars", prop_bars), ("A_Coin", prop_coin)):
        fn(L.collection(name))
    for c in bpy.data.collections:
        if c.name.startswith("A_"):
            tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in c.all_objects if o.type == "MESH")
            print("collection", c.name, len(c.all_objects), "objects", tris, "tris (instances counted)")


build()
out = os.path.join(HERE, "v2_models.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved", out)
