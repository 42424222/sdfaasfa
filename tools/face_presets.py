"""
Expression presets for the AnimeFace rig.

Each preset: {"sym": {base: (x, y, z)}, "bones": {name: (x, y, z)}, "mouth": name} in studs.
  x = outward along the skin for _L/_R bones (toward that ear), +X (character right) for centre bones
  y = up, z = out of the face.
  Irises (Iris_L/R) are look bones: x = travel along the head surface, y = up.
"sym" keys apply to both the _L and _R bone. "mouth" picks one of face_design.MOUTHS (2D images).

Closed-eye lid offsets are solved from the real skin weights so a blink fully closes the eye
whatever the eye shape constants are.
"""
import numpy as np

import face_design as fd

UPPER_BONES = ["LidUpperInner", "LidUpper", "LidUpperOuter"]


def _contours():
    """Both lid curves including their shared corner points, with their lid-bone weights."""
    up = fd.bezier(fd.EYE_UPPER, fd.N_UPPER)
    lo = fd.bezier(fd.EYE_LOWER, fd.N_LOWER)
    su = np.linspace(0, 1, len(up))
    sl = np.linspace(0, 1, len(lo))
    Wu = np.array([[fd.lid_weights(0, x).get(b, 0.0) for b in UPPER_BONES] for x in su])
    Wl = np.array([fd.lid_weights(1, x).get("LidLower", 0.0) for x in sl])
    return up, Wu, lo, Wl


def _interp_curve(ex, pts):
    order = np.argsort(pts[:, 0])
    return np.interp(ex, pts[order, 0], pts[order, 1])


def _solve(target_fn, overlap=0.0018, report=None):
    """Solve vertical lid offsets so both lids meet on target_fn(ex); returns (upper[3], lower)."""
    up_pts, Wu, lo_pts, Wl = _contours()
    ru = target_fn(up_pts[:, 0]) - up_pts[:, 1]
    rl = target_fn(lo_pts[:, 0]) - lo_pts[:, 1]
    lam = 1e-4
    du = np.linalg.solve(Wu.T @ Wu + lam * np.eye(3), Wu.T @ ru)
    dl = float(Wl @ rl / (Wl @ Wl + lam))
    # guarantee the upper lid ends at or below the lower lid everywhere away from the fixed corners
    grid = np.linspace(fd.EYE_INNER[0] + 0.006, fd.EYE_OUTER[0] - 0.006, 300)
    gap = 0.0
    for _ in range(60):
        yu = _interp_curve(grid, np.c_[up_pts[:, 0], up_pts[:, 1] + Wu @ du])
        yl = _interp_curve(grid, np.c_[lo_pts[:, 0], lo_pts[:, 1] + Wl * dl])
        gap = (yu - yl).max()
        if gap <= -overlap:
            break
        worst = grid[np.argmax(yu - yl)]
        # push only the bones that influence the worst spot
        s_w = np.interp(worst, up_pts[:, 0], np.linspace(0, 1, len(up_pts)))
        w = np.array([fd.lid_weights(0, s_w).get(b, 0.0) for b in UPPER_BONES])
        du = du - (gap + overlap) * w / max(w @ w, 1e-6) * 0.5
    if report is not None:
        report.append(float(gap))
    return du, dl


def _closed_target():
    up_pts, _, lo_pts, _ = _contours()

    def f(ex):
        return _interp_curve(ex, lo_pts) + 0.22 * (_interp_curve(ex, up_pts) - _interp_curve(ex, lo_pts))
    return f


def _happy_target(height=0.046):
    (ix, iy), (ox, oy) = fd.EYE_INNER, fd.EYE_OUTER

    def f(ex):
        t = (ex - ix) / (ox - ix)
        line = iy + (oy - iy) * t
        return line + height * np.clip(1 - (2 * t - 1) ** 2, 0, None) ** 0.7
    return f


def _lids(du, dl, k=1.0):
    d = {b: (0.0, float(v) * k, 0.0) for b, v in zip(UPPER_BONES, du)}
    d["LidLower"] = (0.0, float(dl) * k, 0.0)
    return d


SOLVE_GAPS = []
CLOSED_UP, CLOSED_LOW = _solve(_closed_target(), report=SOLVE_GAPS)
HAPPY_UP, HAPPY_LOW = _solve(_happy_target(), report=SOLVE_GAPS)

BLUSH = {"Blush": (0.0, 0.0, fd.BLUSH_SHOW)}


def merge(*parts):
    out = {"sym": {}, "bones": {}}
    for p in parts:
        for key in ("sym", "bones"):
            for name, val in p.get(key, {}).items():
                out[key][name] = tuple(val)
        if "mouth" in p:
            out["mouth"] = p["mouth"]
    return out


def sym(**kw):
    return {"sym": kw}


def bones(**kw):
    return {"bones": kw}


def mouth(name):
    assert name in fd.MOUTHS, name
    return {"mouth": name}


EYES_CLOSED = sym(**_lids(CLOSED_UP, CLOSED_LOW))
EYES_HAPPY = sym(**_lids(HAPPY_UP, HAPPY_LOW))
EYES_HALF = sym(**_lids(CLOSED_UP, CLOSED_LOW * 0.2, 0.45))
EYES_SOFT = sym(LidUpperInner=(0, -0.007, 0), LidUpper=(0, -0.011, 0), LidUpperOuter=(0, -0.007, 0), LidLower=(0, 0.026, 0))
EYES_WIDE = sym(LidUpperInner=(0, 0.026, 0), LidUpper=(0, 0.040, 0), LidUpperOuter=(0, 0.030, 0), LidLower=(0, -0.014, 0))

