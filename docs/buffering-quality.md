# Buffering quality and connection speed on Roku

Status: Implemented on this branch; hardware run 33 on the Ultra
(`docs/hardware-evidence.md`) against the server change, which is not yet
proposed upstream (`docs/implementation-assumptions.md` AG-390, AG-391)
Date: 2026-10-26, revised 2026-10-27
Shared design: silo-server `docs/design/2026-10-17-buffering-quality.md`
(`fdbb88711`, #2699), referred to below as **the shared spec**. Vectors:
silo-server `docs/design/schemas/buffering-quality/v1/vectors.json`.
Reference clients: silo-apple #842 (`604af281`, tvOS), silo-android #636
(`ff8798987`, Android TV).

## 1. Summary

Apple and Android now run one stall controller and one connection speed test,
both defined by the shared spec. Roku runs an older reducer
(`source/playback/autoQuality.bs`) that follows the web player's pre-spec
policy. This document brings Roku onto the shared spec in two phases, matching
the shared spec's own phases:

1. **Detect and lower.** Replace `playback.autoQuality` with the shared
   controller, add the undo pill, the Ask-first prompt, the
   **Lower quality when buffering** setting, the learned-limit row and the
   `plan_summary` route event, and send the `buffering_quality_v1` request
   fields.
2. **Measure and show.** Add the quick and accurate speed tests, the
   connection check schedule, the start estimate, playback throughput samples
   and the Connection group in Settings.

Roku's playback stack can't do three things the other clients rely on. It
can't stream byte counts from an HTTP body, it can't stop a redirect, and it
can't read how many milliseconds are buffered past the playhead. Section 5
covers how Roku works around each, and section 7 lists what needs a hardware
spike before the design is final.

## Functional spec: what the viewer sees

### While watching

| Situation | What happens |
| --- | --- |
| Auto, **Automatically** (default), playback keeps buffering | Silo switches to a lower quality without asking. A card at top right reads "Quality lowered to stop buffering" with **Restore quality** and a 15 s draining bar. **Restore quality** goes back to full Auto. Back or the timer dismisses the card and keeps the lower quality. If buffering continues, Silo lowers again, as far as 360p (about 300 kbps). |
| A quality the viewer picked, playback keeps buffering | Silo never lowers it silently. The card reads "Playback keeps buffering · Try a lower quality to keep watching" with **Lower quality** and **Keep quality**. **Lower quality** steps down one rung for this playback only; the saved preference doesn't change. **Keep quality** or Back stops asking for this title at this quality. If the timer runs out, Silo can ask again 2 minutes later. |
| **Ask first** | The same prompt appears on Auto too. |
| **Never** | Nothing is shown and nothing changes. |
| Nothing lower exists | "Can't lower quality for this video", once per title. |
| Quality menu | Auto reads "Auto · limited after buffering" while a remembered limit holds it down. |

"Keeps buffering" means two stalls of at least a second within two minutes,
or one stall of 6 seconds, after a stream's first 10 seconds.

These never count:

- buffering after a seek or a pause;
- a dropped connection, which shows "Reconnecting…" as today;
- a stall the device causes while its buffer is full.

**Cards and the remote:**

- Skip Intro, Skip Recap, Up Next, the Options panel and error screens take
  priority. A buffering card waits behind them and comes back with the time
  it had left. Its timer also pauses while playback is paused.
- With the controls hidden, OK presses the highlighted button. On the prompt,
  Left and Right move between its two buttons.
- With the controls shown, the card takes focus, and Down moves to the
  transport bar.

### Remembering a slow connection

- **The limit.** After Silo lowers quality on Auto, the server remembers a
  limit for this Roku on this network for 24 hours. Later titles start on
  Auto under it, so they don't buffer first and then drop.
- **What clears it:** **Restore quality**, **Reset** in Settings, a
  **Test speed** result faster than the limit, or expiry.
- **Other networks.** A different home network or public address starts
  without a limit.
- **Starting playback.** Auto plans with the server's latest speed reading for
  this Roku. A 63 Mbps 4K remux on a 40 Mbps link starts on a version or
  transcode that fits.

### Settings → Playback

- **Lower quality when buffering**: Never, Ask first or Automatically.
  - It is a per-profile setting with a per-device override ("Use profile"),
    like Intros.
  - It is hidden on servers that don't offer it, and those servers behave as
    Automatically.
- **Learned limit.** "Limited to 44 Mbps after buffering on Oct 17", with
  **Reset**. It shows only while a limit exists, and not in Never.
- **CONNECTION → Connection speed**, with **Test speed**. Under it, one of:
  - "48 Mbps · measured 3 minutes ago on Ethernet"
  - "Faster than 115 Mbps · measured …"
  - "Faster than 51 Mbps · seen during playback 2 hours ago"
  - "Not measured yet"
- **Budget line.** "Auto plays videos up to 35 Mbps without converting
  them."
- **Test speed.**
  - It takes up to 10 seconds and moves up to 1 GB.
  - It won't run during playback: "Stop playback before testing, then try
    again."
  - Too many tests in a row: "Try again in N seconds".
  - It can also fail with "Couldn't measure the connection speed. Try again."
    or "Couldn't save the speed test result. Try again."

### Automatic speed test

- **When it runs:** about 5 seconds after launch, sign-in, a profile switch or
  a network change, and only when the server holds no current reading for
  this Roku on this network. A reading lasts 7 days by default.
- **When it doesn't:** during playback or within a minute of a playback start.
- **Size:** up to 3 seconds and 100 MB. Usually it stops sooner, once the link
  proves fast enough for the fastest file the viewer could play.
- **Admin control.** An admin can turn automatic tests off.
- **Visibility.** Viewers don't see automatic tests. Admins see each device's
  speed, limit and buffering summary on the server's device page.

### Where Roku differs from Apple TV and Android TV

- Speed readings can come out somewhat lower, because Roku times whole
  downloads (section 5.1).
- Until the server offers a speed-test URL that doesn't redirect, Roku runs no
  speed tests. Settings then shows only the speed seen during playback.
- Roku can't lower quality before a direct-play stream's first frame. A start
  that never plays takes today's retry path.
- A title ended with the Home button reports no buffering summary.
- Every Roku link counts as unmetered, and there is no cellular quality.

## 2. Where each client stands

| | Apple tvOS | Android TV | Roku today |
| --- | --- | --- | --- |
| Stall controller | Shared, replays all vectors | Shared, replays 66 controller cases | Own reducer, web pre-spec rules |
| Step-down estimate | `floor(delivered × 7 / 10)` | Same | `Int(delivered × 70 / 100)`, also capped at the last estimate |
| Kept estimate | Until Restore, quality change or new attempt | Same | 30-minute TTL, survives Retry and restarts |
| Unadopted lowering | Rearm after 60 s | Same | 5 min hold, doubling per refusal to 30 min |
| Outage | No data for 4 s on a network wait | 4 s progressive, 15 s HLS | Stall counts only while media arrives (run 15, AG-186/187) |
| Undo pill / prompt / notices | Yes | Yes | None (deferred, spec 3.3, AG-258) |
| Setting and learned-limit row | Yes | Yes | No |
| `buffering_quality_v1` fields | Sent | Sent | Not sent; the vendored contract already has them |
| `plan_summary` | Sent, journalled across exit | Sent on player close; TV keeps no exit journal | Not sent |
| Speed test | URLSession delegate, 500 ms windows | OkHttp 64 KiB reads, 500 ms windows | None |
| Start estimate | Max of current probe and sample, source `probe` | Same | The reducer's lowered estimate only |
| Connection settings | Playback → CONNECTION section | Connection group | None |

Roku already has what the port needs underneath: `bufferingStatus` and
`downloadedSegment` media-arrival tracking, an outage and reconnect path,
replan serialization with `replan_request_id`, route events, a settings
contract reader with `profile` / `profile_device` scopes, and a vendored
contract pinned at silo-server `2b88b1bb` whose OpenAPI already carries
`bandwidth_estimate_source`, `observed_throughput_kbps`, `learned_limit` and
`plan_summary`.

## 3. What changes in Roku's current behaviour

The shared spec says every client implements the controller identically, so
the Roku-only rules in `autoQuality.bs` and spec section 9.7 go:

| Roku rule today | Becomes |
| --- | --- |
| Grace starts at the plan's (or a reload's) first frame | Grace starts at first play or the first wait before it; a replacement before the attempt has played keeps the attempt's grace |
| A stall counts only from first to latest media arrival | A stall is wall-clock time outside an outage; an outage is media silence (section 5.2) |
| 30-minute estimate TTL, carried across Retry and restarts | Kept step-down estimate for the playback attempt only; the server's learned limit (24 h) carries a slow link across attempts |
| Refusal hold, 5 min doubling to 30 min | `REARM_AFTER_UNADOPTED_MS = 60000`; `NO_LOWER_COOLDOWN_MS = 300000` for a no-lower result |
| A step-down is queued at AUTOMATIC rank and any request may displace it | A lowering that can't be sent now fails (`replan_failed`), as the shared spec requires; it is never queued |
| Auto's refusals are silent | "Can't lower quality for this video" once per title, per the shared spec |

