# Silo Roku implementation plan

**Status:** Draft, revised after review rounds 1 and 2

**Last updated:** 2026-10-21

**Companion to:** [`spec.md`](spec.md). This plan says how and in what order the
client is built. Where it changes a decision in the spec, section 12 lists the
spec edit that lands with the affected work. Section 15 records the review.

## 1. Goal

Build a native SceneGraph/BrightScript Roku client for Silo that:

- runs smoothly on currently supported 512 MB Roku devices, including the
  non-OpenGL ones that still receive the current Roku OS, and on 4K Roku players
  and TVs;
- follows Roku's current performance, certification, and Static Analysis rules;
- plays the original file whenever the Roku can render it, including 4K, HDR10,
  HLG, HDR10+, Dolby Vision, and Dolby Atmos carried as E-AC-3 JOC; otherwise
  lets the server remux before it transcodes;
- never claims a format the Roku cannot actually render.

Targets, with how each is measured. The certification numbers are section 3.x
of the [criteria](https://developer.roku.com/dev/docs/certification), measured
by Roku on the Streaming Stick+ 3810X or Premiere+ 3921X. ECP debug queries need
developer mode and "Control by mobile apps" enabled; on beta builds the device
must be keyed with the app's developer key.

| Target | Limit | Measured by |
| --- | --- | --- |
| Cold launch to a fully rendered Home | ≤ 15 s on 3810X/3921X; the same as a goal on 512 MB devices | Reboot, wait 30 s, ECP `launch`; the `AppLaunchComplete` beacon report on port 8085 (`fwbeacons/track` plus `query/fwbeacons` only if M0-2 shows it lists app beacons); 10 runs, median and max; restored-session and deep-link paths. Sideload numbers are an upper bound; confirm on a beta install |
| Screen transition | ≤ 3 s; spinner after 3 s; any request answered within 10 s (3.4) | `perf` build timestamps ("requested", "first focusable") on port 8085 during an ECP journey |
| Key response, tile to tile | ≤ 250 ms | Perfetto trace (OS 15.1+, `perf` build) from input event to the frame showing the focus change, 20 moves per surface; 240 fps camera spot checks |
| Scrolling | ≥ 50 fps on reference devices, ≥ 30 fps on 512 MB devices while holding a direction | `query/graphics-frame-rate` during ECP hold scripts |
| Playback start | ≤ 8 s from the keypress, including Silo's API round trips | `VODStartInitiate`/`Complete` beacons, with a per-step breakdown from the `perf` build |
| Memory | below 80% of the app limit; no `EXIT_CHANNEL_MEM_LIMIT_FG` | `query/chanperf`, `lastExitOrTerminationReason` |
| Texture | below 70% of the `r2d2-bitmaps` maximum during browse | `query/r2d2-bitmaps` |
| Leaks | node count within 5% of baseline after 20 detail open/close cycles | `query/sgnodes/all?count_only=true` |
| Package | ≤ 4 MB; CI budget 3.5 MB | CI size check |

## 2. What "direct play wherever possible" means on Roku

### 2.1 Platform facts

Sources are in appendix B. *Community* marks evidence from public bug reports
and other open-source Roku clients (jellyfin-roku, JellyRock), not from Roku;
it must be confirmed on our hardware.

- **TrueHD, DTS-HD MA, and DTS:X cannot play in a Roku app.** Roku's Media Player
  article says "Dolby TrueHD and lossless Dolby are not supported" and "DTS-HD
  and lossless DTS are not supported". On some sinks `CanDecodeAudio` still
  answers yes (*community*: `"mat"`, `"dtshd"`, 8-channel `dts`), and playback
  then hangs or fails. The client refuses these codecs whatever the probe says,
  and treats `Video.audioFormat = "mat"` as a failure.
- **Atmos on Roku means E-AC-3 JOC (or AC-4).** AC-3 and E-AC-3 pass through to an
  HDMI sink on players; some models pass Atmos through, and only the Ultra
  4800X/4850X decode it (MS12). The Ultra LT shares model number 4800X and has no
  Dolby decode.
- **DTS core passes through only**, to a DTS-capable sink.
- **AAC:** stereo decodes everywhere. Multichannel AAC decodes to PCM stereo on
  Roku TVs and Ultras, may be re-encoded to Dolby Digital 5.1 on Dolby-decoding
  devices attached to a Dolby AVR, and is unsupported on other models.
  *Community:* FLAC, PCM, and Opus are output as stereo.
- **HDR10 and HLG are documented** for HEVC Main 10; HDR10+ is listed per device.
  `GetDisplayProperties()` describes the attached display, not the current output
  mode; Roku's own recipe checks for 4K output before HDR. *Community:* Roku
  switches the HDMI output into the content's range itself, and frame-rate
  matching changes the mode too, so `GetVideoMode()` changes during playback; no
  app API forces or suppresses a mode.
- **Dolby Vision** is documented as `dvhe.05`, `dvav.09`, and AV1 DV; the HLS and
  DASH rows list "Dolby Vision, HDR10". HLG and HDR10+ through HLS are not
  documented. There is no decoder-side DV probe: the only signal is the display
  flag. *Community:* DV in MKV direct play never enters DV mode (P8.1 and P7 play
  as HDR10, P5 shows wrong colours); the same files remuxed to HLS do.
- **HLS segments: "TS, CMAF (muxing audio and video not supported for CMAF)".**
  Silo's copy remux today packages copied video (H.264 and HEVC alike) in fMP4
  with audio muxed into the same segments, which is exactly the excluded case.
  The server's executor can package copied video in MPEG-TS, but only its
  Jellyfin-compatibility layer can ask for that today (server issue S-15).
- **The video buffer caps HLS segment size** (*community*: about 31.6 MB on
  1–2 GB devices, about 20.5 MB on 512 MB). Silo cuts copy-remux segments at
  keyframes with a 2 s target, so long GOPs at high bitrates can exceed it.
- **AV1** is documented for DASH only; **VP9** is no longer in the streaming
  specification but is still a `CanDecodeVideo` codec.
- **MKV needs `requires_mkv=1`**, which loads an extra library at launch.
- **Probes:** `CanDecodeVideo` takes only codec, profile, level and container (no
  size, frame rate, bit depth, HDR or DV); documented HEVC levels are 4.1, 5.0 and
  5.1, and higher strings are undocumented. `CanDecodeAudio` takes codec,
  profile, channel count, `PassThru` (unset = the Roku or the sink, 0 = the Roku,
  1 = the sink), `Atmos`, sample rate, bitrate and container; Roku says to query
  it before every playback. `IsPassthruCodecActive()` reports whether the sink is
  rendering passthrough audio. `EnableCodecCapChangedEvent` reports audio and
  video capability changes. `roHdmiStatus` exists on players only.
- **Requests and redirects:** `roUrlTransfer` and the `Video` node follow HTTP
  redirects with no app control and expose neither the 3xx response nor the
  final URL. Without its own `roHttpAgent`, a `Video` node's `HttpHeaders` are
  written to the global agent that Posters share. No Roku source says whether
  `HttpHeaders` reach HLS playlists, segments, or side-loaded subtitles, or
  whether headers are re-sent on a cross-host redirect; Milestone 0a measures it.
  The media player always uses HTTP/1.x.
- **Side-loaded subtitles:** the content-metadata page lists SRT, TTML and DFXP
  URLs; the streaming specification lists side-loaded WebVTT for HLS and DASH;
  the closed-caption page says WebVTT only inside HLS or DASH. Local `tmp:/`
  paths are undocumented.

### 2.2 Outcome by source format

How each source reaches the viewer once the relevant gates (section 6.2) have
passed. "Original" is the `original_http` delivery; "remux" is
`server_remux_hls` with the video stream copied. Every row was reproduced by
running Roku payloads through the server planner (`origin/main`, 2026-10-21);
what the viewer actually sees and hears is the hardware question each gate
answers. Every row also assumes the selected audio track can be copied or
converted to something the device decodes (section 6.3).

| Source | Delivery | What reaches the TV and sink |
| --- | --- | --- |
| H.264 High, Main, or Constrained Baseline up to level 4.2, with AAC, AC-3, or E-AC-3 | Original (MKV, MP4) | The original streams. Plain Baseline is transcoded |
| HEVC Main/Main 10 up to 4K and the probed HEVC level, SDR/HDR10/HLG | Original | The original streams, in their range when the output is 4K HDR. Above the probed level: SDR H.264 at up to 1080p (S-5, S-10) |
| HDR10+ | Original | HDR10+ on an HDR10+ panel, else HDR10 |
| Dolby Vision P5, or P8.1 (compatibility ID 1), within the probed HEVC level and DV `max_level` | Remux (DV removed from the original delivery) | DV video bytes unchanged, if gates G5 and G14 pass |
| Dolby Vision P8.4 (HLG base, as iPhones record) or P8.2 on a DV output | Tone-mapping transcode until H3 proves IDs 4 and 2 | SDR H.264 at up to 1080p; DV once H3 adds the IDs |
| Dolby Vision P8.x on an output without DV | P8.1: remux with the server's RPU strip, or the original with the base-layer claim (G7). P8.4: the HLG base layer only with G7 and an HLG output. P8.2: the SDR base layer only with G7. Otherwise a tone-mapping transcode | HDR10, HLG, or SDR |
| Dolby Vision P5 on an output without DV | Tone-mapping transcode (P5 has no HDR10 base layer) | SDR H.264 at up to 1080p, or a terminal error when the server has no DV tone mapper |
| Dolby Vision P7 (FEL/MEL) | Remux with the `server_dv7_to_hdr10` strip | HDR10; DV needs server issue S-2 |
| E-AC-3 JOC, E-AC-3, AC-3 | Copied on the original and on HLS copy remuxes; a video transcode re-encodes them to AAC (5.1 at 384 kbps, or stereo under the interim rule in section 6.1) | When copied, the source bitstream: Atmos where the model and sink pass or decode it, else the 5.1 core |
| DTS core | Original only, after gate G9 (which waits for server issue S-8) | DTS bitstream to a DTS sink |
| TrueHD, DTS-HD MA, DTS:X | Remux, audio converted to AAC: 5.1 (384 kbps) on devices that decode multichannel AAC, stereo elsewhere (section 6.1) | Stereo on most devices; 5.1 only where a Dolby-decoding Ultra re-encodes to Dolby Digital for a Dolby AVR (H9). The client prefers a compatible E-AC-3/AC-3 track in the same language when the file has one; server issue S-1 converts to E-AC-3 5.1 instead |
| Image subtitles (PGS, VobSub) selected | Burn-in transcode | SDR H.264 at up to 1080p; HDR and 4K lost (S-10, S-5) |
| Any source on a 1080p or SDR output | As above within the decoder's limits | 4K SDR is downscaled by the Roku; HDR sources are tone-mapped to SDR H.264 by the server |

### 2.3 What this release does not promise

No native TrueHD, DTS-HD MA, or DTS:X decode or bitstream output; no
multichannel lossless output (stereo FLAC/PCM decode remains a possible, tested
capability); no dual-layer Dolby Vision; no Dolby Vision from MKV direct play
unless hardware evidence contradicts the community reports; no preserved Atmos
objects from a server conversion (E-AC-3 conversion is channel surround only).

## 3. Platform floor, devices, package

- **Roku OS 15.1.0 minimum**, set in the Developer Dashboard's *Minimum firmware*
  field (not a manifest key). Roku OS 16.0 is published for developers and its
  consumer rollout is reported; test on 15.x and 16.x.
- **Manifest:** `rsg_version=1.3`, `requires_mkv=1`, `supports_input_launch=1`,
  `ui_resolutions=fhd`, `mm_icon_focus_fhd`, `mm_icon_focus_hd`,
  `splash_screen_fhd`, `splash_screen_hd`, `splash_screen_sd`, `splash_color`,
  a short `splash_min_time`, and `bs_const` flags. `build_version` is stamped by
  packaging. No `sdk_instant_resume` in the first release.
- **Build variants** from one source: `release`; `perf` (release plus
  `run_as_process=1`, which `chanperf`, Resource Monitor, and Perfetto need, and
  trace points); `dev` (debug logging, diagnostics, test components). M0-2
  measures launch time and memory of `release` against `perf`, and with and
  without `requires_mkv`, on the 512 MB player.
- **Memory monitor:** all five APIs Static Analysis checks
  (`EnableMemoryWarningEvent`, `GetMemoryLimitPercent`,
  `GetChannelAvailableMemory`, `GetChannelMemoryLimit`,
  `roDeviceInfo.EnableLowGeneralMemoryEvent`). The single 80% warning exists since
  Roku OS 10.5; 80/85/90/95% threshold events, up and down, arrive in 15.2. The
  monitor is unsupported on Liberty, Austin, Mustang, and Littlefield devices.
- **Device matrix:**

  | Role | Device | Why |
  | --- | --- | --- |
  | 512 MB current player | Roku Streaming Stick 3840X | Memory floor, 720p UI |
  | 512 MB slow CPU | Roku Express 3930X or 3900X (second-hand) | CPU floor |
  | Non-OpenGL | Roku Express 3710X/3700X or Roku TV 5000X (second-hand); Roku's consumer notes list these on Roku OS 15.3, to confirm on the device | Rendering and memory-monitor fallbacks |
  | Certification reference | Streaming Stick+ 3810X or Premiere+ 3921X (second-hand) | Roku measures 3.2–3.6 on these |
  | 4K player without DV | Streaming Stick Plus 3830X or Express 4K+ | DV gate safety on a DV TV |
  | 4K DV player | Streaming Stick 4K 3820X | Mainstream 4K, DV, HDR10+ |
  | Flagship | Roku Ultra 4850X/4850R | MS12 Atmos decode, Ethernet |
  | Roku TV | a current Roku TV | Internal display, ARC/eARC, no `roHdmiStatus` |
  | Sinks | DV TV, HDR10-only TV, SDR 1080p TV, Atmos AVR or soundbar, DTS sink | Output-dependent claims |

- **Fonts:** Inter Regular, Medium, SemiBold, and Bold (Black falls back to Bold,
  spec section 5.2), static TTFs subset to Latin, Latin Extended, Greek,
  Cyrillic, and Vietnamese, with `fonts/OFL.txt` and `fonts/SOURCE` recording the
  version and subsetting command. `Font` nodes are created once in
  `components/theme/` for the spec's type scale and shared by reference; the
  number of (weight, size) pairs is kept to the spec's scale and its glyph-cache
  cost measured in H17; timecodes use `monospacedDigits`. Milestone 1 tests CJK
  and Arabic titles on the 512 MB device; if a `Label` does not fall back to a
  system font for missing glyphs, catalog metadata uses Roku's system font and
  the chrome keeps Inter (a spec section 5.9 deviation).
- **Package:** PNG artwork compressed, a CI budget of 3.5 MB, the Milestone 1 total
  at most 2.5 MB.

## 4. Architecture

### 4.1 Threads

| Thread | Owns | Never does |
| --- | --- | --- |
| Main (`source/main.bs`) | `roSGScreen` port; `roInput`; `roAppMemoryMonitor`; `roDeviceInfo` events (codec capability, caption mode, low general memory); `roHdmiStatus` on players; the registry snapshot read before the scene starts | UI, HTTP |
| Render (`AppScene` and screens) | Focus, navigation, layout, animation, the `Video` node, the result router, the playback session reducer and progress `Timer` | HTTP, JSON parsing, registry writes, large loops |
| `ApiTask` (one, long-lived) | Every HTTP request and download, the single-flight token refresh, Problem Details decoding, JSON parsing, `ContentNode` building, the capability probe, durable playback jobs, all registry writes | Rendering |
| `MediaTask` (one, long-lived) | CPU-bound work on local files: subtitle conversion and cue shifting in `tmp:/` | Network requests, credentials |

A second HTTP thread would split the single-flight refresh, so all network work
stays in `ApiTask`. If the `perf` build shows launch is parse-bound on the 512 MB
device, one parse worker may take raw bodies and return pruned trees, with
transport and refresh still in `ApiTask`.

### 4.2 Request path

- **Render to `ApiTask`:** requests are set on an `ApiTask` interface field that
  the Task observes with its message port; each set queues one event, so none is
  lost.
- **`ApiTask` to render:** one router in `AppScene`. A requester creates a small
  render-owned `RequestHandle` node, registers it under the request ID, and
  observes the handle's `status` with `observeField(field, "callback")`. `ApiTask`
  posts each result with `roRenderThreadQueue.PostMessage` (Roku OS 15.0+), which
  does not block the Task. The router stores an AA payload with `setRef` (no copy,
  no notification) or a tree in a node field, then sets `status`. Owner teardown
  unregisters its handles from the router. Screens never observe `ApiTask` fields,
  and nothing calls `unobserveField` on a shared field. A field-set fallback, with
  `alwaysNotify`, stays behind a `bs_const` until M0-6 confirms `PostMessage` on
  hardware, including whether a Task-built `ContentNode` tree arrives without later
  rendezvous.
- **Observers:** render-thread code uses `observeField(field, "callback")`;
  `observeFieldScopedEx(field, port)` is used only by the main loop and Tasks;
  `observeFieldScoped` is never used (Roku documents it as broken). Long-lived
  observed nodes (`ApiTask`, the session node) are observed only by `AppScene`.
- **Lanes:** playback, interactive, prefetch. `ApiTask` runs up to four
  concurrent transfers (six on 1 GB+ devices once measured), one of them reserved
  for the playback lane, which a refresh needed by a playback job may also use.
  It services playback events before starting a parse and parses at most one
  large body per loop iteration. Prefetch is dropped first under memory pressure.
- **Ownership and cancellation:** each request carries a request ID and an owner.
  A screen ignores results for request IDs it no longer holds. `AsyncCancel()`
  applies to the interactive and prefetch lanes when the owner goes away; it
  never applies to playback jobs (section 6.6).
- **`roUrlTransfer`:** `SetCertificatesFile("common:/certs/ca-bundle.crt")`,
  `EnableEncodings(true)`, `RetainBodyOnError(true)`, a minimum transfer rate,
  `SetRequest` for DELETE/PUT/PATCH, `SetHeaders` with the full map (never
  `AddHeader` on a reused object), never `InitClientCertificates` (deprecated in
  Roku OS 16). In-flight transfers live in an AA keyed by `GetIdentity()` and are
  matched by `GetSourceIdentity()`; the loop waits until the nearest deadline; a
  cancelled or timed-out request leaves the map without waiting for an event;
  each request ID gets at most one result. Milestone 1 compares
  `SetHttpVersion("http2")` with the default `"AUTO"` on HTTPS origins and records
  the negotiated protocol; `http2` is never forced on `http://` origins.
- **Credential origin (AGENTS.md):** account and profile credentials go only to
  the configured origin, with no automatic HTTPS-to-HTTP downgrade. Because Roku
  follows redirects invisibly (section 2.1), this is enforced by evidence, not by
  a client check: H1 has the header probe answer API and media routes with 302s
  to a second origin and to `http://`, and with absolute child URIs, and records
  whether `Authorization`, `X-Profile-Id`, or `X-Profile-Token` arrive there.
  Gate G1 opens only if none do. If any do, that route stays closed and Milestone
  0a cannot exit until a server-side guarantee exists and is tested (server issue
  S-20: authenticated `/api/v2` and media routes never redirect off-origin, and
  setup refuses an origin that redirects). Server configuration advice alone is
  not enough.
- **Nodes:** `ApiTask` never keeps a node it has handed over; its cache holds raw
  strings or AAs. Card data uses an XML-declared `CardContent extends ContentNode`
  with only the fields cards render, never `addField` per item.

### 4.3 Storage

`Main()` reads a registry snapshot before creating the scene and passes it in.
After that `ApiTask` is the only writer, and it writes and flushes rotated tokens
before releasing requests queued behind a refresh. The registry holds the server
origin, installation ID, tokens, last profile, and profile tokens, within a
budget well under Roku's 32 KB per app, enforced by a unit test. Layout changes
migrate stored sessions (spec section 7.2).

### 4.4 Repository layout

```text
manifest
bsconfig.json, bsconfig.tests.json, bslint.json, .bsfmt.json
source/
  main.bs                      entry, main loop, deep-link args, platform events
  api/                         scheduler, requests, Problem Details, URLs, DTO mapping
  auth/                        session, refresh coordinator, profile and PIN state
  playback/                    probe, gates, v3 serializer, plan mapping, session and seek reducers, recovery
  settings/                    effective preferences for the active profile
  storage/                     versioned registry schema and migrations
  memory/                      tiering and pressure policy
  nav/                         navigation stack reducer
  deeplink/                    deep-link parsing and routing
  util/                        logger, redaction, time formatting, UUIDs
components/
  AppScene.xml/.bs             root state machine, navigation host, result router
  tasks/                       ApiTask, MediaTask
  theme/                       tokens, shared Font nodes
  screens/                     setup, sign-in, profiles, PIN, home, library, search, detail
  player/                      Video wrapper, controls, options, trickplay, skip intro, Up Next
  views/                       cards, rows, grid items, buttons, dialogs, empty/error states
images/ fonts/ locale/
tests/                         Rooibos specs; tests/fixtures/ from silo-server with SOURCE; recorded probe answers
scripts/                       sideload, console, fixtures sync, size, hygiene, sca, headless tests, device checks, header probe
docs/                          spec.md, this plan, hardware-evidence.md
```

Logic lives in `source/` as pure functions over plain data with injected clocks
and transports, so Rooibos tests it headless. Components observe, call module
functions, and set nodes.

### 4.5 Navigation and screen lifecycle

- `AppScene` owns the state machine in spec section 6.2 and one navigation stack
  of `{route, params, focusKey}` entries. At most two pushed screens stay alive
  beneath the top one; older entries are rebuilt from their stack entry with
  focus restored by `jumpToRowItem`/`jumpToItem` (spec section 5.3).
- A hidden screen clears its hero and logo Posters' `uri` and keeps its
  `ContentNode` tree. Under pressure it also sets each list's `content` to
  `invalid`, which destroys the item components and their textures; on show it
  reassigns content and restores focus (target ≤ 300 ms on the 512 MB device).
- **After playback** the detail screen and Home's Continue Watching and Next Up
  rows re-read watch state when the stop job completes or after 3 s, whichever is
  first, so Resume shows immediately after Back (criterion 4.10).

### 4.6 Lists, cards, and images

- Rows: `RowList` with `rowFocusAnimationStyle="fixedFocus"`. Grids: `MarkupGrid`
  (six columns for Browse and Search). No hand-built rows or grids.
- Item components hold a `Poster`, a progress `Rectangle`, and at most one
  `Label`, and observe `focusPercent` only (never `rowFocusPercent`, which fires
  per frame for every item in two rows). `loadWidth`, `loadHeight`, and
  `loadDisplayMode` are set in item XML before any `uri`. On the low tier cards do
  not scale and use the list's native 9-patch `focusBitmapUri` (a spec section
  5.9 deviation); elsewhere the spec's focus scale stays if H17 shows ≥ 30 fps on
  the 512 MB device.
