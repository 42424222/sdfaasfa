"""
AnimeFace R6 - shared design data and procedural geometry.

Everything here is in Roblox head space, in studs:
  +X = character's right, +Y = up, +Z = back of the head (the face looks toward -Z),
  origin = centre of the R6 head.

Design space used for placing features on the head surface:
  u = horizontal arc length around the head (u > 0 is the character's right side)
  v = arc length along the head profile from the equator (v > 0 is up)

Construction (follows the supplied example face):
  * each eye is a real opening in the head: a socket drops 0.045 studs into the head and the eye
    white sits at its bottom, with the iris on it and the highlights floating above;
  * the skin around each opening is a deformable patch stitched into the head shell, so the lids
    can close over the socket for blinks;
  * lashes, lower lashes, lid lines and brows are flat plates of even thickness with straight
    walls, sitting on the skin; the upper lash plate overhangs the top of the opening;
  * mouths are flat 2D images.

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
# Layout (design space). Eye placement and opening size follow the example face.
# ---------------------------------------------------------------------------
EYE_U = 0.320
EYE_V = -0.190
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
# A wide lens-shaped opening (0.39 x 0.125) with blunt, rounded ends; the upper lash plate
# overhangs its top edge, which gives the calm, flat-topped look.
EYE_INNER = (-0.194, 0.000)
EYE_OUTER = (0.194, -0.010)
EYE_TOP = (-0.030, 0.060)
EYE_BOTTOM = (0.070, -0.063)
EYE_UPPER = [_hermite(EYE_INNER, _dir(72), EYE_TOP, (1, 0), 0.50), _hermite(EYE_TOP, (1, 0), EYE_OUTER, _dir(-62), 0.50)]
EYE_LOWER = [_hermite(EYE_OUTER, _dir(242), EYE_BOTTOM, (-1, 0), 0.50), _hermite(EYE_BOTTOM, (-1, 0), EYE_INNER, _dir(110), 0.50)]

SOCKET_DEPTH = 0.045                  # eye white sits this far below the skin
IRIS_C = (-0.004, -0.006)
IRIS_R = (0.050, 0.053)               # smaller than the opening: white shows all round it
H_IRIS = 0.0012                       # iris above the eye white
H_SHINE = 0.0220                      # highlights float this far above the eye white
SCLERA_UV = (0.215, 0.110)            # half extents mapped onto the sclera texture

# Highlights relative to the iris centre, in head-space u (same screen side on both eyes)
HIGHLIGHTS = [
    # (du, dv), (rx, ry), rotation (deg)
    ((0.018, 0.022), (0.0150, 0.0105), 18.0),
    ((-0.019, -0.024), (0.0058, 0.0058), 0.0),
]

BROW = [(-0.205, 0.168), (-0.080, 0.204), (0.080, 0.211), (0.235, 0.180)]
BLUSH_U, BLUSH_V, BLUSH_SIZE = 0.330, -0.315, (0.170, 0.066)

# 2D mouth: flat images on patches that swap by sliding in and out of the head. It sits low on
# the face, on the head's rounded lower edge, like the reference faces.
MOUTH_V = -0.400
MOUTH_UNIT = 0.19                     # studs per sprite unit (sprite x in [-1, 1], y in [-0.5, 0.5])
MOUTHS = ["Neutral", "Smile", "Frown", "Smirk", "OpenSmall", "Open", "Laugh", "Grin", "Teeth", "O", "Pout",
          "Cat", "Wavy"]
DEFAULT_MOUTH = "Neutral"

# Flat plate heights above the skin (studs)
H_LASH = 0.0095                       # upper lash plate and its spikes
LASH_WALL_IN = -0.0140                # the lash's overhanging edge drops into the socket this far
H_LOWER = 0.0045                      # lower lash line and tiles
H_LINE = 0.0040                       # crease and pale lid line
H_BROW = 0.0065
PLATE_BASE = -0.0010                  # plate walls sink slightly into the skin
H_MOUTH = 0.0045
MOUTH_HIDE = 0.0300                   # inactive mouths sit this far inside the head
MOUTH_STAGGER = 0.00015               # so two mouths shown at once never z-fight
H_BLUSH_SHOWN = 0.0180
BLUSH_SHOW = 0.0300                   # the blush rests this far inside the head
IRIS_RADIUS = R - SOCKET_DEPTH + H_IRIS   # look = rotating the iris around the head axis at this radius

# ---------------------------------------------------------------------------
# Texture atlas (pixel rects on a 1024 canvas, origin top-left)
# ---------------------------------------------------------------------------
ATLAS = 1024
RECT = {
    "iris": (0, 0, 512, 512),
    "sclera": (512, 0, 1024, 256),
    "wall": (512, 256, 1024, 320),
    "highlight": (512, 320, 576, 384),
    "skin": (576, 320, 640, 384),
    "lash": (640, 320, 704, 384),
    "brow": (704, 320, 768, 384),
    "crease": (768, 320, 832, 384),
    "lidline": (832, 320, 896, 384),
    "lowerlash": (896, 320, 960, 384),
    "blush": (512, 384, 768, 512),
}
for _i, _name in enumerate(MOUTHS):
    _c, _r = _i % 4, _i // 4
    RECT["mouth_" + _name] = (_c * 256, 512 + _r * 128, (_c + 1) * 256, 512 + (_r + 1) * 128)
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
    th = np.asarray(u, float) / R
    T = np.stack([np.cos(th), np.zeros_like(th), np.sin(th)], -1)
    N = np.stack([np.sin(th), np.zeros_like(th), -np.cos(th)], -1)
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
    """Profile along a stroke: stops = [(t, value), ...] for t in [0, 1]."""
    t = np.linspace(0.0, 1.0, n)
    return np.interp(t, [a for a, _ in stops], [b for _, b in stops])


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


def inside_polygon(pts, poly):
    """Even-odd point-in-polygon test for many 2D points."""
    pts = np.atleast_2d(pts)
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), bool)
    for (ax, ay), (bx, by) in zip(poly, np.roll(poly, -1, axis=0)):
        cond = (ay > y) != (by > y)
        xint = ax + (y - ay) * (bx - ax) / np.where(np.abs(by - ay) < 1e-12, 1e-12, by - ay)
        inside ^= cond & (x < xint)
    return inside


# ---------------------------------------------------------------------------
# Eye contour (shared by geometry, rig and preset solving)
# ---------------------------------------------------------------------------
N_UPPER = 53
N_LOWER = 39


def eye_contour():
    """Opening contour as a closed loop (clockwise in eye-local coordinates).

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


