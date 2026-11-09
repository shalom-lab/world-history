"""Validate the generated dataset and write a report."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import json
import os
import re
import sys
from collections import Counter

DATA = str(ROOT / "data")
REPORT = str(ROOT / "build" / "validation_report.md")

YEAR_MIN, YEAR_MAX = -3100, 2000
HEX = re.compile(r"^#[0-9a-f]{6}$")


def load(n):
    with open(os.path.join(DATA, n), encoding="utf-8") as f:
        return json.load(f)


def main():
    meta, ents, spans, secs, leg = (load("meta.json"), load("entities.json"),
                                    load("spans.json"), load("sections.json"),
                                    load("legend.json"))
    errors, warnings, info = [], [], []

    ids = [e["id"] for e in ents]
    if len(ids) != len(set(ids)):
        errors.append("duplicate entity ids")
    sids = [s["id"] for s in spans]
    if len(sids) != len(set(sids)):
        errors.append("duplicate span ids")

    eids = set(ids)
    by_entity = {}
    for s in spans:
        by_entity.setdefault(s["entity_id"], []).append(s)
        if s["entity_id"] not in eids:
            errors.append(f'{s["id"]}: unknown entity {s["entity_id"]}')
        if not (YEAR_MIN <= s["start_year"] < s["end_year"] <= YEAR_MAX):
            errors.append(f'{s["id"]}: bad year range {s["start_year"]}..{s["end_year"]}')
        if not HEX.match(s.get("color_hex", "")):
            errors.append(f'{s["id"]}: bad colour {s.get("color_hex")}')

    prev_y = -1
    for e in ents:
        if not (e["y0"] < e["y1"]):
            errors.append(f'{e["id"]}: y0 >= y1')
        if e["y0"] < prev_y - 2:
            errors.append(f'{e["id"]}: rows out of y order')
        prev_y = e["y0"]
        ss = by_entity.get(e["id"], [])
        if not ss:
            errors.append(f'{e["id"]}: no spans')
            continue
        if e["start_year"] != min(s["start_year"] for s in ss):
            errors.append(f'{e["id"]}: start_year mismatch')
        if e["end_year"] != max(s["end_year"] for s in ss):
            errors.append(f'{e["id"]}: end_year mismatch')
        ss_sorted = sorted(ss, key=lambda s: s["x0"])
        for a, b in zip(ss_sorted, ss_sorted[1:]):
            if b["x0"] < a["x1"] - 2:
                warnings.append(f'{e["id"]}: overlapping spans {a["id"]}/{b["id"]}')
        if e["span_count"] != len(ss):
            errors.append(f'{e["id"]}: span_count mismatch')

    if meta["counts"]["entities"] != len(ents):
        errors.append("meta.counts.entities mismatch")
    if meta["counts"]["spans"] != len(spans):
        errors.append("meta.counts.spans mismatch")

    # content statistics
    named = [s for s in spans if s["label"]]
    info.append(f"entities: {len(ents)}")
    info.append(f"spans: {len(spans)} ({len(named)} with printed text, "
                f"{100*len(named)/max(1,len(spans)):.0f}%)")
    info.append(f"sections: {len(secs)} -> {', '.join(s['name'] for s in secs)}")
    fams = Counter(s["language_family"] for s in spans if s["language_family"])
    info.append("language families: " + ", ".join(f"{k} ({v})" for k, v in fams.most_common()))
    cat = Counter(e["category"] for e in ents)
    info.append("entity categories: " + ", ".join(f"{k} ({v})" for k, v in cat.most_common()))
    unnamed = [e["name"] for e in ents if e["name"] in ("Unnamed band", "")]
    if unnamed:
        warnings.append(f"{len(unnamed)} unnamed bands")
    long_spans = [s for s in spans if s["end_year"] - s["start_year"] > 2500]
    if long_spans:
        warnings.append(f"{len(long_spans)} spans longer than 2500 years")

    try:
        import schema_check
        schema_errs = schema_check.main()
    except SystemExit:
        schema_errs = []
    except Exception as exc:                      # pragma: no cover
        schema_errs = [f"schema check failed: {exc}"]
    for e in schema_errs:
        errors.append("schema: " + e)

    lines = ["# Dataset validation report", ""]
    lines += ["## Summary", ""] + [f"- {i}" for i in info] + [""]
    lines += ["## Errors", ""] + ([f"- {e}" for e in errors] or ["- none"]) + [""]
    lines += ["## Warnings", ""] + ([f"- {w}" for w in warnings] or ["- none"]) + [""]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", newline="\n", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
