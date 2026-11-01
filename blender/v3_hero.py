"""v3 hero: a wide, thin, pale satin-silver Moebius loop whose WHOLE surface is a fine tile grid.
A scatter wave travels once round the loop per cycle: where the wave is, tiles push out of the
surface to random heights with small tilts and a few lift off; before and after it the surface is
smooth satin. Camera and loop never move. Everything is procedural (no downloads).

Background mode only:
  set RE_MODE=build    -> blender/v3_hero.blend
  set RE_MODE=preview  (RE_FRAMES=0,40  RE_SCALE=0.5)  -> C:\\Jarvis\\tmp\\v3-preview
  set RE_MODE=loop     -> C:\\Jarvis\\tmp\\v3-loop\\fNNNN.png (resumable); then `npm run loop`
  blender -b --factory-startup --python blender/v3_hero.py            (build)
  blender -b --factory-startup blender/v3_hero.blend --python blender/v3_hero.py   (preview / loop)
"""
import bpy, bmesh, math, os, random, sys
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v2_lib as L

MODE = os.environ.get("RE_MODE", "build")
TAU = math.tau
FRAMES = int(os.environ.get("RE_NFRAMES", "168"))   # 7 s at 24 fps
W, H = 1920, 1320

# ------------------------------------------------------------------ shape
HT = 0.022       # half thickness: a thin band
RB = 0.018       # rounded edge radius
SEG = 1400
NTOP = 40
NC = 5
CELL = 0.06      # tile pitch


def centre(t):
    return Vector((2.5 * math.sin(t), 0.78 * math.cos(t), 1.25 * math.sin(2 * t)))


def frame(t, eps=1e-4):
    T = (centre(t + eps) - centre(t - eps)).normalized()
    nin = T.cross(Vector((0, 1, 0))).normalized()
    B = nin.cross(T).normalized()
    phi = math.pi / 2 + t / 2 + 0.35 * math.sin(2 * t)
    Wv = (B * math.cos(phi) + nin * math.sin(phi)).normalized()
    N = T.cross(Wv).normalized()
    return T, Wv, N


def half_width(t):
    return 0.6 + 0.16 * math.sin(t) ** 2


def satin():
    m = bpy.data.materials.get("RE3_Satin") or bpy.data.materials.new("RE3_Satin")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Base Color"].default_value = (0.80, 0.84, 0.90, 1)   # pale blue-grey silver
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.23                      # satin, not mirror
    if "Anisotropic" in b.inputs:
        b.inputs["Anisotropic"].default_value = 0.35
    b.inputs["Coat Weight"].default_value = 0.15
    b.inputs["Coat Roughness"].default_value = 0.12
    return m


def build_ribbon(coll, mat):
    prof_n = 2 + NC + NTOP + NC + 2
    verts, faces = [], []
    for i in range(SEG):
        t = TAU * i / SEG
        c = centre(t)
        T, Wv, N = frame(t)
        hw = half_width(t)
        pts = []
        for j in range(2):
            pts.append((hw, (HT - RB) * j / 2))
        for j in range(NC):
            a = math.radians(90 * j / NC)
            pts.append((hw - RB + RB * math.cos(a), HT - RB + RB * math.sin(a)))
        for j in range(NTOP):
            pts.append(((hw - RB) - 2 * (hw - RB) * j / NTOP, HT))
        for j in range(NC):
            a = math.radians(90 + 90 * j / NC)
            pts.append((-hw + RB + RB * math.cos(a), HT - RB + RB * math.sin(a)))
        for j in range(2):
            pts.append((-hw, (HT - RB) * (1 - j / 2)))
        full = pts + [(-x, -y) for x, y in pts]
        for x, y in full:
            verts.append(c + Wv * x + N * y)
    K = 2 * prof_n
    for i in range(SEG):
        for k in range(K):
            k1 = (k + 1) % K
            if i < SEG - 1:
                faces.append((i * K + k, i * K + k1, (i + 1) * K + k1, (i + 1) * K + k))
            else:  # Moebius seam: k meets k + K/2
                faces.append((i * K + k, i * K + k1, (k1 + prof_n) % K, (k + prof_n) % K))
    return L.mesh_obj("RE3_Ribbon", verts, faces, coll, [mat], smooth=True)


HEIGHTS = [0.004 * 1.42 ** k for k in range(10)]   # 4 mm .. 0.094 extrusion


def tile_meshes(coll, mat):
    """Bevelled tiles with the origin at the BOTTOM centre, one mesh per extrusion height."""
    out = []
    for k, h in enumerate(HEIGHTS):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * CELL * 0.9, v.co.y * CELL * 0.9, (v.co.z + 0.5) * (h + 0.006)))
        ob = L.bm_obj(f"tmp_tile{k}", bm, coll, [mat])
        L.bevel(ob, min(0.006, (h + 0.006) * 0.3), segments=2, angle=40)
        L.apply_mods(ob)
        me = ob.data
        me.name = f"RE3_TileMesh{k}"
        me.use_fake_user = True   # keep unused heights in the saved file
        coll.objects.unlink(ob)
        bpy.data.objects.remove(ob)
        out.append(me)
    return out


