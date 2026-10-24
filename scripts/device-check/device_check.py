#!/usr/bin/env python3
"""Parsing and summary helpers for scripts/device-check.sh.

Reads what the device lane saves: BrightScript console (port 8085) segments
with Roku's beacon lines and the app's log lines, and ECP (port 8060) XML. The
summary it writes is for docs/hardware-evidence.md, so it never carries
addresses, credentials, signed URLs, or content IDs. Python 3.8+ standard
library only.

    device_check.py foreground ACTIVE_APP DEVICE_INFO MEDIA_PLAYER IDLE_INPUT
    device_check.py idle PLAYING_TEXT
    device_check.py facts DEVICE_INFO APPS
    device_check.py uptime DEVICE_INFO
    device_check.py summarize OUT_DIR

A file argument may be "-" when that response is not available.
"""

import datetime
import glob
import json
import os
import re
import statistics
import sys
import xml.etree.ElementTree as ET

# "10-22 09:07:45.120 sdkl [beacon.signal] |AppLaunchComplete ---> Duration(478 ms : 229 ms)".
# Anything before the device timestamp (a capture tool's own clock) is ignored.
BEACON = re.compile(
    r"(?P<stamp>\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\s+(?P<source>\S+)\s+"
    r"\[beacon\.(?P<kind>signal|report)\]\s+\|(?P<name>[A-Za-z]+)\s*-*>\s*(?P<value>.*?)\s*$"
)
DURATION = re.compile(r"Duration\(\s*([\d,]+)\s*ms")
# "[INFO] tag: message {fields}" from source/util/log.bs.
APP_LOG = re.compile(r"^(?:\d\d:\d\d:\d\d\.\d{3} )?\[(DEBUG|INFO|WARN|ERROR)\] ([\w.]+): (.*)$")
CRASH = re.compile(r"BrightScript Micro Debugger|STOP \(runtime error|Backtrace:")
IDLE_STATE = re.compile(r"^\s*Device state:\s*(\S+)", re.MULTILINE)

ROKU_HOME_IDS = ("562859",)  # "Roku Dynamic Menu"; older OS versions send <app>Roku</app>
ROUTE_TAGS = ("deeplink", "nav", "session")
ROUTE_PLATFORM_TYPES = ("launch", "input")
TRACE_LIMIT = 12

# Milestone 1 cold-launch exit (plan section 9.2) by model-number prefix; the
# certification limit (plan section 1) for every other model.
LAUNCH_LIMITS = (
    (("3810", "3921"), 6000, 8000, "Milestone 1 limit for the 3810X/3921X: median ≤ 6 s, max ≤ 8 s"),
    (("3840",), 9000, None, "Milestone 1 limit for the 3840X: median ≤ 9 s"),
)
CERT_LIMIT = (None, 15000, "no Milestone 1 limit for this model; checked against the 15 s certification limit")
MEMORY_LIMIT = 0.80
TEXTURE_LIMIT = 0.70

DEEPLINK_TYPES = ("movie", "episode", "series", "season", "invalid")

UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
URL = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://\S+")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b")


# --- Console -----------------------------------------------------------------


def beacons(text):
    """Every beacon line, in order, as dicts with stamp, source, kind, name, value."""
    found = []
    for line in text.splitlines():
        match = BEACON.search(line)
        if match:
            found.append(match.groupdict())
    return found


def duration_ms(value):
    """The first value of "Duration(A ms)" or "Duration(A ms : B ms)", else None."""
    match = DURATION.match(value)
    return int(match.group(1).replace(",", "")) if match else None


def elapsed_ms(start, end):
    """Milliseconds between two beacon stamps ("MM-DD HH:MM:SS.mmm"), or None."""
    # A leap year, so 02-29 parses; a span across New Year comes out negative.
    parse = lambda stamp: datetime.datetime.strptime("2000-" + stamp, "%Y-%m-%d %H:%M:%S.%f")
    delta = (parse(end["stamp"]) - parse(start["stamp"])).total_seconds() * 1000
    return round(delta) if delta >= 0 else None


def report(text):
    """The last beacon report (Roku prints one when the app exits): name -> value."""
    values = {}
    for line in text.splitlines():
        if "[beacon.header]" in line:
            values = {}
            continue
        match = BEACON.search(line)
        if match and match.group("kind") == "report":
            values[match.group("name")] = match.group("value")
    return values


