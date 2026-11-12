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
# Layout (design space)
# ---------------------------------------------------------------------------
EYE_U = 0.245
EYE_V = -0.090
SIDES = {"R": 1.0, "L": -1.0}        # R = +X (character right), L = -X


def _hermite(a, ta, b, tb, k=0.4):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ta = np.asarray(ta, float) / np.linalg.norm(ta)
    tb = np.asarray(tb, float) / np.linalg.norm(tb)
    L = k * np.linalg.norm(b - a)
    return [tuple(a), tuple(a + ta * L), tuple(b - tb * L), tuple(b)]


def _dir(deg):
    return (math.cos(math.radians(deg)), math.sin(math.radians(deg)))


# Eye-local coordinates: ex = outward (toward the ear), ey = up, origin = eye centre.
# Each lid is two cubic segments with explicit corner tangents. The sharp corners (about 53 deg
# outer, 68 deg inner) give the angular cel-anime eye and let the lids close cleanly.
EYE_INNER = (-0.132, -0.010)
EYE_OUTER = (0.135, 0.022)
EYE_TOP = (-0.020, 0.072)
EYE_BOTTOM = (0.010, -0.066)
EYE_UPPER = [_hermite(EYE_INNER, _dir(50), EYE_TOP, (1, 0)), _hermite(EYE_TOP, (1, 0), EYE_OUTER, _dir(-25))]
EYE_LOWER = [_hermite(EYE_OUTER, _dir(208), EYE_BOTTOM, (-1, 0)), _hermite(EYE_BOTTOM, (-1, 0), EYE_INNER, _dir(162))]
IRIS_C = (0.004, -0.006)
IRIS_R = (0.066, 0.078)
SCLERA_C, SCLERA_R, SCLERA_P = (0.0, 0.004), (0.165, 0.112), 2.6
SCLERA_UV = (0.17, 0.125)            # half extents mapped onto the sclera texture
RING_C, RING_R, RING_P = (0.0, 0.0), (0.225, 0.185), 2.4
RING_K = [0.0, 0.07, 0.16, 0.27, 0.40, 0.55, 0.70, 0.85, 1.0]
RING_FLAT_K = 0.60                    # ring stays fully raised up to this fraction

# Highlights relative to the iris centre, in screen-consistent u (not mirrored per eye)
HIGHLIGHTS = [
    # (du, dv), (rx, ry), rotation (deg)
    ((0.022, 0.028), (0.0205, 0.0145), 28.0),
    ((-0.026, -0.031), (0.0078, 0.0078), 0.0),
]

BROW = [(-0.118, 0.150), (-0.045, 0.176), (0.065, 0.184), (0.150, 0.158)]
NOSE_U, NOSE_V = 0.0, -0.212
BLUSH_U, BLUSH_V, BLUSH_SIZE = 0.268, -0.215, (0.150, 0.066)

# 2D mouth: flat images on patches that swap by sliding in and out of the head.
MOUTH_V = -0.305
MOUTH_UNIT = 0.12                     # studs per sprite unit (sprite x in [-1, 1], y in [-0.5, 0.5])
MOUTHS = ["Smile", "Neutral", "Frown", "Smirk", "OpenSmall", "Open", "Laugh", "Grin", "Teeth", "O", "Pout", "Wavy"]
DEFAULT_MOUTH = "Smile"

# Layer heights above the skin (studs)
H_SCLERA = 0.0012
H_IRIS = 0.0030
H_SHINE = 0.0048
H_RING = 0.0120
H_RING_RIM = -0.0015                  # the ring tucks under the skin at its edge: no exposed seam
H_WALL_BOTTOM = 0.0016
H_CREASE = 0.0138
H_LASH = 0.0146
H_BROW = 0.0146
H_NOSE = 0.0030
H_MOUTH = 0.0045
MOUTH_HIDE = 0.0300                   # inactive mouths sit this far inside the head
MOUTH_STAGGER = 0.00015               # so two mouths shown at once never z-fight
H_BLUSH_SHOWN = 0.0180
BLUSH_SHOW = 0.0300                   # the blush rests this far inside the head

