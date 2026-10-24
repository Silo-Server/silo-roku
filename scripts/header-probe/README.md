# Header probe and transport harness

Development tools for Milestone 0a (plan PR M0-5) that prove playback transport
on a real Roku against a real Silo server: hardware tests H1, H2, H8, H14, and
H19 in `docs/implementation-plan.md` section 10. Neither tool ships: the
harness is compiled only into `debug` builds, and the probe runs on a LAN host.

Record results in `docs/hardware-evidence.md` without addresses, item IDs,
accounts, or URLs.

## The probe

`header_probe.py` is a reverse proxy (Python 3.8+, standard library only) that
forwards to a Silo origin and logs one JSON line per request with only: the
listener, the method, a coarse path class (`api`, `stream`, `playlist`,
`segment`, `subtitle`, `other`), the status, the action (`forward`,
`redirect`, `rewrite`, `abort`, `error`, and the lab modes' `hold`,
`refuse`, and `throttle`, below), and whether `Authorization`,
`X-Profile-Id`, and `X-Profile-Token` were present. It never logs header
values, cookies, paths, or query strings, and logs no bodies unless asked
(`--playback-bodies`, below). `--extra-facts` adds
non-secret booleans and counts for H2 and H8: whether a query string exists
(`query`), whether a parameter name repeats (`duplicate_query_keys`), whether a
playlist uses `#EXT-X-DEFINE` (`ext_x_define`), how many URI lines it has
(`playlist_entries`: segments in a media playlist, variants in a multivariant
one), and the response size (`bytes`).

`--playback-bodies` adds the request bodies of the playback calls, and of no
other request: `POST /api/v2/playback/start`, `.../{session}/replan`,
`.../{session}/progress`, `.../route-events`, and the stop,
`DELETE /api/v2/playback/{session}`, matched on the method and the whole path.
Auth, session, profile, PIN, and sign-in bodies are never logged. The line
gains `op` (`start`, `replan`, `progress`, `stop`, or `route_event`),
`body_bytes`, and `body`, the parsed JSON with every field whose name contains
`token`, `password`, `pin`, `secret`, or `signature` (any case, any depth) and
every string that looks like a URL or a path replaced by `<redacted>`. A body
longer than `--playback-body-max` characters once redacted (default 16384)
keeps only that many as `body_prefix`, with `body_truncated`; a body that is
not JSON gets `body_json: false` and no content. The body is forwarded
unchanged.

`abort` means the client closed the connection before the response was
written, as Roku does on range requests, seeks, cancelled segments, and
playlists it refuses. The line keeps the upstream status, and with
`--extra-facts` the bytes relayed so far and, for a playlist, `ext_x_define`
and `playlist_entries` (playlists are read whole before they are relayed).
`error` means the upstream failed: status 502 when no upstream answer
arrived, otherwise the upstream status of the response that broke off.

Listeners, each its own origin:

| Listener | Flag | Role |
| --- | --- | --- |
| `origin` | `--origin-listen` (default `0.0.0.0:8080`), optional `--tls-cert`/`--tls-key` | The server address typed into the harness. Forwards to `--upstream`; can redirect path classes (`--redirect CLASS=foreign\|plain`, `--redirect-status`) or rewrite HLS playlists so child URIs are absolute on another listener (`--absolute-children foreign\|plain`) |
| `foreign` | `--foreign-listen`, `--foreign-public` | A second origin (another port or host name). Forwards to `--upstream` and prints an `alert` line when any credential header reaches it |
| `plain` | `--plain-listen`, `--plain-public` (an `http://` URL) | Same as `foreign`, for HTTPS-to-HTTP downgrade tests when `origin` uses TLS |

`--*-public` is the URL the Roku uses to reach that listener; a different port
or host name from the harness's server address makes it a different origin.
Ctrl-C (or SIGTERM) prints a summary per listener with
`credential_headers_seen`. `--log FILE` appends the same lines to a file.

The probe answers plain HTTP unless `--tls-cert` is given; Roku trusts only
its system CA bundle, so an HTTPS origin needs a publicly trusted certificate
for a host name that resolves to the probe host. If the upstream itself
redirects, the `Location` passes through unchanged and later requests bypass
the probe.

### Lab modes: a held replan, refused or throttled media

