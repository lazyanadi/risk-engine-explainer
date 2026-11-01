"""v4 hero: a thick SQUARE-section bar twisting along an infinity path, every face covered by a fine tile grid.
A scatter wave travels once round the loop per cycle (6 s): tiles on all four faces push out to different
depths, tilt a little, a few lift off, then settle back flush. Camera and loop never move. Procedural only.

Material detail (still pale blue-grey satin silver on white):
- body: satin metal with a fine noise grain (bump), light anisotropy, faint engraved seam grid at the tile pitch
  (UVs follow arc length and the square's perimeter), ambient-occlusion darkening in the gaps
- tiles: bevelled (3 segments), each with a slightly different tint and roughness (Object Info random), AO in
  the gaps between neighbours

Background mode only:
  blender -b --factory-startup --python blender/v4_hero.py                                   (build -> v4_hero.blend)
  set RE_MODE=preview (RE_FRAMES=0,36 RE_SCALE=0.5) & blender -b --factory-startup blender/v4_hero.blend --python blender/v4_hero.py
  set RE_MODE=loop   -> C:\\Jarvis\\tmp\\v4-loop\\fNNNN.png (resumable); then: node scripts/encode_loop.mjs C:/Jarvis/tmp/v4-loop assets/v4
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v2_lib as L

MODE = os.environ.get("RE_MODE", "build")
TAU = math.tau
FRAMES = int(os.environ.get("RE_NFRAMES", "144"))   # 6 s at 24 fps
W, H = 1920, 1320

S = float(os.environ.get("RE_SIDE", "0.56"))   # side of the square section
HS = S / 2
RB = 0.03          # rounded corner radius
SEG = 1500         # rings along the loop
NFACE = 14         # points per flat face
NC = 4             # points per rounded corner
CELL = S / 10      # tile pitch: 10 tiles across each face (minus the corners)


def centre(t):
    return Vector((2.55 * math.sin(t), 0.8 * math.cos(t), 1.3 * math.sin(2 * t)))


def frame(t, eps=1e-4):
    T = (centre(t + eps) - centre(t - eps)).normalized()
    nin = T.cross(Vector((0, 1, 0))).normalized()
    B = nin.cross(T).normalized()
    phi = math.pi / 4 + t / 2 + 0.35 * math.sin(2 * t)   # half twist overall; a square maps onto itself
    Wv = (B * math.cos(phi) + nin * math.sin(phi)).normalized()
    N = T.cross(Wv).normalized()
    return T, Wv, N


def square_profile():
    """Closed rounded-square outline (x, y) counter-clockwise with perimeter parameter; 4-fold symmetric."""
    pts = []
    h = HS - RB
    for q in range(4):  # each quarter: flat face then corner, rotated by 90 deg
        a0 = q * math.pi / 2
        ca, sa = math.cos(a0), math.sin(a0)
        quarter = []
        for j in range(NFACE):                    # face at x = +HS, y from -h to +h
            quarter.append((HS, -h + 2 * h * j / NFACE))
        for j in range(NC):                       # corner arc
            a = math.radians(90 * j / NC)
            quarter.append((h + RB * math.cos(a), h + RB * math.sin(a)))
        pts += [(x * ca - y * sa, x * sa + y * ca) for x, y in quarter]
    per = [0.0]
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        per.append(per[-1] + math.hypot(x1 - x0, y1 - y0))
    return pts, per


def arc_table(n=20000):
    ts = [TAU * i / n for i in range(n + 1)]
    s = [0.0]
    for i in range(n):
        s.append(s[-1] + (centre(ts[i + 1]) - centre(ts[i])).length)
    return ts, s


def t_at_s(ts, s, x):
    lo, hi = 0, len(s) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if s[m] < x:
            lo = m
        else:
            hi = m
    f = (x - s[lo]) / max(1e-9, s[hi] - s[lo])
    return ts[lo] + (ts[hi] - ts[lo]) * f


# ------------------------------------------------------------------ materials
def node_mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Metallic"].default_value = 1.0
    if "Anisotropic" in b.inputs:
        b.inputs["Anisotropic"].default_value = 0.3
    b.inputs["Coat Weight"].default_value = 0.12
    b.inputs["Coat Roughness"].default_value = 0.1
    return m, nt, b


BASE = (0.79, 0.835, 0.9)


def grain_bump(nt, strength):
    """Very fine satin grain from noise (object space), as a bump."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (900, 900, 900)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    return bump