# ---------------------------------------------------------------------------
# Texture atlas (pixel rects on a 1024 canvas, origin top-left)
# ---------------------------------------------------------------------------
ATLAS = 1024
RECT = {
    "iris": (0, 0, 256, 256),
    "sclera": (256, 0, 512, 128),
    "highlight": (256, 128, 320, 192),
    "skin": (320, 128, 384, 192),
    "lash": (384, 128, 448, 192),
    "brow": (448, 128, 512, 192),
    "crease": (256, 192, 384, 256),
    "wall": (384, 192, 512, 256),
    "blush": (512, 0, 768, 192),
    "nose": (768, 0, 832, 64),
    "noseshade": (832, 0, 896, 64),
}
for _i, _name in enumerate(MOUTHS):
    _c, _r = _i % 4, _i // 4
    RECT["mouth_" + _name] = (_c * 256, 256 + _r * 128, (_c + 1) * 256, 256 + (_r + 1) * 128)
UV_MARGIN = 6  # pixels kept clear inside every rect


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


def taper(n, stops):
    """Width profile along a stroke: stops = [(t, width), ...] for t in [0, 1]."""
    t = np.linspace(0.0, 1.0, n)
    return np.interp(t, [a for a, _ in stops], [b for _, b in stops])


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
    v_vals = sorted(set([round(-a, 6) for a in a_vals] + [round(a, 6) for a in a_vals]))
    rows = len(v_vals)
    cols = nt + 1
    u = np.linspace(-math.pi * R, math.pi * R, cols)        # seam at the back of the head
    uu, vv = np.meshgrid(u, np.array(v_vals))
    P, N = surf(uu.ravel(), vv.ravel(), 0.0)
    UV = rect_uv("skin", 0.15 + 0.7 * (uu.ravel() / (2 * math.pi * R) + 0.5),
                 0.15 + 0.7 * (1 - (vv.ravel() + V_MAX) / (2 * V_MAX)))
    W1 = {"FaceBase": 1.0}
    mb.add("shell", P, N, UV, [W1] * len(P), grid_faces(rows, cols))
    for sgn, row in ((-1, 0), (1, rows - 1)):
        ring = np.arange(row * cols, row * cols + cols)
        pp, pn = surf(np.array([0.0]), np.array([sgn * V_MAX]), 0.0)
        Pf = np.concatenate([P[ring], pp])
        Nf = np.concatenate([N[ring], pn])
        UVf = np.concatenate([UV[ring], rect_uv("skin", [0.5], [0.15 if sgn > 0 else 0.85])])
        mb.add("shell", Pf, Nf, UVf, [W1] * len(Pf), [[c, c + 1, cols] for c in range(cols - 1)])


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


def add_stroke(mb, part, side, cen, width, height, rect, weights, offset=None):
    """Flat ribbon of the given width along an eye-local centreline (solid swatch texture)."""
    n = left_normals(cen)
    off = np.zeros(len(cen)) if offset is None else offset
    a1 = cen - n * (width / 2 - off)[:, None]
    a2 = cen + n * (width / 2 + off)[:, None]
    allp = np.concatenate([a1, a2])
    P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], height)
    al = np.linspace(0.1, 0.9, len(cen))
    UV = np.concatenate([rect_uv(rect, al, 0.2), rect_uv(rect, al, 0.8)])
    mb.add(part, P, N, UV, list(weights) + list(weights), ribbon(a1, a2))


