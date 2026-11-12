"""
Paint the AnimeFace texture atlas (run with system python3: needs numpy + Pillow).

Cel-shaded style: flat colours with hard, anti-aliased edges and bold dark linework.

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

PAL = {
    # eyes (an original amber palette)
    "iris_dark": "#4f2a10", "iris_middark": "#8a4c1a", "iris_mid": "#b9752b", "iris_light": "#efb75c",
    "iris_rim": "#27150a", "pupil": "#160c06",
    "sclera": "#ffffff", "sclera_shade": "#d2d7e6",
    "lash": "#1b1214", "brow": "#261b1e", "crease": "#c08573", "highlight": "#ffffff",
    "nose": "#b87262", "noseshade": "#ecc0aa",
    "blush": "#ff7f90", "blush_line": "#f0546c",
    # mouths
    "line": "#1f1215", "inner": "#4d1622", "tongue": "#e27a8a", "teeth": "#fbf8f8",
    "teeth_line": "#c4b4b9", "teeth_gap": "#6f565b",
}


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def lerp(a, b, t):
    t = np.asarray(t)[..., None]
    return a * (1 - t) + b * t


canvas = np.zeros((SIZE, SIZE, 4))
canvas[..., :3] = np.array(DEFAULT_SKIN) / 255.0
rough = np.full((SIZE, SIZE), 0.85)


def region(name):
    """Pixel-centre coordinates of a rect as (fx, fy) in the same space as fd.rect_uv (edge-extended)."""
    x0, y0, x1, y1 = fd.RECT[name]
    m = fd.UV_MARGIN
    xs = (np.arange(x0 * SS, x1 * SS) + 0.5) / SS
    ys = (np.arange(y0 * SS, y1 * SS) + 0.5) / SS
    FX, FY = np.meshgrid((xs - (x0 + m)) / (x1 - x0 - 2 * m), (ys - (y0 + m)) / (y1 - y0 - 2 * m))
    return (slice(y0 * SS, y1 * SS), slice(x0 * SS, x1 * SS)), FX, FY


def inner_px(name):
    """Inner width of a rect in canvas pixels."""
    x0, _, x1, _ = fd.RECT[name]
    return (x1 - x0 - 2 * fd.UV_MARGIN) * SS


SKIN_ROUGH = 0.85


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
        self.name = name
        self.sl, FX, FY = region(name)
        self.X = xr[0] + FX * (xr[1] - xr[0])
        self.Y = yr[1] - FY * (yr[1] - yr[0])
        self.px = (xr[1] - xr[0]) / inner_px(name)
        self.C = np.zeros(self.X.shape + (3,))
        self.A = np.zeros(self.X.shape)

    def cover(self, sd):
        """Anti-aliased coverage from a signed distance (negative inside)."""
        return np.clip(0.5 - sd / self.px, 0.0, 1.0)

    def over(self, color, cov):
        c = hexc(PAL.get(color, color))
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

    def outline(self, poly, width, color):
        poly = np.asarray(poly, float)
        self.stroke(np.concatenate([poly, poly[:1]]), width, color)

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


# ---------------------------------------------------------------- eyes
def paint_iris():
    s = Surface("iris", (-1 / 0.97, 1 / 0.97), (-1 / 0.97, 1 / 0.97))
    X, Y = s.X, s.Y
    full = np.ones_like(X)
    s.over("iris_mid", full)
    s.over("iris_light", s.cover(np.hypot(X, Y + 0.02) - 0.86) * s.cover(0.84 - np.hypot(X * 0.98, Y - 0.20)))
    s.over("iris_middark", s.cover((0.02 - 0.22 * X * X) - Y))
    s.over("iris_dark", s.cover((0.20 - 0.22 * X * X) - Y))
    s.over("pupil", s.cover((np.hypot(X / 0.29, (Y - 0.03) / 0.35) - 1.0) * 0.30))
    s.over("iris_rim", s.cover(0.885 - np.hypot(X, Y)))
    s.commit(0.35)


def paint_sclera():
    s = Surface("sclera", (-fd.SCLERA_UV[0], fd.SCLERA_UV[0]), (-fd.SCLERA_UV[1], fd.SCLERA_UV[1]))
    up = fd.bezier(fd.EYE_UPPER, 300)
    y_up = np.interp(s.X, up[:, 0], up[:, 1], left=up[0, 1], right=up[-1, 1])
    s.over("sclera", np.ones_like(s.X))
    s.over("sclera_shade", s.cover((y_up - 0.026) - s.Y))     # hard lid shadow under the upper lid
    s.commit(0.4)


def paint_swatches():
    for name in ("lash", "brow", "crease", "highlight", "nose", "noseshade"):
        put(name, hexc(PAL[name]), 1.0, 0.7 if name in ("lash", "brow") else 0.5)
    put("skin", np.array(DEFAULT_SKIN) / 255.0, 0.0, 0.85)
    sl, FX, FY = region("wall")
    p = np.clip(FX, 0, 1)
    a = fd.smoothstep(p / 0.035) * fd.smoothstep((0.5 - p) / 0.035) * (p <= 0.5)
    put("wall", hexc(PAL["lash"]), a, 0.7)


def paint_blush():
    hx, hy = fd.BLUSH_SIZE[0] / 2, fd.BLUSH_SIZE[1] / 2
    s = Surface("blush", (-hx, hx), (-hy, hy))
    d = np.hypot(s.X / hx, s.Y / hy)
    s.over("blush", 0.45 * (1 - fd.smoothstep((d - 0.3) / 0.7)))
    for cx in (-0.024, 0.0, 0.024):
        s.stroke([(cx - 0.006, -0.012), (cx + 0.006, 0.012)], 0.0042, "blush_line")
    s.commit(0.85)


# ---------------------------------------------------------------- mouths (sprite x in [-1, 1], y in [-0.5, 0.5])
def m_smile(s):
    s.stroke(bez([(-0.42, 0.10), (-0.20, -0.07), (0.20, -0.07), (0.42, 0.10)], 90),
             taper(90, [(0, 0.045), (0.5, 0.095), (1, 0.045)]), "line")


def m_neutral(s):
    s.stroke(bez([(-0.34, 0.012), (-0.12, -0.022), (0.12, -0.022), (0.34, 0.012)]),
             taper(80, [(0, 0.045), (0.5, 0.085), (1, 0.045)]), "line")


def m_frown(s):
    s.stroke(bez([(-0.34, -0.10), (-0.16, 0.075), (0.16, 0.075), (0.34, -0.10)]),
             taper(80, [(0, 0.055), (0.5, 0.10), (1, 0.055)]), "line")


def m_smirk(s):
    s.stroke(bez([(-0.36, -0.02), (-0.08, -0.07), (0.20, -0.05), (0.42, 0.11)], 90),
             taper(90, [(0, 0.040), (0.45, 0.085), (1, 0.095)]), "line")
    s.stroke(bez([(0.37, 0.20), (0.45, 0.17), (0.48, 0.11), (0.46, 0.05)], 20),
             taper(20, [(0, 0.012), (0.5, 0.032), (1, 0.012)]), "line")


def m_open_small(s):
    top = bez([(-0.30, 0.10), (-0.10, 0.065), (0.10, 0.065), (0.30, 0.10)], 50)
    poly = shape(top, bez([(0.30, 0.10), (0.25, -0.21), (-0.25, -0.21), (-0.30, 0.10)], 50))
    inside = s.fill(poly, "inner")
    s.fill(ellipse((0.02, -0.085), (0.13, 0.05)), "tongue", clip=inside)
    s.outline(poly, 0.07, "line")
    s.stroke(top, taper(50, [(0, 0.07), (0.5, 0.09), (1, 0.07)]), "line")


def m_open(s):
    top = bez([(-0.50, 0.15), (-0.22, 0.10), (0.22, 0.10), (0.50, 0.15)], 60)
    poly = shape(top, bez([(0.50, 0.15), (0.40, -0.49), (-0.40, -0.49), (-0.50, 0.15)], 60))
    inside = s.fill(poly, "inner")
    s.fill(ellipse((0.0, -0.255), (0.27, 0.12)), "tongue", clip=inside)
    s.outline(poly, 0.075, "line")
    s.stroke(top, taper(60, [(0, 0.085), (0.5, 0.10), (1, 0.085)]), "line")
    for k in (-1, 1):  # little upturned tips at the corners
        tip = bez([(0.50 * k, 0.15), (0.555 * k, 0.165), (0.60 * k, 0.20), (0.625 * k, 0.25)], 14)
        s.stroke(tip, taper(14, [(0, 0.08), (1, 0.018)]), "line")


def m_laugh(s):
    top = bez([(-0.66, 0.22), (-0.30, 0.15), (0.30, 0.15), (0.66, 0.22)], 70)
    poly = shape(top, bez([(0.66, 0.22), (0.56, -0.61), (-0.56, -0.61), (-0.66, 0.22)], 70))
    inside = s.fill(poly, "inner")
    s.fill(np.concatenate([top, (top - np.array([0.0, 0.09]))[::-1]]), "teeth", clip=inside)
    s.fill(ellipse((0.0, -0.335), (0.33, 0.12)), "tongue", clip=inside)
    s.outline(poly, 0.08, "line")
    s.stroke(top, taper(70, [(0, 0.09), (0.5, 0.105), (1, 0.09)]), "line")


def m_grin(s):
    top = bez([(-0.60, 0.20), (-0.30, 0.05), (0.30, 0.05), (0.60, 0.20)], 60)
    bot = bez([(0.60, 0.20), (0.44, -0.36), (-0.44, -0.36), (-0.60, 0.20)], 60)
    poly = shape(top, bot)
    inside = s.fill(poly, "teeth")
    s.fill(np.concatenate([bot, (bot + np.array([0.0, 0.075]))[::-1]]), "inner", clip=inside)
    s.outline(poly, 0.085, "line")


def m_teeth(s):
    poly = rounded_rect(-0.44, -0.12, 0.44, 0.12, 0.08)
    inside = s.fill(poly, "teeth")
    for x in (-0.22, 0.0, 0.22):
        s.stroke([(x, -0.13), (x, 0.13)], 0.012, "teeth_line", clip=inside)
    s.stroke([(-0.46, 0.0), (0.46, 0.0)], 0.022, "teeth_gap", clip=inside)
    s.outline(poly, 0.075, "line")


def m_o(s):
    poly = ellipse((0.0, -0.05), (0.19, 0.235))
    inside = s.fill(poly, "inner")
    s.fill(ellipse((0.0, -0.215), (0.12, 0.065)), "tongue", clip=inside)
    s.outline(poly, 0.08, "line")


def m_pout(s):
    poly = ellipse((0.0, -0.02), (0.095, 0.08))
    s.fill(poly, "inner")
    s.outline(poly, 0.065, "line")


def m_wavy(s):
    x = np.linspace(-0.38, 0.38, 140)
    s.stroke(np.stack([x, 0.032 * np.sin((x + 0.38) / 0.76 * 2.5 * 2 * np.pi)], -1), 0.06, "line")


MOUTH_PAINTERS = {
    "Smile": m_smile, "Neutral": m_neutral, "Frown": m_frown, "Smirk": m_smirk, "OpenSmall": m_open_small,
    "Open": m_open, "Laugh": m_laugh, "Grin": m_grin, "Teeth": m_teeth, "O": m_o, "Pout": m_pout, "Wavy": m_wavy,
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
    sheet = Image.new("RGB", (4 * 256, 3 * 128))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 4) * 256, (i // 4) * 128))
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
    col = np.where(alpha > 1e-4, pm[..., :3] / np.maximum(alpha, 1e-4), plain)
    rgba = np.concatenate([col, alpha], -1)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(to_u8(rgba), "RGBA").save(os.path.join(OUT, "AnimeFace_Color.png"))
    skin = np.array(DEFAULT_SKIN) / 255.0
    Image.fromarray(to_u8(col * alpha + skin * (1 - alpha)), "RGB").save(os.path.join(OUT, "AnimeFace_Color_Opaque.png"))
    Image.fromarray(to_u8(downsample(rough[..., None])[..., 0]), "L").save(os.path.join(OUT, "AnimeFace_Roughness.png"))
    save_mouth_files(rgba)
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