The run 15 protection is kept: an original whose connection is cut no
longer steps down. The outage rule in section 5.2 does that job in place of
media-only stall counting. The run 15 and run 19 sequences in
`tests/playback/session.spec.bs` stay as regression tests, rewritten against
the new adapter.

## 4. Behaviour (phase 1)

### 4.1 Controller

`source/playback/bufferingQuality.bs` (namespace `playback.bufferingQuality`)
is a pure reducer: state in, `{state, outputs}` out, with the clock passed in.
It makes no requests and draws nothing, like `playback.controls`. It
implements the shared spec's *Terms*, *Behaviour* and *Later replans after a
lowering* sections with the shared constant names. Its inputs and outputs are
the vectors' events and outputs, so the Rooibos runner can replay
`vectors.json` without translation.

`playback.session` owns one controller per playback attempt of a title. The
state that belongs to the title survives a new attempt the viewer did not
choose (renewal, Retry, failure recovery): the answer, the once-per-title
notice and the re-offer wait. The kept estimate does not. There is no Watch
Party on Roku, so the controller never suspends.

### 4.2 Requests

- **Gating.** When the `/api/v2` capability `features` or a decision's
  `server_features` list `buffering_quality_v1`, starts and replans add it to
  `client_features` and may carry `bandwidth_estimate_source`,
  `observed_throughput_kbps` and `learned_limit`. Without it, the controller
  still runs and sends the same replans without those fields. One function in
  `playback.capabilities` strips them, as Apple's `permittedMembers` and
  Android's `gatedForBufferingQuality` do.
