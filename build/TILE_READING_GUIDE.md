# Tile reading guide — SenseForMaps “World History Timeline – Decade by Decade”

You are transcribing one horizontal strip of an extremely dense historical timeline
poster into machine-readable JSON. Accuracy and honesty matter far more than volume:
**never invent a word you cannot actually read.**

## 1. What the poster is

* Horizontal axis = time. The poster prints century labels (`-3100, -3000, … -100,
  1, 100, … 2000`); negative = BCE, positive = CE. The same axis strip is repeated
  every few sections for readability.
* Vertical axis = one horizontal **band (row)** per people / culture / state.
  Band height is 9–18 px in the original image.
* Inside a band, coloured **segments** show when that people/state existed or held a
  territory. Many segments carry a printed name (an empire, dynasty, culture).
* Fill colour encodes the language family (legend: “Civilizations by language”).
  White = uninhabited, light grey = other cultures (nomadic/tribal), mid grey =
  other advanced civilizations.
* The far-left margin carries rotated region names (e.g. `SOUTHERN AFRICA`).

## 2. Reading coordinates (critical)

Each tile PNG is an upscaled crop with two rulers drawn on it:

* **Top ruler** — numbers above the artwork are **original-image x pixels**
  (a thin blue guide line drops from every 50 px, stronger every 100 px).
* **Left ruler** — numbers in the left margin are **original-image y pixels**
  (a thin magenta guide line runs across from every 20 px, stronger every 100 px).
* A small red number under some top labels is the year of that guide line. Use it
  as a cross-check only.

Report all coordinates as **integers in original-image pixel space** (e.g. `x0: 742`),
never as coordinates of the displayed PNG. Do not transcribe the ruler digits as
if they were poster text.

## 3. Output

Write **one JSON file per tile** to `D:\dsh\word-history\build\labels\<tile_id>.json`,
containing a single JSON object and nothing else (no markdown fence, no comments):

```json
{
  "tile_id": "r04c1",
  "box": [615, 580, 1235, 710],
  "margin_labels": [
    {"text": "SOUTHERN AFRICA", "x0": 8, "x1": 22, "y0": 300, "y1": 420}
  ],
  "rows": [
    {
      "y0": 655,
      "y1": 671,
      "label": "Scandinavians",
      "row_kind": "mixed",
      "confidence": "high",
      "segments": [
        {"x0": 700, "x1": 812, "text": "", "fill": "midgray", "conf": "high"},
        {"x0": 812, "x1": 905, "text": "DENMARK", "fill": "lime", "conf": "high"}
      ]
    }
  ],
  "notes": "Row at y≈600 continues into the next tile; its label is cut off."
}
```

### Field rules

* `tile_id`, `box` — copy them exactly from the assignment you were given.
* `rows` — **every band** that has text or colour inside the tile, sorted by `y0`.
  * `y0`/`y1` — top and bottom edge of the band (its fill, or its text line if the
    band has no fill). If a band starts/ends outside the tile, clamp to the tile
    edge and say so in `notes`.
  * `label` — the band's own printed name, verbatim. Normalise the poster's wide
    letter-spacing to single spaces and normal capitalisation
    (`Late  Neolithic  Corded  Ware  cultures` → `Late Neolithic Corded Ware cultures`).
    If the name is split across two lines, join with a space. Empty string if the
    band carries no own label.
  * `row_kind` — `"text"` (label only), `"bar"` (colour only), `"mixed"`.
  * `confidence` — `"high"` / `"medium"` / `"low"` for the label.
  * `segments` — left-to-right, non-overlapping contiguous fill runs in this band.
    * `x0`,`x1` — exact extents in original px (a segment boundary usually snaps to a
      decade column ≈ 3.8 px; ±4 px is acceptable).
    * `text` — the name printed **inside** the segment, verbatim, else `""`.
    * `fill` — one of: `white`, `lightgray`, `midgray`, `red`, `crimson`, `pink`,
      `magenta`, `purple`, `blue`, `navy`, `cyan`, `teal`, `green`, `lime`,
      `olive`, `yellow`, `orange`, `brown`, `black`. Pick the dominant hue;
      ignore text pixels and thin hatching.
    * `conf` — `"high"` / `"medium"` / `"low"`.
  * Merge adjacent segments only when the fill is the same **and** the text is the
    same. A tiny colour change between two neighbouring cells is a real boundary.
* `margin_labels` — rotated text in the left margin (only in column `c0` tiles),
  with the y-range of the rotated word. Empty array when none.
* `notes` — free text: cut-off rows, illegible passages, anything you had to skip.

### Transcription discipline

* Use `?` for a character you cannot resolve, `[?]` for a whole unreadable word.
  Example: `Khasar [?]` — do **not** silently replace it with a guess.
* Preserve the poster's spelling, including its errors (`Unhabited`, `Portugese`).
* Do not translate, do not add dates from your own knowledge, do not “correct”
  dates or names. Only what is visible.
* If a row is a duplicate of the row above (the poster repeats e.g.
  `Tropical forest hunter-gatherers` on several consecutive bands), keep it as a
  separate row — that is real poster structure.
* Tiny text (< ~6 px tall in the original) is often mush. Mark `low` and use `[?]`
  rather than guessing.

## 4. Working method

1. Read the tile image with the `read_image` tool.
2. Zoom mentally onto one band at a time, top to bottom; note its `y0`/`y1` from
   the left ruler.
3. Walk left→right inside the band to find segment boundaries (bar edges are
   vertical and align with the decade grid).
4. Write the JSON file with the `write` tool.
5. Re-read your own JSON and check: rows sorted, `x0 < x1`, `y0 < y1`, coordinates
   inside `box` (± 8 px slack), no invented text.
6. Reply with a one-line summary: `<tile_id>: <rows> rows, <segments> segments`.
   Do not paste the JSON into the reply.