- Rounded corners use a 9-patch frame painted in the background colour; the
  hero's bottom fade reaches full black at the top of the row band so painted
  corners never sit over artwork. `MaskGroup` is not used for anything functional
  (it does not clip on non-OpenGL devices). On Roku OS 16 an `Effect` node, created
  at runtime only when `CreateObject("roSGNode", "Effect")` returns a node whose
  `supported` is true, may replace the frame once H17 shows no frame-rate cost;
  each Poster's `shaderCompatible` is then set at runtime before its `uri` (the
  field does not exist on 15.x).
- **Artwork:** catalog requests pass `poster_width`/`backdrop_width`/`logo_width`
  for the card (the server stores posters at 1000/500/300 and backdrops at
  2560/1920/1280/300 px), and Posters also set load dimensions. Logos are fitted in
  a fixed box. Artwork URLs are signed and expire (default 4 h): responses older
  than the signature window are re-fetched, and a Poster that reports
  `loadStatus="failed"` triggers one refresh. Artwork never carries credentials.
- **Hero:** the backdrop decodes at its displayed rectangle: 1229×756 on FHD and
  819×504 on HD and on the low tier (a spec section 5.9 deviation for low-tier
  sharpness). The cross-fade starts only after the incoming Poster reports
  `loadStatus="ready"`, and the outgoing Poster's `uri` is cleared when the fade
  ends.

### 4.7 Memory policy

- **Tier at launch:** `low` when the UI resolution is HD, when
  `GetGraphicsPlatform()` is not `opengl`, when `EnableMemoryWarningEvent(true)`
  returns false, or when `GetChannelMemoryLimit().maxForegroundMemory` is below a
  threshold set from H17 measurements. Raw values are recorded per device class;
  model names are never used.
- **Pressure, Roku OS 15.2+:** the threshold events, up and down.
- **Pressure, Roku OS 15.1:** trim on the single 80% warning, then poll
  `GetMemoryLimitPercent()` every 2 s to derive the 85/90/95% crossings, and stop
  polling below 75%.
- **Without the monitor:** `generalMemoryLevel` only (`normal`, `low`,
  `critical`), with the low tier's budgets throughout.
- **Responses:** at 80%, drop prefetch and shrink grid retention; at 85% or `low`,
  detach hidden screens' list content; at 90–95% or `critical`, also drop cached
  responses and non-visible screens. Restore gradually below 75%.
- **Before playback:** release browse textures behind the player.
- **Identity changes** (account, profile, server) drop every image, cached
  response, and retained page (spec sections 8.4 and 11).

### 4.8 Data budgets

| Item | Budget |
| --- | --- |
| Home and library rows | at most 20 rows and 40 items per row loaded; section items loaded lazily two rows ahead of the viewport; rows more than five away from focus drop their items and keep their cursor |
| Browse and Search grids | at most 10 pages (400 items) retained, oldest dropped first; at most 10 cursor checkpoints kept so a dropped page is re-fetched |
| Response body | 2 MB per request; larger bodies fail as a client error |
| Raw response cache | 1 MB in total, least recently used first |
| Focus restoration | waits at most 5 s for a page that has not loaded, then falls back per spec section 5.3 |
| Subtitles | the current track only: 2 MB and 20,000 cues at most, deleted on stop; counted in the memory budget |
| Playback jobs | per session at most one uncertain in-flight progress sample, the latest unsent sample, and the final stop (section 6.6) |
| Trickplay sheets | section 6.9 |

M0-10 checks these on the 512 MB device with a representative workload: a real
`RowList` and `MarkupGrid` with production-sized artwork and fonts, a hero change,
several paginated traversals of a long synthetic catalog, and player startup after
browse. The exit requires the section 1 memory and texture limits, not just the
object counts. The checks repeat at each milestone exit.

### 4.9 Accessibility, captions, logging, copy

- Item `ContentNode`s carry `AUDIO_GUIDE_TEXT`; custom focusables set
  `audioGuideText`; custom controls speak through `roAudioGuide`.
