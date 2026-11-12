"""
Height map of a face mesh over the front of the R6 head, in face design space (u, v).

Run: blender -b --python tools/heightmap.py -- <mesh.obj> <out_prefix> [u0 u1 v0 v1 px]
Casts a ray inward at every (u, v) and records the outermost surface offset from the head surface
(positive = outward, studs). Writes <out_prefix>_height.png (colour), <out_prefix>_shade.png
(normal shading) and prints depth statistics.
"""
import os
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import face_design as fd  # noqa: E402


def parse_obj(path):
    V, F = [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("v "):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            F.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    return np.array(V), F


def write_png(path, rgb):
    import bpy
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = rgb[::-1]
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    path, prefix = argv[0], argv[1]
    u0, u1, v0, v1, px = (float(x) for x in (argv[2:7] if len(argv) >= 7 else (-0.55, 0.55, -0.48, 0.28, 0.0012)))
    V, F = parse_obj(path)
    bvh = BVHTree.FromPolygons([Vector(v) for v in V], F, all_triangles=False, epsilon=0.0)
    us = np.arange(u0, u1, px)
    vs = np.arange(v1, v0, -px)              # top row first
    H = np.full((len(vs), len(us)), np.nan)
    N = np.zeros((len(vs), len(us), 3))
    lift = 0.15
    for r, v in enumerate(vs):
        P, Nn = fd.surf(us, np.full_like(us, v), lift)
        for c in range(len(us)):
            hit = bvh.ray_cast(Vector(P[c]), Vector(-Nn[c]), 0.4)
            if hit[0] is not None:
                H[r, c] = lift - hit[3]
                n = np.array(hit[1])
                N[r, c] = n if np.dot(n, Nn[c]) > 0 else -n
    lim = 0.04
    t = np.clip((np.nan_to_num(H, nan=-lim) + lim) / (2 * lim), 0, 1)
    rgb = np.stack([np.clip(2 * t, 0, 1), 1 - np.abs(2 * t - 1) * 0.6, np.clip(2 - 2 * t, 0, 1)], -1)
    for lvl in np.arange(-0.04, 0.0401, 0.005):     # contour lines every 0.005 studs
        rgb[np.abs(np.nan_to_num(H, nan=9) - lvl) < 0.00035] *= 0.55
    rgb[np.isnan(H)] = 0
    write_png(prefix + "_height.png", rgb)
    # shading in the local frame: light from upper-left-front
    shade = np.zeros(H.shape)
    for c, u in enumerate(us):
        T, U, Nf = fd.frame(u)
        L = -0.45 * T + 0.55 * U + 0.70 * Nf
        L /= np.linalg.norm(L)
        shade[:, c] = np.clip(N[:, c] @ L, 0, 1)
    write_png(prefix + "_shade.png", np.repeat((0.15 + 0.85 * shade)[..., None], 3, -1))
    front = ~np.isnan(H)
    print(f"grid {len(us)}x{len(vs)} hit {front.mean() * 100:.1f}%  height min {np.nanmin(H):.4f} max {np.nanmax(H):.4f}")
    for name, (a, b, c, d) in {"eye_R(u>0)": (0.10, 0.50, -0.30, -0.02), "brow_R": (0.10, 0.50, -0.02, 0.15),
                               "mouth": (-0.12, 0.12, -0.45, -0.32), "cheek_R": (0.25, 0.45, -0.40, -0.30)}.items():
        mu = (us >= a) & (us <= b)
        mv = (vs >= c) & (vs <= d)
        sub = H[np.ix_(mv, mu)]
        if np.isfinite(sub).any():
            print(f"  {name:11s} min {np.nanmin(sub):+.4f} p5 {np.nanpercentile(sub, 5):+.4f} median {np.nanmedian(sub):+.4f} "
                  f"p95 {np.nanpercentile(sub, 95):+.4f} max {np.nanmax(sub):+.4f}")
    np.save(prefix + "_height.npy", H)


if __name__ == "__main__":
    main()
