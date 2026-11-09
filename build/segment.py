"""Colour-run segmenter: given a row's y-range, find the fill runs along x.

Text is dark and thin; fills are pale and wide. For every x column we take the
per-column median colour over the row's interior (median ignores text strokes and
vertical grid lines), then cut the row where that colour changes.
"""
import json

import numpy as np
from PIL import Image

SRC = r"D:\dsh\word-history\source.jpg"
_A = None

GRID_X0, GRID_PITCH = 60.0, 38.08


def arr():
    global _A
    if _A is None:
        _A = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32)
    return _A


def is_grid_column(x):
    k = round((x - GRID_X0) / (GRID_PITCH / 10.0))
    gx = GRID_X0 + k * GRID_PITCH / 10.0
    return abs(x - gx) < 0.8


def column_colors(y0, y1, x0, x1):
    """Median RGB per column inside the row interior."""
    a = arr()
    pad = max(1, (y1 - y0) // 5)
    top, bot = int(y0 + pad), int(y1 - pad) + 1
    if bot - top < 2:
        top, bot = int(y0), int(y1) + 1
    strip = a[top:bot, int(x0):int(x1)]
    # drop text pixels: those far darker than the strip's bright background
    lum = strip.mean(axis=2)
    thr = np.percentile(lum, 70) - 55
    mask = lum >= thr
    out = np.zeros((strip.shape[1], 3), dtype=np.float32)
    for i in range(strip.shape[1]):
        col = strip[:, i][mask[:, i]]
        out[i] = np.median(col, axis=0) if len(col) >= 2 else np.median(strip[:, i], axis=0)
    return out


def runs(y0, y1, x0, x1, thr=26, min_len=3):
    """Split a row into fill runs of near-constant colour."""
    cols = column_colors(y0, y1, x0, x1)
    n = len(cols)
    # smooth out single-column artefacts (grid lines, JPEG ringing)
    sm = cols.copy()
    for i in range(1, n - 1):
        sm[i] = np.median(cols[i - 1:i + 2], axis=0)

    cuts = [0]
    for i in range(1, n):
        d = np.abs(sm[i] - sm[i - 1]).max()
        if d > thr:
            cuts.append(i)
    cuts.append(n)

    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < min_len:
            continue
        seg = sm[a:b]
        med = np.median(seg, axis=0)
        out.append({"x0": int(x0 + a), "x1": int(x0 + b),
                    "rgb": [int(v) for v in med],
                    "hex": "#%02x%02x%02x" % tuple(int(v) for v in med)})
    # merge neighbours that are visually identical (split by noise)
    merged = []
    for s in out:
        if merged and max(abs(s["rgb"][k] - merged[-1]["rgb"][k]) for k in range(3)) < 14:
            m = merged[-1]
            m["x1"] = s["x1"]
            m["rgb"] = [int((m["rgb"][k] + s["rgb"][k]) / 2) for k in range(3)]
            m["hex"] = "#%02x%02x%02x" % tuple(m["rgb"])
        else:
            merged.append(s)
    return merged


def classify(rgb):
    r, g, b = [v / 255.0 for v in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    sat = 0.0 if mx == 0 else (mx - mn) / mx
    v = mx
    if sat < 0.10:
        if v > 0.94:
            return "white"
        if v > 0.82:
            return "lightgray"
        if v > 0.70:
            return "midgray"
        if v > 0.45:
            return "darkgray"
        return "black"
    # hue in degrees
    d = mx - mn
    if mx == r:
        h = (60 * ((g - b) / d)) % 360
    elif mx == g:
        h = 60 * ((b - r) / d) + 120
    else:
        h = 60 * ((r - g) / d) + 240
    if h < 12 or h >= 345:
        return "red"
    if h < 32:
        return "orange"
    if h < 55:
        return "yellow"
    if h < 72:
        return "olive"
    if h < 95:
        return "lime"
    if h < 155:
        return "green"
    if h < 175:
        return "teal"
    if h < 195:
        return "cyan"
    if h < 250:
        return "blue"
    if h < 285:
        return "purple"
    if h < 320:
        return "magenta"
    return "pink"


if __name__ == "__main__":
    import sys
    y0, y1, x0, x1 = [int(v) for v in sys.argv[1:5]]
    rs = runs(y0, y1, x0, x1)
    for r_ in rs:
        print(f"x {r_['x0']:5d}-{r_['x1']:5d} len={r_['x1']-r_['x0']:4d} {r_['hex']} {classify(r_['rgb'])}")
