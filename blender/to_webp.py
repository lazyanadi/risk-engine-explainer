"""Convert the PNG renders in assets/ to WebP (keeps alpha). Run: blender -b --python blender/to_webp.py"""
import bpy, os
A = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
scn = bpy.context.scene
s = scn.render.image_settings
s.file_format, s.color_mode, s.quality = "WEBP", "RGBA", 86
for f in sorted(os.listdir(A)):
    if f.endswith(".png"):
        img = bpy.data.images.load(os.path.join(A, f))
        out = os.path.join(A, f[:-4] + ".webp")
        img.save_render(out, scene=scn)
        print("webp", out, os.path.getsize(out) // 1024, "KB")
