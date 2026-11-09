"""Refine merged rows into spans (v2).

The tile transcription supplies each band's y-extent and printed text; the raster
supplies the exact horizontal extent of every coloured block.  Runs are converted
to years with the calibrated axis.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import json

import numpy as np

import segment

X_LEFT, X_RIGHT = 42, 2008
MERGED = str(ROOT / "build" / "merged_rows.json")
OUT = str(ROOT / "build" / "refined.json")

# The printed colour-key box is an opaque white sticker over the artwork.
LEGEND_BOX = (118, 162, 590, 352)

LEGEND = str(ROOT / "build" / "legend.json")


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


def load_palette():
    """(name, family, subgroup, rgb) for every swatch in the printed colour key."""
    out = []
    leg = json.load(open(LEGEND, encoding="utf-8"))
    for fam in leg["families"]:
        for sg in fam["subgroups"]:
            for lang in sg["languages"]:
                rgb = lang["rgb"]
                if min(rgb) > 240:          # bad sample of a white sliver
                    continue
                out.append((lang["name"], fam["name"], sg["name"], hex2rgb(lang["hex"])))
    return out


_PAL = None


def load_palette():
    """(language, family, rgb) for every swatch of the printed colour key."""
    global _PAL
    if _PAL is None:
        leg = json.load(open(LEGEND, encoding="utf-8"))
        out = []
        for fam in leg["families"]:
            for sg in fam["subgroups"]:
                for lang in sg["languages"]:
                    if min(lang["rgb"]) > 240:
                        continue
                    out.append((lang["name"], fam["name"], np.array(lang["rgb"], dtype=float)))
        _PAL = out
    return _PAL


def nearest_family(rgb):
    """Nearest printed swatch colour; returns (language, family, alt, distance)."""
    pal = load_palette()
    v = np.array(rgb, dtype=float)
    ds = sorted((float(np.abs(v - c).max()), name, fam) for name, fam, c in pal)
    return ds[0][1], ds[0][2], ds[1][1], ds[0][0]


def sample_y(y0, y1):
    """Vertical window used to sample the row's fills."""
    h = y1 - y0
    if h <= 14:
        return y0 + 2, y1 - 2
    mid = (y0 + y1) / 2
    return int(mid - 5), int(mid + 5)


def edge_scores():
    """Per-y score of a full-width horizontal colour step (row separators)."""
    global _EDGE
    if _EDGE is None:
        a = segment.arr()
        sub = a[2:, 42:2008]
        d = np.abs(sub[1:] - sub[:-1]).max(axis=2)
        _EDGE = (d > 18).mean(axis=1)
        _EDGE = np.concatenate([[0.0], _EDGE])
    return _EDGE


_EDGE = None


