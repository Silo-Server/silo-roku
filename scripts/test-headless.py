#!/usr/bin/env python3
"""Build the Rooibos test packages and run them headless under brs-node.

brs-node keeps every component a run creates until its process exits (about
23 MB a Player), so one process for the whole suite outgrows V8's default
heap. The specs run in shards instead (SHARDS): each a test package of its
own, built with bsconfig.tests.json and only its specs, and run in its own
brs-node process, TEST_JOBS at a time (default 4, at most the CPU count).

brs-cli exits 0 even when tests fail, so a shard passes only when it exits 0
within TIMEOUT seconds, reports "[Rooibos Result]: PASS" and no FAIL, and ran
at least one test. With --junit the shards' reports are merged into
reports/junit.xml, written whenever every shard produced one, failures
included (scripts/update-goldens.sh reads them). Standard library only; run
it through scripts/test-headless.sh.
"""
import concurrent.futures
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
WORK = ROOT / "out" / "test-shards"
BASE_CONFIG = ROOT / "bsconfig.tests.json"
# The base config's spec entry, which each shard replaces with its own specs.
SPEC_ENTRY = {"src": "tests/**/*.spec.bs", "dest": "source/tests"}
TIMEOUT = 300
KILL_AFTER = 10

# Each shard is a name and the paths under tests/ whose specs it runs: a
# directory or a spec file. A spec runs in the shard of the longest path that
# holds it, and every spec must have one. Peak memory follows the components
# a shard's specs create, so the specs that build players and detail pages
# are spread out; the longest shards come first.
SHARDS = [
    ("catalog", ["catalog"]),
    ("playback", ["playback"]),
    ("player-captions", ["player/captions.spec.bs"]),
    ("player-sidecars", ["player/captionSidecars.spec.bs", "api", "deeplink", "dev", "memory", "nav", "platform"]),
    ("detail", ["views/detailScreen.spec.bs", "onboarding", "storage", "theme", "util", "smoke.spec.bs"]),
    ("detail-tracks", ["views/detailTracks.spec.bs", "auth", "control"]),
    ("views", ["views", "player"]),
    ("screens", ["home", "library", "search"]),
]


def specs_by_shard():
    """{ shard: [spec paths relative to tests/] }, or exits naming a spec in
    no shard, a path in two, or a path that holds no spec."""
    paths = {}
    for name, entries in SHARDS:
        for entry in entries:
            if entry in paths:
                sys.exit(f"tests/{entry} is in shards {paths[entry]} and {name} (scripts/test-headless.py)")
            paths[entry] = name
    used = set()
    out = {name: [] for name, _ in SHARDS}
    for spec in sorted(p.relative_to(TESTS).as_posix() for p in TESTS.rglob("*.spec.bs")):
        holders = [entry for entry in paths if spec == entry or spec.startswith(entry + "/")]
        if not holders:
            sys.exit(f"tests/{spec} is in no shard; add it to SHARDS in scripts/test-headless.py")
        entry = max(holders, key=len)
        used.add(entry)
        out[paths[entry]].append(spec)
    unused = sorted(set(paths) - used)
    if unused:
        sys.exit(f"no spec runs from tests/{unused[0]}; update SHARDS in scripts/test-headless.py")
    return out


def write_config(base, name, specs):
    """A bsconfig for the shard: the test config base with only its specs."""
    files = []
    for entry in base["files"]:
        if entry == SPEC_ENTRY:
            files.extend({"src": f"tests/{spec}", "dest": f"source/tests/{spec}"} for spec in specs)
        else:
            files.append(entry)
    config = {
        "extends": str(BASE_CONFIG),
        "rootDir": str(ROOT),
        "files": files,
        "stagingDir": str(WORK / name / "staging"),
        "outFile": str(WORK / name / "tests.zip"),
    }
    path = WORK / name / "bsconfig.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(config, indent=4) + "\n")
    return path


def run(command, log, cwd=ROOT, timeout=None):
    """Runs command in cwd with its output in log; returns its status, or None
    when it outlived timeout and was stopped."""
    with open(log, "wb") as out:
        process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=subprocess.STDOUT)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=KILL_AFTER)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return None


