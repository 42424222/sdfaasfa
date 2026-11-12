"""
AnimeFace R6 - shared design data and procedural geometry.

Everything here is in Roblox head space, in studs:
  +X = character's right, +Y = up, +Z = back of the head (the face looks toward -Z),
  origin = centre of the R6 head.

Design space used for placing features on the head surface:
  u = horizontal arc length around the head (u > 0 is the character's right side)
  v = arc length along the head profile from the equator (v > 0 is up)

Imported by paint_atlas.py (system Python) and the Blender scripts, so it only needs numpy.
"""
import math

import numpy as np

# ---------------------------------------------------------------------------
# Head shape, measured from the supplied R6 mannequin head (a rounded cylinder)
# ---------------------------------------------------------------------------
HEAD_R = 0.6012          # band radius
HEAD_HALF_H = 0.6012     # half height
HEAD_CORNER = 0.3006     # radius of the rounded top/bottom edge
SHELL_PAD = 0.0008       # our shell wraps the original head so both can stay visible
R = HEAD_R + SHELL_PAD
RHO = HEAD_CORNER + SHELL_PAD
YC = HEAD_HALF_H - HEAD_CORNER      # half height of the straight band
RC = HEAD_R - HEAD_CORNER           # radius of the corner arc centre
ARC = RHO * math.pi / 2
V_MAX = YC + ARC + RC

# ---------------------------------------------------------------------------
# Layout (design space) and layer heights above the skin (studs)
# ---------------------------------------------------------------------------
EYE_U = 0.235
EYE_V = -0.085
SIDES = {"R": 1.0, "L": -1.0}        # R = +X (character right), L = -X

# Eye-local coordinates: ex = outward (toward the ear), ey = up, origin = eye centre.
# Each lid is two cubic segments with explicit corner tangents. Sharp corners (about 45 deg outer,
# 65 deg inner) let the lids close cleanly against the fixed corner points.
def _hermite(a, ta, b, tb, k=0.4):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ta = np.asarray(ta, float) / np.linalg.norm(ta)
    tb = np.asarray(tb, float) / np.linalg.norm(tb)
    L = k * np.linalg.norm(b - a)
    return [tuple(a), tuple(a + ta * L), tuple(b - tb * L), tuple(b)]


def _dir(deg):
    return (math.cos(math.radians(deg)), math.sin(math.radians(deg)))


EYE_INNER = (-0.115, -0.002)
EYE_OUTER = (0.125, 0.010)
EYE_TOP = (-0.008, 0.066)
EYE_BOTTOM = (0.006, -0.056)
EYE_UPPER = [_hermite(EYE_INNER, _dir(42), EYE_TOP, (1, 0)), _hermite(EYE_TOP, (1, 0), EYE_OUTER, _dir(-20))]
EYE_LOWER = [_hermite(EYE_OUTER, _dir(205), EYE_BOTTOM, (-1, 0)), _hermite(EYE_BOTTOM, (-1, 0), EYE_INNER, _dir(160))]
IRIS_C = (0.004, -0.002)
IRIS_R = (0.0585, 0.0675)
SCLERA_C, SCLERA_R, SCLERA_P = (0.004, 0.004), (0.152, 0.120), 2.6
RING_C, RING_R, RING_P = (0.004, 0.000), (0.208, 0.176), 2.4
RING_K = [0.0, 0.07, 0.16, 0.27, 0.40, 0.55, 0.70, 0.85, 1.0]
RING_FLAT_K = 0.60                    # ring stays fully raised up to this fraction

# Highlights relative to the iris centre, in screen-consistent u (not mirrored per eye)
HIGHLIGHTS = [
    # (du, dv), (rx, ry), rotation (deg)
    ((0.0195, 0.0245), (0.0158, 0.0118), 32.0),
    ((-0.0215, -0.0255), (0.0068, 0.0066), 0.0),
    ((-0.0040, 0.0400), (0.0034, 0.0034), 0.0),
]

BROW = [(-0.094, 0.150), (-0.032, 0.181), (0.068, 0.188), (0.132, 0.164)]
NOSE_U, NOSE_V = 0.004, -0.192
MOUTH_V = -0.283
MOUTH_HALF_W = 0.060
MOUTH_SMILE = 0.0075                  # corner lift of the resting mouth
BLUSH_U, BLUSH_V, BLUSH_SIZE = 0.262, -0.205, (0.150, 0.066)

H_SCLERA = 0.0012
H_IRIS = 0.0030
H_SHINE = 0.0040
H_RING = 0.0125
H_RING_RIM = -0.0015                  # the ring tucks under the skin at its edge: no exposed seam
H_WALL_BOTTOM = 0.0016
H_CREASE = 0.0134
H_LASH = 0.0142
H_BROW = 0.0142
H_NOSE = 0.0030
H_CAVITY = 0.0028
H_MOUTH_INNER = 0.0038
H_MOUTH_LINE = 0.0050
H_LIPSHADOW = 0.0020
H_BLUSH_HIDDEN = -0.0120
BLUSH_SHOW = 0.0270                   # outward move that brings the blush to +0.015

