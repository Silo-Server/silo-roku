"""Tests for device_check.py. Run from the repository root:

    python3 -I -B -m unittest discover -s scripts/device-check

Console samples are trimmed from a 2026-10-22 port 8085 capture of a
sideloaded dev build (55R625 Roku TV, Roku OS 15.3.4). ECP samples follow
the examples in Roku's External Control Protocol documentation, with
identifiers replaced. Roku shows no sample of the dialog beacon lines, so
those follow the launch beacons' format.
"""

import io
import json
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout

import device_check as dc

LAUNCH = """\
10-22 09:07:40.509 app  [beacon.signal] |AppExitComplete -----------> Duration(199 ms)
10-22 09:07:43.365 app  [beacon.signal] |AppLaunchInitiate ---------> TimeBase(0 ms)
10-22 09:07:43.382 app  [beacon.signal] |AppCompileInitiate --------> TimeBase(17 ms)
------ Compiling dev 'Silo' ------
10-22 09:07:43.661 app  [beacon.signal] |AppCompileComplete --------> Duration(279 ms)
10-22 09:07:43.699 app  [beacon.signal] |AppLaunchInitiate ---------> TimeBase(0 ms)
10-22 09:07:43.699 app  [beacon.signal] |AppLaunchChainInitiate ----> TimeBase(NotApplicable)
10-22 09:07:43.715 app  [beacon.signal] |AppSplashInitiate ---------> TimeBase(15 ms)
10-22 09:07:43.818 app  [beacon.signal] |AppSplashComplete ---------> Duration(104 ms)
10-22 09:07:44.642 sdkl [beacon.signal] |AppLaunchInitiate ---------> TimeBase(0 ms)
------ Compiling dev 'Silo' ------
10-22 09:07:44.890 sdkl [beacon.signal] |AppCompileComplete --------> Duration(247 ms)
------ Running dev 'Silo' main ------
10-22 09:07:44.946 sdkl [beacon.signal] |AppLaunchChainComplete ----> Duration(998 ms)
10-22 09:07:45.089 sdkl [beacon.signal] |AppLaunchComplete ---------> Pending Render Pass
[INFO] diagnostics: Model: 55R625 (A000X)
Roku OS: 15.3.4 build 2303
10-22 09:07:45.120 sdkl [beacon.signal] |AppLaunchComplete ---------> Duration(478 ms : 229 ms)
[INFO] platform: {"lastExitOrTerminationReason":"EXIT_USER_NAV","source":"auto-run-dev","type":"launch"}
[INFO] platform: {"availablekb":542712,"limits":{"maxBackgroundMemory":362496,"maxForegroundMemory":593920,"maxRokuManagedHeapMemory":455680},"percent":1,"type":"memory","warnings":true}
[INFO] platform: {"mode":"Off","type":"captionMode"}
[INFO] session: state {"reason":"","status":"signed_in"}
10-22 09:08:40.721 app  [beacon.signal] |AppExitComplete -----------> Duration(504 ms)
10-22 09:08:40.721 app  [beacon.header] __________________________________________
10-22 09:08:40.721 app  [beacon.report] |AppLaunchInitiate ---------> TimeBase(0 ms), InstantOn
10-22 09:08:40.721 app  [beacon.report] |AppLaunchComplete ---------> Pended without Render
10-22 09:08:40.721 app  [beacon.report] |AppSplashInitiate ---------> TimeBase(15 ms)
10-22 09:08:40.721 app  [beacon.report] |AppSplashComplete ---------> Duration(104 ms)
10-22 09:08:40.721 app  [beacon.report] |AppCompileComplete --------> Duration(247 ms)
10-22 09:08:40.721 app  [beacon.report] |AppExitComplete -----------> Duration(504 ms)
10-22 09:08:40.721 app  [beacon.report] |AppLaunchChainComplete ----> Duration(1247 ms)
10-22 09:08:40.721 app  [beacon.footer] __________________________________________
"""