def closed_normals(pts):
    """Outward normals of a closed clockwise loop."""
    t = np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    return np.stack([-t[:, 1], t[:, 0]], -1)


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
        UV = np.broadcast_to(np.asarray(UV, float), (len(P), 2)) if np.ndim(UV) == 1 else np.asarray(UV, float).reshape(-1, 2)
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


def stitch(a_ang, b_ang):
    """Triangles joining two closed loops sorted by clockwise angle (indices: A = 0..na-1,
    B = na..na+nb-1). Walks both loops together, always advancing the one that lags."""
    na, nb = len(a_ang), len(b_ang)
    faces, i, j = [], 0, 0
    while i < na or j < nb:
        an = a_ang[i + 1] if i + 1 < na else a_ang[0] + 2 * np.pi
        bn = b_ang[j + 1] if j + 1 < nb else b_ang[0] + 2 * np.pi
        if j >= nb or (i < na and an <= bn):
            faces.append([i % na, na + j % nb, (i + 1) % na])
            i += 1
        else:
            faces.append([i % na, na + j % nb, na + (j + 1) % nb])
            j += 1
    return faces


# ---------------------------------------------------------------------------
# Head shell, with a rectangular block of cells cut out around each eye. The block is
# replaced by the deformable lid patch built in build_eye (its outer edge reuses the
# block's grid vertices exactly, so the surface stays watertight).
# ---------------------------------------------------------------------------
SHELL_COLS = 72
SHELL_U = np.linspace(-math.pi * R, math.pi * R, SHELL_COLS + 1)     # seam at the back of the head


