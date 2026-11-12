"""
Paint the AnimeFace texture atlas (run with system python3: needs numpy + Pillow).

Outputs (in ../assets/textures):
  AnimeFace_Color.png         RGBA, for a SurfaceAppearance with AlphaMode = Overlay.
                              Transparent texels show the MeshPart's Color (the skin tone).
  AnimeFace_Color_Opaque.png  Same art with a default skin tone baked in (for MeshPart.TextureID).
  AnimeFace_Roughness.png     Optional roughness map (white = rough).
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import face_design as fd  # noqa: E402

SS = 2                      # supersampling factor
SIZE = fd.ATLAS * SS
OUT = os.path.join(HERE, "..", "assets", "textures")
DEFAULT_SKIN = (255, 226, 204)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def S(x):
    return fd.smoothstep(x)


def lerp(a, b, t):
    t = np.asarray(t)[..., None]
    return a * (1 - t) + b * t


def ramp(t, stops):
    """Piecewise-linear colour ramp; stops = [(pos, '#rrggbb'), ...]."""
    t = np.clip(t, 0, 1)
    pos = np.array([p for p, _ in stops])
    cols = np.array([hexc(c) for _, c in stops])
    return np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], -1)


canvas = np.zeros((SIZE, SIZE, 4))
canvas[..., :3] = np.array(DEFAULT_SKIN) / 255.0
rough = np.full((SIZE, SIZE), 0.85)


def region(name):
    """Pixel-centre coordinates of a rect as (fx, fy) in the same space as fd.rect_uv (edge-extended)."""
    x0, y0, x1, y1 = fd.RECT[name]
    m = fd.UV_MARGIN
    xs = (np.arange(x0 * SS, x1 * SS) + 0.5) / SS
    ys = (np.arange(y0 * SS, y1 * SS) + 0.5) / SS
    fx = (xs - (x0 + m)) / (x1 - x0 - 2 * m)
    fy = (ys - (y0 + m)) / (y1 - y0 - 2 * m)
    FX, FY = np.meshgrid(fx, fy)
    sl = (slice(y0 * SS, y1 * SS), slice(x0 * SS, x1 * SS))
    return sl, FX, FY


def put(name, rgb, alpha, r=None):
    sl, _, _ = region(name)
    canvas[sl][..., :3] = rgb
    canvas[sl][..., 3] = alpha
    if r is not None:
        rough[sl] = r


# ---------------------------------------------------------------- iris
def paint_iris():
    sl, FX, FY = region("iris")
    X = (FX - 0.5) / (0.5 * 0.97)
    Y = -(FY - 0.5) / (0.5 * 0.97)
    r = np.hypot(X, Y)
    ang = np.arctan2(Y, X)
    t = (Y + 1) / 2
    col = ramp(t, [(0.00, "#9be9ff"), (0.14, "#56c0ea"), (0.34, "#2f86cf"), (0.56, "#24539f"),
                   (0.78, "#1c2f70"), (1.00, "#141c4a")])
    # soft lid shadow over the top of the iris
    col = lerp(col, hexc("#0f1540"), 0.55 * S((Y - 0.05) / 0.75))
    # radial fibres, stronger in the lower half
    fib = 0.5 + 0.5 * np.sin(ang * 27 + 1.7 * np.sin(ang * 5.0) + 0.6 * np.sin(ang * 11.0))
    fib = fib ** 3 * S((r - 0.38) / 0.12) * (1 - S((r - 0.84) / 0.08))
    col = lerp(col, hexc("#7fd4ff"), 0.28 * fib * S((-Y + 0.35) / 0.9))
    col = lerp(col, hexc("#0f1a4a"), 0.22 * fib * S((Y + 0.1) / 0.6))
    # bright crescent of reflected light near the bottom
    cres = S((0.93 - np.hypot(X * 1.05, Y + 0.30)) / 0.10) * (1 - S((0.62 - np.hypot(X * 1.15, Y + 0.18)) / -0.12))
    cres *= S((-Y - 0.15) / 0.35)
    col = lerp(col, hexc("#c4f3ff"), 0.55 * np.clip(cres, 0, 1))
    # lighter collarette ring around the pupil
    ring = np.exp(-((r - 0.47) / 0.07) ** 2)
    col = lerp(col, hexc("#6aa6ee"), 0.30 * ring * (0.4 + 0.6 * S(-Y / 0.8 + 0.5)))
    # pupil (vertical oval) with a soft halo
    pr = np.hypot(X / 0.27, (Y - 0.03) / 0.37)
    col = lerp(col, hexc("#0b1032"), 0.55 * (1 - S((pr - 1.0) / 0.45)))
    col = lerp(col, hexc("#05071a"), 1 - S((pr - 0.96) / 0.06))
    # limbal ring + crisp outline
    col = lerp(col, hexc("#0c1238"), S((r - 0.80) / 0.14) * 0.85)
    col = lerp(col, hexc("#070a22"), S((r - 0.935) / 0.03))
    # tiny painted sparkles (the main highlights are geometry)
    for (sx, sy, sr, a) in ((0.42, -0.50, 0.050, 0.85), (0.55, -0.30, 0.030, 0.7), (-0.30, -0.62, 0.028, 0.6)):
        d = np.hypot(X - sx, Y - sy)
        col = lerp(col, hexc("#e9fbff"), a * (1 - S((d - sr * 0.4) / (sr * 0.8))))
    canvas[sl][..., :3] = col
    canvas[sl][..., 3] = 1.0
    rough[sl] = 0.32


# ---------------------------------------------------------------- sclera
def paint_sclera():
    sl, FX, FY = region("sclera")
    ex = (FX - 0.5) * 0.32
    ey = -(FY - 0.5) * 0.26
    up = fd.bezier(fd.EYE_UPPER, 200)
    y_up = np.interp(ex, up[:, 0], up[:, 1], left=up[0, 1], right=up[-1, 1])
    col = np.broadcast_to(hexc("#fcfdff"), ex.shape + (3,)).copy()
    shade = 0.75 * S((ey - (y_up - 0.040)) / 0.040)
    col = lerp(col, hexc("#c3cbe4"), shade)
    corner = S((np.abs(ex - 0.005) - 0.07) / 0.06)
    col = lerp(col, hexc("#d9dcea"), 0.45 * corner)
    put("sclera", col, 1.0, 0.40)


# ---------------------------------------------------------------- strokes
def stroke_swatch(name, inner, mid, outer, r):
    sl, FX, FY = region(name)
    col = ramp(FY, [(0.0, inner), (0.35, mid), (1.0, outer)])
    put(name, col, 1.0, r)


def paint_simple():
    stroke_swatch("lash", "#3a2230", "#160d16", "#0b070c", 0.70)
    stroke_swatch("brow", "#3a2a33", "#2a1e26", "#1f161d", 0.80)
    stroke_swatch("mouthline", "#5a2a31", "#47212a", "#3b1a21", 0.70)

    sl, FX, FY = region("cavity")
    col = ramp(FY, [(0.0, "#2c0a12"), (0.45, "#5c1a27"), (1.0, "#8e3442")])
    col = col * (0.72 + 0.28 * np.sin(np.pi * np.clip(FX, 0, 1)))[..., None]
    put("cavity", col, 1.0, 0.55)

    sl, FX, FY = region("teeth")
    col = ramp(FY, [(0.0, "#e2e7f2"), (0.25, "#ffffff"), (1.0, "#f3f6fc")])
    side = S((np.abs(FX - 0.5) - 0.32) / 0.18)
    col = lerp(col, hexc("#c9d1e2"), 0.6 * side)
    put("teeth", col, 1.0, 0.30)

    sl, FX, FY = region("tongue")
    col = ramp(FY, [(0.0, "#f08f9c"), (0.5, "#e2717f"), (1.0, "#c4566a")])
    groove = np.exp(-((FX - 0.5) / 0.035) ** 2) * S((FY - 0.30) / 0.25)
    col = lerp(col, hexc("#b0475a"), 0.65 * groove)
    hl = np.exp(-(((FX - 0.36) / 0.10) ** 2 + ((FY - 0.30) / 0.12) ** 2))
    col = lerp(col, hexc("#ffc3cb"), 0.55 * hl)
    put("tongue", col, 1.0, 0.40)

    put("highlight", hexc("#ffffff"), 1.0, 0.20)
    put("skin", np.array(DEFAULT_SKIN) / 255.0, 0.0, 0.85)


# ---------------------------------------------------------------- overlay (alpha) swatches
def paint_overlays():
    sl, FX, FY = region("crease")
    a = 0.55 * (1 - np.abs(2 * np.clip(FY, 0, 1) - 1) ** 1.6)
    a *= S(FX / 0.12) * S((1 - FX) / 0.12)
    put("crease", hexc("#94564c"), np.clip(a, 0, 1))

    sl, FX, FY = region("wall")
    p = np.clip(FX, 0, 1)
    a = S(p / 0.035) * S((0.5 - p) / 0.035) * (p <= 0.5)
    put("wall", hexc("#120a12"), a, 0.7)

    sl, FX, FY = region("nose")
    line = (FX <= 0.47) * (1 - np.abs(2 * np.clip(FY, 0, 1) - 1) ** 2.2) * 0.85
    bx = (FX - 0.775) / 0.225
    by = (FY - 0.5) / 0.5
    blob = (FX >= 0.53) * 0.20 * (1 - S((np.hypot(bx * 1.1, by) - 0.25) / 0.75))
    col = np.where((FX <= 0.5)[..., None], hexc("#9c584d"), hexc("#c0806f"))
    put("nose", col, np.clip(line + blob, 0, 1))

    sl, FX, FY = region("lipshadow")
    a = 0.38 * (1 - np.abs(2 * np.clip(FY, 0, 1) - 1) ** 1.5) * np.sin(np.pi * np.clip(FX, 0, 1)) ** 0.8
    put("lipshadow", hexc("#b8705f"), np.clip(a, 0, 1))

    sl, FX, FY = region("blush")
    X = (FX - 0.5) * 2
    Y = (FY - 0.5) * 2
    d = np.hypot(X * 1.0, Y * 1.05)
    a = 0.46 * (1 - S((d - 0.25) / 0.70))
    col = np.broadcast_to(hexc("#ff6f82"), X.shape + (3,)).copy()
    # three hatch strokes leaning the same way on both cheeks
    for cx in (-0.30, 0.0, 0.30):
        # line direction leans 25 degrees from vertical
        dx = (X - cx) + (Y * 0.47)
        w = np.exp(-(dx / 0.045) ** 2) * (1 - S((np.abs(Y) - 0.38) / 0.18))
        a = np.maximum(a, 0.70 * w)
        col = lerp(col, hexc("#f0475f"), np.clip(w, 0, 1))
    put("blush", col, np.clip(a, 0, 1))

    # soft shading painted straight onto the front of the head (no extra geometry).
    # Only paint where no overlay geometry (eye rings, blush) can cover it, or its edge would show.
    sl, FX, FY = region("facepaint")
    u = np.clip(FX, 0, 1) * 2 * fd.FACE_U - fd.FACE_U
    v = fd.FACE_V1 - np.clip(FY, 0, 1) * (fd.FACE_V1 - fd.FACE_V0)
    nose = 0.24 * (1 - S((np.hypot((u - fd.NOSE_U - 0.019) / 0.014, (v - fd.NOSE_V - 0.011) / 0.024) - 0.2) / 0.8))
    put("facepaint", hexc("#c27f6e"), np.clip(nose, 0, 1))


def downsample(img):
    h, w = img.shape[:2]
    return img.reshape(h // SS, SS, w // SS, SS, -1).mean(axis=(1, 3))


def main():
    paint_iris()
    paint_sclera()
    paint_simple()
    paint_overlays()
    # downsample with premultiplied alpha so overlay edges do not darken
    rgb, a = canvas[..., :3], canvas[..., 3:4]
    pm = downsample(np.concatenate([rgb * a, a], -1))
    plain = downsample(rgb)
    alpha = pm[..., 3:4]
    col = np.where(alpha > 1e-4, pm[..., :3] / np.maximum(alpha, 1e-4), plain)
    os.makedirs(OUT, exist_ok=True)
    rgba = np.concatenate([col, alpha], -1)
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(os.path.join(OUT, "AnimeFace_Color.png"))
    skin = np.array(DEFAULT_SKIN) / 255.0
    opaque = col * alpha + skin * (1 - alpha)
    Image.fromarray((np.clip(opaque, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(OUT, "AnimeFace_Color_Opaque.png"))
    r = downsample(rough[..., None])[..., 0]
    Image.fromarray((np.clip(r, 0, 1) * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(OUT, "AnimeFace_Roughness.png"))
    print("wrote", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
