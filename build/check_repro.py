"""Compare the working tree against the committed snapshots.

Byte equality is only required for files that are pure text and platform
independent (viewer HTML, schemas).  For JSON data and the workbook we compare
*content*, so a Linux runner with a different zlib/zip build still passes while a
real change to the dataset fails.

usage: python build/check_repro.py      (run after a full rebuild)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def committed(path):
    """Bytes of a file as of HEAD, or None when it is not tracked yet."""
    r = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def report(ok, label, detail=""):
    print(("  OK   " if ok else "  FAIL ") + label + (("  — " + detail) if detail and not ok else ""))
    return ok


def main():
    ok = True

    # 1. pure-text artefacts must be byte identical
    for rel in ["viewer/index.html", "schema/entity.schema.json", "schema/span.schema.json",
                "schema/meta.schema.json", "schema/section.schema.json", "schema/legend.schema.json"]:
        old = committed(rel)
        new = (ROOT / rel).read_bytes()
        ok &= report(old == new, f"bytes: {rel}")

    # 2. dataset content must be identical (numbers, ids, labels, order)
    for rel in ["data/meta.json", "data/sections.json", "data/entities.json",
                "data/spans.json", "data/legend.json", "data/timeline.csv"]:
        old = committed(rel)
        new = (ROOT / rel).read_bytes()
        if old == new:
            ok &= report(True, f"content: {rel}")
            continue
        if rel.endswith(".csv"):
            ok &= report(old == new, f"content: {rel}", "CSV differs")
            continue
        try:
            a, b = json.loads(old.decode("utf-8")), json.loads(new.decode("utf-8"))
        except Exception as exc:
            ok &= report(False, f"content: {rel}", f"unparsable: {exc}")
            continue
        same = a == b
        detail = ""
        if not same:
            if isinstance(a, list) and isinstance(b, list):
                detail = f"{len(a)} vs {len(b)} records"
            elif isinstance(a, dict) and isinstance(b, dict):
                diff = [k for k in a if a.get(k) != b.get(k)]
                detail = "keys differ: " + ", ".join(diff[:5])
        ok &= report(same, f"content: {rel}", detail)

    # 3. workbook: compare cell values, not bytes
    try:
        from openpyxl import load_workbook
        import io

        rel = "dist/world-history-timeline.xlsx"
        old = committed(rel)
        if old is None:
            ok &= report(False, "workbook", "not committed")
        else:
            wa = load_workbook(io.BytesIO(old), read_only=True)
            wb = load_workbook(ROOT / rel, read_only=True)
            same_sheets = wa.sheetnames == wb.sheetnames
            ok &= report(same_sheets, "workbook sheets", f"{wa.sheetnames} vs {wb.sheetnames}")
            for name in wa.sheetnames:
                if name not in wb.sheetnames:
                    continue
                ra = list(wa[name].iter_rows(values_only=True))
                rb = list(wb[name].iter_rows(values_only=True))
                if ra != rb:
                    ok &= report(False, f"workbook rows: {name}", f"{len(ra)} vs {len(rb)} rows")
    except ImportError:
        print("  SKIP  workbook (openpyxl not installed)")

    print()
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