- **Lowering on Auto.** A `quality_change` with `quality_preference: "auto"`,
  the step-down estimate, `bandwidth_estimate_source: "observed_rebuffer"`,
  and `observed_throughput_kbps` when section 5.3 measured one.
- **Lowering a picked quality** (after **Lower quality**). A `quality_change`
  with the lower rung's label and no estimate.
- **Client replans** (track change, seek reanchor, recovery, output change).
  On Auto they repeat the kept estimate without a source. They never carry the
  speed-test reading.
- **Restore quality.** Auto, no estimate, `learned_limit: "clear"`. If another
  replan is in flight, it waits in the queue at INTENT rank. If a newer
  request replaces it, the `clear` is owed to that request.
- **Never mode.** Every start and replan sends `learned_limit: "ignore"`,
  unless the request owes a `clear`.
- **Retry.** A replan with no response is resent with its original body and
  `replan_request_id`. The session already does this; the controller's replans
  must go through the same path.

### 4.3 Player UI

Roku follows tvOS, as `AGENTS.md` requires.

- **Prompt.** A notice card titled "Playback keeps buffering" with the line
  "Try a lower quality to keep watching", and two capsules, **Lower quality**
  (primary) and **Keep quality**.
- **Undo.** The caption "Quality lowered to stop buffering" over a
  **Restore quality** capsule.
- **Notices.** "Quality lowered to stop buffering" and "Can't lower quality
  for this video", information tone, 5 s, through `PlayerStatus`'s notice
  slot. The existing notice timer counts only while nothing outranks the
  notice.
- **Timer.** 15 s, drawn as a thin track draining along the card's bottom
  edge. It freezes while paused or hidden and resumes with the time left.
- **Placement.** Top-trailing, tvOS's notice position, below any notice.
- **New component.** `components/player/buffering/BufferingPill`, built from
  the existing `CapsuleButton` and `PlayerPill` capsule styles.