def ao_tint(nt, base_socket_value, distance):
    """Base colour darkened by ambient occlusion (contact shading in the gaps)."""
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = distance
    ao.samples = 8
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.55
    if os.environ.get("RE_AO", "0") == "1":   # the AO node is costly in Cycles; real bounce light already darkens gaps
        nt.links.new(ao.outputs["AO"], mr.inputs["Value"])
    else:
        mr.inputs["Value"].default_value = 1.0
    return ao, mix, mr


def body_material():
    m, nt, b = node_mat("RE4_Body")
    b.inputs["Base Color"].default_value = (*BASE, 1)
    # engraved seam grid at the tile pitch, from UVs (u along the loop, v round the square, both in cells)
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "Cells"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    lines = []
    for ch in ("X", "Y"):
        fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
        sub = nt.nodes.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.5
        ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = 0.44; mr.inputs["From Max"].default_value = 0.5
        nt.links.new(sep.outputs[ch], fr.inputs[0]); nt.links.new(fr.outputs[0], sub.inputs[0])
        nt.links.new(sub.outputs[0], ab.inputs[0]); nt.links.new(ab.outputs[0], mr.inputs["Value"])
        lines.append(mr)
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
    nt.links.new(lines[0].outputs[0], mx.inputs[0]); nt.links.new(lines[1].outputs[0], mx.inputs[1])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(mx.outputs[0], inv.inputs[1])
    seam = nt.nodes.new("ShaderNodeBump")
    seam.inputs["Strength"].default_value = 0.22
    seam.inputs["Distance"].default_value = 0.002
    nt.links.new(inv.outputs[0], seam.inputs["Height"])
    g = grain_bump(nt, 0.08)
    nt.links.new(g.outputs["Normal"], seam.inputs["Normal"])
    nt.links.new(seam.outputs["Normal"], b.inputs["Normal"])
    # rougher, slightly darker in the seams; AO contact shading
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.22; rr.inputs["To Max"].default_value = 0.36
    nt.links.new(mx.outputs[0], rr.inputs["Value"])
    nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    ao, mix, mr = ao_tint(nt, BASE, 0.05)
    mix.inputs["A"].default_value = (*BASE, 1)
    nt.links.new(mr.outputs[0], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def tile_material():
    m, nt, b = node_mat("RE4_Tile")
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    # tint: per tile between a cool pale silver and a slightly warmer, brighter one
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.74, 0.79, 0.87, 1)
    ramp.color_ramp.elements[1].color = (0.88, 0.9, 0.93, 1)
    nt.links.new(oi.outputs["Random"], ramp.inputs["Fac"])
    ao, mix, mr = ao_tint(nt, None, 0.035)
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    nt.links.new(mr.outputs[0], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.16; rr.inputs["To Max"].default_value = 0.34
    nt.links.new(oi.outputs["Random"], rr.inputs["Value"])
    nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    g = grain_bump(nt, 0.06)
    nt.links.new(g.outputs["Normal"], b.inputs["Normal"])
    return m


# ------------------------------------------------------------------ geometry
def build_bar(coll, mat, ts, s):
    prof, per = square_profile()
    K = len(prof)
    total = s[-1]
    verts, faces, uvs = [], [], []
    ring_s = []
    for i in range(SEG):
        x = total * i / SEG               # evenly spaced by arc length
        t = t_at_s(ts, s, x)
        ring_s.append(x)
        c = centre(t)
        T, Wv, N = frame(t)
        for px, py in prof:
            verts.append(c + Wv * px + N * py)
    for i in range(SEG):
        last = i == SEG - 1
        u0, u1 = ring_s[i] / CELL, (total if last else ring_s[i + 1]) / CELL
        for k in range(K):
            k1 = (k + 1) % K
            v0, v1 = per[k] / CELL, per[k + 1] / CELL
            if not last:
                faces.append((i * K + k, i * K + k1, (i + 1) * K + k1, (i + 1) * K + k))
            else:  # half twist: profile index k meets k + K/2
                faces.append((i * K + k, i * K + k1, (k1 + K // 2) % K, (k + K // 2) % K))
            uvs.append([(u0, v0), (u0, v1), (u1, v1), (u1, v0)])
    ob = L.mesh_obj("RE4_Bar", verts, faces, coll, [mat], None, uvs, smooth=True, uv_name="Cells")
    print("bar", len(verts), "verts")
    return ob


HEIGHTS = [0.003 * 1.45 ** k for k in range(10)]   # 3 mm .. 0.084 extrusion


def tile_meshes(coll, mat):
    out = []
    for k, h in enumerate(HEIGHTS):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        hh = h + 0.006
        for v in bm.verts:
            v.co = Vector((v.co.x * CELL * 0.9, v.co.y * CELL * 0.9, (v.co.z + 0.5) * hh))
        ob = L.bm_obj(f"tmp4_tile{k}", bm, coll, [mat])
        L.bevel(ob, min(CELL * 0.09, hh * 0.3), segments=3, angle=40)
        L.apply_mods(ob)
        me = ob.data
        me.name = f"RE4_TileMesh{k}"
        me.use_fake_user = True
        coll.objects.unlink(ob)
        bpy.data.objects.remove(ob)
        out.append(me)
    return out


def build_tiles(coll, meshes, ts, s, seed=9):
    rnd = random.Random(seed)
    tc = L.collection("Hero4_Tiles", coll)
    total = s[-1]
    rows = int(total / CELL)
    cols = int((S - 2 * RB) / CELL)        # tiles per face (flat part only)
    n = 0
    for r in range(rows):
        x = (r + 0.5) * total / rows
        t = t_at_s(ts, s, x)
        T, Wv, N = frame(t)
        c = centre(t)
        for face in range(4):                # +W, +N, -W, -N faces of the square
            a = face * math.pi / 2
            fn = Wv * math.cos(a) + N * math.sin(a)          # face normal
            ft = -Wv * math.sin(a) + N * math.cos(a)         # across the face
            for ci in range(cols):
                v = (-cols / 2 + ci + 0.5) * CELL
                base = c + fn * (HS - 0.0035) + ft * v
                ob = bpy.data.objects.new("t", meshes[0])
                ob.matrix_world = Matrix.Translation(base) @ Matrix((T, ft, fn)).transposed().to_4x4()
                ob["t"], ob["face"], ob["v"] = t, face, v / HS
                ob["r1"], ob["r2"], ob["r3"] = rnd.random(), rnd.random(), rnd.random()
                tc.objects.link(ob)
                n += 1
    print("tiles", n, "rows", rows, "per face", cols)


# ------------------------------------------------------------------ studio (same airy rig as v3)
def card(name, size, loc, strength, color=(1, 1, 1), look=(0, 0, 0)):
    coll = L.collection("Rig4")
    ob = bpy.data.objects.get(name)
    if ob is None:
        me = bpy.data.meshes.new(name)
        me.from_pydata([(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        m = bpy.data.materials.new(name + "_M")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        e = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(e.outputs[0], o.inputs[0])
        me.materials.append(m)
    e = ob.data.materials[0].node_tree.nodes["Emission"]
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    ob.scale = (size[0], size[1], 1)
    ob.location = loc
    ob.rotation_euler = (Vector(look) - Vector(loc)).normalized().to_track_quat("Z", "Y").to_euler()
    ob.visible_camera = False
    ob.visible_shadow = False
    return ob


def studio():
    scn = bpy.context.scene
    w = bpy.data.worlds.get("RE4_World") or bpy.data.worlds.new("RE4_World")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.3, (0.1, 0.14, 0.23, 1)
    el[1].position, el[1].color = 0.8, (1.0, 1.0, 1.0, 1)
    mid = el.new(0.5)
    mid.color = (0.44, 0.51, 0.64, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs[0])
    scn.world = w
    card("RE4_Top", (9, 6), (0, -1, 7), 3.4)
    card("RE4_Left", (2.5, 7), (-7, -3, 1.5), 3.2)
    card("RE4_Right", (2.5, 7), (7, -2, 2), 2.4, (0.93, 0.96, 1.0))
    card("RE4_Back", (10, 2), (0, 7, 3), 3.0)
    card("RE4_Front", (10, 3), (0, -9, -1.5), 0.9)
    card("RE4_Blue", (8, 5), (3, 4, -4), 2.6, (0.3, 0.42, 0.66))


def camera():
    scn = bpy.context.scene
    cd = bpy.data.cameras.get("RE4_Cam") or bpy.data.cameras.new("RE4_Cam")
    cd.lens = float(os.environ.get("RE_LENS", "44"))
    cam = bpy.data.objects.get("RE4_Cam") or bpy.data.objects.new("RE4_Cam", cd)
    if not cam.users_collection:
        L.collection("Rig4").objects.link(cam)
    cam.location = tuple(float(x) for x in os.environ.get("RE_CAM", "1.3,-7.9,5.5").split(","))
    target = Vector((0.15, 0.0, -0.15))
    cam.rotation_euler = (target - Vector(cam.location)).normalized().to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam


def render_settings(scale=1.0, samples=56):
    scn = bpy.context.scene
    r = scn.render
    r.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        scn.cycles.device = "GPU"
    except Exception as e:
        print("gpu", e)
    r.resolution_x, r.resolution_y, r.resolution_percentage = int(W * scale), int(H * scale), 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    c = scn.cycles
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.seed = 11
    c.use_animated_seed = False
    c.max_bounces = 8
    c.glossy_bounces = 4
    c.transparent_max_bounces = 4
    c.sample_clamp_indirect = 6
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Base Contrast"
    scn.view_settings.exposure = 0.45


# ------------------------------------------------------------------ the travelling scatter wave
SIG = 0.8


def wave_state(ph):
    tiles = bpy.data.collections["Hero4_Tiles"].objects
    meshes = [bpy.data.meshes[f"RE4_TileMesh{k}"] for k in range(len(HEIGHTS))]
    for ob in tiles:
        t, v = ob["t"], ob["v"]
        r1, r2, r3 = ob["r1"], ob["r2"], ob["r3"]
        if "base" not in ob:
            ob["base"] = [x for row in ob.matrix_world for x in row]
        bb = ob["base"]
        base = Matrix([bb[0:4], bb[4:8], bb[8:12], bb[12:16]])
        d = (t - ph + 0.35 * (r1 - 0.5) + 0.12 * v + 0.05 * ob["face"] + math.pi) % TAU - math.pi
        I = math.exp(-(d / SIG) ** 2)
        k = I * (0.55 + 0.9 * r2)
        if k < 0.12:
            ob.hide_render = True
            continue
        ob.hide_render = False
        lvl = min(len(HEIGHTS) - 1, int((k - 0.12) / 0.95 * len(HEIGHTS) * (0.35 + 0.65 * r3)))
        ob.data = meshes[lvl]
        n = Vector((base[0][2], base[1][2], base[2][2])).normalized()
        tx = Vector((base[0][0], base[1][0], base[2][0])).normalized()
        ty = Vector((base[0][1], base[1][1], base[2][1])).normalized()
        ax = (tx * (r3 - 0.5) + ty * (r2 - 0.5)).normalized()
        loc = base.to_translation()
        tilt = 0.45 * k * (r1 - 0.5)
        lift = 0.0
        if r1 > 0.975 and k > 0.75:
            lift = (k - 0.75) / 0.6 * (0.1 + 0.28 * r2)
            tilt *= 4
        rot = Matrix.Rotation(tilt, 4, ax)
        ob.matrix_world = Matrix.Translation(loc + n * lift) @ rot @ Matrix.Translation(-loc) @ base


def setup_view():
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = lc.name not in ("A_Hero4", "Rig4")


if MODE == "build":
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = L.collection("A_Hero4")
    ts, s = arc_table()
    build_bar(coll, body_material(), ts, s)
    build_tiles(coll, tile_meshes(coll, tile_material()), ts, s)
    studio()
    camera()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "v4_hero.blend"))
    print("saved v4_hero.blend")
else:
    setup_view()
    studio()
    camera()
    scale = float(os.environ.get("RE_SCALE", "1.0" if MODE == "loop" else "0.5"))
    render_settings(scale, int(os.environ.get("RE_SAMPLES", "56")))
    out = os.environ.get("RE_OUT", r"C:\Jarvis\tmp\v4-loop" if MODE == "loop" else r"C:\Jarvis\tmp\v4-preview")
    os.makedirs(out, exist_ok=True)
    frames = [int(x) for x in os.environ["RE_FRAMES"].split(",")] if os.environ.get("RE_FRAMES") else range(FRAMES)
    for f in frames:
        path = os.path.join(out, f"f{f:04d}.png")
        if MODE == "loop" and os.path.exists(path):
            continue
        wave_state(TAU * f / FRAMES)
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("frame", f, flush=True)
