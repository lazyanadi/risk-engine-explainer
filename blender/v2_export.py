"""Bake ambient occlusion into vertex colours and export one GLB per asset (background mode only).

  blender -b --factory-startup blender/v2_models.blend --python blender/v2_export.py
Writes blender/out/*.glb (raw); `npm run optimize` then compresses them into assets/v2/.
All objects live in the active scene, so no scene override is used (that crashed Blender 5.2 in v1).
"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2_lib as L

OUT = os.path.join(L.HERE, "out")
os.makedirs(OUT, exist_ok=True)
scn = bpy.context.scene

ASSETS = {"hero": "A_Hero", "rings": "A_Rings", "plates": "A_Plates", "bars": "A_Bars", "coin": "A_Coin"}
AO_TARGETS = {"A_Hero": ["RE2_Ribbon"], "A_Rings": ["RE2_RingsBase", "RE2_Ring0", "RE2_Ring1", "RE2_Ring2", "RE2_Ring3", "RE2_Ring4"],
              "A_Plates": ["RE2_PlatesMetal"], "A_Bars": ["RE2_BarsPlinth", "RE2_BarsBlocks"], "A_Coin": ["RE2_Coin"]}


def gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        scn.cycles.device = "GPU"
    except Exception as e:
        print("gpu", e)


def bake_ao(coll):
    scn.render.engine = "CYCLES"
    gpu()
    scn.cycles.samples = 128
    scn.render.bake.target = "VERTEX_COLORS"
    scn.world = scn.world or bpy.data.worlds.new("W")
    for name in AO_TARGETS[coll]:
        ob = bpy.data.objects[name]
        me = ob.data
        attr = me.color_attributes.get("AO") or me.color_attributes.new("AO", "BYTE_COLOR", "CORNER")
        me.color_attributes.active_color = attr
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        scn.world.light_settings.distance = 0.6
        bpy.ops.object.bake(type="AO")
        # keep the AO gentle: lift blacks so metal never goes fully dark
        import numpy as np
        n = len(attr.data)
        col = np.zeros(n * 4, np.float32)
        attr.data.foreach_get("color", col)
        col = col.reshape(-1, 4)
        col[:, :3] = 0.35 + 0.65 * col[:, :3]
        attr.data.foreach_set("color", col.ravel())
        print("baked AO", name, n)


def export(key, coll):
    L.only_collection(coll)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in bpy.data.collections[coll].all_objects)
    path = os.path.join(OUT, key + ".glb")
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
              export_cameras=False, export_lights=False, export_extras=False, export_texcoords=True,
              export_normals=True, export_tangents=False, export_image_format="AUTO")
    try:
        bpy.ops.export_scene.gltf(export_vertex_color="ACTIVE", **kw)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)
    print("exported", path, os.path.getsize(path) // 1024, "KB")


only = [s for s in os.environ.get("RE_ONLY", "").split(",") if s] or list(ASSETS)
for key in only:
    coll = ASSETS[key]
    L.only_collection(coll)
    if os.environ.get("RE_NOBAKE") != "1":
        bake_ao(coll)
    export(key, coll)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(L.HERE, "v2_models.blend"))
print("saved")