def _shell_rows():
    band = [YC * k / 6 for k in range(7)]
    a_vals = band + [YC + ARC * k / 8 for k in range(1, 9)] + [YC + ARC + d for d in (0.100, 0.200)]
    return np.array(sorted(set([round(-a, 6) for a in a_vals] + [round(a, 6) for a in a_vals])))


SHELL_V = _shell_rows()
_C0 = int(np.argmin(np.abs(SHELL_U - 0.0525)))
_C1 = int(np.argmin(np.abs(SHELL_U - 0.5779)))
_R0 = int(np.argmin(np.abs(SHELL_V + YC)))
_R1 = int(np.argmin(np.abs(SHELL_V + YC / 6)))
BLOCKS = {"R": (_C0, _C1, _R0, _R1), "L": (SHELL_COLS - _C1, SHELL_COLS - _C0, _R0, _R1)}


def block_loop(side):
    """Grid vertices (column, row) around an eye block, in a closed loop."""
    c0, c1, r0, r1 = BLOCKS[side]
    loop = [(c, r0) for c in range(c0, c1)] + [(c1, r) for r in range(r0, r1)]
    loop += [(c, r1) for c in range(c1, c0, -1)] + [(c0, r) for r in range(r1, r0, -1)]
    return loop


def build_shell(mb):
    rows, cols = len(SHELL_V), SHELL_COLS + 1
    uu, vv = np.meshgrid(SHELL_U, SHELL_V)
    P, N = surf(uu.ravel(), vv.ravel(), 0.0)
    UV = rect_uv("skin", 0.15 + 0.7 * (uu.ravel() / (2 * math.pi * R) + 0.5),
                 0.15 + 0.7 * (1 - (vv.ravel() + V_MAX) / (2 * V_MAX)))
    W1 = {"FaceBase": 1.0}
    faces = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            if any(c0 <= c < c1 and r0 <= r < r1 for c0, c1, r0, r1 in BLOCKS.values()):
                continue
            faces.append([r * cols + c, r * cols + c + 1, (r + 1) * cols + c + 1, (r + 1) * cols + c])
    mb.add("shell", P, N, UV, [W1] * len(P), faces)
    for sgn, row in ((-1, 0), (1, rows - 1)):
        ring = np.arange(row * cols, row * cols + cols)
        pp, pn = surf(np.array([0.0]), np.array([sgn * V_MAX]), 0.0)
        Pf = np.concatenate([P[ring], pp])
        Nf = np.concatenate([N[ring], pn])
        UVf = np.concatenate([UV[ring], rect_uv("skin", [0.5], [0.15 if sgn > 0 else 0.85])])
        mb.add("shell", Pf, Nf, UVf, [W1] * len(Pf), [[c, c + 1, cols] for c in range(cols - 1)])


# ---------------------------------------------------------------------------
# Eye
# ---------------------------------------------------------------------------
def eye_uv_to_world(side, ex, ey, d):
    u = EYE_U * SIDES[side] + SIDES[side] * np.asarray(ex, float)
    v = EYE_V + np.asarray(ey, float)
    return surf(u, v, d)


def iris_point(side, du, dv, d):
    """Point relative to the iris centre, offset in head-space u (not mirrored per eye)."""
    u = SIDES[side] * (EYE_U + IRIS_C[0]) + np.asarray(du, float)
    v = EYE_V + IRIS_C[1] + np.asarray(dv, float)
    return surf(u, v, d)