- **Keys.** The controls reducer (`source/playback/controls.bs`) owns them, as
  it does for Skip Intro.
  - With the controls hidden, OK acts on the lit capsule. On the prompt,
    Left/Right move between Lower and Keep; on the undo pill, they keep their
    skip meaning.
  - With the controls shown, the pill takes focus when it appears, unless the
    viewer is scrubbing or the Options panel is open. Down moves to the
    transport.
  - Back, in `controls.back()` order after scrubbing and before Skip Intro:
    on the prompt it answers **Keep quality**, on the undo pill it only hides
    the pill. Either way the key is consumed.
- **Priority.** Skip Intro, Skip Recap, Up Next, the Options panel and the
  error panel hide the pill with its timer frozen (`pill_obscured` and
  `pill_unobscured`). A plan change or a viewer pick discards a hidden pill.
- **Quality menu.** The Options Quality row reads "Auto · limited after
  buffering" while the plan carries `playback_plan.bandwidth_limit` on Auto.

### 4.4 Settings (phase 1)

- **Lower quality when buffering** joins Playback, next to Maximum Bitrate.
  - Options: Never, Ask first, Automatically.
  - Footer: "What Silo does on Auto when playback keeps buffering. Silo always
    asks before lowering a quality you picked."
  - It is shown only when the server's settings contract lists
    `playback.buffering_quality_mode`. Roku decides by the key's presence, not
    by revision number. Without the key, the row is hidden and the player runs
    `always`.
  - Add the key to `SETTINGS` in `scripts/sync-fixtures.sh` and re-vendor.
- **Learned-limit row.** When the server advertises `buffering_quality_v1`,
  `GET /api/v2/playback/connection` is read when Playback opens, after a
  network change while it is open, and after Reset.
  - The row reads "Limited to 44 Mbps after buffering on Oct 17", with
    **Reset** (`DELETE /api/v2/playback/connection/learned-limit`).
  - It is hidden in Never mode.
  - Failure text: "Couldn't reset the limit. Try again."
- **Player read.** The player reads `playback.buffering_quality_mode` with its
  other preferences (`playback.preferences`). Until that read answers, it uses
  the last mode it saw for this profile on this device, kept in the registry.

### 4.5 `plan_summary`

Sent when the server advertises `playback_plan_summary_v1`, whenever a plan
stops being the playing plan: replaced, stopped, failed or a new attempt.

- **Fields.** `played_ms`, `stall_count`, `stall_total_ms`,
  `stall_longest_ms`, `delivered_kbps`, `buffering_mode`, `buffering_action`,
  `bandwidth_estimate_kbps`, and `throughput_kbps` (phase 2, section 5.3).
- **Delivery.** The event goes through `session.routeEvent` with one
  `event_id` per adoption. It is retried once in-session on a transport
  failure.
- **Exit.** Roku gives a channel no exit callback, so, like Android TV, a plan
  the Home button ends sends no summary (section 6).

## 5. Behaviour (phase 2) and the Roku workarounds

### 5.1 Speed test

**Meter.** `source/playback/speedTest.bs` holds the shared spec's *Measuring*
arithmetic as a pure function of `[t, bytes]` arrivals and clock ticks:

- 500 ms windows; window 0 never counts.
- The quick test settles over its last 2 windows within 3 s and stops early at
  the target. The accurate test settles over its last 6 windows within 10 s.
- The whole-transfer lower bound, the 100–1,000,000 kbps range, and the 10 s
  first-byte abandon.

It replays `probe_cases` unchanged. This part has no Roku-specific risk.

**Transport (Roku workaround 1, needs spike S1).** `roUrlTransfer` reports
only a finished transfer, with no byte progress, and a body saved to `tmp:/`
counts against the app's memory, so neither a 100 MB nor a 1 GB single
download is usable. The probe instead runs in a `Task` as back-to-back
`AsyncGetToFile` chunks on one `roUrlTransfer` object, so the connection is
kept:

- The first chunk is 2 MB; each later one is sized to take a second at the
  last one's rate, up to 16 MB, since each request costs about 200 ms on the
  Ultra (hardware run 33: 2 MB chunks read 35 Mbps, second-long chunks 79
  Mbps). Each chunk's file is deleted as it completes, so at most one chunk
  sits in `tmp:/`.