# ---------------------------------------------------------------------------
# Texture atlas (pixel rects on a 1024 canvas, origin top-left)
# ---------------------------------------------------------------------------
ATLAS = 1024
RECT = {
    "iris": (0, 0, 512, 512),
    "sclera": (512, 0, 768, 256),
    "lash": (768, 0, 896, 128),
    "brow": (896, 0, 1024, 128),
    "mouthline": (768, 128, 896, 256),
    "cavity": (896, 128, 1024, 256),
    "highlight": (512, 256, 640, 384),
    "skin": (640, 256, 768, 384),
    "teeth": (768, 256, 896, 384),
    "tongue": (896, 256, 1024, 384),
    "crease": (512, 384, 768, 448),
    "wall": (512, 448, 768, 512),
    "nose": (768, 384, 896, 512),
    "lipshadow": (896, 384, 1024, 512),
    "blush": (0, 512, 512, 768),
    "facepaint": (512, 512, 1024, 1024),
}
UV_MARGIN = 6  # pixels kept clear inside every rect

# Front of the shell gets its own UV island ("facepaint") for soft painted shading.
# Its bounds sit on shell grid lines (U: 12 columns of the 96-gon either side of centre).
FACE_U = 12 * (2 * math.pi * R / 96)
FACE_V0, FACE_V1 = -0.42, 0.25


def rect_uv(name, fx, fy):
    """Map rect-relative (fx, fy) in [0,1] (fy=0 at the rect top) to UV (v up)."""
    x0, y0, x1, y1 = RECT[name]
    m = UV_MARGIN
    fx, fy = np.broadcast_arrays(np.clip(np.asarray(fx, float), 0.0, 1.0), np.clip(np.asarray(fy, float), 0.0, 1.0))
    x = x0 + m + fx * (x1 - x0 - 2 * m)
    y = y0 + m + fy * (y1 - y0 - 2 * m)
    return np.stack([x / ATLAS, 1.0 - y / ATLAS], -1)