def snap(y, lo, hi, threshold=0.45):
    """Snap a row boundary to the strongest horizontal colour step nearby."""
    e = edge_scores()
    lo, hi = max(int(lo), 2), min(int(hi), len(e) - 2)
    if hi <= lo:
        return y
    seg = e[lo:hi + 1]
    k = int(np.argmax(seg))
    if seg[k] >= threshold:
        return lo + k
    # a uniform full-width gap is an equally good boundary marker
    uniform = np.where(seg < 0.06)[0]
    if len(uniform):
        return lo + int(uniform[len(uniform) // 2])
    return y


def merge_adjacent(spans):
    out = []
    for s in spans:
        if out:
            p = out[-1]
            same_colour = max(abs(s["rgb"][k] - p["rgb"][k]) for k in range(3)) < 16
            if same_colour and not s.get("text") and not p.get("text") and p["x1"] == s["x0"]:
                p["x1"] = s["x1"]
                continue
            if (p.get("fill_class") == s.get("fill_class") and p.get("fill_class")
                    and not s.get("text") and not p.get("text")):
                p["x1"] = s["x1"]
                continue
        out.append(dict(s))
    return out


def build():
    rows = json.load(open(MERGED, encoding="utf-8"))
    out = []
    prev_y1 = None
    for r in rows:
        y0, y1 = int(round(r["y0"])), int(round(r["y1"]))
        # snap both edges to the strongest nearby horizontal step / uniform gap
        ys0 = snap(y0, y0 - 5, y0 + 5)
        ys1 = snap(y1, y1 - 5, y1 + 5)
        if ys1 - ys0 >= 5:
            y0, y1 = ys0, ys1
        if prev_y1 is not None and y0 < prev_y1:
            y0 = prev_y1
        if y1 - y0 < 4:
            continue
        prev_y1 = y1
        sy0, sy1 = sample_y(y0, y1)
        runs = segment.runs(sy0, sy1, X_LEFT, X_RIGHT, thr=30, min_len=5)
        runs = merge_adjacent(runs)
        for run in runs:
            run["texts"] = []
        for s in r.get("segments", []):
            if not s.get("text"):
                continue
            best_ov, best = 0, None
            for run in runs:
                ov = min(s["x1"], run["x1"]) - max(s["x0"], run["x0"])
                if ov > best_ov:
                    best_ov, best = ov, run
            if best is not None and best_ov >= 8:
                best["texts"].append((s["x0"], s["x1"], s["text"]))

        # a wide fill can hold several printed names (one mosaic block, several
        # dynasties); split it at the gaps between those names
        split = []
        for run in runs:
            ts = sorted(run["texts"])
            if len(ts) < 2:
                if ts and not run.get("text"):
                    run["text"] = ts[0][2]
                split.append(run)
                continue
            cuts = [run["x0"]]
            for a, b in zip(ts, ts[1:]):
                cuts.append(int((a[1] + b[0]) / 2))
            cuts.append(run["x1"])
            for i in range(len(cuts) - 1):
                if cuts[i + 1] - cuts[i] < 3:
                    continue
                piece = dict(run, x0=cuts[i], x1=cuts[i + 1], text=ts[min(i, len(ts) - 1)][2])
                piece.pop("texts", None)
                split.append(piece)
        runs = split

        spans = []
        for run in runs:
            cls = segment.classify(run["rgb"])
            text = run.get("text", "")
            if run["x1"] - run["x0"] < 6:
                continue
            if cls == "white" and not text:
                continue
            if cls == "lightgray" and not text and run["rgb"][0] > 246:
                continue
            rgb = run["rgb"]
            sat = (max(rgb) - min(rgb)) / max(max(rgb), 1)
            lang, fam, alt, dist = nearest_family(rgb)
            if sat < 0.25 or dist > 46:
                fam = None
            if dist <= 18 and sat >= 0.35:
                conf = "high"
            elif dist <= 32 and sat >= 0.25:
                conf = "medium"
            elif fam is None:
                conf = "none"
            else:
                conf = "low"
            spans.append({
                "x0": run["x0"], "x1": run["x1"],
                "rgb": run["rgb"],
                "color_hex": run["hex"],
                "fill_class": cls,
                "text": text,
                "language": lang if conf in ("high", "medium") else None,
                "language_family": fam,
                "language_family_alt": alt,
                "color_distance": round(float(dist), 1),
                "color_confidence": conf,
            })

        # drop the region hidden behind the printed legend box
        lx0, ly0, lx1, ly1 = LEGEND_BOX
        occluded = y1 > ly0 and y0 < ly1
        out.append({"row_index": r["row_index"], "y0": y0, "y1": y1,
                    "label": r.get("label", ""), "spans": spans,
                    "occluded": occluded,
                    "label_confidence": r.get("confidence", "medium"),
                    "columns": r.get("cols", [])})

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tot = sum(len(o["spans"]) for o in out)
    print(f"rows {len(out)}  spans {tot}  spans/row {tot/max(1,len(out)):.1f}")
    print("rows without spans:", sum(1 for o in out if not o["spans"]))


if __name__ == "__main__":
    build()