def build_eye(mb, side):
    pts, arc, s, p = eye_contour()
    n = len(pts)
    cw = [contour_weights(arc[i], s[i], side) for i in range(n)]
    eye = {f"Eye_{side}": 1.0}
    nseg = 72
    phi = np.linspace(0, 2 * np.pi, nseg, endpoint=False)

    # --- sclera (conformal, white with a cel lid shadow painted in)
    rings = [0.0, 0.3, 0.55, 0.75, 0.9, 1.0]
    flat = np.concatenate([np.array([SCLERA_C])] +
                          [superellipse(SCLERA_C, (SCLERA_R[0] * k, SCLERA_R[1] * k), SCLERA_P, phi) for k in rings[1:]])
    P, N = eye_uv_to_world(side, flat[:, 0], flat[:, 1], H_SCLERA)
    UV = rect_uv("sclera", 0.5 + 0.5 * flat[:, 0] / SCLERA_UV[0], 0.5 - 0.5 * flat[:, 1] / SCLERA_UV[1])
    mb.add(f"sclera_{side}", P, N, UV, [eye] * len(P), disc_faces(len(rings) - 1, nseg))

    # --- iris (flat disc in the eye's tangent plane)
    rings = [0.0, 0.18, 0.40, 0.62, 0.80, 0.92, 1.0]
    disc = np.concatenate([np.zeros((1, 2))] + [np.stack([np.cos(phi) * k, np.sin(phi) * k], -1) for k in rings[1:]])
    ex = IRIS_C[0] + disc[:, 0] * IRIS_R[0]
    ey = IRIS_C[1] + disc[:, 1] * IRIS_R[1]
    P, N = flat_to_world(side, ex, ey, H_IRIS)
    UV = rect_uv("iris", 0.5 + 0.5 * 0.97 * disc[:, 0], 0.5 - 0.5 * 0.97 * disc[:, 1])
    mb.add(f"iris_{side}", P, N, UV, [{f"Iris_{side}": 1.0}] * len(P), disc_faces(len(rings) - 1, nseg))

    # --- highlights (flat white shapes in front of the iris; screen-consistent placement)
    hp = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    for (du, dv), (rx, ry), rot in HIGHLIGHTS:
        a = math.radians(rot)
        lx, ly = np.cos(hp) * rx, np.sin(hp) * ry
        x = np.concatenate([[0.0], lx * math.cos(a) - ly * math.sin(a)])
        y = np.concatenate([[0.0], lx * math.sin(a) + ly * math.cos(a)])
        P, N = flat_to_world(side, np.full_like(x, IRIS_C[0]), IRIS_C[1] + dv + y, H_SHINE, du=du + x)
        UV = rect_uv("highlight", 0.5 + x / 0.1, 0.5 - y / 0.1)
        mb.add(f"shine_{side}", P, N, UV, [{f"Shine_{side}": 1.0}] * len(P), [[0, 1 + i, 1 + (i + 1) % 32] for i in range(32)])

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

    # --- wall: short skirt from the lid edge down to the sclera (upper part dark like the lashes).
    # Perpendicular to the skin, so it is emitted double-sided with explicit winding (separate
    # vertices per side: mesh tools drop faces that reuse the same vertex set). Authored normals
    # stay radial so it shades like the surrounding skin.
    P1, N1 = eye_uv_to_world(side, pts[:, 0], pts[:, 1], H_RING)
    P2, _ = eye_uv_to_world(side, pts[:, 0], pts[:, 1], H_WALL_BOTTOM)
    UV = np.concatenate([rect_uv("wall", p, 0.0), rect_uv("wall", p, 1.0)])
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    for fl in (faces, [f[::-1] for f in faces]):
        mb.add(f"wall_{side}", np.concatenate([P1, P2]), np.concatenate([N1, N1]), UV, cw + cw, fl, keep_winding=True)

    # --- upper lash line: heavy, thickest toward the outer corner
    up = bezier(EYE_UPPER, 81)
    su = np.linspace(0, 1, len(up))
    nrm = left_normals(up)
    width = np.interp(su, [0.0, 0.05, 0.22, 0.5, 0.8, 1.0], [0.0045, 0.0085, 0.0145, 0.0175, 0.0195, 0.0185])
    over = np.interp(su, [0.0, 0.1, 0.9, 1.0], [0.0010, 0.0022, 0.0022, 0.0014])
    inner = up - nrm * over[:, None]
    outer = up + nrm * width[:, None]
    allp = np.concatenate([inner, outer])
    P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_LASH)
    al = np.linspace(0.1, 0.9, len(up))
    UV = np.concatenate([rect_uv("lash", al, 0.2), rect_uv("lash", al, 0.8)])
    lw = [contour_weights(0, x, side) for x in su]
    mb.add(f"lash_{side}", P, N, UV, lw + lw, ribbon(inner, outer))

    # outer wing: continues the lid line, then flicks up and out to a point
    t_end = up[-1] - up[-3]
    t_end /= np.linalg.norm(t_end)
    base = up[-1] + nrm[-1] * (width[-1] - over[-1]) / 2
    wing = bezier([base, base + t_end * 0.018, base + np.array([0.045, 0.002]), base + np.array([0.064, 0.020])], 19)
    ww = taper(len(wing), [(0.0, width[-1] + over[-1]), (0.45, 0.0115), (1.0, 0.0006)])
    add_stroke(mb, f"lash_{side}", side, wing, ww, H_LASH + 0.0001, "lash", [eye] * len(wing))

    # inner hook: small point at the inner corner
    i0 = up[1]
    hook = bezier([i0, i0 + np.array([-0.006, -0.004]), i0 + np.array([-0.010, -0.010]), i0 + np.array([-0.012, -0.017])], 9)
    add_stroke(mb, f"lash_{side}", side, hook, taper(9, [(0.0, 0.0050), (1.0, 0.0005)]), H_LASH,
               "lash", [contour_weights(0, 0.0, side)] * 9)

    # --- lower lash: a thin line from the outer corner plus a short separate dash
    lo = bezier(EYE_LOWER, 81)
    sl = np.linspace(0, 1, len(lo))
    for s0, s1, prof in ((0.0, 0.44, [(0.0, 0.0045), (0.15, 0.0055), (0.7, 0.0035), (1.0, 0.0005)]),
                         (0.52, 0.72, [(0.0, 0.0005), (0.5, 0.0030), (1.0, 0.0005)])):
        keep = (sl >= s0) & (sl <= s1)
        seg, ss = lo[keep], sl[keep]
        wseg = taper(len(seg), prof)
        nl = left_normals(seg)
        a1 = seg - nl * 0.0009
        a2 = seg + nl * wseg[:, None]
        allp = np.concatenate([a1, a2])
        P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_LASH)
        al = np.linspace(0.1, 0.9, len(seg))
        UV = np.concatenate([rect_uv("lash", al, 0.2), rect_uv("lash", al, 0.8)])
        w = [contour_weights(1, x, side) for x in ss]
        mb.add(f"lashlow_{side}", P, N, UV, w + w, ribbon(a1, a2))

    # --- eyelid crease: thin crisp line that partly follows the lid
    cs = np.linspace(0.30, 0.90, 31)
    upd = bezier(EYE_UPPER, 201)
    idx = np.round(cs * 200).astype(int)
    cen = upd[idx] + left_normals(upd)[idx] * np.interp(cs, [0.30, 0.60, 0.90], [0.022, 0.026, 0.020])[:, None]
    cwid = np.interp(cs, [0.30, 0.40, 0.80, 0.90], [0.0005, 0.0030, 0.0028, 0.0005])
    w = [mix_weights(contour_weights(0, x, side), eye, 0.62) for x in cs]
    add_stroke(mb, f"crease_{side}", side, cen, cwid, H_CREASE, "crease", w)