def app_logs(text):
    """The app's log lines as (level, tag, rest)."""
    lines = []
    for line in text.splitlines():
        match = APP_LOG.match(line.strip())
        if match:
            lines.append(match.groups())
    return lines


def json_fields(rest):
    """The JSON object at the end of a log line, or {}."""
    start = rest.find("{")
    if start < 0:
        return {}
    try:
        value = json.loads(rest[start:])
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def launch_facts(text):
    """What one launch's console segment shows.

    launch_ms is the first AppLaunchInitiate to the AppLaunchComplete line, by
    the device clock. beacon_ms is the value Roku prints in that line, which on
    a sideloaded app counts from the app process's own AppLaunchInitiate and so
    leaves out the first compile pass.
    """
    found = beacons(text)
    signals = [b for b in found if b["kind"] == "signal"]
    completes = [b for b in signals if b["name"] == "AppLaunchComplete" and duration_ms(b["value"]) is not None]
    facts = {
        "beacons": len(found),
        "launch_ms": None,
        "beacon_ms": None,
        "complete_count": len(completes),
        "dialogs": dialogs(signals),
        "report_launch": report(text).get("AppLaunchComplete"),
        "crashed": bool(CRASH.search(text)),
        "exit_reasons": [],
        "session": None,
        "memory_limit_kb": None,
    }
    if completes:
        done = completes[0]
        facts["beacon_ms"] = duration_ms(done["value"])
        before = signals[: signals.index(done)]
        starts = [b for b in before if b["name"] == "AppLaunchInitiate"]
        facts["launch_ms"] = elapsed_ms(starts[0], done) if starts else None
    for level, tag, rest in app_logs(text):
        fields = json_fields(rest)
        if tag == "platform" and fields.get("type") == "launch" and fields.get("lastExitOrTerminationReason"):
            facts["exit_reasons"].append(fields["lastExitOrTerminationReason"])
        elif tag == "platform" and fields.get("type") == "memory":
            limit = (fields.get("limits") or {}).get("maxForegroundMemory")
            if isinstance(limit, (int, float)) and limit > 0:
                facts["memory_limit_kb"] = limit
        elif tag == "session" and fields.get("status"):
            facts["session"] = fields["status"]
    return facts


def dialogs(signals):
    """AppDialogInitiate/AppDialogComplete pairs: [{"ms": n or None, "closed": bool}]."""
    pairs, opened = [], None
    for beacon in signals:
        if beacon["name"] == "AppDialogInitiate":
            if opened is not None:
                pairs.append({"ms": None, "closed": False})
            opened = beacon
        elif beacon["name"] == "AppDialogComplete":
            ms = duration_ms(beacon["value"])
            if ms is None and opened is not None:
                ms = elapsed_ms(opened, beacon)
            pairs.append({"ms": ms, "closed": True})
            opened = None
    if opened is not None:
        pairs.append({"ms": None, "closed": False})
    return pairs


def route_trace(text, scrub=()):
    """The routing lines (deep links, navigation, session, launch and input
    events, warnings and errors), sanitized, in order."""
    trace = []
    for level, tag, rest in app_logs(text):
        if tag == "platform":
            if json_fields(rest).get("type") not in ROUTE_PLATFORM_TYPES:
                continue
        elif tag not in ROUTE_TAGS and level not in ("WARN", "ERROR"):
            continue
        entry = sanitize(tag + ": " + rest, scrub)
        if not trace or trace[-1] != entry:
            trace.append(entry)
    return trace


def sanitize(text, scrub=()):
    """Replace known content IDs, UUIDs, URLs, and IPv4 addresses."""
    for secret in sorted((s for s in scrub if s), key=len, reverse=True):
        text = text.replace(secret, "<id>")
    text = URL.sub("<url>", text)
    text = UUID.sub("<id>", text)
    return IPV4.sub("<addr>", text)


# --- ECP XML -----------------------------------------------------------------


def xml_root(text):
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        return None


