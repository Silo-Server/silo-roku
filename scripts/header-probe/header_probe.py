#!/usr/bin/env python3
"""Header probe: a logging reverse proxy for the Silo Roku transport harness.

Development tool for hardware tests H1 and H2 (docs/implementation-plan.md
section 10). It forwards a Roku's requests to a Silo server and records, per
request, only: the listener that received it, the method, a coarse path
class, the status, and whether Authorization, X-Profile-Id, and X-Profile-Token
were present. It never records header values, cookies, paths, or query
strings, because those carry access tokens, signed stream tokens, session IDs,
and passwords. Bodies are recorded only with --playback-bodies, and then only
the request bodies of playback start, replan, progress, stop, and route-event
calls, with credential-named fields and URL-like values redacted.

Three lab modes are switched at run time by control files, read on each
request (see Config.controls): one holds a replan for some seconds before
forwarding it, one ends media connections without an HTTP answer, and one
relays media no faster than a set rate; the last two act on connections
already open when their file appears too (see MediaTransfers).

Three listeners, each a separate origin:

* origin  - the address typed into the harness as the Silo server; forwards to
            --upstream, optionally redirects some path classes or rewrites HLS
            playlists so their child URIs point at another listener;
* foreign - another port or host name; also forwards to --upstream and raises
            an alert when any credential header reaches it;
* plain   - an http:// listener for downgrade tests when origin uses TLS;
            alerts the same way.

Python 3.8+ standard library only. See README.md for the test procedures.
"""

import argparse
import datetime
import http.client
import http.server
import json
import math
import os
import re
import signal
import socket
import socketserver
import ssl
import struct
import sys
import threading
import time
import urllib.parse

CREDENTIAL_HEADERS = ("authorization", "x-profile-id", "x-profile-token")
PATH_CLASSES = ("api", "stream", "playlist", "segment", "subtitle", "other")
LISTENERS = ("origin", "foreign", "plain")
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
# Not copied as-is upstream: Host is sent separately (the client's own, so the
# server sees the origin the client addressed), identity bodies keep playlists
# rewritable, the probe answers Expect itself, and Content-Length is sent from
# the body the probe read. Not copied back: the probe sends its own Server and
# Date.
DROP_REQUEST = HOP_BY_HOP | {"host", "accept-encoding", "expect", "content-length"}
DROP_RESPONSE = HOP_BY_HOP | {"server", "date"}
URI_ATTRIBUTE = re.compile(r'URI="([^"]*)"')
# Non-secret facts --extra-facts adds for H2 (signed playlists) and H8 (segment
# sizes): whether a query exists, whether a parameter name repeats, whether a
# playlist uses #EXT-X-DEFINE and how many URI lines it has, and the response
# body size in bytes (on an abort, the bytes relayed before the client left).
EXTRA_FACTS = {"query": bool, "duplicate_query_keys": bool, "ext_x_define": bool, "playlist_entries": int, "bytes": int}
# "abort": the client closed the connection before the response was written.
# "hold": a replan the hold-replan control file holds; its own line follows.
# "refuse": a media request answered by ending the connection (refuse-media),
# or one already open that refuse-media cut part-way (its line says "open").
# "throttle": a media relay throttle-media began to slow; its own line follows.
ACTIONS = ("forward", "redirect", "rewrite", "abort", "error", "hold", "refuse", "throttle")
CHUNK = 64 * 1024
# The requests whose bodies --playback-bodies logs, matched on the method and
# the whole path: the playback mutations only. Auth, session, profile, PIN,
# and sign-in requests never match. The v2 stop is a DELETE with a body.
PLAYBACK_BODY_ROUTES = (
    ("POST", re.compile(r"/api/v2/playback/start"), "start"),
    ("POST", re.compile(r"/api/v2/playback/route-events"), "route_event"),
    ("POST", re.compile(r"/api/v2/playback/[A-Za-z0-9_:-]+/replan"), "replan"),
    ("POST", re.compile(r"/api/v2/playback/[A-Za-z0-9_:-]+/progress"), "progress"),
    ("DELETE", re.compile(r"/api/v2/playback/(?!(?:start|capabilities|route-events|transcode)$)[A-Za-z0-9_:-]+"), "stop"),
)
PLAYBACK_BODY_OPS = {op for _, _, op in PLAYBACK_BODY_ROUTES}
# A logged body field whose name contains one of these is replaced.
SECRET_FIELD_PARTS = ("token", "password", "pin", "secret", "signature")
REDACTED = "<redacted>"
# A string value that names a URL or a path is replaced too: it may be signed.
URL_LIKE = re.compile(r"^/|://")
DEFAULT_BODY_MAX = 16 * 1024
# Control files, named NAME.PORT after the origin listener's port so that two
# probes in one directory switch separately. A mode is on while its file exists.
CONTROL_FILES = ("hold-replan", "refuse-media", "throttle-media")
DEFAULT_HOLD_SECONDS = 30
MAX_HOLD_SECONDS = 600
# How refuse-media ends a connection: a TCP reset, or an orderly close.
REFUSALS = ("reset", "close")
MEDIA_CLASSES = ("stream", "playlist", "segment")
# How often open media transfers look for refuse-media and throttle-media, and
# how long a relay blocked on the client or the throttle waits before it looks
# again.
CUT_POLL_SECONDS = 0.25
# throttle-media's rate in kbit/s, and the token bucket that holds a relay to it:
# the relay sends pieces of at most THROTTLE_BURST_SECONDS of the rate (or
# THROTTLE_MIN_BURST bytes at low rates) as the bucket fills.
DEFAULT_THROTTLE_KBPS = 1000
MIN_THROTTLE_KBPS = 8
MAX_THROTTLE_KBPS = 1000000
THROTTLE_BURST_SECONDS = 0.1
THROTTLE_MIN_BURST = 1024