DIALOG = """\
10-22 10:00:00.000 app  [beacon.signal] |AppLaunchInitiate ---------> TimeBase(0 ms)
10-22 10:00:01.500 sdkl [beacon.signal] |AppDialogInitiate ---------> TimeBase(1500 ms)
[INFO] nav: beacon {"name":"AppDialogInitiate"}
10-22 10:00:05.750 sdkl [beacon.signal] |AppDialogComplete ---------> Duration(4250 ms)
10-22 10:00:06.000 sdkl [beacon.signal] |AppDialogInitiate ---------> TimeBase(6000 ms)
10-22 10:00:07.000 sdkl [beacon.signal] |AppDialogComplete ---------> Done
10-22 10:00:09.000 sdkl [beacon.signal] |AppDialogInitiate ---------> TimeBase(9000 ms)
"""

MOVIE_ID = "4d1b2c3a-0000-4000-8000-00000000c0de"

ROUTED = """\
[INFO] platform: {"contentId":"present","mediaType":"present","type":"input"}
[INFO] deeplink: route {"contentId":"%s","to":"player"}
[INFO] platform: {"availablekb":542712,"percent":1,"type":"memory"}
[INFO] nav: phase {"phase":"home"}
[INFO] nav: phase {"phase":"home"}
[INFO] api: request {"url":"http://192.0.2.44:8096/api/v2/items/%s"}
[WARN] api: refused http://192.0.2.44:8096/x?st=signed
[INFO] memory: tier {"tier":"normal"}
""" % (MOVIE_ID, MOVIE_ID)


def root(text):
    return ET.fromstring(text)


ACTIVE_HOME = '<active-app><app id="562859" type="appl" version="1.0.0">Roku Dynamic Menu</app></active-app>'
ACTIVE_LEGACY_HOME = '<active-app><app>Roku</app><screensaver id="55545" type="ssvr" version="2.0.1">Default</screensaver></active-app>'
ACTIVE_DEV = '<active-app><app id="dev" type="appl" version="0.1.0">Silo</app></active-app>'
ACTIVE_HDMI1 = '<active-app><app id="tvinput.hdmi1" type="tvin" version="1.0.0">HDMI 1</app></active-app>'
ACTIVE_HDMI2 = '<active-app><app id="tvinput.hdmi2" type="tvin" version="1.0.0">Console</app></active-app>'
ACTIVE_OTHER = '<active-app><app id="12" type="appl" version="5.0">Another App</app></active-app>'

DEVICE_INFO = """\
<device-info>
  <udn>00000000-0000-0000-0000-000000000000</udn>
  <serial-number>SERIAL0000</serial-number>
  <device-id>DEVICE0000</device-id>
  <model-number>A109X</model-number>
  <model-name>55R625</model-name>
  <ui-resolution>1080p</ui-resolution>
  <wifi-mac>00:00:5e:00:53:01</wifi-mac>
  <network-name>HomeNetwork</network-name>
  <user-device-name>Test TV</user-device-name>
  <software-version>15.3.4</software-version>
  <software-build>2303</software-build>
  <power-mode>%s</power-mode>
  <developer-enabled>%s</developer-enabled>
  <keyed-developer-id>0000</keyed-developer-id>
  <uptime>420</uptime>
</device-info>
"""

APPS = """\
<apps>
  <app id="12" type="appl" version="5.0">Another App</app>
  <app id="dev" type="appl" version="0.1.0">Silo</app>
</apps>
"""

CHANPERF = """\
<chanperf>
  <timestamp>1672980398506</timestamp>
  <plugin>
    <cpu-percent><duration-seconds>1.000000</duration-seconds><user>12.2</user><sys>5.5</sys></cpu-percent>
    <memory><used>87785472</used><res>87785472</res><anon>24027136</anon><swap>0</swap></memory>
    <id>dev</id>
  </plugin>
  <status>OK</status>
</chanperf>
"""

CHANPERF_FAILED = "<chanperf><timestamp>1</timestamp><status>FAILED</status><error>Channel not running as a separate process</error></chanperf>"

