"""
Build the AnimeFace .blend and export it for Roblox.

Run:  blender -b --python tools/build_blend.py
Outputs (assets/): AnimeFace.blend, AnimeFace.fbx, AnimeFace.glb

Blender space: the face looks toward -Y, Z is up, 1 Blender unit = 1 stud.
Export follows Roblox's documented Blender settings (FBX Unit Scale, Forward Z, Up Y, no leaf bones).
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
ASSETS = os.path.join(ROOT, "assets")
sys.path.insert(0, HERE)
import face_design as fd  # noqa: E402

try:
    import face_presets as fp  # noqa: E402
except ImportError:  # presets are optional while iterating on the look
    fp = None


def to_blender(p):
    """Roblox head space (X right, Y up, Z back) -> Blender (face toward -Y, Z up)."""
    p = np.asarray(p, float)
    return np.stack([-p[..., 0], p[..., 2], p[..., 1]], -1)


# The same mapping as a matrix (a proper rotation, det +1, so rotations keep their sense).
HEAD_TO_BLENDER = Matrix(((-1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))


def motion_to_blender(M):
    """Head-space 4x4 bone motion (face_design.bone_motion) -> Blender world space."""
    return HEAD_TO_BLENDER @ Matrix([list(r) for r in M]) @ HEAD_TO_BLENDER.inverted()


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'NONE'
    scene.unit_settings.scale_length = 1.0
    return scene


def build_material():
    tex_dir = os.path.join(ASSETS, "textures")
    mat = bpy.data.materials.new("AnimeFace_Mat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = bpy.data.images.load(os.path.join(tex_dir, "AnimeFace_Color.png"))
    img.name = "AnimeFace_Color"
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.name = tex.label = "Color"
    tex.image = img
    tex.location = (-500, 250)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    rimg = bpy.data.images.load(os.path.join(tex_dir, "AnimeFace_Roughness.png"))
    rimg.name = "AnimeFace_Roughness"
    rimg.colorspace_settings.name = 'Non-Color'
    rtex = nt.nodes.new("ShaderNodeTexImage")
    rtex.name = rtex.label = "Roughness"
    rtex.image = rimg
    rtex.location = (-500, -50)
    nt.links.new(rtex.outputs["Color"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    return mat


def build_mesh(model, mat):
    P = to_blender(model["P"])
    N = to_blender(model["N"])
    mesh = bpy.data.meshes.new("AnimeFace")
    mesh.from_pydata([tuple(v) for v in P], [], [tuple(f) for f in model["F"]])
    mesh.update()
    loop_vi = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loop_vi)
    uv = mesh.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", model["UV"][loop_vi].astype(np.float32).ravel())
    mesh.shade_smooth()
    mesh.normals_split_custom_set_from_vertices([tuple(n) for n in N])
    mesh.materials.append(mat)
    obj = bpy.data.objects.new("AnimeFace", mesh)
    bpy.context.scene.collection.objects.link(obj)
    groups = {}
    for i, w in enumerate(model["W"]):
        for b, x in w.items():
            if b not in groups:
                groups[b] = obj.vertex_groups.new(name=b)
            groups[b].add([i], float(x), 'REPLACE')
    return obj


def build_armature(model):
    data = bpy.data.armatures.new("FaceRig")
    data.display_type = 'STICK'
    arm = bpy.data.objects.new("FaceRig", data)
    arm.show_in_front = True
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for b in model["bones"]:
        eb = data.edit_bones.new(b["name"])
        head = Vector(to_blender(b["pos"]))
        length = {"FaceRoot": 0.12, "FaceBase": 0.09}.get(b["name"], 0.022)
        eb.head = head
        eb.tail = head + Vector((0.0, 0.0, length))
        if b["parent"]:
            eb.parent = data.edit_bones[b["parent"]]
            eb.use_connect = False
        _, _, n = fd.frame(b["frame_u"])
        eb.align_roll(Vector(to_blender(n)))   # local Z points out of the face, X along the surface
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm


def pose_offsets(arm, offsets, bones_by_name):
    """Apply face-space offsets (see face_design.bone_motion) as pose-bone transforms."""
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    A = arm.matrix_world
    for name, val in offsets.items():
        pb = arm.pose.bones[name]
        Mw = motion_to_blender(fd.bone_motion(bones_by_name[name], val))
        B = pb.bone.matrix_local
        pb.matrix_basis = B.inverted() @ A.inverted() @ Mw @ A @ B


def add_expression_action(arm, model):
    """One action with an expression per 10 frames (timeline markers carry the names)."""
    if fp is None:
        return
    scene = bpy.context.scene
    bones_by_name = {b["name"]: b for b in model["bones"]}
    arm.animation_data_create()
    action = bpy.data.actions.new("FaceExpressions")
    arm.animation_data.action = action
    names = list(fp.PRESETS)
    for i, name in enumerate(names):
        frame = i * 10
        pose_offsets(arm, fd.expand_pose(fp.PRESETS[name]), bones_by_name)
        for pb in arm.pose.bones:
            pb.keyframe_insert("location", frame=frame, group=pb.name)
            pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
        scene.timeline_markers.new(name, frame=frame)
    scene.frame_start, scene.frame_end = 0, (len(names) - 1) * 10
    for fc in getattr(action, "fcurves", []):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'
    scene.frame_set(0)


def export(arm, mesh_obj):
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    saved_action = arm.animation_data.action if arm.animation_data else None
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(ASSETS, "AnimeFace.fbx"),
        use_selection=True,
        object_types={'ARMATURE', 'MESH'},
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',
        axis_forward='Z',
        axis_up='Y',
        use_mesh_modifiers=False,
        mesh_smooth_type='OFF',
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        armature_nodetype='NULL',
        use_armature_deform_only=False,
        bake_anim=False,
        path_mode='COPY',
        embed_textures=True,
    )
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(ASSETS, "AnimeFace.glb"),
        export_format='GLB',
        use_selection=True,
        export_animations=False,
        export_skins=True,
        export_yup=True,
    )
    if saved_action is not None:
        arm.animation_data.action = saved_action


def main():
    scene = clear_scene()
    model = fd.build()
    mat = build_material()
    mesh_obj = build_mesh(model, mat)
    arm = build_armature(model)
    mesh_obj.parent = arm
    mod = mesh_obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    add_expression_action(arm, model)
    os.makedirs(ASSETS, exist_ok=True)
    export(arm, mesh_obj)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ASSETS, "AnimeFace.blend"), compress=True)
    tris = sum(len(p.vertices) - 2 for p in mesh_obj.data.polygons)
    print(f"BUILD OK verts={len(mesh_obj.data.vertices)} tris={tris} bones={len(arm.data.bones)} scene_unit={scene.unit_settings.system}")


if __name__ == "__main__":
    main()
