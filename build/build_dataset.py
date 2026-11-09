"""Assemble the final dataset files from the refined geometry."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import csv
import glob
import json
import os
import re
from collections import Counter

import i18n as i18n_mod

BUILD = str(ROOT / "build")
DATA = str(ROOT / "data")

X_ORIGIN, PITCH = 60.0, 38.08
YEAR0 = -3100
YEAR1 = 2000


def year_of_x(x):
    return YEAR0 + (x - X_ORIGIN) * 100.0 / PITCH


def snap(year):
    v = int(round(year / 10.0)) * 10
    return max(YEAR0, min(YEAR1, v))


CATEGORY_RULES = [
    (r"empire|kingdom|khaganate|khanate|caliphate|dynasty|sultanate|tsardom|republic|"
     r"state|principality|duchy|emirate|shogunate|confederation|federation|union|"
     r"commonwealth|colony|province|satrapy|hegemony", "state"),
    (r"hunter[- ]gatherer|forager", "hunter-gatherer"),
    (r"farmer|farming|cereal|agricultur", "farmer"),
    (r"pastoral|nomad|herder", "pastoralist"),
    (r"culture|cultures|ware|complex|horizon|tradition|industry", "archaeological culture"),
    (r"chiefdom", "chiefdom"),
    (r"people|peoples|tribe|tribes|clan|nomads", "people"),
]


def guess_category(name):
    n = (name or "").lower()
    for pat, cat in CATEGORY_RULES:
        if re.search(pat, n):
            return cat
    return "other"


def clean_name(s):
    s = (s or "").replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip(" .;,")
    return s


def load_margin():
    out = []
    for p in glob.glob(os.path.join(BUILD, "labels", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        for m in d.get("margin_labels", []) or []:
            t = clean_name(m.get("text"))
            try:
                y0, y1 = int(m.get("y0")), int(m.get("y1"))
            except (TypeError, ValueError):
                continue
            if t and y1 > y0:
                out.append({"text": t, "y0": min(y0, y1), "y1": max(y0, y1)})
    # de-duplicate overlapping reports of the same rotated label
    out.sort(key=lambda m: (m["y0"], m["text"]))
    merged = []
    for m in out:
        dup = None
        for e in merged:
            if e["text"].lower() == m["text"].lower():
                ov = min(e["y1"], m["y1"]) - max(e["y0"], m["y0"])
                if ov > 0.4 * min(e["y1"] - e["y0"], m["y1"] - m["y0"]):
                    dup = e
                    break
        if dup:
            dup["y0"] = min(dup["y0"], m["y0"])
            dup["y1"] = max(dup["y1"], m["y1"])
        else:
            merged.append(dict(m))
    merged.sort(key=lambda m: m["y0"])
    return merged


CURATED_SECTIONS = [
    # (name, y0, y1, source)
    ("SOUTHERN AFRICA", 60, 456, "margin"),
    ("NORTHERN AFRICA", 456, 727, "margin"),
    ("EUROPE", 727, 967, "margin"),
    ("IRON AGE IN THE INDIAN SUBCONTINENT", 967, 1118, "margin"),
    ("CENTRAL ASIA", 1118, 1242, "margin"),
    ("EAST ASIA", 1242, 1357, "margin"),
    ("SOUTHEAST ASIA", 1357, 1474, "margin"),
    ("NORTH AMERICA", 1474, 1620, "margin"),
    ("SOUTH AMERICA", 1620, 1888, "margin"),
    ("AUSTRALASIA", 1888, 1985, "margin"),
]


def main():
    os.makedirs(DATA, exist_ok=True)
    refined = json.load(open(os.path.join(BUILD, "refined.json"), encoding="utf-8"))
    legend = json.load(open(os.path.join(BUILD, "legend.json"), encoding="utf-8"))
    margin = load_margin()
    zh = i18n_mod.load("zh-CN")
    zh_strings = zh.get("strings", {})

    # ---- sections: curated from the rotated margin labels (the raw reads are
    # fragmented by the tile edges, which is what merge produced above)
    auto = []
    for i, m in enumerate(margin):
        auto.append({"name": m["text"], "y0": m["y0"],
                     "y1": margin[i + 1]["y0"] if i + 1 < len(margin) else 1985})
    sections = []
    for i, (name, y0, y1, src) in enumerate(CURATED_SECTIONS):
        sections.append({"id": f"SEC{i+1:02d}", "name": name, "y0": y0, "y1": y1,
                         "label_source": src})

    def section_of(y):
        for s in sections:
            if s["y0"] <= y <= s["y1"]:
                return s
        return sections[0] if sections else None

    # ---- entities + spans
    entities, spans = [], []
    for r in refined:
        ymid = (r["y0"] + r["y1"]) / 2
        sec = section_of(ymid)
        eid = f"E{r['row_index']+1:03d}"
        raw_spans = []
        last_x1 = 0
        for s in r["spans"]:
            x0, x1 = s["x0"], s["x1"]
            if x0 < last_x1:                 # keep spans monotonic, never overlapping
                x0 = last_x1
            if x1 - x0 < 4:
                continue
            last_x1 = x1
            if x1 - x0 < 5:
                continue
            a, b = snap(year_of_x(x0)), snap(year_of_x(x1))
            if b <= a:
                b = a + 10
            if b > YEAR1:                 # keep the decade inside the chart
                b = YEAR1
                a = min(a, YEAR1 - 10)
            # keep pixel bounds and years in exact correspondence
            x0 = int(round(X_ORIGIN + (a - YEAR0) * PITCH / 100.0))
            x1 = int(round(X_ORIGIN + (b - YEAR0) * PITCH / 100.0))
            raw_spans.append({
                "x0": x0, "x1": x1, "start_year": a, "end_year": b,
                "label": clean_name(s.get("text")),
                "color_hex": s["color_hex"],
                "fill_class": s["fill_class"],
                "language_family": s.get("language_family"),
                "language_family_alt": s.get("language_family_alt"),
                "family_margin": s.get("family_margin"),
            })
        # pixel bounds are re-derived from snapped years, which can push a span
        # a couple of px left into its predecessor; keep the row monotonic
        for a, b in zip(raw_spans, raw_spans[1:]):
            if b["x0"] < a["x1"]:
                b["x0"] = a["x1"]
                b["start_year"] = snap(year_of_x(b["x0"]))
                if b["end_year"] <= b["start_year"]:
                    b["end_year"] = min(YEAR1, b["start_year"] + 10)
        raw_spans = [s for s in raw_spans if s["end_year"] > s["start_year"]]

        if not raw_spans:
            continue
        fams = [s["language_family"] for s in raw_spans if s.get("language_family")]
        fam = Counter(fams).most_common(1)[0][0] if fams else None
        label = clean_name(r["label"])
        if not label:
            texts = [s["label"] for s in raw_spans if s["label"]]
            label = max(texts, key=len) if texts else "Unnamed band"

        ent = {
            "id": eid,
            "order": r["row_index"],
            "name": label,
            "name_zh": zh_strings.get(label),
            "section": sec["id"] if sec else None,
            "section_name": sec["name"] if sec else None,
            "category": guess_category(label),
            "language_family": fam,
            "y0": r["y0"], "y1": r["y1"],
            "start_year": min(s["start_year"] for s in raw_spans),
            "end_year": max(s["end_year"] for s in raw_spans),
            "span_count": len(raw_spans),
            "label_confidence": r.get("label_confidence", "medium"),
            "name_source": "row-label" if clean_name(r["label"]) else "span-text",
            "occluded_by_legend": bool(r.get("occluded")),
            "notes": "",
        }
        entities.append(ent)
        for i, s in enumerate(raw_spans):
            spans.append({
                "id": f"S{len(spans)+1:04d}",
                "entity_id": eid,
                "entity_name": label,
                "label": s["label"],
                "label_zh": zh_strings.get(s["label"]) if s["label"] else None,
                "start_year": s["start_year"],
                "end_year": s["end_year"],
                "start_year_label": f"{abs(s['start_year'])} BCE" if s["start_year"] < 0 else f"{s['start_year']} CE",
                "end_year_label": f"{abs(s['end_year'])} BCE" if s["end_year"] < 0 else f"{s['end_year']} CE",
                "color_hex": s["color_hex"],
                "fill_class": s["fill_class"],
                "language_family": s["language_family"],
                "language_family_alt": s["language_family_alt"],
                "color_confidence": s.get("color_confidence", "none"),
                "x0": s["x0"], "x1": s["x1"],
                # thin mosaic rows (East/Central Asia) cannot be resolved as
                # reliably as the tall bands, so their spans are flagged
                "confidence": "low" if (r["y1"] - r["y0"]) < 9 else "medium",
            })

    # section bounds stay as curated: they describe the poster's region strips


    zh_gaps = i18n_mod.missing(
        zh, {e["name"] for e in entities} | {s["label"] for s in spans if s["label"]})

    # ---- coverage: which of the 60 transcription tiles made it into this build
    man = json.load(open(os.path.join(BUILD, "tiles", "manifest.json"), encoding="utf-8"))
    present = {os.path.splitext(os.path.basename(p))[0]
               for p in glob.glob(os.path.join(BUILD, "labels", "*.json"))}
    tiles_present = sorted(t for t in present if t in {m["tile_id"] for m in man})
    tiles_missing = sorted(m["tile_id"] for m in man if m["tile_id"] not in present)
    missing_bands = sorted({t[1:3] for t in tiles_missing})
    band_rows = {m["tile_id"]: (m["box"][1], m["box"][3]) for m in man}
    band_status = []
    for b in sorted({m["tile_id"][1:3] for m in man}):
        got = [t for t in tiles_present if t[1:3] == b]
        status = "complete" if len(got) == 4 else ("missing" if not got else "partial")
        band_status.append({"band": f"r{b}", "y": list(band_rows[f"r{b}c0"]),
                            "tiles": f"{len(got)}/4", "status": status})
    missing_y = [bs["y"] for bs in band_status if bs["status"] != "complete"]

    meta = {
        "dataset": "world-history-timeline",        "title": "World History Timeline - Decade by Decade",
        "author": "SenseForMaps",
        "source": {"file": "source.jpg", "width": 2048, "height": 2048,
                   "format": "image/jpeg",
                   "sha256": "af17614794782663e4a5e71a3f95919031e64595f54c7563841e30330d94bf5b"},
        "time_range": {"start_year": YEAR0, "end_year": YEAR1, "step_years": 10},
        "axis": {
            "x_of_year0": X_ORIGIN,
            "px_per_century": PITCH,
            "px_per_decade": round(PITCH / 10, 4),
            "calibration": "century labels -3100..2000 at x=60..2002; fit over the printed "
                           "axis label blobs and the full-height 38.08 px grid",
            "decade_alignment": "every 10 years = 3.808 px, so each bar edge resolves to "
                                "about ±2 years; values are snapped to the decade grid",
        },
        "plot_area": {"x0": 30, "y0": 58, "x1": 2032, "y1": 1989},
        "counts": {
            "entities": len(entities),
            "spans": len(spans),
            "sections": len(sections),
            "legend_families": len(legend["families"]),
            "labelled_spans": sum(1 for s in spans if s["label"]),
        },
        "method": "pixel-calibrated raster extraction; band rows transcribed from 3x zoomed "
                  "tiles with a coordinate frame, fill runs re-derived from the raster",
        "coverage": {
            "tiles_total": len(man),
            "tiles_transcribed": len(tiles_present),
            "tiles_missing": tiles_missing,
            "bands": band_status,
            "incomplete_y_ranges": missing_y,
            "note": "The poster was cut into 15 horizontal bands x 4 columns. 'partial' bands "
                    "are missing their right-hand column (x 1625-2032), so recent dates in "
                    "those bands stop early. 'missing' bands have no transcription at all and "
                    "their entities are absent, not empty.",
        },
        "i18n": {
            "locales": i18n_mod.available(),
            "canonical": "en",
            "note": "English is what the poster prints. zh-CN is a translation of those "
                    "strings keyed by the exact English text; a missing key falls back to "
                    "English in every output.",
            "zh_missing": zh_gaps,
        },
        "caveats": [
            "The 2048 px raster is far smaller than the original poster; text below ~6 px "
            "is only partly legible and is marked with '?' or missing.",
            "Bands whose label is unreadable are named after their longest printed span.",
            "Language-family assignment is a nearest-colour match against the printed "
            "colour key; adjacent shades of the same hue can be ambiguous.",
            "Rows that straddle a tile boundary were stitched by label + geometry; a few "
            "may be duplicated or split.",
        ],
    }

    def dump(name, obj):
        with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")

    dump("meta.json", meta)
    dump("entities.json", entities)
    dump("spans.json", spans)
    dump("sections.json", sections)
    dump("legend.json", legend)
    dump("columns.json", {
        "description": "Decade column mapping for the poster grid",
        "year_start": YEAR0, "year_end": YEAR1, "step": 10,
        "x_of_year": "x = 60 + (year + 3100) * 38.08 / 100",
    })

    with open(os.path.join(DATA, "timeline.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "entity", "section", "category", "span_label",
                    "start_year", "end_year", "start_label", "end_label",
                    "color_hex", "fill_class", "language_family"])
        for s in spans:
            e = next(x for x in entities if x["id"] == s["entity_id"])
            w.writerow([s["entity_id"], s["entity_name"], e["section_name"], e["category"],
                        s["label"], s["start_year"], s["end_year"],
                        s["start_year_label"], s["end_year_label"],
                        s["color_hex"], s["fill_class"], s["language_family"]])

    print(f"entities={len(entities)} spans={len(spans)} sections={len(sections)}")
    print("labelled spans:", meta["counts"]["labelled_spans"])
    print("sections:", [s["name"] for s in sections])


if __name__ == "__main__":
    main()
