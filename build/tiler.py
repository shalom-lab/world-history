"""Tile renderer: crop + upscale + coordinate frame, for visual transcription.

Every tile carries rulers in ORIGINAL image pixel coordinates, so annotations
returned by readers can be mapped back without ambiguity.

usage: python tiler.py --box x0 y0 x1 y1 --scale 3 --out tile.png
"""
import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

SRC = r"D:\dsh\word-history\source.jpg"
MLEFT, MTOP = 46, 26          # margins (display px)
GX, GY = 50, 20               # guide spacing in ORIGINAL px

# axis calibration (see build/calib notes)
X_ORIGIN, PITCH = 60.0, 38.08  # x of year -3100, px per century
YEAR0 = -3100


def year_of_x(x):
    return YEAR0 + (x - X_ORIGIN) * 100.0 / PITCH


def x_of_year(y):
    return X_ORIGIN + (y - YEAR0) * PITCH / 100.0


def render(box, scale=3, src=SRC):
    x0, y0, x1, y1 = box
    im = Image.open(src).convert("RGB").crop(box)
    w, h = im.size
    im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=170, threshold=2))
    im = ImageEnhance.Contrast(im).enhance(1.3)

    disp = Image.new("RGB", (int(w * scale) + MLEFT, int(h * scale) + MTOP), "white")
    disp.paste(im, (MLEFT, MTOP))
    dr = ImageDraw.Draw(disp, "RGBA")

    # vertical guides at multiples of GX (original coords), labelled
    gx = ((x0 // GX) + 1) * GX
    while gx < x1:
        dx = int(MLEFT + (gx - x0) * scale)
        strong = (gx % 100 == 0)
        dr.line([(dx, MTOP), (dx, MTOP + int(h * scale))],
                fill=(40, 90, 200, 90 if strong else 40), width=1)
        dr.text((dx + 1, 2), str(gx), fill=(0, 0, 0, 255))
        # year annotation every 500 y
        yr = year_of_x(gx)
        if abs((yr + 3100) % 500) < 60:
            dr.text((dx + 1, 12), f"{int(round(yr))}", fill=(180, 0, 0, 255))
        gx += GX

    # horizontal guides at multiples of GY
    gy = ((y0 // GY) + 1) * GY
    while gy < y1:
        dy = int(MTOP + (gy - y0) * scale)
        strong = (gy % 100 == 0)
        dr.line([(MLEFT, dy), (MLEFT + int(w * scale), dy)],
                fill=(200, 40, 140, 70 if strong else 30), width=1)
        dr.text((1, dy - 4), str(gy), fill=(0, 0, 0, 255))
        gy += GY

    return disp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--box", nargs=4, type=int, required=True)
    ap.add_argument("--scale", type=float, default=3)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    img = render(tuple(a.box), a.scale)
    img.save(a.out)
    print(json.dumps({"out": a.out, "size": img.size, "box": a.box, "scale": a.scale}))


if __name__ == "__main__":
    main()