- Each chunk's bytes are spread evenly over the time from its request to its
  completion, because Roku shows no progress inside a transfer. Measured on
  the Ultra 4850X (OS 16.0.4, Ethernet), 2026-10-27:
  - `roFileSystem.Stat` on an `AsyncGetToFile` target returns an empty object
    for the whole transfer.
  - The file appears complete, 20,000,000 bytes, in the same 50 ms poll as the
    `roUrlEvent` (2,101 ms, about 76 Mbps).
  - Request latency is therefore inside each chunk's time, and the first
    chunk stands in for window 0.
- The clock starts at the first byte of the first chunk. The gaps between
  chunks count as time, so the result can only read low, which is the safe
  direction.
- The chunks of a quick test add up to at most 100 MB, and an accurate test's
  to at most 1 GB. The "whole transfer" rule applies to that total.

This is a Roku deviation. Section 6 records it, with its accuracy measured
against an Apple TV on the same link.

**Redirects (Roku workaround 2, needs a server change).** `bandwidth_probe_url`
can answer 307 to a probe-only URL on a media proxy. A-14 records that Roku
follows redirects with no app control and forwards `X-Profile-Id` and
`X-Profile-Token` to the new origin. Apple strips those headers on redirect,
and Android follows the one hop without credentials. Roku can do neither.

- **Server change.** `GET /api/v2/playback/bandwidth-probe/location?size=N`,
  advertised as `bandwidth_probe_location_v1`, answers
  `{"url", "expires_at"}`: the proxy's token URL when a proxy serves the
  media, else a signed probe URL on the API origin
  (`/api/v2/playback/bandwidth-probe/signed/{token}`). The URL takes no
  credentials and any `size` up to 1,000,000,000 for two minutes, so it
  serves every chunk. It is a separate operation because the probe is a raw
  byte route, which may not answer JSON (silo-server branch
  `feat/bandwidth-probe-target`, not yet proposed upstream).
- **Without it,** Roku runs no speed test. It still reads the connection,
  shows the reading the server holds (playback samples), and sends that
  reading on starts. It does not measure the API path in place of the media
  path; the shared spec forbids that.

**Results.** Results go to `POST /api/v2/playback/bandwidth-probe/results`
with `{kbps, bytes, duration_ms, transport, lower_bound?, manual?}`. The two
booleans are sent only when true. `transport` comes from
`roDeviceInfo.GetConnectionType()`: `WiredConnection` is `ethernet`,
`WiFiConnection` is `wifi`, anything else is `other`. A result is kept only if
the server stored it, or the POST failed for a transport reason. A
**Test speed** result drops the cached playback sample.

**429.** Read `Retry-After` as integer seconds. A missing or unreadable value
means 30 s, and anything under 1 means 1. The hold applies to automatic tests
on that server, in memory, for the life of the app.

### 5.2 Stall signals from the `Video` node (Roku workaround 3)

`source/playback/bufferingSignals.bs` turns `Video` events into the
controller's events:

| Controller event | Roku source |
| --- | --- |
| `playing` | `state = "playing"` with `position` advancing |
| `waiting` (network) | `state = "buffering"` with `bufferingStatus.isUnderrun` after the plan has run, or before first play |
| `waiting` cause `seek` | The session's own seek, and every wait after it until playback runs (before first play, the start keeps it) |
| `waiting` cause `reload` | A source the session replaced or reopened after the attempt played: retrack, reconnect, credential renewal |
| `pause` | `state = "paused"`, the viewer's pause, `finished`, `stopped` |
| `transport_error_start` | `playback.recovery`'s reconnect start; the API answering unreachable or 502/503/504; the link going down (`roDeviceInfoEvent` link status); or a network wait with no media arrival for `OUTAGE_NO_DATA_MS = 4000` (progressive) or `OUTAGE_NO_DATA_SEGMENTED_MS = 15000` (HLS) |
| `transport_error_end` | Media arrives again: a `bufferingStatus` reading above the last, a `downloadedSegment` with status 0, or playback runs |

"Media arrival" keeps today's AG-165 definition (`playback.recovery.noteMedia`).
That definition is what run 15 needed: the buffer held at 2% shows up as
silence, so the wait becomes an outage instead of a stall.