def eye_dir3(side, d2, u):
    """3D direction of an eye-local 2D direction at head-space u."""
    T, Up, _ = frame(u)
    d2 = np.asarray(d2, float)
    v = SIDES[side] * d2[..., 0:1] * T + d2[..., 1:2] * Up
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def add_plate(mb, part, side, lower, upper, h_top, base_lower, base_upper, weights, rect):
    """Flat plate of even thickness between two eye-local edge polylines of equal length.

    The top face sits at h_top over the skin everywhere (flat like a paper cut-out), and
    straight walls drop from each edge to base_lower / base_upper; walls and top use separate
    vertices so the edges stay crisp.
    """
    lower, upper = np.asarray(lower, float), np.asarray(upper, float)
    n = len(lower)
    h_top = np.broadcast_to(np.asarray(h_top, float), (n,))
    base_lower = np.broadcast_to(np.asarray(base_lower, float), (n,))
    base_upper = np.broadcast_to(np.asarray(base_upper, float), (n,))
    uv = rect_uv(rect, 0.5, 0.5)
    W = list(weights)
    quads = [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)]
    Pl, Nl = eye_uv_to_world(side, lower[:, 0], lower[:, 1], h_top)
    Pu, Nu = eye_uv_to_world(side, upper[:, 0], upper[:, 1], h_top)
    mb.add(part, np.concatenate([Pl, Pu]), np.concatenate([Nl, Nu]), uv, W + W, quads)
    across = lower - upper
    across /= np.maximum(np.linalg.norm(across, axis=1, keepdims=True), 1e-9)
    ul = SIDES[side] * (EYE_U + lower[:, 0])
    uu = SIDES[side] * (EYE_U + upper[:, 0])
    Al = eye_dir3(side, across, ul)
    Au = eye_dir3(side, -across, uu)
    Plb, _ = eye_uv_to_world(side, lower[:, 0], lower[:, 1], base_lower)
    Pub, _ = eye_uv_to_world(side, upper[:, 0], upper[:, 1], base_upper)
    mb.add(part, np.concatenate([Pl, Plb]), np.concatenate([Al, Al]), uv, W + W, quads)
    mb.add(part, np.concatenate([Pu, Pub]), np.concatenate([Au, Au]), uv, W + W, quads)
    for i, sgn in ((0, -1.0), (n - 1, 1.0)):
        mid = (lower[i] + upper[i]) / 2
        nxt = (lower[min(i + 1, n - 1)] + upper[min(i + 1, n - 1)]) / 2 - (lower[max(i - 1, 0)] + upper[max(i - 1, 0)]) / 2
        t3 = eye_dir3(side, nxt / max(np.linalg.norm(nxt), 1e-9), SIDES[side] * (EYE_U + mid[0]))
        cap = np.stack([Pl[i], Pu[i], Pub[i], Plb[i]])
        mb.add(part, cap, np.broadcast_to(sgn * t3, (4, 3)), uv, [W[i]] * 4, [[0, 1, 2, 3]])


def strip(center, width):
    """Lower/upper edges of a strip of the given width around a centreline."""
    nrm = left_normals(center)
    return center - nrm * (width / 2)[:, None], center + nrm * (width / 2)[:, None]


