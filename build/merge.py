"""Merge per-tile transcriptions into one row table (v2).

Tiles form a 15 x 4 grid. Rows are matched across columns against a reference
column (the one that transcribed the most rows in that y-band), then rows
clamped at a y-band edge are stitched by label + geometry.

Output: build/merged_rows.json
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import glob
import json
import os
import re
import statistics
from collections import Counter, defaultdict

LABELS = str(ROOT / "build" / "labels")
OUT = str(ROOT / "build" / "merged_rows.json")
TILE_MANIFEST = str(ROOT / "build" / "tiles" / "manifest.json")

X_LEFT, X_RIGHT = 30, 2032


def norm_label(s):
    if not s:
        return ""
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def key_label(s):
    return re.sub(r"[^a-z0-9]+", " ", norm_label(s).lower()).strip()


def load():
    man = {m["tile_id"]: m for m in json.load(open(TILE_MANIFEST, encoding="utf-8"))}
    tiles = {}
    for p in sorted(glob.glob(os.path.join(LABELS, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print("SKIP (bad json)", os.path.basename(p), e)
            continue
        tid = d.get("tile_id") or os.path.basename(p)[:-5]
        if tid not in man:
            print("SKIP (unknown tile id)", tid)
            continue
        d["_box"] = man[tid]["box"]
        tiles[tid] = d
    return tiles


def normalize_rows(tiles):
    out = []
    for tid, d in tiles.items():
        r_band, c_band = int(tid[1:3]), int(tid[4])
        bx0, by0, bx1, by1 = d["_box"]
        for row in d.get("rows", []):
            try:
                y0, y1 = int(row.get("y0")), int(row.get("y1"))
            except (TypeError, ValueError):
                continue
            if y1 < y0:
                y0, y1 = y1, y0
            y0 = max(y0, by0)
            y1 = min(y1, by1)
            if y1 - y0 < 4:
                continue
            segs = []
            for s in row.get("segments", []) or []:
                try:
                    x0, x1 = int(s.get("x0")), int(s.get("x1"))
                except (TypeError, ValueError):
                    continue
                if x1 < x0:
                    x0, x1 = x1, x0
                x0 = max(x0, bx0 + 2)
                x1 = min(x1, bx1 - 2)
                if x1 - x0 < 2:
                    continue
                segs.append({"x0": x0, "x1": x1,
                             "text": norm_label(s.get("text")),
                             "fill": (s.get("fill") or "").lower(),
                             "conf": (s.get("conf") or "medium").lower()})
            out.append({"tile": tid, "r": r_band, "c": c_band,
                        "box": [bx0, by0, bx1, by1],
                        "y0": y0, "y1": y1,
                        "label": norm_label(row.get("label")),
                        "confidence": (row.get("confidence") or "medium").lower(),
                        "segments": segs})
    return out


def overlap_frac(a, b):
    ov = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
    if ov <= 0:
        return 0.0
    return ov / max(1, min(a["y1"] - a["y0"], b["y1"] - b["y0"]))


def build_clusters(rows):
    """Group rows across columns for one y-band."""
    by_col = defaultdict(list)
    for r in rows:
        by_col[r["c"]].append(r)
    for c in by_col:
        by_col[c].sort(key=lambda r: r["y0"])

    ref_col = max(by_col, key=lambda c: (len(by_col[c]), -c))
    ref = by_col[ref_col]
    groups = [[r] for r in ref]
    leftover = []

    for c, rs in by_col.items():
        if c == ref_col:
            continue
        for r in rs:
            best_i, best_f = None, 0.0
            for i, g in enumerate(groups):
                # a group may hold at most one row from each column, otherwise a tall
                # reference row would swallow several thin rows of the same column
                if any(m["c"] == c for m in g):
                    continue
                f = max(overlap_frac(r, m) for m in g)
                if f > best_f:
                    best_i, best_f = i, f
            if best_f >= 0.35:
                groups[best_i].append(r)
            else:
                leftover.append(r)
    return groups + [[r] for r in leftover]


def resolve_segments(group):
    """Merge the per-column segment lists of one row into a coherent run list."""
    segs = []
    for r in group:
        core0, core1 = r["box"][0] + 4, r["box"][2] - 4
        for s in r["segments"]:
            a = max(s["x0"], core0)
            b = min(s["x1"], core1)
            if b - a < 3:
                a, b = s["x0"], s["x1"]
            segs.append(dict(s, x0=a, x1=b, tile=r["tile"], col=r["c"]))
    segs.sort(key=lambda s: (s["x0"], -(s["x1"] - s["x0"])))

    # column-wise coverage resolution
    n = X_RIGHT - X_LEFT
    owner = [None] * n
    for s in segs:
        for x in range(max(s["x0"], X_LEFT), min(s["x1"], X_RIGHT)):
            i = x - X_LEFT
            cur = owner[i]
            if cur is None:
                owner[i] = s
            elif (bool(s["text"]) and not cur["text"]):
                owner[i] = s

    runs = []
    for i, s in enumerate(owner):
        x = X_LEFT + i
        if s is None:
            s = {"x0": x, "x1": x + 1, "text": "", "fill": "", "conf": "", "tile": ""}
        if runs and runs[-1]["text"] == s["text"] and runs[-1]["fill"] == s["fill"] \
                and runs[-1]["x1"] == x:
            runs[-1]["x1"] = x + 1
        else:
            runs.append({"x0": x, "x1": x + 1, "text": s["text"], "fill": s["fill"],
                         "conf": s["conf"], "tile": s.get("tile", "")})
    return [r for r in runs if r["x1"] - r["x0"] >= 4]


def main():
    tiles = load()
    print("tiles loaded:", len(tiles))
    rows = normalize_rows(tiles)
    print("raw rows:", len(rows))

    by_band = defaultdict(list)
    for r in rows:
        by_band[r["r"]].append(r)

    clusters = []
    for band in sorted(by_band):
        for g in build_clusters(by_band[band]):
            # a bare "[?]" is a marker, not a name: do not let it outvote a real label
            labels = [r["label"] for r in g if key_label(r["label"])]
            # deterministic tie-break (set iteration order varies with hash seed)
            counts = Counter(labels)
            label = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if labels else ""
            y0 = statistics.median([r["y0"] for r in g])
            y1 = statistics.median([r["y1"] for r in g])
            confs = [r["confidence"] for r in g]
            clusters.append({
                "band": band,
                "y0": y0, "y1": y1,
                "label": label,
                "cols": sorted({r["c"] for r in g}),
                "confidence": min(confs, key=lambda c: {"high": 0, "medium": 1, "low": 2}.get(c, 3)),
                "segments": resolve_segments(g),
                "tiles": [r["tile"] for r in g],
            })
    clusters.sort(key=lambda c: c["y0"])

    # ---- stitch rows clamped at a y-band edge
    merged = []
    for cl in clusters:
        if merged:
            prev = merged[-1]
            gap = cl["y0"] - prev["y1"]
            same = key_label(prev["label"]) and key_label(prev["label"]) == key_label(cl["label"])
            # only stitch across a tile-band edge: inside one band the rows are
            # already complete, and joining them would swallow thin rows whole
            touching = abs(gap) <= 3 and prev["band"] != cl["band"]
            if touching and (same or not key_label(prev["label"]) or not key_label(cl["label"])) \
                    and (cl["y1"] - prev["y0"]) <= 48:
                prev["y1"] = max(prev["y1"], cl["y1"])
                prev["cols"] = sorted(set(prev["cols"]) | set(cl["cols"]))
                prev["tiles"] += cl["tiles"]
                prev["joined"] = True
                if not prev["label"]:
                    prev["label"] = cl["label"]
                if not prev["segments"]:
                    prev["segments"] = cl["segments"]
                continue
        merged.append(dict(cl))

    # ---- enforce monotonic, non-overlapping y intervals
    for i, m in enumerate(merged):
        m["y0"] = round(m["y0"], 1)
        m["y1"] = round(m["y1"], 1)
        if i and merged[i - 1]["y1"] > m["y0"]:
            mid = (merged[i - 1]["y0"] + m["y1"]) / 2
            if mid > merged[i - 1]["y0"] + 4 and mid < m["y1"] - 4:
                merged[i - 1]["y1"] = round(mid, 1)
                m["y0"] = round(mid, 1)
        m["row_index"] = i

    json.dump(merged, open(OUT, "w", newline="\n", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("merged rows:", len(merged))
    print("rows with label:", sum(1 for m in merged if m["label"]))
    print("rows with segments:", sum(1 for m in merged if m["segments"]))
    print("cols per row:", sorted({len(m["cols"]) for m in merged}))
    hs = sorted(m["y1"] - m["y0"] for m in merged)
    print("height min/median/max:", hs[0], hs[len(hs) // 2], hs[-1])


if __name__ == "__main__":
    main()