- Captions follow Roku's global caption mode, and Silo writes it whenever Silo's
  UI turns captions on or off (section 6.10).
- One logger in `source/util/` redacts tokens, PINs, device-login codes, query
  strings, and media URLs; debug logging is compiled out of `release` with
  `#if debug`. Never log `segUrl`/`streamUrl`.
- English is the first UI language. All user-facing copy, including
  recoverable, offline, authorization, server, and playback errors, lives in
  `locale/` from the first screen.

## 5. Server contract layer

- DTOs follow `contracts/api/v2/openapi.json` in silo-server, not
  `docs/design/schemas/playback-v3/`, which describes the v1 body. Playback objects
  reject unknown members with `422`. The serializer emits every required member;
  optional members change planning and are sent only on purpose: `hdr_details`
  only on `original_http` (to remove Dolby Vision); `failure_reason` only on a
  disabled class; delivery `max_channels` only in the interim AAC case in section
  6.1; `output.audio_passthrough` never (the planner reads it only for exact-tier
  passthrough claims, and probe results stay in local diagnostics). `file_id` is a
  string; `metered` is omitted (deprecated).
- **Validation the server enforces:** `installation_id` is the canonical lowercase
  UUID from capabilities; `profile_id` equals the `X-Profile-Id` header;
  `playback_attempt_id` matches `^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$`;
  `replan_request_id` is 8–128 characters; event and stop IDs are lowercase UUIDs.
- **Identities and idempotent bodies:** `playback_attempt_id` (start),
  `replan_request_id` (minted per replan, reused on every retry of it), and
  `stop_id` (stop). There is no `Idempotency-Key` header. The bodies are stored as
  strings with their identity and replayed verbatim; they are never re-serialized
  (`FormatJson` output is not guaranteed stable). Every replan, whatever its
  operation, carries `failed_plan_id` equal to the current plan's ID.
- **Problem Details:** the client maps errors by the last path segment of the
  Problem `type`; v2 Problems have no top-level `code`.

  | Type | Client action |
  | --- | --- |
  | `invalid_token`, `token_refresh_required` | Refresh once and retry once (authenticated requests only) |
  | `session_expired` | Sign out after a refused refresh |
  | `profile_verification_required` | Ask for the PIN again |
  | `not_found` | Per the session rules below, or a normal not-found state |
  | `playback_session_ended` | Exit the player |
  | `installation_changed` | Re-read capabilities, then start a new attempt |
  | `conflict` | On a replan: a newer plan won (`stale_playback_plan`), the replan ID was reused with a different body, or an identical replan is still running (`replan_in_progress`, after retrying an uncertain response). Retry the stored body once after 2 s; if it is still `conflict`, start a new attempt |
  | `progress_conflict` | A sequence reused with a different payload, a client bug: log it and continue with a higher sequence |
  | `idempotency_conflict` | A reused attempt ID with a different body, a client bug: start a new attempt |
  | `validation_failed` | Generic error; recorded in diagnostics without bodies |
  | `internal_error`, `rate_limited` | Keep tokens; retry progress, replan, and route events with bounded backoff (a plan-store outage answers `internal_error`); elsewhere a generic error |
  | `authentication_required` | As `invalid_token` |
  | `permission_denied`, `capability_not_configured` | Generic error recorded in diagnostics |
  | `dependency_unavailable`, `provider_unavailable` | Keep tokens; wait for `Retry-After` when present, otherwise a bounded backoff (playback problems, including `replan_capacity_exhausted`, carry none); retry |

- **Headers** per spec section 7.4. `X-Profile-Id` and `X-Profile-Token` go
  together; an id without its token on a PIN-locked profile gets `403`
  `profile_verification_required`.
- **Fixtures** are copied from `contracts/api/v2/fixtures/` by
  `scripts/sync-fixtures.sh` at a pinned server commit recorded in
  `tests/fixtures/SOURCE`. The server has no HLS-remux or transcode plan fixture
  yet (S-14); until it does, the client keeps planner outputs recorded from a dev
  server, labelled as such.
- **Corrections to the spec found against the server:**
  - `POST /auth/login` answers a wrong password with `401 invalid_token`; the
    refresh coordinator applies only to authenticated requests, never to login;
  - `GET /playback/capabilities` requires `X-Profile-Id` and returns a strong ETag;
  - only `GET /catalog/items/{id}` carries `play_season_number`; season list items
    do not;
  - section-items routes return one bounded section; paging a section uses
    `/catalog?source=section&scope=home|library&section_id=…` with `limit` ≤ 200
    and `cursor`;
  - progress and stop send `position`; replan sends `position_seconds`; all are
    source positions (section 6.5);
  - `404` (`not_found`) on progress, replan, or media for the current session
    means it ended (expiry, a server-side stop, a restart without Redis): start a
    new attempt at the current position if the viewer is still watching (Android
    counts a progress `404` as a failed post instead; this is a Roku deviation). A
    progress `404` after the client's own stop is ignored. `410
    playback_session_ended` and `409 installation_changed` as in the table above.

## 6. Playback

### 6.1 Capability probe

`source/playback/probe.bs` is pure and takes a `roDeviceInfo` facade, so it is
tested against recorded probe answers per device class. `ApiTask` runs it.

**Video** (`video_evidence: "exact"`): probe a fixed ladder and report only
shapes that answered yes, in ffprobe vocabulary, keeping every measured bound.

| Probe | Reported entry |
| --- | --- |
| `{codec: "mpeg4 avc", profile: "high", level: "4.2"}`, then 4.1, then `main` | `h264`, `profiles` up to the highest passing (`constrained baseline`, `main`, `high`), `levels: [42]` or `[41]`, `bit_depths: [8]`, 1920×1080, 60 fps at 4.2 or 30 at 4.1 |
| `{codec: "hevc", profile: "main 10"}` at levels `6.2`, `6.1`, `6.0`, `5.2`, then the documented `5.1`, `5.0`, `4.1`; and `profile: "main"` | `hevc`, `profiles: ["main", "main 10"]`, `bit_depths: [8, 10]`, `levels` from the highest passing (×30: 6.2 → 186, 6.1 → 183, 6.0 → 180, 5.2 → 156, 5.1 → 153), size and frame rate from that level, capped at 3840×2160 |
| `vp9` profiles 0 and 2 | Only under gate G11 |
| `av1`, probed bare (*community*: a combined probe always fails) | Only under gate G10 |

- HEVC `levels` stay in the report, because removing the bound would also remove
  the server's level check on originals. The cost: a source above the reported
  level loses direct play and HDR (an SDR H.264 transcode at up to 1080p), and the
  server transcodes to H.264 rather than HEVC for this client until server issue
  S-5 pins its HEVC output level. The undocumented level strings above 5.1 count
  only after H4 shows a device that answers yes also plays such a source.
- Size is bounded by the decoder, not the output mode: on a 1080p output the Roku
  downscales a 4K SDR original, which beats a server transcode.
- `max_bitrate_kbps` is omitted until hardware testing gives a number.
- A probe that cannot run removes that codec or shape; it never relaxes bounds
  already measured. If the ladder as a whole cannot run, the report falls back to
  `platform_attested`, which still enforces bit depth and size.

**Audio** (`audio_evidence: "platform_attested"`). Roku cannot enumerate sink
channel layouts, so it never earns a passthrough claim and does not need one: a
codec in `codecs_audio` is copied as the original bitstream.

- Always `aac` and `mp3`. `CanDecodeAudio({codec: "aac", ChCnt: 6})` decides the
  AAC channel case. Interim policy until server issue S-13 adds a per-codec
  channel ceiling, on a device that answers no:
  - Each start, and each replan that carries `client_playback_context`
    (`failure_recovery`, `track_change`, `quality_change`, `output_change`), sets
    `max_channels` from the track that request selects; a ceiling left over from
    an earlier track would convert copied E-AC-3 and AC-3 to stereo AAC.
  - When the selected track has more than two channels and its codec is not in
    `codecs_audio`, the `hls` delivery carries `max_channels: 2`, so the server
    converts to stereo AAC. When it is multichannel AAC, `original_http` carries
    it too, so the server remuxes with stereo AAC instead of offering an original
    the device cannot decode.
  - Otherwise `max_channels` is omitted, so originals and HLS copy remuxes keep
    E-AC-3 and AC-3 channels. A video transcode still encodes every track to AAC,
    5.1 for a 5.1 source. When a returned plan's `effective_recipe` has
    `audio_codec: "aac"` with more than two channels, the client does not open
    it: it stops that session and starts a new attempt with `hls.max_channels: 2`.
    (`failure_recovery` cannot do this, because plan attempt keys ignore the
    channel count, so the stereo variant counts as already failed.) The restart
    costs one extra round trip on these devices until S-13 lands.
  - If H9 shows these devices downmix multichannel AAC after all, the interim
    policy is dropped.
- `ac3`, `eac3` when `CanDecodeAudio` answers yes for the current output with
  `PassThru` unset, probed with `Container: "mkv"` and `"mp4"`. `PassThru: 0`,
  `PassThru: 1`, and `Atmos: 1` are recorded for local diagnostics only.
- `dts` only under gate G9, which requires server issue S-8 (variant-aware DTS
  matching with a channel ceiling): the server today calls DTS-HD MA and DTS:X
  `dts` too.
- `flac`, `opus`, and the tested ffprobe PCM names (for example `pcm_s16le`,
  `pcm_s24le`; a bare `pcm` never matches a source) only under gate G12.
- Never `truehd`, `mlp`, or any DTS-HD variant, whatever the probe says.
- `audio_passthrough_codecs` stays empty on every delivery.

**Output** (`output.hdr_details`, mirrored in `output.display.hdr_types`):

- The output context is built from a **normalized mode** sampled outside
  playback: the resolution class from `GetVideoMode()` (lines ≥ 2160, which
  includes 8K Roku TVs) plus the display's HDR and DV flags, ignoring the refresh
  rate and the current `b10`/`Dv` suffix. `output_context_id` is derived from that
  normalized mode and the audio probe results, so playback's own mode switches
  never change it.
- HDR10, HLG, and HDR10+ (gate G4) come from `GetDisplayProperties()` only when an
  HEVC Main 10 entry exists and the normalized resolution is ≥ 2160 lines. If H5
  shows a 4K SDR Display Type does not output HDR, the rule tightens to a mode with
  `b10`/`Dv` or an Auto Display Type.
- Dolby Vision profiles only under gate G5, whose predicate also requires evidence
  that the Roku itself outputs DV (section 6.2). P5 and P8 are reported with
  `dolby_vision_profile_levels`: a `max_level` from H3 evidence for each, and
  `bl_compatibility_ids: [1]` for P8. IDs 4 and 2 are added once H3 passes them,
  using a `dev`-build override that sends `[1, 4]` and `[1, 2]`.
- `output.display.hdr_evidence` is `"exact"` when `GetDisplayProperties()`
  answers; the probe retries once before reporting `"unknown"`, because `unknown`
  turns every HDR and DV source into an SDR transcode.

**Deliveries:**

| Class | Contents |
| --- | --- |
| `original_http` | `containers: ["mp4", "mkv"]`; the video and audio codecs above; `hdr_details` without Dolby Vision (gate G6 stays off); `validated_claims: ["client_dv8_base_layer_fallback_v1"]` only under gate G7 **and** only when the output reports no DV profile 8 (on a DV output the claim makes the server choose the base layer over the DV remux); `max_channels` only in the interim AAC case |
| `hls` | `containers: ["hls"]`; `h264`, `hevc`; `aac`, `ac3`, `eac3`; `features: ["native_hls_playback_v1"]` so DV copies are labelled `dvh1`; no `hdr_details` (Dolby Vision reaches `hls` through `output.hdr_details`); `max_channels` only in the interim AAC case |
| `progressive` | disabled, `failure_reason: "disabled_pending_seekable_transport"` |

**Never claimed:** `client_managed_dynamic_range_v1`, `client_selected_audio_track_v1`
(until a hardware test shows Roku selects the same track the server named),
passthrough, client transformations.

**Client features:** `seek_reanchor_v1`, `direct_stream_resume_v1`, and under
gate G13 `subrip_sidecar_v1` and `hls_subtitle_renditions_v1`. Not
`header_authenticated_media_v1` or `authorized_media_origins_v1`: the client
uses signed-URL media mode so plans can use proxy nodes (decision D-1, section
6.4). Never `plan_invalidated_v1` (it needs the realtime socket; when the server's
asynchronous copy-safety check rejects a playing copy route it stops the session,
and the resulting media error or `404` starts a new attempt).

Appendix A has a complete example payload.

### 6.2 Hardware gates

A gate turns a claim on once its tests pass on the device cohorts it lists.
Gates live in one table in `source/playback/gates.bs`; each records its runtime
predicate, the test IDs, the cohorts covered, and the evidence entry in
`docs/hardware-evidence.md`. A device outside the tested cohorts keeps optional
claims off. A gate that is on still sends a claim only when its predicate holds.
A qualification run can end with a claim deliberately off; that completes the
gate. Only G1, G13, and G14 are required paths: when they fail, a fix must land.

| Gate | Claim | Runtime predicate | Before evidence | Tests and preconditions |
| --- | --- | --- | --- | --- |
| G1 | Signed-URL media playback at all, on the API origin and on proxy origins | — | Development only | H1, including zero credential forwarding off-origin (section 4.2), and H2 (`#EXT-X-DEFINE` playlists) |
| G2 | HEVC Main 10 4K on `original_http` (MKV, MP4) | HEVC ladder passes | On within tested cohorts (documented) | H4 before beta |
| G3 | HDR10 and HLG | Section 6.1 output rule | On within tested cohorts (documented) | H5 before beta |
| G4 | HDR10+ | Display reports HDR10+ | Off | H5 |
| G5 | Dolby Vision P5 and P8 via `hls`, P8 with `bl_compatibility_ids: [1]` (4 and 2 after H3) | Display reports DV **and** the Roku is shown to output DV: `GetVideoMode()` carries `Dv` outside playback, or, if H3 shows the mode string carries it only during playback, this device's model has an H3 pass recorded (a model-keyed evidence entry combined with the live display flag, never the model name alone) | Off | H3, H19; S-4 or S-15 if H3 or H19 fail |
| G6 | Dolby Vision on `original_http` | — | Off; expected to stay off | H3 |
| G7 | `client_dv8_base_layer_fallback_v1` | Output reports no DV profile 8 | Off | H3 for base-layer IDs 1, 4, and 2 (HDR10, HLG, SDR), or a narrower server contract (S-19) |
| G8 | E-AC-3 JOC copied | `eac3` probe passes | On within tested cohorts (documented on some models) | H9 |
| G9 | `dts` on `original_http` | `CanDecodeAudio({codec: "dts", PassThru: 1, ChCnt: 6})` | Off | S-8, then H10 and H11 |
| G10 | `av1` on `original_http` | Bare probe passes | Off | H6 |
| G11 | `vp9` on `original_http` | Probe passes | Off | H7 |
| G12 | `flac`, `opus`, tested `pcm_*` names | Probe passes | Off | H12 |
| G13 | `sidecar_text: true` and the subtitle features | — | Development only | H14 thresholds (section 6.8) before Milestone 0a exits |
| G14 | Copy remux to `hls` | — | Development only | H19 and the H8 envelope before Milestone 0a exits |

