"""Tiny JSON-Schema (draft-07 subset) checker.

The environment has no `jsonschema` package, so this implements the keywords the
project's schemas actually use: type, required, properties, additionalProperties,
enum, const, pattern, minLength, minimum, maximum, items, $ref (local only).

usage: python schema_check.py            # validates data/*.json against schema/
"""
import json
import os
import re
import sys

DATA = r"D:\dsh\word-history\data"
SCHEMA = r"D:\dsh\word-history\schema"

TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "number": (int, float), "integer": int, "null": type(None),
}


def resolve(root, ref):
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def check(value, schema, root, path="$"):
    errs = []
    if "$ref" in schema:
        return check(value, resolve(root, schema["$ref"]), root, path)

    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        ok = False
        for name in types:
            py = TYPES.get(name)
            if py is None:
                continue
            if name == "integer" and isinstance(value, bool):
                continue
            if isinstance(value, py):
                ok = True
                break
        if not ok:
            return [f"{path}: expected {t}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in enum")

    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errs += check(item, schema["items"], root, f"{path}[{i}]")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errs.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                errs += check(value[key], sub, root, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            for key in sorted(extra):
                errs.append(f"{path}: unexpected property '{key}'")
    return errs


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    jobs = [
        ("meta.json", "meta.schema.json", None),
        ("sections.json", "section.schema.json", None),
        ("entities.json", "entity.schema.json", None),
        ("spans.json", "span.schema.json", None),
        ("legend.json", "legend.schema.json", None),
    ]
    all_errs = []
    for data_name, schema_name, _ in jobs:
        dpath = os.path.join(DATA, data_name)
        spath = os.path.join(SCHEMA, schema_name)
        if not (os.path.exists(dpath) and os.path.exists(spath)):
            all_errs.append(f"{data_name}: missing file ({schema_name})")
            continue
        data, schema = load(dpath), load(spath)
        if schema.get("type") == "array":
            errs = check(data, schema, schema, data_name)
        else:
            errs = check(data, schema, schema, data_name)
        print(f"{data_name:16s} vs {schema_name:22s} {'OK' if not errs else str(len(errs)) + ' problems'}")
        for e in errs[:8]:
            print("   ", e)
        all_errs += errs
    return all_errs


if __name__ == "__main__":
    errs = main()
    print(f"\n{len(errs)} schema violations")
    sys.exit(1 if errs else 0)