def build_tiles(coll, meshes, seed=4):
    rnd = random.Random(seed)
    tc = L.collection("Hero3_Tiles", coll)
    t, n = 0.0, 0
    while t < TAU - 1e-6:
        T, Wv, N = frame(t)
        hw = half_width(t)
        cols = int(2 * (hw - RB) / CELL)
        for side in (1, -1):
            for ci in range(cols):
                u = (-cols / 2 + ci + 0.5) * CELL
                base = centre(t) + Wv * u + N * side * (HT - 0.0035)   # bottom just under the surface
                ob = bpy.data.objects.new("t", meshes[0])
                rot = Matrix((T, Wv, N * side)).transposed().to_4x4()
                ob.matrix_world = Matrix.Translation(base) @ rot
                ob["t"], ob["u"], ob["side"] = t, u / hw, side
                ob["r1"], ob["r2"], ob["r3"] = rnd.random(), rnd.random(), rnd.random()
                tc.objects.link(ob)
                n += 1
        t += CELL / (centre(t + 1e-3) - centre(t - 1e-3)).length * 2e-3
    print("tiles", n)


# ------------------------------------------------------------------ studio: bright, airy, soft
def card(name, size, loc, strength, color=(1, 1, 1), look=(0, 0, 0)):
    coll = L.collection("Rig3")
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
    d = (Vector(look) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    ob.visible_camera = False
    ob.visible_shadow = False
    return ob


def studio():
    scn = bpy.context.scene
    w = bpy.data.worlds.get("RE3_World") or bpy.data.worlds.new("RE3_World")
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
    el[0].position, el[0].color = 0.28, (0.16, 0.21, 0.31, 1)      # deep cool blue-grey below
    el[1].position, el[1].color = 0.8, (1.0, 1.0, 1.0, 1)          # white above
    mid = el.new(0.5)
    mid.color = (0.5, 0.57, 0.69, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs[0])
    scn.world = w
    card("RE3_Top", (9, 6), (0, -1, 7), 3.2)
    card("RE3_Left", (2.5, 7), (-7, -3, 1.5), 3.0)
    card("RE3_Right", (2.5, 7), (7, -2, 2), 2.2, (0.93, 0.96, 1.0))
    card("RE3_Back", (10, 2), (0, 7, 3), 3.0)
    card("RE3_Front", (10, 3), (0, -9, -1.5), 1.2)
    card("RE3_Blue", (8, 5), (3, 4, -4), 2.4, (0.36, 0.48, 0.7))   # cool bounce for the blue-grey undersides


def camera():
    scn = bpy.context.scene
    cd = bpy.data.cameras.get("RE3_Cam") or bpy.data.cameras.new("RE3_Cam")
    cd.lens = 40
    cam = bpy.data.objects.get("RE3_Cam") or bpy.data.objects.new("RE3_Cam", cd)
    if not cam.users_collection:
        L.collection("Rig3").objects.link(cam)
    cam.location = (1.3, -7.6, 5.4)
    target = Vector((0.15, 0.0, -0.15))
    cam.rotation_euler = (target - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
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
    scn.view_settings.exposure = 0.4


# ------------------------------------------------------------------ the travelling scatter wave
SIG = 0.85   # width of the wave along the loop (radians of t)


def wave_state(ph):
    """Apply the wave for loop phase ph (0..2pi). Periodic: ph and ph + 2pi give the same frame."""
    tiles = bpy.data.collections["Hero3_Tiles"].objects
    meshes = [bpy.data.meshes[f"RE3_TileMesh{k}"] for k in range(len(HEIGHTS))]
    for ob in tiles:
        t, u = ob["t"], ob["u"]
        r1, r2, r3 = ob["r1"], ob["r2"], ob["r3"]
        if "base" not in ob:
            ob["base"] = [x for row in ob.matrix_world for x in row]
        base = Matrix([ob["base"][0:4], ob["base"][4:8], ob["base"][8:12], ob["base"][12:16]])
        # wave centre travels once round the loop; the front is ragged (per-tile offset)
        d = (t - ph + 0.35 * (r1 - 0.5) + 0.15 * u + math.pi) % TAU - math.pi
        I = math.exp(-(d / SIG) ** 2)
        k = I * (0.55 + 0.9 * r2)                    # this tile's share of the wave
        if k < 0.12:
            ob.hide_render = True
            continue
        ob.hide_render = False
        lvl = min(len(HEIGHTS) - 1, int((k - 0.12) / 0.95 * len(HEIGHTS) * (0.35 + 0.65 * r3)))
        ob.data = meshes[lvl]
        n = Vector((base[0][2], base[1][2], base[2][2])).normalized()
        loc = base.to_translation()
        tilt = 0.5 * k * (r1 - 0.5)                  # each tile catches the light a little differently
        tx = Vector((base[0][0], base[1][0], base[2][0])).normalized()
        ty = Vector((base[0][1], base[1][1], base[2][1])).normalized()
        ax = (tx * (r3 - 0.5) + ty * (r2 - 0.5)).normalized()
        lift = 0.0
        if r1 > 0.975 and k > 0.75:                   # a few tiles lift off and come back
            lift = (k - 0.75) / 0.6 * (0.12 + 0.3 * r2)
            tilt *= 4
        rot = Matrix.Rotation(tilt, 4, ax)
        ob.matrix_world = Matrix.Translation(loc + n * lift) @ rot @ Matrix.Translation(-loc) @ base


def setup_view():
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = lc.name not in ("A_Hero3", "Rig3")


if MODE == "build":
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = L.collection("A_Hero3")
    mat = satin()
    build_ribbon(coll, mat)
    build_tiles(coll, tile_meshes(coll, mat))
    studio()
    camera()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "v3_hero.blend"))
    print("saved v3_hero.blend")
else:
    setup_view()
    studio()
    camera()
    scale = float(os.environ.get("RE_SCALE", "1.0" if MODE == "loop" else "0.5"))
    render_settings(scale, int(os.environ.get("RE_SAMPLES", "56")))
    out = os.environ.get("RE_OUT", r"C:\Jarvis\tmp\v3-loop" if MODE == "loop" else r"C:\Jarvis\tmp\v3-preview")
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
