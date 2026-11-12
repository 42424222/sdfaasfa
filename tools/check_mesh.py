"""Structural checks for the generated face (run with system python3)."""
import collections
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import face_design as fd  # noqa: E402

m = fd.build()
P, F, W, bones = m["P"], m["F"], m["W"], m["bones"]
names = [b["name"] for b in bones]
tris = sum(len(f) - 2 for f in F)
print(f"verts {len(P)}  faces {len(F)}  triangles {tris}  bones {len(bones)}")
lo, hi = P.min(0), P.max(0)
print("bbox min", lo.round(4), "max", hi.round(4), "size", (hi - lo).round(4), "centre", ((hi + lo) / 2).round(4))

errors = []
if tris > 20000:
    errors.append(f"triangle budget exceeded: {tris}")
if len(set(names)) != len(names):
    errors.append("duplicate bone names")
inf = collections.Counter(len(w) for w in W)
print("influences per vertex:", dict(sorted(inf.items())))
if max(inf) > 4:
    errors.append("more than 4 influences")
used = collections.Counter(b for w in W for b in w)
for w in W:
    if abs(sum(w.values()) - 1) > 1e-6:
        errors.append("weights not normalised")
        break
unknown = set(used) - set(names)
if unknown:
    errors.append(f"weights on unknown bones: {sorted(unknown)}")
if "FaceRoot" in used:
    errors.append("root bone has influences")
print("bones without influences:", [n for n in names if n not in used])
parts = collections.Counter(p.split("_")[0] for p in m["part"])
print("faces per part:", dict(parts))
for f in F:
    if len(set(f)) != len(f):
        errors.append("degenerate face index")
        break
# zero-area faces would be dropped by importers
areas = []
for f in F:
    a, b, c = P[f[0]], P[f[1]], P[f[2]]
    areas.append(np.linalg.norm(np.cross(b - a, c - a)) / 2)
areas = np.array(areas)
print(f"smallest face area {areas.min():.3e}  faces < 1e-9: {(areas < 1e-9).sum()}")
if (areas < 1e-9).any():
    errors.append("zero-area faces present")

# the skin surface (head shell + lid patches + sockets + eye whites) must be watertight:
# every edge shared by exactly two faces once coincident vertices are merged
skin = [i for i, part in enumerate(m["part"]) if part.split("_")[0] in ("shell", "lid", "socket", "sclera")]
key = np.round(P / 1e-6).astype(np.int64)
_, vid = np.unique(key, axis=0, return_inverse=True)
vid = vid.ravel()
edge_use = collections.Counter()
for i in skin:
    f = [vid[k] for k in F[i]]
    for a, b in zip(f, f[1:] + f[:1]):
        edge_use[(min(a, b), max(a, b))] += 1
open_edges = sum(1 for n in edge_use.values() if n == 1)
over_edges = sum(1 for n in edge_use.values() if n > 2)
print(f"skin surface: {len(skin)} faces, open edges {open_edges}, edges shared by >2 faces {over_edges}")
if open_edges or over_edges:
    errors.append(f"skin surface not watertight ({open_edges} open, {over_edges} over-shared edges)")
print("ERRORS:" if errors else "OK", errors)