R2D2 = """\
<r2d2-bitmaps>
  <rographics>
    <sytem-memory><used>115200</used></sytem-memory>
    <texture-memory><used>26841088</used><available>93158912</available><max>120000000</max></texture-memory>
    <bitmap><width>1920</width><height>1080</height><bpp>3</bpp><size>8355840</size><name>http://192.0.2.44:8096/art.jpg</name></bitmap>
    <bitmap><width>1920</width><height>1080</height><bpp>3</bpp><size>8355840</size><name>/nvram/theme/FHD/BackgroundBitmap.jpg</name></bitmap>
  </rographics>
  <status>OK</status>
</r2d2-bitmaps>
"""

SGNODES_COUNT = '<sgnodes><All_Nodes count="214" /><status>OK</status></sgnodes>'
SGNODES_TREE = '<sgnodes><All_Nodes><MainScene bscref="1" /><Poster osref="1" /></All_Nodes><status>OK</status></sgnodes>'
FRAME_RATE = "<graphics-frame-rate><timestamp>1</timestamp><frame-rate>59</frame-rate><status>OK</status></graphics-frame-rate>"

FWBEACONS = """\
<fwbeacons>
  <tracking-enabled>true</tracking-enabled>
  <plugin-id>dev</plugin-id>
  <drop-count>0</drop-count>
  <count>2</count>
  <app-compile-initiate><timestamp>1675727290681</timestamp></app-compile-initiate>
  <app-compile-complete><timestamp>1675727290706</timestamp></app-compile-complete>
  <timestamp>1675727301787</timestamp>
  <status>OK</status>
</fwbeacons>
"""


class BeaconTests(unittest.TestCase):
    def test_launch_segment(self):
        facts = dc.launch_facts(LAUNCH)
        self.assertEqual(facts["launch_ms"], 1755)  # 09:07:43.365 to 09:07:45.120
        self.assertEqual(facts["beacon_ms"], 478)
        self.assertEqual(facts["complete_count"], 1)
        self.assertEqual(facts["report_launch"], "Pended without Render")
        self.assertEqual(facts["exit_reasons"], ["EXIT_USER_NAV"])
        self.assertEqual(facts["memory_limit_kb"], 593920)
        self.assertEqual(facts["session"], "signed_in")
        self.assertEqual(facts["dialogs"], [])
        self.assertFalse(facts["crashed"])

    def test_line_endings_and_capture_prefixes(self):
        prefixed = "\r\n".join("09:14:17.766 " + line for line in LAUNCH.splitlines())
        facts = dc.launch_facts(prefixed)
        self.assertEqual((facts["launch_ms"], facts["beacon_ms"]), (1755, 478))
        self.assertEqual(facts["session"], "signed_in")

    def test_pending_only_is_not_complete(self):
        text = "\n".join(line for line in LAUNCH.splitlines() if "Duration(478" not in line)
        facts = dc.launch_facts(text)
        self.assertEqual(facts["complete_count"], 0)
        self.assertIsNone(facts["launch_ms"])
        self.assertIsNone(facts["beacon_ms"])
        self.assertGreater(facts["beacons"], 0)

    def test_duration_forms(self):
        self.assertEqual(dc.duration_ms("Duration(1,100 ms)"), 1100)
        self.assertEqual(dc.duration_ms("Duration(410 ms : 223 ms)"), 410)
        self.assertIsNone(dc.duration_ms("Pending Render Pass"))
        self.assertIsNone(dc.duration_ms("TimeBase(0 ms)"))

    def test_report_keeps_the_last_block(self):
        first = LAUNCH.replace("Pended without Render", "Duration(900 ms)")
        self.assertEqual(dc.report(first + LAUNCH)["AppLaunchComplete"], "Pended without Render")
        self.assertEqual(dc.report(LAUNCH + first)["AppLaunchComplete"], "Duration(900 ms)")
        self.assertEqual(dc.report("no report"), {})

    def test_dialog_pairs(self):
        facts = dc.launch_facts(DIALOG)
        self.assertEqual(facts["dialogs"], [
            {"ms": 4250, "closed": True},
            {"ms": 1000, "closed": True},  # no Duration: the stamps give it
            {"ms": None, "closed": False},
        ])
        self.assertEqual(facts["complete_count"], 0)

    def test_crash(self):
        self.assertTrue(dc.launch_facts(LAUNCH + "BrightScript Micro Debugger.\n")["crashed"])

    def test_span_needs_order(self):
        reversed_stamps = LAUNCH.replace("10-22 09:07:43.365", "10-22 09:07:46.000")
        self.assertIsNone(dc.launch_facts(reversed_stamps)["launch_ms"])


