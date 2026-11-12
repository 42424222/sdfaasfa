"""
Paint the AnimeFace texture atlas (run with system python3: needs numpy + Pillow).

Anime-style colour work: smooth gradients on the eyes, crisp anti-aliased edges, and 2D mouth
drawings with thick dark strokes, near-black insides, a pink tongue and white teeth.

Outputs (in ../assets/textures):
  AnimeFace_Color.png         RGBA, for a SurfaceAppearance with AlphaMode = Overlay.
                              Transparent texels show the MeshPart's Color (the skin tone).
  AnimeFace_Color_Opaque.png  Same art with a default skin tone baked in (for MeshPart.TextureID).
  AnimeFace_Roughness.png     Optional roughness map (white = rough).
  mouths/Mouth_<Name>.png     Each 2D mouth on its own (transparent), e.g. for Decal swapping.
and ../docs/images/mouths.png, a labelled sheet of the mouth images.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import face_design as fd  # noqa: E402

SS = 2                      # supersampling factor
SIZE = fd.ATLAS * SS
OUT = os.path.join(HERE, "..", "assets", "textures")
DOCS = os.path.join(HERE, "..", "docs", "images")
DEFAULT_SKIN = (255, 224, 199)
SKIN_ROUGH = 0.85

PAL = {
    # eyes: warm brown iris
    "iris_top": "#2c1507", "iris_upper": "#55290e", "iris_mid": "#8a4718", "iris_low": "#c27b2e",
    "iris_bottom": "#e7b05a", "iris_ring": "#1b0d05", "pupil": "#120703", "iris_glow": "#f5cf86",
    "sclera": "#ffffff", "sclera_shade": "#d4d6e6", "sclera_deep": "#b4b8cf", "sclera_corner": "#c7c0cc",
    "socket": "#6b3a33",
    # raised lines
    "lash": "#111012", "brow": "#151214", "crease": "#1b1517", "lidline": "#fff8f4", "lowerlash": "#2a2124",
    "highlight": "#ffffff",
    "blush": "#ff7f90", "blush_line": "#f0546c",
    # mouths
    "line": "#2a1714", "inner_top": "#1b0c0a", "inner_bottom": "#3a1916", "tongue": "#e47c84",
    "tongue_light": "#f4a7ab", "teeth": "#fbf7f7", "teeth_shade": "#e2d6d8", "teeth_line": "#9b8489",
}


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def col(name):
    return hexc(PAL.get(name, name))


def lerp(a, b, t):
    t = np.asarray(t)[..., None]
    return a * (1 - t) + b * t


def S(x):
    return fd.smoothstep(x)


canvas = np.zeros((SIZE, SIZE, 4))
canvas[..., :3] = np.array(DEFAULT_SKIN) / 255.0
rough = np.full((SIZE, SIZE), SKIN_ROUGH)


def region(name):
    """Pixel-centre coordinates of a rect as (fx, fy) in the same space as fd.rect_uv (edge-extended)."""
    x0, y0, x1, y1 = fd.RECT[name]
    m = fd.UV_MARGIN
    xs = (np.arange(x0 * SS, x1 * SS) + 0.5) / SS
    ys = (np.arange(y0 * SS, y1 * SS) + 0.5) / SS
    FX, FY = np.meshgrid((xs - (x0 + m)) / (x1 - x0 - 2 * m), (ys - (y0 + m)) / (y1 - y0 - 2 * m))
    return (slice(y0 * SS, y1 * SS), slice(x0 * SS, x1 * SS)), FX, FY


def inner_px(name):
    x0, _, x1, _ = fd.RECT[name]
    return (x1 - x0 - 2 * fd.UV_MARGIN) * SS


def put(name, rgb, alpha, r=None):
    sl, _, _ = region(name)
    canvas[sl][..., :3] = rgb
    canvas[sl][..., 3] = alpha
    if r is not None:
        # transparent texels must match the skin exactly, or overlay patches show as boxes
        rough[sl] = SKIN_ROUGH + (r - SKIN_ROUGH) * np.asarray(alpha, float)


class Surface:
    """Premultiplied RGBA drawing surface over one atlas rect, in its own units (y up)."""

    def __init__(self, name, xr, yr):
        self.sl, FX, FY = region(name)
        self.X = xr[0] + FX * (xr[1] - xr[0])
        self.Y = yr[1] - FY * (yr[1] - yr[0])
        self.px = (xr[1] - xr[0]) / inner_px(name)
        self.C = np.zeros(self.X.shape + (3,))
        self.A = np.zeros(self.X.shape)

    def cover(self, sd):
        return np.clip(0.5 - sd / self.px, 0.0, 1.0)

    def over(self, color, cov):
        c = col(color) if isinstance(color, str) else color
        cov = np.clip(cov, 0, 1)
        if np.ndim(c) == 1:
            self.C = c * cov[..., None] + self.C * (1 - cov[..., None])
        else:
            self.C = c * cov[..., None] + self.C * (1 - cov[..., None])
        self.A = cov + self.A * (1 - cov)

    def stroke_sd(self, pts, widths):
        pts = np.asarray(pts, float)
        widths = np.broadcast_to(np.asarray(widths, float), (len(pts),))
        best = np.full(self.X.shape, np.inf)
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            abx, aby = bx - ax, by - ay
            L2 = abx * abx + aby * aby
            if L2 < 1e-14:
                continue
            t = np.clip(((self.X - ax) * abx + (self.Y - ay) * aby) / L2, 0.0, 1.0)
            d = np.hypot(self.X - (ax + t * abx), self.Y - (ay + t * aby))
            best = np.minimum(best, d - (widths[i] + t * (widths[i + 1] - widths[i])) / 2)
        return best

    def poly_sd(self, poly):
        poly = np.asarray(poly, float)
        inside = np.zeros(self.X.shape, bool)
        dist = np.full(self.X.shape, np.inf)
        for i in range(len(poly)):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
            cond = (ay > self.Y) != (by > self.Y)
            xint = ax + (self.Y - ay) * (bx - ax) / np.where(np.abs(by - ay) < 1e-12, 1e-12, by - ay)
            inside ^= cond & (self.X < xint)
            abx, aby = bx - ax, by - ay
            L2 = max(abx * abx + aby * aby, 1e-14)
            t = np.clip(((self.X - ax) * abx + (self.Y - ay) * aby) / L2, 0.0, 1.0)
            dist = np.minimum(dist, np.hypot(self.X - (ax + t * abx), self.Y - (ay + t * aby)))
        return np.where(inside, -dist, dist)

    def stroke(self, pts, widths, color, clip=None):
        cov = self.cover(self.stroke_sd(pts, widths))
        self.over(color, cov if clip is None else cov * clip)

    def fill(self, poly, color, clip=None):
        cov = self.cover(self.poly_sd(poly))
        self.over(color, cov if clip is None else cov * clip)
        return cov

    def commit(self, r=0.6):
        rgb = np.where(self.A[..., None] > 1e-6, self.C / np.maximum(self.A[..., None], 1e-6), np.array(DEFAULT_SKIN) / 255.0)
        canvas[self.sl][..., :3] = rgb
        canvas[self.sl][..., 3] = self.A
        rough[self.sl] = SKIN_ROUGH + (r - SKIN_ROUGH) * self.A


def bez(P, n=80):
    return fd.bezier(P, n)


def taper(n, stops):
    return fd.taper(n, stops)


def ellipse(c, r, n=120):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([c[0] + r[0] * np.cos(t), c[1] + r[1] * np.sin(t)], -1)


def rounded_rect(x0, y0, x1, y1, rad, n=10):
    pts = []
    for cx, cy, a0 in ((x1 - rad, y1 - rad, 0), (x0 + rad, y1 - rad, 90), (x0 + rad, y0 + rad, 180), (x1 - rad, y0 + rad, 270)):
        for a in np.radians(np.linspace(a0, a0 + 90, n)):
            pts.append((cx + rad * np.cos(a), cy + rad * np.sin(a)))
    return np.array(pts)


def shape(top, bottom):
    """Closed outline from a top edge (left -> right) and a bottom edge (right -> left)."""
    return np.concatenate([top, bottom[1:-1]])


def ramp(t, stops):
    t = np.clip(t, 0, 1)
    pos = np.array([p for p, _ in stops])
    cs = np.array([col(c) for _, c in stops])
    return np.stack([np.interp(t, pos, cs[:, k]) for k in range(3)], -1)


# ---------------------------------------------------------------- eyes
def paint_iris():
    s = Surface("iris", (-1 / 0.97, 1 / 0.97), (-1 / 0.97, 1 / 0.97))
    X, Y = s.X, s.Y
    r = np.hypot(X, Y)
    ang = np.arctan2(Y, X)
    c = ramp((1 - Y) / 2, [(0.0, "iris_top"), (0.28, "iris_upper"), (0.52, "iris_mid"), (0.78, "iris_low"), (1.0, "iris_bottom")])
    # fine radial fibres
    rng = np.random.default_rng(7)
    f = np.zeros_like(ang)
    for k in (9, 17, 29, 43, 61, 83):
        f += rng.uniform(0.5, 1.0) * np.sin(k * ang + rng.uniform(0, 2 * np.pi) + 0.8 * np.sin(3 * ang + k))
    fib = np.tanh(f * 0.9) * S((r - 0.36) / 0.10) * (1 - S((r - 0.86) / 0.08))
    c = c * (1 + 0.05 * fib)[..., None]
    # soft glow crescent in the lower half, and a lighter collarette around the pupil
    cres = S((0.90 - np.hypot(X * 1.04, Y + 0.30)) / 0.16) * S((np.hypot(X * 1.12, Y + 0.08) - 0.52) / 0.14) * S((-Y - 0.05) / 0.35)
    c = lerp(c, col("iris_glow"), 0.55 * cres)
    c = lerp(c, col("iris_low"), 0.22 * np.exp(-((r - 0.46) / 0.07) ** 2) * S((-Y + 0.6) / 0.8))
    # upper-lid shadow over the top of the iris
    c = lerp(c, col("iris_top"), 0.50 * S((Y - 0.18) / 0.62))
    # pupil
    pr = np.hypot(X / 0.27, (Y - 0.06) / 0.31)
    c = lerp(c, col("pupil"), 1 - S((pr - 0.94) / 0.10))
    # limbal ring and crisp outline
    c = lerp(c, col("iris_ring"), 0.85 * S((r - 0.78) / 0.15))
    c = lerp(c, col("iris_ring"), S((r - 0.925) / 0.025))
    # small painted sparkles (the main highlights are geometry)
    for sx, sy, sr, a in ((-0.46, -0.48, 0.055, 0.55), (0.52, -0.30, 0.030, 0.40)):
        d = np.hypot(X - sx, Y - sy)
        c = lerp(c, col("highlight"), a * (1 - S((d - sr * 0.3) / (sr * 0.9))))
    s.C, s.A = c, np.ones_like(X)
    s.commit(0.30)


def paint_sclera():
    s = Surface("sclera", (-fd.SCLERA_UV[0], fd.SCLERA_UV[0]), (-fd.SCLERA_UV[1], fd.SCLERA_UV[1]))
    up = fd.bezier(fd.EYE_UPPER, 300)
    lo = fd.bezier(fd.EYE_LOWER, 300)
    y_up = np.interp(s.X, up[:, 0], up[:, 1], left=up[0, 1], right=up[-1, 1])
    order = np.argsort(lo[:, 0])
    y_lo = np.interp(s.X, lo[order, 0], lo[order, 1])
    height = np.maximum(y_up - y_lo, 1e-3)
    t = (y_up - s.Y) / height                         # 0 at the upper lid, 1 at the lower lid
    c = np.broadcast_to(col("sclera"), s.X.shape + (3,)).copy()
    # two-tone white: a clean lavender-grey band under the upper lid, darker right at the lash
    c = lerp(c, col("sclera_shade"), 1 - S((t - 0.30) / 0.06))
    c = lerp(c, col("sclera_deep"), 0.7 * (1 - S(t / 0.10)))
    # the deep inner corner and the outer corner fall into soft shadow
    ix, iy = fd.EYE_INNER
    d_in = np.hypot((s.X - ix) / 1.3, s.Y - iy)
    c = lerp(c, col("sclera_corner"), 0.85 * (1 - S((d_in - 0.010) / 0.035)))
    ox, oy = fd.EYE_OUTER
    c = lerp(c, col("sclera_shade"), 0.6 * (1 - S((np.hypot(s.X - ox, s.Y - oy) - 0.010) / 0.040)))
    s.C, s.A = c, np.ones_like(s.X)
    s.commit(0.35)


def paint_swatches():
    for name, r in (("lash", 0.42), ("brow", 0.55), ("crease", 0.55), ("lidline", 0.45), ("lowerlash", 0.55), ("highlight", 0.2)):
        put(name, col(name), 1.0, r)
    put("skin", np.array(DEFAULT_SKIN) / 255.0, 0.0, SKIN_ROUGH)
    # socket walls: x = position around the opening (upper arc inner->outer, then lower arc),
    # y = depth (0 at the rim, 1 at the eye white). Black under the lash plate, shadowed skin
    # (a dark overlay over the skin colour) elsewhere, getting darker deeper in
    sl, FX, FY = region("wall")
    p = np.clip(FX, 0, 1)
    d = np.clip(FY, 0, 1)
    lash = S((p - 0.03) / 0.05) * S((0.43 - p) / 0.05)
    rgb = lerp(np.broadcast_to(col("socket"), p.shape + (3,)), col("lash"), lash)
    put("wall", rgb, np.maximum(0.32 + 0.38 * d, lash), 0.6)


def paint_blush():
    hx, hy = fd.BLUSH_SIZE[0] / 2, fd.BLUSH_SIZE[1] / 2
    s = Surface("blush", (-hx, hx), (-hy, hy))
    d = np.hypot(s.X / hx, s.Y / hy)
    s.over("blush", 0.45 * (1 - S((d - 0.3) / 0.7)))
    for cx in (-0.024, 0.0, 0.024):
        s.stroke([(cx - 0.006, -0.012), (cx + 0.006, 0.012)], 0.0042, "blush_line")
    s.commit(0.85)


# ---------------------------------------------------------------- mouths (sprite x in [-1, 1], y in [-0.5, 0.5])
LINE_W = 0.070


def inner_fill(s, poly, y0, y1):
    """Dark mouth interior with a slight vertical gradient; returns its coverage."""
    cov = s.cover(s.poly_sd(poly))
    t = np.clip((y1 - s.Y) / max(y1 - y0, 1e-6), 0, 1)
    s.over(lerp(np.broadcast_to(col("inner_top"), s.X.shape + (3,)), col("inner_bottom"), t), cov)
    return cov


def tongue(s, c, r, clip):
    cov = s.cover(s.poly_sd(ellipse(c, r))) * clip
    t = np.clip((s.Y - (c[1] - r[1])) / (2 * r[1]), 0, 1)
    s.over(lerp(np.broadcast_to(col("tongue"), s.X.shape + (3,)), col("tongue_light"), 0.6 * S((t - 0.45) / 0.55)), cov)


def teeth_fill(s, poly, clip=None):
    cov = s.cover(s.poly_sd(poly))
    if clip is not None:
        cov = cov * clip
    s.over("teeth", cov)
    return cov


def m_neutral(s):
    s.stroke(bez([(-0.34, 0.006), (-0.12, -0.010), (0.12, -0.010), (0.34, 0.006)]),
             taper(80, [(0, 0.045), (0.5, 0.066), (1, 0.045)]), "line")


def m_smile(s):
    s.stroke(bez([(-0.62, 0.10), (-0.26, -0.065), (0.26, -0.065), (0.62, 0.10)]),
             taper(80, [(0, 0.030), (0.5, 0.080), (1, 0.030)]), "line")


def m_frown(s):
    s.stroke(bez([(-0.40, -0.075), (-0.18, 0.070), (0.18, 0.070), (0.40, -0.075)]),
             taper(80, [(0, 0.045), (0.5, 0.075), (1, 0.045)]), "line")


def m_smirk(s):
    s.stroke(bez([(-0.50, 0.010), (-0.14, -0.050), (0.28, -0.045), (0.60, 0.115)], 90),
             taper(90, [(0, 0.030), (0.5, 0.070), (1, 0.074)]), "line")
    s.stroke(bez([(0.57, 0.20), (0.64, 0.18), (0.67, 0.13), (0.66, 0.08)], 20), taper(20, [(0, 0.012), (0.5, 0.030), (1, 0.012)]), "line")


def m_open_small(s):
    top = bez([(-0.23, 0.10), (-0.08, 0.075), (0.08, 0.075), (0.23, 0.10)], 50)
    poly = shape(top, bez([(0.23, 0.10), (0.19, -0.18), (-0.19, -0.18), (-0.23, 0.10)], 50))
    inside = inner_fill(s, poly, -0.18, 0.10)
    tongue(s, (0.0, -0.115), (0.12, 0.055), inside)
    s.stroke(np.concatenate([poly, poly[:1]]), LINE_W * 0.85, "line")


def m_open(s):
    top = bez([(-0.44, 0.16), (-0.18, 0.11), (0.18, 0.11), (0.44, 0.16)], 60)
    poly = shape(top, bez([(0.44, 0.16), (0.36, -0.45), (-0.36, -0.45), (-0.44, 0.16)], 60))
    inside = inner_fill(s, poly, -0.45, 0.16)
    tongue(s, (0.0, -0.31), (0.23, 0.12), inside)
    s.stroke(np.concatenate([poly, poly[:1]]), LINE_W, "line")
    s.stroke(top, taper(60, [(0, 0.080), (0.5, 0.090), (1, 0.080)]), "line")
    for k in (-1, 1):  # corners curl up
        tip = bez([(0.44 * k, 0.16), (0.50 * k, 0.175), (0.545 * k, 0.21), (0.56 * k, 0.26)], 14)
        s.stroke(tip, taper(14, [(0, 0.075), (1, 0.018)]), "line")


def m_laugh(s):
    top = bez([(-0.58, 0.20), (-0.26, 0.13), (0.26, 0.13), (0.58, 0.20)], 70)
    poly = shape(top, bez([(0.58, 0.20), (0.48, -0.47), (-0.48, -0.47), (-0.58, 0.20)], 70))
    inside = inner_fill(s, poly, -0.47, 0.20)
    teeth_fill(s, np.concatenate([top, (top - np.array([0.0, 0.09]))[::-1]]), inside)
    s.stroke(top - np.array([0.0, 0.09]), 0.018, "teeth_shade", clip=inside)
    tongue(s, (0.0, -0.30), (0.30, 0.12), inside)
    s.stroke(np.concatenate([poly, poly[:1]]), LINE_W, "line")
    s.stroke(top, taper(70, [(0, 0.080), (0.5, 0.095), (1, 0.080)]), "line")


def m_grin(s):
    top = bez([(-0.58, 0.18), (-0.28, 0.06), (0.28, 0.06), (0.58, 0.18)], 70)
    bot = bez([(0.58, 0.18), (0.40, -0.33), (-0.40, -0.33), (-0.58, 0.18)], 70)
    poly = shape(top, bot)
    inside = teeth_fill(s, poly)
    # soft shade along the lower teeth edge and a faint gap line
    s.stroke(bot[8:-8] + np.array([0.0, 0.045]), 0.05, "teeth_shade", clip=inside)
    s.stroke(bez([(-0.40, 0.03), (-0.15, -0.035), (0.15, -0.035), (0.40, 0.03)]), 0.012, "teeth_line", clip=inside)
    s.stroke(top, taper(70, [(0, 0.050), (0.5, 0.055), (1, 0.050)]), "line")
    s.stroke(bot, taper(70, [(0, 0.050), (0.5, 0.115), (1, 0.050)]), "line")


def m_teeth(s):
    poly = rounded_rect(-0.38, -0.11, 0.38, 0.11, 0.07)
    inside = teeth_fill(s, poly)
    for x in (-0.19, 0.0, 0.19):
        s.stroke([(x, -0.12), (x, 0.12)], 0.012, "teeth_line", clip=inside)
    s.stroke([(-0.40, 0.0), (0.40, 0.0)], 0.020, "teeth_line", clip=inside)
    s.stroke(np.concatenate([poly, poly[:1]]), LINE_W * 0.95, "line")


def m_o(s):
    poly = ellipse((0.0, -0.05), (0.15, 0.20))
    inside = inner_fill(s, poly, -0.25, 0.15)
    tongue(s, (0.0, -0.20), (0.10, 0.06), inside)
    s.stroke(np.concatenate([poly, poly[:1]]), LINE_W, "line")


def m_pout(s):
    # a "3"-shaped kissy pout
    path = bez([(-0.05, 0.19), (0.13, 0.22), (0.15, 0.05), (-0.01, 0.015)], 40)
    path2 = bez([(-0.01, 0.015), (0.16, -0.01), (0.15, -0.21), (-0.06, -0.20)], 40)
    p = np.concatenate([path, path2[1:]])
    s.stroke(p, taper(len(p), [(0, 0.030), (0.2, 0.060), (0.5, 0.050), (0.8, 0.060), (1, 0.030)]), "line")


def m_cat(s):
    left = bez([(-0.40, 0.08), (-0.34, -0.08), (-0.06, -0.09), (0.0, 0.03)], 40)
    right = bez([(0.0, 0.03), (0.06, -0.09), (0.34, -0.08), (0.40, 0.08)], 40)
    p = np.concatenate([left, right[1:]])
    s.stroke(p, taper(len(p), [(0, 0.035), (0.25, 0.065), (0.5, 0.050), (0.75, 0.065), (1, 0.035)]), "line")


def m_wavy(s):
    x = np.linspace(-0.42, 0.42, 140)
    s.stroke(np.stack([x, 0.032 * np.sin((x + 0.42) / 0.84 * 2.5 * 2 * np.pi)], -1),
             taper(140, [(0, 0.040), (0.5, 0.058), (1, 0.040)]), "line")


MOUTH_PAINTERS = {
    "Neutral": m_neutral, "Smile": m_smile, "Frown": m_frown, "Smirk": m_smirk, "OpenSmall": m_open_small,
    "Open": m_open, "Laugh": m_laugh, "Grin": m_grin, "Teeth": m_teeth, "O": m_o, "Pout": m_pout, "Cat": m_cat,
    "Wavy": m_wavy,
}
assert set(MOUTH_PAINTERS) == set(fd.MOUTHS)


def paint_mouths():
    for name in fd.MOUTHS:
        s = Surface("mouth_" + name, (-1.0, 1.0), (-0.5, 0.5))
        MOUTH_PAINTERS[name](s)
        s.commit(0.5)


# ---------------------------------------------------------------- output
def downsample(img):
    h, w = img.shape[:2]
    return img.reshape(h // SS, SS, w // SS, SS, -1).mean(axis=(1, 3))


def to_u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def save_mouth_files(rgba):
    os.makedirs(os.path.join(OUT, "mouths"), exist_ok=True)
    for old in os.listdir(os.path.join(OUT, "mouths")):
        os.remove(os.path.join(OUT, "mouths", old))
    skin = np.array(DEFAULT_SKIN) / 255.0
    tiles = []
    font = ImageFont.load_default(size=18)
    for name in fd.MOUTHS:
        x0, y0, x1, y1 = fd.RECT["mouth_" + name]
        cell = rgba[y0:y1, x0:x1]
        Image.fromarray(to_u8(cell), "RGBA").save(os.path.join(OUT, "mouths", f"Mouth_{name}.png"))
        tile = Image.fromarray(to_u8(cell[..., :3] * cell[..., 3:] + skin * (1 - cell[..., 3:])), "RGB")
        ImageDraw.Draw(tile).text((8, 6), name, fill=(90, 60, 60), font=font)
        tiles.append(tile)
    cols = 5
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 256, rows * 128), DEFAULT_SKIN)
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * 256, (i // cols) * 128))
    os.makedirs(DOCS, exist_ok=True)
    sheet.save(os.path.join(DOCS, "mouths.png"))


def main():
    paint_iris()
    paint_sclera()
    paint_swatches()
    paint_blush()
    paint_mouths()
    # downsample with premultiplied alpha so overlay edges do not darken
    rgb, a = canvas[..., :3], canvas[..., 3:4]
    pm = downsample(np.concatenate([rgb * a, a], -1))
    plain = downsample(rgb)
    alpha = pm[..., 3:4]
    colr = np.where(alpha > 1e-4, pm[..., :3] / np.maximum(alpha, 1e-4), plain)
    rgba = np.concatenate([colr, alpha], -1)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(to_u8(rgba), "RGBA").save(os.path.join(OUT, "AnimeFace_Color.png"))
    skin = np.array(DEFAULT_SKIN) / 255.0
    Image.fromarray(to_u8(colr * alpha + skin * (1 - alpha)), "RGB").save(os.path.join(OUT, "AnimeFace_Color_Opaque.png"))
    Image.fromarray(to_u8(downsample(rough[..., None])[..., 0]), "L").save(os.path.join(OUT, "AnimeFace_Roughness.png"))
    save_mouth_files(rgba)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
