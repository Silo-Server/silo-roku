#!/usr/bin/env bash
# Rewrite tests/fixtures/golden/ from the bodies the serializer and the session
# reducer produce now. Runs the headless tests and writes every
# "GOLDEN <path> <body>" failure the playback contract spec
# (tests/playback/contract.spec.bs), the personal lists spec
# (tests/catalog/personal.spec.bs), and the theme music spec
# (tests/playback/themeMusic.spec.bs) report in
# reports/junit.xml. Goldens are the contract: review the diff, then run
# npm run check:contract before committing.
set -euo pipefail
cd "$(dirname "$0")/.."

# The run fails when goldens differ, so its status is ignored; a report left
# from an earlier run must not stand in for one this run did not write.
rm -f reports/junit.xml
scripts/test-headless.sh --junit > /dev/null || true
if [[ ! -f reports/junit.xml ]]; then
    echo "update-goldens: the tests wrote no JUnit report; goldens are unchanged" >&2
    exit 1
fi
python3 -I - reports/junit.xml tests/fixtures/golden <<'PY'
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

report, root = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
line = re.compile(r"GOLDEN ((?:start|replan|progress|stop|route-event|history-remove|theme-playback)/[a-z0-9-]+\.json) (\{.*\})$")
written = set()
for node in ET.parse(report).iter():
    if node.tag not in ("failure", "error"):
        continue
    for text in (node.text or "").splitlines():
        match = line.search(text)
        if not match or match.group(1) in written:
            continue
        path = (root / match.group(1)).resolve()
        if root not in path.parents:
            sys.exit(f"refusing to write outside {root}: {match.group(1)}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json.loads(match.group(2)), indent=2, sort_keys=True) + "\n")
        written.add(match.group(1))
        print(f"wrote tests/fixtures/golden/{match.group(1)}")
print(f"{len(written)} goldens updated")
PY