class RouteTests(unittest.TestCase):
    def test_trace_filters_and_scrubs(self):
        trace = dc.route_trace(ROUTED, [MOVIE_ID])
        self.assertEqual(trace, [
            'platform: {"contentId":"present","mediaType":"present","type":"input"}',
            'deeplink: route {"contentId":"<id>","to":"player"}',
            'nav: phase {"phase":"home"}',
            "api: refused <url>",
        ])

    def test_sanitize(self):
        text = "id %s at http://192.0.2.44/x?st=s via 192.0.2.44:8096 and %s" % (MOVIE_ID, "11111111-2222-4333-8444-555555555555")
        self.assertEqual(dc.sanitize(text, ["", MOVIE_ID]), "id <id> at <url> via <addr> and <id>")
        self.assertEqual(dc.sanitize("item 12345 moved", ["12345"]), "item <id> moved")
        self.assertEqual(dc.sanitize("Roku OS 15.3.4 build 2303"), "Roku OS 15.3.4 build 2303")


class ForegroundTests(unittest.TestCase):
    def device(self, mode="PowerOn", developer="true"):
        return root(DEVICE_INFO % (mode, developer))

    def test_allowed(self):
        self.assertEqual(dc.foreground(root(ACTIVE_HOME), self.device())[0], "home")
        self.assertEqual(dc.foreground(root(ACTIVE_LEGACY_HOME), self.device())[0], "home")
        self.assertEqual(dc.foreground(root(ACTIVE_DEV), self.device()), ("dev", "Silo"))
        self.assertEqual(dc.foreground(root(ACTIVE_HOME))[0], "home")

    def test_idle_input_needs_a_check(self):
        self.assertEqual(dc.foreground(root(ACTIVE_HDMI1), self.device()), ("input", "tvinput.hdmi1"))
        self.assertEqual(dc.foreground(root(ACTIVE_HDMI2), self.device(), idle_input="tvinput.hdmi2")[0], "input")

    def test_refusals(self):
        cases = [
            (root(ACTIVE_HDMI2), self.device(), None, "input tvinput.hdmi2"),
            (root(ACTIVE_OTHER), self.device(), None, "Another App"),
            (root(ACTIVE_HOME), self.device("DisplayOff"), None, "DisplayOff"),
            (root(ACTIVE_HOME), self.device(developer="false"), None, "developer mode"),
            (root(ACTIVE_DEV), self.device(), root('<player error="false" state="play"/>'), "state play"),
            (None, self.device(), None, "could not read"),
            (root("<active-app/>"), None, None, "could not read"),
        ]
        for active, device, player, reason in cases:
            verdict, detail = dc.foreground(active, device, player)
            self.assertEqual(verdict, "refuse", reason)
            self.assertIn(reason, detail)

    def test_closed_player_is_fine(self):
        player = root('<player error="false" state="close"/>')
        self.assertEqual(dc.foreground(root(ACTIVE_HOME), self.device(), player)[0], "home")

    def test_idle_state(self):
        self.assertEqual(dc.idle_state("  Media type: Unknown\nDevice state: Idle\n"), "Idle")
        self.assertEqual(dc.idle_state("Device state: Playing\n  Title: x\n"), "Playing")
        self.assertIsNone(dc.idle_state("Connection refused"))