# ---------------------------------------------------------------------------
# Small math helpers
# ---------------------------------------------------------------------------
def smoothstep(x):
    x = np.clip(np.asarray(x, float), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def profile(v):
    """Head profile at signed arc length v -> (r, y, nr, ny)."""
    v = np.atleast_1d(np.asarray(v, float))
    s = np.where(v < 0, -1.0, 1.0)
    a = np.abs(v)
    r = np.empty_like(a)
    y = np.empty_like(a)
    nr = np.empty_like(a)
    ny = np.empty_like(a)
    band = a <= YC
    corner = (a > YC) & (a <= YC + ARC)
    cap = a > YC + ARC
    r[band], y[band], nr[band], ny[band] = R, a[band], 1.0, 0.0
    phi = (a[corner] - YC) / RHO
    r[corner] = RC + RHO * np.cos(phi)
    y[corner] = YC + RHO * np.sin(phi)
    nr[corner] = np.cos(phi)
    ny[corner] = np.sin(phi)
    r[cap] = np.maximum(RC - (a[cap] - YC - ARC), 0.0)
    y[cap], nr[cap], ny[cap] = YC + RHO, 0.0, 1.0
    return r, y * s, nr, ny * s


def surf(u, v, d=0.0):
    """Point and outward normal on the head surface, offset by d along the normal."""
    u = np.atleast_1d(np.asarray(u, float))
    v = np.atleast_1d(np.asarray(v, float))
    d = np.broadcast_to(np.asarray(d, float), u.shape)
    r, y, nr, ny = profile(v)
    th = u / R
    st, ct = np.sin(th), np.cos(th)
    n = np.stack([nr * st, ny, -nr * ct], -1)
    p = np.stack([r * st, y, -r * ct], -1) + n * d[..., None]
    return p, n


def frame(u):
    """Tangent frame on the band at horizontal position u: (T = +u direction, Up, N = outward)."""
    th = u / R
    T = np.array([math.cos(th), 0.0, math.sin(th)])
    N = np.array([math.sin(th), 0.0, -math.cos(th)])
    return T, np.array([0.0, 1.0, 0.0]), N


def bezier(P, n, dense=600):
    """Sample a cubic Bezier (4 points) or a chain of cubic segments, evenly by arc length."""
    P = np.asarray(P, float)
    segs = P if P.ndim == 3 else P[None]
    t = np.linspace(0.0, 1.0, dense)[:, None]
    parts = []
    for k, S4 in enumerate(segs):
        pts = ((1 - t) ** 3) * S4[0] + 3 * ((1 - t) ** 2) * t * S4[1] + 3 * (1 - t) * t * t * S4[2] + t ** 3 * S4[3]
        parts.append(pts if k == 0 else pts[1:])
    return resample(np.concatenate(parts), n)


def resample(pts, n):
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    target = np.linspace(0.0, cum[-1], n)
    return np.stack([np.interp(target, cum, pts[:, k]) for k in range(pts.shape[1])], -1)


def left_normals(pts):
    t = np.gradient(pts, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    return np.stack([-t[:, 1], t[:, 0]], -1)


def superellipse(c, rad, p, phi):
    cphi, sphi = np.cos(phi), np.sin(phi)
    x = rad[0] * np.sign(cphi) * np.abs(cphi) ** (2.0 / p)
    y = rad[1] * np.sign(sphi) * np.abs(sphi) ** (2.0 / p)
    return np.stack([c[0] + x, c[1] + y], -1)


def ctrl_weights(s, ctrl):
    """Smooth partition of unity along a curve parameter. ctrl = [(s_k, bone), ...] sorted."""
    s = float(np.clip(s, ctrl[0][0], ctrl[-1][0]))
    for (s0, b0), (s1, b1) in zip(ctrl[:-1], ctrl[1:]):
        if s0 <= s <= s1:
            f = float(smoothstep((s - s0) / (s1 - s0)))
            w = {}
            w[b0] = w.get(b0, 0.0) + 1.0 - f
            w[b1] = w.get(b1, 0.0) + f
            return w
    return {ctrl[-1][1]: 1.0}


def mix_weights(a, b, f):
    out = {}
    for k, x in a.items():
        out[k] = out.get(k, 0.0) + x * (1.0 - f)
    for k, x in b.items():
        out[k] = out.get(k, 0.0) + x * f
    return out


# ---------------------------------------------------------------------------
# Eye contour (shared by geometry, rig and preset solving)
# ---------------------------------------------------------------------------
N_UPPER = 49
N_LOWER = 37


def eye_contour():
    """Opening contour as a closed loop.

    Returns (pts[N,2], arc[N] 0=upper/1=lower, s[N] param along its arc, p[N] loop param).
    Upper arc runs inner->outer corner, lower arc runs outer->inner corner.
    """
    up = bezier(EYE_UPPER, N_UPPER)
    lo = bezier(EYE_LOWER, N_LOWER)
    pts = np.concatenate([up[:-1], lo[:-1]])
    arc = np.concatenate([np.zeros(N_UPPER - 1), np.ones(N_LOWER - 1)])
    s = np.concatenate([np.linspace(0, 1, N_UPPER)[:-1], np.linspace(0, 1, N_LOWER)[:-1]])
    p = np.concatenate([np.linspace(0, 0.5, N_UPPER)[:-1], np.linspace(0.5, 1.0, N_LOWER)[:-1]])
    return pts, arc, s, p


UP_BASIS = ["Eye", "LidUpperInner", "LidUpper", "LidUpperOuter", "Eye"]
LOW_BASIS = ["Eye", "LidLower", "LidLower", "LidLower", "Eye"]
UP_BONE_S = [(0.25, "LidUpperInner"), (0.5, "LidUpper"), (0.75, "LidUpperOuter")]
BROW_CTRL = [(0.0, "BrowInner"), (0.5, "Brow"), (1.0, "BrowOuter")]


def bernstein(s, bones):
    """Degree-n Bernstein weights: smooth, pinned to the first/last bone at the ends."""
    n = len(bones) - 1
    s = float(np.clip(s, 0.0, 1.0))
    w = {}
    for k, b in enumerate(bones):
        w[b] = w.get(b, 0.0) + math.comb(n, k) * s ** k * (1 - s) ** (n - k)
    return w


def lid_weights(arc, s):
    """Lid weights along a contour arc (0 = upper inner->outer, 1 = lower outer->inner)."""
    return bernstein(s, UP_BASIS if arc == 0 else LOW_BASIS)


def sided(w, side):
    return {f"{k}_{side}": x for k, x in w.items()}


def contour_weights(arc, s, side):
    return sided(lid_weights(arc, s), side)


def mouth_ctrl(lip):
    return [(-1.0, "MouthCorner_L"), (-0.5, f"{lip}_L"), (0.0, lip), (0.5, f"{lip}_R"), (1.0, "MouthCorner_R")]


# ---------------------------------------------------------------------------
# Mesh accumulator
# ---------------------------------------------------------------------------
class MeshBuilder:
    def __init__(self):
        self.P, self.N, self.UV, self.W, self.F, self.part = [], [], [], [], [], []
        self.count = 0

    def add(self, part, P, N, UV, W, faces, keep_winding=False):
        P = np.asarray(P, float).reshape(-1, 3)
        N = np.asarray(N, float).reshape(-1, 3)
        UV = np.asarray(UV, float).reshape(-1, 2)
        assert len(P) == len(N) == len(UV) == len(W), part
        base = self.count
        self.P.append(P)
        self.N.append(N / np.linalg.norm(N, axis=1, keepdims=True))
        self.UV.append(UV)
        self.W.extend(W)
        for f in faces:
            self.F.append(([base + i for i in f], keep_winding))
            self.part.append(part)
        self.count += len(P)
        return base

    def result(self):
        P = np.concatenate(self.P)
        N = np.concatenate(self.N)
        F = []
        for f, keep in self.F:
            if keep:
                F.append(f)
                continue
            # wind every face so its geometric normal agrees with the authored normal
            a, b, c = P[f[0]], P[f[1]], P[f[2]]
            gn = np.cross(b - a, c - a)
            if len(f) == 4:
                gn = gn + np.cross(c - a, P[f[3]] - a)
            if np.dot(gn, N[f].mean(0)) < 0:
                f = f[::-1]
            F.append(f)
        W = []
        for w in self.W:
            w = {k: x for k, x in w.items() if x > 1e-4}
            top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
            tot = sum(x for _, x in top)
            W.append({k: x / tot for k, x in top})
        return dict(P=P, N=N, UV=np.concatenate(self.UV), F=F, W=W, part=list(self.part))


def grid_faces(rows, cols, wrap=False):
    """Quads for a rows x cols vertex grid (row-major). wrap closes the columns into a loop."""
    faces = []
    cmax = cols if wrap else cols - 1
    for r in range(rows - 1):
        for c in range(cmax):
            c2 = (c + 1) % cols
            faces.append([r * cols + c, r * cols + c2, (r + 1) * cols + c2, (r + 1) * cols + c])
    return faces


def disc_faces(nrings, nseg):
    """Centre vertex + nrings rings of nseg vertices."""
    faces = [[0, 1 + i, 1 + (i + 1) % nseg] for i in range(nseg)]
    faces += [[1 + a for a in f] for f in grid_faces(nrings, nseg, wrap=True)]
    return faces


def ribbon(inner, outer):
    """Quads between two polylines of equal length (vertex order: inner..., outer...)."""
    n = len(inner)
    return [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)]


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
def build_shell(mb):
    nt = 96
    band = [YC * k / 6 for k in range(7)]
    a_vals = band + [YC + ARC * k / 10 for k in range(1, 11)] + [YC + ARC + d for d in (0.075, 0.150, 0.225)]
    v_vals = sorted(set([round(-a, 6) for a in a_vals] + [round(a, 6) for a in a_vals] + [FACE_V0, FACE_V1]))
    rows = len(v_vals)
    cols = nt + 1
    u = np.linspace(-math.pi * R, math.pi * R, cols)        # seam at the back of the head
    uu, vv = np.meshgrid(u, np.array(v_vals))
    P, N = surf(uu.ravel(), vv.ravel(), 0.0)
    skin_uv = rect_uv("skin", 0.15 + 0.7 * (uu.ravel() / (2 * math.pi * R) + 0.5),
                      0.15 + 0.7 * (1 - (vv.ravel() + V_MAX) / (2 * V_MAX)))
    face_uv = rect_uv("facepaint", (uu.ravel() + FACE_U) / (2 * FACE_U), (FACE_V1 - vv.ravel()) / (FACE_V1 - FACE_V0))
    regions = {"skin": [], "face": []}
    for f in grid_faces(rows, cols):
        cu = uu.ravel()[f].mean()
        cv = vv.ravel()[f].mean()
        inside = abs(cu) < FACE_U and FACE_V0 < cv < FACE_V1
        regions["face" if inside else "skin"].append(f)
    W1 = {"FaceBase": 1.0}
    for key, uvs in (("skin", skin_uv), ("face", face_uv)):
        faces = regions[key]
        used = sorted({i for f in faces for i in f})
        remap = {old: new for new, old in enumerate(used)}
        idx = np.array(used)
        mb.add(f"shell_{key}", P[idx], N[idx], uvs[idx], [W1] * len(idx), [[remap[i] for i in f] for f in faces])
    # pole fans
    for sgn, row in ((-1, 0), (1, rows - 1)):
        ring = np.arange(row * cols, row * cols + cols)
        pp, pn = surf(np.array([0.0]), np.array([sgn * V_MAX]), 0.0)
        Pf = np.concatenate([P[ring], pp])
        Nf = np.concatenate([N[ring], pn])
        UVf = np.concatenate([skin_uv[ring], rect_uv("skin", [0.5], [0.15 if sgn > 0 else 0.85])])
        faces = [[c, c + 1, cols] for c in range(cols - 1)]
        mb.add("shell_skin", Pf, Nf, UVf, [W1] * len(Pf), faces)


def eye_uv_to_world(side, ex, ey, d):
    u = EYE_U * SIDES[side] + SIDES[side] * np.asarray(ex, float)
    v = EYE_V + np.asarray(ey, float)
    return surf(u, v, d)


def flat_to_world(side, ex, ey, d, du=None):
    """Point in the flat plane tangent to the head at the eye centre (for iris/highlights)."""
    sgn = SIDES[side]
    uc = EYE_U * sgn
    T, U, N = frame(uc)
    p0, _ = surf(np.array([uc]), np.array([EYE_V]), 0.0)
    x = sgn * np.asarray(ex, float)
    if du is not None:
        x = x + du
    P = p0 + x[..., None] * T + np.asarray(ey, float)[..., None] * U + d * N
    return P, np.broadcast_to(N, P.shape)


def build_eye(mb, side):
    sgn = SIDES[side]
    pts, arc, s, p = eye_contour()
    n = len(pts)
    cw = [contour_weights(arc[i], s[i], side) for i in range(n)]
    eye = {f"Eye_{side}": 1.0}

    # --- sclera (conformal, white)
    rings = [0.0, 0.3, 0.55, 0.75, 0.9, 1.0]
    nseg = 72
    phi = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    pts2 = [np.array([SCLERA_C])]
    for k in rings[1:]:
        pts2.append(superellipse(SCLERA_C, (SCLERA_R[0] * k, SCLERA_R[1] * k), SCLERA_P, phi))
    flat = np.concatenate(pts2)
    P, N = eye_uv_to_world(side, flat[:, 0], flat[:, 1], H_SCLERA)
    UV = rect_uv("sclera", 0.5 + 0.5 * flat[:, 0] / 0.16, 0.5 - 0.5 * flat[:, 1] / 0.13)
    mb.add(f"sclera_{side}", P, N, UV, [eye] * len(P), disc_faces(len(rings) - 1, nseg))

    # --- iris (flat disc in the eye's tangent plane)
    rings = [0.0, 0.18, 0.40, 0.62, 0.80, 0.92, 1.0]
    disc = [np.zeros((1, 2))]
    for k in rings[1:]:
        disc.append(np.stack([np.cos(phi) * k, np.sin(phi) * k], -1))
    disc = np.concatenate(disc)
    ex = IRIS_C[0] + disc[:, 0] * IRIS_R[0]
    ey = IRIS_C[1] + disc[:, 1] * IRIS_R[1]
    P, N = flat_to_world(side, ex, ey, H_IRIS)
    UV = rect_uv("iris", 0.5 + 0.5 * 0.97 * disc[:, 0], 0.5 - 0.5 * 0.97 * disc[:, 1])
    mb.add(f"iris_{side}", P, N, UV, [{f"Iris_{side}": 1.0}] * len(P), disc_faces(len(rings) - 1, nseg))

    # --- highlights (flat, slightly in front of the iris; screen-consistent placement)
    hp = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    for (du, dv), (rx, ry), rot in HIGHLIGHTS:
        a = math.radians(rot)
        lx = np.cos(hp) * rx
        ly = np.sin(hp) * ry
        x = lx * math.cos(a) - ly * math.sin(a)
        y = lx * math.sin(a) + ly * math.cos(a)
        x = np.concatenate([[0.0], x])
        y = np.concatenate([[0.0], y])
        P, N = flat_to_world(side, np.full_like(x, IRIS_C[0]), IRIS_C[1] + dv + y, H_SHINE, du=du + x)
        UV = rect_uv("highlight", 0.5 + x / 0.1, 0.5 - y / 0.1)
        hf = [[0, 1 + i, 1 + (i + 1) % 32] for i in range(32)]
        mb.add(f"shine_{side}", P, N, UV, [{f"Shine_{side}": 1.0}] * len(P), hf)

    # --- skin ring (lid mask) with a raised inner area that hides the iris and closes for blinks
    ang = np.arctan2(pts[:, 1] - RING_C[1], pts[:, 0] - RING_C[0])
    rim = superellipse(RING_C, RING_R, RING_P, ang)
    ring_pts, ring_h, ring_w = [], [], []
    for k in RING_K:
        ring_pts.append(pts + (rim - pts) * k)
        h = H_RING if k <= RING_FLAT_K else H_RING + (H_RING_RIM - H_RING) * float(smoothstep((k - RING_FLAT_K) / (1 - RING_FLAT_K)))
        ring_h.append(np.full(n, h))
        f = (1.0 - k) ** 1.6
        ring_w.extend(mix_weights(cw[i], eye, 1.0 - f) for i in range(n))
    rp = np.concatenate(ring_pts)
    P, N = eye_uv_to_world(side, rp[:, 0], rp[:, 1], np.concatenate(ring_h))
    UV = rect_uv("skin", 0.5 + rp[:, 0] / 0.6, 0.5 - rp[:, 1] / 0.6)
    mb.add(f"ring_{side}", P, N, UV, ring_w, grid_faces(len(RING_K), n, wrap=True))

    # --- wall: short skirt from the lid edge down to the sclera (upper part dark like the lashes)
    P1, N1 = eye_uv_to_world(side, pts[:, 0], pts[:, 1], H_RING)
    P2, _ = eye_uv_to_world(side, pts[:, 0], pts[:, 1], H_WALL_BOTTOM)
    UV = np.concatenate([rect_uv("wall", p, 0.0), rect_uv("wall", p, 1.0)])
    # The skirt is perpendicular to the skin, so it is emitted double-sided with explicit winding
    # (separate vertices per side: mesh tools drop faces that reuse the same vertex set).
    # Authored normals stay radial so it shades like the surrounding skin.
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    for fl in (faces, [f[::-1] for f in faces]):
        mb.add(f"wall_{side}", np.concatenate([P1, P2]), np.concatenate([N1, N1]), UV, cw + cw, fl, keep_winding=True)

    # --- upper lash line (+ outer flick and two lash spikes)
    up = bezier(EYE_UPPER, 61)
    su = np.linspace(0, 1, len(up))
    nrm = left_normals(up)
    o = up[-1]
    tang = up[-1] - up[-3]
    tang /= np.linalg.norm(tang)
    flick = bezier([o, o + tang * 0.012, o + np.array([0.030, -0.001]), o + np.array([0.040, -0.009])], 11)[1:]
    fl_n = left_normals(np.concatenate([up[-2:], flick]))[2:]
    base = np.concatenate([up, flick])
    norms = np.concatenate([nrm, fl_n])
    width = np.interp(su, [0.0, 0.08, 0.3, 0.55, 0.85, 1.0], [0.0035, 0.0085, 0.0150, 0.0168, 0.0160, 0.0130])
    fw = np.interp(np.linspace(0, 1, len(flick)), [0, 0.6, 1.0], [0.0118, 0.0062, 0.0010])
    width = np.concatenate([width, fw])
    over = np.concatenate([np.interp(su, [0, 0.1, 0.9, 1], [0.0008, 0.0020, 0.0020, 0.0012]), np.full(len(flick), 0.0006)])
    inner = base - norms * over[:, None]
    outer = base + norms * width[:, None]
    allp = np.concatenate([inner, outer])
    P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_LASH)
    along = np.linspace(0, 1, len(base))
    UV = np.concatenate([rect_uv("lash", along, 0.0), rect_uv("lash", along, 1.0)])
    lw = [contour_weights(0, x, side) for x in su] + [eye] * len(flick)
    mb.add(f"lash_{side}", P, N, UV, lw + lw, ribbon(inner, outer))

    for s_attach, length, bend, wbase in ((0.70, 0.019, 0.55, 0.0062), (0.86, 0.016, 0.75, 0.0055)):
        i = int(round(s_attach * (len(up) - 1)))
        root = outer[i] - norms[i] * 0.004
        d0 = norms[i]
        t_out = np.array([1.0, -0.15])
        t_out /= np.linalg.norm(t_out)
        d1 = d0 * (1 - bend) + t_out * bend
        d1 /= np.linalg.norm(d1)
        cen = bezier([root, root + d0 * length * 0.4, root + d1 * length * 0.8, root + d1 * length], 7)
        cn = left_normals(cen)
        sw = np.linspace(wbase, 0.0004, len(cen))
        a1 = cen - cn * sw[:, None] / 2
        a2 = cen + cn * sw[:, None] / 2
        allp = np.concatenate([a1, a2])
        P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_LASH + 0.0002)
        al = np.linspace(0.2, 0.8, len(cen))
        UV = np.concatenate([rect_uv("lash", al, 0.3), rect_uv("lash", al, 0.9)])
        w = contour_weights(0, s_attach, side)
        mb.add(f"lash_{side}", P, N, UV, [w] * len(allp), ribbon(a1, a2))

    # --- lower lash (outer part of the lower lid)
    lo = bezier(EYE_LOWER, 49)
    sl = np.linspace(0, 1, len(lo))
    keep = sl <= 0.56
    lo, sl = lo[keep], sl[keep]
    nl = left_normals(lo)
    lwid = np.interp(sl, [0.0, 0.05, 0.16, 0.36, 0.56], [0.0030, 0.0046, 0.0050, 0.0030, 0.0002])
    inner = lo - nl * 0.0009
    outer = lo + nl * lwid[:, None]
    allp = np.concatenate([inner, outer])
    P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_LASH)
    al = np.linspace(0, 1, len(lo))
    UV = np.concatenate([rect_uv("lash", al, 0.0), rect_uv("lash", al, 1.0)])
    lw = [contour_weights(1, x, side) for x in sl]
    mb.add(f"lashlow_{side}", P, N, UV, lw + lw, ribbon(inner, outer))

    # --- eyelid crease (soft shadow line that follows the lid partially)
    cs = np.linspace(0.30, 0.97, 31)
    upd = bezier(EYE_UPPER, 201)
    idx = np.round(cs * 200).astype(int)
    cpts = upd[idx]
    cn = left_normals(upd)[idx]
    gap = np.interp(cs, [0.3, 0.6, 0.97], [0.020, 0.024, 0.016])
    cen = cpts + cn * gap[:, None]
    cwid = np.interp(cs, [0.30, 0.42, 0.85, 0.97], [0.0004, 0.0030, 0.0026, 0.0004])
    a1 = cen - cn * cwid[:, None] / 2
    a2 = cen + cn * cwid[:, None] / 2
    allp = np.concatenate([a1, a2])
    P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_CREASE)
    al = np.linspace(0, 1, len(cs))
    UV = np.concatenate([rect_uv("crease", al, 0.0), rect_uv("crease", al, 1.0)])
    w = [mix_weights(contour_weights(0, x, side), eye, 0.62) for x in cs]
    mb.add(f"crease_{side}", P, N, UV, w + w, ribbon(a1, a2))