**Renderer waits.** `Video` has no buffered-ahead in milliseconds, only a fill
percentage while buffering. Roku follows the AVPlayer rule: no ample
threshold. The renderer rule then rests on the fill when the wait starts:

- A wait whose first reading is at least `RENDERER_FILL_PERCENT` is a renderer
  wait. That is the "full buffer stands in for decoder input" reading of
  AG-165.
- It becomes a stall once readings fall below that fill.
- Spike S3 sets the threshold. Until it does, every wait is a network wait.

**Slow start.** Roku's 20 s no-progress clock (`recovery.STALL_MS`) stays the
failure path. A start lowers before the attempt has played only with
evidence: the plan's measured throughput (section 5.3) below its delivered
bitrate. On a progressive start without a measurement, there is no evidence,
and the start keeps the failure path. The shared spec allows this ("a plan
the client cannot measure gives no evidence").

### 5.3 Throughput (`throughput_kbps`, `observed_throughput_kbps`)

**Primary source (spike S2).** `roSystemLog` `http.complete` events give each
media request's bytes and its transfer time from first byte.

- `roSystemLog` is main-thread only. A Task's `CreateObject("roSystemLog")`
  fails with "creating MAIN-only component failed on TASK thread" (Ultra, OS
  16.0.4).
- So `source/main.bs` owns it and forwards the plan's media request events to
  the Player through a scene field.
- No `http.complete` arrived for the channel's own `roUrlTransfer` downloads.
  Whether it reports the `Video` node's requests is still unmeasured.

- Only the plan's media URLs count, matched by origin and path prefix from the
  plan. Subtitles, artwork, API calls and probes don't.
- Only requests that spent at least 1000 ms receiving count, and overlapping
  time counts once.
- The value is omitted under 1000 ms total, under 100 kbps, or when the link
  status changed during the plan.

**Fallback.** If `roSystemLog` isn't available where the session runs, HLS
plans use `downloadedSegment` (`SegSize` and `DownloadDuration`) under the
same 1000 ms rule, and progressive plans omit the sample.

### 5.4 Schedule

- **When a check runs:**
  - at launch once signed in;
  - after sign-in, profile switch or server change (a re-login counts, and a
    result from before a sign-out is discarded);
  - on `roDeviceInfoEvent` link-status or internet-status changes, and on a
    change of `GetConnectionInfo()` gateway or SSID.
- **Foreground.** Roku channels don't run in the background (no Instant
  Resume), so there is no foreground trigger.
- **Order of a check.**
  1. Read the capabilities and `GET /api/v2/playback/connection` at once, even
     during playback, so a start a few seconds after launch already carries
     the reading.
  2. After a 5 s quiet delay, read again, then run a quick test, if all of
     these hold: automatic tests are on, no current reading proves the link,
     no 429 hold applies, and the media gate is open.
- **Proving the link.** The shared spec's rules, with Apple's and Android's
  clock handling: nothing is current until `bandwidth_probe_max_age_seconds`
  is known, and a server time ahead of the device counts as age 0.
- **Media gate.**
  - No automatic test while a `Player` exists and is loading or playing, or
    within 60 s of a playback start.
  - Starting playback cancels a running test.
  - **Test speed** waits only for no media.
- **Metered.** Roku reports no metered links, so every link is unmetered and
  automatic tests are allowed. The shared spec's rule for platforms that can't
  report link type applies; a TV isn't a phone or tablet.
- **Start estimate.** A start sends the higher of the current probe and the
  current playback sample, as `bandwidth_estimate_kbps` with source `probe`,
  for the same server and network. Apple and Android also label a sample-based
  figure `probe`.
- **Older servers.** Against a server without `connection_speed_v1`, Roku runs
  no tests and sends no estimate. Apple and Android do the same.

### 5.5 Settings (phase 2)

A **Connection** section heading in Playback, below the buffering rows,
matching tvOS's CONNECTION section:

