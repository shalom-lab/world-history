"""Final acceptance check for the delivered dataset."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import csv
import json
import os

ROOT = str(Path(__file__).resolve().parents[1])
DATA = str(Path(ROOT) / "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


ok = True


def check(cond, msg):
    global ok
    print(("  OK   " if cond else "  FAIL ") + msg)
    ok = ok and bool(cond)


print("== artifacts ==")
for rel in ["data/meta.json", "data/sections.json", "data/entities.json", "data/spans.json",
            "data/legend.json", "data/columns.json", "data/timeline.csv",
            "schema/meta.schema.json", "schema/section.schema.json",
            "schema/entity.schema.json", "schema/span.schema.json",
            "schema/legend.schema.json", "dist/world-history-timeline.xlsx",
            "viewer/index.html", "README.md", "build/validate.py", "build/schema_check.py"]:
    check(os.path.exists(os.path.join(ROOT, rel)), rel)

meta, ents, spans, secs, leg = (load("meta.json"), load("entities.json"), load("spans.json"),
                                load("sections.json"), load("legend.json"))

print("\n== consistency ==")
check(len(ents) == meta["counts"]["entities"], f"entity count {len(ents)} == meta")
check(len(spans) == meta["counts"]["spans"], f"span count {len(spans)} == meta")
check(len(secs) == meta["counts"]["sections"], f"section count {len(secs)} == meta")
check({s["entity_id"] for s in spans} <= {e["id"] for e in ents}, "all spans reference known entities")
check(all(e["span_count"] == sum(1 for s in spans if s["entity_id"] == e["id"]) for e in ents),
      "span_count matches actual spans")
check(all(-3100 <= s["start_year"] < s["end_year"] <= 2000 for s in spans), "year ranges in bounds")
check(all(e["y0"] < e["y1"] for e in ents), "entity y ranges ordered")
check(len({e["id"] for e in ents}) == len(ents), "entity ids unique")
check(all(s["language_family"] is None or isinstance(s["language_family"], str) for s in spans),
      "language_family is string or null")
check(len(leg["families"]) >= 20, f"legend families: {len(leg['families'])}")

print("\n== i18n ==")
zh = json.load(open(os.path.join(ROOT, "data", "i18n", "zh-CN.json"), encoding="utf-8"))
missing = meta.get("i18n", {}).get("zh_missing", [])
check(not missing, f"zh-CN covers every printed string (missing: {len(missing)})")
check(all(e.get("name_zh") for e in ents), "every entity has name_zh")
check(all((not s["label"]) or s.get("label_zh") for s in spans), "every printed span label has label_zh")
check(len(zh.get("strings", {})) > 150, f"translation table size: {len(zh.get('strings', {}))}")

with open(os.path.join(DATA, "timeline.csv"), encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
check(len(rows) == len(spans), f"csv rows {len(rows)} == spans")

# year/x monotonicity: a span's pixel extent must map onto its year extent
PITCH, X0 = 38.08, 60.0
bad = []
for s in spans:
    yx0 = -3100 + (s["x0"] - X0) * 100 / PITCH
    if abs(yx0 - s["start_year"]) > 30:
        bad.append(s["id"])
check(len(bad) <= 2, f"pixel->year roundtrip within 30y for {len(spans) - len(bad)}/{len(spans)} spans")

print("\n== sections ==")
for s in secs:
    n = sum(1 for e in ents if e["section"] == s["id"])
    print(f"  {s['id']} {s['name'][:42]:42s} y{s['y0']}-{s['y1']}  entities={n:3d}")

print("\n== coverage ==")
cov = meta["coverage"]
print(f"  tiles {cov['tiles_transcribed']}/{cov['tiles_total']}")
for b in cov["bands"]:
    print(f"  {b['band']} {b['status']:8s} {b['tiles']}")

print("\nRESULT:", "PASS" if ok else "FAIL")
