"""Light, render and export the scenes made by build_hero.py.

Recommended (stable): background mode on the saved file, one stage at a time:
  set RE_MODE=export  &  blender -b blender\hero.blend --python blender\render.py
Modes (env RE_MODE, or a MODE global when run through the add-on socket):
  "preview"  small renders to tmp for checking
  "render"   hero poster + 4 card renders (transparent PNG) into assets/
  "export"   GLB exports into assets/ and save hero.blend
  "final"    render + export
"""
import bpy, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project folder
ASSETS = os.path.join(ROOT, "assets")
MODE = os.environ.get("RE_MODE") or globals().get("MODE", "preview")
PREVIEW_DIR = globals().get("PREVIEW_DIR", r"C:\Jarvis\tmp\blender-preview")


def world(scn, strength=1.0):
    w = bpy.data.worlds.get("RE_Studio") or bpy.data.worlds.new("RE_Studio")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    path = os.path.join(bpy.utils.system_resource("DATAFILES", path="studiolights/world"), "studio.exr")
    env.image = bpy.data.images.load(path, check_existing=True)
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0, 0, math.radians(70))
    coord = nt.nodes.new("ShaderNodeTexCoord")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")  # soften the HDRI's black areas: bright studio feel
    mix.data_type = "RGBA"
    mix.inputs["Factor"].default_value = 0.3
    mix.inputs["B"].default_value = (0.6, 0.66, 0.75, 1)
    nt.links.new(env.outputs["Color"], mix.inputs["A"])
    nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    scn.world = w


