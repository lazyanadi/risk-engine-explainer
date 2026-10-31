"""Shared helpers for the v2 Blender scripts (mesh building, modifiers, materials)."""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
TAU = math.tau


# ------------------------------------------------------------------ collections
def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def only_collection(name):
    """Show (view layer include) one top-level asset collection, exclude the others."""
    root = bpy.context.view_layer.layer_collection
    for lc in root.children:
        if lc.name.startswith("A_"):
            lc.exclude = lc.name != name


# ------------------------------------------------------------------ meshes
def mesh_obj(name, verts, faces, coll, mats=(), face_mat=None, uvs=None, smooth=True, uv_name="UVMap"):
    """verts (n,3), faces list of index tuples, uvs: list (per face) of per-corner (u,v) lists."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    for m in mats:
        me.materials.append(m)
    if face_mat is not None:
        me.polygons.foreach_set("material_index", np.asarray(face_mat, np.int32))
    if uvs is not None:
        lay = me.uv_layers.new(name=uv_name)
        flat = np.asarray([c for f in uvs for c in f], np.float32).ravel()
        lay.data.foreach_set("uv", flat)
    me.polygons.foreach_set("use_smooth", np.full(len(me.polygons), smooth))
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def bm_obj(name, bm, coll, mats=(), smooth=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("use_smooth", np.full(len(me.polygons), smooth))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def box_uv(ob, scale=1.0):
    """Box-project UVs (dominant normal axis), good enough for brushed micro detail."""
    me = ob.data
    lay = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    nrm = np.zeros(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("normal", nrm)
    nrm = np.abs(nrm.reshape(-1, 3))
    lv = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", lv)
    ls = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", lt)
    poly_of_loop = np.repeat(np.arange(len(me.polygons)), lt)
    ax = np.argmax(nrm, 1)[poly_of_loop]
    p = co[lv]
    u = np.where(ax == 0, p[:, 1], p[:, 0])
    v = np.where(ax == 2, p[:, 1], p[:, 2])
    lay.data.foreach_set("uv", (np.stack([u, v], 1) * scale).astype(np.float32).ravel())


def bevel(ob, width, segments=3, angle=30, harden=True, weighted=True, limit="ANGLE"):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = limit
    m.angle_limit = math.radians(angle)
    m.harden_normals = harden
    m.miter_outer = "MITER_ARC"
    if weighted:
        w = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
        w.keep_sharp = True
        w.mode = "FACE_AREA"
    return m


def subsurf(ob, levels=1):
    m = ob.modifiers.new("Sub", "SUBSURF")
    m.levels = levels
    m.render_levels = levels
    return m


def apply_mods(ob):
    """Bake the modifier stack into the mesh data (so linked duplicates share one evaluated mesh)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def cube_bm(sx, sy, sz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * 2 * sx, v.co.y * 2 * sy, v.co.z * 2 * sz))
    return bm


def lathe_mesh(profile, segs, start=0.0, sweep=TAU, wobble=None):
    """Revolve a closed (r, z) profile around Z. Returns verts, faces, uvs (u around, v along profile)."""
    n = len(profile)
    closed = abs(sweep - TAU) < 1e-6
    ring_n = segs if closed else segs + 1
    verts = []
    for i in range(ring_n):
        a = start + sweep * i / segs
        ca, sa = math.cos(a), math.sin(a)
        for k, (r, z) in enumerate(profile):
            rr = r + (wobble(a, k) if wobble else 0.0)
            verts.append((rr * ca, rr * sa, z))
    # perimeter parameter for v
    d = [0.0]
    for k in range(n):
        r0, z0 = profile[k]
        r1, z1 = profile[(k + 1) % n]
        d.append(d[-1] + math.hypot(r1 - r0, z1 - z0))
    faces, uvs = [], []
    for i in range(segs):
        i1 = (i + 1) % ring_n
        for k in range(n):
            k1 = (k + 1) % n
            faces.append((i * n + k, i * n + k1, i1 * n + k1, i1 * n + k))
            u0, u1 = i / segs * 8, (i + 1) / segs * 8
            uvs.append([(u0, d[k]), (u0, d[k + 1]), (u1, d[k + 1]), (u1, d[k])])
    return verts, faces, uvs


def rounded_rect(w, h, r, n=6):
    pts = []
    for cx, cy, a0 in ((w - r, h - r, 0), (-w + r, h - r, 90), (-w + r, -h + r, 180), (w - r, -h + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def extrude_bm(bm, pts, z0, z1, transform=Matrix(), mat_index=0):
    bot = [bm.verts.new(transform @ Vector((x, y, z0))) for x, y in pts]
    top = [bm.verts.new(transform @ Vector((x, y, z1))) for x, y in pts]
    n = len(pts)
    for i in range(n):
        f = bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
        f.material_index = mat_index
    f = bm.faces.new(list(reversed(bot)))
    f.material_index = mat_index
    f = bm.faces.new(top)
    f.material_index = mat_index


# ------------------------------------------------------------------ materials
def image(name, colorspace="Non-Color"):
    path = os.path.join(TEX, name)
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def principled(name, color=(0.8, 0.8, 0.8), metallic=0.0, rough=0.3, coat=0.0, coat_rough=0.03,
               transmission=0.0, ior=1.5, emission=None, emission_strength=0.0, specular_tint=None,
               normal=None, normal_strength=1.0, orm=None, emission_img=None, uv=None, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    b.inputs["Alpha"].default_value = alpha
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = emission_strength
    uvn = None
    if uv:
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = uv
    def tex(img_name, cs="Non-Color"):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = image(img_name, cs)
        if uvn:
            nt.links.new(uvn.outputs["UV"], t.inputs["Vector"])
        return t
    if normal:
        t = tex(normal)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal_strength
        if uv:
            nm.uv_map = uv
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if orm:
        t = tex(orm)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(t.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    if emission_img:
        t = tex(emission_img, "sRGB")
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emission_strength
    m.diffuse_color = (*color, 1)
    return m
