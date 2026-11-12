"""
AnimeFace R6 - shared design data and procedural geometry.

Everything here is in Roblox head space, in studs:
  +X = character's right, +Y = up, +Z = back of the head (the face looks toward -Z),
  origin = centre of the R6 head.

Design space used for placing features on the head surface:
  u = horizontal arc length around the head (u > 0 is the character's right side)
  v = arc length along the head profile from the equator (v > 0 is up)

Structure (follows the supplied example face): the skin around the eyes stays flush with the
head; the eye white and iris sit on the skin; the lashes, crease, lid highlight, lower lashes and
brows are raised 3D ridges. A thin skin "lid" sheet (barely above the skin) slides over the eye
to blink. Mouths are flat 2D images.

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
EYE_U = 0.235
EYE_V = -0.085
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
# A wide, calm, half-lidded eye: flat upper lid, shallow lower lid, sharp corners.
EYE_INNER = (-0.125, -0.012)
EYE_OUTER = (0.140, -0.006)
EYE_TOP = (-0.025, 0.045)
EYE_BOTTOM = (0.018, -0.050)
EYE_UPPER = [_hermite(EYE_INNER, _dir(48), EYE_TOP, (1, 0), 0.45), _hermite(EYE_TOP, (1, 0), EYE_OUTER, _dir(-22), 0.45)]
EYE_LOWER = [_hermite(EYE_OUTER, _dir(197), EYE_BOTTOM, (-1, 0)), _hermite(EYE_BOTTOM, (-1, 0), EYE_INNER, _dir(156))]
IRIS_C = (0.0, -0.002)
IRIS_R = (0.060, 0.064)
SCLERA_C, SCLERA_R, SCLERA_P = (0.007, -0.002), (0.168, 0.096), 2.6
SCLERA_UV = (0.175, 0.105)           # half extents mapped onto the sclera texture
RING_C, RING_R, RING_P = (0.007, -0.002), (0.240, 0.168), 2.4
RING_K = [0.0, 0.07, 0.16, 0.27, 0.40, 0.55, 0.70, 0.85, 1.0]
RING_FLAT_K = 0.60                    # the lid sheet stays at full height up to this fraction

# Highlights relative to the iris centre, in head-space u (same screen side on both eyes)
HIGHLIGHTS = [
    # (du, dv), (rx, ry), rotation (deg)
    ((0.021, 0.025), (0.0175, 0.0128), 24.0),
    ((-0.024, -0.027), (0.0072, 0.0072), 0.0),
]

BROW = [(-0.118, 0.142), (-0.045, 0.163), (0.060, 0.166), (0.150, 0.146)]
BLUSH_U, BLUSH_V, BLUSH_SIZE = 0.262, -0.205, (0.150, 0.066)

# 2D mouth: flat images on patches that swap by sliding in and out of the head.
MOUTH_V = -0.300
MOUTH_UNIT = 0.11                     # studs per sprite unit (sprite x in [-1, 1], y in [-0.5, 0.5])
MOUTHS = ["Neutral", "Smile", "Frown", "Smirk", "OpenSmall", "Open", "Laugh", "Grin", "Teeth", "O", "Pout",
          "Cat", "Wavy"]
DEFAULT_MOUTH = "Neutral"

# Layer heights above the skin (studs)
H_SCLERA = 0.0010
H_IRIS = 0.0022
H_SHINE = 0.0033
H_RING = 0.0045                       # lid sheet: just above the iris layers, nearly flush with the skin
H_RING_RIM = -0.0015                  # ... and tucked under the skin at its edge: no visible seam
H_WALL_BOTTOM = 0.0014
TUCK = 0.0008                         # ridge bases sink this far below the surface they sit on
LASH_BASE_IN = 0.0016                 # bottom of the lash ridge's eye-side wall (just above the eye white)
H_MOUTH = 0.0045
MOUTH_HIDE = 0.0300                   # inactive mouths sit this far inside the head
MOUTH_STAGGER = 0.00015               # so two mouths shown at once never z-fight
H_BLUSH_SHOWN = 0.0180
BLUSH_SHOW = 0.0300                   # the blush rests this far inside the head
IRIS_RADIUS = R + H_IRIS              # look = rotating the iris around the head axis at this radius

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


def ring_profile(k):
    """Lid-sheet height as a function of its ring fraction k (0 = eye edge, 1 = outer rim)."""
    k = np.asarray(k, float)
    slope = H_RING + (H_RING_RIM - H_RING) * smoothstep((k - RING_FLAT_K) / (1 - RING_FLAT_K))
    return np.where(k <= RING_FLAT_K, H_RING, slope)


def surface_height(ex, ey):
    """Height of the visible surface at eye-local points: eye white inside the opening,
    the lid sheet around it, the skin beyond (matches the meshes built below)."""
    pts, _, _, _ = eye_contour()
    ang = np.arctan2(pts[:, 1] - RING_C[1], pts[:, 0] - RING_C[0])
    rim = superellipse(RING_C, RING_R, RING_P, ang)
    order = np.argsort(ang)
    a = np.concatenate([ang[order] - 2 * np.pi, ang[order], ang[order] + 2 * np.pi])
    c = np.concatenate([pts[order]] * 3)
    r = np.concatenate([rim[order]] * 3)
    ex, ey = np.broadcast_arrays(np.asarray(ex, float), np.asarray(ey, float))
    phi = np.arctan2(ey - RING_C[1], ex - RING_C[0])
    cx, cy = np.interp(phi, a, c[:, 0]), np.interp(phi, a, c[:, 1])
    rx, ry = np.interp(phi, a, r[:, 0]), np.interp(phi, a, r[:, 1])
    dx, dy = rx - cx, ry - cy
    k = ((ex - cx) * dx + (ey - cy) * dy) / (dx * dx + dy * dy)
    return np.where(k < 0, H_SCLERA, np.where(k <= 1, np.maximum(ring_profile(k), 0.0), 0.0))


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


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
def build_shell(mb):
    # 72 columns: facets sag at most 0.0006 inside the true surface, still below every layer
    # placed on it (eye white +0.0010, ridge bases -0.0008, lid rim -0.0015 tuck further in)
    nt = 72
    band = [YC * k / 6 for k in range(7)]
    a_vals = band + [YC + ARC * k / 8 for k in range(1, 9)] + [YC + ARC + d for d in (0.100, 0.200)]
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


def add_ridge(mb, part, side, path, width, prot, weights, rect, edge_base=None):
    """Raised 3D strip (rounded triangular cross-section) along an eye-local path.

    width[i]: strip width; prot[i]: crest height above the local surface (surface_height).
    edge_base None: strip centred on the path. Otherwise the strip starts at the path and
    extends along its left normal, with a steep wall on the path side whose bottom height is
    edge_base[i] (the lash ridge sits on the lid edge this way, its wall facing the eye).
    Bases sink TUCK below the surface so the ridge grows out of it without a seam.
    """
    path = np.asarray(path, float)
    n = len(path)
    width = np.broadcast_to(np.asarray(width, float), (n,))
    prot = np.broadcast_to(np.asarray(prot, float), (n,))
    nrm = left_normals(path)
    if edge_base is None:
        fr = np.array([0.0, 0.2, 0.5, 0.8, 1.0]) - 0.5
    else:
        fr = np.array([-0.03, 0.0, 0.28, 0.62, 1.0])
    m = len(fr)
    off = fr[None, :] * width[:, None]
    P2 = path[:, None, :] + nrm[:, None, :] * off[..., None]
    local = surface_height(P2[..., 0], P2[..., 1])
    if edge_base is None:
        base = local - TUCK
        crest = local[:, 2] + prot
        shape = np.array([0.0, 0.72, 1.0, 0.72, 0.0])
        H = base + shape[None, :] * (crest[:, None] - base)
    else:
        eb = np.broadcast_to(np.asarray(edge_base, float), (n,))
        crest = local[:, 2] + prot
        H = np.stack([eb, crest - 0.22 * prot, crest, local[:, 3] + 0.55 * (crest - local[:, 3]), local[:, 4] - TUCK], -1)
    P, Nsurf = eye_uv_to_world(side, P2[..., 0].ravel(), P2[..., 1].ravel(), H.ravel())
    P = P.reshape(n, m, 3)
    Nsurf = Nsurf.reshape(n, m, 3)
    # normals from the cross-section: across direction A and surface normal
    u = SIDES[side] * (EYE_U + P2[..., 0])
    A = eye_dir3(side, np.broadcast_to(nrm[:, None, :], (n, m, 2)), u)
    da = np.gradient(off, axis=1)
    dh = np.gradient(H, axis=1)
    L = np.hypot(da, dh) + 1e-12
    N = (-dh / L)[..., None] * A + (da / L)[..., None] * Nsurf
    UV = np.broadcast_to(rect_uv(rect, 0.5, 0.5), (n * m, 2))
    W = [w for w in weights for _ in range(m)]
    mb.add(part, P.reshape(-1, 3), N.reshape(-1, 3), UV, W, grid_faces(n, m))
    # end caps (separate vertices so they shade as flat ends)
    for i, sgn in ((0, -1.0), (n - 1, 1.0)):
        t2 = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
        t3 = eye_dir3(side, t2 / np.linalg.norm(t2), u[i, 2])
        mb.add(part, P[i], np.broadcast_to(sgn * t3, (m, 3)), UV[:m], [weights[i]] * m,
               [[0, j, j + 1] for j in range(1, m - 1)])


def build_eye(mb, side):
    pts, arc, s, p = eye_contour()
    n = len(pts)
    cw = [contour_weights(arc[i], s[i], side) for i in range(n)]
    eye = {f"Eye_{side}": 1.0}
    nseg = 72
    phi = np.linspace(0, 2 * np.pi, nseg, endpoint=False)

    # --- eye white (on the skin, with a soft lid shadow painted in)
    rings = [0.0, 0.3, 0.55, 0.75, 0.9, 1.0]
    flat = np.concatenate([np.array([SCLERA_C])] +
                          [superellipse(SCLERA_C, (SCLERA_R[0] * k, SCLERA_R[1] * k), SCLERA_P, phi) for k in rings[1:]])
    P, N = eye_uv_to_world(side, flat[:, 0], flat[:, 1], H_SCLERA)
    UV = rect_uv("sclera", 0.5 + 0.5 * flat[:, 0] / SCLERA_UV[0], 0.5 - 0.5 * flat[:, 1] / SCLERA_UV[1])
    mb.add(f"sclera_{side}", P, N, UV, [eye] * len(P), disc_faces(len(rings) - 1, nseg))

    # --- iris: hugs the head surface; looking around rotates it about the head axis, so it
    # never lifts off the eye white or pokes through the lid sheet
    rings = [0.0, 0.18, 0.40, 0.62, 0.80, 0.92, 1.0]
    disc = np.concatenate([np.zeros((1, 2))] + [np.stack([np.cos(phi) * k, np.sin(phi) * k], -1) for k in rings[1:]])
    P, N = iris_point(side, disc[:, 0] * IRIS_R[0], disc[:, 1] * IRIS_R[1], H_IRIS)
    UV = rect_uv("iris", 0.5 + 0.5 * 0.97 * disc[:, 0], 0.5 - 0.5 * 0.97 * disc[:, 1])
    mb.add(f"iris_{side}", P, N, UV, [{f"Iris_{side}": 1.0}] * len(P), disc_faces(len(rings) - 1, nseg))

    # --- highlights (opaque white shapes just above the iris)
    hp = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    for (du, dv), (rx, ry), rot in HIGHLIGHTS:
        a = math.radians(rot)
        lx, ly = np.cos(hp) * rx, np.sin(hp) * ry
        x = np.concatenate([[0.0], lx * math.cos(a) - ly * math.sin(a)])
        y = np.concatenate([[0.0], lx * math.sin(a) + ly * math.cos(a)])
        P, N = iris_point(side, du + x, dv + y, H_SHINE)
        mb.add(f"shine_{side}", P, N, np.broadcast_to(rect_uv("highlight", 0.5, 0.5), (len(P), 2)),
               [{f"Shine_{side}": 1.0}] * len(P), [[0, 1 + i, 1 + (i + 1) % 32] for i in range(32)])

    # --- lid sheet: skin-coloured, barely above the iris layers; its inner edge is the eye
    # opening and follows the lid bones (blinks stretch it over the eye)
    ang = np.arctan2(pts[:, 1] - RING_C[1], pts[:, 0] - RING_C[0])
    rim = superellipse(RING_C, RING_R, RING_P, ang)
    ring_pts, ring_h, ring_w = [], [], []
    for k in RING_K:
        ring_pts.append(pts + (rim - pts) * k)
        ring_h.append(np.full(n, float(ring_profile(k))))
        f = (1.0 - k) ** 1.6
        ring_w.extend(mix_weights(cw[i], eye, 1.0 - f) for i in range(n))
    rp = np.concatenate(ring_pts)
    P, N = eye_uv_to_world(side, rp[:, 0], rp[:, 1], np.concatenate(ring_h))
    UV = rect_uv("skin", 0.5 + rp[:, 0] / 0.6, 0.5 - rp[:, 1] / 0.6)
    mb.add(f"ring_{side}", P, N, UV, ring_w, grid_faces(len(RING_K), n, wrap=True))

    # --- wall: short skirt from the lid edge down to the eye white. Perpendicular to the skin,
    # so it is emitted double-sided with explicit winding (separate vertices per side: mesh tools
    # drop faces that reuse the same vertex set). Radial normals so it shades like the skin.
    P1, N1 = eye_uv_to_world(side, pts[:, 0], pts[:, 1], H_RING)
    P2, _ = eye_uv_to_world(side, pts[:, 0], pts[:, 1], H_WALL_BOTTOM)
    UV = np.concatenate([rect_uv("wall", p, 0.0), rect_uv("wall", p, 1.0)])
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    for fl in (faces, [f[::-1] for f in faces]):
        mb.add(f"wall_{side}", np.concatenate([P1, P2]), np.concatenate([N1, N1]), UV, cw + cw, fl, keep_winding=True)

    # --- upper lash ridge: sits on the lid edge, thickest toward the outer corner, then runs out
    # past the corner as a tapering wing
    up = bezier(EYE_UPPER, 66)
    su = np.linspace(0, 1, len(up))
    o = np.array(EYE_OUTER)
    t_end = (up[-1] - up[-3]) / np.linalg.norm(up[-1] - up[-3])
    wing = bezier([o, o + t_end * 0.018, o + np.array([0.036, -0.009]), o + np.array([0.050, -0.010])], 14)[1:]
    path = np.concatenate([up, wing])
    tw = np.linspace(0, 1, len(wing) + 1)[1:]
    width = np.concatenate([np.interp(su, [0.0, 0.05, 0.25, 0.55, 0.85, 1.0], [0.0050, 0.0090, 0.0160, 0.0200, 0.0215, 0.0205]),
                            np.interp(tw, [0.0, 0.5, 1.0], [0.0205, 0.0120, 0.0012])])
    prot = np.concatenate([np.interp(su, [0.0, 0.1, 0.5, 1.0], [0.0030, 0.0055, 0.0080, 0.0095]),
                           np.interp(tw, [0.0, 0.6, 1.0], [0.0095, 0.0060, 0.0012])])
    wing_local = surface_height(wing[:, 0], wing[:, 1]) - TUCK
    edge = np.concatenate([np.full(len(up), LASH_BASE_IN), wing_local])
    lw = [contour_weights(0, x, side) for x in su] + [eye] * len(wing)
    add_ridge(mb, f"lash_{side}", side, path, width, prot, lw, "lash", edge_base=edge)

    # inner corner: the lash line hooks down a little past the corner
    i0 = up[2]
    hook = bezier([i0, i0 + np.array([-0.006, -0.002]), i0 + np.array([-0.011, -0.008]), i0 + np.array([-0.013, -0.016])], 9)
    add_ridge(mb, f"lash_{side}", side, hook, taper(9, [(0, 0.0055), (1, 0.0010)]), taper(9, [(0, 0.0040), (1, 0.0012)]),
              [contour_weights(0, su[2], side)] * 9, "lash")

    # lash spikes: curved blades growing out of the ridge's outer half
    nrm_up = left_normals(up)
    w_up = width[:len(up)]
    for s_root, length, bend, wbase in ((0.64, 0.021, 0.55, 0.0100), (0.83, 0.027, 0.75, 0.0115)):
        i = int(round(s_root * (len(up) - 1)))
        root = up[i] + nrm_up[i] * (0.42 * w_up[i])
        d0 = nrm_up[i]
        d1 = np.array([1.0, 0.18]) / np.linalg.norm([1.0, 0.18])
        d1 = d0 * (1 - bend) + d1 * bend
        d1 /= np.linalg.norm(d1)
        blade = bezier([root, root + d0 * length * 0.45, root + d1 * length * 0.8, root + d1 * length], 9)
        add_ridge(mb, f"lash_{side}", side, blade, taper(9, [(0, wbase), (1, 0.0006)]),
                  taper(9, [(0, prot[i] * 0.9), (1, 0.0015)]), [contour_weights(0, s_root, side)] * 9, "lash")

    # --- crease: a thin line set back above the lid
    cs = np.linspace(0.30, 1.0, 34)
    upd = bezier(EYE_UPPER, 201)
    idx = np.round(cs * 200).astype(int)
    gap = np.interp(cs, [0.30, 0.60, 1.0], [0.029, 0.033, 0.026])
    crease = upd[idx] + left_normals(upd)[idx] * gap[:, None]
    ext = crease[-1] + (crease[-1] - crease[-3]) / np.linalg.norm(crease[-1] - crease[-3]) * np.linspace(0.004, 0.020, 5)[:, None]
    crease = np.concatenate([crease, ext])
    nc = len(crease)
    cwid = taper(nc, [(0.0, 0.0010), (0.12, 0.0042), (0.75, 0.0040), (1.0, 0.0008)])
    cws = [mix_weights(contour_weights(0, x, side), eye, 0.62) for x in cs] + [eye] * len(ext)
    add_ridge(mb, f"crease_{side}", side, crease, cwid, taper(nc, [(0, 0.0012), (0.12, 0.0032), (0.8, 0.0030), (1, 0.0010)]),
              cws, "crease")

    # --- lid highlight: a long pale line above the crease
    ls = np.linspace(0.16, 0.97, 34)
    idx = np.round(ls * 200).astype(int)
    lgap = np.interp(ls, [0.16, 0.55, 0.97], [0.052, 0.058, 0.050])
    lid = upd[idx] + left_normals(upd)[idx] * lgap[:, None]
    nl = len(lid)
    brow_w = {f"Brow_{side}": 1.0}
    add_ridge(mb, f"lidline_{side}", side, lid, taper(nl, [(0, 0.0008), (0.2, 0.0036), (0.8, 0.0032), (1, 0.0008)]),
              taper(nl, [(0, 0.0010), (0.2, 0.0026), (0.8, 0.0024), (1, 0.0010)]),
              [mix_weights(eye, brow_w, 0.35)] * nl, "lidline")

    # --- lower lashes: a thin line set below the outer part of the lower lid, one short dash,
    # and a small spike at the outer end
    lod = bezier(EYE_LOWER, 201)
    nlo = left_normals(lod)
    for s0, s1, g, wmax, pmax in ((0.02, 0.50, 0.0080, 0.0036, 0.0028), (0.58, 0.70, 0.0095, 0.0030, 0.0024)):
        ss = np.linspace(s0, s1, max(6, int((s1 - s0) * 60)))
        idx = np.round(ss * 200).astype(int)
        line = lod[idx] + nlo[idx] * g
        k = len(line)
        add_ridge(mb, f"lashlow_{side}", side, line, taper(k, [(0, 0.0010), (0.15, wmax), (0.8, wmax * 0.8), (1, 0.0008)]),
                  taper(k, [(0, 0.0010), (0.15, pmax), (0.85, pmax * 0.85), (1, 0.0010)]),
                  [contour_weights(1, x, side) for x in ss], "lowerlash")
    i = int(0.07 * 200)
    root = lod[i] + nlo[i] * 0.0085
    spike = bezier([root, root + nlo[i] * 0.004, root + np.array([0.006, -0.009]), root + np.array([0.010, -0.012])], 7)
    add_ridge(mb, f"lashlow_{side}", side, spike, taper(7, [(0, 0.0034), (1, 0.0005)]), taper(7, [(0, 0.0026), (1, 0.0010)]),
              [contour_weights(1, 0.07, side)] * 7, "lowerlash")


def build_brow(mb, side):
    cen = bezier(BROW, 41)
    s = np.linspace(0, 1, len(cen))
    w = np.interp(s, [0.0, 0.08, 0.45, 0.80, 1.0], [0.0185, 0.0215, 0.0165, 0.0095, 0.0015])
    prot = np.interp(s, [0.0, 0.1, 0.8, 1.0], [0.0050, 0.0060, 0.0050, 0.0015])
    bw = [sided(ctrl_weights(x, BROW_CTRL), side) for x in s]
    add_ridge(mb, f"brow_{side}", side, cen, w, prot, bw, "brow")
    # a short loose hair stroke under the inner end
    a = np.array(BROW[0])
    stroke = bezier([a + np.array([-0.010, -0.030]), a + np.array([-0.004, -0.022]), a + np.array([0.004, -0.017]),
                     a + np.array([0.014, -0.014])], 8)
    add_ridge(mb, f"brow_{side}", side, stroke, taper(8, [(0, 0.0012), (0.4, 0.0050), (1, 0.0008)]),
              taper(8, [(0, 0.0012), (0.4, 0.0036), (1, 0.0010)]), [sided({"BrowInner": 1.0}, side)] * 8, "brow")


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