def area(scn, name, loc, energy, size, color=(1, 1, 1)):
    ld = bpy.data.lights.get(name) or bpy.data.lights.new(name, "AREA")
    ld.energy, ld.size, ld.color = energy, size, color
    ob = scn.objects.get(name) or bpy.data.objects.new(name, ld)
    if ob.name not in scn.collection.objects:
        scn.collection.objects.link(ob)
    ob.location = loc
    d = (Vector((0, 0, 0)) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def camera(scn, name, loc, target, lens=50):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens
    ob = scn.objects.get(name) or bpy.data.objects.new(name, cd)
    if ob.name not in scn.collection.objects:
        scn.collection.objects.link(ob)
    ob.location = loc
    d = (Vector(target) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scn.camera = ob
    return ob


def settings(scn, x, y, samples=64):
    r = scn.render
    r.engine = "BLENDER_EEVEE"
    r.resolution_x, r.resolution_y, r.resolution_percentage = x, y, 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    scn.eevee.taa_render_samples = samples
    if hasattr(scn.eevee, "use_raytracing"):
        scn.eevee.use_raytracing = True
    scn.view_settings.view_transform = "Standard"
    scn.view_settings.exposure = 0.0


def ctx(scn):
    """Context override that works with and without a UI window (background mode)."""
    wins = bpy.context.window_manager.windows
    if wins:
        wins[0].scene = scn
        return bpy.context.temp_override(window=wins[0], scene=scn, view_layer=scn.view_layers[0])
    return bpy.context.temp_override(scene=scn, view_layer=scn.view_layers[0])


def render(scn, path):
    scn.render.filepath = path
    if not bpy.context.window_manager.windows:  # background: no override (see export_glb)
        bpy.ops.render.render(write_still=True, scene=scn.name)
        return print("rendered", path)
    with ctx(scn):
        bpy.ops.render.render(write_still=True, scene=scn.name)
    print("rendered", path)


def setup_hero():
    scn = bpy.data.scenes["Hero"]
    world(scn, 1.0)
    area(scn, "RE_Key", (-4, -5, 5), 900, 5)
    area(scn, "RE_Rim", (5, 4, 3), 600, 6, (0.85, 0.9, 1.0))
    area(scn, "RE_Fill", (2, -6, -2), 250, 8)
    camera(scn, "RE_HeroCam", (1.1, -9.2, 2.6), (0.15, 0, -0.05), 50)
    root = scn.objects["RE_Hero"]
    root.rotation_euler = (math.radians(-8), math.radians(-14), math.radians(-18))
    return scn


def setup_props():
    scn = bpy.data.scenes["Props"]
    world(scn, 1.1)
    area(scn, "RE_PKey", (-3, -4, 6), 500, 4)
    area(scn, "RE_PRim", (4, 3, 4), 300, 5, (0.85, 0.9, 1.0))
    return scn


PROPS = [("RE_Prop_Rings", "prop-rings", (2.4, -3.0, 3.4), (0, 0, 0.0)),
         ("RE_Prop_Stack", "prop-stack", (2.6, -3.1, 2.4), (0, 0, 0.35)),
         ("RE_Prop_Dice", "prop-dice", (2.4, -3.0, 2.2), (0, 0, 0.3)),
         ("RE_Prop_Bars", "prop-bars", (2.6, -3.2, 2.3), (0, 0, 0.4))]


def export_glb(scn, names, path):
    """Export objects from `scn` without overriding the context scene.

    Overriding scene/view_layer to a non-active scene crashed Blender 5.2's depsgraph
    (EXCEPTION_ACCESS_VIOLATION in BKE_base_eval_flags), so instead the objects are
    linked into a temporary collection of the ACTIVE scene, exported, then unlinked.
    Transforms are reset to the origin for the export and restored afterwards.
    """
    active = bpy.context.scene
    vl = bpy.context.view_layer
    tmp = bpy.data.collections.new("RE_ExportTmp")
    active.collection.children.link(tmp)
    objs = [scn.objects[n] for n in names]
    saved = [(o, o.location.copy(), o.rotation_euler.copy()) for o in objs if o.parent is None]
    for o, _, _ in saved:
        o.location = (0, 0, 0)
        o.rotation_euler = (0, 0, 0)
    for o in objs:
        tmp.objects.link(o)
    vl.update()
    for o in active.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    try:
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                                  export_apply=True, export_yup=True, export_cameras=False,
                                  export_lights=False, export_extras=False)
    finally:
        for o in objs:
            tmp.objects.unlink(o)
        active.collection.children.unlink(tmp)
        bpy.data.collections.remove(tmp)
        for o, loc, rot in saved:
            o.location, o.rotation_euler = loc, rot
    print("exported", path, os.path.getsize(path) // 1024, "KB")


def run():
    hero = setup_hero()
    props = setup_props()
    if MODE == "preview":
        os.makedirs(PREVIEW_DIR, exist_ok=True)
        settings(hero, 960, 660, 16)
        render(hero, os.path.join(PREVIEW_DIR, "hero.png"))
        settings(props, 600, 450, 16)
        for name, slug, cam, tgt in PROPS:
            for o in props.objects:
                if o.type == "MESH":
                    o.hide_render = o.name != name
            ob = props.objects[name]
            camera(props, "RE_PropCam", Vector(cam) + ob.location, Vector(tgt) + ob.location, 50)
            render(props, os.path.join(PREVIEW_DIR, slug + ".png"))
        return
    os.makedirs(ASSETS, exist_ok=True)
    if MODE == "export":
        return export_and_save(hero, props)
    if MODE == "render":
        render_all(hero, props)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "hero.blend"))
        return
    render_all(hero, props)
    export_and_save(hero, props)


def render_all(hero, props):
    settings(hero, 1800, 1240, 96)
    render(hero, os.path.join(ASSETS, "hero-poster.png"))
    settings(props, 1200, 900, 96)
    for name, slug, cam, tgt in PROPS:
        for o in props.objects:
            if o.type == "MESH":
                o.hide_render = o.name != name
        ob = props.objects[name]
        camera(props, "RE_PropCam", Vector(cam) + ob.location, Vector(tgt) + ob.location, 50)
        render(props, os.path.join(ASSETS, slug + ".png"))


def export_and_save(hero, props):
    for o in props.objects:
        o.hide_render = False
    export_glb(hero, ["RE_Hero", "RE_Ribbon", "RE_Tiles", "RE_EmeraldCluster"], os.path.join(ASSETS, "hero.glb"))
    for name, slug, _, _ in PROPS:
        export_glb(props, [name], os.path.join(ASSETS, slug + ".glb"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "hero.blend"), copy=False)
    print("saved", bpy.data.filepath)


run()