def build_eye(mb, side):
    sgn = SIDES[side]
    pts, arc, s, p = eye_contour()
    n = len(pts)
    cw = [contour_weights(arc[i], s[i], side) for i in range(n)]
    eye = {f"Eye_{side}": 1.0}
    base = {"FaceBase": 1.0}
    nout = closed_normals(pts)

    # --- lid patch: skin from the opening out to the block cut from the shell. Its inner edge
    # follows the lid bones (blinks stretch it over the socket); its outer edge is the block's
    # own grid vertices (FaceBase only), so it joins the shell without a seam.
    centre = np.array([0.02, 0.0])
    loop = block_loop(side)
    lu = np.array([SHELL_U[c] for c, _ in loop])
    lv = np.array([SHELL_V[r] for _, r in loop])
    LB = np.stack([sgn * lu - EYE_U, lv - EYE_V], -1)            # block loop in eye-local coords

    def cw_angle(q):
        return np.mod(np.pi - np.arctan2(q[:, 1] - centre[1], q[:, 0] - centre[0]), 2 * np.pi)

    def ray_hit(theta):
        """Point of the block polygon in direction theta from the centre."""
        d = np.array([math.cos(theta), math.sin(theta)])
        best = None
        for a, b in zip(LB, np.roll(LB, -1, axis=0)):
            e = b - a
            m = np.array([[d[0], -e[0]], [d[1], -e[1]]])
            if abs(np.linalg.det(m)) < 1e-12:
                continue
            t, k = np.linalg.solve(m, a - centre)
            if t > 0 and -1e-9 <= k <= 1 + 1e-9 and (best is None or t < best):
                best = t
        return centre + d * best

    theta = np.arctan2(pts[:, 1] - centre[1], pts[:, 0] - centre[0])
    proj = np.array([ray_hit(t) for t in theta])
    ks = [0.0, 0.12, 0.28, 0.48, 0.70]
    rows_p, rows_w = [], []
    for k in ks:
        rows_p.append(pts + (proj - pts) * k)
        f = 1.0 - (1.0 - k) ** 1.6
        rows_w.extend(mix_weights(cw[i], base, f) for i in range(n))
    rp = np.concatenate(rows_p)
    P, N = eye_uv_to_world(side, rp[:, 0], rp[:, 1], 0.0)
    skin_uv = rect_uv("skin", 0.5, 0.5)
    mb.add(f"lid_{side}", P, N, skin_uv, rows_w, grid_faces(len(ks), n, wrap=True))
    # stitch the outer row (n points) to the block's grid vertices (exact shell positions)
    A = rows_p[-1]
    a_ang, b_ang = cw_angle(A), cw_angle(LB)
    ia, ib = np.argsort(a_ang), np.argsort(b_ang)
    PA, NA = eye_uv_to_world(side, A[ia, 0], A[ia, 1], 0.0)
    PB, NB = surf(lu[ib], lv[ib], 0.0)
    WA = [rows_w[(len(ks) - 1) * n + i] for i in ia]
    mb.add(f"lid_{side}", np.concatenate([PA, PB]), np.concatenate([NA, NB]), skin_uv,
           WA + [base] * len(ib), stitch(a_ang[ia], b_ang[ib]))

    # --- socket: walls from the opening down to the eye white. Undercut slightly along the top
    # and bottom (hidden from the front); at the inner corner the wall slopes in, so the inner
    # corner reads as a deep, shaded recess.
    off = 0.006 - 0.030 * smoothstep((-0.115 - pts[:, 0]) / 0.075)
    depth = [0.0, 0.40, 1.0]
    wall_p, wall_h, wall_w = [], [], []
    for f in depth:
        wall_p.append(pts + nout * (off * f ** 0.7)[:, None])
        wall_h.append(np.full(n, -SOCKET_DEPTH * f))
        wall_w.extend(mix_weights(cw[i], eye, f) for i in range(n))
    wp = np.concatenate(wall_p)
    P, _ = eye_uv_to_world(side, wp[:, 0], wp[:, 1], np.concatenate(wall_h))
    P3 = P.reshape(len(depth), n, 3)
    tang = np.roll(P3, -1, axis=1) - np.roll(P3, 1, axis=1)
    down = np.gradient(P3, axis=0)
    N = np.cross(tang, down)
    uw = sgn * (EYE_U + wp.reshape(len(depth), n, 2)[..., 0])
    inward = eye_dir3(side, -np.broadcast_to(nout, (len(depth), n, 2)), uw)
    N = np.where((np.sum(N * inward, -1) < 0)[..., None], -N, N)
    UV = np.concatenate([rect_uv("wall", p, f) for f in depth])
    mb.add(f"socket_{side}", P, N.reshape(-1, 3), UV, wall_w, grid_faces(len(depth), n, wrap=True))

    # --- eye white: the floor of the socket (its rim is the bottom row of the wall)
    floor = wall_p[-1]
    c = np.array(IRIS_C)
    rings = [0.30, 0.55, 0.75, 0.90, 1.0]
    flat = np.concatenate([c[None]] + [c + (floor - c) * f for f in rings])
    P, N = eye_uv_to_world(side, flat[:, 0], flat[:, 1], -SOCKET_DEPTH)
    UV = rect_uv("sclera", 0.5 + 0.5 * flat[:, 0] / SCLERA_UV[0], 0.5 - 0.5 * flat[:, 1] / SCLERA_UV[1])
    mb.add(f"sclera_{side}", P, N, UV, [eye] * len(P), disc_faces(len(rings), n))

    # --- iris on the eye white: looking around rotates it about the head axis, so it slides
    # across the eye white and under the socket walls
    nseg = 48
    phi = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    rings = [0.0, 0.25, 0.55, 0.80, 0.93, 1.0]
    disc = np.concatenate([np.zeros((1, 2))] + [np.stack([np.cos(phi) * k, np.sin(phi) * k], -1) for k in rings[1:]])
    P, N = iris_point(side, disc[:, 0] * IRIS_R[0], disc[:, 1] * IRIS_R[1], -SOCKET_DEPTH + H_IRIS)
    UV = rect_uv("iris", 0.5 + 0.5 * 0.97 * disc[:, 0], 0.5 - 0.5 * 0.97 * disc[:, 1])
    mb.add(f"iris_{side}", P, N, UV, [{f"Iris_{side}": 1.0}] * len(P), disc_faces(len(rings) - 1, nseg))

    # --- highlights: white shapes floating inside the socket, in front of the iris (parallax)
    hp = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    for (du, dv), (rx, ry), rot in HIGHLIGHTS:
        a = math.radians(rot)
        lx, ly = np.cos(hp) * rx, np.sin(hp) * ry
        x = np.concatenate([[0.0], lx * math.cos(a) - ly * math.sin(a)])
        y = np.concatenate([[0.0], lx * math.sin(a) + ly * math.cos(a)])
        P, N = iris_point(side, du + x, dv + y, -SOCKET_DEPTH + H_SHINE)
        mb.add(f"shine_{side}", P, N, rect_uv("highlight", 0.5, 0.5), [{f"Shine_{side}": 1.0}] * len(P),
               [[0, 1 + i, 1 + (i + 1) % 24] for i in range(24)])

    # --- upper lash plate: overhangs the top of the opening, heaviest over the outer half, and
    # runs out past the outer corner into a pointed wing
    up = bezier(EYE_UPPER, 201)
    su = np.linspace(0, 1, 201)
    nup = left_normals(up)
    sl = np.linspace(0.025, 0.975, 70)
    il = np.round(sl * 200).astype(int)
    ov = np.interp(sl, [0.025, 0.15, 0.5, 0.85, 0.975], [0.002, 0.008, 0.013, 0.012, 0.004])
    lower_c = up[il] - nup[il] * ov[:, None]
    wing_tip = np.array([0.280, -0.014])
    t_low = (lower_c[-1] - lower_c[-3]) / np.linalg.norm(lower_c[-1] - lower_c[-3])
    lower_w = bezier([lower_c[-1], lower_c[-1] + t_low * 0.012, wing_tip + np.array([-0.045, -0.002]), wing_tip], 22)[1:]
    su_up = np.linspace(0.025, 0.80, 56)
    iu = np.round(su_up * 200).astype(int)
    wid = np.interp(su_up, [0.025, 0.10, 0.35, 0.60, 0.80], [0.002, 0.010, 0.021, 0.028, 0.031])
    upper_c = up[iu] + nup[iu] * wid[:, None]
    t_up = (upper_c[-1] - upper_c[-3]) / np.linalg.norm(upper_c[-1] - upper_c[-3])
    upper_w = bezier([upper_c[-1], upper_c[-1] + t_up * 0.030, wing_tip + np.array([-0.040, 0.012]), wing_tip], 36)[1:]
    lower_e = resample(np.concatenate([lower_c, lower_w]), 96)
    upper_e = resample(np.concatenate([upper_c, upper_w]), 96)
    upper_e[-1] = upper_e[-1] + np.array([0.0, 0.0012])        # a hair-thin tip, never a zero-area cap
    poly = pts
    base_l = np.where(inside_polygon(lower_e, poly), LASH_WALL_IN, PLATE_BASE)
    # weights follow the lid along the contour part and blend into the eye along the wing
    l1 = np.linalg.norm(np.diff(lower_c, axis=0), axis=1).sum()
    l2 = np.linalg.norm(np.diff(np.concatenate([lower_c[-1:], lower_w]), axis=0), axis=1).sum()
    s_of = np.interp(np.linspace(0, 1, 96), [0.0, l1 / (l1 + l2), 1.0], [0.025, 0.975, 1.0])
    lw = [contour_weights(0, x, side) for x in s_of]
    add_plate(mb, f"lash_{side}", side, lower_e, upper_e, H_LASH, base_l, PLATE_BASE, lw, "lash")

    # two flat lash spikes growing out of the plate's outer half, pointing up and out
    for s_root, tip_off, w0 in ((0.62, np.array([0.030, 0.036]), 0.0105), (0.78, np.array([0.044, 0.026]), 0.0120)):
        i = int(round(s_root * 200))
        root = up[i] + nup[i] * (0.55 * np.interp(s_root, su_up, wid))
        tip = root + tip_off
        cen = bezier([root, root + nup[i] * 0.010, tip - tip_off * 0.35 + np.array([0.004, -0.002]), tip], 10)
        lo_e, up_e = strip(cen, taper(10, [(0, w0), (1, 0.0008)]))
        add_plate(mb, f"lash_{side}", side, lo_e, up_e, H_LASH, PLATE_BASE, PLATE_BASE,
                  [contour_weights(0, s_root, side)] * 10, "lash")

    # --- lower lashes: a thin line along the outer half of the lower lid, a small spike at the
    # outer corner, and two short tiles below (like the example's lower lash pieces)
    lo = bezier(EYE_LOWER, 201)
    nlo = left_normals(lo)
    sl2 = np.linspace(0.04, 0.46, 30)
    il2 = np.round(sl2 * 200).astype(int)
    gap, wl = 0.0035, taper(30, [(0, 0.0012), (0.12, 0.0042), (0.75, 0.0036), (1, 0.0008)])
    add_plate(mb, f"lashlow_{side}", side, lo[il2] + nlo[il2] * gap, lo[il2] + nlo[il2] * (gap + wl)[:, None],
              H_LOWER, PLATE_BASE, PLATE_BASE, [contour_weights(1, x, side) for x in sl2], "lowerlash")
    i = int(0.06 * 200)
    root = lo[i] + nlo[i] * 0.004
    cen = bezier([root, root + np.array([0.008, -0.004]), root + np.array([0.020, -0.012]), root + np.array([0.026, -0.020])], 8)
    lo_e, up_e = strip(cen, taper(8, [(0, 0.0055), (1, 0.0008)]))
    add_plate(mb, f"lashlow_{side}", side, lo_e, up_e, H_LOWER, PLATE_BASE, PLATE_BASE, [contour_weights(1, 0.06, side)] * 8,
              "lowerlash")
    for s_t, length in ((0.38, 0.030), (0.62, 0.024)):
        i = int(round(s_t * 200))
        t2 = lo[min(i + 3, 200)] - lo[max(i - 3, 0)]
        t2 /= np.linalg.norm(t2)
        mid = lo[i] + nlo[i] * 0.020
        cen = np.stack([mid + t2 * (length * (k - 0.5)) for k in np.linspace(0, 1, 8)])
        lo_e, up_e = strip(cen, taper(8, [(0, 0.0050), (0.2, 0.0072), (0.8, 0.0072), (1, 0.0050)]))
        add_plate(mb, f"lashlow_{side}", side, lo_e, up_e, H_LOWER, PLATE_BASE, PLATE_BASE,
                  [contour_weights(1, s_t, side)] * 8, "lowerlash")

    # --- pale lid line hugging the top of the lash plate's outer half, and a thin dark crease
    # set further back
    sp = np.linspace(0.40, 0.80, 26)
    ip = np.round(sp * 200).astype(int)
    gp = np.interp(sp, su_up, wid) + 0.0060
    wp_ = taper(26, [(0, 0.0008), (0.2, 0.0040), (0.8, 0.0040), (1, 0.0008)])
    add_plate(mb, f"lidline_{side}", side, up[ip] + nup[ip] * gp[:, None], up[ip] + nup[ip] * (gp + wp_)[:, None],
              H_LINE, PLATE_BASE, PLATE_BASE, [contour_weights(0, x, side) for x in sp], "lidline")
    sc = np.linspace(0.24, 0.84, 34)
    ic = np.round(sc * 200).astype(int)
    gc = np.interp(sc, [0.24, 0.55, 0.84], [0.048, 0.056, 0.050])
    wc = taper(34, [(0, 0.0008), (0.2, 0.0034), (0.8, 0.0032), (1, 0.0008)])
    add_plate(mb, f"crease_{side}", side, up[ic] + nup[ic] * gc[:, None], up[ic] + nup[ic] * (gc + wc)[:, None],
              H_LINE, PLATE_BASE, PLATE_BASE, [mix_weights(contour_weights(0, x, side), eye, 0.62) for x in sc], "crease")