def read_root(path):
    if path == "-" or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as handle:
        return xml_root(handle.read())


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def foreground(active, device=None, player=None, idle_input="tvinput.hdmi1"):
    """Whether a device run may proceed, from query/active-app, device-info,
    and media-player roots (assumption A-10).

    Returns ("home" | "dev", detail) to proceed, ("input", id) when the TV
    shows the one input that may be left after its device reports idle, or
    ("refuse", reason).
    """
    if device is not None:
        mode = device.findtext("power-mode")
        if mode and mode != "PowerOn":
            return "refuse", "the TV is in power mode %s; this script does not wake it" % mode
        if device.findtext("developer-enabled") == "false":
            return "refuse", "developer mode is off"
    app = active.find("app") if active is not None else None
    if app is None:
        return "refuse", "could not read the foreground app (query/active-app)"
    if player is not None and player.get("state") in ("play", "buffer", "pause"):
        return "refuse", "media is open (media-player state %s)" % player.get("state")
    app_id, name = app.get("id"), (app.text or "").strip()
    if app_id == "dev":
        return "dev", name
    if app_id in ROKU_HOME_IDS or (app_id is None and name == "Roku"):
        return "home", name
    if app_id and app_id.startswith("tvinput."):
        if app_id == idle_input:
            return "input", app_id
        return "refuse", "the TV is on input %s; only %s may be left, after its idle check" % (app_id, idle_input)
    return "refuse", "another app is in the foreground (%s)" % (name or app_id)


def idle_state(text):
    """The "Device state:" value from pyatv's `atvremote playing`, or None."""
    match = IDLE_STATE.search(text)
    return match.group(1) if match else None


DEVICE_FIELDS = ("model-name", "model-number", "software-version", "software-build", "ui-resolution")


def device_facts(device, apps):
    """Only the non-identifying device-info fields, plus the dev app."""
    facts = {field: device.findtext(field) for field in DEVICE_FIELDS} if device is not None else {}
    facts["uptime"] = uptime(device)
    for app in apps.findall("app") if apps is not None else []:
        if app.get("id") == "dev":
            facts["dev_title"] = (app.text or "").strip()
            facts["dev_version"] = app.get("version")
    return facts


def uptime(device):
    value = number(device.findtext("uptime")) if device is not None else None
    return int(value) if value is not None else None


def chanperf(root):
    if root is None:
        return None
    memory, cpu = root.find(".//memory"), root.find(".//cpu-percent")
    return {
        "status": root.findtext("status"),
        "error": root.findtext(".//error"),
        "used": number(memory.findtext("used")) if memory is not None else None,
        "cpu_user": number(cpu.findtext("user")) if cpu is not None else None,
        "cpu_sys": number(cpu.findtext("sys")) if cpu is not None else None,
    }


def r2d2(root):
    if root is None:
        return None
    texture = root.find(".//texture-memory")
    return {
        "status": root.findtext("status"),
        "used": number(texture.findtext("used")) if texture is not None else None,
        "max": number(texture.findtext("max")) if texture is not None else None,
        "bitmaps": len(root.findall(".//bitmap")),
    }


def sgnodes(root):
    """The numeric attributes of All_Nodes (count_only puts the total there),
    or the number of nodes listed."""
    if root is None:
        return None
    nodes = root.find(".//All_Nodes")
    if nodes is None:
        return {"status": root.findtext("status")}
    values = {key: value for key, value in nodes.attrib.items() if number(value) is not None}
    if not values:
        values["nodes"] = str(sum(1 for _ in nodes.iter()) - 1)
    return dict(values, status=root.findtext("status"))


def numeric_leaves(root):
    """Leaf elements with numeric text, as "path=value", timestamps left out.
    Roku documents no sample for graphics-frame-rate, so it is read this way."""
    if root is None:
        return None
    leaves = []

    def walk(element, path):
        children = list(element)
        if not children:
            if element.tag != "timestamp" and number(element.text) is not None:
                leaves.append("%s=%s" % (path, element.text.strip()))
        for child in children:
            walk(child, path + "/" + child.tag if path else child.tag)

    walk(root, "")
    return leaves


def fwbeacons(root):
    """The event names query/fwbeacons listed (children that hold a timestamp)."""
    if root is None:
        return None
    return [child.tag for child in root if child.find("timestamp") is not None]


# --- Summary -----------------------------------------------------------------


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def read_meta(out):
    path = os.path.join(out, "meta.txt")
    meta = {}
    if os.path.isfile(path):
        for line in read_text(path).splitlines():
            key, _, value = line.partition("=")
            meta[key.strip()] = value.strip()
    return meta


def read_steps(out):
    """steps.tsv: session, step, value (an HTTP status, an offset, a verdict)."""
    path = os.path.join(out, "steps.tsv")
    steps = {}
    if os.path.isfile(path):
        for line in read_text(path).splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                steps[(parts[0], parts[1])] = parts[2]
    return steps


def seconds(ms):
    return "%.2f s" % (ms / 1000)


