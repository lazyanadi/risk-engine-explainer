"""v2 studio rig + Cycles renders (background mode only).

  set RE_MODE=preview  (small, quick)  |  final (2400 px posters)  |  turntable (hero frames -> video)
  blender -b blender/v2_models.blend --python blender/v2_render.py
Optional: RE_ONLY=hero,rings,...  to limit the assets.

Rig (also mirrored procedurally in js/studio.js for the web): grey gradient world, a large overhead
softbox, two tall strip lights, a back rim strip, two black flags for chrome contrast, and a curved
soft-grey backdrop (cyc) that is only used for the beauty renders of the props.
"""
import bpy, math, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2_lib as L

ROOT = os.path.dirname(L.HERE)
MODE = os.environ.get("RE_MODE", "preview")
ONLY = [s for s in os.environ.get("RE_ONLY", "").split(",") if s]
PREV = r"C:\Jarvis\tmp\v2-preview"
OUTDIR = os.path.join(ROOT, "blender", "renders")
os.makedirs(PREV, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)
scn = bpy.context.scene


def gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            ok = False
            for d in prefs.devices:
                d.use = d.type == kind
                ok = ok or d.use
            if ok:
                scn.cycles.device = "GPU"
                print("cycles device", kind)
                return
        except Exception as e:
            print("gpu", kind, e)
    scn.cycles.device = "CPU"