class EcpTests(unittest.TestCase):
    def test_device_facts_keep_only_safe_fields(self):
        facts = dc.device_facts(root(DEVICE_INFO % ("PowerOn", "true")), root(APPS))
        self.assertEqual(facts, {
            "model-name": "55R625",
            "model-number": "A109X",
            "software-version": "15.3.4",
            "software-build": "2303",
            "ui-resolution": "1080p",
            "uptime": 420,
            "dev_title": "Silo",
            "dev_version": "0.1.0",
        })
        self.assertNotIn("dev_version", dc.device_facts(None, root("<apps/>")))

    def test_chanperf(self):
        self.assertEqual(dc.chanperf(root(CHANPERF)), {"status": "OK", "error": None, "used": 87785472, "cpu_user": 12.2, "cpu_sys": 5.5})
        failed = dc.chanperf(root(CHANPERF_FAILED))
        self.assertEqual((failed["status"], failed["used"]), ("FAILED", None))

    def test_r2d2(self):
        self.assertEqual(dc.r2d2(root(R2D2)), {"status": "OK", "used": 26841088, "max": 120000000, "bitmaps": 2})

    def test_sgnodes(self):
        self.assertEqual(dc.sgnodes(root(SGNODES_COUNT)), {"count": "214", "status": "OK"})
        self.assertEqual(dc.sgnodes(root(SGNODES_TREE)), {"nodes": "2", "status": "OK"})

    def test_numeric_leaves(self):
        self.assertEqual(dc.numeric_leaves(root(FRAME_RATE)), ["frame-rate=59"])

    def test_fwbeacons(self):
        self.assertEqual(dc.fwbeacons(root(FWBEACONS)), ["app-compile-initiate", "app-compile-complete"])

    def test_unparsable(self):
        self.assertIsNone(dc.xml_root("<html>Forbidden"))
        self.assertIsNone(dc.chanperf(None))


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.out = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.out, name), "w") as handle:
            handle.write(text)

    def prepare(self, model="A109X", meta=""):
        self.write("meta.txt", "date=2026-10-22\nlaunches=3\nreboot=none\nperf=1\ndeeplinks=1\n"
                   "foreground=the TV showed Roku Home\ntimeout=30\nexit_timeout=15\nsnapshot_wait=5\n" + meta)
        self.write("device.json", json.dumps({"model-name": "55R625", "model-number": model, "software-version": "15.3.4",
                                              "software-build": "2303", "ui-resolution": "1080p", "uptime": 600,
                                              "dev_title": "Silo", "dev_version": "0.1.0"}))
        for number in (1, 2, 3):
            self.write("launch-%02d.log" % number, LAUNCH)
            self.write("launch-%02d-fwbeacons.xml" % number, FWBEACONS)
        self.write("perf.log", LAUNCH)
        self.write("chanperf.xml", CHANPERF)
        self.write("r2d2-bitmaps.xml", R2D2)
        self.write("sgnodes-count.xml", SGNODES_COUNT)
        self.write("sgnodes-sizes.xml", SGNODES_COUNT)
        self.write("graphics-frame-rate.xml", FRAME_RATE)
        launch_part = LAUNCH.split("10-22 09:08:40.721")[0]
        self.write("deeplink-movie-launch.log", LAUNCH + ROUTED)
        self.write("deeplink-movie-input.log", launch_part + ROUTED)
        steps = [
            ("launches", "fwbeacons-track", "200"),
            ("perf", "chanperf", "200"), ("perf", "r2d2-bitmaps", "200"), ("perf", "sgnodes-count", "200"),
            ("perf", "sgnodes-sizes", "200"), ("perf", "graphics-frame-rate", "200"),
            ("deeplink-movie-launch", "launch", "200"), ("deeplink-movie-launch", "after", "dev"),
            ("deeplink-movie-input", "launch", "200"), ("deeplink-movie-input", "input-offset", str(len(launch_part.encode()))),
            ("deeplink-movie-input", "input", "202"), ("deeplink-movie-input", "after", "dev"),
            ("deeplink-episode", "skipped", "no ID"),
        ]
        self.write("steps.tsv", "".join("\t".join(row) + "\n" for row in steps))

    def rows(self, summary):
        return [line for line in summary.splitlines() if line.startswith("| M1")]

    def test_summary(self):
        self.prepare()
        summary = dc.summarize(self.out, [MOVIE_ID])
        rows = self.rows(summary)
        self.assertEqual(len(rows), 4)
        launch, perf, movie_launch, movie_input = rows
        self.assertIn("| M1 cold launch | 2026-10-22 | 55R625 (A109X) / 15.3.4 | — | — |", launch)
        self.assertIn("| PASS |", launch)
        self.assertIn("3 of 3 launches", launch)
        self.assertIn("median 1.75 s, max 1.75 s", launch)
        self.assertIn("15 s certification limit", launch)
        self.assertIn("Roku's beacon value: median 0.48 s", launch)
        self.assertIn("EXIT_USER_NAV ×3", launch)
        self.assertIn("does not list `app-launch-complete`", launch)
        self.assertIn("3 cold launches, `exit-app` between runs, awaited for up to 15 s; no reboot (uptime 10 min at the first launch)", launch)
        self.assertIn("| PASS |", perf)
        self.assertIn("memory used 83.7 MiB (14% of the 580.0 MiB foreground limit)", perf)
        self.assertIn("texture memory 25.6 MiB of 114.4 MiB (22%), 2 bitmaps", perf)
        self.assertIn("count=214", perf)
        self.assertIn("frame-rate=59", perf)
        self.assertIn("| (judge) |", movie_launch)
        self.assertIn("session signed_in (console)", movie_launch)
        self.assertIn("ECP `launch` HTTP 200", movie_launch)
        self.assertIn("ECP `input` HTTP 202", movie_input)
        self.assertIn("`AppLaunchComplete` 1.75 s after launch", movie_input)
        self.assertIn("`deeplink: route {\"contentId\":\"<id>\",\"to\":\"player\"}`", movie_input)
        self.assertIn("Not run, no ID given: episode.", summary)
        for leak in (MOVIE_ID, "192.0.2.44", "http://", "SERIAL", "st=signed"):
            self.assertNotIn(leak, summary)

    def test_input_trace_starts_at_the_input(self):
        self.prepare()
        text = LAUNCH.split("10-22 09:08:40.721")[0]
        self.write("deeplink-movie-input.log", text + '[INFO] nav: phase {"phase":"before"}\n' + ROUTED)
        steps = dc.read_text(os.path.join(self.out, "steps.tsv"))
        steps += "deeplink-movie-input\tinput-offset\t%d\n" % len((text + '[INFO] nav: phase {"phase":"before"}\n').encode())
        self.write("steps.tsv", steps)
        movie_input = self.rows(dc.summarize(self.out, [MOVIE_ID]))[3]
        self.assertNotIn("before", movie_input)

    def test_launch_over_the_milestone_limit_fails(self):
        self.prepare(model="3810X")
        slow = LAUNCH.replace("10-22 09:07:45.120", "10-22 09:07:52.000")
        self.write("launch-02.log", slow)
        self.write("launch-03.log", slow)
        launch = self.rows(dc.summarize(self.out))[0]
        self.assertIn("| FAIL |", launch)
        self.assertIn("median 8.63 s, max 8.63 s (Milestone 1 limit for the 3810X/3921X", launch)

    def test_missing_and_uncaptured_launches(self):
        self.prepare()
        self.write("launch-02.log", "")
        launch = self.rows(dc.summarize(self.out))[0]
        self.assertIn("| PARTIAL |", launch)
        self.assertIn("No beacon lines captured: runs 2.", launch)
        self.write("launch-03.log", "\n".join(l for l in LAUNCH.splitlines() if "Duration(478" not in l))
        launch = self.rows(dc.summarize(self.out))[0]
        self.assertIn("| FAIL |", launch)
        self.assertIn("No `AppLaunchComplete` within 30 s: runs 3.", launch)

    def test_stopped_run_is_partial(self):
        self.prepare()
        os.remove(os.path.join(self.out, "launch-03.log"))
        launch = self.rows(dc.summarize(self.out))[0]
        self.assertIn("| PARTIAL |", launch)
        self.assertIn("The run stopped after 2 launches of 3.", launch)

    def test_chanperf_without_the_perf_build(self):
        self.prepare()
        self.write("chanperf.xml", CHANPERF_FAILED)
        perf = self.rows(dc.summarize(self.out))[1]
        self.assertIn("| PARTIAL |", perf)
        self.assertIn("needs the perf build (`run_as_process=1`)", perf)

    def test_texture_over_the_limit_fails(self):
        self.prepare()
        self.write("r2d2-bitmaps.xml", R2D2.replace("<used>26841088</used>", "<used>90000000</used>"))
        self.assertIn("| FAIL |", self.rows(dc.summarize(self.out))[1])