def report_of(text):
    """The JUnit report in a run's output, or None. It can span lines (a
    crash's stack trace), so it runs from <?xml through </testsuites>."""
    start = re.search(r"^<\?xml", text, re.M)
    if not start:
        return None
    end = text.find("</testsuites>", start.start())
    if end < 0:
        return None
    try:
        return ET.fromstring(text[start.start():end + len("</testsuites>")])
    except ET.ParseError:
        return None


def count(text, label):
    found = re.findall(rf"^\s*{label}:\s*(\d+)\s*$", text, re.M)
    return int(found[-1]) if found else 0


def run_shard(base, name, entries, specs, printed):
    started = time.monotonic()
    config = write_config(base, name, specs)
    shard = {"name": name, "tests": 0, "passed": 0, "failure": None, "report": None}
    build_log = WORK / name / "build.log"
    log = WORK / name / "run.log"
    if run([str(ROOT / "node_modules/.bin/bsc"), "--project", str(config)], build_log) != 0:
        shard["failure"] = "the build failed"
        output = build_log.read_text(errors="replace")
    else:
        # In the shard's directory: a request cut short by the timeout
        # leaves brs-node's temporary file in the working directory.
        status = run([str(ROOT / "node_modules/.bin/brs-cli"), str(WORK / name / "tests.zip")], log, WORK / name, TIMEOUT)
        output = log.read_text(errors="replace")
        shard["report"] = report_of(output)
        shard["tests"] = count(output, "Total")
        shard["passed"] = count(output, "Passed")
        if status is None:
            shard["failure"] = f"timed out after {TIMEOUT} seconds"
        elif status != 0:
            shard["failure"] = f"brs-cli exited {status}"
        elif "[Rooibos Result]: FAIL" in output:
            shard["failure"] = "Rooibos reported FAIL"
        elif "[Rooibos Result]: PASS" not in output:
            shard["failure"] = "Rooibos reported no result"
        elif shard["tests"] == 0:
            shard["failure"] = "no tests ran"
    shard["seconds"] = time.monotonic() - started
    with printed:
        print(f"==> shard {name}: {len(specs)} spec files from {', '.join('tests/' + entry for entry in entries)}", flush=True)
        sys.stdout.write(output)
        print(f"<== shard {name}: {shard['failure'] or 'PASS'}", flush=True)
    return shard


def merge(shards):
    """The shards' reports as one <testsuites>, with the first's properties."""
    merged = ET.Element("testsuites")
    properties = shards[0]["report"].find("properties")
    if properties is not None:
        merged.append(properties)
    for shard in shards:
        for suite in shard["report"].findall("testsuite"):
            merged.append(suite)
    return ET.ElementTree(merged)


def main(args):
    junit = args[:1] == ["--junit"]
    if args[junit:]:
        sys.exit("usage: scripts/test-headless.sh [--junit]")
    jobs = max(1, int(os.environ.get("TEST_JOBS") or min(4, os.cpu_count() or 1)))
    plan = specs_by_shard()
    base = json.loads(BASE_CONFIG.read_text())
    if SPEC_ENTRY not in base["files"]:
        sys.exit(f"{BASE_CONFIG.name} no longer lists {SPEC_ENTRY}; update scripts/test-headless.py")
    shutil.rmtree(WORK, ignore_errors=True)
    printed = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(run_shard, base, name, entries, plan[name], printed) for name, entries in SHARDS]
        shards = [future.result() for future in futures]

    print("\nshard            tests   passed  seconds  result")
    for shard in shards:
        print(f"{shard['name']:<16} {shard['tests']:>5}  {shard['passed']:>7}  {shard['seconds']:>7.1f}  {shard['failure'] or 'PASS'}")
    print(f"{'all':<16} {sum(s['tests'] for s in shards):>5}  {sum(s['passed'] for s in shards):>7}", flush=True)

    failed = [shard for shard in shards if shard["failure"]]
    if failed:
        print("headless tests failed: " + "; ".join(f"{s['name']} ({s['failure']})" for s in failed), file=sys.stderr)
    if junit:
        missing = [shard["name"] for shard in shards if shard["report"] is None]
        if missing:
            print(f"no complete JUnit report from shard {', '.join(missing)}", file=sys.stderr)
            return 1
        reports = ROOT / "reports"
        reports.mkdir(exist_ok=True)
        merge(shards).write(reports / "junit.xml.tmp", encoding="UTF-8", xml_declaration=True)
        (reports / "junit.xml.tmp").replace(reports / "junit.xml")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