def build_brow(mb, side):
    cen = bezier(BROW, 41)
    s = np.linspace(0, 1, len(cen))
    n = left_normals(cen)
    w = np.interp(s, [0.0, 0.06, 0.35, 0.75, 1.0], [0.0128, 0.0150, 0.0120, 0.0068, 0.0016])
    shift = np.interp(s, [0, 1], [0.0, 0.0010])
    a1 = cen - n * (w / 2 - shift)[:, None]
    a2 = cen + n * (w / 2 + shift)[:, None]
    # slanted inner cut: pull the lower inner corner a little outward
    a1[0] = a1[0] + (cen[1] - cen[0]) * 0.9
    allp = np.concatenate([a1, a2])
    P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_BROW)
    UV = np.concatenate([rect_uv("brow", s, 0.0), rect_uv("brow", s, 1.0)])
    bw = [sided(ctrl_weights(x, BROW_CTRL), side) for x in s]
    mb.add(f"brow_{side}", P, N, UV, bw + bw, ribbon(a1, a2))


def build_nose(mb):
    # small tapered tip line + soft side shadow
    cen = bezier([(0.010, -0.170), (0.012, -0.183), (0.008, -0.194), (-0.006, -0.197)], 13)
    cen[:, 0] += NOSE_U
    cen[:, 1] += NOSE_V + 0.192
    s = np.linspace(0, 1, len(cen))
    n = left_normals(cen)
    w = np.interp(s, [0, 0.35, 0.8, 1], [0.0006, 0.0034, 0.0030, 0.0006])
    a1 = cen - n * w[:, None] / 2
    a2 = cen + n * w[:, None] / 2
    allp = np.concatenate([a1, a2])
    P, N = surf(allp[:, 0], allp[:, 1], H_NOSE)
    UV = np.concatenate([rect_uv("nose", s * 0.45, 0.0), rect_uv("nose", s * 0.45, 1.0)])
    mb.add("nose", P, N, UV, [{"Nose": 1.0}] * len(allp), ribbon(a1, a2))
    # the soft side shadow is painted on the shell ("facepaint"), not separate geometry