def mib(value):
    return "%.1f MiB" % (value / 1048576)


def plural(count, noun, nouns=None):
    return "%d %s" % (count, noun if count == 1 else nouns or noun + "s")


def cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def launch_limit(model):
    for prefixes, median_ms, max_ms, label in LAUNCH_LIMITS:
        if model and model.startswith(prefixes):
            return median_ms, max_ms, label
    return CERT_LIMIT


def run_number(path):
    return int(re.sub(r"\D", "", os.path.basename(path)) or 0)


def listed(numbers):
    return ", ".join(map(str, numbers))


def launch_row(out, meta, device, steps):
    runs = sorted(glob.glob(os.path.join(out, "launch-*.log")), key=run_number)
    facts = [launch_facts(read_text(path)) for path in runs]
    values = [f["launch_ms"] if f["launch_ms"] is not None else f["beacon_ms"] for f in facts]
    measured = [v for v in values if v is not None]
    numbers = lambda test: [i + 1 for i, f in enumerate(facts) if test(f)]
    missing = numbers(lambda f: f["beacons"] and f["complete_count"] == 0)
    uncaptured = numbers(lambda f: not f["beacons"])
    repeated = numbers(lambda f: f["complete_count"] > 1)
    with_dialogs = numbers(lambda f: f["dialogs"])
    crashed = numbers(lambda f: f["crashed"])
    median_limit, max_limit, label = launch_limit(device.get("model-number"))

    requested = int(meta.get("launches") or 0)
    notes = ["%d of %d launches reached `AppLaunchComplete`." % (len(measured), len(facts))]
    if len(facts) < requested:
        notes.append("The run stopped after %s of %d." % (plural(len(facts), "launch", "launches"), requested))
    over = False
    if measured:
        median, top = statistics.median(measured), max(measured)
        over = (median_limit is not None and median > median_limit) or (max_limit is not None and top > max_limit)
        notes.append("First `AppLaunchInitiate` to `AppLaunchComplete`: median %s, max %s (%s)." % (seconds(median), seconds(top), label))
        roku = [f["beacon_ms"] for f in facts if f["beacon_ms"] is not None]
        notes.append("Roku's beacon value: median %s, max %s." % (seconds(statistics.median(roku)), seconds(max(roku))))
        notes.append("Runs: %s." % ", ".join("%.2f" % (v / 1000) if v is not None else "—" for v in values))
    if missing:
        notes.append("No `AppLaunchComplete` within %s s: runs %s." % (meta.get("timeout", "?"), listed(missing)))
    if uncaptured:
        notes.append("No beacon lines captured: runs %s." % listed(uncaptured))
    if repeated:
        notes.append("More than one `AppLaunchComplete`: runs %s." % listed(repeated))
    else:
        notes.append("One `AppLaunchComplete` per completed launch.")
    if with_dialogs:
        notes.append("Dialog beacons in runs %s, so those launches waited for the viewer." % listed(with_dialogs))
    else:
        notes.append("No dialog beacons.")
    if crashed:
        notes.append("Crash output in runs %s." % listed(crashed))
    reasons = [r for f in facts for r in f["exit_reasons"]]
    if reasons:
        notes.append("`lastExitOrTerminationReason`: %s." % ", ".join("%s ×%d" % (r, reasons.count(r)) for r in sorted(set(reasons))))
    reports = sorted({f["report_launch"] for f in facts if f["report_launch"]})
    if reports:
        notes.append("Exit beacon report's `AppLaunchComplete`: %s." % "; ".join(reports))
    notes.append(fwbeacons_note(out, steps))

    if missing or crashed or over:
        result = "FAIL"
    elif uncaptured or len(facts) < requested or not facts:
        result = "PARTIAL"
    else:
        result = "PASS"
    if "exit_timeout" in meta:
        between = "`exit-app` between runs, awaited for up to %s s" % meta["exit_timeout"]
    else:
        between = "`exit-app` and %s s between runs" % meta.get("exit_wait", "?")
    settings = "%s, %s; %s" % (plural(len(facts), "cold launch", "cold launches"), between, reboot_note(meta, device))
    return ["M1 cold launch", settings, result, " ".join(notes)]