### 6.3 Start path

- Capabilities are read when a detail screen opens (`If-None-Match`) and cached per
  installation; effective settings are read at profile selection.
- `ApiTask` refreshes the access token proactively when expiry is under 30
  minutes, from its own clock; the start path waits for a refresh only when the
  token has already expired. Headers cannot change on a playing stream.
- On Play the render thread sends only the intent. `ApiTask` runs the audio probe,
  reuses the cached video ladder for the current `output_context_id`, builds and
  stores the body, and posts start. The `perf` build logs each step's time; the
  Milestone 0a exit records them on the 512 MB and reference devices.
- **Resume and Start Over:** the server applies no rewind to its stored position,
  so Resume sends `start_position` = the watch state's position minus
  `player.resume_rewind_seconds` (default 7 s, spec section 5.7), never below 0;
  Start Over sends `start_position: 0`; a deep link with a position sends it. For
  a multipart item, whose parts share one resume point, Resume omits
  `start_position` and the server's own rule applies.
- **Audio track:** the client picks the initial track from the watch projection
  (spec section 8.5). When the server's default would be converted, or is
  multichannel AAC on a device without multichannel AAC, and the file also
  carries an E-AC-3 or AC-3 track in the chosen language, the client sends
  that track's `audio_track_id` and `audio_track_index`, so the server copies it
  on a remux (the original delivery would need `client_selected_audio_track_v1`).
- A fresh `playback_attempt_id` per user action; the stored body is replayed
  verbatim only after an uncertain response.

### 6.4 Plan execution and media authentication

- **Signed-URL media mode (decision D-1).** The client sends neither
  `header_authenticated_media_v1` nor `authorized_media_origins_v1`, so the server
  may route media through proxy nodes. A plan's media URL is then one of two
  kinds (spec section 9.4):
  - **on the configured origin**, carrying the signed `st` transport token, which
    lets the server rebuild the session after an API restart but does not
    authenticate: these requests carry `Authorization` and the profile headers;
  - **on a proxy origin**, with a signed token in the path, which is the
    credential: these requests carry no account or profile headers
    (`authorized_media_origins_v1` would send `Authorization` to the proxy, which
    AGENTS.md forbids).
  Subtitle artifacts stay on the API origin in both cases and need the headers,
  so for proxy-served plans they use the download transport in section 6.8.
  Signed HLS playlists put the `st` query on every segment URI, and long ones are
  compacted with `#EXT-X-DEFINE` variable substitution (HLS version 8); whether
  Roku parses that is test H2, a Milestone 0a gate, with server issue S-21 if it
  fails.
- **One `Video` node per player session**, with `enableUI=false`,
  `asyncStopSemantics=true`, and its own `roHttpAgent` (`setHttpAgent`) created
  before any content is set, so headers never reach the global agent that Posters
  share. A new attempt sets `control="stop"`, waits for `state="stopped"`,
  increments the attempt token, assigns new content, and plays; every observer
  callback checks the attempt token. From `error`, the same node takes the new
  content directly. If the node is still `stopping` after 3 s, the player waits
  up to a second deadline of 10 s and then shows the playback error with Retry. A
  second `Video` node is never created while one is `stopping`. Milestone 0a
  records stop-to-first-frame and how often the first deadline is hit.
- **ContentNode:** `url` resolved against the configured origin; `StreamFormat`
  from `plan.stream.protocol` and `plan.stream.container` (`hls`, `mkv`, `mp4`),
  never from the URL; `HttpHeaders` (`Authorization`, `X-Profile-Id`,
  `X-Profile-Token`) only when the URL's origin equals the configured origin;
  `PlayStart` set to `plan.timeline.player_start_seconds` (Roku OS 15.1 starts at
  the manifest start otherwise); subtitle tracks per section 6.8; Audio Guide
  metadata. Nothing sets `HttpHeaders`, cookies, or certificate attributes on a
  node without its own agent.
- **Focus:** while Silo's controls are hidden the `Video` node keeps focus, so `*`
  goes straight to Roku's overlay (section 6.10); the player's `onKeyEvent`
  handles the other keys.
- **Mid-playback `401`:** refresh, then reopen through the rules in section 6.5.

### 6.5 Timeline and seeking

A pure reducer in `source/playback/seek.bs` owns position conversion and seek
decisions, following protocol section 5 and each returned plan's `timeline`:

- **Positions:** source position = player position + `timeline_offset_seconds`.
  Progress, stop, and replan always send source positions. Runtime comes from
  `source.duration_seconds` (or the catalog runtime when the server lacks
  `plan_source_duration_v1`), never from a growing HLS playlist's duration.
- **Local seek:** when `can_seek_anywhere` is true, or both
  `seek_window_start_seconds` and `seek_window_end_seconds` are present and the
  target lies inside them, the player seeks locally to the source target minus
  the current `timeline_offset_seconds`. Originals and complete transcodes
  usually qualify; the reducer follows the returned timeline rather than the
  delivery type.
- **Reanchor:** otherwise, which is always the case on copy remuxes (their window
  end is absent), the client sends a `seek_reanchor` replan with the target as
  `position_seconds`, keeping the current track and quality intent; adopts the
  returned plan and identity; plays it from `player_start_seconds`; applies the new
  `timeline_offset_seconds`; and re-fetches or re-shifts the subtitle sidecar.
  Rapid skips merge before the replan (spec section 5.7's 200 ms rule).
- **Reopen on a copy remux** at an advanced position is a reanchor too: the client
  adopts the returned plan rather than replaying the old one.
- **Reanchor failure** takes the `seek_failure_recovery` path (section 6.7).
- Milestone 0a proves forward and backward seeks, resume at a non-zero keyframe,
  and a token-expiry reopen on a copy remux.

### 6.6 Session lifecycle

- **Capabilities** (`GET /api/v2/playback/capabilities`): requires
  `state: "available"`, `allowed: true`, protocol 3, and `sequenced_progress_v1`;
  stores `installation_id`. Without `output_display_evidence_v1` the client
  reports SDR only; without `plan_source_duration_v1` it uses the catalog runtime.
- **Durable obligations:** the player component owns only the in-memory reducer
  for the active attempt (`state, event → state, commands[]`). The final progress
  sample, the stop with its `stop_id`, and any sample whose post had an uncertain
  result are handed to `ApiTask` as playback jobs keyed by `session_id` and fenced
  by server, account, profile, attempt, and session, within the section 4.8 bound.
  They are retried with backoff (1, 2, 4, 8, 16, then every 30 s) after the player
  is destroyed, and owner teardown never cancels them. A progress job expires
  after 10 minutes; a stop job retries for up to 30 minutes. An identity change
  first lets the previous identity's jobs finish or expire with a recorded reason;
  they are never sent with new credentials.
- **Uncertain start or replan:** replayed verbatim with the same identifiers until
  certain. A session accepted after the viewer has left (Back during start) is
  stopped. A newer user intent waits for an in-flight mutation to settle, then
  supersedes it.
- **Progress:** every 10 s while playing or paused, from a render-thread `Timer`
  that samples `Video.position` and enqueues the sample. A sample whose post was
  uncertain is resent byte-identically under its sequence; newer positions take a
  new, higher sequence; a sequence is never reused with a different payload.
  After three failed posts the player shows "Playback progress is pending…", as
  Android TV does.
- **Stop:** `DELETE /api/v2/playback/{session_id}` with `stop_id` minted once and
  reused on every retry, plus the final `sequence` and `position`.
- **Home during playback** ends the app without a stop; the server reaps the
  session after 45–60 s if it was playing, or 30 minutes if it was paused.
- **Route events:** each with a fresh UUID `event_id`; never retried; a `429`
  drops it; `diagnostics.first_frame_ms` on `first_frame`, omitted for autoplay
  starts.
- **Output changes:** during playback the client re-probes on capability events
  and sends an `output_change` replan with a new `output_context_id` only when the
  normalized output context changes (a different display, HDR/DV capability, or
  audio probe result), and only when the server advertises `output_change_v1`.
  Mode switches caused by playback itself never trigger one.
- **Acceptance scenarios** (M0-10 and Milestone 3): Back during start; profile or server
  change during a replan and during a pending stop; rapid Up Next autoplay; a long
  network outage during playback.

### 6.7 Recovery and adaptation

| Situation | Action |
| --- | --- |
| Network error or stall | One reopen per plan at the current position, recorded as the `transport_reopen` local mutation on a later replan. On a copy remux the reopen is a reanchor (section 6.5) |
| No progress for 20 s at startup or mid-stream | `transport_stall`; `decoder_no_output` when the decoder had input but rendered nothing |
| Reopen failed, or a decoder or format error | `failure_recovery` |
| Seek or reanchor fails | `seek_failure_recovery` |
| HLS subtitle rendition never becomes selectable | `failure_recovery` with `subtitle_hls_rendition_failed`; the server uses a sidecar for the rest of the attempt |
| Unsupported audio reported (`audioFormat = "mat"`) | `failure_recovery`; the codec stays refused |
| User changes track or quality, or the output changes | `track_change`, `quality_change`, or `output_change` with empty `attempted_plan_keys` and `attempt_count: 1`; any returned key is accepted, including one seen before |
| `terminal` reply, including `adaptation_exhausted` | Full-screen error with Retry |

- **Failure chain:** `failure_recovery` and `seek_failure_recovery` carry the
  failed plan's `failed_plan_id`, `plan_attempt_id`, and `plan_attempt_key`, the
  chain's `attempted_plan_keys` (each key added after its plan failed; the server
  rejects more than 16), and a client-incremented `attempt_count` (1–8; at 8 show
  the terminal error). `failure` with a `classification` is required on these two
  operations and must be absent on intent replans. The server may return a key
  already in the failed list: when the failed plan's transcode node stopped
  answering, or a proxy origin refused the source (`sourceRefused`), it runs the
  same recipe again elsewhere, so the client accepts the key and `attempt_count`
  bounds the chain. Seek replans are built from the server's stored request and
  ignore the body's capabilities and context, so they cannot carry a
  `max_channels` change. The chain starts empty with a plan that has played past
  its first frame, and every intent replan starts a new chain. Reducer cases cover Auto → explicit quality →
  Auto and an output change that returns the same key.
- **Auto quality:** a transcode is a single rendition the player cannot step
  down on its own. With Auto selected, the client keeps a bounded stall history
  that separates outages and seeks from bandwidth shortage; after sustained
  buffering it sends a `quality_change` replan with a measured, lower
  `bandwidth_estimate_kbps`, with hysteresis before stepping again. An explicit
  quality choice is never overridden. The reducer is tested with injected stall
  histories in Milestone 0a; H18 tests it on hardware.
- One recovery runs at a time; a newer user intent replaces a queued one.

### 6.8 Subtitles

