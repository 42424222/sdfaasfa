"""
Preview renders of AnimeFace.blend (Cycles, CPU).

Run:  blender -b assets/AnimeFace.blend --python tools/render_preview.py -- <mode> <out_dir> [names...]
modes:
  look    neutral face, front + three-quarter + side
  sheet   one tile per expression preset (front)
  poses   one tile per named preset in front and three-quarter view
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import face_design as fd  # noqa: E402
import build_blend as bb  # noqa: E402

try:
    import face_presets as fp  # noqa: E402
except ImportError:
    fp = None

SKIN = (1.0, 0.886, 0.80, 1.0)       # sRGB-ish preview skin tone (MeshPart.Color in Roblox)


def srgb_to_linear(c):
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c[:3]) + (1.0,)


def setup_material():
    mat = bpy.data.materials["AnimeFace_Mat"]
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes["Color"]
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = srgb_to_linear(SKIN)
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Factor"])
    nt.links.new(tex.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    # channel-packed: no premultiply round-trip (straight-alpha unpremultiply brightens low-alpha edges)
    tex.image.alpha_mode = 'CHANNEL_PACKED'


def setup_scene(res):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.view_settings.view_transform = 'Standard'
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("preview")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.33, 0.35, 0.40, 1)
    bg.inputs[1].default_value = 0.85
    key = bpy.data.objects.new("key", bpy.data.lights.new("key", 'SUN'))
    key.data.energy = 2.6
    key.data.angle = math.radians(12)
    key.rotation_euler = (math.radians(62), 0.0, math.radians(-28))
    scene.collection.objects.link(key)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'SUN'))
    fill.data.energy = 0.7
    fill.rotation_euler = (math.radians(75), 0.0, math.radians(40))
    scene.collection.objects.link(fill)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    for o in scene.objects:
        if o.type == 'ARMATURE':
            o.hide_render = True
        elif o.type == 'MESH':
            # Roblox's shadow maps cannot resolve the sub-0.02-stud layer offsets; Cycles would draw
            # micro-shadows around every overlay, so the face does not shadow itself in previews.
            o.visible_shadow = False
    return scene, cam


def aim(cam, loc, target, ortho=None, lens=85):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'
        cam.data.lens = lens


VIEWS = {
    "front": ((0.0, -6.0, -0.06), (0.0, 0.0, -0.06), 0.95),
    "three_quarter": ((-2.35, -4.1, 0.55), (0.0, 0.0, -0.08), None),
    "side": ((-6.0, -0.9, -0.05), (0.0, 0.0, -0.05), 1.05),
    "face_close": ((0.0, -6.0, -0.10), (0.0, 0.0, -0.10), 0.62),
}


def render(scene, cam, view, path):
    loc, target, ortho = VIEWS[view]
    aim(cam, loc, target, ortho=ortho, lens=110)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mode = argv[0] if argv else "look"
    out = argv[1] if len(argv) > 1 else "/tmp/work/render"
    names = argv[2:]
    os.makedirs(out, exist_ok=True)
    arm = bpy.data.objects["FaceRig"]
    if arm.animation_data:
        arm.animation_data.action = None
    model = fd.build()
    bones = {b["name"]: b for b in model["bones"]}
    setup_material()
    res = 900 if mode == "look" else 480
    scene, cam = setup_scene(res)

    def pose(name):
        offsets = fd.expand_pose(fp.PRESETS[name]) if (fp and name in fp.PRESETS) else {}
        bb.pose_offsets(arm, offsets, bones)
        bpy.context.view_layer.update()

    if mode in ("look", "quick"):
        pose(names[0] if names else "Neutral")
        views = ("front", "three_quarter", "side", "face_close") if mode == "look" else ("face_close", "three_quarter")
        for view in views:
            render(scene, cam, view, os.path.join(out, f"look_{view}.png"))
    elif mode == "sheet":
        for name in (names or list(fp.PRESETS)):
            pose(name)
            render(scene, cam, "front", os.path.join(out, f"sheet_{name}.png"))
    elif mode == "poses":
        for name in names:
            pose(name)
            render(scene, cam, "front", os.path.join(out, f"pose_{name}_front.png"))
            render(scene, cam, "three_quarter", os.path.join(out, f"pose_{name}_34.png"))


if __name__ == "__main__":
    main()