Three modes reproduce what a server outage or a slow server cannot on demand:
a replan still in flight when the viewer changes profile (plan section 6.6),
an original's outage seen as a network failure rather than 502 answers (run
12's T2b'), and a slow link that delays media without failing it (W10-1's
renewal while buffering, AG-182 decision 4; Auto's step-down on a slow link,
AG-187). All are off by default. The probe reads a control file per mode
on every request, so a test switches a mode on and off without a restart: a
mode is on while its file exists. The files sit in `--control-dir` (default:
the probe's working directory) and end in the origin listener's port, so two
probes started in one directory switch separately. The probe prints their
paths when it starts (`control_files`).

| File | Default | While it exists |
| --- | --- | --- |
| `hold-replan.PORT` | absent (off) | Each `POST /api/v2/playback/{session}/replan`, on any listener, waits before it is forwarded. The file holds the seconds to wait: empty or not a number means 30, at most 600, and 0 forwards at once. A `hold` line (`status` 0, `hold_seconds`) is logged when the wait begins and the request's usual line when it ends; only that one counts in the summary |
| `refuse-media.PORT` | absent (off) | Each `stream`, `playlist`, and `segment` request, on any listener, gets no HTTP answer: the probe resets the connection (TCP RST), or closes it in order when the file says `close`. A `refuse` line (`status` 0, `refusal` `reset` or `close`) is logged. Media connections already open when the file appears are cut the same way part-way through their answer, and their upstream connections closed; each gets a `refuse` line with `open: true` instead of its usual line (with `--extra-facts`, `bytes` relayed before the cut). API and subtitle requests, open or new, are forwarded as usual, and a refused class is not redirected |
| `throttle-media.PORT` | absent (off) | Each `stream`, `playlist`, and `segment` response, on any listener, is relayed to the client no faster than the file's rate in kbit/s (`3000` is 3 Mbit/s), on each connection separately: empty or not a number means 1000, at least 8, at most 1000000. Media connections already open when the file appears slow down too, a new rate applies to them as well, and removing the file returns them to full speed. A `throttle` line (`status` 0, `throttle_kbps`, and `open: true` when the file appeared after the request arrived) is logged at the request's first throttled write, and the request's usual line when it ends; only that one counts in the summary. API and subtitle responses are never throttled; while `refuse-media` exists it applies instead |

```sh
echo 20 > hold-replan.8180       # hold each replan 20 s
touch refuse-media.8180          # reset media connections
echo close > refuse-media.8180   # close them instead
echo 3000 > throttle-media.8180  # relay media at 3 Mbit/s per connection
rm hold-replan.8180 refuse-media.8180 throttle-media.8180   # all off
```

The hold comes before forwarding, so the server sees the replan only after
it. The client's request timeout (15 s by default, `source/api/request.bs`)
can end first; the client then replays the replan, the replay is held again,
and the abandoned request is still forwarded. The refusal comes after the connection is
accepted and the request read, because only the request names its class: a
closed port would stop the API as well.

Open connections matter for originals: Roku reads one over a single range
request opened at the start, so a refusal of new requests alone leaves it
playing (hardware run 14, T2a). While any media request is being relayed, a
watcher reads the refusal file every 0.25 s; once it exists, each open media
relay is cut within about half a second, whether it was waiting on the
upstream (its socket is shut down) or on a Roku that had stopped reading (the
relay sends with a 0.25 s timeout and looks again). Removing the file stops
the cutting; relays that ended before the file appeared are not touched.

The throttle works the same way. A media request reads the throttle file when
it arrives, and the watcher reads it every 0.25 s and gives each open relay
the rate it finds, or none once the file is gone. Each relay holds a token
bucket that starts empty when the throttle begins (or resumes) on it and fills
at the rate, and sends a piece of the answer each time the bucket holds one:
0.1 s of the rate, at least 1 KiB. So over any stretch a connection receives
at most the rate times its length plus one piece; the response headers are
not counted. A relay waiting for its bucket looks for a cut or a new rate at
least every 0.25 s, so `refuse-media` still cuts a throttled relay within
about half a second. The probe reads the upstream only as fast as it writes
to the client, so the server sees a slow reader: at a rate low enough, a
server's own write timeout may end a long answer, which the probe logs as
`error`. A throttle line names the rate in force at the first throttled
write; a later change of rate is not logged.

Deploying a new version of the script changes nothing until each probe is
restarted with the flags it was started with (the lab records them); the
control files and their names stay the same, and `throttle-media` works only
after that restart.

Unit tests: `python3 -I -B -m unittest discover -s scripts/header-probe`.

## The harness

### Build and install a debug package

The harness exists only in the dev package, which sets `debug`:

```sh
npm ci
npm run sideload:dev           # builds out/silo-roku-dev.zip and installs it
npm run console                # the debug console, where the harness logs
```

The diagnostic screen then says "press * (Options) for the transport harness".

### Use

1. **Server:** type the probe's origin listener, for example
   `http://192.0.2.20:8080`. A bare host gets `https://`; plain HTTP asks
   "Connect without encryption?" first. The harness checks
   `GET /api/v2/system/info` (`api_major` 2) before sending any credential.
2. **Sign in:** user name, then password (secure entry). The password goes
   once into `POST /api/v2/auth/login` and is never stored or logged.
3. **Profile:** pick one; PIN-locked profiles open the PIN pad.
4. **Item ID:** the catalog item ID that `GET /api/v2/watch/{id}` accepts. The
   harness lists its file versions; **File** cycles them. **Audio track**
   cycles "server default" and each track, sent as `audio_track_index` (the
   track's position in the version). **Subtitle track** cycles "off" and each
   track, sent as `subtitle_track_index` in the server's combined ordinal
   space: external tracks first, then embedded ones. The menu shows that
   ordinal as `#n`. Protocol v3 selects a subtitle only from the request and
   ignores the profile's subtitle preferences, so with "off" the plan has
   none.
5. **Toggles** steer the server through what the client advertises:
   `original_http` off forces a remux; HEVC and E-AC-3 off forces an HEVC
   transcode and E-AC-3 conversion; subtitle sidecars off withholds
   `sidecar_text` and the subtitle features; `ForwardQueryStringParams` false
   overrides Roku's default on the content; **Start** sends
   `start_position: 0` instead of using the server's resume point. Two
   server prototype toggles, off by default, ask for features only a
   prototype server branch knows (assumption A-13): **TS copy remux** adds
   `hls_copy_mpegts_v1` to `deliveries.hls.features` (S-15), and **No
   playlist variables** adds `hls_no_variable_substitution_v1` to
   `client_features` (S-21). A server that rejects them answers the start
   with a Problem, and the menu shows its type, detail, and field errors.
6. **Play.** Keys: OK pause or resume; Left/Right seek 30 s; Rewind/Fast
   Forward 5 minutes; Up shows or hides the stats; Down cycles the subtitle
   transport (off, native URL track, `tmp:/` copy); Back stops the session
   (`DELETE /api/v2/playback/{session_id}`) and returns to the menu.

The stats overlay shows only non-secret facts: delivery and decision reason,
protocol and container with the chosen `StreamFormat`, whether the media
origin is the API (and whether headers were attached) or a proxy, timeline
offset, player start and the `PlayStart` read back from the content, `Video`
state, position (player and source), `videoFormat`, `audioFormat`,
`IsPassthruCodecActive()`, the subtitle transports, the last action (local
seek, `seek_reanchor`, `failure_recovery`, a queued seek), the prototype
features advertised, progress results, and the `Video` error code and
category.

A `Video` error opens a panel beside the stats with the node's `errorCode`,
`errorMsg`, `errorStr`, and `errorInfo` (URLs reduced and credential-like
members masked by the logger's redactor). It stays until Back, through the
recovery replan and any later error, and the menu's status repeats the last
error's code and category.

The console (`npm run console`) explains a run: one line per start, replan,
and stop outcome with the plan's delivery, decision reason, stream and
container, recipe, media origin, timeline, and the harness toggles, or the
terminal reason or Problem; failed progress posts; `Video` state changes;
seeks; subtitle transport changes; and each `Video` error as a `WARN`. Every
line goes through `source/util/log.bs` and is redacted.

Behaviour worth knowing: progress posts every 10 s while playing, paused, or
buffering; a seek outside the plan's timeline sends `seek_reanchor`; a seek
key pressed while a replan is in flight is queued (the newest target wins,
counted from the in-flight reanchor's target) and applied once the replan has
settled and the plan is playing; the first `Video` error sends one
`failure_recovery` replan, and a later error is shown without another; the
subtitle `tmp:/` copy is downloaded before playback with a 10 s deadline; VTT
sidecars request `timestamp_offset`, SRT sidecars are not shifted (stats say
"offset applied no" on a remux).

## Test procedures

Replace `silo.dev.example` with the dev server and `192.0.2.20` with the
probe host. Each run starts the probe, then plays from the harness with its
server set to the probe's origin listener.

### H1: credential headers per request class, none off-origin

1. Baseline. `python3 -I scripts/header-probe/header_probe.py --upstream https://silo.dev.example --log h1-baseline.jsonl`.
   Play, with a PIN-locked and an unlocked profile: an H.264/AAC MP4 original
   (defaults), the same with `original_http` off (HLS copy remux), and with
   HEVC and E-AC-3 off on an HEVC source (HLS transcode). On each: seek Left
   and Right, Fast Forward (a reanchor on the remux), then Down twice for both
   subtitle transports on a title whose plan selects a sidecar. Pass: every
   `stream`, `playlist`, `segment`, and `subtitle` line on `origin` has
   `authorization` and `x_profile_id` true, and `x_profile_token` true exactly
   for the PIN-locked profile. Report any class that is false.
2. Proxy origin. On a server with a proxy node, run a second probe in front of
   the node (`--upstream http://proxy-node:PORT --origin-listen 0.0.0.0:9090 --log h1-proxy.jsonl`)
   and set the node's public URL to `http://192.0.2.20:9090`. Play an
   original and a remux; the stats show "proxy (no account headers)". Pass:
   that probe's summary has `credential_headers_seen: false`.
3. Off-origin redirects of media. Add
   `--foreign-listen 0.0.0.0:8081 --foreign-public http://192.0.2.20:8081 --redirect stream=foreign --redirect playlist=foreign --redirect segment=foreign --redirect subtitle=foreign`
   and play the three routes again. Repeat with `--redirect-status 307`.
   Pass: no `alert` line, and the `foreign` summary has
   `credential_headers_seen: false` (playback is expected to fail).
4. Off-origin redirects of the API client. `--redirect api=foreign`, then sign
   in and play; repeat with `--redirect-status 307` (a 302 may turn POST
   into GET). Pass as in step 3.
5. Absolute child URIs. `--foreign-listen ... --foreign-public ... --absolute-children foreign`
   with `original_http` off, then with HEVC and E-AC-3 off. Pass as in step 3.
6. Downgrade to `http://`. Serve `origin` over TLS (`--origin-listen 0.0.0.0:8443 --tls-cert fullchain.pem --tls-key privkey.pem`)
   for a host name in the certificate, add
   `--plain-listen 0.0.0.0:8082 --plain-public http://probe.example.net:8082`,
   and repeat steps 3 to 5 with `plain` as the target. Pass: the `plain`
   summary has `credential_headers_seen: false`.

Not covered by the harness: requests after a token refresh (it does not
refresh) and Poster requests (it shows none); those wait for M0-10.

### H2: signed `#EXT-X-DEFINE` playlists

1. `python3 -I scripts/header-probe/header_probe.py --upstream https://silo.dev.example --extra-facts --log h2.jsonl`.
2. With `original_http` off, play a feature-length title (a remux); the
   `playlist` lines should show `ext_x_define: true`. Play 2 minutes, Fast
   Forward and Rewind (each a `seek_reanchor`; the stats show "seek_reanchor
   adopted"), and play on. Repeat with HEVC and E-AC-3 off (a transcode).
3. Repeat both with `ForwardQueryStringParams: false`. Compare
   `duplicate_query_keys` on `segment` lines: `true` with Roku's default means
   Roku appended the playlist's query to child requests that already carry
   `st`.
4. Proxy-origin HLS: as H1 step 2 with `original_http` off.
5. Against a server with the S-21 prototype, repeat the long transcode with
   **No playlist variables** on: `playlist` lines should show
   `ext_x_define: false`. Record `bytes` and `playlist_entries` for each
   playlist Roku accepts or refuses (an `abort` line).

Pass: playback starts and continues after each seek, with no `Video` error.

### H8: copy-remux segment envelope

1. Run the probe with `--extra-facts`.
2. With `original_http` off, play copy remuxes of increasingly high-bitrate
   sources (4K HEVC on the 4K device, 1080p H.264 on the 512 MB device); for
   each, start and seek forward twice.
3. Record the largest `bytes` on a `segment` line that started and seeked,
   and the first source that did not. Pass for that source: the stats show a
   `Video` error and "failure_recovery adopted" (normally a transcode). A
   `Video state` stuck at `buffering` with no error for 20 s is a hang, which
   activates server issue S-11.

### H14: subtitle transports

1. Keep subtitle sidecars on. Choose the track under test (external SRT, an
   embedded text track, an ASS track) with **Subtitle track**.
2. Play an original and a remux (`original_http` off). The stats line
   "Subtitles" shows the artifact format, whether the `tmp:/` copy downloaded
   (and its status), and whether the timeline offset was applied.
3. Press Down for the native URL track and time how long the first cue takes
   to appear; Down again for the `tmp:/` copy. Then seek, Fast Forward (a
   reanchor rebuilds both tracks with the new offset), and check cue timing.
4. On a transcode of a title with embedded text (HEVC and E-AC-3 off), the
   plan may carry an HLS subtitle rendition instead (stats: "none in plan");
   check it through Roku's `*` caption settings.

Pass per section 6.8 of the plan: a selected track is visible within 5 s of
start or selection. On a proxy-served plan only the `tmp:/` copy can work,
because the `Video` node gets no account headers.

### H19: audible muxed-fMP4 audio on copy remuxes

1. Set `original_http` off (HEVC and E-AC-3 on).
2. Play H.264 with AAC and with AC-3 on every device; on 4K devices also HEVC
   with AAC, E-AC-3, and E-AC-3 JOC.
3. For each, check the stats (delivery `server_remux_hls`, recipe audio
   codec, `audioFormat`, passthrough active), the TV's or receiver's info
   panel, and listen. Pass: audio is audible and `audioFormat` is set. Silence
   with `Video state: playing` fails H19 and activates S-15 or S-4.
4. Against a server with the S-15 prototype, repeat with **TS copy remux** on.
   The stats show "Prototype features: hls_copy_mpegts_v1".
