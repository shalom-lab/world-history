"""Build the legend table (language colour key) with sampled swatch colours.

Names come from visual transcription of the legend box; colours are sampled from
the printed gradient strips in the source image.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import json

import numpy as np
from PIL import Image

A = np.asarray(Image.open(str(ROOT / "source.jpg")).convert("RGB")).astype(int)

SWATCH_X = {0: (131, 143), 1: (193, 205), 2: (257, 269), 3: (324, 336),
            4: (389, 401), 5: (454, 466), 6: (523, 532)}

FAMILIES = [
    # (column, family, [(subgroup, y-range, [languages])])
    (0, "Afroasiatic", [
        ("Afroasiatic", (209, 229), ["Berber", "Merotic", "Old Nubian"]),
        ("Semitic", (239, 277), ["Amharic", "Arabic", "Canaanite", "Hebrew", "Himyaritic", "Horn"]),
    ]),
    (0, "Amerindian", [
        ("Amerindian", (294, 343), ["Aymaran", "Mayan", "Mixtec", "Nahuatl", "Puyuna",
                                    "Purepecha", "Quechua", "Teotihuacan"]),
    ]),
    (1, "Ancient languages", [
        ("Ancient languages", (209, 277), ["Akkadian", "Amorite", "Anatolian", "Ebiste",
                                           "Egyptian", "Elamite", "Hurrian", "Linear A",
                                           "Marote", "Phlisive", "Sumerian"]),
    ]),
    (1, "Austroasiatic", [
        ("Austroasiatic", (293, 314), ["Khmer", "Monic", "Vietic"]),
    ]),
    (1, "Austronesian", [
        ("Austronesian", (330, 338), ["Austronesian"]),
    ]),
    (2, "Dravidian", [
        ("Dravidian", (208, 241), ["Gondi", "Harappan", "Kannada", "Tamil", "Telugu"]),
    ]),
    (2, "Indo-European", [
        ("Indo-European", (257, 283), ["Albanian", "Armenian", "Baltic", "Celtic"]),
    ]),
    (2, "Germanic", [
        ("Germanic", (293, 332), ["Dutch", "East", "English", "German", "North", "West"]),
    ]),
    (2, "Greek", [
        ("Greek", (335, 344), ["Greek"]),
    ]),
    (3, "Indo-Iranian", [
        ("Indo-Aryan", (213, 271), ["Bengali", "Gujerati", "Hindi", "Nepali", "Prakit",
                                    "Rajput", "Sanskrit", "Sinhala", "Urdu"]),
    ]),
    (3, "Iranic", [
        ("Iranic", (281, 324), ["Median", "Parthian", "Pashto", "Persian", "Persianate",
                                "Scythian", "Tajik"]),
    ]),
    (4, "Romance", [
        ("Romance", (213, 253), ["French", "Italian", "Latin", "Portugese", "Romanian", "Spanish"]),
    ]),
    (4, "Slavic", [
        ("Slavic", (263, 284), ["East", "South", "West"]),
    ]),
    (4, "Japanese", [
        ("Japanese", (300, 307), ["Japanese"]),
    ]),
    (4, "Kartvelian", [
        ("Kartvelian", (324, 332), ["Kartvelian"]),
    ]),
    (5, "Koreanic", [
        ("Koreanic", (208, 217), ["Koreanic"]),
    ]),
    (5, "Kra-Dai", [
        ("Kra-Dai", (232, 241), ["Kra-Dai"]),
    ]),
    (5, "Mongolic", [
        ("Mongolic", (257, 271), ["Khitan", "Mongolic"]),
    ]),
    (5, "Niger-Congo", [
        ("Niger-Congo", (287, 307), ["Atlantic-Congo", "Dogon", "Mande"]),
    ]),
    (5, "Nilo-Saharan", [
        ("Nilo-Saharan", (323, 332), ["Nilo-Saharan"]),
    ]),
    (6, "Sino-Tibetan", [
        ("Sino-Tibetan", (210, 228), ["Burmese", "Chinese", "Tibetan"]),
    ]),
    (6, "Turkic", [
        ("Turkic", (246, 306), ["Turkic (other)", "Chagatai", "Karluk", "Khazar", "Kipchak",
                                "Oghur", "Oghuz", "Tatar", "Tuvin", "Uyghur", "Uzbek"]),
    ]),
]


def sample(col, y):
    x0, x1 = SWATCH_X[col]
    reg = A[max(y - 1, 0):y + 2, x0:x1 + 1].reshape(-1, 3)
    keep = reg[reg.min(axis=1) < 248]
    med = np.median(keep if len(keep) > 2 else reg, axis=0).astype(int)
    return "#%02x%02x%02x" % tuple(med), [int(v) for v in med]


def main():
    out = {"title": "Civilizations by language - Color key",
           "base_types": [
               {"name": "Uninhabited", "hex": "#ffffff", "rgb": [255, 255, 255]},
               {"name": "Other cultures, usually nomadic or tribal", "hex": "#f0f0f0", "rgb": [240, 240, 240]},
               {"name": "Other advanced civilizations", "hex": "#b3b3b3", "rgb": [179, 179, 179]},
           ],
           "families": []}
    for col, fam, subs in FAMILIES:
        fam_obj = {"id": fam.lower().replace(" ", "-"), "name": fam,
                   "legend_column": col + 1, "subgroups": []}
        for sg_name, (y0, y1), langs in subs:
            n = len(langs)
            entries = []
            for i, lang in enumerate(langs):
                cy = int(y0 + (y1 - y0) * (i + 0.5) / n)
                hexv, rgb = sample(col, cy)
                entries.append({"name": lang, "hex": hexv, "rgb": rgb, "legend_y": cy})
            fam_obj["subgroups"].append({"name": sg_name, "y_range": [y0, y1],
                                         "languages": entries})
        out["families"].append(fam_obj)
    json.dump(out, open(str(ROOT / "build" / "legend.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    for f in out["families"]:
        for sg in f["subgroups"]:
            print(f"{f['name']:18s} {sg['name']:18s}",
                  " ".join(f"{l['name']}={l['hex']}" for l in sg["languages"]))


if __name__ == "__main__":
    main()