def mouth_curves(t):
    """Rest centreline and the upper/lower lip curves of the closed mouth."""
    t = np.asarray(t, float)
    c = MOUTH_V + MOUTH_SMILE * np.minimum(t * t, 1.0) + np.where(np.abs(t) > 1, (np.abs(t) - 1) * 0.02, 0.0)
    eps = 0.0004 + 0.0004 * np.clip(1 - t * t, 0, 1)
    return c, c + eps, c - eps


def build_mouth(mb):
    up_ctrl = mouth_ctrl("LipUpper")
    lo_ctrl = mouth_ctrl("LipLower")

    def uw(t):
        return ctrl_weights(t, up_ctrl)

    def lw(t):
        return ctrl_weights(t, lo_ctrl)

    # cavity
    t = np.linspace(-1, 1, 33)
    _, U, L = mouth_curves(t)
    x = t * MOUTH_HALF_W
    P, N = surf(np.concatenate([x, x]), np.concatenate([U, L]), H_CAVITY)
    UV = np.concatenate([rect_uv("cavity", (t + 1) / 2, 0.0), rect_uv("cavity", (t + 1) / 2, 1.0)])
    W = [uw(a) for a in t] + [lw(a) for a in t]
    mb.add("cavity", P, N, UV, W, ribbon(t, t))

    # upper teeth: top follows the upper lip, bottom edge sits 22% of the way to the lower lip
    tt = np.linspace(-0.92, 0.92, 29)
    _, U, L = mouth_curves(tt)
    x = tt * MOUTH_HALF_W
    P, N = surf(np.concatenate([x, x]), np.concatenate([U + 0.0001, U - 0.0008]), H_MOUTH_INNER)
    UV = np.concatenate([rect_uv("teeth", (tt / 0.92 + 1) / 2, 0.0), rect_uv("teeth", (tt / 0.92 + 1) / 2, 1.0)])
    W = [uw(a) for a in tt] + [mix_weights(uw(a), lw(a), 0.30) for a in tt]
    mb.add("teeth", P, N, UV, W, ribbon(tt, tt))

    # tongue: bottom follows the lower lip, rounded top rises with the opening
    tg = np.linspace(-0.72, 0.72, 25)
    _, U, L = mouth_curves(tg)
    bulge = np.sqrt(np.clip(1 - (tg / 0.72) ** 2, 0, 1))
    x = tg * MOUTH_HALF_W
    P, N = surf(np.concatenate([x, x]), np.concatenate([L - 0.0001, L + 0.0009 * bulge]), H_MOUTH_INNER + 0.0002)
    UV = np.concatenate([rect_uv("tongue", (tg / 0.72 + 1) / 2, 1.0), rect_uv("tongue", (tg / 0.72 + 1) / 2, 0.0)])
    W = [lw(a) for a in tg] + [mix_weights(lw(a), uw(a), 0.36 * b) for a, b in zip(tg, bulge)]
    mb.add("tongue", P, N, UV, W, ribbon(tg, tg))

    # lip lines (upper is a little heavier and extends past the corners)
    tu = np.linspace(-1.10, 1.10, 45)
    _, U, _ = mouth_curves(tu)
    a = np.clip(1 - tu * tu, 0, 1) ** 0.6
    th = 0.0010 + 0.0022 * a
    th = np.where(np.abs(tu) > 1, 0.0010 * np.clip((1.10 - np.abs(tu)) / 0.10, 0, 1) + 0.0001, th)
    x = tu * MOUTH_HALF_W
    P, N = surf(np.concatenate([x, x]), np.concatenate([U - 0.0015, U + th]), H_MOUTH_LINE)
    al = (tu + 1.1) / 2.2
    UV = np.concatenate([rect_uv("mouthline", al, 0.0), rect_uv("mouthline", al, 1.0)])
    W = [uw(a) for a in tu]
    mb.add("lipline", P, N, UV, W + W, ribbon(tu, tu))

    tl = np.linspace(-1.0, 1.0, 37)
    _, _, L = mouth_curves(tl)
    a = np.clip(1 - tl * tl, 0, 1) ** 0.6
    th = 0.0006 + 0.0016 * a
    x = tl * MOUTH_HALF_W
    P, N = surf(np.concatenate([x, x]), np.concatenate([L + 0.0015, L - th]), H_MOUTH_LINE - 0.0001)
    al = (tl + 1) / 2
    UV = np.concatenate([rect_uv("mouthline", al, 0.0), rect_uv("mouthline", al, 1.0)])
    W = [lw(a) for a in tl]
    mb.add("lipline", P, N, UV, W + W, ribbon(tl, tl))

    # soft lower-lip shadow that rides on the jaw
    ts = np.linspace(-1, 1, 13)
    x = ts * 0.016
    y = MOUTH_V - 0.020 + 0.0015 * ts * ts
    th = 0.0026 * np.clip(1 - ts * ts, 0, 1) ** 0.5 + 0.0002
    P, N = surf(np.concatenate([x, x]), np.concatenate([y + th / 2, y - th / 2]), H_LIPSHADOW)
    UV = np.concatenate([rect_uv("lipshadow", (ts + 1) / 2, 0.0), rect_uv("lipshadow", (ts + 1) / 2, 1.0)])
    mb.add("lipshadow", P, N, UV, [{"LipLower": 1.0}] * (2 * len(ts)), ribbon(ts, ts))


