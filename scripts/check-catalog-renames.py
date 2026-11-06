#!/usr/bin/env python3
"""Show that the generated English catalog renders every old key's text (D21).

    python3 -I scripts/check-catalog-renames.py [--old FILE] [--new FILE] [--renames FILE]

The old table defaults to locale/en_US/strings.json as of 1dc62a8d, the last
hand-written one (read with git show), the new one to the working tree's
generated locale/en_US/strings.json, and the rename map to
scripts/catalog-renames.json (silo-translations' seed import). For each of the
old keys it renders the old text and the new key's text with the same sample
values and compares them:

- unchanged keys and renamed keys: the text as it stands;
- a plural form (".one", "xOne", "oneProfile", ...): the new key's English
  category entry at the count that selected the old form (1 for "one", 2 for
  "other");
- a count message that had one text for every count ("form": "plural"): the
  new key at 1 and at 2.

Every {placeholder} gets the count, so a ".one" text that spelled out "1"
compares equal to the new "{count} ..." at 1. Exits 1 and lists each mismatch.
"""
import argparse
import json
import re
import subprocess
import sys

BASE = "1dc62a8d"
PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def english_category(count):
    return "one" if count == 1 else "other"


def render(text, count):
    return PLACEHOLDER.sub(str(count), text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old")
    parser.add_argument("--new", default="locale/en_US/strings.json")
    parser.add_argument("--renames", default="scripts/catalog-renames.json")
    args = parser.parse_args()
    if args.old:
        with open(args.old, encoding="utf-8") as f:
            old = json.load(f)
    else:
        raw = subprocess.run(["git", "show", BASE + ":locale/en_US/strings.json"], check=True, capture_output=True).stdout
        old = json.loads(raw.decode("utf-8"))
    with open(args.new, encoding="utf-8") as f:
        new = json.load(f)
    with open(args.renames, encoding="utf-8") as f:
        renames = json.load(f)

    failures = []
    for key, text in old.items():
        entry = renames.get(key, {"key": key, "kind": "same"})
        if entry["kind"] in ("same", "renamed"):
            cases = [(entry["key"], None)]
        elif entry["form"] == "plural":
            cases = [(entry["key"], 1), (entry["key"], 2)]
        else:
            cases = [(entry["key"], 1 if entry["form"] == "one" else 2)]
        for new_key, count in cases:
            if count is not None:
                new_key = new_key + "." + english_category(count)
            want = render(text, count if count is not None else 7)
            got = new.get(new_key)
            if got is None:
                failures.append(f"{key}: {new_key} is missing")
            elif render(got, count if count is not None else 7) != want:
                failures.append(f"{key} -> {new_key}: {want!r} != {render(got, count or 7)!r}")
    for line in failures:
        print(line, file=sys.stderr)
    print(f"{len(old)} old keys, {len(renames)} renamed or plural, {len(failures)} mismatches")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