- **Connection speed**, with the value **Test speed** or **Testing…**. Its
  status line is one of:
  - "48 Mbps · measured 3 minutes ago on Wi-Fi" (or Ethernet, or "this
    connection")
  - "Faster than 115 Mbps · measured …" for a lower bound
  - "Faster than 51 Mbps · seen during playback 2 hours ago" for a sample
  - "Not measured yet"
- **Messages.**
  - "Try again in N seconds" ("1 second" at one), which clears itself after N
    seconds
  - "Stop playback before testing, then try again."
  - "Couldn't measure the connection speed. Try again."
  - "Couldn't save the speed test result. Try again."
- **Budget line.** "Auto plays videos up to 35 Mbps without converting them.",
  from `auto_budget_kbps`. It is hidden in Never mode while a limit exists.
- **Rates.** Rounded down: kbps under 1 Mbps, one decimal under 10 Mbps,
  whole Mbps above, with no digit grouping.

All strings go through `locale/`.

## 6. Roku deviations to record in `docs/spec.md`

| Deviation | Reason |
| --- | --- |
| Speed test in chunked requests, each timed whole, not one streamed body | `roUrlTransfer` has no progress events and a file appears only once its transfer completes; `tmp:/` counts as app memory |
| No speed test until the server offers a no-redirect probe | A-14: Roku forwards profile credentials across redirects |
| No ample-buffer renderer rule; renderer waits judged by buffer fill | `Video` exposes fill percentage, not buffered milliseconds |
| No `plan_summary` for a plan the Home button ends | No exit callback; Android TV does the same |
| No foreground trigger for connection checks | Roku channels don't background |
| Progressive starts never lower before the first frame (unless spike S2 shows `roSystemLog` sees the request) | No in-flight byte count for the `Video` node's range request |

## 7. Unknowns needing a hardware spike

These run on the Ultra 4850X and the TCL Roku TV through the lab relay,
against a lab sandbox with a shaped link, before phase 2 code is
merged:

- **S1, probe transport.**
  - Settled: `Stat` shows nothing until the transfer completes, and no
    BrightScript API reports a link rate. `GetConnectionInfo()` on Ethernet
    has only type, interface, addresses, gateway, DNS and MAC, and ECP
    `device-info` has only `network-type`.
  - Still open: Wi-Fi fields on the TCL TV.
  - Still open: does a reused `roUrlTransfer` keep the connection between
    chunks?
  - What does the chunked test read against an Apple TV's test on the same
    link at 20, 100 and ~400 Mbps?
  - How much `tmp:/` and memory pressure does it cause on the low tier?
  - The Ultra's Ethernet is 100 Mbit, so Wi-Fi is the fast case.
- **S2, `roSystemLog`.**
  - Can it be enabled in the Task or render thread that owns the session?
  - Do `http.complete` and `http.error` cover the `Video` node's HLS segment
    and progressive range requests, with byte and timing fields?
- **S3, buffering readings.**
  - How often do `bufferingStatus` readings arrive during a shaped stall, a
    cut link and a renderer catch-up?
  - This sets `RENDERER_FILL_PERCENT` and confirms the 4 s and 15 s silence
    detection works from readings alone.
- **S4, redirect.** Confirm A-14's header forwarding on the probe's 307
  against a sandbox with a probe-capable proxy node. This shows whether the
  server ask is required or only prudent.

## 8. Plan

Each step is one PR with headless tests. After phase 1 and after phase 2, a
hardware run is recorded in `docs/hardware-evidence.md`.

**Phase 1: detect and lower**

1. **Vendor and gate.** Re-vendor at current silo-server `main`:
   `vectors.json` with a SOURCE note, and the settings manifest with
   `playback.buffering_quality_mode` (add it to `SETTINGS`). Add the
   `buffering_quality_v1` / `playback_plan_summary_v1` gating and field
   stripping in `playback.capabilities`, with fixture tests against the
   vendored `buffering-*` request fixtures.
2. **Controller.** `playback.bufferingQuality` plus a Rooibos runner that
   replays every `vectors.json` controller case on a fake clock and names each
   failing case. Register the new spec in `scripts/test-headless.py`
   `SHARDS`.
3. **Adapter and session wiring.**
   - Add `playback.bufferingSignals`.
   - Replace `playback.autoQuality` in `playback.session`.
   - Stop queueing lowerings, and add the owed `clear`, the kept estimate on
     client replans, and `ignore` in Never mode.
   - Port the run 15, run 16 and run 19 sequences and add the slow-start
     evidence cases.
   - Delete `autoQuality.bs` and its spec.
4. **Player UI.** `BufferingPill`, the notices, controls-reducer keys and
   priority, and the "Auto · limited after buffering" label. Add probe tests
   in `tests/components` for focus, Back order and timer freeze.
5. **Settings and telemetry.** The mode row (presence-gated), the
   learned-limit row with Reset, the last-seen mode in the registry, and
   `plan_summary`.
6. **Docs.**
   - `docs/spec.md`: rewrite 9.7, remove the deferral in 3.3, add the rows to
     5.8.1, and add the section 6 deviations.
   - `docs/implementation-plan.md` 6.7.
   - New AG entries that supersede AG-186/187's counting rule.
7. **Hardware run.** On the Ultra and the TCL TV:
   - shaped 8 Mbps and 2.4 Mbps links on a 4K original (expect a lowering and
     the undo pill, and a learned limit visible in Settings);
   - a link cut mid-play (expect no lowering: run 15);
   - Ask first on a picked quality;
   - Restore;
   - Never;
   - a server without the feature.

   Evidence goes through `silo-report-share`.

**Phase 2: measure and show**

8. **Spikes S1–S4 and the server change.** Record the results as AG
   entries, then settle sections 5.1–5.3. In parallel, open the silo-server
   PR for the no-redirect probe (section 9), plus `test_id` if S1 calls for
   it, and update the shared spec's *Media path and limits* in the same PR.
9. **Meter.** `playback.speedTest` plus the `probe_cases` runner (13 cases).
10. **Probe Task and scheduler.** The chunked transport, the result POST, the
    429 hold, the link-status `roDeviceInfo` events in `main.bs`, the check
    order and the media gate.
11. **Start estimate and throughput.** Send the reading on starts. Add the
    `roSystemLog` (or `downloadedSegment`) meter for `throughput_kbps` and
    `observed_throughput_kbps`, and the slow-start evidence path.
12. **Connection section** in Settings, with its strings.
13. **Hardware run.**
    - Speed test on Wi-Fi and Ethernet against an Apple TV on the same link.
    - Test speed clears a learned limit.
    - A 429 from back-to-back tests.
    - A start that sends the reading.
    - A shaped slow start on HLS lowering with evidence.

## 9. Server changes

| Change | What it fixes on Roku | Priority |
| --- | --- | --- |
| Probe location: `GET /api/v2/playback/bandwidth-probe/location?size=N` (`bandwidth_probe_location_v1`) answers `{"url", "expires_at"}`, a credential-free probe URL on the proxy or the API origin, valid two minutes for any `size` | Speed tests on any server, without forwarding profile credentials (A-14). One URL serves every chunk of a test | Built on silo-server `feat/bandwidth-probe-target`; required for phase 2 |
| Chunked tests count as one test: an optional `test_id` on probe requests, so the limiter admits a test's chunks as one probe and one byte budget | A sequence of chunks can't hit a `429` partway through a test, or briefly overlap the 2-per-account limit as one chunk's release races the next | Optional; adopt if spike S1 shows mid-test refusals |
| Interim `plan_summary`: a resend with the same `event_id` and a higher `played_ms` replaces the stored summary instead of being ignored | Roku sends a snapshot every few minutes, so a plan the Home button ends still reports its stalls, which the shared spec's 28-day default check counts | Optional |

Server-side timing doesn't fix the measurement gaps. The server could time
its own writes (Linux `TCP_INFO` delivery rate) for the probe or for media,
but behind a reverse proxy it would measure the hop to the proxy, and a
buffering proxy such as nginx accepts a body as fast as the server writes it.
Most self-hosted Silo servers sit behind one. Server changes also can't help
with renderer waits, which only the device sees.

## 10. Open items

1. **Server change upstream.** The probe location operation is committed on
   silo-server `feat/bandwidth-probe-target`, not yet pushed or proposed.
   Until a server has it, Roku shows the connection's reading but runs no
   test.
2. **Optional server changes.** `test_id` and interim `plan_summary` (section
   9) wait for hardware evidence and the first telemetry.
3. **Hardware run H18.** Section 7's remaining checks, and the behaviour
   section 8 lists for phases 1 and 2.