def build_blush(mb, side):
    sgn = SIDES[side]
    gx, gy = np.meshgrid(np.linspace(-1, 1, 15), np.linspace(-1, 1, 7))
    pu = sgn * BLUSH_U + gx.ravel() * BLUSH_SIZE[0] / 2
    pv = BLUSH_V + gy.ravel() * BLUSH_SIZE[1] / 2
    P, N = surf(pu, pv, H_BLUSH_HIDDEN)
    fx = (gx.ravel() + 1) / 2                # not mirrored: hatch lines lean the same way on both cheeks
    UV = rect_uv("blush", fx, (1 - gy.ravel()) / 2)
    mb.add(f"blush_{side}", P, N, UV, [{f"Blush_{side}": 1.0}] * len(pu), grid_faces(7, 15))


# ---------------------------------------------------------------------------
# Rig
# ---------------------------------------------------------------------------
def bone_defs():
    """Bones in parent-first order: name, parent, position (head space), frame_u (tangent frame)."""
    B = []

    def add(name, parent, u, v, d, frame_u=None, pos=None):
        if pos is None:
            pos = surf(np.array([u]), np.array([v]), d)[0][0]
        B.append(dict(name=name, parent=parent, pos=np.asarray(pos, float), frame_u=u if frame_u is None else frame_u))

    add("FaceRoot", None, 0.0, 0.0, 0.0, pos=(0.0, 0.0, 0.0))
    add("FaceBase", "FaceRoot", 0.0, 0.0, 0.0, pos=(0.0, 0.0, 0.0))
    pts, arc, s, _ = eye_contour()
    up = bezier(EYE_UPPER, 201)
    lo = bezier(EYE_LOWER, 201)
    for side, sgn in (("L", -1.0), ("R", 1.0)):
        uc = EYE_U * sgn

        def eu(ex):
            return uc + sgn * ex

        add(f"Eye_{side}", "FaceBase", uc, EYE_V, 0.020, frame_u=uc)
        add(f"Iris_{side}", f"Eye_{side}", eu(IRIS_C[0]), EYE_V + IRIS_C[1], 0.026, frame_u=uc)
        du, dv = HIGHLIGHTS[0][0]
        add(f"Shine_{side}", f"Iris_{side}", eu(IRIS_C[0]) + du, EYE_V + IRIS_C[1] + dv, 0.030, frame_u=uc)
        for sp, name in UP_BONE_S:
            q = up[int(round(sp * 200))]
            add(f"{name}_{side}", f"Eye_{side}", eu(q[0]), EYE_V + q[1], 0.020)
        q = lo[100]
        add(f"LidLower_{side}", f"Eye_{side}", eu(q[0]), EYE_V + q[1], 0.020)
        bc = bezier(BROW, 201)
        add(f"Brow_{side}", "FaceBase", eu(bc[100][0]), EYE_V + bc[100][1], 0.022)
        add(f"BrowInner_{side}", f"Brow_{side}", eu(bc[0][0]), EYE_V + bc[0][1], 0.022)
        add(f"BrowOuter_{side}", f"Brow_{side}", eu(bc[200][0]), EYE_V + bc[200][1], 0.022)
    add("Nose", "FaceBase", NOSE_U + 0.006, NOSE_V, 0.012)
    c0, _, _ = mouth_curves(np.array([0.0, 0.5, 1.0]))
    add("Mouth", "FaceBase", 0.0, MOUTH_V, 0.020)
    add("MouthCorner_L", "Mouth", -MOUTH_HALF_W, c0[2], 0.018)
    add("MouthCorner_R", "Mouth", MOUTH_HALF_W, c0[2], 0.018)
    add("LipUpper", "Mouth", 0.0, c0[0] + 0.004, 0.018)
    add("LipUpper_L", "LipUpper", -MOUTH_HALF_W / 2, c0[1] + 0.004, 0.018)
    add("LipUpper_R", "LipUpper", MOUTH_HALF_W / 2, c0[1] + 0.004, 0.018)
    add("LipLower", "Mouth", 0.0, c0[0] - 0.006, 0.018)
    add("LipLower_L", "LipLower", -MOUTH_HALF_W / 2, c0[1] - 0.006, 0.018)
    add("LipLower_R", "LipLower", MOUTH_HALF_W / 2, c0[1] - 0.006, 0.018)
    for side, sgn in (("L", -1.0), ("R", 1.0)):
        add(f"Blush_{side}", "FaceBase", sgn * BLUSH_U, BLUSH_V, 0.0)
    return B


