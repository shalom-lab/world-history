"""Build the Excel workbook from the JSON dataset."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import json
import os
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

DATA = str(ROOT / "data")
OUT = str(ROOT / "dist" / "world-history-timeline.xlsx")

HEAD_FILL = PatternFill("solid", fgColor="1F3864")
HEAD_FONT = Font(color="FFFFFF", bold=True)
SUB_FILL = PatternFill("solid", fgColor="D9E2F3")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def year_label(y):
    if y is None:
        return ""
    if y < 0:
        return f"{abs(y)} BCE"
    return f"{y} CE"


def sheet(wb, title, headers, rows, widths, wrap_cols=()):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(vertical="center")
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for col in wrap_cols:
        for row in ws.iter_rows(min_row=2, min_col=col, max_col=col):
            row[0].alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    return ws


def normalize_zip(path):
    """Rewrite the .xlsx zip with fixed entry timestamps so rebuilds are byte-identical."""
    import shutil
    import tempfile
    import zipfile

    import re

    tmp = tempfile.mktemp(suffix=".xlsx")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "docProps/core.xml":
                # openpyxl stamps the save time here; pin it so rebuilds are identical
                data = re.sub(rb"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                              rb"\g<1>2026-01-01T00:00:00Z\g<2>", data)
            info = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = item.external_attr
            zout.writestr(info, data)
    shutil.move(tmp, path)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = load("meta.json")
    ents = load("entities.json")
    spans = load("spans.json")
    legend = load("legend.json")
    sections = load("sections.json")

    wb = Workbook()
    wb.remove(wb.active)
    # fixed document properties: a rebuild must produce a byte-identical workbook
    wb.properties.creator = "world-history dataset"
    wb.properties.lastModifiedBy = "world-history dataset"
    wb.properties.created = datetime(2026, 1, 1)
    wb.properties.modified = datetime(2026, 1, 1)

    # --- overview
    ws = wb.create_sheet("README")
    lines = [
        ("World History Timeline — Decade by Decade", ""),
        ("Author", meta.get("author", "")),
        ("Source image", f'{meta["source"]["file"]}  {meta["source"]["width"]}×{meta["source"]["height"]} px'),
        ("Time range", f'{year_label(meta["time_range"]["start_year"])} → {year_label(meta["time_range"]["end_year"])}'),
        ("Axis", f'x = {meta["axis"]["x_of_year0"]:.1f} px at year {meta["time_range"]["start_year"]}, '
                 f'{meta["axis"]["px_per_century"]:.2f} px per century'),
        ("Entities (bands)", meta["counts"]["entities"]),
        ("Spans (coloured blocks)", meta["counts"]["spans"]),
        ("Sections", meta["counts"]["sections"]),
        ("Legend families", meta["counts"]["legend_families"]),
        ("", ""),
        ("How to read", "Each entity is one horizontal band of the poster. Each span is one coloured "
                        "block inside that band, with its start/end year converted from pixel position."),
        ("Precision", "Boundaries are snapped to the poster's decade grid (±10 years)."),
        ("Caveats", "Text transcribed from a 2048 px raster; small print marked with ? or low confidence."),
    ]
    for a, b in lines:
        ws.append([a, b])
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 110
    ws["A1"].font = Font(bold=True, size=14)

    # --- entities
    rows = []
    for e in ents:
        rows.append([e["id"], e.get("order"), e.get("name", ""), e.get("name_zh") or "",
                     e.get("section_name", ""),
                     e.get("category", ""), e.get("language_family", ""),
                     e.get("start_year"), e.get("end_year"),
                     year_label(e.get("start_year")), year_label(e.get("end_year")),
                     e.get("span_count"), e.get("y0"), e.get("y1"), e.get("notes", "")])
    sheet(wb, "Entities",
          ["id", "order", "name (en)", "name (zh)", "section", "category", "language family",
           "start year", "end year", "start", "end", "spans", "y0", "y1", "notes"],
          rows, [8, 6, 38, 34, 20, 14, 16, 10, 10, 12, 12, 7, 6, 6, 40], wrap_cols=(15,))

    # --- spans
    rows = []
    ent_zh = {e["id"]: (e.get("name_zh") or "") for e in ents}
    for s in spans:
        rows.append([s["id"], s["entity_id"], s.get("entity_name", ""), ent_zh.get(s["entity_id"], ""),
                     s.get("label", ""), s.get("label_zh") or "",
                     s["start_year"], s["end_year"], year_label(s["start_year"]), year_label(s["end_year"]),
                     s.get("color_hex", ""), s.get("fill_class", ""), s.get("language_family", ""),
                     s.get("x0"), s.get("x1"), s.get("confidence", "")])
    ws = sheet(wb, "Spans",
               ["id", "entity", "entity name (en)", "entity name (zh)", "label (en)", "label (zh)",
                "start year", "end year", "start", "end",
                "colour", "fill", "language family", "x0", "x1", "confidence"],
               rows, [8, 8, 28, 24, 32, 26, 10, 10, 12, 12, 10, 12, 16, 7, 7, 11])
    for r in range(2, ws.max_row + 1):
        hexv = ws.cell(row=r, column=11).value or ""
        if len(hexv) == 7:
            ws.cell(row=r, column=11).fill = PatternFill("solid", fgColor=hexv[1:])

    # --- sections
    rows = [[s["id"], s.get("name", ""), s.get("y0"), s.get("y1"),
             sum(1 for e in ents if e.get("section") == s["id"])] for s in sections]
    sheet(wb, "Sections", ["id", "name", "y0", "y1", "entities"], rows, [8, 30, 7, 7, 10])

    # --- legend
    rows = []
    for fam in legend["families"]:
        for sg in fam["subgroups"]:
            for lang in sg["languages"]:
                rows.append([fam["name"], sg["name"], lang["name"], lang["hex"]])
    ws = sheet(wb, "Legend", ["family", "subgroup", "language / branch", "swatch colour"],
               rows, [22, 20, 26, 14])
    for r in range(2, ws.max_row + 1):
        hexv = ws.cell(row=r, column=4).value or ""
        if len(hexv) == 7:
            ws.cell(row=r, column=4).fill = PatternFill("solid", fgColor=hexv[1:])

    # --- coverage
    cov = meta.get("coverage", {})
    if cov.get("bands"):
        rows = [[b["band"], b["y"][0], b["y"][1], b["tiles"], b["status"]] for b in cov["bands"]]
        sheet(wb, "Coverage", ["band", "y0", "y1", "tiles", "status"], rows, [10, 8, 8, 10, 14])
        ws.append([])
        ws.append(["tiles transcribed", f"{cov.get('tiles_transcribed')} / {cov.get('tiles_total')}"])

    # --- data dictionary
    dd = [
        ("entities.json", "id", "stable identifier E###"),
        ("entities.json", "name", "band label as printed on the poster"),
        ("entities.json", "section", "left-margin region the band belongs to"),
        ("entities.json", "category", "band type: people / culture / state / empire / other"),
        ("entities.json", "language_family", "dominant colour family of the band's spans"),
        ("spans.json", "start_year / end_year", "negative = BCE, positive = CE"),
        ("spans.json", "label", "text printed inside the block (may be empty)"),
        ("spans.json", "color_hex / fill_class", "sampled fill colour of the block"),
        ("spans.json", "confidence", "high / medium / low transcription confidence"),
    ]
    sheet(wb, "Data dictionary", ["file", "field", "meaning"], dd, [18, 24, 80], wrap_cols=(3,))

    wb.save(OUT)
    normalize_zip(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
