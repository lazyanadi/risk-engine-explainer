"""v5 hero: ONE solid, continuous ribbon (a belt) along an infinity path. Still image only.

- Tapered: thick in the bottom-left foreground, thin as it recedes (thickness and width scale together).
- Posed on a diagonal, pitching up from left to right; the left lobe is the nearest, biggest part.
- Two-sided: outer face = polished warm-silver mirror (metallic 1, roughness 0.04);
  inner face = real geometry: a deep coffered grid of recessed grooves (panels shrink with the taper).
- The path has a clear gap at the crossing, so the smooth outer band passes cleanly over the gridded one.
- Harsh studio light (sun + big key + rim strips), dark world, heavy defined shadow on a shadow-catcher floor.
- A thin light-grey emissive rectangle frame sits on a plane behind the loop.

Background mode only:
  blender -b --factory-startup --python blender/v5_hero.py                        (build -> v5_hero.blend)
  set RE_MODE=render & blender -b --factory-startup blender/v5_hero.blend --python blender/v5_hero.py
  (RE_SCALE=0.4 RE_SAMPLES=48 for a preview; output C:\\Jarvis\\tmp\\v5\\hero.png, transparent background)
"""
import bpy, math, os, sys
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v2_lib as L

E = os.environ.get
MODE = E("RE_MODE", "build")
TAU = math.tau
W, H = int(E("RE_W", "1920")), int(E("RE_H", "1320"))

FLOOR_YMAX = float(E("RE_FLOORY", "1.0"))
NROW = 4            # grid panels across the belt (inner face)
GU, GV = 20, 14     # mesh samples per panel along / across
OUT_N = 12          # samples across the outer face
RC = 3              # samples per rounded corner
NPAN = float(E("RE_PANELS", "80"))
HW = float(E("RE_HW", "0.36"))   # half the belt width (the nearest lobe)
TH = float(E("RE_TH", "0.56"))   # belt thickness: about the same as the old square bar   # approx. panels round the whole loop
GROOVE_W = 0.70     # groove starts at this fraction of the half-panel
SIGN = float(E("RE_SIDE", "1"))       # +1: mirror on the +side normal, -1: swap sides

ROLL = float(E("RE_ROLL", "-24"))     # about Y: negative lifts the right side
PITCH = float(E("RE_PITCH", "62"))    # about X: lays the loop back so the inner face shows
YAW = float(E("RE_YAW", "-18"))       # about Z: brings the left lobe nearer the camera


def centre(t):
    # figure-8 in the XZ plane; the two crossings are 1.7 apart in Y so the bands never touch
    return Vector((2.6 * math.sin(t), 0.85 * math.cos(t), 1.25 * math.sin(2 * t)))


def taper(t):
    """1 on the near left lobe (t = 3pi/2), ~0.26 on the far right (t = pi/2); smooth and periodic."""
    w = 0.5 - 0.5 * math.sin(t)
    f = float(E("RE_TAPER", "0.7"))
    return f + (1 - f) * w ** 1.25


def frame(t, eps=1e-4):
    T = (centre(t + eps) - centre(t - eps)).normalized()
    side = T.cross(Vector((0, 1, 0))).normalized() * SIGN   # in-plane normal: outer face looks this way
    up = side.cross(T).normalized() * SIGN                  # along the belt width
    return T, side, up


def groove(x):
    """0 on a panel, 1 in the groove; grooves sit at integer x."""
    a = abs((x % 1.0) - 0.5) * 2
    k = max(0.0, min(1.0, (a - GROOVE_W) / (0.97 - GROOVE_W)))
    return k * k * (3 - 2 * k)


def arc_table(n=20000):
    ts = [TAU * i / n for i in range(n + 1)]
    s = [0.0]
    for i in range(n):
        s.append(s[-1] + (centre(ts[i + 1]) - centre(ts[i])).length)
    return np.array(ts), np.array(s)


# ------------------------------------------------------------------ materials
def principled_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Metallic"].default_value = 1.0
    return m, nt, b


def mirror_material():
    m, nt, b = principled_mat("RE5_Outer")
    b.inputs["Base Color"].default_value = (0.82, 0.78, 0.72, 1)    # warm silver/grey
    b.inputs["Roughness"].default_value = 0.035
    return m