PRESETS = {
    "Neutral": {},
    "Blink": EYES_CLOSED,
    "Smile": merge(EYES_SOFT, sym(Brow=(0, 0.004, 0)), mouth("Smile")),
    "Happy": merge(EYES_HAPPY, sym(Brow=(0, 0.012, 0), BrowInner=(0, 0.005, 0)), mouth("Open")),
    "Laugh": merge(EYES_HAPPY, sym(Brow=(0, 0.016, 0), BrowInner=(0, 0.007, 0)), mouth("Laugh")),
    "Grin": merge(sym(LidLower=(0, 0.024, 0), LidUpper=(0, -0.006, 0), Brow=(0, 0.006, 0)), mouth("Grin")),
    "Angry": merge(sym(LidUpperInner=(0, -0.072, 0), LidUpper=(0, -0.040, 0), LidUpperOuter=(0, -0.006, 0), LidLower=(0, 0.017, 0),
                       Brow=(0, -0.016, 0), BrowInner=(-0.006, -0.028, 0), BrowOuter=(0, 0.009, 0)), mouth("Teeth")),
    "Sad": merge(sym(LidUpperInner=(0, 0.008, 0), LidUpper=(0, -0.017, 0), LidUpperOuter=(0, -0.058, 0), LidLower=(0, 0.006, 0),
                     Brow=(0, 0.006, 0), BrowInner=(-0.004, 0.030, 0), BrowOuter=(0, -0.012, 0), Iris=(0, -0.010, 0)),
                 mouth("Frown")),
    "Surprised": merge(EYES_WIDE, sym(Brow=(0, 0.032, 0), BrowInner=(0, 0.006, 0)), mouth("OpenSmall")),
    "Shocked": merge(EYES_WIDE, sym(Brow=(0, 0.044, 0), BrowInner=(0, 0.010, 0)), mouth("O")),
    "Sleepy": merge(EYES_HALF, sym(Brow=(0, -0.004, 0), BrowOuter=(0, -0.006, 0), Iris=(0, -0.016, 0)), mouth("Neutral")),
    # the smirk image rises on the viewer's right = the character's left, so the mouth shifts left (-X)
    "Smug": merge(sym(**_lids(CLOSED_UP, CLOSED_LOW * 0.1, 0.32)),
                  bones(Brow_L=(0, 0.015, 0), BrowInner_L=(0, 0.004, 0), Brow_R=(0, -0.006, 0), BrowInner_R=(0, -0.006, 0),
                        Mouth=(-0.016, 0.004, 0), Iris_L=(0.040, 0, 0), Iris_R=(-0.040, 0, 0)),
                  mouth("Smirk")),
    "Determined": merge(sym(LidUpperInner=(0, -0.034, 0), LidUpper=(0, -0.017, 0), LidLower=(0, 0.020, 0),
                            Brow=(0, -0.010, 0), BrowInner=(-0.004, -0.015, 0), BrowOuter=(0, 0.004, 0)),
                        mouth("Neutral")),
    "Serious": merge(sym(LidUpper=(0, -0.012, 0), LidLower=(0, 0.010, 0), Brow=(0, -0.005, 0), BrowInner=(0, -0.006, 0)),
                     mouth("Neutral")),
    "Shy": merge(sym(**_lids(CLOSED_UP, CLOSED_LOW * 0.2, 0.18)), sym(Brow=(0, 0.009, 0), BrowInner=(0, 0.012, 0)),
                 sym(**BLUSH), bones(Iris_L=(-0.048, -0.020, 0), Iris_R=(0.048, -0.020, 0)), mouth("Wavy")),
    "Nervous": merge(sym(Brow=(0, 0.012, 0), BrowInner=(0, 0.018, 0), BrowOuter=(0, -0.005, 0), LidLower=(0, 0.005, 0)),
                     bones(Iris_L=(0.022, 0, 0), Iris_R=(-0.022, 0, 0)), mouth("Wavy")),
    "Playful": merge(EYES_SOFT, sym(Brow=(0, 0.008, 0), BrowOuter=(0, 0.004, 0)), mouth("Cat")),
    "Wink": merge(bones(**{f"{k}_L": v for k, v in _lids(HAPPY_UP, HAPPY_LOW).items()}),
                  bones(Brow_L=(0, -0.004, 0), Brow_R=(0, 0.009, 0)), mouth("Grin")),
    "Pout": merge(sym(Brow=(0, 0.004, 0), BrowInner=(0, 0.010, 0), LidUpper=(0, -0.012, 0)), mouth("Pout")),
    "Blush": sym(**BLUSH),
    "LookLeft": bones(Iris_L=(0.085, 0, 0), Iris_R=(-0.085, 0, 0)),
    "LookRight": bones(Iris_L=(-0.085, 0, 0), Iris_R=(0.085, 0, 0)),
    "LookUp": sym(Iris=(0, 0.026, 0), LidUpper=(0, 0.008, 0), Brow=(0, 0.006, 0)),
    "LookDown": sym(Iris=(0, -0.030, 0), LidUpperInner=(0, -0.014, 0), LidUpper=(0, -0.020, 0), LidUpperOuter=(0, -0.014, 0)),
}

# Expressions whose eyes are already closed or squeezed: no automatic blinking on top.
NO_BLINK = {"Blink", "Happy", "Laugh", "Wink"}

# 2D mouth images the controller flips through while talking (relative weights), with the
# expression's own mouth shown between syllables.
TALK_MOUTHS = {"OpenSmall": 0.40, "Open": 0.30, "O": 0.15, "Teeth": 0.15}

# Eye-look range used by the controller (studs of iris travel at full deflection).
LOOK_RANGE = (0.085, 0.030)
