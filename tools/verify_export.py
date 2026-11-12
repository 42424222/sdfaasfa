"""
Round-trip check of the exported files (run: blender -b --python tools/verify_export.py).

1. Loads AnimeFace.blend and records skinned vertex positions for a few poses.
2. Imports AnimeFace.fbx (and .glb) into empty scenes, checks bones / weights / UVs / normals /
   texture, applies the same poses through the imported rig and compares every vertex.
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
sys.path.insert(0, HERE)
import face_design as fd  # noqa: E402
import face_presets as fp  # noqa: E402
import build_blend as bb  # noqa: E402

POSES = ["Neutral", "Blink", "Laugh", "Angry", "Shy", "LookLeft", "LookUp", "Smug"]
MODEL = fd.build()
BONES = {b["name"]: b for b in MODEL["bones"]}
problems = []


def find(kind):
    objs = [o for o in bpy.context.scene.objects if o.type == kind]
    assert objs, f"no {kind} in scene"
    return objs[0]


def evaluated_world_verts(mesh_obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh_obj.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(mesh_obj.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    ev.to_mesh_clear()
    return co


def apply_pose(arm, offsets):
    """Pose from head-space bone motions so it works whatever the imported bone axes are."""
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    A = arm.matrix_world
    for name, val in offsets.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            problems.append(f"missing bone {name}")
            continue
        Mw = bb.motion_to_blender(fd.bone_motion(BONES[name], val))
        B = pb.bone.matrix_local
        pb.matrix_basis = B.inverted() @ A.inverted() @ Mw @ A @ B
    bpy.context.view_layer.update()


def record(path_kind):
    arm, mesh = find('ARMATURE'), find('MESH')
    if arm.animation_data:
        arm.animation_data.action = None
    out = {}
    for name in POSES:
        apply_pose(arm, fd.expand_pose(fp.PRESETS[name]))
        out[name] = evaluated_world_verts(mesh)
    return arm, mesh, out


def check_import(label, ref):
    arm, mesh = find('ARMATURE'), find('MESH')
    names = {b.name for b in arm.data.bones}
    expected = set(BONES)
    if names != expected:
        problems.append(f"{label}: bone set differs: missing {sorted(expected - names)} extra {sorted(names - expected)}")
    for b in arm.data.bones:
        want = BONES.get(b.name, {}).get("parent")
        got = b.parent.name if b.parent else None
        if b.name in BONES and want != got:
            problems.append(f"{label}: {b.name} parent {got} != {want}")
    me = mesh.data
    groups = {g.index: g.name for g in mesh.vertex_groups}
    max_inf = max(sum(1 for g in v.groups if g.weight > 1e-4) for v in me.vertices)
    root_w = any(groups[g.group] == "FaceRoot" and g.weight > 1e-4 for v in me.vertices for g in v.groups)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    imgs = [i for i in bpy.data.images if i.size[0] > 0]
    print(f"[{label}] verts={len(me.vertices)} tris={tris} bones={len(names)} groups={len(groups)} max_influences={max_inf} "
          f"uv_layers={len(me.uv_layers)} custom_normals={me.has_custom_normals} images={[(i.name, tuple(i.size)) for i in imgs]} "
          f"arm_matrix_scale={tuple(round(x, 4) for x in arm.matrix_world.to_scale())}")
    if max_inf > 4:
        problems.append(f"{label}: more than 4 influences")
    if root_w:
        problems.append(f"{label}: FaceRoot has influences")
    if len(me.uv_layers) == 0:
        problems.append(f"{label}: no UVs")
    # facing: the eyes must be on the -Y side in Blender (= the front)
    co = evaluated_world_verts(mesh)
    if co[:, 1].min() > -0.5:
        problems.append(f"{label}: face is not on the front (-Y) side")
    _, _, got = record(label)
    for name in POSES:
        a, b = ref[name], got[name]
        if len(a) == len(b):
            err = np.abs(a - b).max()
        else:
            tree = KDTree(len(a))
            for i, p in enumerate(ref["Neutral"]):
                tree.insert(p, i)
            tree.balance()
            idx = [tree.find(p)[1] for p in got["Neutral"]]
            err = np.abs(a[idx] - b).max()
        print(f"[{label}] pose {name:9s} max vertex deviation vs source: {err:.2e} studs")
        if err > 2e-4:
            problems.append(f"{label}: pose {name} deviates by {err:.2e}")


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ASSETS, "AnimeFace.blend"))
    _, _, ref = record("blend")
    print(f"[blend] bbox min {ref['Neutral'].min(0).round(4)} max {ref['Neutral'].max(0).round(4)}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ASSETS, "AnimeFace.fbx"))
    check_import("fbx", ref)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, "AnimeFace.glb"))
    check_import("glb", ref)

    print("PROBLEMS:" if problems else "VERIFY OK", problems)


if __name__ == "__main__":
    main()