# --- Pure helpers (unit-tested) ----------------------------------------------


def path_class(path):
    """Coarse class of a request path. Never logged together with the path."""
    path = path.split("?", 1)[0].split("#", 1)[0].lower()
    if "/subtitles/" in path or path.endswith((".vtt", ".srt", ".ass", ".ssa")):
        return "subtitle"
    if path.endswith(".m3u8"):
        return "playlist"
    if "/segment/" in path:
        return "segment"
    if path.startswith(("/api/v2/stream/", "/stream/")):
        return "stream"
    if path.startswith(("/api/v2/images/", "/api/images/")):
        return "other"
    if path.startswith("/api/"):
        return "api"
    return "other"


def credential_presence(headers):
    """Booleans for each credential header; `headers` is a list of (name, value)."""
    names = {name.lower() for name, _ in headers}
    return {name.replace("-", "_"): name in names for name in CREDENTIAL_HEADERS}


def query_facts(query):
    """Whether a query string exists and whether any parameter name repeats.

    The repeat check answers H2 (does ForwardQueryStringParams duplicate the
    signed `st` parameter) without recording names or values.
    """
    names = [name for name, _ in urllib.parse.parse_qsl(query, keep_blank_values=True)]
    return {"query": bool(query), "duplicate_query_keys": len(names) != len(set(names))}