def build_brow(mb, side):
    cen = bezier(BROW, 46)
    s = np.linspace(0, 1, len(cen))
    w = np.interp(s, [0.0, 0.06, 0.45, 0.82, 1.0], [0.0230, 0.0250, 0.0200, 0.0110, 0.0012])
    lo_e, up_e = strip(cen, w)
    lo_e[0] = lo_e[0] + (cen[2] - cen[0]) * 1.2                     # angled inner cut
    bw = [sided(ctrl_weights(x, BROW_CTRL), side) for x in s]
    add_plate(mb, f"brow_{side}", side, lo_e, up_e, H_BROW, PLATE_BASE, PLATE_BASE, bw, "brow")


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
    xs, ys = np.linspace(-1, 1, 9), np.linspace(-0.5, 0.5, 5)
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
LOOK_BONES = ("Iris_L", "Iris_R")


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
        # pivot at the head centre: rotating it moves the iris around the head surface
        add(f"Iris_{side}", f"Eye_{side}", uc, 0.0, 0.0, frame_u=uc, pos=(0.0, 0.0, 0.0))
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
    build_mouth(mb)
    out = mb.result()
    out["bones"] = bone_defs()
    return out


# ---------------------------------------------------------------------------
# Posing helpers (pure numpy linear-blend skinning)
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