With `sidecar_text: false` (the spec's current default), selecting an external
SRT is a terminal error and selecting an embedded text track forces an SDR
burn-in transcode, so subtitles are a Milestone 0a gate (G13).

- **Request:** `subtitle_fidelity_preference: "compatible"`; `sidecar_text: true`
  on every enabled delivery; `ass_styling`, `font_attachments`, `embedded_bitmap`
  false; `subrip_sidecar_v1` and `hls_subtitle_renditions_v1`.
- **What arrives:** original SRT for external and downloaded SRT tracks; a WebVTT
  rendition inside the HLS stream for embedded text on a transcode (already
  `DEFAULT=YES`, no `LANGUAGE`); WebVTT sidecars for embedded text on originals
  and remuxes; **raw `.ass`** for ASS/SSA tracks; burn-in for PGS and VobSub. All
  sidecars carry absolute source timestamps.
- **Timing:** for `.vtt`, the client requests the protocol's
  `timestamp_offset=-{timeline_offset_seconds}` (the negative of the video timeline
  offset), and the server shifts and clips the cues. Original `.srt` and raw `.ass`
  cannot use the parameter, so `MediaTask` shifts their cues itself, dropping cues
  that end before the new origin and clipping overlapping ones at zero. Every
  reanchor re-applies the offset.
- **Transport, chosen by H14 in this order:**
  1. a native `SubtitleTracks` URL to the server artifact, if H1 shows the headers
     reach subtitle requests (only for plans whose media is on the configured
     origin: on a proxy-served plan the `Video` node carries no account headers,
     so its API-origin subtitles always use transport 2);
  2. a local file: `ApiTask` downloads the artifact with `AsyncGetToFile` into a
     bounded `tmp:/` directory under the normal headers and refresh; `MediaTask`
     shifts cues where needed and converts VTT and ASS to SRT (dropping styling);
     the `Video` node gets the local path, if H14 shows Roku accepts `tmp:/`
     tracks;
  3. app-rendered captions. This forfeits Roku's caption styles and caption-mode
     behaviour, so it is a product and certification decision (section 13), not an
     automatic fallback.
- **Success criteria for H14 and G13:** a selected external or sidecar track is
  visible within 5 s of playback start or of selection; the download has a 10 s
  deadline and can be cancelled; files above the section 4.8 bound are refused
  with a message. Embedded text on an original or remux must be visible within
  15 s on the H14 reference file (a large 4K MKV on network storage, resumed at
  75%). The player starts without it, shows "Loading subtitles…", and cancels the
  wait when the viewer changes track. If the 15 s target fails, server issue S-18
  becomes a prerequisite for embedded text on those deliveries, and until it lands
  such tracks are offered only where they meet the target.
- ASS tracks are hidden if conversion fails, until server issue S-12 converts them
  server-side.

### 6.9 Trickplay thumbnails

Criterion 4.7 requires thumbnails while seeking VOD longer than 15 minutes, so
trickplay is in the first release. Thumbnails show for Left/Right scrubbing and
for every rate-ladder speed.

- **Source:** `GET /api/v2/watch/{item_id}/trickplay?file_id={file id}`, requested
  only when that file version's `trickplay_available` (from
  `GET /api/v2/watch/{item_id}`) is true and capabilities list `trickplay_v1`. The
  manifest gives `interval_ms`, `thumbnail_width`, `thumbnail_height`,
  `tile_columns`, `tile_rows`, `thumbnail_count`, `sheets[{index, url}]`, and
  `expires_at`. Sheets default to 10×8 tiles of 300 px (3000 px wide, never over
  3200).
- **Sheet URLs are signed** and need no headers: a Poster loads them, and they are
  never given credentials. The manifest is re-fetched after `expires_at`, after a
  sheet reports `loadStatus="failed"`, or when a replan changes the file.
- **Rendering:** one `Poster` inside a `Group` with `clippingRect`, translated to
  the tile. `loadDisplayMode="limitSize"` with `loadWidth` at most 1600 px and the
  matching `loadHeight` is set before `uri`, so a 300 px tile decodes at about
  160 px and is shown at 240 px wide on FHD; tile maths uses the decoded scale.
  Retention: the current sheet on the low tier, the current and next sheet
  elsewhere; sheets are dropped when the scrubber hides.
- **Missing or failed sheets:** when a file has no published sheets (generation off,
  pending, unusable, deleted, or the manifest or sheet fails to load), the scrubber
  shows time only and tells the viewer that previews are not available for this
  title. The server provides trickplay (decision D-5), so this is an edge case;
  Roku is still asked about it, but public release does not wait for the answer.
- **Unproven:** whether every supported device decodes a 3000 px sheet, and its
  decode time and texture cost (H20). If H20 fails, server issue S-16 asks for a
  narrower sheet variant.

### 6.10 Player controls and certification

The spec's player (section 5.7) stands, with these Roku changes:

- **`*` with controls hidden** reaches Roku's caption and audio overlay because the
  `Video` node keeps focus (criterion 4.4). `*` opens Silo's Options only while
  Silo's controls are shown. Track changes made in Roku's overlay are observed
  (`audioTrack`, `subtitleTrack`) and turned into a `track_change` replan or
  reverted, because the plan owns track identity (H15).
- **Captions:** Silo's Options offers Off, On, On replay, and On mute (Roku TVs
  only), written to `Video.globalCaptionMode` as `"Off"`, `"On"`,
  `"Instant replay"`, and `"When mute"` (criterion 4.8). Every on/off change in
  Silo's UI writes it; choosing a subtitle track sets On and sets `subtitleTrack`;
  caption-mode changes made in Roku's overlay are observed.
- **Replay** rewinds by the profile's skip-back value clamped to 10–25 s
  (criterion 4.9). In "Instant replay" caption mode it forces captions on for the
  replayed span and restores the previous mode afterwards; repeated presses extend
  the span. Left/Right keep the unclamped profile values.
- **Up Next** autoplay honours `roDeviceInfo.IsAutoplayEnabled()`.

### 6.11 Diagnostics

The Stats tab shows the non-secret plan (delivery, decision reason, effective
recipe, warnings), `Video.videoFormat`, `audioFormat`, the `streamingSegment` HDR
mode on HLS, the recorded audio probe results, and `IsPassthruCodecActive()`.
These do not prove DV or Atmos: `videoFormat` has no DV value, `audioFormat` has
no JOC flag, and `streamingSegment` is meaningless for originals. H3 and H9 also
record the TV's and AVR's info panels.

## 7. Launch, deep links, certification

- **Beacons:** `AppDialogInitiate`/`AppDialogComplete` around server entry,
  sign-in, profile picker, PIN, and any pre-Home error dialog the user must
  dismiss. `AppLaunchComplete` once per launch, when Home is fully rendered: the
  hero and the visible rows have content and their artwork has loaded or failed.
  For a deep link, once playback has started and accepts remote keys. The port
  8085 beacon report is the primary measurement.
- **Deep links** (criteria 5.1, 5.2): `Main(args)` and `roInput` events with
  `contentId` and `mediaType`. Profile rule, from Roku's deep-linking page ("set
  the last one used as the default … Do not use any profiles linked to children
  as the default"): use the most recently used profile on this device whose
  `is_child` is false, else the account's first non-child profile, and play. A
  server-required PIN is never bypassed. Until Roku confirms that a PIN prompt
  counts as authentication, the rule skips PIN-locked profiles; if that leaves no
  usable non-child profile that can see the content, the app opens Home. (Section
  13 lists this as a decision.)

  | App state when `roInput` arrives | Action |
  | --- | --- |
  | No session (setup, sign-in) | Store the link; continue it after sign-in |
  | Profile picker or PIN at launch | Apply the profile rule and play; leave the picker |
  | Keyboard or dialog open | Close it, then handle the link |
  | Browse screens | Push the player above the current stack |
  | Player or Up Next | Hand the stop and final progress to `ApiTask`, then start the new item |
  | Invalid or inaccessible | Stay on the current screen if running; Home on launch |

- **Keyboards:** `DynamicKeyboard` for server URL, username, password, and search;
  `DynamicPinPad` for PINs.
- **Back:** journeys assert Back from Home's tab bar exits to the Roku home screen
  (criterion 4.6). The app never sets `disableScreenSaver` outside the `Video`
  node's own handling (4.5).
- **Splash and store art** keep a black level of at least 16 and no transparency
  (criterion 6.4; Roku publishes no numeric range, so this follows the community
  lint heuristic); `splash_color=#161616`.
- **Criterion 4.3 (Roku Event Dispatcher):** if Roku says it applies, the app adds
  `sg_component_libs_required=roku_analytics` and fires `Roku_Authenticated` on
  each authenticated launch, and M1-8 measures the library's launch-time cost.
- **Questions for Roku**, added to spec section 10.2 and sent in Milestone 0a:
  whether 4.3 applies to a free app with self-hosted sign-in; whether the
  `getUserData` and Customer Account Requirement Static Analysis rules apply;
  whether 4.7 is met when thumbnails depend on the user's server generating them;
  whether a PIN prompt on a deep link counts as authentication; whether opening
  Home is acceptable when only child or PIN-locked profiles remain.
- **Static Analysis** runs in CI from the start. The dashboard version runs on the
  first beta upload (Milestone 0a) to expose authentication-category rules local
  `sca-cmd` does not run.
- **Review:** a public reviewer server with one PIN-free profile, seeded movie,
  series, and episode, trickplay enabled, and test credentials with a "Valid
  until" date. App Behavior Analysis needs sign-in and sign-out scripts recorded
  in Roku's remote tool that type the server URL, and a public app record; it runs
  at the Milestone 2 and 3 exits against an unpublished record.

## 8. Tooling, CI, and tests

