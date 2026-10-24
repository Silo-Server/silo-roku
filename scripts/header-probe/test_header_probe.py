"""Tests for header_probe.py. Run from the repository root:

    python3 -I -B -m unittest discover -s scripts/header-probe
"""

import contextlib
import http.client
import http.server
import io
import json
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
import urllib.parse

import header_probe as probe

SECRET_TOKEN = "Bearer SECRET-ACCESS-TOKEN"
SECRET_PROFILE_TOKEN = "SECRET-PROFILE-TOKEN"
SECRET_QUERY = "st=SECRET-SIGNED-TOKEN"
# Large enough that loopback socket buffers cannot absorb the whole response
# before a client that reads little and hangs up is noticed.
LONG_ENTRIES = 200_000
BIG_BODY = 8 * 1024 * 1024
DRIP_CHUNK = b"\0" * 1024
DRIP_INTERVAL = 0.05


def long_playlist():
    lines = ["#EXTM3U", "#EXT-X-VERSION:8", '#EXT-X-DEFINE:NAME="st",VALUE="signed"']
    for number in range(LONG_ENTRIES):
        lines += ["#EXTINF:2.0,", "segment/%d.ts?st={$st}" % number]
    return ("\n".join(lines) + "\n").encode()


class PathClassTests(unittest.TestCase):
    def test_classes(self):
        cases = {
            "/api/v2/system/info": "api",
            "/api/v2/auth/login": "api",
            "/api/v2/playback/start": "api",
            "/api/v2/stream/11111111-1111-4111-8111-111111111111": "stream",
            "/stream/v3/11111111/token-path": "stream",
            "/api/v2/playback/transcode/s1/master.m3u8": "playlist",
            "/stream/v3/s1/master.m3u8": "playlist",
            "/api/v2/playback/transcode/s1/segment/init.mp4": "segment",
            "/api/v2/playback/transcode/s1/segment/12.m4s": "segment",
            "/stream/v3/s1/segment/12.ts": "segment",
            "/api/v2/playback/transcode/s1/segment/subs_3.vtt": "subtitle",
            "/api/v2/stream/s1/subtitles/0.srt": "subtitle",
            "/api/v2/stream/s1/subtitles/1/fonts": "subtitle",
            "/api/v2/images/poster/1.jpg": "other",
            "/favicon.ico": "other",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(probe.path_class(path), expected)

    def test_ignores_query_and_case(self):
        self.assertEqual(probe.path_class("/API/V2/STREAM/s1?st=x.m3u8"), "stream")


class FactTests(unittest.TestCase):
    def test_credential_presence_is_case_insensitive(self):
        presence = probe.credential_presence([("AUTHORIZATION", "x"), ("x-profile-id", "1"), ("Accept", "*/*")])
        self.assertEqual(presence, {"authorization": True, "x_profile_id": True, "x_profile_token": False})

    def test_query_facts(self):
        self.assertEqual(probe.query_facts(""), {"query": False, "duplicate_query_keys": False})
        self.assertEqual(probe.query_facts("st=a&seek=1"), {"query": True, "duplicate_query_keys": False})
        self.assertEqual(probe.query_facts("st=a&st=a"), {"query": True, "duplicate_query_keys": True})

    def test_record_holds_only_the_fixed_vocabulary(self):
        entry = probe.record("origin", "GET", "segment", 200, {"authorization": True}, "forward")
        self.assertEqual(set(entry), {"time", "listener", "method", "class", "status", "action", "authorization", "x_profile_id", "x_profile_token"})
        self.assertTrue(entry["authorization"])
        self.assertFalse(entry["x_profile_token"])

    def test_record_keeps_only_known_extra_facts(self):
        facts = {"query": "st=x", "duplicate_query_keys": 0, "ext_x_define": 1, "playlist_entries": "3", "bytes": "12", "path": "/api/v2/stream/s1"}
        entry = probe.record("origin", "GET", "playlist", 200, {}, "forward", facts)
        self.assertEqual({key: entry[key] for key in probe.EXTRA_FACTS}, {"query": True, "duplicate_query_keys": False, "ext_x_define": True, "playlist_entries": 3, "bytes": 12})
        self.assertNotIn("path", entry)

    def test_record_accepts_abort(self):
        self.assertEqual(probe.record("origin", "GET", "stream", 206, {}, "abort")["action"], "abort")

    def test_playlist_facts_count_uri_lines(self):
        self.assertEqual(probe.playlist_facts(PlaylistTests.PLAYLIST), {"ext_x_define": True, "playlist_entries": 4})
        self.assertEqual(probe.playlist_facts("#EXTM3U\r\n#EXT-X-STREAM-INF:BANDWIDTH=1\r\n  v0.m3u8\r\n\r\n"), {"ext_x_define": False, "playlist_entries": 1})
        self.assertEqual(probe.playlist_facts(""), {"ext_x_define": False, "playlist_entries": 0})

    def test_record_replaces_unexpected_words(self):
        entry = probe.record("/api/v2/stream/s1", "GET /x?st=1", "/secret", 200, {}, "leak")
        self.assertEqual((entry["listener"], entry["method"], entry["class"], entry["action"]), ("unknown", "other", "other", "error"))

    def test_redirect_location_keeps_path_and_query(self):
        self.assertEqual(probe.redirect_location("http://192.0.2.20:8081/", "/api/v2/stream/s1?st=t"), "http://192.0.2.20:8081/api/v2/stream/s1?st=t")


SESSION = "11111111-1111-4111-8111-111111111111"


class PlaybackBodyTests(unittest.TestCase):
    def test_only_playback_mutations_match(self):
        cases = {
            ("POST", "/api/v2/playback/start"): "start",
            ("POST", "/api/v2/playback/route-events"): "route_event",
            ("POST", "/api/v2/playback/%s/replan" % SESSION): "replan",
            ("POST", "/api/v2/playback/%s/progress?x=1" % SESSION): "progress",
            ("DELETE", "/api/v2/playback/%s" % SESSION): "stop",
            ("GET", "/api/v2/playback/capabilities"): None,
            ("GET", "/api/v2/playback/transcode/s1/master.m3u8"): None,
            ("PUT", "/api/v2/playback/start"): None,
            ("DELETE", "/api/v2/playback/start"): None,
            ("DELETE", "/api/v2/playback/.."): None,
            ("POST", "/api/v2/playback/a/b/replan"): None,
            ("POST", "/api/v2/playback/a%2F..%2Fauth/replan"): None,
            ("POST", "/api/v2/playback/start/../../auth/login"): None,
            ("POST", "/api/v2/auth/login"): None,
            ("POST", "/api/v2/auth/refresh"): None,
            ("POST", "/api/v2/auth/device/token"): None,
            ("POST", "/api/v2/profiles/p1/select"): None,
            ("POST", "/api/v2/profiles/p1/pin/verify"): None,
            ("POST", "/api/v2/sessions/current"): None,
            ("POST", "/api/v2/playback"): None,
        }
        for (method, path), expected in cases.items():
            with self.subTest(method=method, path=path):
                self.assertEqual(probe.playback_body_op(method, path), expected)

    def test_redacts_credential_names_at_any_depth_and_url_values(self):
        body = {
            "file_id": "42",
            "profile_token": "SECRET-1",
            "X-Profile-Token": "SECRET-2",
            "nested": {"PIN": "SECRET-3", "pinCode": "SECRET-4", "Password": "SECRET-5", "client_secret": "SECRET-6"},
            "items": [{"requestSignature": "SECRET-7"}, {"stream_url": "/api/v2/stream/s1?st=SECRET-8"}],
            "diagnostics": {"message": "Video error -5 at https://h/x?sig=SECRET-9", "first_frame_ms": "4604"},
            "position": 12.5,
            "is_paused": False,
        }
        redacted = probe.redact_body(body)
        self.assertNotIn("SECRET", json.dumps(redacted))
        self.assertEqual(redacted["file_id"], "42")
        self.assertEqual(redacted["profile_token"], probe.REDACTED)
        self.assertEqual(redacted["nested"]["pinCode"], probe.REDACTED)
        self.assertEqual(redacted["items"][1]["stream_url"], probe.REDACTED)
        self.assertEqual(redacted["diagnostics"], {"message": probe.REDACTED, "first_frame_ms": "4604"})
        self.assertEqual((redacted["position"], redacted["is_paused"]), (12.5, False))

    def test_body_facts(self):
        self.assertEqual(probe.body_facts("stop", b""), {"op": "stop", "body_bytes": 0})
        self.assertEqual(probe.body_facts("start", b"password=SECRET"), {"op": "start", "body_bytes": 15, "body_json": False})
        facts = probe.body_facts("replan", b'{"operation":"seek_reanchor","position_seconds":1411}')
        self.assertEqual(facts["body"], {"operation": "seek_reanchor", "position_seconds": 1411})

    def test_long_bodies_keep_a_redacted_prefix(self):
        body = json.dumps({"a_token": "SECRET", "padding": "x" * 1000}).encode()
        facts = probe.body_facts("start", body, limit=300)
        self.assertTrue(facts["body_truncated"])
        self.assertEqual(len(facts["body_prefix"]), 300)
        self.assertNotIn("body", facts)
        self.assertNotIn("SECRET", json.dumps(facts))
        self.assertEqual(facts["body_bytes"], len(body))

    def test_record_keeps_bodies_only_for_known_calls(self):
        entry = probe.record("origin", "POST", "api", 200, {}, "forward", None, {"op": "start", "body_bytes": 2, "body": {}, "path": "/x"})
        self.assertEqual((entry["op"], entry["body_bytes"], entry["body"]), ("start", 2, {}))
        self.assertNotIn("path", entry)
        entry = probe.record("origin", "POST", "api", 200, {}, "forward", None, {"op": "login", "body": {"x": 1}})
        self.assertNotIn("body", entry)
        self.assertNotIn("op", entry)

    def test_body_limit_argument(self):
        self.assertEqual(probe.build_parser().parse_args(["--upstream", "http://h"]).playback_body_max, probe.DEFAULT_BODY_MAX)
        for value in ("0", "255", "-1", "x", "2000000"):
            with self.subTest(value=value), self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                probe.build_parser().parse_args(["--upstream", "http://h", "--playback-body-max", value])


class PlaylistTests(unittest.TestCase):
    PLAYLIST = "\n".join(
        [
            "#EXTM3U",
            "#EXT-X-VERSION:8",
            '#EXT-X-DEFINE:NAME="st",VALUE="signed"',
            '#EXT-X-MAP:URI="segment/init.mp4?st={$st}"',
            '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="English",URI="subs.m3u8"',
            "#EXTINF:2.0,",
            "segment/0.m4s?st={$st}",
            "#EXTINF:2.0,",
            "https://silo.example/api/v2/playback/transcode/s1/segment/1.m4s",
            "#EXTINF:2.0,",
            "https://proxy.example/stream/v3/s1/segment/2.m4s",
            "{$base}/segment/3.m4s",
            "",
        ]
    )

    def rewrite(self):
        return probe.rewrite_playlist(self.PLAYLIST, "/api/v2/playback/transcode/s1/master.m3u8?st=x", "http://192.0.2.20:8081", "https://silo.example").split("\n")

    def test_relative_children_become_absolute_on_the_target(self):
        lines = self.rewrite()
        self.assertIn("http://192.0.2.20:8081/api/v2/playback/transcode/s1/segment/0.m4s?st={$st}", lines)
        self.assertIn('#EXT-X-MAP:URI="http://192.0.2.20:8081/api/v2/playback/transcode/s1/segment/init.mp4?st={$st}"', lines)
        self.assertIn('#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="English",URI="http://192.0.2.20:8081/api/v2/playback/transcode/s1/subs.m3u8"', lines)

    def test_upstream_absolute_children_move_and_others_stay(self):
        lines = self.rewrite()
        self.assertIn("http://192.0.2.20:8081/api/v2/playback/transcode/s1/segment/1.m4s", lines)
        self.assertIn("https://proxy.example/stream/v3/s1/segment/2.m4s", lines)
        self.assertIn("{$base}/segment/3.m4s", lines)

    def test_defines_and_tags_are_untouched(self):
        lines = self.rewrite()
        self.assertEqual(lines[:3], ["#EXTM3U", "#EXT-X-VERSION:8", '#EXT-X-DEFINE:NAME="st",VALUE="signed"'])
        self.assertEqual(lines[-1], "")


class ControlTests(unittest.TestCase):
    def test_hold_seconds(self):
        cases = {None: 0, "": probe.DEFAULT_HOLD_SECONDS, "soon": probe.DEFAULT_HOLD_SECONDS, "nan": probe.DEFAULT_HOLD_SECONDS, "12": 12, "2.5": 2.5, "0": 0, "-4": 0, "inf": probe.MAX_HOLD_SECONDS, "9999": probe.MAX_HOLD_SECONDS}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(probe.hold_seconds(text), expected)

    def test_refusal(self):
        cases = {None: None, "": "reset", "reset": "reset", "on": "reset", "close": "close", "CLOSE": "close"}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(probe.refusal(text), expected)

    def test_throttle_kbps(self):
        cases = {None: None, "": probe.DEFAULT_THROTTLE_KBPS, "fast": probe.DEFAULT_THROTTLE_KBPS, "3M": probe.DEFAULT_THROTTLE_KBPS, "nan": probe.DEFAULT_THROTTLE_KBPS, "3000": 3000, "2500.5": 2500.5, "0": probe.MIN_THROTTLE_KBPS, "-5": probe.MIN_THROTTLE_KBPS, "inf": probe.MAX_THROTTLE_KBPS, "9e9": probe.MAX_THROTTLE_KBPS}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(probe.throttle_kbps(text), expected)

    def test_record_keeps_only_known_control_facts(self):
        entry = probe.record("origin", "POST", "api", 0, {}, "hold", control={"hold_seconds": "2.5", "refusal": "explode", "path": "/x"})
        self.assertEqual((entry["action"], entry["status"], entry["hold_seconds"]), ("hold", 0, 2.5))
        self.assertNotIn("refusal", entry)
        self.assertNotIn("path", entry)
        entry = probe.record("origin", "GET", "segment", 0, {}, "refuse", control={"refusal": "reset"})
        self.assertEqual((entry["action"], entry["refusal"]), ("refuse", "reset"))
        self.assertNotIn("hold_seconds", entry)
        entry = probe.record("origin", "GET", "stream", 0, {}, "throttle", control={"throttle_kbps": "3000", "open": True})
        self.assertEqual((entry["action"], entry["throttle_kbps"], entry["open"]), ("throttle", 3000.0, True))
        self.assertNotIn("open", probe.record("origin", "POST", "api", 0, {}, "hold", control={"hold_seconds": 1, "open": True}))

    def test_control_files_are_named_after_the_origin_port(self):
        args = probe.build_parser().parse_args(["--upstream", "http://h", "--origin-listen", "0.0.0.0:8180", "--control-dir", "/srv/lab"])
        self.assertEqual(probe.Config(args).controls, {"hold-replan": "/srv/lab/hold-replan.8180", "refuse-media": "/srv/lab/refuse-media.8180", "throttle-media": "/srv/lab/throttle-media.8180"})
        controls = probe.Config(probe.build_parser().parse_args(["--upstream", "http://h"])).controls
        self.assertEqual(controls["refuse-media"], os.path.join(os.getcwd(), "refuse-media.8080"))


class ArgumentTests(unittest.TestCase):
    def test_redirect_rules(self):
        self.assertEqual(probe.parse_redirect("segment=foreign"), ("segment", "foreign"))
        self.assertEqual(probe.parse_redirect("all=plain"), ("all", "plain"))
        for value in ("segment", "segment=elsewhere", "posters=foreign"):
            with self.subTest(value=value), self.assertRaises(Exception):
                probe.parse_redirect(value)

    def test_origins(self):
        self.assertEqual(probe.origin_of("https://silo.example:8443/x"), "https://silo.example:8443")
        for value in ("ftp://silo.example", "https://user:pw@silo.example", "/relative"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.origin_of(value)

    def test_targets_need_public_urls(self):
        args = probe.build_parser().parse_args(["--upstream", "http://127.0.0.1:1", "--redirect", "api=foreign"])
        with self.assertRaises(SystemExit):
            probe.Config(args)


class Upstream(http.server.BaseHTTPRequestHandler):
    """A stand-in Silo that records which credential headers reached it."""

    protocol_version = "HTTP/1.1"
    seen = []
    # How many Content-Length headers each request with a body carried.
    lengths = []
    # Set when a dripped body's connection broke before it was all written.
    dropped = threading.Event()

    def log_message(self, *args):
        pass

    def do_GET(self):
        Upstream.seen.append(probe.credential_presence(list(self.headers.items())))
        path, _, query = self.path.partition("?")
        if "/drip" in path:
            params = urllib.parse.parse_qs(query)
            self.drip(float(params.get("s", ["5"])[0]), int(params.get("kib", ["1"])[0]))
            return
        if path.endswith("/short.m3u8"):
            # Promises more than it sends, then closes: a truncated read.
            self.close_connection = True
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b"#EXTM3U\n")
            return
        if path.endswith("/long.m3u8"):
            body = long_playlist()
        elif path.endswith(".m3u8"):
            body = b"#EXTM3U\n#EXTINF:2.0,\nsegment/0.m4s?st=t\n"
        elif path.endswith("/big.ts"):
            body = b"\0" * BIG_BODY
        else:
            body = json.dumps({"api_major": 2}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            Upstream.dropped.set()  # the probe hung up after its client did, or a cut

    def drip(self, seconds, kib=1):
        """A body sent slowly over `seconds`, as a long range request is read:
        `kib` KiB each DRIP_INTERVAL."""
        count = int(seconds / DRIP_INTERVAL)
        chunk = DRIP_CHUNK * kib
        self.send_response(200)
        self.send_header("Content-Length", str(count * len(chunk)))
        self.end_headers()
        for _ in range(count):
            try:
                self.wfile.write(chunk)
            except OSError:
                Upstream.dropped.set()
                return
            time.sleep(DRIP_INTERVAL)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        Upstream.lengths.append(len(self.headers.get_all("Content-Length") or []))
        Upstream.seen.append(probe.credential_presence(list(self.headers.items())))
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_DELETE = do_POST


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        Upstream.seen = []
        Upstream.lengths = []
        Upstream.dropped = threading.Event()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.control_dir = directory.name
        self.upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        self.output = io.StringIO()
        self.recorder = probe.Recorder(self.output)
        self.servers = [self.upstream]
        threading.Thread(target=self.upstream.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

    def tearDown(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()

    def start(self, *extra):
        upstream = "http://127.0.0.1:%d" % self.upstream.server_address[1]
        args = probe.build_parser().parse_args(["--upstream", upstream, "--foreign-public", "http://127.0.0.1:1", "--control-dir", self.control_dir, *extra])
        config = self.config = probe.Config(args)
        origin = probe.ProbeServer(("127.0.0.1", 0), "origin", config, self.recorder)
        foreign = probe.ProbeServer(("127.0.0.1", 0), "foreign", config, self.recorder)
        config.public["foreign"] = "http://127.0.0.1:%d" % foreign.server_address[1]
        for server in (origin, foreign):
            self.servers.append(server)
            threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return origin.server_address[1], foreign.server_address[1]

    def request(self, port, method, path, body=None, credentials=True):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        headers = {"Authorization": SECRET_TOKEN, "X-Profile-Id": "p-owner", "X-Profile-Token": SECRET_PROFILE_TOKEN} if credentials else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response, data

    def read_then_hang_up(self, port, path, keep=4096):
        """Reads `keep` bytes of the response, then resets the connection, as
        Roku does when it has what it needs or refuses a playlist."""
        client = socket.socket()
        client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        client.settimeout(10)
        client.connect(("127.0.0.1", port))
        client.sendall(("GET %s HTTP/1.1\r\nHost: probe\r\nAuthorization: %s\r\n\r\n" % (path, SECRET_TOKEN)).encode())
        received = 0
        while received < keep:
            data = client.recv(keep - received)
            if not data:
                break
            received += len(data)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        client.close()

    def raw_get(self, port, path):
        """Sends a GET and returns the bytes that came back and how the
        connection ended: "close" (an orderly close) or "reset"."""
        client = socket.create_connection(("127.0.0.1", port), timeout=10)
        client.sendall(("GET %s HTTP/1.1\r\nHost: probe\r\nAuthorization: %s\r\nConnection: close\r\n\r\n" % (path, SECRET_TOKEN)).encode())
        received = b""
        try:
            while True:
                data = client.recv(65536)
                if not data:
                    return received, "close"
                received += data
        except ConnectionResetError:
            return received, "reset"
        finally:
            client.close()

    def open_get(self, port, path, rcvbuf=None):
        """Sends a GET and reads up to the end of the response headers;
        returns the socket, which the test reads on (finish_get) or leaves."""
        client = socket.socket()
        if rcvbuf:
            client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
        client.settimeout(10)
        client.connect(("127.0.0.1", port))
        client.sendall(("GET %s HTTP/1.1\r\nHost: probe\r\nAuthorization: %s\r\nConnection: close\r\n\r\n" % (path, SECRET_TOKEN)).encode())
        received = b""
        while b"\r\n\r\n" not in received:
            data = client.recv(1)
            if not data:
                break
            received += data
        self.addCleanup(client.close)
        return client, received

    def finish_get(self, client):
        """Reads to the end; returns the body bytes read and how the connection
        ended: "close" or "reset"."""
        received = 0
        try:
            while True:
                data = client.recv(65536)
                if not data:
                    return received, "close"
                received += len(data)
        except ConnectionResetError:
            return received, "reset"

    def read_for(self, client, seconds):
        """Reads for `seconds`; returns the number of body bytes that arrived."""
        received = 0
        deadline = time.monotonic() + seconds
        try:
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    return received
                client.settimeout(left)
                try:
                    data = client.recv(65536)
                except socket.timeout:
                    return received
                if not data:
                    return received
                received += len(data)
        finally:
            client.settimeout(10)

    def control(self, name, text=None):
        """Writes a control file of the running probe, or removes it when `text` is None."""
        path = self.config.controls[name]
        if text is None:
            os.remove(path)
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def entries(self, at_least=1):
        # The probe logs a request after finishing its response, so wait for it.
        deadline = time.monotonic() + 5
        while True:
            lines = [json.loads(line) for line in self.output.getvalue().splitlines()]
            if len([line for line in lines if "listener" in line and "time" in line]) >= at_least or time.monotonic() > deadline:
                return lines
            time.sleep(0.01)

    def test_forwards_and_logs_only_presence(self):
        origin, _ = self.start()
        response, data = self.request(origin, "POST", "/api/v2/auth/login?" + SECRET_QUERY, body=b'{"password":"SECRET-PASSWORD"}')
        self.assertEqual(response.status, 200)
        self.assertEqual(data, b'{"password":"SECRET-PASSWORD"}')
        self.assertEqual(Upstream.seen, [{"authorization": True, "x_profile_id": True, "x_profile_token": True}])
        [entry] = self.entries()
        self.assertEqual((entry["listener"], entry["class"], entry["status"], entry["action"]), ("origin", "api", 200, "forward"))
        self.assertTrue(entry["authorization"] and entry["x_profile_id"] and entry["x_profile_token"])
        self.assertNotIn("query", entry)
        self.assertNotIn("SECRET", self.output.getvalue())
        self.assertNotIn("/api/", self.output.getvalue())

    def test_a_fixed_length_body_goes_upstream_with_one_content_length(self):
        origin, _ = self.start()
        response, data = self.request(origin, "POST", "/api/v2/playback/progress", body=b'{"position_ms":1}')
        self.assertEqual((response.status, data), (200, b'{"position_ms":1}'))
        self.assertEqual(Upstream.lengths, [1])

    def test_a_slow_body_is_relayed_as_it_arrives(self):
        origin, _ = self.start()
        # 1 KiB each DRIP_INTERVAL for 1 s is 20 KiB, less than one CHUNK.
        client, head = self.open_get(origin, "/api/v2/stream/s1/drip?s=1")
        self.assertIn(b" 200 ", head.split(b"\r\n", 1)[0])
        early = self.read_for(client, 0.3)
        self.assertGreater(early, 0)
        # Read to the end, so no relay is left to break in a later test.
        rest, how = self.finish_get(client)
        self.assertEqual((early + rest, how), (int(1 / DRIP_INTERVAL) * len(DRIP_CHUNK), "close"))

    def test_a_truncated_playlist_answers_one_bad_gateway(self):
        origin, _ = self.start()
        received, _ = self.raw_get(origin, "/api/v2/playback/transcode/s1/short.m3u8")
        self.assertTrue(received.startswith(b"HTTP/1.1 502 "), received[:40])
        self.assertEqual(received.count(b"HTTP/1."), 1)
        [entry] = self.entries()
        self.assertEqual((entry["status"], entry["action"]), (502, "error"))

    def test_redirects_a_class_to_the_foreign_listener(self):
        origin, foreign = self.start("--redirect", "segment=foreign")
        path = "/api/v2/playback/transcode/s1/segment/1.m4s?" + SECRET_QUERY
        response, _ = self.request(origin, "GET", path)
        self.assertEqual(response.status, 302)
        self.assertEqual(response.getheader("Location"), "http://127.0.0.1:%d%s" % (foreign, path))
        self.assertEqual(Upstream.seen, [])
        [entry] = self.entries()
        self.assertEqual((entry["class"], entry["status"], entry["action"]), ("segment", 302, "redirect"))
        self.assertNotIn("SECRET", self.output.getvalue())

    def test_alerts_when_credentials_reach_the_foreign_listener(self):
        _, foreign = self.start()
        self.request(foreign, "GET", "/api/v2/stream/s1", credentials=False)
        self.entries(1)
        self.assertNotIn("alert", self.output.getvalue())
        self.request(foreign, "GET", "/api/v2/stream/s1")
        alerts = [entry for entry in self.entries(2) if "alert" in entry]
        self.assertEqual(alerts, [{"alert": "credential header reached a non-origin listener", "listener": "foreign", "class": "stream"}])
        self.recorder.summary()
        summary = {entry["summary"]: entry for entry in self.entries() if "summary" in entry}
        self.assertTrue(summary["foreign"]["credential_headers_seen"])
        self.assertEqual(summary["foreign"]["requests"], 2)
        self.assertFalse(summary["origin"]["credential_headers_seen"])

    def test_rewrites_playlists_to_absolute_foreign_children(self):
        origin, foreign = self.start("--absolute-children", "foreign")
        response, data = self.request(origin, "GET", "/api/v2/playback/transcode/s1/master.m3u8?" + SECRET_QUERY)
        self.assertEqual(response.status, 200)
        self.assertIn(b"http://127.0.0.1:%d/api/v2/playback/transcode/s1/segment/0.m4s?st=t" % foreign, data)
        self.assertEqual(int(response.getheader("Content-Length")), len(data))
        self.assertEqual(self.entries()[0]["action"], "rewrite")

    def test_extra_facts_report_sizes_defines_and_repeated_parameters(self):
        origin, _ = self.start("--extra-facts")
        self.request(origin, "GET", "/api/v2/playback/transcode/s1/master.m3u8?st=a&st=a")
        self.request(origin, "GET", "/api/v2/playback/transcode/s1/segment/0.m4s?st=a")
        entries = {entry["class"]: entry for entry in self.entries(2) if "time" in entry}
        playlist, segment = entries["playlist"], entries["segment"]
        self.assertEqual((playlist["ext_x_define"], playlist["duplicate_query_keys"], playlist["query"]), (False, True, True))
        self.assertEqual(playlist["playlist_entries"], 1)
        self.assertGreater(playlist["bytes"], 0)
        self.assertEqual(segment["bytes"], len(json.dumps({"api_major": 2})))
        self.assertFalse(segment["duplicate_query_keys"])

    def test_an_aborted_playlist_keeps_its_status_and_facts(self):
        origin, _ = self.start("--extra-facts")
        self.read_then_hang_up(origin, "/api/v2/playback/transcode/s1/long.m3u8?" + SECRET_QUERY)
        [entry] = [entry for entry in self.entries() if "time" in entry]
        self.assertEqual((entry["class"], entry["status"], entry["action"]), ("playlist", 200, "abort"))
        self.assertEqual((entry["ext_x_define"], entry["playlist_entries"], entry["bytes"]), (True, LONG_ENTRIES, len(long_playlist())))
        self.assertTrue(entry["authorization"])
        self.assertNotIn("SECRET", self.output.getvalue())

    def test_an_aborted_segment_logs_the_bytes_relayed(self):
        origin, _ = self.start("--extra-facts")
        self.read_then_hang_up(origin, "/api/v2/playback/transcode/s1/segment/big.ts")
        [entry] = [entry for entry in self.entries() if "time" in entry]
        self.assertEqual((entry["class"], entry["status"], entry["action"]), ("segment", 200, "abort"))
        self.assertGreater(entry["bytes"], 0)
        self.assertLess(entry["bytes"], BIG_BODY)
        self.assertNotIn("playlist_entries", entry)

    def test_playback_bodies_are_logged_redacted(self):
        origin, _ = self.start("--playback-bodies")
        start = {"file_id": "42", "profile_token": SECRET_PROFILE_TOKEN, "client_playback_context": {"pin": "SECRET-PIN"}}
        response, data = self.request(origin, "POST", "/api/v2/playback/start", body=json.dumps(start).encode())
        self.assertEqual(json.loads(data), start)  # forwarded unchanged
        self.request(origin, "DELETE", "/api/v2/playback/%s" % SESSION, body=b'{"stop_id":"s1","position":1441}')
        start_entry, stop_entry = [entry for entry in self.entries(2) if "time" in entry]
        self.assertEqual((start_entry["op"], start_entry["body_bytes"]), ("start", len(json.dumps(start))))
        self.assertEqual(start_entry["body"], {"file_id": "42", "profile_token": probe.REDACTED, "client_playback_context": {"pin": probe.REDACTED}})
        self.assertEqual((stop_entry["op"], stop_entry["body"]), ("stop", {"stop_id": "s1", "position": 1441}))
        self.assertNotIn("SECRET", self.output.getvalue())
        self.assertNotIn("/api/", self.output.getvalue())

    def test_auth_and_profile_bodies_are_never_logged(self):
        origin, _ = self.start("--playback-bodies")
        self.request(origin, "POST", "/api/v2/auth/login", body=b'{"username":"u","password":"SECRET-PASSWORD"}')
        self.request(origin, "POST", "/api/v2/profiles/p1/pin/verify", body=b'{"pin":"SECRET-PIN"}')
        for entry in [entry for entry in self.entries(2) if "time" in entry]:
            self.assertNotIn("body", entry)
            self.assertNotIn("op", entry)
        self.assertNotIn("SECRET", self.output.getvalue())

    def test_playback_bodies_need_the_flag(self):
        origin, _ = self.start()
        self.request(origin, "POST", "/api/v2/playback/start", body=b'{"file_id":"BODY-MARKER"}')
        [entry] = [entry for entry in self.entries() if "time" in entry]
        self.assertNotIn("body", entry)
        self.assertNotIn("BODY-MARKER", self.output.getvalue())

    def test_an_abort_without_extra_facts_still_logs_the_status(self):
        origin, _ = self.start()
        self.read_then_hang_up(origin, "/api/v2/stream/big.ts")
        [entry] = [entry for entry in self.entries() if "time" in entry]
        self.assertEqual((entry["class"], entry["status"], entry["action"]), ("stream", 200, "abort"))
        self.assertNotIn("bytes", entry)

    def test_modes_are_off_without_control_files(self):
        origin, _ = self.start()
        self.assertEqual(os.listdir(self.control_dir), [])
        response, _ = self.request(origin, "POST", "/api/v2/playback/%s/replan" % SESSION, body=b"{}")
        self.assertEqual(response.status, 200)
        data, _ = self.raw_get(origin, "/api/v2/playback/transcode/s1/segment/0.m4s")
        self.assertTrue(data.startswith(b"HTTP/1.1 200 "))
        self.assertEqual([entry["action"] for entry in self.entries(2) if "time" in entry], ["forward", "forward"])

    def test_holds_a_replan_before_forwarding_it(self):
        origin, _ = self.start("--playback-bodies")
        self.control("hold-replan", "1\n")
        result = {}

        def replan():
            began = time.monotonic()
            result["response"], _ = self.request(origin, "POST", "/api/v2/playback/%s/replan?%s" % (SESSION, SECRET_QUERY), body=b'{"operation":"track_change"}')
            result["seconds"] = time.monotonic() - began

        thread = threading.Thread(target=replan)
        thread.start()
        hold = next(entry for entry in self.entries() if entry.get("action") == "hold")
        self.assertEqual(Upstream.seen, [])  # held: not forwarded yet
        thread.join(10)
        self.assertEqual(result["response"].status, 200)
        self.assertGreaterEqual(result["seconds"], 1)
        self.assertEqual(len(Upstream.seen), 1)
        self.assertEqual((hold["method"], hold["class"], hold["status"], hold["hold_seconds"]), ("POST", "api", 0, 1.0))
        self.assertTrue(hold["authorization"] and hold["x_profile_token"])
        self.assertNotIn("body", hold)
        forward = [entry for entry in self.entries(2) if "time" in entry][1]
        self.assertEqual((forward["action"], forward["status"], forward["op"], forward["body"]), ("forward", 200, "replan", {"operation": "track_change"}))
        self.recorder.summary()
        summary = {entry["summary"]: entry for entry in self.entries() if "summary" in entry}
        self.assertEqual(summary["origin"]["requests"], 1)
        self.assertNotIn("SECRET", self.output.getvalue())
        self.assertNotIn("/api/", self.output.getvalue())

    def test_only_replans_are_held_and_the_hold_switches_off_at_run_time(self):
        origin, _ = self.start()
        self.control("hold-replan", "5")
        began = time.monotonic()
        self.request(origin, "POST", "/api/v2/playback/%s/progress" % SESSION, body=b"{}")
        self.request(origin, "POST", "/api/v2/playback/start", body=b"{}")
        self.request(origin, "GET", "/api/v2/stream/s1")
        self.control("hold-replan")
        self.request(origin, "POST", "/api/v2/playback/%s/replan" % SESSION, body=b"{}")
        self.assertLess(time.monotonic() - began, 4)
        self.assertEqual([entry["action"] for entry in self.entries(4) if "time" in entry], ["forward"] * 4)

    def test_refuses_media_with_a_reset_until_the_file_is_removed(self):
        origin, _ = self.start("--extra-facts")
        self.control("refuse-media", "")
        media = ("/api/v2/stream/s1?" + SECRET_QUERY, "/api/v2/playback/transcode/s1/master.m3u8", "/api/v2/playback/transcode/s1/segment/0.m4s")
        for path in media:
            with self.subTest(path=path):
                self.assertEqual(self.raw_get(origin, path), (b"", "reset"))
        self.assertEqual(Upstream.seen, [])
        self.assertEqual(self.request(origin, "GET", "/api/v2/system/info")[0].status, 200)
        self.assertEqual(self.request(origin, "GET", "/api/v2/stream/s1/subtitles/0.srt")[0].status, 200)
        self.control("refuse-media")
        data, _ = self.raw_get(origin, "/api/v2/stream/s1")
        self.assertTrue(data.startswith(b"HTTP/1.1 200 "))
        entries = [entry for entry in self.entries(6) if "time" in entry]
        refused, later = entries[:3], entries[3:]
        self.assertEqual([entry["class"] for entry in refused], ["stream", "playlist", "segment"])
        for entry in refused:
            self.assertEqual((entry["action"], entry["status"], entry["refusal"]), ("refuse", 0, "reset"))
            self.assertTrue(entry["authorization"])
        self.assertTrue(refused[0]["query"])
        self.assertEqual([entry["action"] for entry in later], ["forward"] * 3)
        self.assertNotIn("SECRET", self.output.getvalue())

    def test_a_close_refusal_ends_without_an_answer(self):
        origin, _ = self.start()
        self.control("refuse-media", "close")
        self.assertEqual(self.raw_get(origin, "/api/v2/playback/transcode/s1/segment/0.m4s"), (b"", "close"))
        self.assertEqual(Upstream.seen, [])
        [entry] = [entry for entry in self.entries() if "time" in entry]
        self.assertEqual((entry["class"], entry["action"], entry["status"], entry["refusal"]), ("segment", "refuse", 0, "close"))

    def test_a_reset_cuts_a_media_transfer_already_open(self):
        origin, _ = self.start("--extra-facts")
        client, head = self.open_get(origin, "/api/v2/stream/s1/drip.mkv?" + SECRET_QUERY)
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
        began = time.monotonic()
        self.control("refuse-media", "")
        _, how = self.finish_get(client)
        self.assertEqual(how, "reset")
        self.assertLess(time.monotonic() - began, 2)
        self.assertTrue(Upstream.dropped.wait(5), "the upstream connection is closed too")
        [entry] = [entry for entry in self.entries() if "time" in entry]
        self.assertEqual((entry["class"], entry["action"], entry["status"], entry["refusal"], entry["open"]), ("stream", "refuse", 0, "reset", True))
        self.assertTrue(entry["authorization"] and entry["query"])
        self.assertIn("bytes", entry)
        self.assertNotIn("SECRET", self.output.getvalue())
        self.assertNotIn("/api/", self.output.getvalue())

    def test_a_close_cuts_a_relay_the_client_has_stopped_reading(self):
        origin, _ = self.start()
        # Roku stops reading an original while its buffer is full: the relay
        # waits on the client, not on the upstream.
        client, head = self.open_get(origin, "/api/v2/stream/s1/big.ts", rcvbuf=4096)
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
        time.sleep(0.5)
        self.control("refuse-media", "close")
        time.sleep(1)
        received, how = self.finish_get(client)
        self.assertEqual(how, "close")
        self.assertLess(received, BIG_BODY)
        self.assertTrue(Upstream.dropped.wait(5), "the upstream connection is closed too")
        [entry] = [entry for entry in self.entries() if "time" in entry]
        self.assertEqual((entry["class"], entry["action"], entry["status"], entry["refusal"], entry["open"]), ("stream", "refuse", 0, "close", True))
        self.assertNotIn("bytes", entry)

    def test_a_cut_logs_each_open_media_connection_and_spares_the_api(self):
        origin, _ = self.start()
        stream, _ = self.open_get(origin, "/api/v2/stream/s1/drip.mkv")
        segment, _ = self.open_get(origin, "/api/v2/playback/transcode/s1/segment/drip.m4s")
        api, head = self.open_get(origin, "/api/v2/items/drip?s=1.5")
        self.control("refuse-media", "")
        self.assertEqual(self.finish_get(stream)[1], "reset")
        self.assertEqual(self.finish_get(segment)[1], "reset")
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
        self.assertEqual(self.finish_get(api), (int(1.5 / DRIP_INTERVAL) * len(DRIP_CHUNK), "close"))
        entries = [entry for entry in self.entries(3) if "time" in entry]
        refused = sorted((entry["class"], entry["action"], entry["status"], entry.get("open")) for entry in entries if entry["action"] == "refuse")
        self.assertEqual(refused, [("segment", "refuse", 0, True), ("stream", "refuse", 0, True)])
        self.assertEqual([(entry["class"], entry["action"], entry["status"]) for entry in entries if entry["action"] != "refuse"], [("api", "forward", 200)])

    def test_ended_transfers_are_not_cut_and_removing_the_file_stops_cutting(self):
        origin, _ = self.start()
        data, _ = self.raw_get(origin, "/api/v2/playback/transcode/s1/segment/0.m4s")
        self.assertTrue(data.startswith(b"HTTP/1.1 200 "))
        self.control("refuse-media", "")
        time.sleep(3 * probe.CUT_POLL_SECONDS)
        self.control("refuse-media")
        client, _ = self.open_get(origin, "/api/v2/stream/s1/drip.mkv?s=1")
        self.assertEqual(self.finish_get(client), (int(1 / DRIP_INTERVAL) * len(DRIP_CHUNK), "close"))
        self.assertEqual([entry["action"] for entry in self.entries(2) if "time" in entry], ["forward", "forward"])
        self.assertFalse(Upstream.dropped.is_set())
        self.assertEqual(self.config.media.open, set())

    def test_throttles_each_media_connection_to_the_rate(self):
        origin, _ = self.start("--extra-facts")
        self.control("throttle-media", "2000\n")
        rate = 2000 * 1000 / 8  # bytes per second
        seconds = 2
        playlist = len(long_playlist())
        sizes = {"/api/v2/stream/s1/big.ts?" + SECRET_QUERY: BIG_BODY, "/api/v2/playback/transcode/s1/long.m3u8": playlist, "/api/v2/playback/transcode/s1/segment/big.ts": BIG_BODY}
        results = {}

        def measure(path):
            client, head = self.open_get(origin, path)
            results[path] = (client, head, self.read_for(client, seconds))

        threads = [threading.Thread(target=measure, args=(path,)) for path in sizes]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        for path, (_, head, received) in results.items():
            with self.subTest(path=path):
                self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
                self.assertGreater(received, 0.8 * rate * seconds)
                self.assertLess(received, 1.05 * rate * seconds)
        began = time.monotonic()
        _, data = self.request(origin, "GET", "/api/v2/items/big.ts")
        self.assertEqual(len(data), BIG_BODY)
        self.assertLess(time.monotonic() - began, 3, "API responses are not throttled")
        self.control("throttle-media")
        began = time.monotonic()
        for path, (client, _, received) in results.items():
            self.assertEqual(self.finish_get(client), (sizes[path] - received, "close"))
        self.assertLess(time.monotonic() - began, 5, "open relays return to full speed")
        entries = [entry for entry in self.entries(7) if "time" in entry]
        throttled = sorted((entry["class"], entry["status"], entry["throttle_kbps"], "open" in entry) for entry in entries if entry["action"] == "throttle")
        self.assertEqual(throttled, [("playlist", 0, 2000.0, False), ("segment", 0, 2000.0, False), ("stream", 0, 2000.0, False)])
        relayed = sorted((entry["class"], entry["action"], entry["status"], entry["bytes"]) for entry in entries if entry["action"] != "throttle")
        self.assertEqual(relayed, [("api", "forward", 200, BIG_BODY), ("playlist", "forward", 200, playlist), ("segment", "forward", 200, BIG_BODY), ("stream", "forward", 200, BIG_BODY)])
        self.recorder.summary()
        summary = {entry["summary"]: entry for entry in self.entries() if "summary" in entry}
        self.assertEqual(summary["origin"]["requests"], 4)
        self.assertNotIn("SECRET", self.output.getvalue())
        self.assertNotIn("/api/", self.output.getvalue())

    def test_a_throttle_slows_an_open_relay_until_the_file_is_removed(self):
        origin, _ = self.start()
        # The upstream sends 640 kB/s; the throttle holds the relay to 125 kB/s.
        client, head = self.open_get(origin, "/api/v2/stream/s1/drip.mkv?s=5&kib=32")
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
        total = int(5 / DRIP_INTERVAL) * 32 * len(DRIP_CHUNK)
        rate = 1000 * 1000 / 8
        before = self.read_for(client, 0.5)
        self.assertGreater(before, 2 * rate * 0.5)
        self.control("throttle-media", "1000")
        # The watcher applies the rate within CUT_POLL_SECONDS; what was sent
        # before arrives meanwhile.
        settling = self.read_for(client, 0.6)
        throttled = self.read_for(client, 1.5)
        self.assertGreater(throttled, 0.75 * rate * 1.5)
        self.assertLess(throttled, 1.05 * rate * 1.5)
        self.control("throttle-media")
        began = time.monotonic()
        rest, how = self.finish_get(client)
        self.assertEqual((before + settling + throttled + rest, how), (total, "close"))
        self.assertGreater(rest / (time.monotonic() - began), 3 * rate)
        throttle, forward = [entry for entry in self.entries(2) if "time" in entry]
        self.assertEqual((throttle["class"], throttle["action"], throttle["status"], throttle["throttle_kbps"], throttle["open"]), ("stream", "throttle", 0, 1000.0, True))
        self.assertTrue(throttle["authorization"])
        self.assertEqual((forward["class"], forward["action"], forward["status"]), ("stream", "forward", 200))
        self.assertFalse(Upstream.dropped.is_set())

    def test_refuse_media_wins_over_a_throttle(self):
        origin, _ = self.start()
        # The lowest rate needs a second for a piece, but a cut still lands at once.
        self.control("throttle-media", "0")
        client, head = self.open_get(origin, "/api/v2/playback/transcode/s1/segment/big.ts")
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
        self.assertLess(self.read_for(client, 0.5), 2 * probe.THROTTLE_MIN_BURST)
        self.control("refuse-media", "")
        began = time.monotonic()
        self.assertEqual(self.finish_get(client)[1], "reset")
        self.assertLess(time.monotonic() - began, 1)
        self.assertTrue(Upstream.dropped.wait(5), "the upstream connection is closed too")
        self.assertEqual(self.raw_get(origin, "/api/v2/stream/s1"), (b"", "reset"))
        entries = [entry for entry in self.entries(3) if "time" in entry]
        self.assertEqual(
            [(entry["class"], entry["action"], entry.get("throttle_kbps"), entry.get("refusal"), entry.get("open")) for entry in entries],
            [("segment", "throttle", float(probe.MIN_THROTTLE_KBPS), None, None), ("segment", "refuse", None, "reset", True), ("stream", "refuse", None, "reset", None)],
        )


if __name__ == "__main__":
    unittest.main()
