"""v3: three more props so every picture on the page shows a different object (background mode only).

  blender -b --factory-startup blender/v2_models.blend --python blender/v3_props.py  -> blender/v3_props.blend
  A_Dice     Monte Carlo: a cloud of tumbling bevelled dice, fanning out; the far-out ones are orange
  A_Traffic  Report card: a machined tower with three lenses (green lit, amber + red dark), Basel traffic light
  A_Pillars  Your turn: four brushed pillars (SPY, TLT, GLD, EEM) with engraved bands, one pushed down by a shock
Materials are reused from v2_build.py (same file).
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v2_lib as L

M = {n: bpy.data.materials[k] for n, k in (("brushed", "RE2_Brushed"), ("polished", "RE2_Polished"), ("dark", "RE2_DarkSatin"),
                                            ("ceramic", "RE2_Ceramic"), ("green", "RE2_GreenLacquer"), ("orange", "RE2_TailOrange"),
                                            ("emerald", "RE2_EmeraldGlass"), ("glow", "RE2_GlowGreen"))}
M["amber"] = L.principled("RE3_AmberLens", (0.55, 0.32, 0.05), 0.0, 0.12, coat=1.0)
M["redlens"] = L.principled("RE3_RedLens", (0.35, 0.05, 0.03), 0.0, 0.12, coat=1.0)
M["greenlit"] = L.principled("RE3_GreenLit", (0.2, 0.9, 0.5), 0.0, 0.1, coat=1.0, emission=(0.25, 1.0, 0.5), emission_strength=6.0)
for k in ("RE2_TailOrange",):
    b = next(n for n in bpy.data.materials[k].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Emission Strength"].default_value = 0.0      # plain lacquer, not glowing clay
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Coat Weight"].default_value = 1.0


def rounded_box(name, coll, sx, sy, sz, bev, mat, segs=4):
    ob = L.bm_obj(name, L.cube_bm(sx, sy, sz), coll, [mat])
    L.bevel(ob, bev, segments=segs, angle=40)
    L.apply_mods(ob)
    return ob


def dice(coll):
    rnd = random.Random(21)
    base = rounded_box("RE3_DieBase", coll, 0.5, 0.5, 0.5, 0.11, M["ceramic"], 5)
    tail = rounded_box("RE3_DieTail", coll, 0.5, 0.5, 0.5, 0.11, M["orange"], 5)
    # pips as small dark spheres slightly sunk into each face
    for src in (base, tail):
        pb = bmesh.new()
        lay = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
               5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}
        for d, n in (((0, 0, 1), 1), ((0, 0, -1), 6), ((1, 0, 0), 2), ((-1, 0, 0), 5), ((0, 1, 0), 3), ((0, -1, 0), 4)):
            d = Vector(d)
            a1 = Vector((d.y, d.z, d.x)) if d.z == 0 else Vector((1, 0, 0))
            a2 = d.cross(a1)
            for px, py in lay[n]:
                c = d * 0.49 + a1 * px * 0.25 + a2 * py * 0.25
                bmesh.ops.create_uvsphere(pb, u_segments=16, v_segments=10, radius=0.075, matrix=Matrix.Translation(c))
        me = bpy.data.meshes.new(src.name + "Pips")
        pb.to_mesh(me)
        pb.free()
        me.materials.append(M["dark"])
        for p in me.polygons:
            p.use_smooth = True
        # join pips into the die mesh
        bm = bmesh.new()
        bm.from_mesh(src.data)
        bm.from_mesh(me)
        bm.to_mesh(src.data)
        bm.free()
        src.data.materials.append(M["dark"])
        n0 = len(src.data.polygons) - len(me.polygons)
        for i, p in enumerate(src.data.polygons):
            if i >= n0:
                p.material_index = 1
        bpy.data.meshes.remove(me)
    for o in (base, tail):
        coll.objects.unlink(o)
    # a fan of dice: dense near the centre, sparse and orange far out (fat tails)
    for i in range(70):
        g = Vector((rnd.gauss(0, 0.55), rnd.gauss(0, 0.32), 0))
        far = g.length > 1.0
        s = rnd.uniform(0.16, 0.24) * (0.85 if far else 1.0)
        z = s * 0.5 + abs(rnd.gauss(0, 0.35)) * (0.4 if i % 3 else 1.0)
        ob = bpy.data.objects.new("d", (tail if far else base).data)
        ob.location = (g.x, g.y, z)
        ob.rotation_euler = (rnd.uniform(0, math.tau), rnd.uniform(0, math.tau), rnd.uniform(0, math.tau))
        ob.scale = (s, s, s)
        coll.objects.link(ob)
    bm = bmesh.new()
    L.extrude_bm(bm, L.rounded_rect(1.7, 1.0, 0.2, 8), -0.06, 0.0)
    p = L.bm_obj("RE3_DicePlate", bm, coll, [M["brushed"]])
    L.bevel(p, 0.02, segments=3, angle=40)
    L.apply_mods(p)
    L.box_uv(p, 0.8)


def traffic(coll):
    bm = bmesh.new()
    L.extrude_bm(bm, L.rounded_rect(0.42, 0.34, 0.16, 8), 0.0, 1.9)
    body = L.bm_obj("RE3_TrafficBody", bm, coll, [M["brushed"]])
    L.bevel(body, 0.03, segments=4, angle=40)
    L.apply_mods(body)
    L.box_uv(body, 1.0)
    v, f, uv = L.lathe_mesh([(0.001, -0.06), (0.75, -0.06), (0.78, -0.03), (0.78, 0.0), (0.001, 0.0)], 160)
    L.mesh_obj("RE3_TrafficBase", v, f, coll, [M["dark"]], None, uv)
    for i, (z, mk) in enumerate(((1.55, "redlens"), (1.0, "amber"), (0.45, "greenlit"))):
        # hood ring + lens dome on the front face
        v, f, uv = L.lathe_mesh([(0.2, 0.0), (0.27, 0.0), (0.27, 0.1), (0.25, 0.12), (0.2, 0.02)], 96)
        hood = L.mesh_obj(f"RE3_Hood{i}", v, f, coll, [M["polished"]], None, uv)
        hood.rotation_euler = (math.radians(90), 0, 0)
        hood.location = (0, -0.34, z)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=0.2, location=(0, -0.33, z))
        lens = bpy.context.active_object
        lens.name = f"RE3_Lens{i}"
        lens.scale = (1, 0.45, 1)
        for c in lens.users_collection:
            c.objects.unlink(lens)
        coll.objects.link(lens)
        lens.data.materials.append(M[mk])
        for p in lens.data.polygons:
            p.use_smooth = True
    # engraved ruler of 250 days down the side
    bm = bmesh.new()
    for k in range(26):
        zz = 0.2 + k * 0.06
        l = 0.12 if k % 5 == 0 else 0.06
        L.extrude_bm(bm, [(0.42, -0.2), (0.43, -0.2), (0.43, -0.2 + l), (0.42, -0.2 + l)], zz, zz + 0.008)
    L.bm_obj("RE3_TrafficTicks", bm, coll, [M["dark"]], smooth=False)


SHOCK = [-35, 10, 5, -40]   # the "2008-style" preset: SPY, TLT, GLD, EEM


def pillars(coll):
    bm = bmesh.new()
    L.extrude_bm(bm, L.rounded_rect(1.5, 0.55, 0.12, 8), -0.1, 0.0)
    plinth = L.bm_obj("RE3_PillarPlinth", bm, coll, [M["dark"]])
    L.bevel(plinth, 0.02, segments=3, angle=40)
    L.apply_mods(plinth)
    L.box_uv(plinth, 0.8)
    for i, s in enumerate(SHOCK):
        x = -1.05 + i * 0.7
        h = 1.0 * (1 + s / 100)
        v, f, uv = L.lathe_mesh([(0.001, 0.0), (0.2, 0.0), (0.22, 0.02), (0.22, h - 0.02), (0.2, h), (0.001, h)], 128)
        mat = M["orange"] if s < -30 else (M["green"] if s > 0 else M["brushed"])
        p = L.mesh_obj(f"RE3_Pillar{i}", v, f, coll, [M["polished"] if s >= -30 and s <= 0 else mat], None, uv)
        p.location.x = x
        # ghost ring at the pre-shock height (100%)
        v, f, uv = L.lathe_mesh([(0.23, 0.995), (0.26, 0.995), (0.26, 1.005), (0.23, 1.005)], 96)
        g = L.mesh_obj(f"RE3_PillarRef{i}", v, f, coll, [M["emerald"]], None, uv)
        g.location.x = x
        # engraved bands every 10%
        for b in range(1, int(h * 10)):
            v, f, uv = L.lathe_mesh([(0.219, b * 0.1 - 0.003), (0.224, b * 0.1 - 0.003), (0.224, b * 0.1 + 0.003), (0.219, b * 0.1 + 0.003)], 96)
            r = L.mesh_obj(f"RE3_Band{i}_{b}", v, f, coll, [M["dark"]], None, uv)
            r.location.x = x


for name, fn in (("A_Dice", dice), ("A_Traffic", traffic), ("A_Pillars", pillars)):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    fn(L.collection(name))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "v3_props.blend"))
print("saved v3_props.blend")