def grid_material():
    m, nt, b = principled_mat("RE5_Inner")
    b.inputs["Roughness"].default_value = 0.30
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")      # crevices go dark
    ao.inputs["Distance"].default_value = 0.10
    ao.samples = 8
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = 0.05
    nt.links.new(ao.outputs["AO"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs["A"].default_value = (0.66, 0.64, 0.62, 1)
    nt.links.new(mr.outputs[0], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


# ------------------------------------------------------------------ the ribbon
def profile(hw, th, r):
    """Closed outline of the belt section as (lat, ht, is_inner, pv): lat = along the face normal,
    ht = along the width. Order: outer face up, top, inner face down, bottom."""
    P = []
    for j in range(OUT_N + 1):
        P.append((th / 2, -hw + r + (2 * hw - 2 * r) * j / OUT_N, False, 0))
    for j in range(1, RC + 1):      # outer-top corner
        a = j / RC * math.pi / 2
        P.append((th / 2 - r + r * math.cos(a), hw - r + r * math.sin(a), False, 0))
    for j in range(0, RC + 1):      # inner-top corner
        a = math.pi / 2 + j / RC * math.pi / 2
        P.append((-th / 2 + r + r * math.cos(a), hw - r + r * math.sin(a), j == RC, 0))
    nin = NROW * GV
    for j in range(1, nin + 1):     # inner face, top -> bottom
        P.append((-th / 2, hw - r - (2 * hw - 2 * r) * j / nin, True, j / nin))
    for j in range(1, RC + 1):      # inner-bottom corner
        a = math.pi + j / RC * math.pi / 2
        P.append((-th / 2 + r + r * math.cos(a), -hw + r + r * math.sin(a), False, 0))
    for j in range(0, RC):          # outer-bottom corner
        a = 1.5 * math.pi + j / RC * math.pi / 2
        P.append((th / 2 - r + r * math.cos(a), -hw + r + r * math.sin(a), False, 0))
    return P


ANIM = {}


def build_ribbon(coll, mats):
    ts, s = arc_table()
    total = s[-1]
    # ring positions: uniform in panel units, so panels stay square as the belt narrows
    xs = np.linspace(0, total, 6000)
    tt = np.interp(xs, s, ts)
    plen0 = np.array([2 * HW * taper(t) / NROW for t in tt])
    cum = np.concatenate([[0], np.cumsum(np.diff(xs) / ((plen0[1:] + plen0[:-1]) / 2))])
    npan = max(1, round(NPAN * cum[-1] / cum[-1]))   # keep the requested count
    cum *= npan / cum[-1]                             # integer number of panels closes the grid
    nring = npan * GU
    ring_u = np.arange(nring) / GU
    ring_x = np.interp(ring_u, cum, xs)
    ring_t = np.interp(ring_x, s, ts)
    verts, nP = [], None
    A_dir, A_wt, A_pu, A_pv, A_k = [], [], [], [], []
    for i in range(nring):
        t = float(ring_t[i])
        c = centre(t)
        T, side, up = frame(t)
        k = taper(t)
        hw, th, r = HW * k, TH * k, 0.025 * k
        P = profile(hw, th, r)
        nP = len(P)
        u = ring_u[i] + 0.5
        for lat, ht, inner, pv in P:
            wt, pu, pvi = 0.0, 0, 0
            if inner:
                v = pv * NROW + 0.5
                depth = th * 0.64 * (1 - (1 - groove(u)) * (1 - groove(v)))
                lat = lat + depth
                if 0 < pv < 1:      # the belt edges stay pinned; every panel in between can move
                    wt = (1 - groove(u)) * (1 - groove(v))
                pu, pvi = int(math.floor(u)) % npan, min(NROW, int(math.floor(v)))
            verts.append(c + side * lat + up * ht)
            A_dir.append(tuple(side)); A_wt.append(wt); A_pu.append(pu); A_pv.append(pvi); A_k.append(k)
    P = profile(0.5, 0.27, 0.014)
    inner_flags = [p[2] for p in P]
    faces, fmat, smooth = [], [], []
    for i in range(nring):
        n = (i + 1) % nring
        for j in range(nP):
            j1 = (j + 1) % nP
            faces.append((i * nP + j, i * nP + j1, n * nP + j1, n * nP + j))
            inn = inner_flags[j] and inner_flags[j1] and P[j][3] < P[j1][3]
            fmat.append(1 if inn else 0)
            smooth.append(not inn)
    V = np.array([tuple(v) for v in verts])
    rot = Euler((math.radians(PITCH), 0, 0)).to_matrix()
    rot = Euler((0, math.radians(ROLL), 0)).to_matrix() @ rot
    rot = Euler((0, 0, math.radians(YAW))).to_matrix() @ rot
    V = (np.array(rot) @ V.T).T
    ob = L.mesh_obj("RE5_Ribbon", V, faces, coll, mats, fmat, None, smooth=True)
    ob.data.polygons.foreach_set("use_smooth", np.array(smooth, bool))
    ob.data.update()
    R = np.array(rot)
    ANIM.update(ob=ob, V0=V, DIR=(R @ np.array(A_dir).T).T, WT=np.array(A_wt), PU=np.array(A_pu), PV=np.array(A_pv),
                K=np.array(A_k), tc=ring_t[::GU].copy(), npan=npan)
    print("ribbon", len(V), "verts", npan, "panels", total, "length")
    return ob, V


# ------------------------------------------------------------------ the travelling pop wave
SIG = float(E("RE_SIG", "0.9"))
POP = float(E("RE_POP", "0.26"))   # how far a panel lifts out, as a fraction of the local belt scale


def wave(ph):
    """Move every panel for loop phase ph (0..tau). Panels near the wave front pop out to different heights (a few
    sink in instead) and settle flush again behind it. The loop never moves."""
    npan = ANIM["npan"]
    rnd = np.random.default_rng(9)
    r1, r2, r3 = rnd.random((3, npan, NROW + 1))
    vn = np.arange(NROW + 1) / NROW * 2 - 1
    d = (ANIM["tc"][:, None] - ph + 0.35 * (r1 - 0.5) + 0.12 * vn[None, :] + math.pi) % TAU - math.pi
    k = np.exp(-(d / SIG) ** 2) * (0.55 + 0.9 * r2)
    k = np.where(k < 0.08, 0.0, k)
    Hh = np.where(r3 < 0.28, -0.42 * k, k) * POP          # r3 < 0.28: sinks instead of popping
    disp = Hh[ANIM["PU"], ANIM["PV"]] * ANIM["K"] * ANIM["WT"]
    V = ANIM["V0"] - ANIM["DIR"] * disp[:, None]
    me = ANIM["ob"].data
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.update()


# ------------------------------------------------------------------ studio
def emit_obj(name, verts, faces, strength, color, coll, vis_camera=True, vis_shadow=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    m = bpy.data.materials.new(name + "_M")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0])
    me.materials.append(m)
    ob.visible_camera = vis_camera
    ob.visible_shadow = vis_shadow
    return ob


def card(coll, name, size, loc, strength, look=(0, 0, 0), color=(1, 1, 1)):
    ob = emit_obj(name, [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], [(0, 1, 2, 3)], strength, color, coll,
                  vis_camera=False)
    ob.scale = (size[0], size[1], 1)
    ob.location = loc
    ob.rotation_euler = (Vector(look) - Vector(loc)).normalized().to_track_quat("Z", "Y").to_euler()
    return ob


def studio(coll, zmin, zmax):
    scn = bpy.context.scene
    w = bpy.data.worlds.new("RE5_World")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")     # dark horizon, bright overhead: mirror shows grey-to-white sweeps
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.42, (0.015, 0.016, 0.02, 1)
    el[1].position, el[1].color = 0.85, (0.34, 0.34, 0.36, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = float(E("RE_WORLD", "0.9"))
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])
    scn.world = w
    # high contrast: hard sun (defined shadow), big key, thin rim strips that streak across the mirror
    sun = bpy.data.objects.new("RE5_Sun", bpy.data.lights.new("RE5_Sun", "SUN"))
    sun.data.energy, sun.data.angle = 16.0, math.radians(2.5)
    sun.rotation_euler = (math.radians(38), math.radians(8), math.radians(-35))
    coll.objects.link(sun)
    key = bpy.data.objects.new("RE5_Key", bpy.data.lights.new("RE5_Key", "AREA"))
    key.data.shape, key.data.size, key.data.size_y, key.data.energy = "RECTANGLE", 7.0, 3.5, float(E("RE_KEY", "700"))
    key.location = (-5.5, -5.0, 6.5)
    key.rotation_euler = (Vector((0, 0, 0)) - key.location).normalized().to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(key)
    card(coll, "RE5_StripL", (0.9, 9), (-6.5, -2.0, 1.5), 90, (0, 0, 0))
    card(coll, "RE5_StripR", (0.9, 9), (6.5, -2.5, 2.5), 70, (0, 0, 0), (0.92, 0.95, 1.0))
    card(coll, "RE5_Top", (8, 2.5), (0, -1.5, 8.5), float(E("RE_TOP", "4")), (0, 0, 0))
    # shadow catcher floor
    fl = bpy.data.objects.new("RE5_Floor", bpy.data.meshes.new("RE5_Floor"))
    fl.data.from_pydata([(-12, -14, 0), (12, -14, 0), (12, FLOOR_YMAX, 0), (-12, FLOOR_YMAX, 0)], [], [(0, 1, 2, 3)])
    fl.location = (0, 0, zmin - float(E("RE_FLOORGAP", "0.35")))
    fl.is_shadow_catcher = True
    fm = bpy.data.materials.new("RE5_FloorM")   # what the mirror sees reflected below: a dark studio floor
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.022, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    fl.data.materials.append(fm)
    coll.objects.link(fl)
    return fl.location.z


def frame_rect(coll, cam, depth, margin=float(E("RE_FRAMEM", "0.8"))):
    """Thin rectangle outline on a plane facing the camera at `depth`, sized to sit just inside the picture."""
    cd = cam.data
    sc = cd.lens / (cd.sensor_width / 2)
    hw = depth / sc * margin
    hh = hw * H / W
    t = depth / sc * 0.0024
    verts, faces = [], []

    def box(ax, ay, bx, by):
        i = len(verts)
        for x in (ax, bx):
            for y in (ay, by):
                for z in (-depth, -depth - t):
                    verts.append(tuple(cam.matrix_world @ Vector((x, y, z))))
        faces.extend([(i + a, i + b, i + c, i + d) for a, b, c, d in
                      [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]])

    box(-hw, -hh, hw, -hh + t)
    box(-hw, hh - t, hw, hh)
    box(-hw, -hh, -hw + t, hh)
    box(hw - t, -hh, hw, hh)
    emit_obj("RE5_Frame", verts, faces, 1.6, (0.62, 0.63, 0.66), coll, vis_camera=True, vis_shadow=False)


def camera_fit(coll, V):
    """Aim and dolly the camera so the loop fills FILL of the picture height (and fits the width)."""
    scn = bpy.context.scene
    cd = bpy.data.cameras.new("RE5_Cam")
    cd.lens = float(E("RE_LENS", "50"))
    cam = bpy.data.objects.new("RE5_Cam", cd)
    coll.objects.link(cam)
    scn.camera = cam
    sc = cd.lens / (cd.sensor_width / 2)
    fill, fillw = float(E("RE_FILL", "0.9")), float(E("RE_FILLW", "0.9"))
    dirv = Vector(tuple(float(x) for x in E("RE_DIR", "-0.45,-0.86,0.22").split(","))).normalized()
    P = Vector(((V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2,
                (V[:, 2].min() + V[:, 2].max()) / 2))
    D = 14.0
    Vh = np.hstack([V, np.ones((len(V), 1))])
    for _ in range(12):
        cam.location = P + dirv * D
        cam.rotation_euler = (P - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        Vc = (np.array(cam.matrix_world.inverted()) @ Vh.T).T
        z = -Vc[:, 2]
        nx, ny = Vc[:, 0] / z * sc, Vc[:, 1] / z * sc * W / H
        cx, cy = (nx.max() + nx.min()) / 2, (ny.max() + ny.min()) / 2
        zm = z.mean()
        P = P + cam.matrix_world.to_quaternion() @ Vector((cx * zm / sc, cy * zm / sc * H / W, 0))
        hf, wf = (ny.max() - ny.min()) / 2, (nx.max() - nx.min()) / 2
        D *= max(hf / fill, wf / fillw)
    cam.location = P + dirv * D
    cam.rotation_euler = (P - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    Vc = (np.array(cam.matrix_world.inverted()) @ Vh.T).T
    print("fit: height", hf, "width", wf, "depth", D)
    return cam, float((-Vc[:, 2]).max())



def render_settings(scale, samples):
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
    c.max_bounces = 10
    c.glossy_bounces = 6
    c.sample_clamp_indirect = 8
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - High Contrast"
    scn.view_settings.exposure = float(E("RE_EXP", "0.0"))


def scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = L.collection("A_Hero5")
    ob, V = build_ribbon(coll, [mirror_material(), grid_material()])
    zmin, zmax = V[:, 2].min(), V[:, 2].max()
    fz = studio(coll, zmin, zmax)
    cam, zfar = camera_fit(coll, V)
    if E("RE_NOFRAME", "0") != "1":      # the loop video gets its frame from the encoder, under the render
        frame_rect(coll, cam, zfar + float(E("RE_FRAMEGAP", "1.4")))
    print("bbox z", zmin, zmax, "x", V[:, 0].min(), V[:, 0].max(), "y", V[:, 1].min(), V[:, 1].max())


if MODE == "build":
    scene()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "v5_hero.blend"))
    print("saved v5_hero.blend")
else:
    if MODE in ("both", "loop"):
        scene()
    render_settings(float(E("RE_SCALE", "1.0")), int(E("RE_SAMPLES", "128")))
    out = E("RE_OUT", "C:/Jarvis/tmp/v5-loop" if MODE == "loop" else "C:/Jarvis/tmp/v5")
    os.makedirs(out, exist_ok=True)
    if MODE == "loop":
        NF = int(E("RE_NFRAMES", "144"))
        frames = [int(x) for x in E("RE_FRAMES").split(",")] if E("RE_FRAMES") else range(NF)
        for f in frames:
            path = os.path.join(out, f"f{f:04d}.png")
            if os.path.exists(path):
                continue
            wave(TAU * f / NF)
            bpy.context.scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            print("frame", f, flush=True)
    else:
        bpy.context.scene.render.filepath = os.path.join(out, E("RE_NAME", "hero.png"))
        bpy.ops.render.render(write_still=True)
        print("rendered", bpy.context.scene.render.filepath)
