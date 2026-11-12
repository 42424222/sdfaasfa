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


def add_rest_normals(model):
    """Store the authored normals as a point attribute for the preview shader.

    The face bones only translate, so Roblox's skinned normals stay exactly as authored. Blender
    instead re-derives custom normals from the deformed faces, which would light the stretched
    lid skin differently in previews.
    """
    me = bpy.data.objects["AnimeFace"].data
    attr = me.attributes.get("rest_normal") or me.attributes.new("rest_normal", 'FLOAT_VECTOR', 'POINT')
    attr.data.foreach_set("vector", bb.to_blender(model["N"]).astype("float32").ravel())


def setup_material():
    """Raster-style preview shading: colour x (sky/ground ambient + key + fill), from the normal only.

    Roblox shades each pixel from its normal and the lights, with no ray-traced interaction
    between the thin face layers, so the previews do the same instead of path tracing
    (which draws false outlines around overlay patches floating a few thousandths of a stud up).
    """
    mat = bpy.data.materials["AnimeFace_Mat"]
    nt = mat.node_tree
    tex = nt.nodes["Color"]
    tex.image.alpha_mode = 'CHANNEL_PACKED'
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = srgb_to_linear(SKIN)
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Factor"])
    nt.links.new(tex.outputs["Color"], mix.inputs["B"])
    rest = nt.nodes.new("ShaderNodeAttribute")
    rest.attribute_name = "rest_normal"
    norm = nt.nodes.new("ShaderNodeVectorMath")
    norm.operation = 'NORMALIZE'
    nt.links.new(rest.outputs["Vector"], norm.inputs[0])
    normal = norm.outputs["Vector"]

    def math(op, a, b):
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                nt.links.new(v, m.inputs[i])
        return m.outputs[0]

    def lambert(direction, strength):
        d = Vector(direction).normalized()
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = 'DOT_PRODUCT'
        nt.links.new(normal, dot.inputs[0])
        dot.inputs[1].default_value = tuple(d)
        return math('MULTIPLY', math('MAXIMUM', dot.outputs["Value"], 0.0), strength)

    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(normal, sep.inputs[0])
    sky, ground = 0.50, 0.30
    key_dir = Vector((-0.45, -0.75, 0.55)).normalized()
    ambient = math('ADD', math('MULTIPLY', sep.outputs["Z"], (sky - ground) / 2), (sky + ground) / 2)
    light = math('ADD', math('ADD', ambient, lambert(key_dir, 0.62)), lambert((0.65, -0.55, 0.05), 0.14))
    scale = nt.nodes.new("ShaderNodeVectorMath")
    scale.operation = 'SCALE'
    nt.links.new(mix.outputs["Result"], scale.inputs[0])
    nt.links.new(light, scale.inputs["Scale"])
    # Blinn-Phong highlight from the key light, stronger on smooth surfaces (roughness map),
    # so the glossy black lash ridges read as 3D like they do under Roblox lighting
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    half = nt.nodes.new("ShaderNodeVectorMath")
    half.operation = 'ADD'
    half.inputs[1].default_value = tuple(key_dir)
    nt.links.new(geo.outputs["Incoming"], half.inputs[0])
    hn = nt.nodes.new("ShaderNodeVectorMath")
    hn.operation = 'NORMALIZE'
    nt.links.new(half.outputs["Vector"], hn.inputs[0])
    ndh = nt.nodes.new("ShaderNodeVectorMath")
    ndh.operation = 'DOT_PRODUCT'
    nt.links.new(normal, ndh.inputs[0])
    nt.links.new(hn.outputs["Vector"], ndh.inputs[1])
    gloss = math('POWER', math('SUBTRACT', 1.0, nt.nodes["Roughness"].outputs["Color"]), 2.0)
    spec = math('MULTIPLY', math('MULTIPLY', math('POWER', math('MAXIMUM', ndh.outputs["Value"], 0.0), 40.0), gloss), 0.9)
    lit = nt.nodes.new("ShaderNodeVectorMath")
    lit.operation = 'ADD'
    nt.links.new(scale.outputs[0], lit.inputs[0])
    nt.links.new(spec, lit.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(lit.outputs["Vector"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], nt.nodes["Material Output"].inputs["Surface"])


def setup_scene(res):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False   # emission-only shading: samples only anti-alias, keep lines crisp
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
    "front": ((0.0, -6.0, -0.15), (0.0, 0.0, -0.15), 0.95),
    "three_quarter": ((-2.35, -4.1, 0.55), (0.0, 0.0, -0.10), None),
    "side": ((-6.0, -0.9, -0.05), (0.0, 0.0, -0.05), 1.05),
    "face_close": ((0.0, -6.0, -0.17), (0.0, 0.0, -0.17), 0.80),
    "face_mid": ((0.0, -6.0, -0.17), (0.0, 0.0, -0.17), 0.80),
    # the character's right eye (head +X = Blender -X), straight on and from a three-quarter angle
    "eye_front": ((-0.257, -6.0, -0.085), (-0.257, 0.0, -0.085), 0.56),
    "eye_34": ((-1.10, -1.20, 0.30), (-0.30, -0.53, -0.09), None),
}

# Short demo clip at 12 fps: (expression, mouth override or None, frames). Talking flips 2D mouths.
ANIM_FPS = 12
ANIM = [
    ("Neutral", None, 8), ("Blink", None, 2), ("Neutral", None, 6),
    ("Smile", "OpenSmall", 2), ("Smile", "Open", 2), ("Smile", None, 1), ("Smile", "O", 2), ("Smile", "Teeth", 2),
    ("Smile", None, 1), ("Smile", "Open", 2), ("Smile", "OpenSmall", 2), ("Smile", None, 6),
    ("Happy", None, 10), ("Laugh", None, 10), ("Surprised", None, 8), ("Shocked", None, 8), ("Angry", None, 10),
    ("Sad", None, 10), ("Smug", None, 10), ("Shy", None, 10), ("Playful", None, 10), ("Wink", None, 10), ("Neutral", None, 6),
]


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
    add_rest_normals(model)
    setup_material()
    res = 900 if mode == "look" else (420 if mode == "anim" else 480)
    scene, cam = setup_scene(res)

    def pose(name):
        offsets = fd.expand_pose(fp.PRESETS[name]) if (fp and name in fp.PRESETS) else {}
        bb.pose_offsets(arm, offsets, bones)
        bpy.context.view_layer.update()

    if mode in ("look", "quick"):
        pose(names[0] if names else "Neutral")
        views = ("front", "three_quarter", "side", "face_close", "eye_front", "eye_34") if mode == "look" else ("face_close", "eye_front", "eye_34")
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
    elif mode == "anim":
        cache, frames = {}, []
        for expr, mouth, n in ANIM:
            key = (expr, mouth)
            if key not in cache:
                offsets = fd.expand_pose(fp.PRESETS[expr])
                if mouth:
                    offsets = {k: v for k, v in offsets.items() if not k.startswith("Mouth_")}
                    offsets.update(fd.mouth_offsets(mouth))
                bb.pose_offsets(arm, offsets, bones)
                bpy.context.view_layer.update()
                cache[key] = os.path.join(out, f"anim_{len(cache):02d}.png")
                render(scene, cam, "face_mid", cache[key])
            frames.append((cache[key], n))
        # ffmpeg concat list: each unique pose is held for its frame count
        with open(os.path.join(out, "anim.txt"), "w") as f:
            for path, n in frames:
                f.write(f"file '{path}'\nduration {n / ANIM_FPS:.4f}\n")
            f.write(f"file '{frames[-1][0]}'\n")


if __name__ == "__main__":
    main()