| Tool | Version | Use |
| --- | --- | --- |
| BrighterScript (`bsc`) | 0.73.7, exact | Build and diagnostics; v1 is still alpha |
| `@rokucommunity/bslint` | 0.8.47, exact | `no-print: error` (the logger excepted), `no-array-component-field-type: error`; `no-assocarray-component-field-type` and `color-cert` off (results use `assocarray` fields, and the spec's black and near-white tokens are in-app colours, not store art) |
| `brighterscript-formatter` | 1.8.4 | Format check |
| `rooibos-roku` | 5.17.0 | Unit tests |
| `brs-node`, `brs-scenegraph` | 2.6.1, 0.6.1, Node 22 | Headless runner (not release evidence) |
| `sca-cmd` | 14.16.0, sha256-pinned | Static Analysis |
| `roku-test-automation` | 2.2.x | On-device journeys from Milestone 2 |
| Roku Resource Monitor, Perfetto, port 8080/ECP queries | — | Memory, texture, rendezvous, frame-rate, latency |

**Per-PR CI** (GitHub Actions, Ubuntu, Node 22, Java 21): `npm ci`; `bsc` with
bslint; `bsfmt --check`; the production zip and the 3.5 MB budget;
`scripts/sca.sh` on `out/staging`, failing on errors and on any
`monitoring`-category warning; `scripts/test-headless.sh`, which fails unless
stdout contains `[Rooibos Result]: PASS` (`brs-cli` exits 0 even when tests fail),
with a 5-minute timeout and JUnit output; `scripts/hygiene.sh`, case-insensitive
greps on built output (no `/api/v1`, `InitClientCertificates`,
`observeFieldScoped(`, `observeFieldScopedEx` with a string argument, or bare
`print`; required manifest keys). Packaging stamps `build_version` from the CI run
number; the version-increase check runs only on release tags.

**`sca-cmd` supply:** the pinned zip comes from a mirror the maintainers choose
before M0-3 merges (it is Apache-2.0), cached in CI. On a cache miss with a changed
upstream hash the job fails with a "bump the pin" instruction; it never falls back
to the live tool silently. A weekly job runs the live `sca-cmd` and flags a hash
change.

**Headless limits:** under brs-node async `roUrlTransfer` is synchronous, memory
events and `roRenderThreadQueue` are absent or unverified, and `@SGNode` suites can
hang. So the scheduler, auth coordinator, router, session and seek reducers,
recovery chain, Auto-quality policy, memory policy, gates, probe, serializer, and
converters are pure modules with injected clocks and transports, and nothing
depending on Task concurrency or platform events is claimed as tested headless.
Those suites are tagged `device`.

**Device lanes** are local scripts reading `.env`, like `sideload.sh`:
`scripts/device-check.sh` (reboot, 30 s wait, 10 cold launches with the port 8085
beacon report, `fwbeacons/track` and `sgrendezvous/track` set up where used,
`chanperf` and `r2d2-bitmaps` snapshots, the ECP deep-link matrix) and
`scripts/header-probe/` (a logging reverse proxy that records method, path class,
status, and presence booleans for `Authorization`, `X-Profile-Id`, and
`X-Profile-Token`, never values or query strings, and can answer with redirects to
a second origin or to `http://`). Results go to `docs/hardware-evidence.md` without
addresses or credentials.

Unit tests cover spec section 12.1, plus the probe (recorded answers per device
class), gates, the serializer against OpenAPI shapes, timeline and seek decisions,
the recovery chain, durable playback jobs, memory policy, data budgets, and the
subtitle converters and cue shifting.

## 9. Delivery

### 9.1 Critical path outside code

| Item | When | Owner |
| --- | --- | --- |
| Roku developer account owned by the Silo-Server organization | Before Milestone 0a | To assign |
| Devices in section 3 (the 512 MB player and one 4K player first) | Before Milestone 0a; the rest before 0b | To assign |
| `sca-cmd` mirror location | Before M0-3 merges | To assign |
| Signing key: `genkey` on one designated device; developer ID, password, and a signed reference package in the team's secret manager with two custodians, never in git. Losing it means a new app and a forced sign-in for every user (criterion 4.1) | Milestone 0a | To assign |
| Beta app, re-created every 120 days (20 testers) | Milestone 0a | To assign |
| Dashboard Static Analysis on each milestone exit | From Milestone 0a | — |
| Unpublished public app record for App Behavior Analysis | By the Milestone 2 exit | To assign |
| Reviewer server owner and host | Named in Milestone 0a | To assign |
| Store listing inputs: poster 540×405, up to six 1920×1080 screenshots, privacy and terms URLs, support URL, email, and phone, age rating | By Milestone 3 | To assign |
| Questions to Roku (section 7) | Sent in Milestone 0a | To assign |
| An owner for each server dependency that a failed test activates (S-9, S-15, S-4, S-11, S-18, S-20) | When the test fails | To assign |
| Release checklist: version and channel mapping, key custody, reproducible package and sign steps, exclusion of `dev` components, beta expiry, an install-over-existing-data rehearsal with saved server, tokens, remembered profile and PIN, and installation ID | Before the first beta with households | To assign |

### 9.2 Milestones

Each exit is met on hardware, not in the simulator. A required path that fails
blocks the exit until a fix is implemented and tested; a recorded failure is not a
pass.

**Milestone 0a — platform feasibility (gates Milestone 1).** Work: section 9.3,
PRs M0-1 to M0-12; the transport harness (M0-5) runs before the production
infrastructure. Exit, per cohort:

| Cohort | Required routes, each starting, seeking (local or reanchor), reporting progress, stopping with the final position, taking one replan, and reopening after token expiry |
| --- | --- |
| 512 MB player | H.264 original with AAC and AC-3; HLS copy remux of H.264 with AAC and AC-3, with audible audio (H19); HLS transcode |
| 4K player | The above, plus HEVC Main 10 original and HEVC copy remux with AAC, E-AC-3, and E-AC-3 JOC, with audible audio |

- H2 passes (signed `#EXT-X-DEFINE` playlists play), or S-21 is implemented and
  tested;
- H1 passes with zero credentials forwarded off-origin, or S-9/S-20 is implemented
  and tested;
- H19 passes, or S-15/S-4 is implemented and tested;
- H8 records each cohort's segment envelope, and over-envelope sources fail
  detectably (a `Video` error, not a hang or silence) so `failure_recovery` reaches
  a transcode; if failures are not detectable, S-11 is implemented and tested;
- H14 meets the section 6.8 success criteria and the subtitle transport is chosen;
- G1, G13, and G14 set;
- the threading spike's delivery decision, the start-path timing, and the
  `release`/`perf`/`requires_mkv` measurements recorded;
- the section 4.8 workload holds the section 1 memory and texture limits on the
  512 MB player;
- section 9.1's Milestone 0a items done, the dashboard Static Analysis run on a
  signed beta package, and the Roku questions sent.

**Milestone 0b — output claims (runs alongside Milestones 1–2).** H3, H4, H5, H9,
H13, H16, and H20 on the DV, HDR10-only, and SDR TVs, the Atmos and DTS sinks, the
no-DV 4K player, and the Roku TV. Exit: each of G2–G8 has a recorded result, on or
deliberately off within its tested cohorts. Exits before Milestone 3 starts.

**Milestone 1 — foundation.** PRs M1-1 to M1-8. Exit: spec section 13 Milestone 1
criteria; a placeholder Home fires `AppLaunchComplete`; with a restored session
and a PIN-free remembered profile, over 10 cold launches after a reboot and 30 s
wait, median ≤ 6 s and max ≤ 8 s on the 3810X/3921X and median ≤ 9 s on the
3840X; `sca-cmd` reports no errors and no monitoring warnings; the ECP deep-link
matrix routes correctly to placeholders, signed in and out; CJK and Arabic titles
render or the font fallback decision is recorded.

**Milestone 2 — browse.** Top bar, Home with hero and rows, library landing and
Browse with sort and alphabet rail, Search, movie and series detail with seasons
and episodes, loading/empty/error states, focus restoration, post-playback
refresh hooks. Exit: spec section 13 Milestone 2 criteria; the section 1 browse
targets (launch, transition, key response, scrolling, memory, texture, leaks) on
the 512 MB player, the non-OpenGL device, and a reference device; the side-by-side
parity review against tvOS and Android TV (spec section 12.3); the first App
Behavior Analysis run.

**Milestone 3 — playback.** Player controls and Options, track and quality
replans, subtitles, trickplay, skip intro, Up Next, server preferences, recovery
and Auto adaptation, output-change replans, deep-link playback. Exit: spec section
13 Milestone 3 criteria; the 8 s playback-start target; G1–G8, G13, and G14
recorded across the device matrix (G9–G12 stay off unless their preconditions and
tests are met); the section 6.6 acceptance scenarios; the parity review for the
player.

**Milestone 4 — beta and public readiness.** Deep Linking Tester, dashboard
Static Analysis, store assets, privacy policy (Silo's progress and route events
are the only telemetry; no analytics, crash reporting, or tracking SDKs, spec
section 11), the release checklist, a Roku beta with real households. Public
submission additionally requires Roku's answers (section 7) on LAN HTTP, private
catalogs, 4.3, the authentication rules, and PINs on deep links, or a supported
scope that satisfies them.

### 9.3 Pull requests for Milestones 0a and 1

| PR | Scope | Accept |
| --- | --- | --- |
| M0-1 Repo foundation | `LICENSE` (AGPL-3.0-or-later) and the Silo trademark notice; `.brs` → `.bs` with no behaviour change; `bslint.json`, `.bsfmt.json`; exact tool versions; `.nvmrc` 22 | `npm ci`, lint, and build clean; sideload shows the existing diagnostic screen |
| M0-2 Manifest and certification plumbing | Section 3 manifest keys; placeholder icons and splashes; main loop with the multi-line `roInput` handler, all five memory APIs and the general-memory fallback, codec-capability and HDMI events; `AppLaunchComplete` from the diagnostic screen; `release`/`perf`/`dev` variants | Local `sca-cmd` has no errors and no monitoring warnings; ECP `launch` and `input` print parsed, non-secret args; the port 8085 report shows one `AppLaunchComplete` (and whether `query/fwbeacons` lists it); launch time and memory recorded for `release` versus `perf` and with and without `requires_mkv` on the 3840X |
| M0-3 CI | Section 8 per-PR pipeline and weekly job | Green; a temporary failing test and a temporary 4 MB file each turn it red |
| M0-4 Logger and redaction | `source/util/log.bs`, `redact.bs`, specs per AGENTS.md secret class | Specs pass; `no-print` passes with the logger excepted |
| M0-5 Transport harness (`dev` only) | A narrow temporary Task: sign-in with credentials typed through `StandardKeyboardDialog` (never stored), a fixed capability body, start for a typed item ID, a `Video` node with its own agent; `scripts/header-probe/` | First H1 run (headers on every API-origin request class, none on proxy origins, zero forwarding on redirects and absolute child URIs), first H2 run (signed `#EXT-X-DEFINE` playlists), and first H19 run (audible muxed-fMP4 audio) on both devices, recorded before M0-6 starts |
| M0-6 Threading spike | `ApiTask` loop, in-flight map, deadlines, lanes, reserved playback slot, cancellation on a pure scheduler; `AppScene` router with `RequestHandle`, `setRef` payloads, and teardown unregistering; `PostMessage` delivery with the field-set fallback; `GET /api/v2/system/info` | Scheduler specs headless; on device, a 200-item tree arrives with no read rendezvous (`sgrendezvous/track`, then `query/sgrendezvous`), and in a Perfetto trace of the `perf` build the router handler and handle callback slices fit the device's frame budget (16.7 ms at 60 Hz), excluding list population; decision recorded |
| M0-7 Storage and auth | Registry schema and migrations, `Main()` snapshot, `ApiTask` as single writer; login, single-flight refresh with a generation counter, logout, Problem Details mapping (section 5); fixtures sync | Concurrent `401`s cause one refresh and one retry each; refused refresh signs out; `503` keeps tokens; sign-in survives relaunch and reboot |
| M0-8 Diagnostic sign-in, profiles, PIN | Plain screens with `StandardKeyboardDialog`/`StandardPinPadDialog` for server URL (HTTPS, then HTTP after the prompt), username, password, profile, PIN, item ID | Sign-in, wrong PIN, lockout with the server's `Retry-After`; profile headers paired; no secrets in the debug console |
| M0-9 Probe, gates, serializer | `probe.bs`, `gates.bs`, `serialize.bs`; recorded probe answers per device class; the normalized output context; payload on the diagnostic screen | Serializer matches OpenAPI shapes; payloads recorded for both devices; a `201` with `original_http` for H.264/AAC MP4 |
| M0-10 Test player | Session, seek, and recovery reducers; durable playback jobs; Auto-quality reducer; one reused `Video` node with its own agent; Stats overlay; stored-body replay; the section 4.8 workload | Reducer specs (sequence monotonic, stop-ID reuse, failure-chain bookkeeping, intent replans accepting repeated keys, Auto → explicit → Auto, stall histories); on device the section 9.2 required routes per cohort, the section 6.6 scenarios, resume shown on reopen, stop-to-first-frame and deadline hits recorded; the workload within the section 1 limits |
| M0-11 Hardware runs | `docs/hardware-evidence.md` template; full H1, H2, H8, H14, H19 runs | Rows record device, OS, sink, file class, result, without secrets; gates updated with test IDs |
| M0-12 Signing and dashboard (owner) | `genkey`, key custody, beta app, signed upload, dashboard Static Analysis | Redacted report saved; authentication-category findings triaged |
| M1-1 Theme, fonts, assets | Tokens, shared `Font` nodes, subset Inter with licence and source, corner and focus 9-patches (FHD/HD), gradient ramp | Zip ≤ 2.5 MB; non-Latin titles render or fallback recorded |
| M1-2 Navigation | Stack reducer, screen host, Back routing (spec section 5.3, criterion 4.6), hidden-screen release hooks | Reducer specs; 20 push/pop cycles keep the node count within 5% |
| M1-3 Production `ApiTask` | Headers per spec section 7.4, `503`/`Retry-After`, proactive refresh, prefetch shedding, `AUTO` versus `http2` measurement | 30-minute device soak with an expiring token: one refresh per expiry, no stuck requests |
| M1-4 Setup and sign-in screens | Spec section 5.4 layout, `DynamicKeyboard`, `auth/providers` with the `password_login=false` message, "server update required", dialog beacons, sign-out and server change clearing state | Parity notes against Android TV; HTTPS→HTTP prompt; offline sign-out; no previous-account artwork after a server change |
| M1-5 Profile picker and PIN | "Who's watching?", `DynamicPinPad` submitting on the fourth digit, lockout copy, remembered profile, single-profile skip, `is_child` plumbing | Restore and refusal specs; PIN token re-requested only after a server refusal; dialog beacons in the port 8085 report |
| M1-6 Memory policy and platform events | `source/memory/policy.bs` per section 4.7; main-loop wiring; 15.1 polling; general-memory fallback; codec, caption-mode, and HDMI events routed | Policy specs per OS path; raw limits recorded per device class; a forced-allocation test sheds per policy |
| M1-7 Deep links and placeholder Home | `source/deeplink/`; launch and `roInput` routing per section 7, with deferral through sign-in; placeholder Home | Parser specs; the ECP matrix for movie, episode, series, season, launch and input, signed in and out; one `AppLaunchComplete` per launch |
| M1-8 Device lane and exit | `scripts/device-check.sh`; dashboard Static Analysis on a new beta package; 4.3 library cost if Roku says it applies | Milestone 1 numeric exit met; no dashboard errors |

### 9.4 First-release acceptance map

| Spec section 3.2 requirement | Milestone | Acceptance |
| --- | --- | --- |
| One server by URL; password sign-in; LDAP-style providers | 1 | M1-4 on device; `password_login=false` message |
| Profile picker, PIN, child restrictions | 1 | M1-5; server-side restrictions honoured on Home and Search in Milestone 2 |
| Switch profile, switch server, sign out | 1 | Identity change clears state (section 4.7) and settles pending playback jobs (section 6.6) |
| Home with server sections, Continue Watching, Next Up | 2 | Rows in server order; refresh after playback |
| Movies and Series tabs, Recommended, Browse with sort and alphabet rail | 2 | Section 4.8 budgets on the 512 MB device |
| Search across movies, series, episodes | 2 | `video_with_episodes` when advertised |
| Movie and series detail, seasons, episodes | 2 | `play_season_number` from item detail |
| Play, resume, start over | 3 | Section 6.3 `start_position` rules, tested separately at a non-zero position |
| Direct play, HLS remux, HLS transcode | 0a, 3 | Gates G1, G13, G14; Milestone 3 matrix |
| Play/pause, skip, rate ladder, scrubbing, Replay, stop | 3 | Section 6.10; trickplay on every speed |
| Audio, subtitle, quality via replan | 3 | Sections 6.7–6.8 |
| Skip intro, Up Next with autoplay | 3 | `IsAutoplayEnabled()` honoured |
| Periodic and final progress | 0a, 3 | Durable jobs (section 6.6) |
| Server-stored playback preferences | 3 | Spec section 8.5 keys applied |
| Deep links and Direct to Play | 1, 3 | Section 7 matrix; Deep Linking Tester in Milestone 4 |
| Roku caption and accessibility settings | 3 | Section 6.10; Audio Guide on every focusable |

## 10. Hardware test catalogue

Each run records device, Roku OS, sink, file class, and result in
`docs/hardware-evidence.md`, never credentials or signed URLs.

| ID | Test |
| --- | --- |
| H1 | `Authorization` and profile headers on original MKV/MP4 range requests, HLS playlists, init and media segments, WebVTT renditions, side-loaded subtitles; after seek, reanchor, replan, and token refresh. Poster requests after playback carry no `Authorization`. With the header probe answering API, media, and subtitle routes with 302s to a second origin and to `http://`, and serving absolute child URIs: no credential header reaches another origin or plain HTTP, from the API client or the `Video` node. `?token=` behaviour should S-9 be needed |
| H2 | Signed HLS on the API origin for a feature-length remux and transcode: `#EXT-X-DEFINE` (version 8) playlists parse and play, including after seek and reanchor; `ForwardQueryStringParams` does not duplicate the `st` query; proxy-origin HLS and originals play with no account headers sent to the proxy |
| H3 | Dolby Vision P5, P8.1, P8.4, and P8.2 (the latter two through the `dev` override) as original MKV and MP4 and as HLS copy remux (fMP4 and, once S-15 exists, TS; with and without S-4 attributes); `GetVideoMode()` outside and during DV playback; P7 strip to HDR10; P8.1, P8.4, and P8.2 base layers on an HDR10-only TV; the no-DV 4K player on a DV TV; DV `max_level` |
| H4 | HEVC Main 10 4K original MKV and MP4 at 24, 30, and 60 fps, including level 5.2 and 6.x sources against the probe's answers; 4K SDR downscaled on a 1080p output; startup, seek, sustained bitrate, memory |
| H5 | HDR10 and HLG on HDR10/HLG and HDR10-only TVs; HDR10+ on HDR10+ and non-HDR10+ TVs; Display Type 1080p and 4K SDR on an HDR TV, recording `GetDisplayProperties()` and `GetVideoMode()`; HLG through an HLS remux; an 8K Roku TV if available |
| H6 | AV1 original MKV and MP4, bare versus container probe |
| H7 | VP9 profile 2 HDR in MKV/WebM |
| H8 | Copy-remux segment size per RAM class: the largest segment that starts and seeks, and whether a larger one fails with a `Video` error or hangs |
| H9 | E-AC-3 JOC to an Atmos AVR (player) and over ARC/eARC (Roku TV); MS12 decode on the Ultra; `IsPassthruCodecActive()`; AAC 5.1 output on a Stick 4K and an Ultra, and the interim stereo rule on a device without multichannel AAC |
| H10 | DTS core original MKV/MP4 with a DTS sink: start, pause, seek; behaviour with a non-DTS sink |
| H11 | DTS-HD MA and DTS:X under a `dts` claim; TrueHD reaching the player |
| H12 | Multichannel FLAC, PCM (each tested `pcm_*` name), and Opus output |
| H13 | Codec-capability and hot-plug events: AVR power, HDMI swap, private listening, Display Type change, on players and a Roku TV; no replan caused by playback's own mode switch |
| H14 | Subtitles against the section 6.8 success criteria: native URL tracks with `timestamp_offset`, `tmp:/` SRT tracks, the HLS WebVTT rendition; original and remux; SRT and ASS on a remux after reanchor; after seek and resume; Unicode; caption-mode changes; Replay captions; embedded-text readiness on the reference file |
| H15 | Track changes made in Roku's `*` overlay during playback |
| H16 | Frame-rate matching at 23.976 and 24.000 with auto-adjust on and off; no replan caused by the switch |
| H17 | Memory, texture, frame rate, glyph cache, and focus-scale cost through a scripted browse journey on the 512 MB, non-OpenGL, and reference devices |
| H18 | Intermittent bandwidth, failed adaptation, and a server with transcoding disabled; Roku OS 16 regressions across the above |
| H19 | Copy remux with muxed audio and video in fMP4 on every cohort: H.264 with AAC and AC-3 on all devices, HEVC with AAC, E-AC-3, and E-AC-3 JOC on 4K devices; audio presence from `audioFormat`, the sink's info panel, and an audible check, not from `state`; then TS once S-15 exists |
| H20 | Trickplay sheet decode time and `loaded_textures` on the 512 MB, non-OpenGL, and reference devices |

## 11. Server coordination

Draft issues for silo-server, to file only when the maintainers agree. Server
behaviour behind each was traced on `origin/main` on 2026-10-21.

| ID | Title | Roku impact | Priority |
| --- | --- | --- | --- |
| S-15 | Let v3 clients request MPEG-TS packaging for copy remuxes (the executor already supports it as `CopyVideoMPEGTS`; only the Jellyfin-compatibility layer sets it) | Every copy remux, H.264 included, if H19 shows muxed fMP4 audio fails | Blocking if H19 fails |
| S-20 | Authenticated `/api/v2` and media routes never redirect off-origin or to HTTP, and the setup check refuses an origin that redirects | Credential confinement if H1 shows Roku forwards headers on redirects | Blocking if H1 shows forwarding |
| S-9 | A short-lived, session- and profile-bound media token for players that cannot set headers on HLS child requests; `?token=` works today but puts the 8-hour account token in every segment URL | Needed only if H1 shows headers missing on API-origin media | Blocking if H1 fails |
| S-21 | Let clients opt out of `#EXT-X-DEFINE` playlist compaction (a client feature such as `hls_no_variable_substitution_v1`), or move the signed token out of segment queries | Needed if H2 shows Roku cannot parse `#EXT-X-DEFINE`; otherwise long signed HLS titles fail | Blocking if H2 fails |
| S-4 | Publish a multivariant HLS master with `CODECS`, `VIDEO-RANGE`, and `SUPPLEMENTAL-CODECS`, optionally with demuxed audio as an `EXT-X-MEDIA:TYPE=AUDIO` rendition | Needed if H3 shows Roku will not enter HDR or DV mode from a bare media playlist; an alternative fix for H19 | High if H3 or H19 fail |
| S-11 | Bound copy-remux segment bytes for clients with small media buffers (a client-declared limit, falling back to transcode); related to #1770 and #2515 | Needed if H8 shows over-envelope failures are not detectable | Blocking if H8 shows hangs |
| S-1 | Convert tracks the client cannot decode (TrueHD, DTS-HD, DTS) to E-AC-3 5.1 instead of AAC on a video-copy remux when the HLS delivery lists `eac3`, including `platform_attested` clients, behind an opt-in client feature. Builds on the `audio_to_eac3@1` recipe in draft PR #2015 (issue #2010), which covers only client-decodable tracks with exact sink evidence | Surround for TrueHD and DTS-HD titles on every Roku with a Dolby sink | High |
| S-13 | Capability-aware default audio selection (prefer a track the client can copy), and a per-codec channel ceiling so AAC 5.1 is not planned for clients that cannot decode it | Replaces the client-side track pick, the interim `max_channels: 2`, and the stop-and-restart round trip on devices without multichannel AAC | High |
| S-18 | Bounded or streamed extraction of embedded text subtitles for source-preserving playback | Needed if H14 misses the 15 s target | Prerequisite for embedded text on originals and remuxes if H14 fails |
| S-12 | Convert ASS/SSA to WebVTT for clients sending `ass_styling: false` with `compatible` fidelity | Removes client-side ASS conversion and shifting | Medium |
| S-8 | Variant-aware DTS matching (core, HD MA, DTS:X) with a channel ceiling | Prerequisite for G9 | Medium |
| S-5 | Pin the HEVC transcode output level so level-bounded clients can receive HEVC | HEVC rather than H.264 transcodes | Medium |
| S-2 | Server-side Dolby Vision P7 → P8.1 conversion | P7 titles in DV instead of HDR10 | Medium |
| S-19 | Scope `client_dv8_base_layer_fallback_v1` to the compatibility IDs the client names | P8.4 as its HLG base layer on a DV output without giving up the P8.1 DV remux | Medium if H3 fails for ID 4 |
| S-16 | A narrower trickplay sheet variant (fewer columns or 160–200 px tiles) | Needed if H20 fails on low-end devices | Medium if H20 fails |
| S-17 | Trickplay on by default for new libraries, or clear setup guidance | Criterion 4.7 on real installs | Low (decision D-5) |
| S-14 | HLS-remux and transcode playback-plan fixtures in `contracts/api/v2/fixtures/` | Client contract tests | Low |
| S-3 | Probe-backed passthrough evidence without sink layouts | Proper passthrough claims | Low |
| S-6 | Container-scoped HDR/DV capability on `original_http` | DV from MP4 direct play if H3 shows MP4 works and MKV does not | Low |
| S-7 | `claims.audio.atmos_preserved` never becomes true | Diagnostics | Low |
| S-10 | HDR-preserving transcode for HDR10-capable outputs | Burn-in, quality changes, and over-level sources keep HDR | Low |

The spec section 14 items (migration ledger, settings manifest platform list,
diagnostics allowlist) remain.

## 12. Spec changes that land with this plan

Each edit lands in `docs/spec.md` with the work it affects.

| Spec section | Change |
| --- | --- |
| 3.2, 3.3 | Trickplay thumbnails move into the first release (criterion 4.7) |
| 4 | Minimum firmware is a dashboard field; the manifest keys in section 3, including `requires_mkv=1`; memory-monitor history and unsupported models; Roku OS 16; tooling (BrighterScript `.bs`, `scripts/sideload.sh` rather than `roku-deploy`, brs-node); replace the "On-device authentication" link, which points at rendezvous linking |
| 5.2 | Four Inter weights now; subsets and the fallback rule |
| 5.7, 5.9 | `*` hands off to Roku's overlay when controls are hidden; the four caption modes in Options and global caption writes; Replay clamped to 10–25 s with replay captions; autoplay setting; overlay track changes; "Playback progress is pending…" and "Loading subtitles…" copy; deviations: low-tier cards without focus scale, the HD-sized low-tier hero, any font fallback |
| 6.1 | `.bs` sources and the new files and directories in section 4.4 |
| 6.3 | Results reach screens through the router and handles, not a shared envelope field; durable playback jobs |
| 7.2–7.4, 8.1, 8.3, 9.1 | The corrections in section 5 |
| 9.2 | Rewritten from section 6.1: tiers, probe ladder with measured HEVC levels up to 6.2, decoder-bounded size, the normalized output context, HDR gated on ≥ 2160-line output, DV device evidence and profile levels with compatibility IDs, per-delivery HDR, never-claimed codecs, gates; Dolby Vision, HDR10+, HLG move from "later increments" to gated first-release claims; DTS waits for S-8; plain Baseline H.264 transcoded |
| 9.3 | The OpenAPI v2 components define the body; optional members only on purpose (including the interim `max_channels: 2`); identities and stored bodies replayed verbatim; `failed_plan_id` on every replan; stream format and `PlayStart` from the plan; client track pick; Resume sends the rewound position explicitly |
| 9.4 | Signed-URL mode kept, as the spec already says (decision D-1); headers only on configured-origin URLs; per-`Video` `roHttpAgent`; subtitles for proxy-served plans downloaded through the API client; the `#EXT-X-DEFINE` risk (H2, S-21); credential confinement proven by H1, with S-20 if needed |
| 9.5, 9.6 | Section 6.5 seek and reanchor; section 6.6 lifecycle and job bounds; section 6.7 recovery, the failure chain, client-side `attempt_count`, `adaptation_exhausted`, Auto adaptation; the Problem type table and `404` handling in section 5 (progress `404` restarts, a Roku deviation from Android) |
| 9.7 | Section 6.8: ASS arrives raw; client-side cue shifting for SRT and ASS; the negative `timestamp_offset`; success criteria; app-rendered captions only by decision; the documentation conflict on side-loaded WebVTT |
| 10.1, 10.2 | Section 7's deep-link profile rule, interim PIN rule, and state table; the new questions for Roku |
| 12.2 | Fixture layout as found in `contracts/api/v2/fixtures/` |
| 12.4 | Section 3's device matrix and section 10's tests |
| 13, 16 | Milestones 0a and 0b replace Milestone 0; section 9.1's account, key, and owner items join the definition of done; Milestone 4's Roku-answer prerequisite |
| 14, 15 | Section 11's issues; Dolby Vision and advanced HDR become gated first-release claims; AC-3/E-AC-3 "copied, no passthrough claim" |

## 13. Decisions

Decided on 2026-10-21; [`implementation-assumptions.md`](implementation-assumptions.md)
records the answers and the assumptions made since.

| Decision | Outcome |
| --- | --- |
| Media authentication | **Decided (D-1):** support proxy nodes through signed-URL mode (section 6.4) |
| Resolution bound | **Decided (D-2):** decoder limit where possible, so 4K SDR originals play on 1080p outputs |
| Dolby Vision | **Decided (D-3):** HLS copy remux under G5 with device-side DV evidence; P8.4 and P8.2 transcode to SDR until H3 passes their compatibility IDs; the base-layer claim only on outputs without DV |
| Deep link when the last profile is a child | **Decided (D-4):** use the most recent non-child profile and play, as Roku's text reads; skip PIN-locked profiles until Roku rules on PIN prompts. The trade-off: a household whose adult profile has no PIN can reach adult titles through Roku search |
| Trickplay when a server has none | **Decided (D-5):** the server provides trickplay; files without sheets show time only with an explanation; Roku is asked, but release does not wait |
| App-rendered captions if native subtitle paths fail H14 | Open: do not adopt silently; decide with the H14 results, since it gives up Roku's caption styles |
| Devices without multichannel AAC | **Decided (D-6):** interim stereo conversion until S-13: `max_channels: 2` when the selected track is converted or is multichannel AAC, and a stop-and-restart with the ceiling when a plan returns multichannel AAC (one extra round trip). Alternatives: an `output_change` replan (verified only in the planner, and the output has not changed), or making S-13 a beta blocker |
| Server issues | Drafts only (assumption A-1): S-15, S-20, S-21, S-4, S-1, S-11, S-13, S-12; file when the maintainers agree |
| Prior community client (whitepeakcreative/silo-roku, AGPL-3.0-or-later) | Reuse lessons, not code |
| Owners | Open (assumption A-7): Roku account, signing-key custody, `sca-cmd` mirror, reviewer server, device purchases, activated server dependencies (section 9.1) |

## 14. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| `HttpHeaders` do not reach HLS child or subtitle requests | No authenticated HLS | H1 in M0-5; S-9 implemented before Milestone 1 if it fails |
| Headers forwarded on a redirect to another origin | Credentials leak (AGENTS.md) | H1 redirect cases; G1 stays closed; S-20 |
| Roku cannot parse `#EXT-X-DEFINE` | Long signed HLS titles fail on the API origin | H2 in M0-5; S-21 |
| Muxed fMP4 remuxes play without audio | Every remux, H.264 and HEVC, is silent with no error to trigger a replan | H19 in M0-5; S-15 or S-4 |
| Roku needs HLS master attributes for HDR/DV | DV remuxes play in the wrong range | H3; S-4; base-layer fallback on non-DV outputs |
| P8.4 home videos and over-level HEVC sources | SDR 1080p transcodes until H3 and H4 widen the claims | H3 override; the extended HEVC ladder; S-5, S-10 |
| Large copy-remux segments | 4K remuxes fail to start | H8 envelope; S-11; a transcode fallback that may be unavailable or SDR on servers without transcoding |
| Subtitle transport fails or is slow | External SRT terminal; SDR burn-in; late subtitles | H14 criteria in Milestone 0a; S-18 |
| 512 MB and non-OpenGL budgets | Crashes, slow focus | Sections 4.6–4.8; the 0a workload; H17 at every exit |
| Private-catalog review, 4.3, 4.7, dashboard auth rules | Rejection | Questions to Roku in Milestone 0a; early ABA; Milestone 4 prerequisite |
| Probe over-claims | Hangs on unsupported audio | Never-claimed list; `mat` refusal; replan |
| Lost signing key | New app, forced sign-in | Section 9.1 custody |
| Roku OS 16 changes | Regressions | H18; test on 15.x and 16.x |

## 15. Review record

**Round 1** (2026-10-21) used four independent reviews: Roku platform accuracy
against current Roku documentation; server-contract accuracy, which re-ran the
planner on the payloads; architecture, performance, certification, and delivery;
and a whole-plan review on a different model. They reported 7 blockers, 47 major,
and 56 minor findings.

**Round 2** re-checked every round-1 finding against the revised plan and looked
for new errors. Platform and architecture: 57 of 68 findings resolved, 10
partial, 1 justified deviation, no new blocker, 3 new major. Contract: 25 of 27
resolved, 2 partial; the revised payload validates; the planner refuted two
outcome rows (P8.4/P8.2 and over-level HEVC sources), now corrected. Whole plan:
7 of 15 resolved, 8 partial, verdict "ready after listed fixes", with 1 new
blocker (credential confinement across redirects). This revision addresses every
round-2 must-fix item.

**Round 3** ran the server planner on the rules this revision added. The final
Appendix A validates; the HEVC level ladder, the audio-track pick, and the
interim stereo ceiling behave as written. It found that video transcodes
re-encode copyable surround to AAC 5.1, that `failure_recovery` cannot switch a
plan to stereo, that the Problem table missed several types, and that a local
repeated-key check would end legitimate server retries; sections 2.2, 5, 6.1,
6.3, 6.7, and 13 now reflect those results. The prose of this last revision has
not been re-reviewed as a whole.

Where reviewers disagreed, the plan takes:

- one `Video` node per session with asynchronous stop, over one per attempt, and
  never a second node while one is stopping;
- the deep-link profile rule in Roku's own words, with the child-safety trade-off
  and the interim PIN rule listed in section 13;
- measured HEVC levels kept, extended up to 6.2, over removing the bound.

Not verified anywhere and left to hardware or Roku: whether `HttpHeaders` reach
HLS child and subtitle requests, and whether Roku forwards them on cross-host
redirects; muxed fMP4 audio on current firmware; DV from HLS remuxes without
master attributes, and P8.4/P8.2 DV; HEVC level strings above 5.1; `tmp:/`
subtitle tracks; how a Task obtains `roRenderThreadQueue` and whether it moves node
trees without rendezvous; whether `query/fwbeacons` lists app beacons; texture
ceilings for trickplay sheets; how Roku reviews private-catalog apps and applies
4.3, 4.7, and the dashboard authentication rules; and the 4 MB limit's measurement
point.

## Appendix A. Example payload

A Roku Ultra on a Dolby Vision/HDR10/HLG TV (no HDR10+) at 2160p, with an Atmos
AVR, after gates G1–G5, G8, G13, and G14 have passed and G9 has not. Values come
from live probes in practice: identifiers, the HEVC level (here the documented
5.1), and DV levels are placeholders.

```json
{
  "installation_id": "5b0c1f8e-7a2d-4e3b-9c41-0f6d2a8b7e15",
  "protocol_version": 3,
  "client_features": ["hls_subtitle_renditions_v1", "subrip_sidecar_v1",
                      "seek_reanchor_v1", "direct_stream_resume_v1"],
  "file_id": "42",
  "profile_id": "1",
  "playback_attempt_id": "3f2b7c9e-0d1a-4c55-9f0e-6a7b8c9d0e1f",
  "quality_preference": "auto",
  "subtitle_fidelity_preference": "compatible",
  "client_capabilities": {
    "video_evidence": "exact",
    "audio_evidence": "platform_attested",
    "codecs_video": ["h264", "hevc"],
    "codecs_video_hardware": ["h264", "hevc"],
    "codecs_audio": ["aac", "mp3", "ac3", "eac3"],
    "containers": ["mp4", "mkv"],
    "max_resolution": "2160p",
    "hdr": true,
    "hdr_details": {
      "hdr10": true, "hdr10_plus": false, "hlg": true, "dolby_vision_profiles": [5, 8],
      "dolby_vision_profile_levels": [
        { "profile": 5, "max_level": 9 },
        { "profile": 8, "max_level": 9, "bl_compatibility_ids": [1] }
      ]
    },
    "video_decode": [
      { "codec": "h264", "hardware": true, "profiles": ["constrained baseline", "main", "high"],
        "levels": [42], "bit_depths": [8], "max_width": 1920, "max_height": 1080, "max_frame_rate": 60 },
      { "codec": "hevc", "hardware": true, "profiles": ["main", "main 10"], "levels": [153],
        "bit_depths": [8, 10], "max_width": 3840, "max_height": 2160, "max_frame_rate": 60 }
    ]
  },
  "client_playback_context": {
    "protocol_version": 3,
    "form_factor": "tv",
    "app_version": "0.1.0",
    "app_build": "1",
    "app_channel": "sideload",
    "device": {
      "platform": "roku",
      "os_version": "15.1.4",
      "manufacturer": "Roku",
      "model": "4850X",
      "platform_details": { "model_type": "STB", "video_mode": "2160p", "ui_resolution": "fhd" }
    },
    "output": {
      "hdr_details": {
        "hdr10": true, "hdr10_plus": false, "hlg": true, "dolby_vision_profiles": [5, 8],
        "dolby_vision_profile_levels": [
          { "profile": 5, "max_level": 9 },
          { "profile": 8, "max_level": 9, "bl_compatibility_ids": [1] }
        ]
      },
      "current_sink": "hdmi",
      "sink_type": "hdmi",
      "display": {
        "hdr_evidence": "exact",
        "hdr_types": {
          "hdr10": true, "hdr10_plus": false, "hlg": true, "dolby_vision_profiles": [5, 8],
          "dolby_vision_profile_levels": [
            { "profile": 5, "max_level": 9 },
            { "profile": 8, "max_level": 9, "bl_compatibility_ids": [1] }
          ]
        },
        "display_id": "hdmi"
      },
      "output_context_id": "roku:2160:dv.hdr10.hlg:ac3.eac3"
    },
    "deliveries": {
      "original_http": {
        "enabled": true, "supported_on_device": true,
        "containers": ["mp4", "mkv"], "video_codecs": ["h264", "hevc"],
        "audio_decode_codecs": ["aac", "mp3", "ac3", "eac3"], "audio_passthrough_codecs": [],
        "hdr_details": { "hdr10": true, "hdr10_plus": false, "hlg": true, "dolby_vision_profiles": [] },
        "subtitles": { "embedded_text": false, "sidecar_text": true, "ass_styling": false,
                       "embedded_bitmap": false, "sidecar_bitmap": false, "font_attachments": false },
        "features": [], "auth_header_refresh": false, "validated_claims": [], "transformations": []
      },
      "progressive": {
        "enabled": false, "supported_on_device": false,
        "failure_reason": "disabled_pending_seekable_transport",
        "containers": [], "video_codecs": [], "audio_decode_codecs": [], "audio_passthrough_codecs": [],
        "subtitles": { "embedded_text": false, "sidecar_text": false, "ass_styling": false,
                       "embedded_bitmap": false, "sidecar_bitmap": false, "font_attachments": false },
        "features": [], "auth_header_refresh": false, "validated_claims": [], "transformations": []
      },
      "hls": {
        "enabled": true, "supported_on_device": true,
        "containers": ["hls"], "video_codecs": ["h264", "hevc"],
        "audio_decode_codecs": ["aac", "ac3", "eac3"], "audio_passthrough_codecs": [],
        "subtitles": { "embedded_text": false, "sidecar_text": true, "ass_styling": false,
                       "embedded_bitmap": false, "sidecar_bitmap": false, "font_attachments": false },
        "features": ["native_hls_playback_v1"], "auth_header_refresh": false,
        "validated_claims": [], "transformations": []
      }
    }
  }
}
```

## Appendix B. Sources

Roku (fetched 2026-10-12 to 2026-10-21):

- [Streaming specifications](https://developer.roku.com/dev/docs/media)
- [ifDeviceInfo](https://developer.roku.com/docs/references/brightscript/interfaces/ifdeviceinfo.md),
  [roDeviceInfoEvent](https://developer.roku.com/dev/docs/rodeviceinfoevent),
  [ifHdmiStatus](https://developer.roku.com/dev/docs/ifhdmistatus)
- [Video node](https://developer.roku.com/dev/docs/video),
  [content metadata](https://developer.roku.com/dev/docs/content-metadata),
  [Poster](https://developer.roku.com/dev/docs/poster),
  [Group](https://developer.roku.com/dev/docs/group),
  [RowList](https://developer.roku.com/dev/docs/rowlist),
  [MarkupGrid](https://developer.roku.com/dev/docs/markupgrid),
  [MaskGroup](https://developer.roku.com/dev/docs/maskgroup),
  [Effect](https://developer.roku.com/dev/docs/effect)
- [Closed captions](https://developer.roku.com/dev/docs/closed-caption),
  [HLS and DASH thumbnail tiles](https://developer.roku.com/docs/developer-program/media-playback/trick-mode/hls-and-dash.md)
- [Hardware specifications](https://developer.roku.com/dev/docs/hardware),
  [manifest](https://developer.roku.com/dev/docs/channel-manifest),
  [file system](https://developer.roku.com/dev/docs/file-system)
- [Static Analysis](https://developer.roku.com/dev/docs/static-analysis-tool),
  [certification criteria](https://developer.roku.com/dev/docs/certification),
  [certification tests](https://developer.roku.com/dev/docs/cert-tests),
  [authenticated app testing](https://developer.roku.com/dev/docs/authenticated-cert-testing),
  [publishing guide](https://developer.roku.com/dev/docs/channel-publishing-guide)
- [Measuring app performance (beacons)](https://developer.roku.com/dev/docs/measuring-channel-performance),
  [External Control Protocol](https://developer.roku.com/dev/docs/external-control-api),
  [app tracing](https://developer.roku.com/dev/docs/app-tracing),
  [deep linking](https://developer.roku.com/dev/docs/implementing-deep-linking),
  [autoplay](https://developer.roku.com/dev/docs/autoplay)
- [Optimization techniques](https://developer.roku.com/dev/docs/optimization-techniques),
  [SceneGraph threads](https://developer.roku.com/dev/docs/threads),
  [node access](https://developer.roku.com/dev/docs/sgnode-access),
  [ifSGNodeField](https://developer.roku.com/dev/docs/ifsgnodefield),
  [data transfer APIs](https://developer.roku.com/dev/docs/data-transfer-apis),
  [roRenderThreadQueue](https://developer.roku.com/dev/docs/rorenderthreadqueue),
  [ifUrlTransfer](https://developer.roku.com/dev/docs/ifurltransfer),
  [roUrlEvent](https://developer.roku.com/dev/docs/rourlevent)
- [roAppMemoryMonitor](https://developer.roku.com/dev/docs/roappmemorymonitor),
  [deprecated APIs](https://developer.roku.com/dev/docs/deprecated-apis),
  [release notes](https://developer.roku.com/dev/docs/release-notes)
- Support articles: [Roku Media Player formats](https://support.roku.com/article/share-media-over-usb-or-network),
  [player surround sound](https://support.roku.com/article/set-up-your-player-for-surround-sound),
  [Roku TV surround](https://support.roku.com/article/connect-surround-sound-to-your-roku-tv),
  [refresh rate](https://support.roku.com/article/change-the-refresh-rate),
  [Roku OS release notes](https://support.roku.com/article/roku-os-release-notes)

Community (confirm on hardware): jellyfin-roku and its JellyRock fork
(`source/utils/deviceCapabilities.bs`; issue
[#1027](https://github.com/jellyfin/jellyfin-roku/issues/1027) on segment size),
brs-engine's limitations and Rooibos notes, and the whitepeakcreative/silo-roku
community client's hardware notes.

Silo: in silo-server, `docs/architecture/playback-protocol-v3.md`,
`docs/architecture/trickplay.md`, `docs/playback-api.md`, and
`contracts/api/v2/openapi.json`; the Android TV app in silo-android.