def reboot_note(meta, device):
    note = "after a manual restart and a 30 s wait" if meta.get("reboot") == "awaited" else "no reboot"
    if device.get("uptime") is not None:
        up = device["uptime"]
        note += " (uptime %s at the first launch)" % ("%d s" % up if up < 600 else "%d min" % (up // 60))
    return note


def fwbeacons_note(out, steps):
    status = steps.get(("launches", "fwbeacons-track"))
    if status != "200":
        return "`fwbeacons/track` answered HTTP %s, so `query/fwbeacons` was not read." % (status or "—")
    events = []
    for path in sorted(glob.glob(os.path.join(out, "launch-*-fwbeacons.xml"))):
        events.extend(fwbeacons(read_root(path)) or [])
    if not events:
        return "`query/fwbeacons` listed no events."
    lists = "lists" if "app-launch-complete" in events else "does not list"
    return "`query/fwbeacons` %s `app-launch-complete` (events seen: %s)." % (lists, ", ".join(sorted(set(events))))


def perf_row(out, meta, steps):
    status = lambda name: steps.get(("perf", name), "—")
    notes, failed, partial = [], False, False
    console = os.path.join(out, "perf.log")
    limit_kb = launch_facts(read_text(console))["memory_limit_kb"] if os.path.isfile(console) else None

    perf = chanperf(read_root(os.path.join(out, "chanperf.xml")))
    if status("chanperf") == "200" and perf and perf["status"] == "OK" and perf["used"] is not None:
        text = "`chanperf`: memory used %s" % mib(perf["used"])
        if limit_kb:
            share = perf["used"] / (limit_kb * 1024)
            text += " (%.0f%% of the %s foreground limit)" % (share * 100, mib(limit_kb * 1024))
            failed = failed or share >= MEMORY_LIMIT
        else:
            text += " (no foreground limit in the console: info logs need the dev build)"
        if perf["cpu_user"] is not None:
            text += ", CPU user %.1f%%, sys %.1f%%" % (perf["cpu_user"], perf["cpu_sys"] or 0)
        notes.append(text + ".")
    else:
        detail = (perf or {}).get("error") or (perf or {}).get("status") or "no XML"
        notes.append("`chanperf`: HTTP %s, %s; it needs the perf build (`run_as_process=1`)." % (status("chanperf"), sanitize(detail)))
        partial = True

    bitmaps = r2d2(read_root(os.path.join(out, "r2d2-bitmaps.xml")))
    if status("r2d2-bitmaps") == "200" and bitmaps and bitmaps["used"] is not None and bitmaps["max"]:
        share = bitmaps["used"] / bitmaps["max"]
        notes.append("`r2d2-bitmaps`: texture memory %s of %s (%.0f%%), %s." % (mib(bitmaps["used"]), mib(bitmaps["max"]), share * 100, plural(bitmaps["bitmaps"], "bitmap")))
        failed = failed or share >= TEXTURE_LIMIT
    else:
        notes.append("`r2d2-bitmaps`: HTTP %s, no texture figures." % status("r2d2-bitmaps"))
        partial = True

    for name, label in (("sgnodes-count", "count_only=true"), ("sgnodes-sizes", "count_only=true&sizes=true")):
        nodes = sgnodes(read_root(os.path.join(out, name + ".xml")))
        values = ", ".join("%s=%s" % item for item in sorted((nodes or {}).items()) if item[0] != "status")
        notes.append("`sgnodes/all?%s`: HTTP %s%s." % (label, status(name), ", " + values if values else ""))

    leaves = numeric_leaves(read_root(os.path.join(out, "graphics-frame-rate.xml")))
    notes.append("`graphics-frame-rate` (idle on Home): HTTP %s%s." % (status("graphics-frame-rate"), ", " + ", ".join(leaves) if leaves else ""))
    result = "FAIL" if failed else "PARTIAL" if partial else "PASS"
    return ["M1 snapshots", "`--perf`; Home, %s s after `AppLaunchComplete`" % meta.get("snapshot_wait", "?"), result, " ".join(notes)]


def deeplink_rows(out, steps, scrub):
    rows, skipped = [], []
    for media_type in DEEPLINK_TYPES:
        if steps.get(("deeplink-" + media_type, "skipped")):
            skipped.append(media_type)
            continue
        for via in ("launch", "input"):
            name = "deeplink-%s-%s" % (media_type, via)
            path = os.path.join(out, name + ".log")
            if os.path.isfile(path):
                rows.append(deeplink_row(path, name, media_type, via, steps, scrub))
    return rows, skipped


def deeplink_row(path, name, media_type, via, steps, scrub):
    """One deep-link case. For an input case the launch comes before the
    recorded offset and the routing after it."""
    with open(path, "rb") as handle:
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    offset = steps.get((name, "input-offset"))
    if offset:
        launch = data[: int(offset)].decode("utf-8", errors="replace")
        routed = data[int(offset) :].decode("utf-8", errors="replace")
    else:
        launch = routed = text
    whole = launch_facts(text)
    facts = launch_facts(launch) if offset else whole
    notes = ["ECP `%s` HTTP %s" % (via, steps.get((name, via), "—"))]
    notes.append("foreground afterwards: %s" % steps.get((name, "after"), "—"))
    if facts["launch_ms"] is not None:
        notes.append("`AppLaunchComplete` %s after launch" % seconds(facts["launch_ms"]))
    else:
        notes.append("no `AppLaunchComplete`")
    if facts["dialogs"]:
        notes.append("dialog %s" % ("closed" if all(d["closed"] for d in facts["dialogs"]) else "open"))
    if whole["crashed"]:
        notes.append("crash output")
    trace = route_trace(routed, scrub)
    shown = trace[:TRACE_LIMIT] + (["…"] if len(trace) > TRACE_LIMIT else [])
    notes.append("route: " + (" → ".join("`%s`" % line for line in shown) if shown else "no routing lines (info logs need the dev build)"))
    settings = "session %s (console)" % (whole["session"] or "not logged")
    return ["M1 deep link, %s, %s" % (media_type, via), settings, "(judge)", "; ".join(notes) + "."]


def summarize(out, scrub=()):
    meta, steps = read_meta(out), read_steps(out)
    device_path = os.path.join(out, "device.json")
    device = json.loads(read_text(device_path)) if os.path.isfile(device_path) else {}
    date = meta.get("date", "")
    model = device.get("model-name") or ""
    if device.get("model-number"):
        model = ("%s (%s)" % (model, device["model-number"])).strip()
    device_cell = "%s / %s" % (model or "unknown", device.get("software-version") or "?")

    lines = ["## Session %s: device check (`scripts/device-check.sh`)" % date, ""]
    lines.append("- **Device:** %s, Roku OS %s build %s, UI %s." % (
        model or "unknown", device.get("software-version") or "?", device.get("software-build") or "?", device.get("ui-resolution") or "?"))
    lines.append("- **App:** the dev slot, \"%s\" %s. ECP does not show the build variant (release, perf, or dev); record it here." % (
        device.get("dev_title") or "?", device.get("dev_version") or "?"))
    lines.append("- **Pre-flight:** %s." % meta.get("foreground", "not recorded"))
    lines.append("- **Raw files:** the tester's private evidence folder (console segments and ECP XML; bitmap names there can carry server addresses).")

    rows = []
    if int(meta.get("launches") or 0) > 0:
        rows.append(launch_row(out, meta, device, steps))
    if meta.get("perf") == "1":
        rows.append(perf_row(out, meta, steps))
    if meta.get("deeplinks") == "1":
        deep, skipped = deeplink_rows(out, steps, scrub)
        rows.extend(deep)
        lines.append("- **Deep links:** `(judge)` rows need PASS or FAIL against the routing table in plan section 7 before they are appended.%s" % (
            " Not run, no ID given: %s." % ", ".join(skipped) if skipped else ""))
    lines += ["", "| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for test, settings, result, facts in rows:
        lines.append("| %s |" % " | ".join(cell(c) for c in (test, date, device_cell, "—", "—", settings, result, facts)))
    return "\n".join(lines) + "\n"


# --- Command line ------------------------------------------------------------


def main(argv):
    command, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if command == "foreground" and len(args) == 4:
        verdict, detail = foreground(read_root(args[0]), read_root(args[1]), read_root(args[2]), args[3])
        print(verdict, detail)
        return 0
    if command == "idle" and len(args) == 1:
        state = idle_state(read_text(args[0]))
        print(state or "unknown")
        return 0 if state == "Idle" else 1
    if command == "facts" and len(args) == 2:
        facts = device_facts(read_root(args[0]), read_root(args[1]))
        print(json.dumps(facts, indent=2, sort_keys=True))
        return 0 if facts.get("dev_version") else 1
    if command == "uptime" and len(args) == 1:
        value = uptime(read_root(args[0]))
        print("" if value is None else value)
        return 0
    if command == "summarize" and len(args) == 1:
        scrub = os.environ.get("DEVICE_CHECK_SCRUB", "").split("\n")
        sys.stdout.write(summarize(args[0], scrub))
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