EXIT_SH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exit.sh")

# exit_dev with a stubbed ECP: the exit-app/dev status, then the foreground
# verdicts the polls see in turn (the last repeats). Polls run in command
# substitutions, so a file counts them. Prints the ECP calls, then "left"
# once exit_dev returns.
EXIT_HARNESS = """
set -euo pipefail
. "$1"
status=$2
shift 2
verdicts=("$@")
counter=$(mktemp)
trap 'rm -f "$counter"' EXIT
echo 0 > "$counter"
EXIT_TIMEOUT=1
EXIT_POLL=0.05
ecp() { echo "ecp $1 $2" >&2; printf '%s\\n' "$status"; }
foreground() {
    local polls i
    polls=$(cat "$counter")
    echo $((polls + 1)) > "$counter"
    i=$polls
    [ "$i" -lt "${#verdicts[@]}" ] || i=$((${#verdicts[@]} - 1))
    echo "${verdicts[$i]}"
}
die() { echo "die: $*" >&2; exit 1; }
exit_dev
echo "left after $(cat "$counter") polls"
"""


class ExitDevTests(unittest.TestCase):
    """scripts/device-check/exit.sh, run by bash with ECP stubbed."""

    def run_exit(self, status, *verdicts):
        return subprocess.run(["bash", "-c", EXIT_HARNESS, "exit-test", EXIT_SH, status] + list(verdicts or ("home Roku",)),
                              capture_output=True, text=True, timeout=20)

    def test_waits_for_an_exit_answered_200_or_202_to_leave_the_foreground(self):
        for status in ("200", "202"):
            run = self.run_exit(status, "dev Silo", "dev Silo", "home Roku")
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("left after 3 polls", run.stdout)
            self.assertIn("ecp POST exit-app/dev", run.stderr)

    def test_does_not_wait_when_the_dev_app_was_not_running(self):
        run = self.run_exit("404", "dev Silo")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("left after 0 polls", run.stdout)

    def test_stops_on_a_refused_or_missing_answer(self):
        for status in ("403", "500", "000"):
            run = self.run_exit(status)
            self.assertEqual(run.returncode, 1)
            self.assertIn("die: ECP exit-app/dev answered HTTP %s" % status, run.stderr)
            self.assertNotIn("left", run.stdout)

    def test_stops_when_an_accepted_exit_never_finishes(self):
        run = self.run_exit("202", "dev Silo")
        self.assertEqual(run.returncode, 1)
        self.assertIn("die: the dev app was still in the foreground 1 s after ECP exit-app/dev answered HTTP 202", run.stderr)

    def test_leaves_other_foregrounds_to_the_ownership_checks(self):
        run = self.run_exit("200", "refuse another app is in the foreground (Netflix)")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("left after 1 polls", run.stdout)


class CommandLineTests(unittest.TestCase):
    def run_main(self, *args):
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            status = dc.main(["device_check.py"] + list(args))
        return status, output.getvalue()

    def test_foreground_and_idle(self):
        with tempfile.TemporaryDirectory() as folder:
            active, playing = os.path.join(folder, "active.xml"), os.path.join(folder, "playing.txt")
            with open(active, "w") as handle:
                handle.write(ACTIVE_HDMI1)
            self.assertEqual(self.run_main("foreground", active, "-", "-", "tvinput.hdmi1"), (0, "input tvinput.hdmi1\n"))
            with open(playing, "w") as handle:
                handle.write("Device state: Paused\n")
            self.assertEqual(self.run_main("idle", playing), (1, "Paused\n"))
            with open(playing, "w") as handle:
                handle.write("Device state: Idle\n")
            self.assertEqual(self.run_main("idle", playing), (0, "Idle\n"))

    def test_usage(self):
        self.assertEqual(self.run_main("nonsense")[0], 2)


if __name__ == "__main__":
    unittest.main()
