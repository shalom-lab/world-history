"""Generate the full tile manifest for visual transcription."""
import json
import os
import subprocess
import sys

PY = sys.executable
TILER = r"D:\dsh\word-history\build\tiler.py"
OUT = r"D:\dsh\word-history\build\tiles"

XBANDS = [(30, 645, 3.0), (615, 1235, 3.0), (1205, 1645, 3.5), (1625, 2032, 3.5)]
YBANDS = [(60, 190), (190, 320), (320, 450), (450, 580), (580, 710),
          (710, 840), (840, 970), (970, 1100), (1100, 1230), (1230, 1360),
          (1360, 1490), (1490, 1620), (1620, 1750), (1750, 1880), (1880, 1990)]


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for r, (y0, y1) in enumerate(YBANDS):
        for c, (x0, x1, sc) in enumerate(XBANDS):
            tid = f"r{r:02d}c{c}"
            path = os.path.join(OUT, tid + ".png")
            subprocess.run([PY, TILER, "--box", str(x0), str(y0), str(x1), str(y1),
                            "--scale", str(int(round(sc))), "--out", path], check=True,
                           capture_output=True)
            manifest.append({"tile_id": tid, "path": path,
                             "box": [x0, y0, x1, y1], "scale": sc})
    with open(r"D:\dsh\word-history\build\tiles\manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print("tiles:", len(manifest))


if __name__ == "__main__":
    main()