def look_angle(bone_name, x):
    """Rotation about the head's up axis (right-handed, radians) for x studs of iris travel
    outward along the surface (toward that eye's ear)."""
    return -bone_side(bone_name) * x / IRIS_RADIUS


def bone_motion(bone, val):
    """The bone's own motion as a 4x4 head-space matrix (applied before its parent's motion).

    Look bones (irises) rotate about the head's vertical axis through their pivot at the head
    centre (x = travel along the surface) and slide straight up/down (y). Every other bone
    translates by local_to_head(val).
    """
    M = np.eye(4)
    if bone["name"] in LOOK_BONES:
        a = look_angle(bone["name"], val[0])
        c, s = math.cos(a), math.sin(a)
        M[:3, :3] = [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]
        M[:3, 3] = bone["pos"] - M[:3, :3] @ bone["pos"] + np.array([0.0, val[1], 0.0])
    else:
        M[:3, 3] = local_to_head(bone, val)
    return M


def bone_matrices(bones, offsets):
    by_name = {b["name"]: b for b in bones}
    unknown = set(offsets) - set(by_name)
    if unknown:
        raise KeyError(f"unknown bones in pose: {sorted(unknown)}")
    G = {}
    for b in bones:  # parent-first order
        M = bone_motion(b, offsets.get(b["name"], (0.0, 0.0, 0.0)))
        G[b["name"]] = G[b["parent"]] @ M if b["parent"] else M
    return G


def deform(model, offsets):
    G = bone_matrices(model["bones"], offsets)
    P = model["P"]
    Ph = np.concatenate([P, np.ones((len(P), 1))], 1)
    out = np.zeros_like(P)
    for name, M in G.items():
        w = np.array([wd.get(name, 0.0) for wd in model["W"]])
        if w.any():
            out += w[:, None] * (Ph @ M.T)[:, :3]
    return out