def world():
    w = bpy.data.worlds.get("RE2_World") or bpy.data.worlds.new("RE2_World")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    # Generated z: 0 = straight down, 1 = straight up
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.32, (0.05, 0.055, 0.065, 1)
    els[1].position, els[1].color = 0.75, (0.86, 0.88, 0.91, 1)
    mid = els.new(0.5)
    mid.color = (0.36, 0.39, 0.44, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.85
    nt.links.new(bg.outputs[0], out.inputs[0])
    scn.world = w


def emitter(name, size, loc, strength, color=(1, 1, 1), coll=None, black=False):
    """Emissive card: lights the scene and shows up in reflections, invisible to the camera."""
    coll = coll or L.collection("Rig")
    ob = bpy.data.objects.get(name)
    if ob is None:
        bpy.ops.mesh.primitive_plane_add(size=1)
        ob = bpy.context.active_object
        ob.name = name
        for c in ob.users_collection:
            c.objects.unlink(ob)
        coll.objects.link(ob)
    ob.scale = (size[0], size[1], 1)
    ob.location = loc
    d = (Vector((0, 0, 0.3)) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    m = bpy.data.materials.get(name + "_M") or bpy.data.materials.new(name + "_M")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    if black:
        e = nt.nodes.new("ShaderNodeBsdfDiffuse")
        e.inputs["Color"].default_value = (0.005, 0.005, 0.006, 1)
    else:
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*color, 1)
        e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    ob.visible_camera = False
    ob.visible_shadow = False
    return ob


def rig():
    world()
    emitter("RE2_SoftboxTop", (7, 4.5), (-1.2, -1.5, 6.5), 5.5)
    emitter("RE2_StripL", (0.7, 6), (-6.5, -2.5, 1.2), 9.0, (1.0, 0.98, 0.95))
    emitter("RE2_StripR", (0.6, 6), (6.5, -1.0, 1.5), 7.0, (0.9, 0.95, 1.0))
    emitter("RE2_Rim", (8, 0.8), (0.5, 6.5, 2.5), 8.0, (0.92, 0.96, 1.0))
    emitter("RE2_Front", (6, 2.2), (0.5, -8, -0.5), 1.6)
    emitter("RE2_FlagL", (3, 6), (-5, 3.5, 0.5), 0, black=True)
    emitter("RE2_FlagR", (3, 6), (5, -5.5, -1.5), 0, black=True)
    # sun for crisp contact shadows
    ld = bpy.data.lights.get("RE2_Sun") or bpy.data.lights.new("RE2_Sun", "SUN")
    ld.energy, ld.angle = 1.6, math.radians(8)
    sun = bpy.data.objects.get("RE2_Sun") or bpy.data.objects.new("RE2_Sun", ld)
    if not sun.users_collection:
        L.collection("Rig").objects.link(sun)
    sun.rotation_euler = (math.radians(38), math.radians(-18), math.radians(-30))


def backdrop():
    """Curved soft-grey cyc with a gentle gradient, for the prop beauty renders."""
    coll = L.collection("Backdrop")
    ob = bpy.data.objects.get("RE2_Cyc")
    if ob is None:
        prof = []
        for i in range(25):  # floor -> curve -> wall, in (y, z)
            a = math.radians(90 * i / 24)
            prof.append((2.0 + 2.5 * math.sin(a), 2.5 - 2.5 * math.cos(a)))
        verts, faces = [], []
        prof = [(-12.0, 0.0)] + prof + [(4.5, 12.0)]
        for x in (-14, 14):
            for y, z in prof:
                verts.append((x, y, z))
        n = len(prof)
        for k in range(n - 1):
            faces.append((k, k + 1, n + k + 1, n + k))
        ob = L.mesh_obj("RE2_Cyc", verts, faces, coll)
        mod = ob.modifiers.new("Sub", "SUBSURF")
        mod.levels = mod.render_levels = 2
        m = bpy.data.materials.new("RE2_CycM")
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Roughness"].default_value = 0.85
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = -4
        mr.inputs["From Max"].default_value = 6
        nt.links.new(sep.outputs["Y"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
        ramp.color_ramp.elements[0].color = (0.82, 0.83, 0.85, 1)
        ramp.color_ramp.elements[1].color = (0.58, 0.6, 0.64, 1)
        nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
        ob.data.materials.append(m)
    return ob


def camera(name, loc, target, lens=50):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens
    cd.dof.use_dof = False
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if not ob.users_collection:
        L.collection("Rig").objects.link(ob)
    ob.location = loc
    d = (Vector(target) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scn.camera = ob
    return ob


def settings(x, y, samples, transparent):
    r = scn.render
    r.engine = "CYCLES"
    gpu()
    r.resolution_x, r.resolution_y, r.resolution_percentage = x, y, 100
    r.film_transparent = transparent
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA" if transparent else "RGB"
    r.image_settings.color_depth = "8"
    c = scn.cycles
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.015
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.max_bounces = 12
    c.glossy_bounces = 6
    c.transmission_bounces = 10
    c.transparent_max_bounces = 8
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.sample_clamp_indirect = 8
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
    scn.view_settings.exposure = 0.25


# asset -> collection, camera location, target, lens, backdrop?, poster size (w, h)
SHOTS = {
    "hero": ("A_Hero", (0.6, -9.6, 4.6), (0.05, 0, -0.1), 46, False, (2400, 1650)),
    "herobeauty": ("A_Hero", (0.6, -10.4, 4.9), (0.05, 0, -0.25), 46, True, (2400, 1500)),
    "rings": ("A_Rings", (2.9, -4.3, 3.9), (0, 0, 0.3), 50, True, (2400, 1800)),
    "plates": ("A_Plates", (2.6, -3.4, 2.4), (0, 0, 0.42), 55, True, (2400, 1800)),
    "bars": ("A_Bars", (2.7, -5.2, 2.9), (0, 0, 0.85), 50, True, (2400, 1800)),
    "coin": ("A_Coin", (0.6, -5.4, 2.7), (0, -0.2, 0.6), 50, True, (2400, 1800)),
    "dice": ("A_Dice", (2.6, -4.4, 2.6), (0, 0, 0.25), 45, True, (2400, 1800)),
    "traffic": ("A_Traffic", (2.4, -4.6, 2.3), (0, 0, 0.95), 42, True, (2400, 1800)),
    "pillars": ("A_Pillars", (2.3, -4.6, 2.2), (0, 0, 0.45), 45, True, (2400, 1800)),
    "coindark": ("A_Coin", (0.6, -5.4, 2.7), (0, -0.2, 0.6), 50, False, (2000, 2000)),
}


def shoot(key, path, scale, samples):
    coll, cam, tgt, lens, cyc, (w, h) = SHOTS[key]
    L.only_collection(coll)
    bd = bpy.context.view_layer.layer_collection.children.get("Backdrop")
    if bd:
        bd.exclude = not cyc
    rigc = bpy.context.view_layer.layer_collection.children.get("Rig")
    if rigc:
        rigc.exclude = False
    cyc_ob = bpy.data.objects.get("RE2_Cyc")
    if cyc_ob and cyc:  # floor touches the lowest point of the asset
        zs = [(o.matrix_world @ Vector(c)).z for o in bpy.data.collections[coll].all_objects if o.type == "MESH" for c in o.bound_box]
        cyc_ob.location.z = min(zs) - 0.002
    camera("RE2_Cam", cam, tgt, lens)
    settings(int(w * scale), int(h * scale), samples, not cyc)
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


def hero_loop(frames=144, w=1600, h=1100, samples=64):
    """Calm, seamless hero loop. The loop and the camera never move. Over one cycle:
    a tall strip light circles the model once (light sweeps across the chrome), the tiles shimmer
    (tiny lifts along their normals), ~70 tiles at the tiled patch lift off and settle back
    (dissolve / assemble), the floating cubes drift on small closed paths and the green circuit
    glow breathes. Every motion uses whole periods of the cycle, so frame N == frame 0.
    Frames -> C:\\Jarvis\\tmp\\v2-loop (resumable); encoded by scripts/encode_loop.mjs."""
    import random
    from mathutils import Matrix
    coll, cam, tgt, lens, cyc, _ = SHOTS["hero"]
    L.only_collection(coll)
    lcs = bpy.context.view_layer.layer_collection.children
    if lcs.get("Backdrop"):
        lcs["Backdrop"].exclude = True   # transparent film; composited on white when encoding
    if lcs.get("Rig"):
        lcs["Rig"].exclude = False
    camera("RE2_Cam", cam, tgt, lens)
    settings(w, h, samples, True)
    scn.cycles.seed = 7
    scn.cycles.use_animated_seed = False
    rnd = random.Random(3)
    tiles = []
    for o in bpy.data.collections["Hero_Tiles"].objects:
        z, kind = o.get("zone", 0.0), o.get("kind", "tile")
        n = Vector(o.get("nrm", (0, 0, 1))).normalized()
        base = o.matrix_world.copy()
        role = "still"
        if kind == "cloud":
            role = "drift"
        elif 0.5 < z < 0.9 and rnd.random() < 0.13:
            role = "lift"
        elif z > 0.3:
            role = "shimmer"
        ax = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()
        side = n.cross(ax).normalized()
        tiles.append((o, base, n, side, ax, role, rnd.uniform(0, math.tau), rnd.choice([1, 2]), rnd.uniform(0.08, 0.22)))
    print("loop roles", {r: sum(1 for t in tiles if t[5] == r) for r in ("still", "shimmer", "lift", "drift")})
    core = bpy.data.materials.get("RE2_Core")
    core_b = next((n for n in core.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if core else None
    out = os.environ.get("RE_LOOPDIR", r"C:\Jarvis\tmp\v2-loop")
    os.makedirs(out, exist_ok=True)
    only = os.environ.get("RE_FRAMES")
    todo = [int(x) for x in only.split(",")] if only else range(frames)
    for f in todo:
        pth = os.path.join(out, f"f{f:04d}.png")
        if os.path.exists(pth):
            continue
        ph = math.tau * f / frames
        # light sweep: a tall strip light on a circle around the model (one turn per loop)
        a = ph + 0.6
        emitter("RE2_Sweep", (0.45, 7.5), (7.5 * math.sin(a), -7.5 * math.cos(a), 2.2), 16.0, (1.0, 0.99, 0.97))
        for (o, base, n, side, ax, role, phi, k, amp) in tiles:
            if role == "still":
                continue
            if role == "shimmer":
                o.matrix_world = Matrix.Translation(n * 0.006 * math.sin(k * ph + phi)) @ base
            elif role == "lift":
                s = (0.5 - 0.5 * math.cos(ph + phi)) ** 2.2        # mostly assembled, then lifts and returns
                rot = Matrix.Rotation(s * 1.4, 4, ax)
                loc = base.to_translation()
                o.matrix_world = Matrix.Translation(loc + n * amp * s + side * 0.03 * s) @ rot @ Matrix.Translation(-loc) @ base
            else:  # drift on a small closed loop
                d = n * 0.025 * math.sin(ph + phi) + side * 0.02 * math.cos(ph + phi)
                rot = Matrix.Rotation(0.15 * math.sin(ph + phi), 4, ax)
                loc = base.to_translation()
                o.matrix_world = Matrix.Translation(loc + d) @ rot @ Matrix.Translation(-loc) @ base
        if core_b:
            core_b.inputs["Emission Strength"].default_value = 3.0 * (1 + 0.3 * math.sin(2 * ph))
        scn.render.filepath = pth
        bpy.ops.render.render(write_still=True)
        print("frame", f, flush=True)
    for (o, base, *_r) in tiles:
        o.matrix_world = base


rig()
backdrop()
keys = ONLY or list(SHOTS)
if MODE == "preview":
    for k in keys:
        shoot(k, os.path.join(PREV, k + ".png"), 0.33, 48)
elif MODE == "final":
    for k in keys:
        shoot(k, os.path.join(OUTDIR, k + ".png"), 1.0, 256)
elif MODE == "loop":
    hero_loop()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.HERE, "v2_render.blend"))