def build_brow(mb, side):
    cen = bezier(BROW, 41)
    s = np.linspace(0, 1, len(cen))
    n = left_normals(cen)
    w = np.interp(s, [0.0, 0.08, 0.40, 0.80, 1.0], [0.0160, 0.0200, 0.0170, 0.0100, 0.0020])
    a1 = cen - n * (w / 2)[:, None]
    a2 = cen + n * (w / 2)[:, None]
    a1[0] = a1[0] + (cen[2] - cen[0]) * 0.8          # angled inner cut
    allp = np.concatenate([a1, a2])
    P, N = eye_uv_to_world(side, allp[:, 0], allp[:, 1], H_BROW)
    al = np.linspace(0.1, 0.9, len(cen))
    UV = np.concatenate([rect_uv("brow", al, 0.2), rect_uv("brow", al, 0.8)])
    bw = [sided(ctrl_weights(x, BROW_CTRL), side) for x in s]
    mb.add(f"brow_{side}", P, N, UV, bw + bw, ribbon(a1, a2))


def build_nose(mb):
    """Small slanted line plus a hard-edged cel shadow triangle."""
    cen = bezier([(0.010, 0.022), (0.012, 0.009), (0.008, -0.002), (-0.006, -0.005)], 13)
    cen = cen + np.array([NOSE_U, NOSE_V])
    s = np.linspace(0, 1, len(cen))
    n = left_normals(cen)
    w = np.interp(s, [0, 0.35, 0.8, 1], [0.0006, 0.0036, 0.0032, 0.0006])
    a1 = cen - n * w[:, None] / 2
    a2 = cen + n * w[:, None] / 2
    allp = np.concatenate([a1, a2])
    P, N = surf(allp[:, 0], allp[:, 1], H_NOSE)
    al = np.linspace(0.1, 0.9, len(cen))
    UV = np.concatenate([rect_uv("nose", al, 0.2), rect_uv("nose", al, 0.8)])
    mb.add("nose", P, N, UV, [{"Nose": 1.0}] * len(allp), ribbon(a1, a2))
    tri = np.array([(0.011, 0.020), (0.026, -0.004), (0.008, -0.004)]) + np.array([NOSE_U, NOSE_V])
    P, N = surf(tri[:, 0], tri[:, 1], H_NOSE - 0.0008)
    mb.add("nose", P, N, rect_uv("noseshade", [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]), [{"Nose": 1.0}] * 3, [[0, 1, 2]])