def playlist_facts(text):
    """Whether a playlist uses #EXT-X-DEFINE, and its number of URI lines
    (segments in a media playlist, variants in a multivariant one). Answers
    H2's size questions without keeping any URI."""
    entries = sum(1 for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#"))
    return {"ext_x_define": "#EXT-X-DEFINE" in text, "playlist_entries": entries}


def playback_body_op(method, path):
    """The playback call a request is (a word from PLAYBACK_BODY_ROUTES), or
    None when its body must not be logged."""
    path = path.split("?", 1)[0].split("#", 1)[0]
    for route_method, pattern, op in PLAYBACK_BODY_ROUTES:
        if method == route_method and pattern.fullmatch(path):
            return op
    return None


def redact_body(value):
    """A copy of a parsed JSON body with every field whose name contains a
    SECRET_FIELD_PARTS word, at any depth, and every URL-like string replaced."""
    if isinstance(value, dict):
        return {name: REDACTED if any(part in name.lower() for part in SECRET_FIELD_PARTS) else redact_body(item) for name, item in value.items()}
    if isinstance(value, list):
        return [redact_body(item) for item in value]
    if isinstance(value, str) and URL_LIKE.search(value):
        return REDACTED
    return value


def body_facts(op, body, limit=DEFAULT_BODY_MAX):
    """What --playback-bodies logs for a playback request body: its size and,
    when it is JSON, the redacted body. Redacted bodies longer than `limit`
    once serialized keep only their first `limit` characters (body_prefix)."""
    data = body or b""
    facts = {"op": op, "body_bytes": len(data)}
    if not data:
        return facts
    try:
        parsed = json.loads(data.decode("utf-8"))
    except ValueError:
        facts["body_json"] = False
        return facts
    redacted = redact_body(parsed)
    text = json.dumps(redacted, sort_keys=True, separators=(",", ":"))
    if len(text) > limit:
        facts["body_prefix"] = text[:limit]
        facts["body_truncated"] = True
    else:
        facts["body"] = redacted
    return facts


def hold_seconds(text):
    """How long a hold-replan file holds a replan: 0 when the file is absent
    (`text` None), else its number of seconds, DEFAULT_HOLD_SECONDS when it is
    empty or not a number, within 0 to MAX_HOLD_SECONDS."""
    if text is None:
        return 0
    try:
        seconds = float(text)
    except ValueError:
        return DEFAULT_HOLD_SECONDS
    if math.isnan(seconds):
        return DEFAULT_HOLD_SECONDS
    return min(max(seconds, 0.0), MAX_HOLD_SECONDS)


def refusal(text):
    """How a refuse-media file ends media connections: None when the file is
    absent, "close" when it says so, otherwise "reset"."""
    if text is None:
        return None
    return "close" if text.lower() == "close" else "reset"


def throttle_kbps(text):
    """The rate in kbit/s a throttle-media file holds media relays to: None
    when the file is absent (`text` None), DEFAULT_THROTTLE_KBPS when it is
    empty or not a number, within MIN_THROTTLE_KBPS to MAX_THROTTLE_KBPS."""
    if text is None:
        return None
    try:
        kbps = float(text)
    except ValueError:
        return DEFAULT_THROTTLE_KBPS
    if math.isnan(kbps):
        return DEFAULT_THROTTLE_KBPS
    return min(max(kbps, MIN_THROTTLE_KBPS), MAX_THROTTLE_KBPS)


def record(listener, method, klass, status, presence, action, facts=None, body=None, control=None):
    """The only shape the probe ever logs. Every value is a boolean, a number,
    or a word from a fixed vocabulary. `facts` (with --extra-facts) may add
    the EXTRA_FACTS below, coerced to their types; anything else is dropped.
    `body` (with --playback-bodies) is body_facts() for a playback call.
    `control` adds a hold line's `hold_seconds`, a refuse line's `refusal`, or
    a throttle line's `throttle_kbps`, and `open` for a refusal that cut a
    transfer already under way or a throttle that began after the request."""
    entry = {
        "time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "listener": listener if listener in LISTENERS else "unknown",
        "method": method if method.isalpha() and len(method) <= 10 else "other",
        "class": klass if klass in PATH_CLASSES else "other",
        "status": int(status),
        "action": action if action in ACTIONS else "error",
    }
    for name in ("authorization", "x_profile_id", "x_profile_token"):
        entry[name] = bool(presence.get(name))
    for name, kind in EXTRA_FACTS.items():
        if facts and name in facts:
            entry[name] = kind(facts[name])
    if body and body.get("op") in PLAYBACK_BODY_OPS:
        entry["op"] = body["op"]
        entry["body_bytes"] = int(body.get("body_bytes", 0))
        for name in ("body", "body_prefix", "body_truncated", "body_json"):
            if name in body:
                entry[name] = body[name]
    if control:
        if "hold_seconds" in control:
            entry["hold_seconds"] = float(control["hold_seconds"])
        if "throttle_kbps" in control:
            entry["throttle_kbps"] = float(control["throttle_kbps"])
        if control.get("refusal") in REFUSALS:
            entry["refusal"] = control["refusal"]
        if control.get("open") and ("refusal" in entry or "throttle_kbps" in entry):
            entry["open"] = True
    return entry


def redirect_location(public_base, path_and_query):
    """Location for a redirect to another listener: same path and query, new origin."""
    return public_base.rstrip("/") + path_and_query


def rewrite_playlist(text, playlist_url, public_base, upstream_origin):
    """Makes every child URI in an HLS playlist absolute on `public_base`.

    `playlist_url` is the playlist's path and query as requested. Relative
    URIs resolve against it; absolute URIs on the upstream origin move to
    `public_base`; URIs on any other origin, `#EXT-X-DEFINE` lines, and URIs
    that start with a variable reference are left alone.
    """
    base = public_base.rstrip("/") + playlist_url.split("?", 1)[0]
    upstream = upstream_origin.rstrip("/")

    def absolute(uri):
        if uri.startswith("{$"):
            return uri
        lowered = uri.lower()
        if lowered.startswith(("http://", "https://")):
            if lowered.startswith(upstream.lower() + "/"):
                return public_base.rstrip("/") + uri[len(upstream):]
            return uri
        return urllib.parse.urljoin(base, uri)

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#EXT-X-DEFINE"):
            lines.append(line)
        elif stripped.startswith("#"):
            lines.append(URI_ATTRIBUTE.sub(lambda match: 'URI="' + absolute(match.group(1)) + '"', line))
        else:
            lines.append(absolute(stripped))
    return "\n".join(lines)


def origin_of(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("expected an http or https URL")
    if parts.username or parts.password:
        raise ValueError("URLs with credentials are not accepted")
    return parts.scheme + "://" + parts.netloc


def parse_redirect(value):
    klass, _, target = value.partition("=")
    if klass not in PATH_CLASSES + ("all",) or target not in ("foreign", "plain"):
        raise argparse.ArgumentTypeError("use CLASS=foreign or CLASS=plain, CLASS one of " + ", ".join(PATH_CLASSES + ("all",)))
    return klass, target


def body_limit(value):
    if not value.isdigit() or not 256 <= int(value) <= 1024 * 1024:
        raise argparse.ArgumentTypeError("use a number of characters from 256 to 1048576")
    return int(value)


def parse_address(value):
    host, _, port = value.rpartition(":")
    if not port.isdigit():
        raise argparse.ArgumentTypeError("use HOST:PORT")
    return host or "0.0.0.0", int(port)


# --- Logging -------------------------------------------------------------------


class Recorder:
    """Writes one JSON line per request and keeps per-listener totals."""

    def __init__(self, stream, path=None, listeners=LISTENERS):
        self.stream = stream
        self.file = open(path, "a", encoding="utf-8") if path else None
        self.lock = threading.Lock()
        self.totals = {name: {"requests": 0, "authorization": 0, "x_profile_id": 0, "x_profile_token": 0} for name in listeners}

    def write(self, entry):
        line = json.dumps(entry, sort_keys=True)
        with self.lock:
            # Hold and throttle lines announce a request whose own line
            # follows; count that one.
            if entry["action"] in ("hold", "throttle"):
                self._emit(line)
                return
            totals = self.totals.get(entry["listener"])
            if totals is not None:
                totals["requests"] += 1
                for name in ("authorization", "x_profile_id", "x_profile_token"):
                    totals[name] += int(entry[name])
            self._emit(line)
            if entry["listener"] != "origin" and (entry["authorization"] or entry["x_profile_id"] or entry["x_profile_token"]):
                self._emit(json.dumps({"alert": "credential header reached a non-origin listener", "listener": entry["listener"], "class": entry["class"]}, sort_keys=True))

    def summary(self):
        with self.lock:
            for name, totals in self.totals.items():
                seen = any(totals[key] for key in ("authorization", "x_profile_id", "x_profile_token"))
                self._emit(json.dumps({"summary": name, "credential_headers_seen": seen, **totals}, sort_keys=True))

    def _emit(self, line):
        print(line, file=self.stream, flush=True)
        if self.file:
            self.file.write(line + "\n")
            self.file.flush()


# --- Proxy -----------------------------------------------------------------------


class Cut(Exception):
    """refuse-media cut a media transfer that was already under way."""


class Transfer:
    """One media request the probe is relaying, which refuse-media can cut and
    throttle-media can slow. `kbps` is the throttle's rate, None when off; the
    request sets it when it arrives and the watcher while it is open.
    `announce(kbps, open)` logs the first throttled write."""

    def __init__(self, kbps=None, announce=None):
        self.how = None
        self.upstream = None
        self.kbps = kbps
        self.began_unthrottled = kbps is None
        self.announce = announce
        self.announced = False
        self.tokens = 0.0
        # When the token bucket last filled; None while the throttle is off.
        self.filled = None

    def cut(self, how):
        """Called by the watcher. A relay blocked reading the upstream wakes
        when its socket shuts down; one blocked writing to the client sees
        `how` within CUT_POLL_SECONDS (ProbeHandler.write). The handler then
        ends the client's connection itself, as refuse() does for a new request."""
        if self.how:
            return
        self.how = how
        upstream = self.upstream
        if upstream is not None:
            try:
                # The base method, so an SSLSocket's TLS state is left to the handler.
                socket.socket.shutdown(upstream, socket.SHUT_RDWR)
            except OSError:
                pass

    def check(self):
        if self.how:
            raise Cut()

    def allowance(self, wanted):
        """How many of `wanted` bytes the relay may send now: all of them
        while throttle-media is off, else what the token bucket holds once it
        holds a piece. Waits at most CUT_POLL_SECONDS for that and returns 0
        if it was not enough, so the relay looks for a cut or a new rate."""
        kbps = self.kbps
        if kbps is None:
            self.filled = None
            return wanted
        now = time.monotonic()
        rate = kbps * 125.0  # bytes per second
        burst = max(rate * THROTTLE_BURST_SECONDS, THROTTLE_MIN_BURST)
        if self.filled is None:
            # An empty bucket, so a throttle that begins or resumes sends no
            # more than the rate from then on.
            self.tokens = 0.0
            if not self.announced:
                self.announced = True
                if self.announce:
                    self.announce(kbps, self.began_unthrottled)
        else:
            self.tokens = min(self.tokens + (now - self.filled) * rate, burst)
        self.filled = now
        piece = min(wanted, burst)
        if self.tokens < piece:
            time.sleep(min((piece - self.tokens) / rate, CUT_POLL_SECONDS))
            return 0
        return min(wanted, int(self.tokens))

    def spend(self, sent):
        if self.filled is not None:
            self.tokens -= sent


class MediaTransfers:
    """The media transfers under way on every listener. refuse-media and
    throttle-media act on new requests when they arrive, but Roku reads an
    original over one range request opened at the start (hardware run 14,
    T2a), so a watcher thread applies them to those already open too: it cuts
    each while refuse-media exists and gives each throttle-media's rate, or
    none once that file is gone. The watcher runs only while a transfer is
    open, and reads the files every CUT_POLL_SECONDS."""

    def __init__(self, refusal_now, throttle_now):
        self.refusal_now = refusal_now
        self.throttle_now = throttle_now
        self.lock = threading.Lock()
        self.open = set()
        self.watching = False

    def add(self, transfer):
        with self.lock:
            self.open.add(transfer)
            if not self.watching:
                self.watching = True
                threading.Thread(target=self.watch, daemon=True).start()

    def remove(self, transfer):
        with self.lock:
            self.open.discard(transfer)

    def watch(self):
        while True:
            time.sleep(CUT_POLL_SECONDS)
            how = self.refusal_now()
            kbps = self.throttle_now()
            with self.lock:
                if not self.open:
                    self.watching = False
                    return
                transfers = list(self.open)
            for transfer in transfers:
                transfer.kbps = kbps
                if how:
                    transfer.cut(how)


class Config:
    def __init__(self, args):
        self.upstream = origin_of(args.upstream)
        parts = urllib.parse.urlsplit(self.upstream)
        self.upstream_https = parts.scheme == "https"
        self.upstream_host = parts.hostname
        self.upstream_port = parts.port or (443 if self.upstream_https else 80)
        self.upstream_netloc = parts.netloc
        self.upstream_context = None
        if self.upstream_https:
            self.upstream_context = ssl.create_default_context()
            if args.upstream_insecure:
                self.upstream_context.check_hostname = False
                self.upstream_context.verify_mode = ssl.CERT_NONE
        self.public = {"foreign": args.foreign_public, "plain": args.plain_public}
        self.redirects = dict(args.redirect or [])
        self.redirect_status = args.redirect_status
        self.absolute_children = args.absolute_children
        self.extra_facts = args.extra_facts
        self.playback_bodies = args.playback_bodies
        self.playback_body_max = args.playback_body_max
        directory = os.path.abspath(args.control_dir)
        self.controls = {name: os.path.join(directory, "%s.%d" % (name, args.origin_listen[1])) for name in CONTROL_FILES}
        self.media = MediaTransfers(lambda: refusal(self.control("refuse-media")), lambda: throttle_kbps(self.control("throttle-media")))
        for target in list(self.redirects.values()) + ([self.absolute_children] if self.absolute_children else []):
            if not self.public.get(target):
                raise SystemExit("--" + target + "-public is required to send requests to the " + target + " listener")

    def redirect_target(self, listener, klass):
        if listener != "origin":
            return None
        return self.redirects.get(klass) or self.redirects.get("all")

    def control(self, name):
        """The stripped text of a control file, or None when it does not exist.
        Read on every request so a mode switches without a restart."""
        try:
            with open(self.controls[name], encoding="utf-8", errors="replace") as handle:
                return handle.read(64).strip()
        except FileNotFoundError:
            return None

    def connect(self):
        if self.upstream_https:
            return http.client.HTTPSConnection(self.upstream_host, self.upstream_port, timeout=60, context=self.upstream_context)
        return http.client.HTTPConnection(self.upstream_host, self.upstream_port, timeout=60)


class ProbeServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, listener, config, recorder):
        super().__init__(address, ProbeHandler)
        self.listener = listener
        self.config = config
        self.recorder = recorder

    # The default prints a traceback, whose exception text can quote a URL.
    def handle_error(self, request, client_address):
        print(json.dumps({"error": sys.exc_info()[0].__name__, "listener": self.listener}), file=sys.stderr, flush=True)


class ClientGone(Exception):
    """The client closed the connection while the probe was answering."""


class ProbeHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "silo-header-probe"
    sys_version = ""
    timeout = 120

    # The default handler logs request lines, which carry paths and queries.
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.handle_request()

    do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_GET

    def handle_request(self):
        server = self.server
        config = server.config
        split = urllib.parse.urlsplit(self.path)
        klass = path_class(split.path)
        presence = credential_presence(list(self.headers.items()))
        facts = query_facts(split.query) if config.extra_facts else None
        op = playback_body_op(self.command, split.path)
        body_op = op if config.playback_bodies else None
        how = refusal(config.control("refuse-media")) if klass in MEDIA_CLASSES else None
        if how:
            self.refuse(how)
            server.recorder.write(record(server.listener, self.command, klass, 0, presence, "refuse", facts, control={"refusal": how}))
            return
        target = config.redirect_target(server.listener, klass)
        if target:
            body = self.read_body()
            self.send_response(config.redirect_status)
            self.send_header("Location", redirect_location(config.public[target], self.path))
            self.send_header("Content-Length", "0")
            self.end_headers()
            logged = body_facts(body_op, body, config.playback_body_max) if body_op else None
            server.recorder.write(record(server.listener, self.command, klass, config.redirect_status, presence, "redirect", facts, logged))
            return
        hold = hold_seconds(config.control("hold-replan")) if op == "replan" else 0
        if hold:
            # Before forwarding, so the server sees the replan only afterwards.
            server.recorder.write(record(server.listener, self.command, klass, 0, presence, "hold", facts, control={"hold_seconds": hold}))
            time.sleep(hold)
        # What forward() has learned so far, so an abort or a failure part-way
        # through still logs the upstream status and the facts gathered.
        progress = {"status": 502, "headers_sent": False, "facts": {}, "body_op": body_op, "body": None}
        transfer = None
        if klass in MEDIA_CLASSES:

            def announce(kbps, already_open):
                control = {"throttle_kbps": kbps, "open": already_open}
                server.recorder.write(record(server.listener, self.command, klass, 0, presence, "throttle", facts, control=control))

            transfer = Transfer(throttle_kbps(config.control("throttle-media")), announce)
        try:
            action = self.forward(klass, progress, transfer)
            status = progress["status"]
        except Cut:
            self.refuse(transfer.how)
            if facts is not None:
                facts.update(progress["facts"])
            server.recorder.write(record(server.listener, self.command, klass, 0, presence, "refuse", facts, control={"refusal": transfer.how, "open": True}))
            return
        except ClientGone:
            status, action = progress["status"], "abort"
            self.close_connection = True
        except Exception:  # noqa: BLE001 - the exception text may contain the URL
            status, action = progress["status"], "error"
            self.close_connection = True
            if not progress["headers_sent"]:
                status = 502
                try:
                    self.send_response(502)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                except OSError:
                    pass
        if facts is not None:
            facts.update(progress["facts"])
        server.recorder.write(record(server.listener, self.command, klass, status, presence, action, facts, progress["body"]))

    def refuse(self, how):
        """Ends the connection without an HTTP answer, as when the origin goes
        away: a TCP reset, or with "close" an orderly close."""
        self.close_connection = True
        if how == "reset":
            # Linger 0 makes close() send RST. The read buffer shares the
            # socket; closing it first resets now, not when the handler ends.
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            self.rfile.close()
            self.connection.close()

    def read_body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            body = b""
            while True:
                size = int(self.rfile.readline().split(b";", 1)[0].strip() or b"0", 16)
                if size == 0:
                    while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                        pass
                    return body
                body += self.rfile.read(size)
                self.rfile.readline()
        # An explicit Content-Length: 0 stays b"", so it is still sent upstream.
        length = self.headers.get("Content-Length")
        return None if length is None else self.rfile.read(int(length or 0))

    def forward(self, klass, progress, transfer=None):
        """Relays one request upstream and returns the action. Records in
        `progress` the upstream status, whether headers reached the client, and
        the non-secret facts about the body (size, playlist facts) as they
        become known. Raises ClientGone when the client hangs up, and Cut when
        refuse-media cuts `transfer`, a media request, part-way; throttle-media
        slows `transfer`'s writes (write)."""
        config = self.server.config
        body = self.read_body()
        if progress["body_op"]:
            progress["body"] = body_facts(progress["body_op"], body, config.playback_body_max)
        connection = config.connect()
        if transfer:
            config.media.add(transfer)
        try:
            # Connected first, so a cut can shut the socket a read waits on.
            connection.connect()
            if transfer:
                transfer.upstream = connection.sock
                transfer.check()
            connection.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            # Silo derives its absolute URLs and system/info request_origin
            # from Host (forwarding headers count only from a trusted proxy),
            # so pass the client's Host through like a transparent proxy.
            connection.putheader("Host", self.headers.get("Host") or config.upstream_netloc)
            for name, value in self.headers.items():
                if name.lower() not in DROP_REQUEST:
                    connection.putheader(name, value)
            if body is not None:
                connection.putheader("Content-Length", str(len(body)))
            connection.endheaders(body)
            response = connection.getresponse()
            progress["status"] = response.status
            headers = [(name, value) for name, value in response.getheaders() if name.lower() not in DROP_RESPONSE]
            no_body = self.command == "HEAD" or response.status in (204, 304) or 100 <= response.status < 200

            # Playlists are small: buffer them to detect #EXT-X-DEFINE and,
            # on the origin listener, to rewrite their child URIs.
            if klass == "playlist" and response.status == 200 and not no_body:
                text = response.read().decode("utf-8", errors="replace")
                if transfer:
                    transfer.check()
                action = "forward"
                target = config.absolute_children
                if target and self.server.listener == "origin":
                    text = rewrite_playlist(text, self.path, config.public[target], config.upstream)
                    action = "rewrite"
                data = text.encode("utf-8")
                progress["facts"] = {"bytes": len(data), **playlist_facts(text)}
                self.send_headers(response.status, headers, len(data), progress)
                self.write(data, transfer)
                return action

            length = response.getheader("Content-Length")
            chunked = length is None and not no_body
            self.send_headers(response.status, headers, length, progress, chunked)
            sent = progress["facts"] = {"bytes": 0}
            while not no_body:
                # read1 relays what has arrived; read would wait for a full CHUNK.
                data = response.read1(CHUNK)
                # A cut upstream socket reads as the end of the body.
                if transfer:
                    transfer.check()
                if not data:
                    break
                sent["bytes"] += len(data)
                self.write(b"%x\r\n%s\r\n" % (len(data), data) if chunked else data, transfer)
            if chunked:
                self.write(b"0\r\n\r\n", transfer)
            return "forward"
        except Exception:
            # Whatever a cut made the relay raise (a short read, a TLS error).
            if transfer and transfer.how:
                raise Cut() from None
            raise
        finally:
            if transfer:
                config.media.remove(transfer)
                try:
                    self.connection.settimeout(self.timeout)
                except OSError:
                    pass
            connection.close()

    def send_headers(self, status, headers, length, progress, chunked=False):
        # The status line is buffered here, not before a playlist is read, so
        # a failed read leaves the buffer to handle_request's 502.
        self.send_response(status)
        for name, value in headers:
            if name.lower() != "content-length":
                self.send_header(name, value)
        if chunked:
            self.send_header("Transfer-Encoding", "chunked")
        elif length is not None:
            self.send_header("Content-Length", str(length))
        try:
            self.end_headers()
        except OSError as error:
            raise ClientGone() from error
        progress["headers_sent"] = True

    def write(self, data, transfer=None):
        """Writes to the client. For a media transfer it sends in pieces with a
        CUT_POLL_SECONDS timeout, so a relay blocked on a client that has
        stopped reading (Roku with a full buffer) still sees a cut; the
        handler's own timeout still ends a client that reads nothing. The
        pieces are as large as throttle-media's token bucket allows."""
        try:
            if not transfer:
                self.wfile.write(data)
                return
            self.connection.settimeout(CUT_POLL_SECONDS)
            view = memoryview(data)
            moved = time.monotonic()
            while view:
                transfer.check()
                allowed = transfer.allowance(len(view))
                if not allowed:
                    continue
                try:
                    sent = self.connection.send(view[:allowed])
                except socket.timeout:
                    if time.monotonic() - moved > self.timeout:
                        raise ClientGone() from None
                    continue
                transfer.spend(sent)
                view = view[sent:]
                moved = time.monotonic()
        except OSError as error:
            raise ClientGone() from error


def build_parser():
    parser = argparse.ArgumentParser(description="Logging reverse proxy for the Silo Roku transport harness (tests H1, H2).")
    parser.add_argument("--upstream", required=True, help="Silo origin to forward to, for example https://silo.example or http://192.0.2.5:8096")
    parser.add_argument("--upstream-insecure", action="store_true", help="skip TLS verification of the upstream (private-CA dev servers only)")
    parser.add_argument("--origin-listen", type=parse_address, default=("0.0.0.0", 8080), help="origin listener HOST:PORT (default 0.0.0.0:8080)")
    parser.add_argument("--tls-cert", help="PEM certificate chain; serves the origin listener over HTTPS")
    parser.add_argument("--tls-key", help="PEM private key for --tls-cert")
    parser.add_argument("--foreign-listen", type=parse_address, help="foreign listener HOST:PORT")
    parser.add_argument("--foreign-public", help="URL the Roku uses to reach the foreign listener, for example http://192.0.2.20:8081")
    parser.add_argument("--plain-listen", type=parse_address, help="plain-HTTP listener HOST:PORT")
    parser.add_argument("--plain-public", help="http:// URL the Roku uses to reach the plain listener")
    parser.add_argument("--redirect", type=parse_redirect, action="append", metavar="CLASS=TARGET", help="answer CLASS requests on the origin listener with a redirect to TARGET (foreign or plain); repeatable")
    parser.add_argument("--redirect-status", type=int, choices=(301, 302, 303, 307, 308), default=302)
    parser.add_argument("--absolute-children", choices=("foreign", "plain"), help="rewrite HLS playlists on the origin listener so child URIs are absolute on this listener")
    parser.add_argument("--extra-facts", action="store_true", help="also log non-secret facts for H2 and H8: query present, repeated parameter name, #EXT-X-DEFINE in a playlist, response size")
    parser.add_argument("--playback-bodies", action="store_true", help="also log the request bodies of playback start, replan, progress, stop, and route-event calls, with credential-named fields and URL-like values redacted")
    parser.add_argument("--playback-body-max", type=body_limit, default=DEFAULT_BODY_MAX, metavar="CHARS", help="keep at most this many characters of a redacted body (default %d)" % DEFAULT_BODY_MAX)
    parser.add_argument("--control-dir", default=".", metavar="DIR", help="directory of the hold-replan.PORT, refuse-media.PORT, and throttle-media.PORT control files, PORT the origin listener's (default: the working directory)")
    parser.add_argument("--log", help="also append the JSON lines to this file")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if bool(args.tls_cert) != bool(args.tls_key):
        raise SystemExit("--tls-cert and --tls-key go together")
    config = Config(args)
    listeners = ["origin"] + [name for name in ("foreign", "plain") if getattr(args, name + "_listen")]
    recorder = Recorder(sys.stdout, args.log, listeners)
    servers = []
    origin = ProbeServer(args.origin_listen, "origin", config, recorder)
    if args.tls_cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.tls_cert, args.tls_key)
        origin.socket = context.wrap_socket(origin.socket, server_side=True)
    servers.append(origin)
    if args.foreign_listen:
        servers.append(ProbeServer(args.foreign_listen, "foreign", config, recorder))
    if args.plain_listen:
        servers.append(ProbeServer(args.plain_listen, "plain", config, recorder))
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        host, port = server.server_address[:2]
        print(json.dumps({"listening": server.listener, "port": port, "host": host}), flush=True)
    print(json.dumps({"control_files": config.controls}), flush=True)
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    while not stop.wait(1):
        pass
    for server in servers:
        server.shutdown()
    recorder.summary()


if __name__ == "__main__":
    main()
