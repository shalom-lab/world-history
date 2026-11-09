"""Translation lookup.

The dataset keeps English as the canonical text (that is what the poster prints).
Locales live in data/i18n/<locale>.json as a flat "English string -> translation"
dictionary, so a repeated label is translated once and every occurrence follows.

A missing key is never fatal: callers get None and the build reports the gap.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import json
import os

I18N_DIR = str(ROOT / "data" / "i18n")


def available():
    if not os.path.isdir(I18N_DIR):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(I18N_DIR) if f.endswith(".json"))


def load(locale="zh-CN"):
    path = os.path.join(I18N_DIR, locale + ".json")
    if not os.path.exists(path):
        return {"locale": locale, "strings": {}, "ui": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def missing(bundle, strings):
    """Strings present in the data but absent from the translation file."""
    table = bundle.get("strings", {})
    return sorted(s for s in strings if s and s not in table)