def build_blush(mb, side):
    """Built at its shown shape, then stored inside the head along its bone's normal."""
    sgn = SIDES[side]
    gx, gy = np.meshgrid(np.linspace(-1, 1, 15), np.linspace(-1, 1, 7))
    pu = sgn * BLUSH_U + gx.ravel() * BLUSH_SIZE[0] / 2
    pv = BLUSH_V + gy.ravel() * BLUSH_SIZE[1] / 2
    P, N = surf(pu, pv, H_BLUSH_SHOWN)
    P = P - frame(sgn * BLUSH_U)[2] * BLUSH_SHOW
    UV = rect_uv("blush", (gx.ravel() + 1) / 2, (1 - gy.ravel()) / 2)
    mb.add(f"blush_{side}", P, N, UV, [{f"Blush_{side}": 1.0}] * len(pu), grid_faces(7, 15))


def mouth_patch(name, k):
    """Flat 2D mouth image on a patch conformal to the head.

    Sprite x runs toward the viewer's right (the character's left) so the images read
    unmirrored from the front. Only the default mouth rests on the skin; the others are stored
    MOUTH_HIDE inside the head and slide straight out along the mouth bone's normal.
    """
    xs, ys = np.linspace(-1, 1, 13), np.linspace(-0.5, 0.5, 7)
    gx, gy = np.meshgrid(xs, ys)
    u = -gx.ravel() * MOUTH_UNIT
    v = MOUTH_V + gy.ravel() * MOUTH_UNIT
    P, N = surf(u, v, H_MOUTH + MOUTH_STAGGER * k)
    if name != DEFAULT_MOUTH:
        P = P - frame(0.0)[2] * MOUTH_HIDE
    UV = rect_uv("mouth_" + name, (gx.ravel() + 1) / 2, 0.5 - gy.ravel())
    return P, N, UV, grid_faces(len(ys), len(xs))


def build_mouth(mb):
    for k, name in enumerate(MOUTHS):
        P, N, UV, faces = mouth_patch(name, k)
        mb.add(f"mouth_{name}", P, N, UV, [{f"Mouth_{name}": 1.0}] * len(P), faces)


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
    up = bezier(EYE_UPPER, 201)
    lo = bezier(EYE_LOWER, 201)
    bc = bezier(BROW, 201)
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
        add(f"Brow_{side}", "FaceBase", eu(bc[100][0]), EYE_V + bc[100][1], 0.022)
        add(f"BrowInner_{side}", f"Brow_{side}", eu(bc[0][0]), EYE_V + bc[0][1], 0.022)
        add(f"BrowOuter_{side}", f"Brow_{side}", eu(bc[200][0]), EYE_V + bc[200][1], 0.022)
    add("Nose", "FaceBase", NOSE_U + 0.006, NOSE_V, 0.012)
    add("Mouth", "FaceBase", 0.0, MOUTH_V, 0.020)
    for name in MOUTHS:
        add(f"Mouth_{name}", "Mouth", 0.0, MOUTH_V, 0.024)
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


def mouth_show_hide(name):
    """Outward offsets (studs) of a mouth bone when its image is shown / hidden."""
    return (0.0, -MOUTH_HIDE) if name == DEFAULT_MOUTH else (MOUTH_HIDE, 0.0)


def mouth_offsets(mouth):
    if mouth not in MOUTHS:
        raise KeyError(f"unknown mouth {mouth!r}")
    out = {}
    for name in MOUTHS:
        show, hide = mouth_show_hide(name)
        z = show if name == mouth else hide
        if z:
            out[f"Mouth_{name}"] = (0.0, 0.0, z)
    return out


def expand_pose(pose):
    """pose = {"sym": {base: (x,y,z)}, "bones": {name: (x,y,z)}, "mouth": name} -> {bone: (x,y,z)}."""
    out = {}
    for base, val in pose.get("sym", {}).items():
        for side in ("L", "R"):
            out[f"{base}_{side}"] = tuple(val)
    for name, val in pose.get("bones", {}).items():
        out[name] = tuple(val)
    out.update(mouth_offsets(pose.get("mouth", DEFAULT_MOUTH)))
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
    unknown = set(offsets) - set(by_name)
    if unknown:
        raise KeyError(f"unknown bones in pose: {sorted(unknown)}")
    own = {b["name"]: (local_to_head(b, offsets[b["name"]]) if b["name"] in offsets else np.zeros(3)) for b in bones}
    total = {}
    for b in bones:  # parent-first order
        total[b["name"]] = own[b["name"]] + (total[b["parent"]] if b["parent"] else 0.0)
    return total


def deform(model, offsets):
    D = bone_displacements(model["bones"], offsets)
    P = model["P"].copy()
    for i, w in enumerate(model["W"]):
        for b, x in w.items():
            P[i] += x * D[b]
    return P