def build():
    mb = MeshBuilder()
    build_shell(mb)
    for side in ("L", "R"):
        build_eye(mb, side)
        build_brow(mb, side)
        build_blush(mb, side)
    build_nose(mb)
    build_mouth(mb)
    out = mb.result()
    out["bones"] = bone_defs()
    return out


# ---------------------------------------------------------------------------
# Posing helpers (pure numpy linear-blend skinning, translations only)
# ---------------------------------------------------------------------------
def bone_side(name):
    if name.endswith("_L"):
        return -1.0
    if name.endswith("_R"):
        return 1.0
    return 0.0


def expand_pose(pose):
    """pose = {"sym": {base: (x,y,z)}, "bones": {name: (x,y,z)}} -> {bone: (x,y,z)}."""
    out = {}
    for base, val in pose.get("sym", {}).items():
        for side in ("L", "R"):
            out[f"{base}_{side}"] = tuple(val)
    for name, val in pose.get("bones", {}).items():
        out[name] = tuple(val)
    return out


def local_to_head(bone, val):
    """Face-space offset (x outward for sided bones / +u for centre bones, y up, z out of the face)."""
    T, U, N = frame(bone["frame_u"])
    sgn = bone_side(bone["name"]) or 1.0
    x, y, z = val
    return x * sgn * T + y * U + z * N


def bone_displacements(bones, offsets):
    """Total head-space displacement per bone, including inherited parent motion."""
    by_name = {b["name"]: b for b in bones}
    own = {b["name"]: (local_to_head(b, offsets[b["name"]]) if b["name"] in offsets else np.zeros(3)) for b in bones}
    total = {}
    for b in bones:  # parent-first order
        total[b["name"]] = own[b["name"]] + (total[b["parent"]] if b["parent"] else 0.0)
    unknown = set(offsets) - set(by_name)
    if unknown:
        raise KeyError(f"unknown bones in pose: {sorted(unknown)}")
    return total


def deform(model, offsets):
    D = bone_displacements(model["bones"], offsets)
    P = model["P"].copy()
    for i, w in enumerate(model["W"]):
        for b, x in w.items():
            P[i] += x * D[b]
    return P
