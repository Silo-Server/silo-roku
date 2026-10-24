# Hardware evidence log

Results of the hardware tests in `docs/implementation-plan.md` section 10, one
row per test run, newest session last. Each row records the test ID, date,
device and Roku OS, audio sink, file class, harness settings, result, and the
observed facts. Rows never carry server addresses, item or file IDs, accounts,
titles, tokens, or URLs; fixtures are named by their opaque corpus label
(`FX-nnn`) or `SYNTHETIC`.

Results: **PASS** meets the test's pass criteria; **FAIL** a criterion was
observed to fail; **PARTIAL** part of the procedure ran or a criterion could
not be observed; **PENDING** not runnable in this lab or session.

Sources for each fact: the harness stats overlay, ECP `query/media-player`,
and the header probe (`scripts/header-probe`, with `--extra-facts`).
Screenshots, probe slices, and console output stay in the tester's private
evidence folder.

## Session 2026-10-22: TCL Roku TV, lab stack behind the header probe

- **Device:** TCL 55R625 Roku TV (A109X), Roku OS 15.3.4 build 2303, 2160p60
  output, panel HDR10/HLG/Dolby Vision. Abbreviated below as "55R625 / 15.3.4".
- **Sink:** the TV itself. `IsPassthruCodecActive()` was false in every run;
  no external audio device was verified. Audio could not be heard remotely, so
  audibility is never claimed.
- **Server:** isolated lab stack (assumption A-11), proxy node disabled, so every
  media URL is on the API origin behind the probe. Signed-URL media mode (D-1).
- **Harness:** `npm run sideload:dev` build of `d8481b7`, used unmodified for H1,
  H2, H8, and H19. H14 used a temporary local patch that is not committed:
  it adds a subtitle-track selector that sends `subtitle_track_index`, and adds
  `roInt` to `harness.isNumber`. The stock harness cannot run H14 (see
  "Harness and probe defects").
- **Profiles:** "no-PIN" is the primary profile; "PIN" is a PIN-locked profile.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H1 step 1, original | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 H.264/AAC 1080p | defaults, no-PIN; Left, Right, FF, Rew (local seeks) | PASS | Every `api` and `stream` request on the origin carried `Authorization` and `X-Profile-Id`, and none carried `X-Profile-Token`. |
| H1 step 1, HLS copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 H.264/AAC; FX-009 MKV HEVC 2160p SDR AAC | `original_http` off, no-PIN; Left, Right, FF, Rew (4 `seek_reanchor` adopted) | PASS | 20 playlist and 252 segment requests, all with `Authorization` and `X-Profile-Id`, none with `X-Profile-Token`. |
| H1 step 1, HLS transcode | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 MKV HEVC 2160p SDR AAC | HEVC and E-AC-3 off, no-PIN; local seeks | PASS | 1 playlist and 218 segment requests, all with `Authorization` and `X-Profile-Id`. 9 segment 404s came from requests ahead of the transcoder after seeks. |
| H1 step 1, PIN profile | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 as transcode, HEVC remux, MKV original | PIN; one seek or reanchor each | PASS | `Authorization`, `X-Profile-Id`, and `X-Profile-Token` on every `api`, `stream`, `playlist`, and `segment` request. |
| H1 step 1, subtitle requests | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC external SRT; FX-003, FX-009, FX-028 embedded text | patched harness (H14), PIN; sidecars on | PASS | Sidecar downloads, `Video` subtitle fetches, and 113 HLS WebVTT rendition segments all carried the three headers. |
| H1 step 2, proxy origin | 2026-10-22 | — | — | — | — | PENDING | Not testable: the lab's proxy node is disabled and unreachable from the Roku. |
| H1 step 3, media 302 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 as original, remux, transcode | PIN; probe redirects `stream`, `playlist`, `segment`, `subtitle` to the foreign listener with 302 | FAIL | The `Video` node followed every redirect cross-origin. The foreign origin received `X-Profile-Id` and `X-Profile-Token`, but not `Authorization`, on the original's range request and on each HLS playlist, including the `failure_recovery` plan's. 5 probe alerts. Playback failed (401); segments and subtitles were never reached. |
| H1 step 3, media 307 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 as original, remux, transcode | as above with 307 | FAIL | Same as with 302: `X-Profile-Id` and `X-Profile-Token` reached the foreign origin on `stream` and `playlist` (5 alerts). |
| H1 step 4, API 302 | 2026-10-22 | 55R625 / 15.3.4 | TV | — | PIN; probe redirects `api` with 302; Play, then Sign in again | FAIL | The API client (`roUrlTransfer`) followed the cross-origin redirect: `GET /playback/capabilities` reached the foreign origin with `X-Profile-Id` and `X-Profile-Token`, without `Authorization`. The login POST was re-sent there as a POST without a usable body (400) and carried no credential headers. |
| H1 step 4, API 307 | 2026-10-22 | 55R625 / 15.3.4 | TV | — | as above with 307 | FAIL | The login POST was re-sent with its body to the foreign origin, and sign-in succeeded there (200), so the password reached a non-configured origin. The probe flags headers only; the 200 shows the body arrived. Later authenticated GETs reached the foreign origin without `Authorization`, and with `X-Profile-Id` and `X-Profile-Token` once a profile was selected. |
| H1 step 5, absolute child URIs | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 as remux and transcode | PIN; probe rewrites playlists so children are absolute on the foreign listener | FAIL | The `Video` node sent `Authorization`, `X-Profile-Id`, and `X-Profile-Token` on all 121 foreign segment requests, and playback succeeded. `HttpHeaders` go to whatever origin the playlist names. |
| H1 step 6, HTTPS to HTTP | 2026-10-22 | — | — | — | — | PENDING | Needs a TLS origin with a publicly trusted certificate; the lab has none. |
| H1, token refresh and Posters | 2026-10-22 | — | — | — | — | PENDING | The harness does not refresh tokens or show Posters (M0-10). |
| H2, long remux | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001 MKV H.264 1080p AAC, 78 min | PIN; `original_http` off; 2 min play, FF, Rew | PARTIAL | Playback started and continued after both `seek_reanchor`s, with no `Video` error. No playlist used `#EXT-X-DEFINE` (63 fetches, growing to 2.44 MB). Playlists totalled 91.5 MB against 126 MB of segments in about 3 min. `duplicate_query_keys` was false on every segment. |
| H2, long remux, `ForwardQueryStringParams` false | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001 | as above, FQSP false; FF | PARTIAL | Played and reanchored. `duplicate_query_keys` false on all 95 segments, as with Roku's default. No `#EXT-X-DEFINE`. |
| H2, long transcode | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 MKV HEVC Main 10 2160p HDR10, 127 min (fixture version and a second library version) | PIN; HEVC and E-AC-3 off | FAIL | The Roku refused the media playlist: ECP error `reader pick stream error:bad:mpr playlist file is too large.` The server served it with 200 (633,424 bytes). Earlier 754 KB and 2.4 MB playlists played, so the limit is not bytes alone; it is either the entry count (about 3,800 two-second segments) or the playlist's `#EXT-X-DEFINE` form, which the server's synthetic manifest uses above 64 KB of savings. The probe could not record `ext_x_define` because the relay aborted. After the `failure_recovery` replan the player exited. |
| H2, short transcode | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009, 24 min | HEVC and E-AC-3 off, both profiles | PASS | Played; local seeks (Left, Right, FF, Rew) worked. 754 KB playlist without `#EXT-X-DEFINE`; `duplicate_query_keys` false. |
| H2, proxy-origin HLS | 2026-10-22 | — | — | — | — | PENDING | No proxy reachable (see H1 step 2). |
| H19, H.264 + AAC | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4; FX-001 MKV | `original_http` off | FAIL | `server_remux_hls` with recipe h264/aac. `audioFormat` was `none` throughout (checked for up to 3 min), and ECP showed `audio="none"`, `segment_type="mux"`. Position advanced and `Video` state was playing. Audible: not verified remotely. |
| H19, H.264 + AC-3 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-008 MP4 H.264 1080p AC-3 5.1 | `original_http` off | FAIL | Recipe h264/ac3; `audioFormat` `none`, ECP `audio="none"`; passthrough inactive; position advancing. |
| H19, H.264 + E-AC-3 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-003 MKV H.264 1080p E-AC-3 5.1 | `original_http` off | FAIL | Recipe h264/eac3; `audioFormat` `none`; position advancing. |
| H19, H.264 + E-AC-3 JOC | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-018 MKV H.264 1080p E-AC-3 JOC | `original_http` off; control run as original | FAIL | Remux: `audioFormat` `none`. Control: the same file as an MKV original reported `audioFormat` `eac3` (ECP `audio="eac3"`). |
| H19, HEVC + AAC | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 MKV HEVC 2160p SDR AAC; FX-011/019/038/020/012 with audio adapted to AAC | `original_http` off | FAIL | Recipe hevc/aac; `audioFormat` `none` in every run, ECP `audio="none"`. Controls: the HEVC MKV original reported `aac`; the HLS transcode reported `aac_adts`. |
| H19, HEVC + E-AC-3 | 2026-10-22 | — | — | — | — | PENDING | No fixture has HEVC video with E-AC-3 audio. |
| H8, 4K HEVC SDR | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 MKV HEVC 2160p SDR | `original_http` off; FF | PASS | Started and reanchored; largest segment 4.3 MB; no `Video` error. |
| H8, 4K HDR10 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 MKV HEVC Main 10 2160p HDR10, DTS-HD MA (server converts audio to AAC) | `original_http` off; FF twice | PASS | Started; both reanchors adopted. Largest segment 23.5 MB (90th percentile 12.1 MB); no `Video` error. |
| H8, Dolby Vision + TrueHD | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 and FX-038 MKV HEVC Main 10 2160p DV P8.1, TrueHD Atmos (to AAC) | `original_http` off; FF twice | PARTIAL | Both started and reanchored with no `Video` error; `videoFormat` `hevc_b`. Largest segments 16.5 MB and 22.5 MB. FX-038 rebuffered 10–15 s after the second reanchor and re-fetched many segments with ranges (75 of 140 answered 206, 26 aborted). |
| H8, Dolby Vision + DTS-HD MA | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-020 (7.1) and FX-012 (5.1) MKV HEVC Main 10 2160p DV P8.1 (to AAC) | `original_http` off; FF two or three times | PARTIAL | Both started and reanchored with no `Video` error. Largest segments 11.2 MB and 17.5 MB. FX-012 rebuffered about 10 s after a reanchor and re-fetched by range (148 of 210 answered 206, 2 answered 416). No over-envelope source was found, so failure detectability is unobserved. |
| H14, external SRT, original | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 + external SRT | patched harness, PIN; native URL, then `tmp:/` copy | PASS | Both transports showed a correctly timed cue at most 1.7 s after selection, and still did after a local FF seek. |
| H14, external SRT, remux | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 + external SRT | patched harness; `original_http` off; resume at 404 s; FF | PARTIAL | Both transports were visible within 1.7 s, but cues were off by the timeline offset (404 s), as the README expects for unshifted SRT. The `tmp:/` track was rebuilt after the reanchor. Confirms the client must shift SRT cues (plan 6.8). |
| H14, embedded text, remux | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-003 MKV H.264 1080p, 87 min, embedded SRT (served as WebVTT) | patched harness; `original_http` off; FF | FAIL | First load: the WebVTT sidecar became available about 65 s after start (server-side extraction), so the `tmp:/` copy hit its 10 s deadline (`-1001`) and nothing could show within 15 s. Once cached, after a reanchor with the new `timestamp_offset`, native and `tmp:/` cues appeared 2–4 s into the new plan. Non-ASCII "♪" rendered correctly. |
| H14, embedded text, original | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-003 (cached sidecar); FX-009 24-min (first load) | patched harness; `original_http` on | PASS | Cues on both transports at most 1.7 s after selection. FX-009's first load fit within the 10 s download deadline, though playback began about 10 s after Play. |
| H14, HLS WebVTT rendition | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 transcode with embedded SRT | patched harness; HEVC and E-AC-3 off | PENDING | Plan had no sidecar (stats "none in plan"); ECP reported `captions="webvtt"` and the Roku fetched 113 rendition segments. The cues were not shown: the harness keeps `globalCaptionMode` off and cannot select the rendition, and `*` opens the TV's system Settings panel rather than caption options. |
| H14, embedded SRT, MKV original, first load | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-028 MKV H.264 1080p, embedded SRT | patched harness | PARTIAL | `tmp:/` copy `-1001` (extraction slower than 10 s). Cues were seen after a 5-min seek, but the probe logged no completed sidecar fetch, so they may have come from Roku's own MKV demux (ECP reports `captions="srt"` on MKV originals). Unconfirmed. |
| H14, ASS, remux | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-028 embedded ASS | patched harness; `original_http` off | FAIL | The plan delivered raw `.ass` and the `Video` node downloaded it (194 KB), but no cue appeared in the observed window. No `tmp:/` copy and no offset (expected until ASS conversion, plan 6.8 and S-12). |
| H14, Unicode / CJK | 2026-10-22 | — | — | — | — | PARTIAL | Non-ASCII music notes render. CJK was not tested: both tracks tagged `zh` contain English text. |

### Harness and probe defects found in this session

1. `harness.isNumber` (`source/dev/harnessPlan.bs`) does not accept `roInt`.
   Numbers read back from the Task's `request` assocarray field are boxed, so
   `start_position: 0` (the "Start: from the beginning" toggle) and
   `audio_track_index` are silently omitted. Symptom: playback resumed at the
   previous stop point in three runs with the toggle on. Adding `roInt` made
   `subtitle_track_index` reach the server; `start_position` uses the same
   path but was not re-tested.
2. The harness has no subtitle-track selector. Protocol v3 selects a subtitle
   only from the request's `subtitle_track_index` or `subtitle_track_id` and
   ignores profile preferences, so every stock-harness plan has no subtitles.
   README H14 step 1 does not work against this server.
3. After a `Video` error, the player exits to the menu ("Playback stopped.")
   within about 0.5 s, sometimes before the `failure_recovery` reply. No error
   code stays visible, and a second error is never shown, contrary to the
   README. A likely cause is the node reporting `finished` after `error`,
   which `onVideoState` treats as the end of content.
4. The harness logs nothing to the console, and the overlay shows only the
   error code and category; `errorStr` and `errorInfo` are lost. ECP
   `query/media-player` was the only source of the Roku error text.
5. Seek keys are silently ignored while a replan is in flight (one FF lost on
   a slow reanchor).
6. The HLS subtitle rendition cannot be turned on from the harness, and `*`
   on a Roku TV opens system Settings.
7. Header probe: when the Roku closes a connection mid-body (range requests,
   seeks, aborted segment downloads), the line is logged as status 502,
   action `error`, with no bytes or `ext_x_define`. Progressive originals
   always log 502, and the long-transcode playlist's `#EXT-X-DEFINE` use was
   lost.
8. The diagnostic screen reports the model as "A000X"; ECP reports "A109X".

## H2b — playlist limits

Follow-up to the H2 long-transcode failure: which media-playlist property makes
the Roku answer "mpr playlist file is too large".

- **Device:** 55R625 / 15.3.4 (build 2303), session 2026-10-22.
- **Player:** ECP URL playback is unavailable on this TV (`input/15985` and
  `launch/15985` return 404), so a throwaway channel with one `Video` node
  played a URL passed as a launch parameter. It was sideloaded over the dev
  app, outside the repository.
- **Media:** one synthetic 2 s MPEG-TS segment (H.264 720p + AAC) served for
  every entry from a static test server on the lab LAN. All playlists use
  2-second `#EXTINF` entries. Forms: plain relative URIs; URIs with a 1 KB
  `?st=` query repeated on every line (Silo's legacy signed form); the
  server's synthetic `#EXT-X-VERSION:8` + `#EXT-X-DEFINE:NAME="silo_query"`
  form; and EVENT playlists that grow on each fetch.
- **Accepted** means the `Video` node reached `play` and held it with no
  error. Because the segment repeats, playback position is not meaningful.
- **Refused** means `Video` error -3, `errorStr` `reader pick stream
  error:bad:mpr playlist file is too large.`, and ECP `error="true"` with the
  same verbose text, 0.22–0.27 s after `play`. The server log shows that the
  Roku dropped the playlist connection after reading the headers.

| Playlist form | Entries | Bytes (wire / decoded) | Delivery | Result | Observed facts |
| --- | --- | --- | --- | --- | --- |
| plain | 1,000–10,000 (7 sizes) | 31 KB–310 KB | Content-Length | PASS | All played, 2.6–3.5 s to `play`; duration complete (20,000 s at 10,000 entries). |
| 1 KB query | 1,000 / 2,000 / 3,000 / 4,000 | 1.03 / 2.06 / 3.10 / 4.13 MB | Content-Length | PASS | 3.2–3.3 s to `play`; duration complete. |
| 1 KB query | 6,000 / 10,000 | 6.19 / 10.32 MB | Content-Length | FAIL | Refused: "mpr playlist file is too large". |
| 1 KB query, exact size | 100 / 1,000 / 3,800 | 4,194,304 | Content-Length | PASS | Played at every entry count. |
| 1 KB query, exact size | 100 / 1,000 / 3,800 | 4,194,305 | Content-Length | FAIL | Refused at every entry count. Also refused: 5,000,000, 5,242,880, and 5,242,881 bytes. |
| 1 KB query | 1,000 | 4,194,305 | chunked; gzip | PASS | Played with no Content-Length, and with gzip (33 KB on the wire). |
| 1 KB query | 6,000 / 10,000 | 6.19 / 10.32 MB | chunked; gzip | PARTIAL | No error, but silently truncated: duration 8,130 s instead of 12,000 or 20,000 s. That is the 4,065 entries that start within the first 4 MiB. Stays VOD (`is_live` false) and is not refetched. |
| `#EXT-X-DEFINE` | 100 / 1,000 / 3,800 / 4,000 / 4,100 / 6,000 | 6 KB–271 KB / up to 6.19 MB expanded | Content-Length | PASS | All played, 2.9–3.5 s to `play`; duration complete (12,000 s at 6,000 entries). Segment requests carried the substituted query, never the literal `{$silo_query}`. |
| EVENT, growing 100 → 200 | 100–200 | 3 KB–6 KB | Content-Length | PASS | Refetched every 2 s (the target duration); stopped refetching after `#EXT-X-ENDLIST`. |
| EVENT, growing across 4 MiB | 3,900 → 4,300 | 4.02 → 4.44 MB | Content-Length | FAIL | Refreshes up to 4,179,700 bytes completed. From 4,231,300 bytes on, the Roku cut off every refresh, and the interval backed off from 2 s to 10 s. There was no `Video` error; playback continued on the last accepted copy, so new segments and `#EXT-X-ENDLIST` were never seen. |
| EVENT, growing across 4 MiB | 3,900 → 4,300 | 4.02 → 4.44 MB | chunked | FAIL | Every refresh completed, but polling continued every 2 s for 28 s after the server added `#EXT-X-ENDLIST`. This fits ENDLIST lying beyond the 4 MiB cut. |

**Conclusion.** The trigger is bytes. Entry count (up to 10,000) and
`#EXT-X-DEFINE` (supported, expansion not counted) are not. The Roku's media
playlist reader holds at most 4,194,304 bytes (4 MiB) of playlist text:

- If the response declares a larger `Content-Length`, the reader refuses the
  playlist with "mpr playlist file is too large".
- If the response is chunked or gzip-encoded, the reader keeps the first
  4 MiB and drops the rest without an error.

A media playlist must stay under 4 MiB, including every later EVENT refresh.
In the legacy signed form (about 1 KB per entry), that is about 4,000 two-second
segments, or about 2 h 15 min. Header-authenticated URLs or the
`#EXT-X-DEFINE` form keep feature-length playlists far below the limit.

**Open point.** The H2 long-transcode row records a 633,424-byte playlist as
refused, but a 633 KB playlist plays here. The header probe buffers each
playlist and re-sends it with its full `Content-Length`, so the Roku would
have seen the real size. The source of the 633,424 figure is not in the
session notes or probe slices, and the probe logged that request as 502 with
no size. To settle it, re-fetch the FX-011 media playlist exactly as the
harness requested it, with its signed query, and measure the body. In the
legacy form, 127 minutes of 2-second segments comes to about 4.0–4.2 MB, which
is at the limit.

## Run 2 — TS copy remux prototype

Second hardware round on the same TV, against the lab stack running the
silo-server prototype branch `roku/client-support` (assumption AG-35):
delivery feature `hls_copy_mpegts_v1` (harness toggle "TS copy remux") and the
admin setting `playback.copy_keyframe_playlist` on. "No playlist variables"
stayed off. Run IDs continue from run 1.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers.
  `IsPassthruCodecActive()` was false in every run. Audio could not be heard
  remotely, so audibility is never claimed.
- **Harness:** `npm run sideload:dev` build of `c339d98`, unmodified; no-PIN
  profile; `original_http` off; "Start: from the beginning". "TS" means TS copy
  remux on; "fMP4" means it was off. The overlay showed
  "Prototype features: hls_copy_mpegts_v1" whenever it was on.
- **Probe:** the repository build (`playlist_entries`, `ext_x_define`).
  2,146 playlist and segment requests, all carrying `Authorization` and
  `X-Profile-Id`. No playlist used `#EXT-X-DEFINE`, and no segment had
  `duplicate_query_keys`.
- **Packaging check:** the lab transcode node's ffmpeg commands show
  `-hls_segment_type mpegts` (`.ts`) with TS and `fmp4` (`.m4s`) without it.
  ECP cannot tell them apart: both report `container="hls"` and
  `segment_type="mux"`.
- **Seeks:** in every run, Left (−30 s, inside the played range) and Fast
  Forward were both sent as `seek_reanchor`. The plan carried
  `can_seek_anywhere` false and a seek window that did not cover the played
  range, even with a complete playlist. Every reanchor was adopted.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H19, H.264 + AAC, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 H.264 1080p AAC (R29) | TS | PARTIAL | `audioFormat` `aac_adts` from start, ECP `audio="aac_adts"`. Position advanced (22.6 → 45.1 s). Left and FF reanchors were adopted, and `audioFormat` stayed set after them. 123 segments, largest 1.15 MB, no `Video` error. Only audibility is unconfirmed. |
| H19, H.264 + AC-3, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-008 MP4 H.264 1080p AC-3 5.1 (R31) | TS | PARTIAL | `audioFormat` `ac3`, ECP `audio="ac3"`, before and after two reanchors. Position advancing; largest segment 11.4 MB. Audibility unconfirmed. |
| H19, H.264 + E-AC-3, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-003 MKV H.264 1080p E-AC-3 5.1 (R33, R35) | TS | PARTIAL | `audioFormat` `eac3`, ECP `audio="eac3"`, through three reanchors. Position advancing. Audibility unconfirmed. |
| H19, H.264 + E-AC-3 JOC, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-018 MKV H.264 1080p E-AC-3 JOC (R36) | TS | PARTIAL | `audioFormat` `eac3` (JOC is not distinguished, as with the original in run 1), ECP `audio="eac3"`, before and after two reanchors. Audibility and Atmos rendering unconfirmed. |
| H19, HEVC + AAC, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 MKV HEVC 2160p SDR AAC (R38) | TS | PARTIAL | `videoFormat` `hevc_b`, `audioFormat` `aac_adts`, before and after two reanchors; largest segment 4.4 MB. The DV and HDR10 4K remuxes below also reported `aac_adts` under TS. Audibility unconfirmed. |
| H19, same files as fMP4 | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC, FX-008, FX-003, FX-018, FX-009 (R30, R32, R34, R37, R39); FX-019 (R46, R48) | fMP4 | FAIL | `audioFormat` `none` and ECP `audio="none"` in every run, as in run 1. Video played and the position advanced. |
| H19, HEVC + E-AC-3 | 2026-10-22 | — | — | — | — | PENDING | Still no fixture with HEVC video and E-AC-3 audio. |
| H3 (partial), DV P8.1 + TrueHD, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 and FX-038 MKV HEVC Main 10 2160p DV P8.1, TrueHD Atmos (R40–R42, R45, R54) | TS | PARTIAL | Start body, per the installed harness source (the harness does not log it): `dolby_vision_profiles: []` in every `hdr_details` (capabilities, output, display), `hdr10` and `hlg` true, no `validated_claims`. Plan: `server_remux_hls`, `hls_audio_adaptation`, recipe hevc/aac. The harness does not log `effective_recipe.dynamic_range`; the server's plan log line says `dv_profile=8 dynamic_range=dolby_vision`, while its ffmpeg command strips the RPU (`dovi_rpu=strip=1`, `filter_units=remove_types=63`). `videoFormat` `hevc_b`. The TV's Picture settings showed Picture mode "Dark" with an HDR badge and no Dolby Vision indication: HDR10, not DV. |
| H3 (partial), DV P8.1 + TrueHD, fMP4 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 (R46) | fMP4 | PARTIAL | Same plan, `hevc_b`, Picture mode "Dark" with the HDR badge. `GetVideoMode()` during playback is not observable with the harness. |
| H3 (partial), DV P8.1 + DTS-HD MA, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-020 (7.1) and FX-012 (5.1) MKV HEVC Main 10 2160p DV P8.1 (R43, R44) | TS | PARTIAL | Plan and server log as for TrueHD (RPU stripped, audio to AAC); `hevc_b`. Picture mode not checked on these two. |
| H2, keyframe playlists, copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-003 87 min, FX-038 95 min, FX-019 110 min, FX-018 119 min (MKV) | TS (and fMP4 for comparison) | PASS | Complete on first fetch (`#EXT-X-ENDLIST`, ECP `is_live` false, full duration), fetched once, and played. FX-003 1,283,714 B / 1,203 entries (fMP4 1,266,715). FX-038 3,347,187 B / 2,851. FX-019 **3,946,913 B** / 3,289 (fMP4 3,898,757). FX-018 **3,749,030 B** / 3,567 (fMP4 3,696,555). Bold sizes are at or above 3.5 MB. |
| H2, keyframe playlists over 4 MiB | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-012 116 min, FX-020 124 min, FX-011 127 min (MKV HEVC 2160p) (R53, R52, R55) | TS | FAIL | Complete playlists of **4,253,513 B** / 3,475, **4,494,053 B** / 3,714, and **4,220,333 B** / 3,802 entries. The Roku refused each: `Video` error −3, "mpr playlist file is too large." The `failure_recovery` replan (`copy_routes_exhausted`) moved to a transcode whose playlist was also refused (6,102,213, 6,468,159, and 6,334,245 B), so the start failed. FX-011 had played on its first two plays (R49, R50), when it got EVENT playlists. |
| H2, first play and reanchored plans | 2026-10-22 | 55R625 / 15.3.4 | TV | first plays of FX-003, FX-038, FX-020, FX-012, FX-011; every reanchored plan | TS and fMP4 | PASS | Without a finished keyframe index, and after any reanchor, the plan is an EVENT playlist (`is_live` true). The server pauses the remux about 300 s ahead, so the 4K playlists level off at about 150–215 entries (≤ 263 KB); 1080p ones reached 300–1,164 entries (≤ 1.27 MB). All are re-polled every 2–5 s. FX-011 needed three plays before its complete playlist appeared. |
| H2, long transcode | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 MKV HEVC Main 10 2160p HDR10, 127 min (R51) | HEVC and E-AC-3 off | FAIL | Transcode playlist **6,334,245 B**, 3,802 entries, no `#EXT-X-DEFINE` (about 1.67 KB per entry). Refused ("mpr playlist file is too large"); `failure_recovery` answered `adaptation_exhausted`. This settles the H2b open point: the run 1 refusal was this 6.3 MB playlist. The 633,424 figure is probably the same number with one digit dropped. |
| H8, highest-bitrate 4K remux, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 MKV HEVC Main 10 2160p DV P8.1, 55.5 Mb/s (R41) | TS; FF twice | PARTIAL | Started and both reanchors adopted, with no `Video` error and no recovery. The start plan (complete playlist) played smoothly: 25 of 26 segments whole, largest 13.9 MB. The two reanchored (EVENT) plans re-fetched by byte range (40 of 49 and 104 of 123 requests answered 206; 10 and 14 aborted) and rebuffered three and four times. The longest stall was about 45 s at a position 18 s into the second reanchored plan (ECP buffer frozen at 241/1000); it then recovered. That stall is longer than H8's 20 s hang threshold. Largest whole segment 18.8 MB. |
| H8, same file as fMP4 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 (R48) | fMP4; FF twice | PARTIAL | Start plan smooth (largest 13.6 MB). Reanchored plans also mostly ranged (30 of 41, 25 of 40) but rebuffered once each, for under 20 s. One run per packaging: TS rebuffered more here, which is suggestive but not established. |
| H8, other 4K remuxes, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-038, FX-012, FX-020 DV P8.1; FX-011 HDR10 40.5 Mb/s (R42–R44, R49, R54) | TS; one or two FFs | PARTIAL | All started and reanchored with no `Video` error. FX-038 and FX-012 rebuffered in every plan, with most segment requests ranged (60 of 65, 81 of 87, 33 of 48, 33 of 50). R54 shows the trigger on a complete playlist: the Roku aborted a 17.2 MB segment, then fetched the rest by range while buffering. FX-011 played without rebuffering, with a 24.0 MB segment fetched whole: the largest segment that played. |
| H8, stall with the system overlay | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 (R40) | TS | PARTIAL | After the TV's Settings overlay was opened twice during playback, the Roku re-fetched by range and then stalled in `buffering` for over 60 s with no segment requests and no `Video` error. It only polled the unchanged EVENT playlist, and Back ended the run. Both overlay openings were followed within seconds by range re-fetches. It did not recur without the overlay (R41), so it is recorded separately. |

### Run 2 conclusions

- **TS fixes H19's decoder criterion on this TV.** Every codec pair reported
  a real `audioFormat` under TS (`aac_adts`, `ac3`, `eac3`), and every one was
  `none` as fMP4. Audibility still needs a listener in the room.
- **Dolby Vision is not engaged.** The harness claims no DV, the server
  strips the RPU on copy, and the TV shows HDR10 for both packagings. The
  server's plan log still labels these plans `dynamic_range=dolby_vision`.
  Whether the plan body says the same is unconfirmed.
- **Complete keyframe playlists break long 4K titles.** With audio
  adaptation they cost about 1.2 KB per entry, so 2-second segments cross
  4 MiB after about 114 minutes (3,426 entries). Pure copies cost about 1.05 KB
  per entry and allow about 2 h 13 min. TS adds 14–15 B per entry over fMP4.
  Three of the seven long MKVs became unplayable once their index was ready.
  The transcode fallback, at about 1.7 KB per entry, is over 4 MiB for every
  title longer than about 80 minutes. AG-35's estimate of about 1 KB per entry
  for transcode playlists is low.
- **The largest segment that played is 24.0 MB (FX-011).** Rebuffering tracks
  range re-fetching of 13–19 MB DV segments, mostly in EVENT (reanchored or
  first-play) plans, not segment size alone.

### Harness and server-prototype defects found in run 2

1. Harness: the console and overlay show neither the plan's
   `effective_recipe.dynamic_range` and claims, nor `GetVideoMode()` during
   playback. H3 had to rely on the server log and the TV's Picture settings.
2. Harness: after a fatal error and a failed recovery, Fast Forward still
   makes a "local seek" on the errored node, which raises a second error
   ("Player cannot recover after a fatal error"). The node still reports
   `finished` after `error` (run 1 defect 3).
3. Harness: connection, sign-in, and toggles are lost when the app exits.
   On the menu, Back closes the harness and a second Back exits the app.
4. Harness and server: seek windows. The harness keeps the seek window from
   the start reply. The server reports `can_seek_anywhere` false, with a window
   that excludes already-played time, even for complete keyframe playlists. A
   30-second backward seek therefore always reanchors.
5. Server prototype: complete keyframe playlists are not kept under 4 MiB
   and use no `#EXT-X-DEFINE` compaction. The transcode fallback is larger
   still (S-22).
6. Server prototype: keyframe playlists exist only for start plans, once
   the index is ready, so the same title gives different playlists from play
   to play. FX-011 played as EVENT twice, then failed once complete.
7. Server prototype: the plan log reports `dynamic_range=dolby_vision` for
   streams whose RPU is stripped, for a client that claims no Dolby Vision.
8. Tooling: an ECP screenshot closes the TV's system overlay, so a key sent
   after a screenshot reaches the app. Reconnecting the debug console replays
   the Roku's buffered log.

## Run 3 — playlist compaction

Third hardware round on the same TV, against the lab stack running the
silo-server prototype branch `roku/client-support` at `1e51649a9` (S-22): every
v3 HLS media playlist uses `#EXT-X-DEFINE` compaction, complete keyframe
playlists carry a closed seek window, and the Dolby Vision plan log line reports
the delivered range. `hls_copy_mpegts_v1` and `playback.copy_keyframe_playlist`
are as in run 2. Run IDs continue from run 2.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers.
  Audio could not be heard remotely, so audibility is never claimed.
- **Harness:** `npm run sideload:dev` build of `c339d98`, the run 2 build,
  unmodified, so the client is the same as in run 2. The branch head (`3f55168`)
  could not be used: it never leaves the splash screen (see "Defects found in
  run 3"). No-PIN profile; `original_http` off; TS copy remux on unless stated;
  "Start: from the beginning"; "No playlist variables" off.
- **Files:** FX-011, FX-012, FX-019, and FX-020 each have three file versions in
  the lab library, and the harness defaults to the first. Every run used the
  corpus fixture file except R56, which played FX-011's library copy (same
  title, separate file) by default.
- **Server state:** the lab server restarted for the new build about 20 minutes
  before the session. FX-011, FX-012, and FX-020 already had keyframe indexes;
  FX-019 did not.
- **Probe:** the repository build, unchanged. 1,755 playlist and segment
  requests, all carrying `Authorization` and `X-Profile-Id` and none
  `X-Profile-Token`. Every playlist response with a body used `#EXT-X-DEFINE`.
  No segment had `duplicate_query_keys`, and nothing reached the foreign
  listener.
- **Timing:** resume times are measured from the seek key to the first ECP
  `query/media-player` poll showing `play` at the new position. Polls ran about
  once a second, so resume times are accurate to ±1.5 s. Rebuffer durations
  come from the harness's `Video` state lines, timestamped as they were
  captured.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S-22 / H2, keyframe playlists over 4 MiB in run 2 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 127 min HDR10 (R57), FX-012 116 min DV P8.1 (R58), FX-020 124 min DV P8.1 (R59), MKV HEVC 2160p | TS | PASS | Complete on first fetch, in `#EXT-X-DEFINE` form: **202,730 B** / 3,802 entries, **185,513 B** / 3,475, and **198,166 B** / 3,714. In run 2 they were 4,220,333, 4,253,513, and 4,494,053 B, and all were refused. Each was fetched once and played; ECP `is_live` false, with the full duration (7,603 s, 6,949 s, 7,427 s). About 53 B per entry. |
| S-22 / H2, long transcode | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 MKV HEVC Main 10 2160p HDR10, 127 min (R60) | HEVC and E-AC-3 off | PASS | `server_transcode_hls`, recipe h264/aac, 1080p tone-mapped to SDR. Playlist **203,286 B** / 3,802 entries with `#EXT-X-DEFINE` (run 2: 6,334,245 B, refused). Played with `is_live` false and full duration; `can_seek_anywhere` true. |
| S-22 / H2, keyframe playlist under 4 MiB in run 2 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 MKV HEVC 2160p DV P8.1, 110 min (R63) | TS | PASS | 175,631 B / 3,289 entries (run 2: 3,946,913 B). Played. |
| S-22, EVENT playlists | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 library copy, first play (R56); FX-019, first and second play after the server restart (R61, R62) | TS | PASS | With no keyframe index, the start plan is still an EVENT playlist (`is_live` true), now compacted: first fetch 1,455–1,531 B / 3 entries, growing to at most 230 entries and 13.6 KB. Every seek reanchored (8 in R56, 1 and 2 in R61 and R62), and R56's reanchors resumed 4.0–6.7 s after the key. FX-019 got its complete playlist on the third play. |
| Seek window, complete playlists | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011, FX-012, FX-020 (R57–R59); FX-011 transcode (R60); FX-019 (R63) | TS; transcode | PASS | All 26 seeks were local (Left −30 s, Right +30 s, Rew and FF ±5 min); none sent `seek_reanchor`. The copy plans still report `can_seek_anywhere` false, so the seek window made them local. The 30 s backward seek, a reanchor in every run 2 plan, resumed in 2.8–3.3 s (R57, R59). Copy remux resumes: Right 1.1 s (FX-020) and 11.5 s (FX-012); FF 3.5–14.8 s; Rew 3.4–10.0 s. Two seeks were still buffering when the next key came. R57's Right landed on FX-011's 24.0 MB segment, which the Roku aborted and re-fetched by range (over 13.6 s). R58's Left to 0 s buffered over 14.2 s. Transcode seeks resumed within 1–4 s. |
| Seek window, far forward | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-012 (R58); FX-011 (R57) | TS; chained FF | PARTIAL | The harness cannot make one +20 min jump: FF seeks 5 min from `Video.position`, which does not change until a local seek completes, so quick presses do not add up (R57: four presses gave targets 408, 708, 708, and 708 s). R58 instead sent four FFs, each once the previous one was playing: 100 → 401 → 702 → 1,003 → 1,304 s. All four were local and resumed after 14.8, 15.2, 20.7, and 15.0 s. For the third and fourth, the segment was ahead of FFmpeg. The server waited (`transcode segment wait`, `planned_segment_ahead`, timeout 30 s), served it about 4–5 s later, and did not restart FFmpeg. The Roku buffering range-fetched 4K segments accounts for the rest of each wait. A single jump far beyond FFmpeg's head was not tested. |
| H8, Dolby Vision + TrueHD, EVENT plans, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 MKV HEVC Main 10 2160p DV P8.1, 55.5 Mb/s (R61, R62) | TS; FF twice | PARTIAL | Every reanchor was adopted, with no `Video` error. Reanchored plans re-fetched by range as in run 2 (118 of 141, 44 of 65, and 34 of 52 segment requests answered 206). Rebuffers: R61 12.8 s, **20.7 s**, and at least 5.8 s (to stop); R62 4.1, 5.6, and 9.8 s in the first reanchored plan, then 10.6 s and at least 7.0 s in the second. The 20.7 s stall is over H8's 20 s hang threshold; run 2's longest (R41) was about 45 s. R61's second FF produced no harness log and no seek. |
| H8, Dolby Vision + TrueHD, complete playlist, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 (R63) | TS; FF twice (local) | PARTIAL | Both FFs were local and resumed after 4.4 s and 14.7 s. Between the two, the player rebuffered for 1.6 s and **20.2 s**. 56 of 115 segment requests answered 206 and 18 were aborted; the largest whole segment was 18.5 MB. Range re-fetching also happens with complete playlists, so it is not specific to EVENT plans. |
| H19 sanity, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011, FX-012, FX-020, FX-019 (R56–R59, R61–R63) | TS | PARTIAL | `audioFormat` `aac_adts`, ECP `audio="aac_adts"`, and `videoFormat` `hevc_b` in every TS copy remux, as in run 2. The transcode (R60) reported `aac_adts` and `mpeg4_10b`. Audibility unconfirmed. |

### Run 3 conclusions

- **S-22 fixes the long-title failures on this TV.** The three complete
  playlists the Roku refused in run 2, and the transcode fallback, are now
  175–204 KB and play. At about 53 B per entry, a media playlist reaches
  4 MiB only at about 78,000 two-second segments (about 43 hours).
- **Complete playlists make every seek local.** The −30 s seek that always
  reanchored in run 2 now resumes in about 3 s. Reanchoring remains for EVENT
  plans, which a title still gets until its keyframe index exists. The index
  did not survive the server restart: FX-019 needed three plays again (run 2
  defect 6).
- **Far seeks wait for FFmpeg instead of restarting it.** The server holds a
  segment request ahead of the produced head for up to 30 s. In R58 a copy
  remux caught up within about 5 s.
- **H8 rebuffering is unchanged.** Stalls of about 20 s still occur on
  55.5 Mb/s Dolby Vision copies. They follow the Roku's range re-fetching of
  large segments, with complete playlists as well as with EVENT playlists.
- **The plan log now reports the delivered range.** It reads
  `dv_profile=8 dynamic_range=hdr10 source_dynamic_range=dolby_vision` for the
  Dolby Vision copies, which fixes run 2 defect 7. The transcode logs `sdr`.

### Defects found in run 3

1. Client, since `3a7889c` (M0-7) and still at `3f55168`: `Main` calls
   `scene.callFunc("apiStart", snapshot)` before `screen.show()`. On this TV
   that call never returns. The app stays on the splash screen, ECP shows no
   scene, and on exit the console prints `roSGNode.CallFunc: Rendezvous aborted
   for Scene: pkg:/source/main.brs(11)`. Bisect: `c339d98` launches; `3a5cbde`,
   `59a41d4`, and `3f55168` hang. `3f55168` with `screen.show()` moved first
   launches to the server setup placeholder. Headless tests cannot catch this.
2. Harness: quick FF or Rew presses during a local seek do not add up, because
   `seekBy` counts from `Video.position`, which does not change until the seek
   completes. Only seeks queued behind a replan add up.
3. Harness: in R61, a second FF during playback had no effect and logged
   nothing (no local seek, no replan, no queued seek). Whether the key arrived
   is unconfirmed.
4. Harness: after choosing the PIN profile, pressing Back on its PIN pad left
   that profile selected ("Profile … selected"), and no `verify-pin` request
   was made. Whether the server accepts that profile's requests without
   `X-Profile-Token` was not tested.
5. Server prototype: the transcode node restarts FFmpeg too often. In R60 it
   logged 26 `transcode node seek restart` lines in 2.5 minutes, and the Roku
   received 20 segment 404s and 3 410s. Two triggers appear in the log.
   `request_beyond_produced_window` fired when the Roku's normal 2–3-segment
   lookahead ran ahead of the transcoder, during plain playback too.
   `before_start_segment` fired when the requests for skipped segments came
   back after their 12 s waits timed out. The restart positions oscillated
   (`-ss` 66, 72, 66, 70, 88, 66 …). Playback and seeks still worked.
6. Server prototype: keyframe indexes are lost when the server restarts
   (run 2 defect 6 persists).
7. Run 2 defect 4 is fixed for complete playlists. The window now covers the
   played range, though copy plans still report `can_seek_anywhere` false.

## Run 4 — production app

First hardware pass of the production client (setup, sign-in, profiles, PIN,
the production `Player` through the dev build's Up entry, deep links, and
launch timing) on the same TV, against the lab stack on silo-server
`roku/client-support` at `a6cb3b4df` (`request_origin` in `system/info`,
`hls_copy_mpegts_v1`, `#EXT-X-DEFINE` compaction, complete keyframe
playlists). Run IDs continue from run 3 (R64–R87).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could
  not be heard remotely, so audibility is never claimed.
- **Builds:** `f047ac4`. The stock dev build could not get past server entry
  (defect 1 below), so every row after "Onboarding, stock build" used that dev
  build plus an uncommitted scratch patch, built outside the checkout: the
  onboarding screens and `KeyboardPanel` release focus from the focused
  descendant before taking it, the player's `Video` node sets
  `enableTrickPlay="false"`, and diagnostic prints of keys and plan timelines.
  Launch timing used the unpatched release build. The stock dev build was
  reinstalled at the end.
- **Profiles:** "no-PIN" for playback and deep links; "PIN" for onboarding.
- **Start positions:** "Start over" unless stated; "resume" is the test
  entry's Resume (the server position minus 7 s).
- **Positions** come from ECP `query/media-player`; stored positions from the
  watch projection's `user_data.position_seconds` after the stop; operations
  (`startPlayback`, `replanPlayback`, `updatePlaybackProgress`,
  `stopPlayback`) from the lab server's request log.
- **Probe:** 1,036 `stream`, `playlist`, `segment`, and `subtitle` requests,
  all with `Authorization` and `X-Profile-Id`; nothing reached the foreign
  listener. Every playlist body but one used `#EXT-X-DEFINE` (largest
  155,840 B). Largest segment 28.1 MB. 52 segment 404s; the ones checked
  against the server log fell during reanchor replans (defect 10).
- **Packaging:** all 50 HLS FFmpeg jobs in the session used
  `-hls_segment_type mpegts`.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Onboarding, stock build | 2026-10-22 | 55R625 / 15.3.4 | — | — | stock dev build, fresh install | FAIL | After the server address was typed and the keyboard closed (Play, or Down to Done), OK on Connect did nothing: no request, no dialog. `query/sgnodes/all` showed `KeyboardPanel visible="false"` with its `DynamicKeyGrid` still focused, so every key went to the hidden keyboard. A diagnostic print right after `m.top.setFocus(true)` in `ServerScreen.onKeyboardClosed` read `screenHasFocus=false panelInChain=true`. The profile picker has the same fault: Down highlights Change server, but the `MarkupGrid` keeps focus and Right moves to the next profile, so Change server and Sign out cannot be reached. |
| Onboarding, patched | 2026-10-22 | 55R625 / 15.3.4 | — | — | scratch patch; PIN profile | PASS | Host typed without a scheme: HTTPS failed in 354 ms (TLS error), then "Connect without encryption?" named host and port; HTTP `system/info` 200, then sign-in. A wrong password got 401 and "Invalid username or password" with the password cleared; the right one opened "Who's watching?" with Change server and Sign out. A wrong PIN showed four red dots and "Wrong PIN. Try again."; the right one opened Home. Relaunch went straight to Home with no dialog (`AppLaunchComplete` 425 ms). The focused avatar's ring is clipped along its top and left edges. |
| Onboarding, dialog beacons | 2026-10-22 | 55R625 / 15.3.4 | — | — | scratch patch; one launch: sign-in, picker, PIN | FAIL | The first `AppDialogInitiate` was accepted (TimeBase 303 ms). The picker's was refused: `roSGNode.signalBeacon: "AppDialogInitiate": already signaled`. Both `AppDialogComplete`s were accepted, each timed from the first Initiate (27,945 and 41,084 ms). `AppLaunchComplete`: Duration 41,531 ms with DialogTime 69,029 ms, longer than the launch itself. One `AppLaunchComplete` per launch. The first launch (server, then sign-in) showed the same refusal. |
| Credential-origin gate | 2026-10-22 | 55R625 / 15.3.4 | — | — | scratch patch | PASS | At setup and on every launch, the first request was `GET system/info` with no credential headers (probe), and credentialed requests followed only after its 200. No `origin_unconfirmed` warning. Through the probe, `request_origin` equals the configured origin. Mismatch and absent-field paths: specs only (the backend address is not reachable from the TV). |
| M0a original, H.264 + AAC, MP4, stock build | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 H.264 1080p AAC 2.0 (R64) | stock dev build | FAIL | Plan and start as in the next row. Right put the `Video` node into its own trick play: ECP `state="pause"` with the position frozen at 40.6 s through FF, Left, and Rew. The player's key handler never ran. Play resumed at 2.7 s. The position stored after the stop was 356.9 s; the true position was about 42 s. |
| M0a original, H.264 + AAC, MP4 | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC (R65, R66) | scratch patch | PASS | `original_http` (`validated_original_playback`), mp4, h264/aac 2.0, `sdr`; `videoFormat` `mpeg4_15`, `audioFormat` `aac`; `VODStartComplete` 2.4 s. Local seeks (Right +30 s, FF +300 s, Left −10 s, Rew −300 s) each played again within about 1 s. 8 progress posts in 80 s. Stop at 88.7 s stored 89.2 s. Resume started at about 82.2 s. |
| M0a original, HEVC Main SDR + AAC, MKV | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-009 2160p (R67, R68) | scratch patch | PARTIAL | `original_http`, mkv, hevc/aac; `videoFormat` `hevc`, `audioFormat` `aac`. Right +30 s local in under 9 s. FF after it buffered more than 20 s at the target while the Roku read two 80 MB ranges. The client then replanned to `server_remux_hls` (`hls_packaging_required`, offset 337.5 s), and the new content was assigned 686 ms after the stop. A second run's FF alone played within 5 s. Resume correct. |
| M0a originals, H.264 with AAC, AC-3, E-AC-3, E-AC-3 JOC | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001 MKV AAC (R69), FX-008 MP4 AC-3 5.1 (R70), FX-003 MKV E-AC-3 5.1 (R71), FX-018 MKV E-AC-3 JOC (R72) | scratch patch | PASS | All `original_http`; the production app has no "original off" toggle, so the server chose originals for every H.264 fixture and no H.264 copy remux ran. `audioFormat` `aac`, `ac3`, `eac3`, `eac3`; VODStart 1.9–4.3 s. Right and FF were local. FX-003's FF was still buffering 13 s later; the others were playing at the target by the next poll (12–19 s). Stored positions were within 1 s of the stop. Resume reopened 7 s back. |
| M0a copy remux, HEVC Main 10 HDR10 | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 127 min (R73) | scratch patch | PASS | `server_remux_hls` (`hls_packaging_required`), hevc/ac3 2.0 (the AC-3 track, not DTS-HD MA), `hdr10`; `hevc_b`/`ac3`; EVENT playlist. Right, FF, and Left were each a `seek_reanchor` (replans 5.0, 0.2, and 0.2 s on the server). During the first, the playing node hit segment 404s and reported `Video` error −5; the client stayed on the reanchored plan (defect 10). Stored 380.3 s; resume offset 372.8 s. |
| M0a copy remux, Dolby Vision P8.1 sources | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 (R75), FX-020 (R76), FX-038 (R77), MKV HEVC Main 10 2160p | scratch patch | PARTIAL | `server_remux_hls`, hevc/ac3 (5.1, 2.0, 5.1), `dynamic_range` `hdr10`, Dolby Vision not claimed; `hevc_b`/`ac3`. Seek windows had no end, so every seek reanchored, and new content was assigned 0.84–1.0 s after the stop. FX-019's Right repeated the −5 / 404 race. FX-038 buffered for over 20 s after Left (H8). Stored positions and resume correct. |
| M0a copy remux, HEVC + AAC (audio adapted) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-012 DV P8.1, DTS-HD MA 5.1, 116 min (R74) | scratch patch | PARTIAL | `server_remux_hls` (`hls_audio_adaptation`), hevc/aac 6 ch, `hdr10`; `hevc_b`/`aac_adts`. `VODStartComplete` 8.5 s. All three seeks reanchored; buffered over 18 s after Left. Stored 352.1 s; resume offset 344.8 s. |
| M0a transcode | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-038 with an image subtitle selected (R80, R81) | scratch patch | PASS | Choosing the image subtitle with Down gave `server_transcode_hls` (`subtitle_burn_in_required`), h264/aac 6 ch, `sdr`, `can_seek_anywhere` true; `mpeg4_10b`/`aac_adts`. Right +30 s and FF +300 s were local and played within 3–4 s. Stored 413.7 s. Choosing a text track next gave another transcode with `quality_bandwidth_limit`, which the client did not explain. |
| H2, long titles | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-011 127 min, FX-012 116 min, FX-020 124 min; FX-038 95 min | scratch patch | PASS | All started and reanchored. FX-038 later got a complete playlist (`seek_window_end_seconds` 5702.57, `is_live` false), on which seeks were local. Largest playlist 155,840 B. |
| H14, external SRT, original | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT (R78) | scratch patch; Down | PARTIAL | Cues showed at the right times (0:20, 1:30, and 7:20, and 9:30 after a +30 s local seek). Choosing the track is a `track_change` replan and a content reload: playback came back 2.9, 5.0, and 7.6 s after Down, with "Buffering" between. Cues show only once playing, so the 5 s criterion held in 1 of 3 tries. |
| H14, embedded text, original | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-003 embedded SRT (R79, R82) | scratch patch; Down | PARTIAL | The server served the cached WebVTT sidecar (104 KB) in 44 ms; playback came back 7.5 s after Down. Cues were visible, including "♪", and again after a +30 s local seek. Not checked against a cue reference; first-load extraction was not retested. |
| H14, text after a reanchor | 2026-10-22 | — | — | — | — | PENDING | No EVENT remux with a text track in this lab state: the text-track fixtures play as originals, and FX-038 now has a complete playlist. |
| H14, HLS WebVTT rendition | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-038 transcode, embedded text track (R80) | scratch patch | PARTIAL | ECP `captions="webvtt"` with captions On. Cue display was not checked (the chosen track's script renders as boxes, A-17). |
| Theme check | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build, Fast Forward | PASS | The Inter Tabular timecode row renders every digit. The screen measures `1:11:11` and `0:00:00` at 92 px each (proportional row: 71 and 101 px). |
| Memory check | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build, Rewind (R83) | FAIL | The check reached 22 blocks of 23 MB (510 MB, 86% of the 593,920 KB limit by its own count), held them, and released them. `GetMemoryLimitPercent()` read 2% throughout, the level stayed `normal`, and no memory event arrived, so trim, pressure, and critical were never seen. At launch `GetGeneralMemoryLevel` reported `normal` and memory warnings were enabled. No 15.3 warning fired, so its payload is unrecorded. |
| Navigation check | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build (R84, R85) | PASS | OK ×5, Play, then Back ×6 returned to Home, and one more Back exited to Roku Home. With the player on top, the stack held Home plus three screens. Play now opens the real player, which shows "Nothing to play". `sgnodes` count: 27 at Home, +5 per detail, 27 after 20 push/pop cycles (0%). |
| M1 deep links, signed in | 2026-10-22 | 55R625 / 15.3.4 | — | movie (SYNTHETIC), episode, series, season | scratch patch; `device-check.sh --deeplinks` with a 202 fix (R86) | PASS | Movie, episode, series, and season, by `launch` and by `input`, all reached a first frame with `startPositionRule` resume. Launch-time `AppLaunchComplete` came 3.96–4.70 s after launch; input rows 1.30–1.55 s. Made-up ID: `deeplink: dropped {"reason":"inaccessible"}` after two 404s, and the app stayed on Home. |
| M1 deep link, signed out | 2026-10-22 | 55R625 / 15.3.4 | — | movie (SYNTHETIC) | scratch patch (R87) | PASS | Signed out through the picker, then launched with a movie link. Sign-in showed, and the link was kept (`valid`). After sign-in the picker was skipped (no-PIN profile), and the movie resumed at 589 s. One `AppLaunchComplete` (34.5 s, DialogTime 31.2 s). |
| M1 cold launch, release | 2026-10-22 | 55R625 / 15.3.4 | — | — | release build, restored session, no-PIN remembered; 10 launches, no reboot | PASS | Median 1.35 s, max 1.38 s from `AppLaunchInitiate` to `AppLaunchComplete` (Roku's value: median 0.48 s, max 0.50 s). No dialog beacons; one `AppLaunchComplete` per launch. The exit beacon reports list `AppLaunchInitiate … InstantOn` and `AppLaunchComplete … Pended without Render`, although the live signal printed a duration. |

### Defects found in run 4

1. **Client, blocking:** on this TV, `setFocus(true)` on a node whose
   descendant has focus does nothing. `ServerScreen` and `SignInScreen`
   (after the keyboard closes), `KeyboardPanel` (Down to its actions),
   `ProfileScreen` (Down to the buttons), and `PinScreen` (Down to Cancel) all
   rely on it. Server entry cannot reach Connect, so onboarding cannot finish
   on the stock build. The scratch fix walks `focusedChild` to the focused
   node and calls `setFocus(false)` on it first; that fixed every screen.
2. **Client:** the player's `Video` node (`enableUI="false"`) keeps Roku's
   built-in trick play. It takes Left, Right, FF, and Rew, pauses, and scrubs
   invisibly, so the player's seek and reanchor logic never runs. The stored
   position then came out wrong. `enableTrickPlay="false"` fixed it.
3. **Client:** Roku OS 15.3.4 accepts one `AppDialogInitiate` per launch.
   Later waits log "already signaled", every `AppDialogComplete` is timed from
   the first Initiate, and DialogTime is overcounted (69.0 s against a 41.5 s
   launch).
4. **Client:** the player timecode separator `/` is not in the Inter Tabular
   subset (`scripts/subset-fonts.sh`), so it renders as a box ("0:23 ▯ 22:00").
5. **Client:** the focused profile avatar's ring is clipped at its top and
   left.
6. **Client:** choosing a subtitle reloads the content (replan, stop, sidecar
   grace, buffer), so cues appear 3–8 s after Down. That fails the 5 s
   criterion even when the sidecar is cached.
7. **Client:** the memory check's string allocations do not move
   `GetMemoryLimitPercent()`, so it cannot drive the memory levels on this TV.
8. **Client (dev only):** on the diagnostic Home the help lines overlap, the
   development line runs off the right edge and says "Down test player" (Up
   opens it), and the model still reads "A000X".
9. **Client:** Roku's global caption mode stays On after playback ends, so the
   next title starts with the TV's captions on.
10. **Server prototype:** a `seek_reanchor` replan tears down the old
    remux when it arrives, so the still-playing node's segment requests get
    404s. That raised `Video` error −5 twice before the new plan applied.
11. **Server or Roku:** one far seek on a 4K HEVC MKV original stalled for over
    20 s while the Roku read 80 MB ranges; another on the same file took 5 s.
12. **Tooling:** `scripts/device-check.sh` treats ECP `exit-app` HTTP 202 (what
    15.3.4 answers) as a failure and stops. The debug console accepts one
    connection, so a running `npm run console` makes the device check fail.
    `ROKU_IDLE_CHECK` in `.env` needs `\$HOME` so that `HOME` expands on the
    relay, not locally.

## Run 5 — run-4 fixes and Milestone 2 screens

Fifth hardware pass on the same TV: the run-4 client fixes, the Milestone 2
screens (Home, Library, Search, Detail) on lab data, stability, playback
follow-ups, deep links, and launch timing. Lab stack on silo-server
`roku/client-support` at `2ba0b978b` (AG-58: `silo_transport` generations and
read-ahead waits). Run IDs continue from run 4 (R88–R92).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could not
  be heard remotely, so audibility is never claimed.
- **Builds:** `80352e3`, stock, from `npm run build:dev` and `npm run build`; no
  scratch patch. The dev build was installed fresh (installer Delete, then
  sideload) for onboarding, the release build for the cold launches, and the
  dev build again at the end.
- **Profiles:** "PIN" for onboarding, "no-PIN" for everything after it.
- **Lab conditions:** the lab host was overloaded by other work. The shared
  Postgres timed out from 13:05:49 to 13:07:44 UTC and crashed into recovery from
  about 13:15 to 13:26 UTC; catalog reads then took up to 30 s and `watch`
  answered 503. Rows below that ran in that window say so. The stability cycles
  and every timing row ran after it (catalog reads median 31 ms).
- **Sources:** positions and states from ECP `query/media-player` polled about
  every 0.5–1 s; plan facts from the dev build's `player: plan` console line and
  the Stats overlay (Up); tracks and packaging from the transcode node's FFmpeg
  commands; stored positions from the watch projection read with a separate
  sign-in. Screenshots through the installer are cached (two requests less than
  about 3 s apart return the same image) and can lag the screen by seconds, so
  no timing below comes from a screenshot.
- **Probe:** 1,087 requests; all 527 `stream`, `playlist`, `segment`, and
  `subtitle` requests carried `Authorization` and `X-Profile-Id` (none
  `X-Profile-Token`, no-PIN profile), and nothing reached the foreign listener.
  Every playlist body used `#EXT-X-DEFINE` (largest 176,226 B). Largest segment
  19.7 MB. Errors: 6 segment 416s, 2 playlist 410s (polls after a stop), and the
  API 503s and 404s explained in the rows.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Onboarding, stock build | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build; signed out through the avatar menu, then a fresh install; PIN profile | PASS | Sign Out in the avatar menu went straight to sign-in. On the fresh install the app opened on address entry. The host was typed without a scheme; Play closed the keyboard with Connect focused (run 4 defect 1 fixed). OK on Connect: HTTPS failed in 342 ms (TLS), then "Connect without encryption?" named host and port; Connect led to sign-in. Play moved focus Username → Password → Sign in. In "Who's watching?", Down reached Change server, Right reached Sign out, and Up returned to the avatars. The PIN profile's PIN opened Home. Switch Profile in the avatar menu reopened the picker, and the no-PIN profile opened Home. |
| Onboarding, dialog beacons | 2026-10-22 | 55R625 / 15.3.4 | — | — | fresh install, one launch: address entry, consent, sign-in, picker, PIN | PASS | One `AppDialogInitiate` (TimeBase 238 ms), no "already signaled", one `AppDialogComplete` (147,955 ms). One `AppLaunchComplete`: Duration 149,780 ms (Roku 149,661 ms), DialogTime 147,955 ms, now below the launch duration (run 4: 69,029 ms against 41,531 ms). |
| Player keys, original | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 H.264 1080p AAC 2.0 (R88) | Detail Resume | PASS | `original_http` (`validated_original_playback`), `mpeg4_15`/`aac`; playing about 3 s after OK, 595.6 s for a stored 601.6 s. Right 628.2 → 659.8 s, Fast Forward 667.8 → 967.1 s, Left 976.6 → 968.6 s, Rewind 976.6 → 677.8 s; each was playing at the target by the first poll (2–3 s), ECP never left `play`, and Roku's trick-play UI never showed (run 4 defect 2 fixed). Back at about 731.8 s stored 731.33 s; Detail then read "Resume 12:11", and reopening started at 722.7 s (target 724.3 s). The timecode reads "10:17 / 22:00" (run 4 defect 4 fixed). |
| Memory check | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build, Rewind on the diagnostic screen | PASS | `roByteArray` blocks move `GetMemoryLimitPercent()`: 2% → 6% at 2 blocks of 23 MB, then about 4 points a block. Roku sent memory warnings at 80, 85, and 90% (payload `availablekb`, `percent`, `usage`), and the level went trim (82%), pressure (85%), critical (90%). The check held 23 blocks (533 MB, 94%, "ceiling"), released them, and came back through pressure (74%) and trim (70%) to normal (66%). `GetGeneralMemoryLevel` stayed `normal` throughout. Texture blocks were never needed. |
| H14, Off → English → Off | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT (cues every 10 s, 4 s long) (R89) | caption mode Off before the start; Down, then Down | FAIL | With caption mode Off the content loaded with the sidecar (ECP `captions="srt"`). Down to English still replanned and reloaded: ECP `startup` → `buffer` → `play`, "Buffering" in the chrome, `content assigned after the stop` 640 ms, `VODStartComplete` 2,317 ms, position back 1 s. The next cue (840 s) showed on time, 6.6 s after the key, which landed just after the 830–834 s cue ended. Down to Off reloaded the same way (612 ms, 2,241 ms). Warm-up from caption mode On behaved the same. Caption mode now follows the choice and was Off after playback. |
| Visual fixes | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build | PARTIAL | The player timecode renders "/" (row above). The theme check's timecode row has no "/" sample, so it cannot show the fix; its tabular row still measures 92 px for `1:11:11` and `0:00:00`. The focused picker avatar's ring is whole. The diagnostic screen's lines no longer overlap, the development line wraps inside the screen and says "Up test player", but the model still reads "A000X" (ECP: A109X). |
| M2 Home | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build, no-PIN | PARTIAL | Hero, Continue Watching (landscape) and poster rows in server order; Down, Right, and Up move focus with the focused card pinned at the row start, and the hero follows. OK on a movie and on a series opened their Detail pages; OK on a Continue Watching episode opened its series with that episode active ("Resume S1:E3"). Back from Detail restored focus to the same card, and after playback Home re-read its rows and kept focus on the item. Defect: in every row the focused card's ring and top edge are clipped along the top. |
| M2 Detail, movie | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build | FAIL | Play on an unwatched movie; "Resume 10:01" for a stored 601.6 s, Start Over beside it. Audio appeared only for a file with more than one track (Auto, TrueHD Atmos 7.1 Default, AC-3 5.1, Commentary), Subtitles for any (Auto, Off, then the tracks). A focused round button widens to its label; Back closes a picker. Down reaches Details; Back restores Home focus. Defect: Details shows "Released Jan 1, 1970" for two movies whose API `release_date` is 2026-05-06 and 2012-03-14. |
| M2 Detail, series | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode: MKV HEVC Main 10 2160p (DV P8, HDR10 base), E-AC-3 5.1 (R90) | dev build | FAIL | "Play S1:E1", season capsule, episode cards "S1 · E2". Focusing E3 put "S1 · E3 · 46 min" and its title and synopsis in the hero; OK played E3. The first OK hit the Postgres outage: `watch` 503, and the player showed "Can't load this title" with retry; Back returned to Detail on E3. After Back from 4 minutes of playback, focus stayed on E3 (not finished), Start Over appeared, and Play read "Resume S1:E3". Defect: Details shows "First Aired Jan 1, 1970" and "Last Aired Jan 1, 1970" (API 2020-10-23). |
| M2 Search | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build | PARTIAL | Opens on the keyboard with "Search your library". Four characters sent about 0.1 s apart made one search request; two sent 0.7 s apart made two. Play folded the keyboard into the query field and focused the chips; Movies and Series re-ran a one-word query at once ("1 result", then "No matches for …" with the shorter-title hint). OK on a result opened Detail; Back returned to the result, Back unfolded the keyboard, and Back left Search for Home's bar. Confirmed W6-4: on Search, OK on Movies in the top bar opened Home, not Movies. The result grid clips the focused poster's top and left, as D-L2 does. |
| M2 Library | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build | PARTIAL | Movies: resting on the tab previewed the list (two libraries, each with Recommended and Browse); Down entered it; OK opened Recommended rows; Browse opened sorted by Title with the rail. Every sort and its reverse relabelled the pill and reordered the grid except Rating, which kept title order both ways: the page sends `rating_imdb`, which is empty on every lab item, while `rating_tmdb` is set and sorts correctly through the API. Rail: B showed the three B titles; `#` showed only the title starting with "#". Series (one library) offered Recommended and Browse. Back: rail → grid → tab → Home. Confirmed D-L1 (the rail stays wide over the sixth column while the grid has focus) and D-L2 (the focused card's top and left are clipped). |
| Stability, node count | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build; 20 × Home → Detail → Back, 10 × Home → Movies Browse → Back | PASS | `sgnodes/all` (the `count_only` form returned the whole tree with `node-count`): Home 802 before, 802 after the Detail cycles, 802 after the Browse cycles (0%). 485 with Detail on top, 453 with Browse. No key lag was seen beyond the screen's own transitions; key-to-frame time was not measured (no Perfetto run). |
| Stability, texture | 2026-10-22 | 55R625 / 15.3.4 | — | — | dev build; `query/r2d2-bitmaps` at Home, Detail, and Browse | FAIL | 108.2 of 120.0 MB (90%) in all three snapshots, against the 70% browse target. The 223 bitmaps were identical each time: the cache keeps art from screens already left, such as 31 Browse posters at 282×423 while Home is shown. Large entries: the 1920×1080 splash (8.4 MB) and a 1920×1080 `background.png` (8.4 MB), six 1344×756 hero backdrops (4.1 MB each), and three 1229×691 Detail backdrops (3.5 MB each). Whether Roku evicts these before the limit is unconfirmed. |
| HEVC Main 10 MKV | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-039 MKV HEVC Main 10 2160p DV P8.1 (HDR10+ tagged), E-AC-3 JOC 5.1 (R91) | Detail Play | PARTIAL | Not an original: `server_remux_hls` (`hls_packaging_required`), hevc/eac3 6 ch, `dynamic_range` `hdr10`, Dolby Vision not claimed, EVENT playlist; `hevc_b`/`eac3`; `VODStartComplete` 3,961 ms. Right (+30 s) and Left (−10 s) both reanchored (replans 274 and 284 ms) and played again after 5.6 and 6.3 s; the −10 s target lay inside the plan's played range. Every HDR HEVC MKV in this lab plays as a remux, so the HEVC Main 10 original route is still unobserved. |
| Copy remux reanchors (AG-58) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, as above (R90) | Fast Forward twice, then Rewind twice | PASS | TS packaging (`-hls_segment_type mpegts`), one FFmpeg job per plan, offsets 363.8, 766.3, 491.1, 204.9 s. No segment 404 or 410 in the probe and no `transcode node seek restart` on the node. Forward: replans 342 and 591 ms, playing again 5.2 and 5.9 s after the key. Backward: replans 7,400 and 9,006 ms (the transport was ready 311 ms into the first), so the old plan kept playing about 11 s and playback resumed 15.2 and 13.3 s after the key. Six segment requests during plain playback answered 416. |
| H19, HEVC + E-AC-3 and E-AC-3 JOC, TS | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, E-AC-3 5.1 (R90); FX-039, E-AC-3 JOC 5.1 (R91) | — | PARTIAL | Both copy remuxes reported `audioFormat` `eac3` (ECP `audio="eac3"`) at the first frame of every plan, reanchors included; JOC is not distinguished. This is the first HEVC + E-AC-3 copy remux in the log (run 2 had no fixture). Sink: the TV's own speakers, no AVR or soundbar; `IsPassthruCodecActive()` not read. Audibility unconfirmed. |
| Detail track pick reaches start | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-019 MKV HEVC Main 10 2160p DV P8.1, TrueHD Atmos 7.1 + AC-3 5.1 + AC-3 2.0 commentary (R92) | Detail: Audio → the commentary track; Resume | PASS | The probe logs no bodies, so the node shows it: `-map 0:a:2 -c:a copy` (Auto would take the AC-3 5.1), and the plan read ac3 2 ch, `hdr10`. About 20 s in the 55.5 Mb/s remux stalled, and the client replanned to `server_transcode_hls` (`quality_bandwidth_limit`, h264/aac, `sdr`, `mpeg4_10b`/`aac_adts`, replan 4.2 s), still with `-map 0:a:2`. |
| Reopen after token expiry | 2026-10-22 | — | — | — | — | PENDING | Not attempted. The lab's access tokens last 3,600 s and the client refreshes on any request after 30 minutes, so an expiry needs about an hour with the app idle. Changing the server's token lifetime was out of scope; revoking the session would test sign-out, not expiry. |
| M1 deep links, signed in | 2026-10-22 | 55R625 / 15.3.4 | — | movie (SYNTHETIC), episode, series, season | dev build; `device-check.sh --launches 0 --deeplinks` | PASS | All eight rows (four types, by `launch` and by `input`) reached a first frame with `startPositionRule` resume and one `AppLaunchComplete`; launch rows 4.04–5.64 s after launch by the device clock (run 4: 3.96–4.70 s). Made-up ID: `deeplink: dropped {"reason":"inaccessible"}` after 404s, app left on Home. On launch rows Home, built under the player, still logs `home: launch complete without all artwork` 15 s later; no second beacon is sent. |
| M1 cold launch, release | 2026-10-22 | 55R625 / 15.3.4 | — | — | release build, restored session, no-PIN remembered; 10 launches, no reboot | PASS | Median 2.39 s, max 2.61 s from `AppLaunchInitiate` to `AppLaunchComplete` (Roku's value: median 1.50 s, max 1.69 s); Home now waits for the first two rows' art (AG-57), against 1.35/1.38 s in run 4. No dialog beacons, one `AppLaunchComplete` per launch, no artwork fallback. |

### Defects found in run 5

1. **Client:** Details dates read "Jan 1, 1970". `catalog.detail` passes a
   date-only `YYYY-MM-DD` string to `roDateTime.FromISO8601String`, which on
   Roku OS 15.3.4 leaves the epoch; the `GetYear() < 1000` guard does not catch
   1970. Released, First Aired, and Last Aired are all affected.
2. **Client:** subtitle switches still reload the content (run 4 defect 6), from
   Off to English and from English to Off, although caption mode was Off at load
   and the content carried the sidecar. Each replan returns a stream the client
   does not treat as the same media; the cause (for example a new `stream.url`
   per plan failing `playback.sidecars.sameMedia`) is unconfirmed.
3. **Client:** Home rows clip the focused card's top edge and ring, in
   Continue Watching and in poster rows. The Search grid clips the top and left
   like the Browse grid (D-L2).
4. **Client:** the Browse Rating sort uses `rating_imdb`, empty on every lab
   item, so it returns title order in both directions; the server sorts
   `rating_tmdb`.
5. **Client:** texture memory sits at 90% of the `r2d2-bitmaps` maximum on
   Home, Detail, and Browse, with bitmaps from screens already left still
   resident.
6. **Client (dev only):** the diagnostic screen still reports model "A000X";
   the theme check has no "/" sample.
7. **Server prototype:** backward reanchor replans take 7–9 s against 0.3–0.6 s
   forward, so a −300 s seek on an EVENT remux resumes after 13–15 s. EVENT
   plans still reanchor for a −10 s seek inside the plan's played range.
8. **Lab:** the shared Postgres on the lab host stalled once and crashed once
   under unrelated load; the client showed "Can't load this title" with retry
   for the 503 and recovered after it.
9. **Tooling:** `scripts/console.sh` in the background drops at once unless its
   stdin stays open, and each reconnect replays the console buffer. Installer
   screenshots are cached for about 3 s and can lag the screen.

## Run 6 — Milestone 3 player

Sixth hardware pass on the same TV: the Milestone 3 player (controls, keys,
Options, replans, caption modes, preferences, seek previews, Up Next) and the
W6/W7 fixes, against the lab stack on silo-server `roku/client-support` at
`63ecc659f` (AG-107).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could not
  be heard remotely, so audibility is never claimed.
- **Build:** `c2cf8b9`, stock dev build (`npm run sideload:dev`); no scratch
  patch. The dev build stays installed.
- **Profile:** "no-PIN". Its playback settings were all at their defaults
  (subtitle mode set to auto). For T4, T6, and T7 the run set
  `playback.subtitle_language`, `playback.preferred_quality`,
  `playback.max_bitrate_kbps`, and `playback.auto_play_next`, then removed them
  again; the profile's stored values afterwards match the originals.
- **Roku settings:** caption mode Off at the start and the end. Roku's autoplay
  setting was not changed (Up Next showed its toggle, so it is On).
- **Lab data:** no file in the lab has `trickplay_available` or any
  `marker_segments` (or single intro, credits, or recap markers), so seek
  thumbnails and Skip Intro could not run.
- **Sources:** key times from the relay's clock; positions and states from ECP
  `query/media-player` polled every 0.3–0.5 s; caption mode from ECP
  `device-info`; the dev console (`player: focus`, `player: plan`, `caption
  mode`, `platform`, `api` lines); plan decisions and replan timings from the
  lab server log; recipes from the transcode node's FFmpeg commands. The header
  probe logs no request bodies, so request fields were judged from the server
  log and FFmpeg. Screenshots never show the video plane; captions and Roku's
  own menus are captured.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 controls and keys | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 H.264 1080p AAC 2.0, `original_http` | Detail Start Over and Resume | PASS | OK showed the context line ("MOVIE · 2026"), title, scrubber, elapsed time, "−21:42 · Ends 11:38 AM", and skip back 10, play/pause (focused), skip forward 30, Subtitles, Options, Close. The controls hid 4.99 s after the last key. With the controls hidden, Right went 34.6 → 64.2 s and Left 67.2 → 56.2 s; three Rights 160 ms apart made one seek, 61.2 → 150.3 s. `hold Right 2.5` started the ladder (1×, then 2× at 1.2 s, running on at 2× after the release) and OK committed 171 → 418.5 s. Rev Rev showed «2×, Fwd stepped to «1×, and Back cancelled with no seek. Replay went 461.6 → 450.6 s. Back chain: Back cancelled a ladder (controls stayed), Back hid the controls at once, Back stopped and returned to Detail. |
| T2 `*` with the controls shown (DP-1) | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC | Up, then `*` 0.7 s and 0.35 s later | FAIL | Both times the console logged `player: focus {"controls":true,"focused":"keyfocus","reason":"controls shown"}` and then nothing: no `"options key"` line. Roku TV's own Settings menu (Sleep timer, Picture settings, Sound settings, Accessibility & language, Picture off) opened over the controls instead of Silo's Options. AG-113's condition is met: Roku TV takes `*` during full-screen playback whatever has focus. With the controls hidden, `*` opened the same menu (intended); Back 1.6 s later closed it and playback continued. The menu closes by itself about 10 s after it opens or when the player hides its controls, and a Back after that exits the player. |
| T2 Options panel | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC; library series episode, MKV H.264 1080p, AAC 2.0 ja + en, 3 SRT | controls' Options button; Left/Right, Down, Back | FAIL | Options opens on Info; Left and Right move along Info, Stats, Video, Audio, Subtitles; Down enters a list; Back returns to the tabs, then closes the panel with focus on the Options button. Info, Stats, and Audio render. Video shows only a "Quality" heading, and Subtitles only "Subtitles" and "Captions": in every tab with titled sections the section titles are drawn as the list's rows and the real rows (Auto and the qualities, Auto-play next, Off and the tracks, the caption modes) never appear. OK on the n-th drawn row chooses the n-th row of the flattened list. Info reads "MP4 · 4 kbps · 686.9 MB" for a 4,162 kb/s file. Stats ends "last stop:  ms" with no value. |
| T2 Down with the controls hidden | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC (1 audio, 1 SRT); library series episode (2 audio) | Down | PARTIAL | Down opened Options on Subtitles for the one-audio title and on Audio for the two-audio episode. Opened this way (and from the controls' Subtitles button) the list shows no focused row, and OK does nothing; Back, then Down, focuses the checked row and works. |
| T3 quality change | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | Options Video, the blank second row (flattened row 1) | PARTIAL | The UI cannot offer a quality (row above). OK on the second drawn row chose the first published quality: a `quality_change` replan (server 2,352 ms) returned `server_transcode_hls` `quality_fixed_rung` (FFmpeg `scale=-2:1080`, `-maxrate 3000k`), and playback reloaded at 263.9 → 260.0 s (`content assigned after the stop` 696 ms, `VODStartComplete` 1,085 ms). "Auto → a lower label" could not be chosen. |
| T3 audio change | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls`, AAC ja (default) + en | Options Audio: English → Japanese | FAIL | The `track_change` replan was refused in 3 ms: `[WARN] api: request failed {"kind":"http","ms":63,…,"status":422}`, then `[WARN] player: replan refused {"kind":"rejected","operation":"track_change"}`; the server logged `validation_failed`. The player names the audio by `{index}` alone (spec section 9.7), while the server's OpenAPI `TrackIdentityV3` requires `id`. The viewer sees nothing: English stays checked and plays. A Detail audio pick at start (`audio_track_index`) works (FFmpeg `-map 0:a:1`). |
| T3 subtitles Off → English → Off (DP-2) | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT (cues every 10 s, 4 s long) | caption mode Off; Options Subtitles via the flattened rows | PASS | Off → English: `caption mode chosen {"mode":"On"}`, one `track_change` (server 25 ms), position continuous with no `buffer` state, no "Buffering", and no `content assigned after the stop`; the cue "… cue 85 at 14:00" showed. English → Off: `caption mode chosen {"mode":"Off"}`, `track_change` 19 ms, again in place. The controls' pill read "Subtitles · <the track's file name>" rather than the language. |
| T3 captions On with subtitles Off (W7-5) | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT | after English → Off; Roku's menu: Accessibility & language → Closed captioning → On always | PARTIAL | Roku's menu: `platform: {"mode":"On"}`, `player: the plan follows the caption mode {"mode":"On","subtitle":false}`, one `track_change` and one reload (`content assigned after the stop` 766 ms, `VODStartComplete` 2,130 ms, 1,010.5 → 1,009.0 s) into content without sidecars (ECP captions `none`); five screenshots across two cue times showed nothing. Options' Captions rows are not reachable (T2 Options panel). |
| T3 caption modes | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC | Roku's menu: On always, On replay, On mute, Off | PARTIAL | Each change reached the player (`platform` and `player: caption mode` lines) and ECP. On mute is reported to the player as `"On"` while ECP reads `When mute`. Options' Off, On, On replay, and On mute rows cannot be shown (T2 Options panel). |
| T3 Replay and caption mode (W7-4, AG-80) | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC | caption mode "Instant replay" | PASS | Replay then Back 55 ms later: no seek, no caption-mode write, ECP still `Instant replay`. Replay alone: 1,101.7 → 1,091.2 s, the mode became `On` 0.2 s after the commit and `Instant replay` again at 11.1 s, when playback passed the press point. |
| T3 burned-in subtitle (W7-6) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-004 MKV H.264 1080p FLAC 2.0 ja + en, PGS only | Detail: English PGS; caption mode Off; Roku's menu On, then Off | PARTIAL | Start: `server_transcode_hls` `subtitle_burn_in_required` (FFmpeg `overlay`), then `the plan follows the caption mode {"mode":"Off","subtitle":false}` and a `server_remux_hls` plan without the subtitle. Captions On: `{"mode":"On","subtitle":true}`, burn-in plan again, reload 630 ms. Off: remux without the subtitle, reload 608 ms. Options' Off/On-only rows could not be checked (T2 Options panel). |
| T4 preferences (W7-7) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, MKV H.264 1080p AAC | profile: preferred quality 720p, max bitrate 1,500 kb/s, subtitle language en | PASS | Server log for the start: `quality_preference=720p`, `target_resolution=720p`, `target_bitrate_kbps=1500`, `decision_reason=quality_bandwidth_cap`. The subtitle `track_change` that followed produced a second FFmpeg job, also `-maxrate 1500k` and `scale=-2:720` (720p alone would be 2,000 kb/s), so the replan carried the cap. The next episode (auto-play) started capped again. A seek replan did not occur: the capped transcode seeks locally. |
| T5 seek previews | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC; FX-004; library series episode | ladder 2×–32× both ways | PARTIAL | No lab file publishes trickplay, so thumbnails and decode lag could not be tested. "Previews aren't available for this title" and the scrub time showed above the speed chip at 2×, 8×, 16×, and «32×, kept within the scrubber at its right end. With Left/Right the merged seek commits before a screenshot (about 2–3 s), so the message there was not captured. The speed chip and time overlap the title line. |
| T6a Skip Intro | 2026-10-22 | — | — | — | — | PENDING | No markers in the lab. |
| T6b Up Next | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, MKV H.264 1080p AAC | controls' Up Next button; Keep Watching; ladder to the end and OK | PASS | The button opened Up Next without a countdown: video box left, panel with "UP NEXT", still, series, episode title, "S2 · E5 · 24 min", Play Now, Keep Watching, Back, "Auto-play is On". Keep Watching closed it; at the end it reopened as "PLAYING NEXT" with Play Now and Back and no countdown. Back there exited to Detail, which had refreshed to the next episode. Opened at the end without credits, the countdown ran 10.0 s (stop 11:41:51.49, `playing the next episode {"auto":true,"streak":1}` 11:42:01.49). |
| T6c Roku autoplay off | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode | profile `playback.auto_play_next` false instead | PENDING | Roku's autoplay setting was not changed: its Settings screens cannot be captured, so the toggle would be set blind. With the profile's auto-play off, Up Next showed "Auto-play is Off" and no countdown for 17 s; turning the panel's toggle on started the countdown at once and advanced (`streak 1`). |
| T6d automatic advances | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes | four ends in a row | PASS | `streak` 1, 2, 3, each 10.0 s after the end; the fourth end opened "PLAYING NEXT" with no countdown, still waiting after 20 s. Each ladder seek to the end of a remux returned `server_transcode_hls` `copy_routes_exhausted`. |
| T6e Back after a chain | 2026-10-22 | 55R625 / 15.3.4 | — | library series | Back from the fourth Up Next | PARTIAL | Back returned to the Detail page the first episode was played from, and the page refreshed. Its Play read the episode after the first one played ("Play S2:E6"), although the watch projection marks that episode and the two after it as played. |
| T7 Search episode outside the play season (W7-1) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series (play season 1) | Search an S2 episode's title | PASS | One result (the series poster for season 2, caption truncated before its tag). OK opened the series with Season 2 selected, E4 first in the rail, and "Play S2:E4"; Play played S2:E4. |
| T7 Auto subtitles with a non-default audio (W7-2) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, AAC ja (default) + en, SRT forced, full, SDH | Detail: Audio English, Subtitles Auto; profile subtitle language en | PASS | FFmpeg `-map 0:a:1` (English); the first plan was followed by a `track_change`, and the pill read "Subtitles · Forced": the forced track, as chosen against English audio. Without a subtitle language the same start chose none, as `autoSubtitle` intends. |
| T7 Play while episodes load (W7-3) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series, MKV H.264 1080p E-AC-3 5.1, `original_http` | OK on the search result, Play 0.2 s later | PASS | Play went while the seasons and episodes reads were in flight; the play target played. Back showed "Play S1:E1" with the season's rail; Right to E2 updated the hero ("S1 · E2 · 1h 3m"), and OK played "S1:E2". |
| T8 Search top bar (W6-4) | 2026-10-22 | 55R625 / 15.3.4 | — | — | Up from the keyboard to the bar | PASS | Resting on Movies opened its library list; OK opened Movies as the root page. Resting on Series opened its list; OK opened Series. Resting on the avatar opened its menu; Back closed it with focus on the avatar. |
| T9 stability | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-004 | 10 × Home → Detail → Play 20 s → Back → Back | PASS | Every cycle was playing at 20 s and returned to Home. `sgnodes/all` at Home: 824 before, 826 after (+0.2%). No BrightScript error, crash, or backtrace in the console for the whole run (1,671 lines); its only warnings were the 422 above and one `the Video node is still stopping {"ms":3000}` during a reload (content assigned after 3,411 ms). |

### Defects found in run 6

1. **Client / platform (DP-1):** on Roku OS 15.3.4 the Roku TV takes `*`
   during full-screen playback even while the overlay's `keyFocus` has focus,
   so Silo's Options cannot be opened with `*`. Spec section 5.7 needs another
   route (AG-113).
2. **Client:** Options' Video and Subtitles tabs draw their section titles as
   rows and never show the rows, so Quality, Auto-play next, subtitle tracks,
   and caption modes cannot be chosen in Options; OK on a drawn row picks the
   flattened row of the same index. Cause unconfirmed: the section nodes from
   `listContent` may need to be marked as sections for `MarkupList`.
3. **Client:** Options opened straight into a list (Down with the controls
   hidden, or the Subtitles button) shows no focused row and OK does nothing
   until Back, then Down.
4. **Client / contract:** an audio change in Options is refused with 422: the
   replan's `selected_tracks.audio` has `index` only, and `TrackIdentityV3`
   requires `id`. The refusal is silent.
5. **Client:** Options Info shows the bitrate divided by 1,000 ("4 kbps" for
   4,162 kb/s).
6. **Client:** after an Up Next chain, Detail's Play targets the episode after
   the one launched from it, not after the last one played.
7. **Client (minor):** the subtitle pill shows the track's title (a file name)
   instead of its language; Stats prints "last stop:  ms" without a value; the
   ladder's speed chip and time overlap the title; Home's hero kept the
   previous item's logo over the next card's info line once, for an item
   without art; a Search episode's caption is cut before its tag.
8. **Platform:** Roku's caption mode event reports On mute as `"On"`.
9. **Server prototype:** a seek reanchor to the last seconds of a copy remux
   returns `server_transcode_hls` with `copy_routes_exhausted`.
10. **Lab and tooling:** the lab has no trickplay sheets and no markers; the
    header probe does not log request bodies.

## Run 7 — Milestone 3 retest

Seventh hardware pass on the same TV: the Milestone 3 player with the W8 fixes
and player fix batch 2 (run 6 defects 2–5 and 7, AG-117 to AG-123), against
the lab stack on silo-server `roku/client-support` at `63ecc659f`, now with
trickplay sheets and chapter markers (AG-118).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could not
  be heard remotely, so audibility is never claimed.
- **Build:** `5de73de`, stock dev build (`npm run sideload:dev`); no scratch
  patch. The dev build stays installed.
- **Profile:** "no-PIN". Its playback settings were at their defaults
  (subtitle mode auto, intro skip unset, so ask). For T5 the run set
  `playback.intro_skip_mode` to always, then never, then removed it; the stored
  values afterwards match the originals. Auto-play next was toggled only in
  Options, which lasts for the session.
- **Roku settings:** caption mode Off at the start and the end; Roku's
  autoplay setting not changed (Up Next showed its toggle and counted down).
- **Lab data:** sheets on every episode of the library series used here and on
  the second version of FX-001; intro and credits markers on S1E9–S1E11 (S1E11
  also a recap), credits only on S1E12 and S2E1. S2E1 carries no `user_data`
  because its only session stopped below the server's 5% minimum-resume
  threshold (corrected after server prototype 7; its files are ordinary
  single-episode files).
- **Sources:** the dev console (`player:`, `platform:`, `api:` lines); ECP
  `query/media-player` polled every 0.4–0.5 s (player positions; source
  position = the plan's `timeline_offset_seconds` + player position); the
  header probe with `--playback-bodies` (start, replan, progress, route event,
  and stop bodies, secrets redacted); a start replayed with its identical body,
  which returned the stored decision without a new session. Sheet requests go
  to the lab server directly, not through the probe. Screenshots requested
  under about 3 s apart return the same cached image, so timed checks used ECP.
  The console capture stopped once (14:35–14:37 local); Roku's replayed buffer
  on reconnect covers that span.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a Options routes and rows (defects 2, 3; AG-117, AG-119) | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC + external SRT; library series episodes | controls' Options button; Down with the controls hidden; controls' Subtitles button | PASS | The Options button opened Info; Info, Stats, Video, Audio, and Subtitles each showed their headings with rows beneath (Quality: Auto, five rungs with bitrates; Subtitles: Off, English · SRT; Captions: Off, On, On replay, On mute; on an episode, Auto-play next below the rungs, reached by scrolling). Down with the controls hidden opened Subtitles on a one-audio title and Audio on a two-audio episode, and the Subtitles button opened Subtitles; each time the checked row was lit and OK on the next row acted at once. |
| T1b quality Auto → lower | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` | Options Video: 720p Medium | PASS | `quality_change` with `quality_preference` `720p-medium`; plan `server_transcode_hls` `quality_fixed_rung` (server 1.8 s); `content assigned after the stop` 587 ms, `VODStartComplete` 1,229 ms; 297.9 → 296.0 s; the dot moved to 720p Medium. |
| T1c Auto-play next | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode | Options Video, last row | PASS | Shown for the episode only, reading On; OK set Off, OK set On again (screen identical to the first). Up Next later read "Auto-play is On" and counted down. |
| T1d subtitles Off → English → Off (DP-2, W8-2) | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT, `original_http` | caption mode Off | PASS | English: `caption mode chosen {"mode":"On"}`, one `track_change` (95 ms), no reload line, position continuous. Off: `caption mode chosen {"mode":"Off"}`, one `track_change`, no reload. From the Subtitles button later, English again showed "cue 70 at 11:30" in place and the pill read "Subtitles · English" (run 6: the file name). |
| T1e caption modes (defect 8, AG-123) | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC | Options Captions rows | FAIL | On with subtitles Off: `the plan follows the caption mode {"mode":"On","subtitle":false}`, one reload without sidecars (660 ms), ECP `captions="none"`. On replay → ECP `Instant replay`. On mute chosen from On replay: ECP `When mute`, but Options checked On: the first platform event after the write repeated the old mode (`platform: {"mode":"Instant replay"}`), then `{"mode":"On"}` arrived and was shown as On. In two later tries (from Off, and from On replay again) the events were `On`, `On` and On mute stayed checked: 1 failure in 3. |
| T1f more than seven subtitle tracks | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode, 15 ASS tracks | Down, then Down to the end | PASS | The list scrolled row by row through Off, the 15 tracks, the Captions heading, and On mute, keeping the lit row inside the window. |
| T1g `*` on a Roku TV | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC | Up, then `*` 0.6 s later | PASS | Roku TV's Settings menu opened over the controls (expected, AG-117); Back closed it and playback continued. |
| T2 audio change (defect 4, AG-120) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, MKV H.264 1080p, AAC ja (default) + en, `server_remux_hls` | Options Audio: English → Japanese | PASS | Probe: `POST replan 200 {"operation":"track_change","position_seconds":46.621,"selected_tracks":{"audio":{"id":"file:<id>:audio:0","index":0}}}`. The new plan was `original_http` (MKV); console `video formats` went from `aac_adts`/`mpeg4_10b` to `aac`/`mpeg4_15`; `content assigned after the stop` 657 ms, `VODStartComplete` 983 ms; 47.1 → 44.0 s; Japanese checked. |
| T3 Info, Stats, ladder at the left (defects 5, 7) | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC | Options Info and Stats; Rev Rev from 8 min | PASS | Info read "MP4 · 4 Mbps · 686.9 MB": the plan's `source.bitrate_kbps` is 4,026 (the stored start decision, replayed), which rounds to 4 Mbps; the watch projection's 4,162 is not used (AG-121). Stats ended "Slow stops: 0" with no "last stop" line. At «2× near 0:19 the context line and title were hidden, and the chip, time, and "Previews aren't available for this title" crossed nothing; Back cancelled with no seek. |
| T4 seek previews | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode with sheets | Fwd ×2, ×4, ×5, ×6; Rev ×5, ×6; Back | PASS | Thumbnails (240 px, 16:9) with the time under them showed at »2×, »8×, »16×, »32× (clamped at the right end) and «16×, «32× (clamped at 0:00), each in the first screenshot after the key (1–2 s); the title and context line hid. No texture, bitmap, or load-failure line in the console. Sheet load times were not measurable (sheets bypass the probe; screenshots lag 2–3 s). |
| T4 seek previews, movie | 2026-10-22 | 55R625 / 15.3.4 | — | FX-001 | deep link; Fwd ×2 | PARTIAL | The client plays the title's default version, which has no sheets (the lab's sheets are on its second version), so the scrubber showed the time and "Previews aren't available for this title". |
| T5 Skip Intro, ask | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, intro markers | profile default (ask) | PASS | "Skip Intro" appeared at the bottom right 114 px up with a growing fill as playback entered the intro; OK with the controls hidden at about 3 s jumped to the intro's end (137 → 223.8 s). A later OK, after the 5 s ran out, only showed the controls. With the controls shown the button rose to 400 px and dimmed, and OK paused playback instead of skipping; paused for 5 s, the fill did not move (screenshots identical); after resuming, Back removed the button with no seek and the controls hid 4.4 s later. |
| T5 Skip Intro, always | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, recap + intro (S1E11) | `intro_skip_mode` always | PASS | The recap (green band, 0–2:36) played unskipped; entering the intro seeked to its end (246 s) and showed "Intro skipped" with Watch Intro. With the controls hidden, OK on Watch Intro went back to the intro's start (159.7 s 4 s later) and the button left; with the controls up (after a skip), OK went to play/pause, as specified. |
| T5 Skip Intro, never | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode | `intro_skip_mode` never | PASS | No button at 181 s or 185 s inside the intro range. |
| T6 Up Next at the credits | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, credits markers | seek to about a minute before the credits | PASS | Crossing the credits opened Up Next with the video in the left box and a countdown equal to the runtime left: 123 at 1,349.5 s of 1,472 s (118 3.5 s later); 93 at 1,377.5 s of 1,471 s; 159 at 1,290.5 s of 1,450 s. Play Now: `playing the next episode {"auto":false,"streak":0}`, the stop, and the next start in the same player (first frame 1,772 ms). Keep Watching closed it; seeking back before the credits and crossing again did not reopen it; the end reopened it as "PLAYING NEXT" with Play Now and Back. Back there exited to Detail. |
| T6 chain across seasons (W8-1, AG-116) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series S1E11 → S1E12 → S2E1 | countdown to the end, then Play Now; Back at 45 s | PASS | S1E11's countdown ran to the video's end and S1E12 started (`auto":true,"streak":1`); S1E12's Play Now started S2E1. Back at 45.7 s returned to the Detail page the chain started from, now on Season 2 with S2·E1 active. Play read "Play S2:E1", not Resume, because the lab returns no `user_data` for that file (above). A second chain, S1E11 → S1E12 with Back at 42.7 s, ended on S1·E12 with "Resume S1:E12" and Start Over; the server kept that episode's earlier position (1,293 s) rather than the 42.7 s stop. |
| T6 seek back before the next episode resolves (W8-4) | 2026-10-22 | — | — | — | — | PENDING | Not reproducible here: the next episode resolves about 150 ms after the first plan (`next episode {"found":true}`), well before playback can cross the credits, so the window needs a slow catalog read. |
| T7 end of an episode (AG-118 open item) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, `server_remux_hls` | natural end after Keep Watching; natural end with Up Next counting down | PASS | Keep Watching path: progress to 1,468.5 s, then `DELETE stop` at 1,471.88 s (no replan after the last reanchor), "PLAYING NEXT" shown; ECP stayed `play` with the player position frozen at the end for the minute before Back, and no `decoder_no_output`, `transport_stall`, `failure_recovery`, or `plan_failed` was logged. Countdown path: progress to 1,466.04 s, `DELETE stop` at 1,471.92 s and `playing the next episode {"auto":true,"streak":1}` together, the next start 0.4 s later, first frame 3 s after that; no failure. Run 6's failures followed ladder seeks into the last seconds, which this run did not repeat. |
| T8 captions on during a load (W8-3, AG-115) | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT, transcode | captions Off; 720p Medium → 720p Low, then Captions On 1.1 s after the key | PASS | Captions On landed before the quality plan arrived: `quality_change`, then a corrective `track_change` 141 ms later; one `content assigned after the stop` (626 ms); ECP `captions="none"`; eight screenshots inside cue windows (400–424 s) showed no cue. Positive control: English then showed "cue 47 at 07:40". |
| T9 Home hero and Search caption (defect 7) | 2026-10-22 | 55R625 / 15.3.4 | — | — | Home Right/Left between a card with a logo and one without art (2 slow, 3 at 0.25 s); Search for an S2 episode title | PASS | The card without art always showed its title and no logo or backdrop. The episode result showed the series title cut with "…" and the tag " · S02E04" whole. |
| T10 stability | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001 | 10 × Home → Detail → Resume 20 s → Back → Back | PASS | Every cycle was playing at 20 s and returned to Home. `sgnodes/all` at Home: 825 before, 826 after (+0.1%). No BrightScript error, backtrace, `[WARN]`, or `[ERROR]` line in the run's console (2,004 lines). |

### Defects found in run 7

1. **Client:** On mute chosen in Options sometimes reads On (1 of 3). When
   the platform's first event after the write repeats the previous mode, it
   clears `m.wroteMute` (`components/player/Player.bs`, `onPlatform`) before
   Roku's `"On"` echo arrives, so the echo is taken for On. Console:
   `caption mode chosen {"mode":"When mute"}`,
   `platform: {"mode":"Instant replay","type":"captionMode"}`,
   `platform: {"mode":"On","type":"captionMode"}`,
   `player: caption mode {"mode":"On"}`; ECP read `When mute`. Every write here
   produced two events, and the first sometimes carried the old mode (Off then
   On for On; On then Instant replay for On replay).
2. **Client (minor):** the rate-ladder speed chip is not kept within the
   scrubber's ends: at the right end it overhangs by 56 px (»32×), at the left
   by 58 px («32×). Near the left end the "Previews aren't available" text and
   its time sit about 300 px right of the scrub point.
3. **Client (minor):** a scrolled Options list cuts its top heading in half
   (the Subtitles heading after scrolling to On mute).
4. **Lab / server:** S2E1's 45 s session left no resume point and no
   `user_data`, and S1E12 kept its older position (1,293 s) after a later
   session stopped at 42.7 s. Server prototype 7 traced both to the server's
   minimum-resume rule: a stop below 5% of the runtime is discarded, and an
   earlier, later position stays (AG-125). Not a client or indexing defect.
5. **Lab:** FX-001's sheets are on its second version; the client plays the
   default version, so the movie preview check could not run.
6. **Tooling:** a background console capture started without an explicit
   timeout stops after 30 minutes; start it with a timeout above the run's
   length.

Observations for review, not counted as defects: Back from a partial
re-watch of an episode the server already marks played moves Detail to the
next episode (the rule reads the server's `played`); after the deep-link
player closed over Home, focus returned to the Home tab and the hero kept the
pre-refresh first item until focus entered the rows; captions turned on
before a quality plan arrives cost one extra `track_change` (AG-111's path on
the old content), with a single load.

## Run 8 — Milestone 3 lifecycle

Eighth hardware pass on the same TV: token refresh during playback, server
restart, an unreachable server and the terminal error, reopening after token
expiry, the run 7 UI fixes, and stability, against the lab stack on
silo-server `roku/client-support` at `63ecc659f` with 3-minute access tokens
(`auth.access_token_expiry` `3m`, refresh tokens 30 days; AG-125).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could not
  be heard remotely, so audibility is never claimed.
- **Build:** `02d9c98`, stock dev build (`npm run sideload:dev`); no scratch
  patch. The dev build stays installed.
- **Profile:** "no-PIN", settings unchanged. Roku's caption mode stayed Off; the
  Options On mute row was only focused, never chosen.
- **Lab:** only the sandbox's API container was restarted or stopped (host load
  2–7 on 32 cores); it ended running and healthy. While it is down the header
  probe answers 502, as a reverse proxy would, so the client never saw a refused
  connection. The synthetic title's default version now has seek previews, so
  the no-preview check used FX-001.
- **Sources:** the dev console (`api:`, `player:`, `playback:` lines, local
  time); ECP `query/media-player` every 0.5 s; the header probe with
  `--playback-bodies`; the lab server log for resume targets. Token lifetime
  confirmed on the device: after the last 1-hour token reached its refresh
  point, refreshes ran every 90 s on the next request.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a token refresh, copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, MKV H.264 1080p AAC, `server_remux_hls` | Start Over, 18 min across an Up Next advance | FAIL | 105 progress posts all 200; 9 refreshes all 200; no API 401. Exactly when the token in the content's `HttpHeaders` expired (3 min after it was issued), segments answered 401 (4, then 5 after the next load) and the console logged `[WARN] player: Video error {"category":"mediaerror","error":-5,"kind":"decode","message":"Video error -5: buffer:loop:demux:Errors seen on all bitrates:last_err:401:…","status":0}`. The client sent `failure_recovery` `decoder_failure` instead of refreshing and reopening: the first reply was `server_transcode_hls` `copy_routes_exhausted` (2.1 s), the second a remux again. Playback continued after each. |
| T1b token refresh, original | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001 MKV H.264 1080p AAC 2.0, `original_http` | 8 min with no seek, then ladder seeks | FAIL | Eight minutes played on one progressive connection with no 401; 54 progress posts all 200, 6 refreshes all 200. Right (+30 s, inside the buffer) made no request. A ladder seek forward after the header token expired: the range request got 401, the `Video` node reported no error and sat in `buffer` at the old position for 20 s, then the stall clock sent `seek_failure_recovery` `decoder_no_output` and the server returned `server_remux_hls` at the target. A backward ladder seek repeated it with about 230 range requests answered 401 (about 11 a second) during the 20 s. No refresh-and-reopen (plan 6.4) happened in any case. |
| T1c seek after expiry, reanchor | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | paused 2 min past the header token's expiry, Replay | PASS | No media request while paused. Replay sent `seek_reanchor` (330.2 → 320.2 s); the new load took headers from the token the progress posts had refreshed (no refresh needed), `content assigned after the stop` 562 ms, `VODStartComplete` 1,535 ms, no 401. A forward ladder seek on this remux stayed local. |
| T2a server restart, copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | `docker restart` of the API container 20 s into playback | PASS | Down about 6 s. Segments answered 502, then `Video error -5` with `last_err:502` (classed `decode`); `failure_recovery` `decoder_failure` was answered 404 (session lost), and the client started a new attempt: `start` 201, remux at 420.42 s, first frame 3.0 s after the error. Playback resumed by itself; no "Reconnecting" (the server answered throughout). Stop reported 468.584 s. |
| T2b server restart, original | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | `docker restart` 30 s into playback | PASS | Down about 11 s. Playback never stopped: one progress post got 502 and was resent byte for byte 10 s later (200); Roku reopened the range request by itself after the old connection failed. Stop reported 1,449.45 s. |
| T2c resume point after a restart | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode | Resume after T2a | FAIL | After T2a's stop (468.584 s) the console logged `playback: stopping a session because its player left` and a second `DELETE` (only `installation_id` and `stop_id`) went out 0.6 s later, 200. The next Resume started from the server's target 406.988 s, the lost session's last progress (413.988 s) minus 7, not 461.6 s. |
| T3a unreachable, copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | `docker stop` | PASS | Segments 502 → `Video error -5` → `failure_recovery` → 502 → reconnect: `track_change` tries at once, then 1, 2, 4, and 8 s apart and every 15 s after, with "Reconnecting. Playback will resume automatically." at the top right. 120 s after the reconnect began: full-screen "Can't reach the server" / "Check the network connection and that the server is running, then try again." with Retry and Try Anyway. |
| T3b Retry, Try Anyway, Back while down | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode | server still stopped | PARTIAL | Retry: `GET /api/v2/system/info` 502, `[WARN] player: the server is still unreachable`, screen unchanged. Try Anyway: "Starting…", `start` tried 6 times over 31 s (all 502), then the error came back with Retry only, no Try Anyway (defect 4). Back from that screen returned to Detail cleanly; Detail's reads failed silently. When the server returned, the pending progress and stop jobs were delivered (stop at 481.556 s). |
| T3c server back, Retry | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | `docker stop` 30 s in; Fwd Fwd + OK past the buffer; `docker start`, then Retry | PARTIAL | Roku played about 2 min from its buffer while "Playback progress is pending…" showed and it retried the range about 12 times a second (502). After the seek, the stall clock sent `seek_failure_recovery` `decoder_no_output` (502), then the reconnect ran with "Reconnecting…" over the controls, and the terminal error came 120 s later. Server back, Retry: `system/info` 200, then `start` answered 401 five times in 17 s (defect 5), a refresh 30 s after the last failed one, then `start` 201 and the first frame 46 s after Retry, at the pending seek target. The lab was healthy afterwards. |
| T4a Resume after token expiry | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | stop at 501.034 s (past 5%), 3 min 44 s idle on Detail with no request, Resume | PARTIAL | The refresh went first (`auth/refresh` 200, Detail's reads waited for it), then capabilities 304 and `start` 201. Server target 494.034 s (saved − 7), plan offset 492.492 s, but Roku's first playing position was 8.04 s into the content (about 500.5 s), so the rewind was lost on this start (defect 6). The previous Resume of the same title started at the segment start, 2.1 s before its target. |
| T4b cold launch after token expiry | 2026-10-22 | 55R625 / 15.3.4 | — | — | Roku Home 3 min 44 s, token expired 74 s earlier, launch | PASS | `system/info`, `session: state signed_in`, a refresh before the profile and Home reads, Home with Continue Watching and no sign-in; `AppLaunchComplete` 2,615 ms. |
| T5a ladder chip at the ends (run 7 defect 2) | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC (now with previews) | «32× clamped at 0:00; »32× clamped at the end | PASS | «32× chip from x 88 (the scrubber's left end); »32× chip ending at x 1832 (its right end). Run 7 overhung by 58 and 56 px. |
| T5b «2× near the left end without previews | 2026-10-22 | 55R625 / 15.3.4 | — | FX-001 (default version, no sheets) | Rev Rev at 0:25 and at 0:00 | PASS | "Previews aren't available for this title" starts at the scrubber's left end and the time sits above the chip, centred in the 240 px preview box anchored at the left end (about 110 px right of the scrub point). At «2× the scrub moves 40 s a second, so 0:19 itself could not be captured; the closest was 0:25. |
| T5c Options scroll (run 7 defect 3) | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC + external SRT; library series episode with 15 ASS tracks | Down, then Down to On mute (not chosen) | PASS | Synthetic: the list scrolled 48 px and the Subtitles heading left whole. 15-track episode: at the last track, at Captions Off, and at On mute the top row was whole; no half heading. |
| T6 stability | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` | 10 × Home → Detail → Resume 20 s → Back → Back | PASS | Every cycle was playing at 20 s and returned to Home. `sgnodes/all` at Home: 826 before, 826 after (0%). No BrightScript error, backtrace, or `[ERROR]` line in the run's console (1,988 lines); its `[WARN]` lines are the 401, 404, and 502 failures above. |

### Defects found in run 8

1. **Client:** a media 401 or 502 on HLS segments reaches the player as
   `Video` error −5, category `mediaerror`, with the status only inside
   `errorStr` (`last_err:401`). `playback.video.httpStatus`
   (`source/playback/video.bs`) reads a status only from an `http` category or
   "http NNN", so the failure is classed `decode` and sent as
   `failure_recovery` `decoder_failure`: the route is excluded and nothing
   refreshes the headers (plan 6.4), and a server outage after the first frame
   starts with `failure_recovery` instead of spec 9.6's `track_change`. With
   these tokens it recurred every 3 minutes after each load; content headers
   keep the token they were loaded with.
2. **Client:** a 401 on a progressive original's range request produces no
   `Video` error at all. The node buffers for 20 s while Roku retries the
   range about 11 times a second, then the stall clock sends
   `seek_failure_recovery` `decoder_no_output` and the original route is
   excluded.
3. **Client / server:** after a server restart, the stop for the lost session
   ("stopping a session because its player left", no final sample) went out
   after the new session's stop, and the server's resume point fell back to
   the lost session's last progress (413.988 s instead of 468.584 s).
4. **Client:** Try Anyway during an outage that answers 502 retries the start
   6 times over 31 s, then shows the error with Retry only: a 5xx answer leaves
   the session reducer's `reachable` true, so `serverUnreachable` is false and
   Retry there skips the server check.
5. **Client:** after an outage longer than the access-token lifetime, Retry's
   start went out with the expired token and was refused 401 five times over
   17 s. A failed refresh's 30 s backoff (`notBefore`) suppresses the refresh,
   and `unauthorized` (`source/auth/coordinator.bs`) answers
   `auth_unavailable` instead of refreshing, although `system/info` had just
   succeeded. Playback returned 46 s after Retry.
6. **Client (unconfirmed cause):** one Resume started about 6.5 s after the
   server's target (8.04 s into a remux whose `player_start_seconds` should be
   about 1.5 s), losing the 7 s rewind; the previous Resume of the same title
   started 2.1 s before its target.
7. **Lab and tooling:** the probe answers 502 for a stopped upstream, so the
   refused-connection path (`status 0`, reconnect without a failed
   replan) was not exercised. Trickplay sheets for the synthetic title's
   default version now exist, and sheet requests pass through the probe
   without credentials.

Observations for review, not counted as defects: during the outage the
progress job kept resending the first failed sample (sequence 4, 1,478.98 s)
rather than the latest one, while the stop carried the right final position;
the Home hero kept describing the previously focused title after a return
from playback, through all ten T6 cycles (run 7 noted the same); two subtitle
tracks on the 15-track episode are named by region ("Saudi Arabia",
"Hong Kong"); while scrubbing, the elapsed time shows the scrub time but the
remaining time and "Ends" keep the playing position.

## Run 9 — lifecycle fixes and parity fixes

Ninth hardware pass on the same TV: run 8's T1a to T6 and defects 1 to 6
again with the lifecycle fixes (AG-137 to AG-142), the parity fixes (AG-126 to
AG-135), and plan 6.6's acceptance scenarios, against the lab stack on
silo-server `roku/client-support` at `63ecc659f` with 3-minute access tokens
(`auth.access_token_expiry` `3m`, left as found).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could not
  be heard remotely, so audibility is never claimed.
- **Build:** `f1d9d9b`, stock dev build (`npm run sideload:dev`); no scratch
  patch. The dev build stays installed.
- **Start state:** the dev app was signed in to a non-lab server; the run
  changed the server to the lab, which ends the local session only (no logout
  goes to the old server).
- **Profiles:** "no-PIN" for most tests; "PIN" for the profile change. Roku's
  caption mode read On at launch and was not changed.
- **Lab:** only the sandbox's API container was restarted or stopped (host
  load 1.5–12 on 32 cores); it ended running and healthy. While it is down the
  header probe answers 502. For T5a the run uploaded a PNG avatar to the no-PIN
  profile and set the PIN profile to an SVG preset; both were removed
  afterwards. The probe's second listener (another port, same upstream)
  served as the second server for T6d.
- **Sources:** the dev console (local time); ECP `query/media-player` every
  0.5 s; the header probe with `--playback-bodies` (listener, auth and profile
  header presence, positions; 2,945 lines, none answered 401); the lab API for
  avatars, library versions, and episode states.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a credential renewal, copy remux (run 8 defect 1) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | Resume, 10 min 43 s of playback | PASS | `player: renewing the media credential before it expires {"seconds":60}` seven times, about every 90 s, each a `seek_reanchor` 200 at the position. Interruption 1.5–3.0 s per renewal (ECP); playback resumed 0.7–4.1 s before where it left (Roku started each reanchored load at 0.0, before `player_start_seconds`). Probe: no 401, 64 progress posts all 200, 7 refreshes 200, no `failure_recovery` or `decoder_*`. |
| T1b credential renewal, original (run 8 defect 2) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | deep link, 10 min 8 s of playback | FAIL | Renewals ran as local reloads at the same position with no 401 (60 progress posts all 200). The first reload rebuffered 4.5 s; at the second, 90 s later, Auto stepped down: `quality_change` with `bandwidth_estimate_kbps` 1827 (70% of the source rate), `server_transcode_hls` `quality_bandwidth_limit`, `[WARN] player: the Video node is still stopping {"ms":3000}`, 7.6 s without picture (defect 1). Later renewals on the transcode reloaded in about 1 s. |
| T1c pause past expiry, then Play | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | paused 4 min 10 s, Play | PASS | No media request while paused. Play: `renewing the media credential before it expires {"seconds":-126}`, `seek_reanchor` 200, playing 3.0 s later; no 401. |
| T1d ladder seek after expiry, forward | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | paused 4 min 17 s, Fwd Fwd, OK | PASS | `mediaHeaders`, reload at the target (+100 s) with a range request 206 carrying the headers; no 401; stays paused, as OK commits only. |
| T1e ladder seek after expiry, backward, committed with Play | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | paused 4 min 10 s, Rev Rev, Play | FAIL | Renewed reload at the target (−103 s), 206, no 401, but playback stayed paused (ECP `pause`, progress `is_paused` true) (defect 2). Control with a fresh credential 50 s later: the same keys resumed playing. |
| T2a server restart, copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | `docker restart` 24 s into playback | PASS | Segments 502, then `Video error {"category":"mediaerror","error":-5,"kind":"server",…last_err:502…}`; `track_change` 502, then 404 (session lost), new `start` 201 at the position; playing 3.5 s after the error, 1.1 s behind. No `failure_recovery`. |
| T2b server restart, original | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | `docker restart` 27 s into playback | PASS | Playback never stopped; one progress post got 502 and was resent byte for byte 10 s later (200). One stop. |
| T2c resume point after a restart (run 8 defect 3) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode | Back after T2a, then Resume | PASS | One `DELETE` (1,255.87 s); no "stopping a session because its player left". The next Resume asked for 1,248.87 s, the newer session's stop minus 7. |
| T3a outage, copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | `docker stop` for about 4 min | PASS | `Video error … "kind":"server"` (last_err 502), then `track_change` tries 1, 2, 4, and 8 s apart and every 15 s after (all 502) with "Reconnecting. Playback will resume automatically."; 120 s later "Can't reach the server" with Retry and Try Anyway. |
| T3b Retry and Try Anyway while down (run 8 defect 4) | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode | server still stopped | PASS | Retry: `system/info` 502, `[WARN] player: the server is still unreachable`, screen unchanged. Try Anyway: "Starting…", `start` 502 six times over 32 s, then the error again with Retry and Try Anyway. |
| T3c server back, Retry (run 8 defect 5) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode | `docker start`, Retry | PASS | Retry: `system/info` 200, refresh 200 at once (the outage outlasted the token), `start` 201, first frame 3.2 s after Retry; no 401. |
| T3d the outage's superseded start | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode | Back 60 s after T3c | FAIL | After the player's stop, the network task replayed Try Anyway's unanswered start (which a newer start had replaced): `start` 201, then `playback: stopping a session because its player left` and a `DELETE` with no sample (defect 5). The resume point did not move here (that start's position was below the 5% threshold). |
| T4a Resume rewind (run 8 defect 6) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, `server_remux_hls` | five Resumes past 5%, plus other loads | FAIL | First ECP positions against `player_start_seconds`: 8.016 vs 2.084, 0.0 vs 3.628, 0.617 vs 1.04, 8.041 vs 0.666, 8.041 vs 0.165. Each late start logged `[WARN] player: the load started past its start; seeking back`, buffered 2.5–5 s, and resumed at 8.17 s, not at the start (defect 3). The same happened on a Retry's start (7.29 vs 0.408), a skip's reanchor (8.041 vs 0.629), and a Play from the beginning (8.041 vs 0). |
| T4b viewer seek in the first 3 s | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | Right 1.0 s, then 1.9 s, after a late first frame | FAIL | The controls showed but no seek or replan followed; playback ran on from 8.17 s (defect 4). A Right 30 s later sent `seek_reanchor` at once. |
| T5a profile avatars (AG-126) | 2026-10-22 | 55R625 / 15.3.4 | — | — | uploaded PNG, SVG preset; picker → Home → avatar menu → Switch Profile → PIN profile's Home | PARTIAL | The upload's presigned object-store URL is unreachable from the TV's network on this lab, so it is the broken-URL case: initials on the profile colour in the picker, the top bar, and the menu header, unchanged 30 s later. The SVG preset showed initials in the picker and in the PIN profile's top bar. A loading raster could not be shown on this lab. |
| T5b clocks at the 32× ends (AG-127) | 2026-10-22 | 55R625 / 15.3.4 | — | SYNTHETIC, `original_http` | »32× to the end, Back; «32× to 0:00, OK | PASS | At the right end: 22:00 and "−0:00" ("Ends" is left out when nothing remains). Back: 4:17, "−17:42 · Ends 7:27 PM", no seek. At the left end: 0:00, "−22:00 · Ends 7:31 PM". OK: playing from 0:00, then 0:04, "−21:55 · Ends 7:32 PM". |
| T5c partial rewatch (AG-128) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode marked played | play 41 s, Back | PASS | Detail kept the rewatched episode active. |
| T5d season finale (AG-129) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series S1E12 (next season unplayed); S3E12 (last episode) | ladder to the end; Back from "Playing Next" | PASS | S1E12: Detail opened Season 2 with S2E1 active and described. S3E12 (`next episode {"found":false}`): the player exited at the end and Detail kept S3E12. A finale before a fully watched season was not tried. |
| T5e Play pill width (AG-131) | 2026-10-22 | 55R625 / 15.3.4 | — | library series; SYNTHETIC | Detail of a series and a movie | PASS | Series: "Resume S2:E1" and "Play S2:E2" both 340 px with the label centred; movie: "Resume 3:56" 261 px, its label's width. |
| T5f title without audio (AG-132) | 2026-10-22 | — | — | — | — | PENDING | No title without audio on the lab (the 73 movie items' versions all list audio tracks). |
| T5g library menu with 3+ libraries (AG-133) | 2026-10-22 | — | — | — | — | PENDING | The lab has three libraries, at most two per tab. |
| T6a Back during start | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode, `original_http` | Play, then Back Back 0.3 s apart | PASS | `start` 201, the player left before the first frame, `DELETE` 200 0.6 s later; no first-frame event or progress. A single Back during start only hid the controls shown at start. |
| T6b profile change during a pending stop | 2026-10-22 | 55R625 / 15.3.4 | — | FX-009, `original_http` | PIN profile playing, `docker stop`, Back, picker; `docker start`, choose no-PIN about 3 s after the API answered | PASS | `api: session operation waits for playback jobs`, then after 10 s `playback: playback job identity_changed` for the progress and the stop, then the new profile. No progress or stop went out afterwards, with either profile's headers. |
| T6c profile change during a replan | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | `docker stop`, Back during "Reconnecting" | PARTIAL | The player left while the reconnect's `track_change` was retrying; the switch came after the server returned and the jobs had drained (old identity). A replan in flight at the switch could not be produced: the probe answers 502 within 40 ms. |
| T6d server change during a pending stop | 2026-10-22 | 55R625 / 15.3.4 | — | library series episode | `docker stop`, Back, Switch Server to the probe's second listener; `docker start`, Connect | PASS | `session operation waits for playback jobs`, 10 s, `playback job identity_changed` (progress, stop), `api: server changed`, sign-in. The second listener received only `system/info` and `auth/providers`; no job reached either listener after the change. |
| T6e rapid Up Next chain | 2026-10-22 | 55R625 / 15.3.4 | TV | library series S3E1–S3E4, `original_http` | ladder to the end, Play Now ×3, Back Back during S3E4's start | PASS | `playing the next episode {"auto":false,"streak":0}` three times; four starts and four stops, the last a `DELETE` without a sample 2.1 s after its start; Detail returned on Season 3 with S3E4 selected. |
| T6f output change | 2026-10-22 | — | — | — | — | PENDING | Not testable on this TV without changing its settings. |
| T7 stability | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` | 10 × Home → Detail → Resume 20 s → Back → Back | PASS | Every cycle was playing at 20 s and returned to Home. `sgnodes/all` at Home: 842 before, 842 after (0%). No BrightScript error, backtrace, or `[ERROR]` line in the run's console (2,707 lines), and no `[WARN]` during the cycles. |

### Defects found in run 9

1. **Client:** a credential renewal on a progressive original is a local
   reload of the same plan, and its rebuffer counts as a bandwidth stall:
   `onPlayer` (`source/playback/session.bs`) classes buffering as `reload`
   only before the plan's first frame, and the auto-quality grace applies only
   at a plan's start. Two renewals within 120 s (3-minute tokens) stepped Auto
   down from the original to a transcode (T1b). With 8-hour tokens this needs
   two local reloads of a played plan within two minutes.
2. **Client (minor):** Play committing a ladder seek once the credential has
   expired reloads with renewed headers but leaves playback paused (T1e). The
   renewal reload takes its autoplay from `state.player.paused`
   (`reload`), which the resume has not yet changed.
3. **Client / server:** run 8 defect 6 persists. Copy-remux loads whose
   playlist is still growing start about 8 s past `player_start_seconds`, and
   the seek back never lands: Roku resumes at 8.17 s after a 2.5–5 s buffer.
   Resume loses its rewind, and Play from the beginning skips the first 8 s.
   As AG-142 anticipated, the next step is the server's (a complete playlist
   at start, or `#EXT-X-START`).
4. **Client:** a viewer skip in that seek-back window is lost (T4b): the
   controls show and nothing seeks.
5. **Client:** an unanswered start that a newer attempt of the same player
   replaced (Try Anyway's six 502s, then Retry's start) is replayed once the
   player leaves, and the session it creates is stopped without a sample
   (T3d). Spec 9.5 says a session given up for a newer attempt is never
   stopped later; above the 5% threshold such a stop could write an older
   position.

Observations for review, not counted as defects: renewal reanchors on a copy
remux replay up to 4 s, because Roku starts the new load at 0.0 rather than at
`player_start_seconds`; when an identity change waits, the old identity's
jobs keep their backoff, so with the server back they were dropped after
10 s rather than sent (spec 9.5 allows either); the first Back during a start
hides the controls; the Home hero kept the previously focused title after a
profile change until focus moved (runs 7 and 8 noted the same after playback).

## Run 10 — W9 fixes, run 9 fixes, BrowseRows focus fix

Tenth hardware pass on the same TV: run 9's renewal, late-start, and outage
defects again (AG-143 to AG-154), the proxy origin (H1 step 2, H2 proxy-origin
HLS), the Home hero after a Continue Watching reorder, the section 1 playback
start target, and stability, against the lab stack on silo-server
`roku/client-support` at `8bafe15fb` (copy remux starts 20 s before the
requested position, AG-153) with 3-minute access tokens (left as found).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could not
  be heard remotely, so audibility is never claimed.
- **Build:** `d2ce1f2`, stock dev build (`npm run sideload:dev`), left
  installed. T7 used the `perf` build with a temporary local patch turning G1,
  G13, and G14 on (release-style builds keep them closed); it was reverted and
  is not committed.
- **Start state:** the dev app was signed in to the lab on the "no-PIN"
  profile; Roku Home, nothing playing, the HDMI 1 device idle (A-10).
- **Profiles:** "no-PIN"; "PIN" for T2c. Roku's caption mode read On and was
  not changed.
- **Lab:** only the sandbox's API container was stopped and started (host load
  2–14 on 32 cores when touched); it ended running and healthy. While it is down
  the header probe answers 502. The proxy node was enabled for T5 only, its
  public origin served by the second probe, and disabled again; the second probe
  was left running.
- **Sources:** the dev console (local time); ECP `query/media-player` every
  0.5 s; both header probes with `--playback-bodies` (3,275 API-origin lines,
  none answered 401; 374 proxy-origin lines); the lab server log for plan
  deliveries and stream timings.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a renewal, original on Auto (run 9 defect 1) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | deep link, 10 min 26 s, no seek | PASS | `renewing the media credential before it expires {"seconds":60}` six times, every 90 s, each a local reload: `content assigned after the stop` about 0.5 s, `VODStartComplete` about 1.8 s, 2.0–3.0 s without picture, 0–1.5 s replayed. No `quality_change`, no new plan, no `[WARN]`. Probe: 62 progress 200, 7 refreshes 200, no 401. |
| T1b ladder seeks after expiry (run 9 defect 2) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | paused 4 min 18 s, Fwd Fwd, OK, Play; paused 2 min 35 s (42 s past expiry), Rev Rev, Play | PASS | OK: renewed reload at the target (+262 s), first frame 2.7 s after OK, ECP `pause` at the target, progress `is_paused` true; Play then played from it. Rev Rev, Play: ECP went from `pause` at the old position straight to `startup`/`buffer` and `play` at the target (−239 s), with no sample playing at the old position. No 401. |
| T1c renewal, copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | deep link, 8 min 38 s | PASS | First ECP position 20.04 s against `player_start_seconds` 20.73 (no seek back). Six renewals, each `seek_reanchor` 200; the reanchored loads started at 18.5–20.7 s against 20.9–21.6 s; 1.5–2.0 s without picture, 0.2–3.0 s of source replayed. Probe: no 401, 91 progress 200, 605 segments 200; six 416s were Roku's range re-fetches of segments. |
| T2a subtitle change near expiry (AG-143) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls`, SRT sidecars | paused after a renewal, Off → English 21 s before the content's token expired; then, playing, English → SDH inside the renew window | PASS | Each change: `track_change` 200 adopted as one new load (no in-place retrack of the aging content) with headers from a newer token, subtitle sidecars 200 with the headers, cues shown, no 401. The playing change carried the renewal: no proactive renewal at the time it was due. |
| T2b quality change during an outage (AG-143) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001; `server_transcode_hls` | (1) 720p High, then `docker stop` 0.15 s later; (2) `docker stop`, then Auto while down | PASS | (1) The `quality_change` was answered before the stop finished and played; then `Video error … "kind":"server" … last_err:502`, `track_change` 502 at 0, 1, 2, 4, 8 s, "Reconnecting"; after `docker start` `track_change` 404, `start` 201 at the position with 720p kept, first frame 6 s after the start. (2) The media 502 came 50 ms before the key, so the reconnect went first and the Auto intent waited; after the restart `start` 201 (original, Auto applied), then the queued `quality_change` 200. No frozen error frame either time. |
| T2c profile switch, stop while down (AG-144) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | Switch Profile to PIN, Resume, `docker stop`, Back Back, `docker start` | PASS | The stop (with `X-Profile-Token`, its final position) got 502 at 0, 1, 2, 4, 8, 16 s and 200 at the next try after the restart; `playback job done {"kind":"stop"}`; no `identity_changed`, `superseded`, or `fenced` line. A renewal reload that met the stop was classed wrongly (defect 2). |
| T3a Resume start, copy remux (AG-153, AG-148) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episodes, `server_remux_hls` | three Detail Resumes past 5% | PASS | `start_position` = saved − 7 each time. First ECP positions against `player_start_seconds`: 20.05 vs 21.48, 18.05 vs 20.27, 19.84 vs 21.90; no seek back logged; first frame 2.3–3.1 s after the key. |
| T3b skip right after the first frame (AG-148) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | Right 0.25 s after the first frame | PASS | The controls the start showed hid at the first frame; Right sent `seek_reanchor` (+30 s) 200; the new load's first position 20.05 s against 20.19 (on target). |
| T3c Play from the start before and after the keyframe index | 2026-10-22 | 55R625 / 15.3.4 | TV | never-played library series episode, `server_remux_hls` | Detail Play twice, 100 s apart | PARTIAL | First: live playlist, first ECP position 8.041 s (start 0), `the load started past its start; seeking back`, then `the seek back landed {"position":0}` 130 ms later, but ECP stayed in `buffer` at 8.041 and played on from 8.166 (defect 3). Second: complete playlist, first position 0.575 s, no seek back. The first case stays open (AG-153). Another never-played episode was an `original_http` MKV, so it could not be used. |
| T4 outage, Try Anyway while down, Retry when back (AG-149) | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | `docker stop` 3 min 40 s; Retry and Try Anyway while down; `docker start`, Retry; Back 74 s after the first frame | PASS | Reconnect with "Reconnecting", then "Can't reach the server" 2 min later with Retry and Try Anyway. Retry: `system/info` 502, `the server is still unreachable`. Try Anyway: `start` 502 six times over 31.7 s, then the error again with both buttons. Retry once back: refresh, `start` 201, first frame 3.0 s after the key. The older session's queued progress and stop were dropped as superseded (spec 9.5). Back: one `DELETE` with its final position, and no `start` or `DELETE` in the 95 s after. |
| T5a H1 step 2, proxy origin | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001 as original and transcode; library series episode as remux | proxy node enabled; ladder seeks, skip (reanchor), subtitles, 720p, skips | PASS | Plans carried `"origin":"proxy"` (Stats: "from the proxy origin"). Proxy origin: 5 playlists, 361 segments, 8 progressive requests, none with `Authorization`, `X-Profile-Id`, or `X-Profile-Token`. API origin: 103 API requests and 3 subtitle sidecar downloads with `Authorization` and `X-Profile-Id`. |
| T5b H2, proxy-origin HLS | 2026-10-22 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls`; FX-001, `server_transcode_hls` | as T5a | PASS | Remux: `seek_reanchor` to a new proxy plan, first position 21.89 s against 22.07. Transcode: 720p `quality_change` to a proxy plan, first frame 3.1 s; a +60 s skip was a local seek with 1 s of buffering. Original: ladder seeks local. A subtitle change on the proxy remux reloaded (7.5 s without picture) instead of switching in place. |
| T5c renewal on a proxy-routed plan (AG-140) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001; library series episode | 3 min 22 s, 5 min 27 s, and 3 min 18 s on proxy plans | PARTIAL | No renewal ran and none was needed: the proxy path token lasts the plan's 24 h, and the access token refreshed three times with no 401. A real renewal on a proxy plan (a proxy 401 or 403, or within an hour of `expires_at`) could not be produced. |
| T5d routing back to the API origin | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001, `original_http` | proxy node disabled | PASS | The next plan had `"origin":"api"`, with stream requests on the API origin carrying the headers; the proxy-origin probe logged nothing more. |
| T6a Home hero, focus in the rows (AG-154) | 2026-10-22 | 55R625 / 15.3.4 | — | — | three returns from playback that reordered Continue Watching | PASS | Each time the ring and the hero described the same card once settled (one screenshot 2 s after the refresh caught the hero mid-change). After a deep link from Home the ring followed the card to its new index; after Home → Detail → player it stayed on the index. |
| T6b Home hero, focus in the top bar (AG-154) | 2026-10-22 | 55R625 / 15.3.4 | — | — | two returns from playback that reordered Continue Watching, focus on the Home pill | FAIL | Both times, with the top bar focused, the hero described the card now at the previously focused index; Down put the ring on the previously focused card at its new index, and the hero then changed to it (defect 1). |
| T7 playback start, `perf` build (section 1) | 2026-10-22 | 55R625 / 15.3.4 | TV | FX-001 `original_http`; library series episodes `server_remux_hls`; template-library MPEG-4 Part 2 AVI `server_transcode_hls` | Detail Play/Resume to `VODStartComplete`; 6 original, 15 remux, 6 transcode starts | FAIL | Original: median 2.12 s, max 3.90. Transcode: median 2.48 s, max 3.93. Copy remux: median 2.75 s, max 16.30; 2 of 15 over 8 s (11.72 and 16.30), both when the same episode was resumed again 6 s after Back. Five resumes 20 s apart took 1.46–3.09 s. Per step: key to `start` 201 0.26–0.97 s, `start` to first media request 0.17–0.49 s, first media request to first frame 0.72–15.56 s. The slow starts sat in `buffer` on a growing playlist, re-fetched segments by range, and played on time when the playlist completed. The server answered `start` in 250 ms, and its log shows only the expected plans. |
| T8 stability | 2026-10-22 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` | 10 × Home → Detail → Resume 20 s → Back → Back | PASS | Every cycle was playing at 20 s and returned to Home. `sgnodes/all` at Home: 954 before, 954 after (0%). No BrightScript error, backtrace, or `[ERROR]` line in the run's console (2,821 lines), and no `[WARN]` during the cycles. |

### Defects found in run 10

1. **Client:** with the top bar focused, a Continue Watching reorder on the
   return from playback leaves the Home hero on the card now at the old
   index, while the `RowList`'s focus follows the card to its new index
   (T6b, twice). AG-154's open case: the unfocused list takes the jump but
   does not report it through `rowItemFocused`, and BrowseRows then keeps the
   stale report. The hero corrects itself when focus enters the rows.
2. **Client:** `playback.video.httpStatus` (`source/playback/video.bs`) misses
   the status in Roku's error −1 text, `…HTTP response code said error response
   code:(<url>):502:…`, because the status follows the URL. So a progressive
   original's 502 after the first frame is classed `http` (status 0) and sent as
   `failure_recovery` `http_failure`, which excludes the route, instead of spec
   9.6's reconnect (T2c). Here the replan also got 502, and the reconnect
   followed.
3. **Client:** `checkSeekBack` (`source/playback/session.bs`) logs `the seek
   back landed` on the first position reading below where the seek back
   began, even before the node plays again. Roku reports position 0 while it
   rebuffers after the seek, so it logged a landing at 0 s, 130 ms after the
   seek. ECP showed playback resuming at 8.17 s (T3c), so the log contradicts
   ECP.
4. **Client:** the startup stall clock restarts when a plan is adopted
   (`restartStall` in `adopt`), so the wait for the `Video` node to stop
   (3.3 s here) counts against the 20 s budget. After a cold first start of
   FX-001 stalled, the replacement remux's first frame came 1.7 s after its
   clock had already sent `failure_recovery` (16.9 s after its content was
   assigned), and the chain went on to a transcode and back to the original
   before the viewer left. The cold start itself was the lab's: the first
   original read from byte 0 delivered 5.6 MB in 23 s, and a retry 2 minutes
   later started in 1.9 s.
5. **Client / server:** a copy remux resumed again a few seconds after the
   previous session of the same episode stopped can take 8–16 s to its first
   frame (T7). Roku buffers the growing playlist, re-fetches segments by
   range, and starts when the playlist completes. The cause is not
   established.
6. **Client (minor):** the "Reconnecting. Playback will resume
   automatically." chip is drawn under the Options panel, so with the panel
   open only its last word shows (spec 5.7: notices show at the top right
   whatever is open).

Observations for review, not counted as defects: the `perf` build has no
app-side start timing (info logs compile out), so section 1's per-step
breakdown came from the probes, the server log, and Roku's beacons, whose
`VODStartInitiate` follows content assignment rather than the keypress (one
deep-link start reported 16.8 s for a 2.7 s start); remux first frames
reported `audioFormat` `aac_adts`; Up Next opening at the credits closed the
Options panel and took the keys meant for it (toggling the session's
auto-play); Down from the Video tab twice entered its list one row below the
current choice; the lab's host load reached 42–45 during T5 from other
users' CI.

## Run 11 — format matrix

Eleventh hardware pass on the same TV: the playback format matrix (H3, H4, H5, H6, H7, H9, H10, H11, H12)
with the stock gates and, where a gate is off, with that gate overridden; the no-audio Options panel
(AG-132) and the library list with three libraries (AG-133). Lab stack on silo-server
`roku/client-support` at `8bafe15fb`, 1-hour access tokens, proxy node disabled (every media URL on the API
origin behind the header probe).

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio could not be heard and the TV's
  picture and HDR/DV badge could not be seen remotely, so neither is claimed.
- **Build:** dev build of `5ae4fbf` with a temporary local patch (not committed): debug-only logging of
  every probe answer, the gate results, the plan without URLs or tokens, and, every 10 s during playback,
  `GetVideoMode()`, `GetDisplayProperties()`, `videoFormat`, `audioFormat`, `IsPassthruCodecActive()`,
  `GetAudioOutputChannel()`, `GetAudioDecodeInfo()`, `streamInfo` and `streamingSegment` without their
  URLs; an ECP input that sets a `playback.gates.evaluate` context (`overrides`, and for G5 the provisional
  `dolbyVisionModels` entry; predicates unchanged); and a switch that skips the Auto quality step-down,
  used only where a row says "Auto off". The stock dev build was reinstalled at the end.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing,
  the HDMI 1 device idle (A-10). Deep links started every title (Resume where the title had a position).
- **Lab:** no container was touched. The path to the Roku (TV Wi-Fi, the probe host, a VPN link to
  the lab host) carried 7–35 Mbps when measured from the probe host, and the Roku measured 7.8–24.6 Mbps on
  originals. Sources of 35–55 Mbps rebuffered within about 10 s and Auto stepped down to an SDR
  transcode; 16–21 Mbps sources rebuffered now and then; sources up to about 9 Mbps played cleanly. Those
  stalls are the lab's, not the device's.
- **Probe (first recorded run on this TV):** as `tests/fixtures/probes/dev-tv-tcl-55r625.json` except
  `CanDecodeAudio` eac3 `Atmos: 1`, `flac`, `opus`, and `pcm` answered yes. `GetModel()` returns `A000X`
  (ECP reports A109X). `GetDisplayProperties()`: Dolby Vision, HDR10, HLG yes; HDR10+ no; internal.
  `GetVideoMode()` read `2160p60` outside playback and in all 373 samples during HDR10, HLG, and Dolby
  Vision playback; no `b10` or `Dv` suffix. `IsPassthruCodecActive()` false and
  `GetAudioOutputChannel()` "5.1 surround" throughout; `streamingSegment.hdrMode` was `hdr10` only on the
  HDR10 MP4 original and `unknown` on every HLS remux. Node count: 952–974 at Home, 381–386 while playing.
- **Sources:** the dev console, ECP `query/media-player` every 0.5 s, and the API-origin header probe with
  `--playback-bodies` (37 starts, 28 replans, 37 stops; 2,160 media requests, all with `Authorization`).

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H4, MP4 original | 2026-10-22 | 55R625 / 15.3.4 | TV | MP4 HEVC Main 10 2160p HDR10, AC-3 2.0, 35 Mbps, 90 s | stock gates; deep link twice | PARTIAL | `original_http` (`validated_original_playback`), HDR10 claimed. First frame 8.2 and 7.6 s after the link; `videoFormat` `hevc`, `audioFormat` `ac3`. Both stalled at 6–8 s (Roku measured 7.8–12.3 Mbps) and Auto moved to a 1080p SDR transcode, which played to the end; +30 s and −10 s seeks there took 1 s and 0.5 s. |
| H4, MKV original | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p, Dolby Vision P8.1 with HDR10 base layer, E-AC-3 JOC 5.1, 16.6 Mbps | G7 on (the only route to an HEVC Main 10 MKV original among the fixtures) | PARTIAL | `original_http` (`client_dv8_base_layer`), HDR10. First frame 18.6 s (cold read); then 69 s without a stall, +30 s seek 1 s, one 2.5 s stall, −10 s seek 0.5 s, about 2 min in all. `videoFormat` `hevc`. No 60 fps or level 5.2/6.x source exists in the lab. |
| H4/H5, HDR10 MKV with DTS-HD MA | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p HDR10, DTS-HD MA 7.1 default plus an AC-3 2.0 commentary, 40 Mbps | stock gates; then the AC-3 track from the Down panel | PARTIAL | `server_remux_hls` (`hls_audio_adaptation`): HEVC HDR10 copied, AAC 5.1 from the DTS-HD MA track; first frame 9.4 s; `hevc_b`/`aac_adts`; stall at 6.2 s, then Auto. The AC-3 track gave `server_remux_hls` (`hls_packaging_required`) with AC-3 2.0 copied, not `original_http`: a non-default track needs `client_selected_audio_track_v1`, which the client never sends. |
| H5, HLG original | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 1080p HLG, AAC 2.0, 3.6 Mbps, 20 s | stock gates; twice, one −10 s seek | PARTIAL | `original_http`, HLG claimed. First frame 3.3 s, then 13.5 s (the lab took 14 s for the file's 9 MB). Played to the end both times; the seek took 0.5 s. `hevc`/`aac`. HLG output not observable. |
| H5, HLG through an HLS remux | 2026-10-22 | 55R625 / 15.3.4 | TV | as above | G2 off (no HEVC on `original_http`) | PARTIAL | `server_remux_hls` (`hls_packaging_required`), HEVC copied, HLG claimed. First frame 1.6 s, played to the end without a stall; `hevc_b`/`aac_adts`. HLG output not observable. |
| H3, P5, stock | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p Dolby Vision P5 (level 6), E-AC-3 JOC 5.1, 17 Mbps | stock gates | PASS | `server_transcode_hls` (`quality_auto_source`): 1080p SDR H.264 with "HDR video is tone-mapped to SDR", AAC 5.1. First frame 8.8 s; a stall at 9.6 s stepped down to 720p; +30 s seek 6.3 s, −10 s 1 s; then 85 s without a stall. |
| H3, P5, G5 | 2026-10-22 | 55R625 / 15.3.4 | TV | as above | G5 on: (a) alone, (b) with the provisional model entry `A000X` | PARTIAL | (a) G5 on but its predicate false (`GetVideoMode()` has no `Dv`), so no claim and the same transcode. (b) `server_remux_hls` with DV (`native_profile_supported`), E-AC-3 copied, TS segments. Try 1: no first frame; the buffer reached 74% in 28 s, then `decoder_no_output` and a `copy_routes_exhausted` transcode (defect 1). Try 2: first frame 16.6 s, `hevc_b`/`eac3`, started 9.0 s late and sought back, buffered 20 s, then Auto. DV output not observable; mode stayed `2160p60`. |
| H3, P5, G5 and G6 | 2026-10-22 | 55R625 / 15.3.4 | TV | as above | G5 with `A000X`, G6 on; Auto off | PARTIAL | `original_http` with DV (`validated_original_playback`). First frame 15.1 s; 97 s without a stall; +30 s seek 0.5 s. `hevc`/`eac3`. P5 has no HDR10 base layer, so whether the picture was DV (or tinted) needs eyes on the TV. |
| H3, P8.1 with E-AC-3 JOC, stock | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p Dolby Vision P8.1 (HDR10 base layer), E-AC-3 JOC 5.1, 16.6 Mbps | stock gates | PARTIAL | `server_remux_hls` with the server's DV strip (`server_dv7_to_hdr10`, "Dolby Vision metadata is removed and the validated HDR10 base layer is preserved"), E-AC-3 copied. First frame 8.6 s, `hevc_b`/`eac3`; started 8.0 s late; stall at 15.7 s, then Auto. |
| H3, P8.1 with E-AC-3 JOC, G5 | 2026-10-22 | 55R625 / 15.3.4 | TV | as above | G5 with `A000X`; again with Auto off | PARTIAL | `server_remux_hls` with DV, E-AC-3 copied. First frame 3.8 s and 2.4 s; `hevc_b`/`eac3`. Rebuffers of 3.5 and 4 s brought Auto; with Auto off it played 2 min with about eight rebuffers. DV output not observable. |
| H3, P8.1 with E-AC-3 JOC, G7 | 2026-10-22 | 55R625 / 15.3.4 | TV | as above | G7 on | PARTIAL | `original_http` (`client_dv8_base_layer`), HDR10 base layer, E-AC-3 copied; see the H4 MKV row. Base-layer ID 1 only; IDs 4 and 2 have no fixture. |
| H3, P8.1 with E-AC-3 JOC, G5 and G6 | 2026-10-22 | 55R625 / 15.3.4 | TV | as above | G5 with `A000X`, G6 on; Auto off | PARTIAL | `original_http` with DV. Try 1: the first frame came 0.6 s after the 20 s startup clock had sent `decoder_no_output`, so the DV remux replaced it (defect 1). Try 2: first frame 12.2 s, 79 s without a stall, then lab stalls; local seeks. `hevc`/`eac3`. DV output not observable. |
| H3/H11, P8.1 with TrueHD Atmos, stock | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p Dolby Vision P8.1, TrueHD Atmos 7.1 plus AC-3 5.1 (and AC-3 2.0 in a second file), 47 and 55 Mbps | stock gates | PARTIAL | The client sent the AC-3 5.1 track (index 1); `server_remux_hls`, HDR10 base layer, AC-3 copied; first frame 8.8 s and 7.6 s, `hevc_b`/`ac3`; stalls, then Auto. With G7 on, still the remux (the AC-3 track is not the default). |
| H11, TrueHD reaching the player | 2026-10-22 | 55R625 / 15.3.4 | TV | as above (47 Mbps) | TrueHD picked in the Down panel; Auto on, then off | PASS | Auto on: a transcode with AAC 5.1. Auto off: `server_remux_hls` (`hls_audio_adaptation`), "converted to AAC for HLS delivery", `atmos_preserved: false`, 6 channels; `audioFormat` `aac_adts`. That remux then buffered over 20 s (lab) and went to a transcode. |
| H3, P8.1 with TrueHD Atmos, G5 | 2026-10-22 | 55R625 / 15.3.4 | TV | as above (47 Mbps) | G5 with `A000X`; Auto off | PARTIAL | `server_remux_hls` with DV, AC-3 5.1 copied; first frame 18.9 s, `hevc_b`/`ac3`. After 8 s it rebuffered; the buffer was full 12 s later but playback did not resume, and at 20 s `decoder_no_output` brought an HDR10 remux without DV. |
| H9, E-AC-3 JOC original | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV H.264 1080p, E-AC-3 JOC 5.1, 8.5 Mbps | stock gates | PARTIAL | `original_http`, E-AC-3 copied. First frame 6.1 s; over 2 min with seeks of 0.5 s. `audioFormat` `eac3`, the track's format "Dolby Digital Plus" (no JOC flag), passthrough inactive, output "5.1 surround". Atmos rendering not observable. |
| H9, E-AC-3 JOC copy remux | 2026-10-22 | 55R625 / 15.3.4 | TV | the P5 and P8.1 rows above | stock and G5 | PARTIAL | E-AC-3 JOC copied into TS remuxes; `audioFormat` `eac3` each time. Atmos not observable. |
| H10/H11, DTS-HD MA | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p Dolby Vision P8.1 (one also HDR10+), DTS-HD MA 5.1 (53 Mbps) and 7.1 (42 Mbps) | stock gates; then G9 on | PASS | Both `server_remux_hls` (`hls_audio_adaptation`): HDR10 base layer and AAC 5.1 (7.1 down to 5.1); first frame 12.0 and 8.7 s, `aac_adts`; stalls, then Auto. G9 on: its predicate (`CanDecodeAudio` dts, `PassThru: 1`, `ChCnt: 6`) is false with the TV as sink, so no `dts` claim and the same route. No DTS sink exists in this lab. |
| H6, AV1 | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV AV1 Main 10-bit 1080p, HE-AAC 2.0, 2.5 Mbps | stock gates; then G10 on | PASS | `server_transcode_hls` (`quality_auto_source`), H.264 and AAC 2.0; first frame 2.6 s; over 2 min, seeks 0.5 s. G10 on: the bare AV1 probe answers no, so no claim and the same transcode. |
| H7, VP9, stock | 2026-10-22 | 55R625 / 15.3.4 | TV | MKV VP9 profile 0 1080p SDR, AAC 5.1, 2.5 Mbps | stock gates | PASS | `server_transcode_hls`, H.264 and AAC 5.1; first frame 2.1 s; over 2 min, seeks 0.5 s. |
| H7, VP9, G11 | 2026-10-22 | 55R625 / 15.3.4 | TV | as above | G11 on | PASS | `original_http` with `vp9` and AAC 5.1 copied; first frame 2.5 s; `videoFormat` `vp9`, `audioFormat` `aac`; over 2.5 min, seeks without visible buffering. VP9 profile 2 (HDR) has no fixture. |
| H12, FLAC, stock | 2026-10-23 | 55R625 / 15.3.4 | TV | MKV H.264 1080p, FLAC 1.0 24-bit, 21 Mbps | stock gates | PARTIAL | `server_remux_hls` (`hls_audio_adaptation`), H.264 copied, AAC 1.0; first frame 5.8 s; +30 s and −10 s were `seek_reanchor`s (4.5 and 8 s); then a stall and Auto. |
| H12, FLAC, G12 | 2026-10-23 | 55R625 / 15.3.4 | TV | as above | G12 on (sends `flac`, `opus`, `pcm_s16le`, `pcm_s24le`: every probe answered yes) | PASS | `original_http`, `audioFormat` `flac`; first frame 8.6 s; over 2 min, seeks 0.5 s. Mono only: multichannel FLAC, Opus, and PCM have no fixture. |
| AG-132, title without audio | 2026-10-23 | 55R625 / 15.3.4 | TV | MKV H.264 1080p, no audio track, 60 s | stock gates; Down, and the controls' Options button | PASS | `original_http`, `audioFormat` `none`. Tabs Info, Stats, Video, Subtitles, no Audio; Down opened on Video (no audio, no subtitle track); the button opened on Info; the controls showed no Audio button; Left and Right moved along the four tabs; Back closed the panel with focus on Options. Stats reads "Recipe: h264/ ch" (defect 3). `*` opened the TV's own menu, as spec 5.9 says. |
| AG-133, three libraries | 2026-10-23 | 55R625 / 15.3.4 | — | — | Movies tab; slow and quick moves; Down and Right sent back to back | PASS | Rows and both headers measure a 21–22 px cap height (Inter 28 px), the hint two 24 px lines. After Down, Up, Down the highlight and the sections both showed the second library; Down and Right sent together landed on the third library's Recommended. Back from the sections closed the list with focus on the Movies tab; Back again exited the app from Home's bar (spec 5.3). The sections header truncates a 17-character library name. |

### Defects found in run 11

1. **Client:** the 20 s stall clock reports `decoder_no_output` whenever any media input arrived, including
   a slow start whose buffer was still filling (P5 remux: 74% after 28 s) and a rebuffer whose buffer was
   full but had not resumed (P8.1 TrueHD remux). The server then excludes the route: `copy_routes_exhausted`
   to an SDR transcode, or the DV remux replaced by an HDR10 one. With run 10's defect 4 (the clock counts
   the wait before content is assigned), a DV original whose first frame came 20.6 s after its plan was
   failed 0.6 s before that frame.
2. **Client:** run 10's defect 3 again: `the seek back landed {"position":0}` 165 ms after a late start's
   seek back, while ECP played on from 8.16 s.
3. **Client (minor):** Stats shows "Recipe: h264/ ch" for a title without audio (empty codec and channels).
4. **Client (minor):** after a deep-link player returned to Home and Continue Watching reordered, four
   Left presses left the ring on the first card and the hero on the fourth until the next key (AG-154's
   case, here with focus in the rows); not retried.
5. **Client (minor):** the "Buffering" chip is drawn under the Options panel's edge (run 10 defect 6).
6. **Server:** a `quality_change` replan sent just before the viewer's stop, and answered after it, got 500
   (a stopped session should answer 404 or 410).

Observations for review, not counted as defects: Auto's step-down logs nothing, so a `quality_change`
appears in the console without its cause; `GetModel()` reads `A000X` on this TCL, so G5's model-keyed
entry would name a value other Roku TVs may share; `streamingSegment.hdrMode` cannot report HDR on HLS
here; key presses over the relay land 0.5–6 s after they are sent.

### What run 11 shows for the gates on the Roku TV cohort

- **G2, G3, G8 (on):** HEVC Main 10 4K originals decode (the MKV played about 2 min; the 35 Mbps MP4
  outran the lab), HDR10 and HLG originals and remuxes play, and E-AC-3 JOC is copied and decoded on
  originals and remuxes; HDR output itself was not observed.
- **G5 (off):** DV P5 and P8.1 copy remuxes decode, but `GetVideoMode()` never shows `Dv`, during playback
  or outside it, so only the model-keyed path can satisfy the predicate, and the model value is `A000X`.
  Stays off until someone confirms the TV's DV indicator and the predicate question is decided.
- **G6 (off):** P5 and P8.1 MKV originals with DV claims decode and played 79–97 s; stays off with G5.
- **G7 (off):** the base-layer original (ID 1) played on `original_http`; it replaces the stock HDR10 remux
  for P8.1 files whose default audio track the TV decodes. IDs 4 and 2 untested.
- **G9, G10 (off):** their predicates are false on this TV (no DTS sink, no AV1 decoder); they stay off.
- **G11 (off):** VP9 profile 0 on `original_http` passed; profile 2 untested.
- **G12 (off):** mono FLAC on `original_http` passed; the gate also sends Opus and two PCM names, which
  were not tested.

## Run 12 — resume playlist A/B, run 10 and run 11 fix checks

Twelfth hardware pass on the same TV: an A/B of server prototype 10's resume playlist (AG-168), the device checks
of the run 10 fixes (AG-156 to AG-161) and the run 11 fixes (AG-163 to AG-166), and stability. Lab stack on
silo-server `roku/client-support` at `c040f7a5a`, 1-hour access tokens, proxy node disabled.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio, the picture, and the HDR/DV badge could not
  be observed remotely and are not claimed.
- **Build:** stock dev build of `5126d6d`, installed at the start and again after T3c–T3e, and left installed. T3c–T3e
  used a temporary local patch (not committed, reverted): an ECP input that sets a debug `playback.gates.evaluate`
  context (G5 with the provisional `A000X` model entry; G5 and G6), and an info line for every `bufferingStatus`
  reading.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10). Ended the same way.
- **Lab:** the resume-playlist switch was absent (new behaviour), then `off` (old) for the B pass, then removed. Only
  the sandbox's API container was stopped and started, twice (host load under 2 on 32 cores); it ended running and
  healthy. Four first starts kept the growing playlist because their file had no keyframe index yet (one T1a
  episode, T2c's played episode, the P5 remux, a 4K HEVC episode); the two loaded again (a Resume and a reanchor) got
  the keyframe playlist, as AG-168 describes.
- **Sources:** the dev console, ECP `query/media-player` every 0.5 s, a timed ECP relay for keys and inputs (key times
  are its ECP accept times), the API-origin header probe with `--playback-bodies` (2,672 lines; every media request
  carried `Authorization`), and the lab's switch, keyframe-playlist, and plan log lines.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a resume playlist, new (AG-168) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episodes, H.264 1080p MKV, `server_remux_hls` | switch absent; deep-link Resumes past 5%, 15–20 s each, Back; seven loads | PASS | Six loads got the keyframe playlist (VOD, 358–481 entries at first fetch, ECP `is_live` false): first ECP position 0.39–1.93 s before `player_start_seconds`, first frame 1.29–3.04 s after the input (median 1.96 s), no seek back. Two of them re-resumed the same episode 8.3 and 6.1 s after Back: 1.53 and 1.29 s. The first resume of one episode (no keyframe index yet) got the growing playlist (162 entries, live): 3.84 s early, 1.95 s. |
| T1b resume playlist, old (AG-168) | 2026-10-23 | 55R625 / 15.3.4 | TV | as T1a | switch `off`; the same sequence; six loads | PASS | Every load got the growing playlist (116–246 entries at first fetch, live), server `planned=false` 9 times. First positions 1.80 s early to 1.95 s late, first frame 1.84–3.00 s (median 2.49 s), no seek back. Re-resumes 4.1 and 6.3 s after Back: 1.84 and 2.47 s. Run 10's 8–16 s re-resume did not recur in either mode. |
| T1c skips on a copy remux (AG-168) | 2026-10-23 | 55R625 / 15.3.4 | TV | as T1a | Right (+30 s); Left ×3 merged (−30 s), 6 s after the first frame | PASS | New: Right was a local seek inside the plan's seek window (4.0 s of buffering, no replan); two Left ×3 sent `seek_reanchor` 200 and got keyframe playlists, landing 0.99 and 0.03 s before their start, first frame 3.47 and 3.16 s after the first Left. Old: Right and two Left ×3 each sent `seek_reanchor`; the growing playlist was already complete at Roku's first fetch; 0.11–3.14 s early, 2.45–3.20 s. |
| T2a Home hero, focus in the top bar (AG-156) | 2026-10-23 | 55R625 / 15.3.4 | — | — | two returns from deep-link playback that moved the focused Continue Watching card from index 2 to 3, then 3 to 4, focus on the Home pill | PASS | Both times the hero kept the previously focused card with focus on the pill, and Down put the ring on that card at its new index with the hero unchanged. While the pill has focus the row shows from its first card. |
| T2b media 502 after the first frame, copy remux (AG-157) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls` | `docker stop` 12 s after the first frame; `docker start` 41 s later | PASS | `Video error … "error":-5,"kind":"server" … last_err:502 …,"status":502`; "Reconnecting"; `track_change` 502 at 0, 1, 3, 7, 15, 30 s; after the restart `track_change` 404, `start` 201 at the position, first frame 1.6 s after the `start`. No `failure_recovery`. |
| T2b' outage during a progressive original (AG-157) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` | `docker stop`; after 72 s from Roku's buffer, Right (+30 s) | PARTIAL | Roku raised no Video error: 1,150 range requests answered 502 in about 20 s. `no progress for 20 s {"buffer":33,"kind":"stall"}` was followed by `track_change` (API unreachable), no `failure_recovery`. The error −1 form AG-157 parses was not produced. The tester's second Back exited the player during the outage; the queued progress and the stop landed after the restart. |
| T2c seek-back log against ECP (AG-158) | 2026-10-23 | 55R625 / 15.3.4 | TV | played library series episode (start at 0); DV P5 fixture (T3c) | Play before the file's keyframe index existed | PASS | Both started 8–9 s late on a growing playlist: `the load started past its start; seeking back {"position":8.041,"start":0}`, then `the seek back did not land {"position":8.166,"start":0}`; ECP played on from 8.166 s. The P5 remux: `did not land {"position":9.158}`, ECP 9.158 s. No `landed` case occurred. |
| T2d cold original start (AG-159) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-003, FX-018, FX-032, FLAC fixture, MP4 HEVC Main 10 35 Mbps, DV P5 (T3d) | first starts of the run | PARTIAL | No start stalled for 20 s, so the cascade case did not arise: first frames 2.9–11.8 s, the DV original 18.1 s with its buffer rising, and no `failure_recovery` anywhere in the run. The one replacement load after a stop wait (an Auto `quality_change` on the 35 Mbps original): `content assigned after the stop {"ms":958}`, first frame 1.6 s later, no further replan. |
| T2e status chip with Options open (AG-161, AG-164) | 2026-10-23 | 55R625 / 15.3.4 | TV | T2b's episode; MP4 HEVC Main 10 2160p HDR10, AC-3 2.0, 35 Mbps | Down during the reconnect; Down during a rebuffer | PASS | "Reconnecting. Playback will resume automatically." and "Buffering" each showed whole under the panel's bottom edge at the right; with the panel closed, the reconnect message was back at the top right. Down opened Audio on the two-track episode and Video on the one-track original. |
| T3a VP9 profile 0, stock (AG-166) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-032, MKV VP9 profile 0 1080p, AAC 5.1 | stock gates, deep link | PASS | `original_http` (`validated_original_playback`), `video_codec` vp9; first frame 2.9 s; `videoFormat` `vp9`. |
| T3b FLAC, stock (AG-166) | 2026-10-23 | 55R625 / 15.3.4 | TV | MKV H.264 1080p, FLAC 1.0 24-bit, 21 Mbps | stock gates, deep link | PASS | `original_http`, `audio_codec` flac, 1 channel; first frame 8.2 s from 0; `audioFormat` `flac`. |
| T3c DV P5 copy remux, G5 (AG-165) | 2026-10-23 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p Dolby Vision P5, E-AC-3 JOC 5.1, 17 Mbps | G5 with `A000X` (temporary patch) | PASS | `server_remux_hls` with DV, E-AC-3 copied; buffer 0 to 100% in 5.7 s, first frame 6.8 s (`hevc_b`/`eac3`); 40 s without a rebuffer; no `no progress` line, no replan, no route exclusion. The slow-filling start of run 11 did not recur on today's link. |
| T3d DV P5 original, G5 and G6 (AG-165, AG-159) | 2026-10-23 | 55R625 / 15.3.4 | TV | as T3c | G5 with `A000X`, G6 (temporary patch) | PASS | `original_http` with DV; the buffer rose steadily from 0 to 100% over 17.6 s and the first frame came 18.1 s after the input with no replan and no `no progress` line before it (run 11 lost this start 0.6 s before its first frame); 40 s after it without a stall. |
| T3e `bufferingStatus` scale (AG-165) | 2026-10-23 | 55R625 / 15.3.4 | TV | T3c and T3d | info line per reading (temporary patch) | PASS | `percentage` runs 0–100: 80 against ECP's `current="702"`–`"865"` (tenths of a percent), 100 against 1000. |
| T3f Stats without audio (AG-163) | 2026-10-23 | 55R625 / 15.3.4 | TV | MKV H.264 1080p, no audio track, 60 s | Down, then the Stats tab | PASS | "Recipe: h264, no audio". |
| T4 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC; FX-032; MP4 HEVC Main 10 35 Mbps (see defect 1) | 10 × Home → Detail → Resume 20 s → Back → Back | PASS | Every cycle played and returned to Home; Resume to first frame 1.7–11.8 s. `sgnodes/all` at Home: 982 before, 983 after (+0.1%). No BrightScript error, backtrace, or `[ERROR]` line in the run's console (1,873 lines). |

### Defects found in run 12

1. **Client (minor):** after Home → Detail → Resume → Back → Back, Home's focus lands on the Continue Watching
   card now at the previously focused index, not on the same item (spec 5.3). The title just played moves to the
   front, so the ten T4 cycles rotated through three titles. 0.3 s after the second Back the ring was on the first
   card (the title just played) while the hero showed the card at the old index; 4 s later both were on the card at
   the old index. Returns from deep-link playback follow the item (T2a). Run 10's T6a recorded the same
   "stayed on the index" without classing it.
2. **Server (observation, AG-168):** a resume before the file's keyframe index exists keeps the growing playlist.
   On a 4K HEVC copy remux the first playlist held five segments and Roku started 18 s before
   `player_start_seconds` (25 s before the saved position instead of 7); the client logs nothing for an early start.
   Building the index at scan time (AG-153 decision 2) would remove the case.

Observations for review, not counted as defects: with the keyframe playlist a forward skip inside the playlist is
a local seek, so a copy remux reanchors only for targets outside the plan's window; a progressive original's
refused range requests raise no Video error on this TV (T2b'), so the stall clock is its only recovery path; a
growing playlist the server's throttler paused stayed without `#EXT-X-ENDLIST` and Roku re-fetched it every 2–3 s;
two Auto `quality_change` replans that the viewer's stop overtook were answered 404, as prototype 9 intended
(AG-167); five segment requests in flight at a stop were answered 410.

## Run 13 — Home return focus, T6b, and G7 on the stock build

Thirteenth hardware pass on the same TV: the device checks of AG-170 (Home return focus) and AG-171 (G7 on the Roku TV
cohort), T6b again (AG-156), and stability. Lab stack on silo-server `roku/client-support` at `c166d16d1`, which
advertises `dv8_base_layer_compatibility_ids_v1`; proxy node disabled.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio, the picture, and the HDR badge could not be
  observed remotely and are not claimed.
- **Build:** stock dev build of `24a7ce8`, no override and no patch, installed at the start and left installed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10). Ended the same way.
- **Lab:** no container was touched; the run only played titles.
- **Sources:** the dev console, ECP `query/media-player` every 0.5 s, a timed ECP relay (key times are its ECP accept
  times), screenshots taken at fixed delays after a key's accept (a capture completes about 1.2 s after its request),
  and the API-origin header probe with `--playback-bodies` (17 starts, 1 replan, 17 stops; 117 media requests, all with
  `Authorization`).

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 Home return focus (AG-170) | 2026-10-23 | 55R625 / 15.3.4 | TV | Continue Watching titles: two H.264 1080p MKV feature originals with E-AC-3 5.1, the DV P8.1 episode of T3, and an H.264 1080p title of 60 s without audio | Home → Continue Watching's third card → Detail → Resume 20 s → Back → Back; screenshots 0.3 s and 4 s after the second Back | PASS | Three returns that moved the title just played from third to first, one per title: at 0.3 s and 4 s the ring and the hero were both on that title, now first. In two the row loaded again 8 ms after the second Back, before the 0.3 s screenshot; in the third nothing loaded early, the reorder came with the quiet refresh (layout at 3.0 s, the row at 3.3 s), and focus followed the title to the front. A fourth return, of the 60 s title, which ran to 91% because the tester's Back came late, took that title out of the row: focus went to the same place (spec 5.3); at 0.3 s the hero still showed the removed title while the ring was on the card now there, as the hero waits 0.15 s and cross-fades for 0.5 s; at 4 s both were on that card. T4 repeats the check ten times. |
| T2 T6b, focus in the top bar (AG-156) | 2026-10-23 | 55R625 / 15.3.4 | TV | an H.264 feature original and the DV P8.1 episode | the same return, with Up sent straight after the second Back; Down about 7 s later | PASS | Twice: Up was accepted about 65 ms after Back, and the reorder came 3.3–3.5 s after Back (quiet refresh). With the Home pill focused the hero showed the title just played before and after the reorder; Down put the ring on that title, now first, with the hero unchanged, 0.3 s and 2 s after Down. |
| T3 G7, P8.1 with E-AC-3 JOC (AG-171) | 2026-10-23 | 55R625 / 15.3.4 | TV | MKV HEVC Main 10 2160p Dolby Vision P8.1 (base-layer ID 1), E-AC-3 JOC 5.1, 16.6 Mbps | stock gates, no override; deep link (`input`) with a saved position; Right (+30 s), then Left ×3 (−30 s) | PARTIAL | The start body's `original_http` carried `validated_claims` [`client_dv8_base_layer_fallback_v1`] and `dv8_base_layer_compatibility_ids` [1]. Plan `original_http` (`client_dv8_base_layer`), `hdr10`, `dolby_vision` false, E-AC-3 6 channels copied. First frame 12.1 s after the link; `videoFormat` `hevc`, `audioFormat` `eac3`, ECP 3840x2160 at 24 fps, `GetVideoMode()` `2160p60`. 45 s without a stall; +30 s played again about 6 s after Right, −30 s 1.6 s after the last Left. Six rebuffers of 0.5–1.5 s came between and after the seeks, and 98 s after the first frame a rebuffer that held a full buffer without resuming lasted until Auto's `quality_change` (Roku's estimate 11,637 kbps; the body again carried the claim and [1]) moved to `server_transcode_hls` (`quality_bandwidth_limit`, H.264 SDR, AAC 6 channels): first frame 13.5 s after that plan (`mpeg4_10b`/`aac_adts`), then 65 s without a stall. The stalls are the lab link's (run 11), not the device's. Five Resumes of the same episode from Detail (T1, T2, T4) also got `original_http` (`client_dv8_base_layer`), first frame 13.9–21.5 s after Resume. All 18 start and replan bodies of the run carried the claim with [1]. HDR10 output not observable. |
| T4 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | T1's titles | 10 × Home → Detail → Resume 20 s → Back → Back, from Continue Watching's third card | PASS | Every cycle played (first frame 5.8–20.9 s after Resume) and returned to Home with the ring and the hero on the title just played, now first, at 0.3 s and 4 s, rotating through three titles as the reorder predicts (AG-170's T4). The row loaded again 41–55 ms after each second Back. `sgnodes/all` at Home: 974 before, 975 after (+0.1%). No BrightScript error, backtrace, `[ERROR]`, or `[WARN]` line in the run's console (890 lines). |

### Defects found in run 13

None.

Observations for review, not counted as defects: BrowseRows still logs no reason for a row load, so the early reload (13
of 16 returns, a row request without a layout request) is only inferred to be `onArtFailed`, since cards with failed
artwork sat in the row; Play on the 60 s title with a saved position under the 30 s Resume threshold started at 0, because
the client sends no start position and the server planned `player_start_seconds` 0, while the code comment says Android TV
and tvOS start such a Play at the saved position; the rebuffer that kept a full buffer without resuming matches run 11's
TrueHD remux case, and here Auto's replan came 6.5 s after it began, before the 20 s stall clock.

## Run 14 — W10 fixes, held replan at a profile change, refused media

Fourteenth hardware pass on the same TV: plan 6.6's profile change during an in-flight replan (run 9's T6c was
PARTIAL), the original's outage as a network failure (AG-169 decision 3), the W10 device checks (AG-177 to
AG-180), and stability, using the probe's lab modes (AG-175). Lab stack on silo-server `roku/client-support` at
`c166d16d1`, 1-hour access tokens, proxy node disabled.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio, the picture, and the HDR badge could not be
  observed remotely and are not claimed.
- **Build:** stock dev build of `fcf7f2d`, no override and no patch, installed at the start and left installed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. A-10 was applied again before T4c, which relaunched
  the app. Ended on Roku Home with nothing playing.
- **Lab:** no container was touched. `hold-replan.8180` (20 s) and `refuse-media.8180` (empty for reset, `close`)
  were created and removed; both probes kept running. Five read-only admin API requests read item metadata.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, a timed ECP relay (key times are its
  ECP accept times), screenshots at fixed delays after a key's accept, and the API-origin header probe with
  `--playback-bodies` (25 starts, 21 replans, 25 stops; 354 forwarded media requests, all with `Authorization`; 3,317
  refused; no 401 or 403).

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a profile change during a held replan (plan 6.6) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` | PIN profile playing; replan held 20 s; Options → 1080p Low, Back ×3, avatar → Switch Profile → no-PIN profile, as one relay sequence | PASS | The `quality_change` reached the probe 0.05 s after OK, with all three credential headers, and was held. Back sent the stop at once (200, 0.1 s), with the replan still in flight. Choosing the profile 8.8 s after OK logged `api: session operation waits for playback jobs`; the replan timed out at 15 s (`request timed out`), and the switch went through 6.2 s into the wait. No job was left, so no `identity_changed` line. The held replan was forwarded 20 s after it arrived (before the switch) with the PIN profile's headers and answered 404; no playback request reached the probe after the switch. The no-PIN profile's Home loaded. |
| T1b switch to the same profile during a held replan | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` | as T1a, no-PIN profile playing, the no-PIN profile chosen again | PASS | The replan was held and the stop sent at once (200). Choosing the profile 8.8 s after OK ran at once, with no wait (selecting the open profile changes no identity), while the replan was in flight (timed out 6.2 s later). The held replan was forwarded after 20 s and answered 404. |
| T2a original outage, reset (AG-169 decision 3) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http`, Auto | `refuse-media` 30 s; again with Right (+30 s) 2 s into it | FAIL | Without a seek nothing happened: Roku reads an original over one range request opened at the start, which the refusal does not cut, and made no new request in 30 s. With the seek: 1,641 refused range requests in 24 s and no `Video` error; `no progress for 20 s {"buffer":33,"kind":"stall"}`, then the reopen (`content assigned after the stop {"ms":577}`), whose first request was reset: 0.2 s later `Video error -3 … reader pick stream error:bad:Transfer error: Failure when receiving data from the peer` with `kind` `player`. That sent `seek_failure_recovery` with `player_failure` (and `transport_reopen`); the copy remux it returned and then a transcode (`copy_routes_exhausted`) failed on their playlists (`-3 … mpr zero length playlist err0`, `player`) and sent `failure_recovery` 2 and 3; the third answer was terminal 4.0 s after the stall line: "Can't play this title. All compatible playback recipes have already failed for this output route." with Back only. No reconnect, no `decoder_no_output`; three route exclusions (defect 1). |
| T2b original outage, close | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http`, Auto | `refuse-media` `close` 30 s, Right 2 s into it | FAIL | The same sequence: stall line at 20 s, reopen, `-3 … Transfer error: Server returned nothing (no headers, no data)` (`player`), the remux and the transcode failed on their playlists, terminal 3.3 s after the stall line (defect 1). |
| T3 W10-1, renewal while buffering (AG-177) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http`, Auto | reset, then Right after the content's refresh time (a renewal by local seek), 8 s of refusal | NOT TESTED | A rebuffer during playback cannot be made with the refusal: an HLS load fails at its first refused segment (T4) and an original's open request is not cut (T2a). The proactive renewal of a load started before the account's refresh time comes 29 min after that time, with playback running throughout. The partial run: the seek renewed the headers and reloaded, the reload's first request was reset and gave `-3 … Failure when receiving data from the peer` 0.18 s after assignment, and the T2a chain ended terminal 2.6 s after that error. No `quality_change` was sent. |
| T4a W10-2, media cut on HLS (AG-178) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode, H.264 MKV with E-AC-3 5.1, `server_transcode_hls` at an explicit 1080p Low | reset 75 s | FAIL | Eight segment requests were reset within 0.25 s and 0.3 s after the refusal began `Video error -5 … buffer:loop:demux:Errors seen on all bitrates:last_err:961:…` came with `kind` `decode`: `failure_recovery` with `decoder_failure`, answered terminal (the explicit rung was the only recipe). No stall clock, no reopen (defect 1). |
| T4b W10-2, close | 2026-10-23 | 55R625 / 15.3.4 | TV | as T4a | `close` 60 s | FAIL | The same: `-5 … last_err:961` (`decode`) 0.9 s after the refusal began, `decoder_failure`, terminal. |
| T4c W10-2, copy remux | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode, H.264 MKV with two AAC tracks (track 1 chosen), `server_remux_hls` (`hls_packaging_required`), Auto | reset 60 s | FAIL | Roku played 16.8 s from its buffer until its next segment request; eight resets, then `-5 … last_err:961` (`decode`): `failure_recovery` `decoder_failure`, a transcode (`copy_routes_exhausted`) whose playlist was reset (`-3 … zero length playlist`, `player`), `failure_recovery` 2 with `player_failure`, terminal 2.2 s after the error. No `transport_stall`, no reopen, no `decoder_no_output` (defect 1). |
| T5 W10-3, VP9 envelope (AG-179) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-032, MKV VP9 profile 0 1920×1080 at 23.976 fps (server metadata; 8-bit SDR, level unknown, 2.5 Mbps) | stock gates, deep link | PASS | The start body's VP9 entry: `profiles` ["profile 0"], `bit_depths` [8], `max_width` 1920, `max_height` 1080, `max_frame_rate` 30, hardware. Plan `original_http` (`validated_original_playback`), `video_codec` vp9; first frame 1.7 s after the plan; ECP `vp9` 1920x1080 at 23.976. |
| T6 W10-4, Right straight after the return (AG-180) | 2026-10-23 | 55R625 / 15.3.4 | TV | an H.264 feature original; the DV P8.1 episode (`client_dv8_base_layer`) | Home → Continue Watching card → Detail → Resume 20 s → Back → Back, Right 0.17–0.20 s after the second Back's accept; screenshots 0.3 s and 4 s after Right | PASS | Twice the ring moved to the card to the right at once and stayed; the hero showed the played title at 0.3 s (its 0.15 s wait and cross-fade) and the card Right reached at 4 s. The quiet refresh moved the played title to the front 3.1–3.2 s after Back, and the ring and hero stayed on the viewer's card. |
| T7 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | Continue Watching titles: originals, copy and audio-adaptation remuxes, a DV P8.1 base-layer original | 10 × Home → Detail → Resume 24 s → Back → Back, from Continue Watching's third card | PASS | Every cycle started (201), showed its first frame, and stopped (200). `sgnodes/all` at Home: 983 before, 1006 after (+2.3%). No BrightScript error, backtrace, or `[ERROR]` line in the run's console (1,384 lines). Two Auto `quality_change`s sent 1.4–2.7 s before a stop were answered 404 after it (`request failed … 404`). Focus walked two cards right per cycle instead of rotating through three titles (defect 2). |
| T8 Home return focus after the quiet refresh (AG-170) | 2026-10-23 | 55R625 / 15.3.4 | TV | a feature original from Continue Watching's third card | the T7 cycle once, screenshots 0.3, 2, 4, and 8 s after the second Back | FAIL | At 0.3 and 2 s the ring and the hero were on the played title. The quiet refresh came 3.1 s after Back and moved it to the front; at 4 and 8 s the ring and the hero were on the title that took its place (defect 2). |

### Defects found in run 14

1. **Client:** a refused media connection is read as a player or decoder failure. Roku reports a reset or closed
   connection as `Video` error −3 (`Transfer error: Failure when receiving data from the peer`, `Server returned
   nothing`, `mpr zero length playlist`) or, for HLS segments, −5 with `last_err:961`, which is not an HTTP status;
   `playback.video.failure` classes the first `player` and the second `decode`, so recovery sends `failure_recovery`
   with `player_failure` or `decoder_failure` and the server excludes the route. Each new plan then fails on its
   first refused request within 0.2–0.7 s, so a media outage of a few seconds exhausts every route in 2–4 s and ends
   in a terminal "Can't play this title" with Back only (T2, T3, T4). The stall clock ran only for a seek within an
   original, where Roku retried about 70 times a second without an error. Even classed `network`, plan 6.7 gives one
   reopen and then `failure_recovery`, which excludes the route while the API answers; how a media-only outage should
   recover is open.
2. **Client (regression):** run 12's defect 1 is back. After Detail → Resume → Back → Back, the ring and the hero stay
   on the played title until the quiet refresh moves it to the front, then rest on whatever title now has its old
   place (T8; every T7 cycle). Run 13 passed the same quiet-refresh return at `24a7ce8`. Not confirmed: the W10-4
   change (`b2ccd23`) reading the list's report after the refresh as the viewer's move, which AG-180 assumes the list
   never makes.
3. **Harness (lab mode):** `refuse-media` acts only on new requests, so it cannot cut an original's playback: Roku
   reads an original over one long range request opened at the start (T2a).

Observations for review, not counted as defects: Back during a replan sends the stop at once, so a profile change
seconds later finds no job left and no `identity_changed` line is logged; the held replans the server received after
the stop answered 404. After Switch Profile, Home restores focus to the avatar without opening the menu preview, and
Down from there goes to the rows rather than into the menu. A copy remux played 16.8 s from its buffer after the
refusal began before Roku requested a segment.

## Run 15 — reconnect after a media outage, Home return focus

Fifteenth hardware pass on the same TV: the device checks of AG-183 (a refused media connection is a network drop that
reconnects), AG-184 (the probe's refusal also cuts open media connections), and AG-185 (Home return focus), and
stability. Lab stack on silo-server `roku/client-support` at `c166d16d1`, 1-hour access tokens, proxy node disabled.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio, the picture, and the HDR badge could not be
  observed remotely and are not claimed.
- **Build:** stock dev build of `77f8822`, no override and no patch, installed at the start and left installed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. Ended on Roku Home with nothing playing.
- **Lab:** no container was touched. `refuse-media.8180` (empty for reset, `close` once) was created and removed by a
  controller that held it for a set time from the probe's first `refuse` line; both probes kept running.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, a timed ECP relay (key times are its
  ECP accept times), screenshots at fixed delays after a key's accept, and the API-origin header probe with
  `--playback-bodies` (23 starts, 61 replans, 23 stops; 595 forwarded media requests, all with `Authorization`;
  18,616 refused, 7 of them open connections cut; no 401 or 403).

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a original, 10 s outage (AG-183, AG-184) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http`, Auto | reset 10 s from the first refused request; again for 60 s | PARTIAL | The probe cut the open range requests 0.23 and 0.28 s after the file appeared (`open: true`; 2.2 and 38.5 MB relayed on them) and refused 565 and 4,283 retries. Roku played on from its buffer: ECP buffer full, position advancing, no `Video` error, no stall line, no replan. The reconnect path did not run. |
| T1b original, long outage | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http`, Auto, from 0 | reset until the terminal error (253 s), then Retry; again with reset 150 s | PASS | Both times Roku played 88–89 s from its buffer after the cut, then rebuffered; about 6 s into the rebuffer (Auto's one long stall), before any `Video` error, Auto sent `quality_change` (Roku's estimate 2,818 kbps) and the server moved the session to `server_transcode_hls` (`quality_bandwidth_limit`) at the same position (defect 1). That plan's playlist failed `−3 … mpr zero length playlist` (`network`), which began the outage: "Reconnecting. Playback will resume automatically." and a no-op `track_change` at once (0.1 s), then, after each plan failed again, 1.1, 2.1, 4.1, 8.1, and 15.1 s later. Long outage: 13 tries, then 2:03.6 after it began "Can't reach the server" with Retry only (the API answered); Retry after the refusal ended sent `start` (201, with the same estimate), and the transcode played from the outage position 2.2 s after Retry. 150 s: the outage lasted 63 s; the eighth try played from the same position 8.6 s after the refusal ended. |
| T1c transcode, 10 s outage | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `server_transcode_hls` (`quality_bandwidth_limit`), Auto | reset 10 s; once more with `close` 10 s | PASS | The first refused segment gave `Video error −5 … buffer:loop:demux:Errors seen on all bitrates:last_err:961` (`mediaerror`, no status, `network`) in 0.23 and 0.28 s; each reconnect plan failed `−3 … mpr zero length playlist` (`network`) 0.2–0.6 s after it, and the next waited 1, 2, 4, 8 s. The fifth `track_change` played from the outage position 8.3 s (reset) and 8.0 s (`close`) after the refusal ended. Reset and `close` gave the same strings. |
| T1d transcode, 150 s outage | 2026-10-23 | 55R625 / 15.3.4 | TV | as T1c | reset 150 s, then Retry | PASS | −5 0.28 s after the first refused segment (`network`), "Reconnecting", 12 `track_change`s on the schedule, then 2:04.2 after the outage began "Can't reach the server" with Retry only and a stop. Retry after the refusal ended: `start` 201 at the outage position, first frame 2.5 s after Retry. |
| T1e copy remux, 10 s outage | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode, H.264 with AAC 2.0, `server_remux_hls` (`hls_packaging_required`), Auto | reset 10 s | PASS | −5 `last_err:961` (`network`) 0.22 s after the first refused segment (2.2 s after the file, while Roku played from its buffer); 5 `track_change`s; the fifth played from the outage position 9.0 s after the refusal ended (2.0 s of it plan to first frame). |
| T1f copy remux, 150 s outage | 2026-10-23 | 55R625 / 15.3.4 | TV | as T1e | reset 150 s, then Retry | PASS | −5 `network` 0.26 s after the first refused segment, 12 `track_change`s, all at the same window and position; "Can't reach the server" with Retry only 2:04.6 after the outage began. Retry: `start` 201 with a new window at the same source position, first frame 2.1 s after Retry. |
| T1 totals | 2026-10-23 | 55R625 / 15.3.4 | TV | all of T1 | — | PASS | 62 `Video` errors, all `network`: 5 × −5 `Errors seen on all bitrates:last_err:961` and 57 × −3 `mpr zero length playlist`; no `Transfer error`, `decode`, or `player` kind. No `failure_recovery`, `seek_failure_recovery`, or `plan_failed` route event; 59 `track_change`s and 2 Auto `quality_change`s, all answered 200. |
| T2a Home return focus after the reorder (AG-185, AG-170) | 2026-10-23 | 55R625 / 15.3.4 | TV | Continue Watching titles: an H.264 feature original, the T1e episode, FX-009 (`original_http`) | Home → Continue Watching card → Detail → Resume 20 s → Back → Back; screenshots 0.3, 2, 4, and 8 s after the second Back | PASS | Three returns that moved the played title to the front: in two (third card) the row loaded again 0.01–0.02 s after Back and the ring and the hero were on the played title, now first, at every screenshot (the hero still fading in at 0.3 s); in one (fourth card) nothing loaded early, so at 0.3 and 2 s the ring and the hero were on the title at its old place and, after the quiet refresh (3.2 s) moved it to the front, on it, now first, at 4 and 8 s: run 14's T8 case, now passing. A fourth return, of SYNTHETIC, did not reorder: it resumed from 0 without a saved position and stopped at 20.6 s, the server left it third, and the ring and the hero stayed on it. |
| T2b ten returns from the third card (AG-185) | 2026-10-23 | 55R625 / 15.3.4 | TV | as T2a | 10 × the T2a cycle from Continue Watching's third card; screenshots 0.3 and 4 s after the second Back | PASS | Every return: the ring and the hero on the played title at its old place at 0.3 s and on it, now first, at 4 s, after the quiet refresh (layout 2.9–3.2 s, row 3.3–3.6 s after Back; no early reload in any of the ten). The three titles rotated as the reorder predicts. |
| T2c Right straight after the return (AG-180, AG-185) | 2026-10-23 | 55R625 / 15.3.4 | TV | the T1e episode; FX-009 | the T2a cycle from the third card, Right 0.21 and 0.19 s after the second Back's accept; screenshots 0.3 and 4 s after Right | PASS | Twice the ring moved to the card to the right at once and stayed; the hero showed the played title (or was mid-fade) at 0.3 s and the card Right reached at 4 s, after the quiet refresh (3.0–3.1 s after Back) moved the played title to the front. Nothing loaded early, so no restoration was pending at the Right. |
| T2d `browse` debug lines (AG-185) | 2026-10-23 | 55R625 / 15.3.4 | — | — | the console of T2a–T2c | PASS | No `the viewer's move ends a pending focus restoration` line in the 16 returns (14 without a key, 2 with T2c's Right). |
| T3 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | T2b's titles | T2b's ten cycles | PASS | `sgnodes/all` at Home: 985 before, 985 after (0%). No BrightScript error, backtrace, `[ERROR]`, or `request failed` line in the run's console (1,446 lines); its only `[WARN]` lines are T1's `Video` errors. |

### Defects found in run 15

1. **Client (minor):** on an original under Auto, a media outage longer than Roku's buffer reads as a bandwidth
   shortage. After about 88 s of buffered playback the node rebuffers, and 6 s later (Auto's one long stall) the client
   sends `quality_change` with Roku's measured estimate, below the original's bitrate, so the server moves the session
   to a transcode before any `Video` error arrives; the outage is then reconnected on the transcode, and Retry's `start`
   carries the same estimate (T1b). No route is excluded, but the viewer comes back to a lower-quality transcode, and the
   original's own failure path (stall, reopen, `Transfer error`) did not run in this pass. With the API answering, the
   client cannot tell a refused media connection from a slow one at that point; whether Auto should hold off while the
   node's last media request failed is open.

Observations for review, not counted as defects: a 10 s or even 60 s outage on an original is invisible (after the
cut Roku played on for 88–89 s before it rebuffered, T1b); resume after a 10 s HLS outage takes 8–9 s from the network's return because
the fifth try (after the 8 s wait) is the first after it; `close` and reset refusals produce identical error strings on
HLS; the early Continue Watching reload after Back came in the first three returns and in none of the 13 after them,
and BrowseRows still logs no reason for a row load; a resumed title with no saved position that plays 20 s is not moved
to the front of Continue Watching by the server.

## Run 16 — original outage under Auto, regression smoke

Sixteenth hardware pass on the same TV: the device check of AG-187 (a rebuffer that no media reaches is an outage, not
a bandwidth shortage) on an original, a smoke pass over the whole ten-foot UI (spec section 5) after the fixes since
run 13, and stability. Lab stack on silo-server `roku/client-support` at `c166d16d1`, 1-hour access tokens, proxy node
disabled.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio, the picture, and the HDR badge could not be
  observed remotely and are not claimed; screenshots show the UI plane and Roku's caption plane, not the video.
- **Build:** stock dev build of `36a7da5`, no override and no patch, installed at the start and left installed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. Roku's caption mode was On at the start (earlier runs
  started at Off) and was On at the end. Ended on Roku Home with nothing playing.
- **Lab:** no container was touched and no setting written. `refuse-media.8180` (empty, reset) was created and
  removed by a controller that ended it once the refusal had lasted 120 s and the console showed the stall line and a
  `Video` error after it; both probes kept running.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, a timed ECP relay (key times are its
  ECP accept times), screenshots at fixed delays after a key's accept, and the API-origin header probe with
  `--playback-bodies` (18 starts, 15 replans, 18 stops; 918 forwarded media requests, 917 with `Authorization`;
  7,751 refused, 2 of them open connections cut; one 401).

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 original outage under Auto (AG-187) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http` (`validated_original_playback`), Auto, from 0 by deep link | reset from 25 s in, ended at 123 s | PASS | The probe cut the open range request 0.35 s after the file appeared (2.3 MB relayed). Roku played 87.4 s from its buffer, then rebuffered at 114.7 s with ECP's reading held at 11 for 20 s; no `quality_change` was sent. 20.1 s into the rebuffer: `no progress for 20 s {"buffer":33,"kind":"stall"}`, the reopen (`content assigned after the stop {"ms":604}`), and 0.16 s later `Video error -3 … Transfer error: Failure when receiving data from the peer` (`network`). "Reconnecting. Playback will resume automatically." showed; five no-op `track_change`s followed, at once and then 1.1, 2.1, 4.1, and 8.1 s after each failed plan, each answered `original_http` at 114.681, none with `failure` or `bandwidth_estimate_kbps`. The fifth played from 114.1 s, 4.2 s after the refusal ended. The 18 s outage did not reach the terminal error, so Retry was not needed; the start carried no estimate. |
| T2a Home, top bar, avatar menu (5.3, 5.5) | 2026-10-23 | 55R625 / 15.3.4 | — | — | key walk with screenshots | PASS | Hero (logo, info line, synopsis, backdrop) follows the focused card; Continue Watching landscape cards with progress, poster rows below. Back from content moved focus to the Home tab; resting on Movies opened its list of three libraries with each library's Recommended and Browse beside it, Series its sections; resting on the avatar previewed the menu, and Down entered it. |
| T2b profile picker and switch (5.4) | 2026-10-23 | 55R625 / 15.3.4 | — | — | Switch Profile → PIN profile → Switch Profile → no-PIN profile | PASS | "Who's watching?" with focus on the first profile and a lock badge on the PIN profile. The PIN profile opened without asking for the PIN (its stored profile token, spec section 7.3); switching back restored the no-PIN profile's Home. |
| T2c library pages (5.5) | 2026-10-23 | 55R625 / 15.3.4 | — | — | Movies tab, list, Browse, sort, rail | PASS | Recommended rows; the list's three libraries; Browse with the Sort pill ("Title A–Z"), a six-column grid, and the rail strip; the sort menu's seven sorts; Year hid the rail and Title restored it; the rail widened from All, a letter filtered the grid, and Back narrowed the rail to the grid, then went to the tab. Back to the selected tab does not preview its list and Down from it enters the content (as on Android TV, per the shell's own comment). |
| T2d Search (5.6) | 2026-10-23 | 55R625 / 15.3.4 | — | library series episode | episode title typed with ECP | PASS | "Search your library" before a query; chips, "1 result", the keyboard folded into a field once focus left it; the episode result read "series… · S02E03" with the tag whole; OK opened its series' Detail on that season with the episode first. Back returned to the result, then the keyboard, then left Search. |
| T2e Detail (5.6) | 2026-10-23 | 55R625 / 15.3.4 | — | an H.264 feature original; library series | key walk | PASS | Movie: 72 px title without a logo, metadata line, synopsis, "Resume 7:15" pill and Start Over, Details section; Resume sent `start_position` 7 s before the saved position. Series: logo, season capsules, landscape episode cards; resting on a season switched it and made its first episode active ("Play S1:E1"); focusing an episode updated the metadata line, synopsis, and pill. |
| T2f player on an original (5.7) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT, `original_http` | OK, Right, Left, Fwd ×2, Back, Rev ×3, OK, Down, tabs | PASS | Controls with context line, title, scrubber, "−18:45 · Ends 8:17 AM", and the six buttons; Right +30 s and Left −10 s with the controls hidden; »2× and «4× with a 240 px trickplay thumbnail (the lab now has sheets for SYNTHETIC), its time, and the speed chip, title hidden; Back cancelled the ladder at the playing position and OK committed. Down opened Options on Subtitles; Info, Stats, Video (Auto and five rungs), Audio, and Subtitles all rendered. |
| T2g subtitle change in place (9.7) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC + external SRT | Options Subtitles: English, Off, English | PASS | Loaded with captions On and no subtitle, so the first English reloaded once (645 ms). Then Off sent a `track_change` without the subtitle and turned captions Off, and English sent one with the track and turned them On, both without a reload; the cue showed. |
| T2h copy remux, transcode, audio change (9.6, 9.7) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episodes, H.264 MKV, AAC ja (default) + en | Detail → episode; Options Audio and Video | PASS | `server_remux_hls` (`hls_packaging_required`) with the known late start (8 s, seek back not landed). A skip outside the window sent `seek_reanchor`, and skips pressed while it was in flight moved the new load's start, so none was lost. Audio Japanese: `track_change` naming the track by id and index → `original_http`, reload 584 ms. 720p Medium: `quality_change` → `server_transcode_hls` (`quality_fixed_rung`), reload 728 ms. |
| T2i Skip Intro and Up Next (5.7, 9.8) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode with intro and credits markers | profile default (ask); play into the intro; skip to the credits | PASS | "Skip Intro" appeared at the bottom right with a growing fill as playback entered the intro and withdrew after 5 s; re-entering and pressing OK 4.9 s in jumped to the intro's end. At the credits Up Next opened with the video box, the next episode's still and "S1 · E10 · 24 min", Play Now, a countdown equal to the runtime left (122), Keep Watching, Back, and "Auto-play is On"; Play Now stopped (200) and started the next episode (201) in the same player. |
| T2j Back paths and Home return focus (5.3) | 2026-10-23 | 55R625 / 15.3.4 | TV | an H.264 feature original from Continue Watching | Detail → Resume 20 s → Back → Back; screenshots 0.3, 2, 4, 8 s | PASS | Back closed an Options list, then the panel, then stopped and exited; from Home's content it went to the Home tab and the app stayed open. The played title reloaded to the front of Continue Watching, and the ring and the hero were on it at every screenshot. After an Up Next chain, the episode card that opened Detail had left the row and focus took its position. |
| T2k Resume on a title marked played | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC; library series episodes watched to the end in earlier runs | Detail's Resume pill; OK on the episode card | FAIL | Detail showed "Resume 2:19" or "Resume S1:E10" with Start Over, but both the pill and the card sent `start` without `start_position` and the plan started at 0 (defect 1). |
| T2l Subtitles Off with captions On on an original MKV | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode, `original_http` MKV with embedded SRT (forced, full, SDH) | after the audio change; Options Subtitles | FAIL | Options checked Off and no sidecar was requested, but ECP reported `captions="srt"` and Roku drew the embedded track, with a literal `{\an8}` before each cue (defect 2). |
| T3 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC (Continue Watching's third card) | 10 × Home → Detail → Resume 20 s → Back → Back | PASS | Every cycle started (201), showed its first frame, and stopped (200). `sgnodes/all` at Home: 983 before, 983 after (0%). No BrightScript error, backtrace, `[ERROR]`, or `request failed` line in the run's console (1,296 lines); its only `[WARN]` lines are T1's stall and five `Video` errors and two late-start lines. |

### Defects found in run 16

1. **Client:** Resume on a title the server marks played starts at 0. Detail shows Resume (and Start Over) whenever the
   saved position is past 30 s, but the player drops a saved position when `user_data.played` is true, so the start
   carries no `start_position` (T2k: the pill, the episode card's OK, and the deep links; T3's ten cycles). A rewatch
   stopped partway therefore restarts from the beginning. Cause inferred from the code: `catalog.detail.resumePoint`
   ignores `played`, `playback.intent.fromWatch` reads the position only when not played; `played` was not read from the
   server.
2. **Client / spec gap:** with Roku's caption mode On and no subtitle selected, an original whose container carries
   text subtitles shows one anyway, chosen by Roku by the caption language, while Options shows Off. Spec section 9.7
   keeps sidecars out of the content under captions On but does not cover embedded tracks. The cues also print their
   ASS override tags (`{\an8}`) literally (T2l).
3. **Platform (minor):** one segment request in 918 reached the probe without `Authorization`, `X-Profile-Id`, or
   `X-Profile-Token` and was answered 401, 3.8 s into a remux reanchor load that took 7.6 s to start with many aborted
   segment reads; no `Video` error followed. Spec section 9.4 assumes every media request carries the headers.

Observations for review, not counted as defects: T1's stall line read buffer 33 where AG-187 predicted 2 (ECP read 11);
a local seek on the copy remux rebuffered about 20 s with segments arriving 6 to 7 s apart, so Auto stepped down to a
transcode as spec section 9.7 intends (the slowness is the server's packaging); the next episode's `start` from Play
Now carried no bandwidth estimate; the avatar menu's preview already draws its first row with the focused fill; a
backdrop with a white top leaves the top bar's labels on white; two `track_change`s took the server 2.6 and 3.3 s to
answer.

## Run 17 — run 16 fixes: resume on a played title, embedded subtitles under each caption mode

Seventeenth hardware pass on the same TV: the device checks of AG-189 (one saved-position rule for Detail and the
start), AG-190 (the `Video` node draws only the plan's subtitle) and AG-191 (ASS override tags in SRT cues), and
stability. Lab stack on silo-server `roku/client-support` at `c166d16d1`.

- **Device / sink:** 55R625 / 15.3.4 (build 2303), TV speakers. Audio and the picture could not be observed remotely
  and are not claimed; screenshots show the UI plane and Roku's caption plane, which also shows through the player
  controls.
- **Build:** stock dev build of `2791211`, no override and no patch, installed at the start and left installed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. Roku's caption mode was On at the start and On at the
  end. For On mute the TV was muted with the remote's mute key (six presses, ending unmuted). Ended on Roku Home with
  nothing playing.
- **Lab:** no container was touched and no setting written; the plays changed the watch state of the titles used.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, ECP `device-info` for the caption
  mode, the API-origin header probe with `--playback-bodies` (22 starts, 20 replans, 22 stops; 613 media and subtitle
  requests, all with `Authorization` and `X-Profile-Id`), and screenshots taken when ECP reported a target position.
  ECP read `captions="srt"` on the MKV in every state (no subtitle, a sidecar selected, caption mode Off), so what Roku
  drew was judged from the screenshots, at the times the English and Forced tracks have cues.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a Resume on a played movie (AG-189) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC, `original_http`, played to the end in earlier runs | Detail's Resume and Start Over; rewatch past 5% and stop | PASS | Detail read "Resume 2:19" with Start Over; Resume sent `start_position` 132.172 and ECP's first position was 132.1 s. Skipped ahead and stopped at 338.438 s: Detail read "Resume 5:38", and Resume sent 331.438 (first position 330.9 s). Start Over sent 0 and started at 0. |
| T1b Resume on a played episode (AG-189) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S1E10), `server_remux_hls`, played to the end in earlier runs | Detail's pill and the episode card's OK; rewatch past 5% and stop | PASS | "Resume S1:E10" with Start Over; Resume sent `start_position` 175.136, 7 s before the saved 182.136 (plan offset plus ECP's first position: 175.13 s). After a stop at 302.961 s Detail stayed on S1·E10 with Resume and a longer progress bar; the pill sent 295.961 (first frame at 292.3 s, a segment start) and, after a stop at 312.887 s, the card's OK sent 305.887 (305.4 s). Start Over sent 0 and started at 0. |
| T1c A played title stopped near its end (AG-189) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC | played to its end; then Back 3.6 s before the end | PASS | Ended at 1,319.92 s of 1,320.02: the title left Continue Watching and Detail offered Play without Start Over; Play sent no `start_position` and started at 0. Stopped by Back at 1,316.41 s: Play only again, starting at 0.1 s. The server marks a stop past 90% played and zeroes its position, so the client's own 5 s rule was not isolated. |
| T2a Subtitles Off and English under caption mode On (AG-190) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S1E10) as `original_http` MKV (Options Audio Japanese) with embedded SRT (Forced, English, SDH) | Options Subtitles; screenshots at the English track's cue times | PASS | With no subtitle selected (after `the plan follows the caption mode {"mode":"On","subtitle":false}` reloaded without sidecars), no cue in 11 shots over 248–285 s, the four cue times included; run 16 saw Roku draw the embedded track here. English: one `track_change`, a reload (660 ms; captions were On at load, so no sidecars were carried), the three server sidecars requested, and cues at the cue times. Off: a `track_change` without the subtitle, caption mode written Off (spec 9.7), nothing drawn. |
| T2b caption mode On replay (AG-190) | 2026-10-23 | 55R625 / 15.3.4 | TV | same | Options Captions On replay; Replay over a cue | PASS | Writing On replay reloaded without sidecars (695 ms). Subtitles Off: nothing in normal play, nor during a Replay (Roku's mode `On` for its 11 s, 274.4 → 264.4 s). English (reload 751 ms with sidecars): nothing in normal play; the cue at 268.9 s drawn during a Replay. |
| T2c caption mode On mute (AG-190) | 2026-10-23 | 55R625 / 15.3.4 | TV | same | Options Captions On mute; the TV muted with the remote's mute key | FAIL | Drawing followed Roku: Subtitles Off drew nothing muted or unmuted, and English drew its cues only while muted. The client lost the mode (defect 2): the write produced events `Off`, `Off` and Options checked Captions Off while `device-info` read `When mute`; each unmute (3 of 3) produced `Off`, taken as the viewer's Off; a later mute's `On` was taken as On and reloaded the title (657 ms); choosing English then wrote On over On mute. |
| T2d caption mode Off with English selected (spec 9.7) | 2026-10-23 | 55R625 / 15.3.4 | TV | same | English, then Options Captions Off | PASS | Captions Off wrote the mode and sent no replan; no cue at the four cue times. A selected subtitle shows only while Roku's caption mode is on (spec section 5.9); the run's brief expected the sidecar to draw. |
| T2e ASS override tags in SRT cues (AG-191) | 2026-10-23 | 55R625 / 15.3.4 | TV | same, Forced track | Forced selected with a reload; screenshots at its sign and lyrics | PASS | The episode's title-card sign and the opening lyrics, which run 16 saw printed after a literal `{\an8}`, showed without it, at the bottom. |
| T2f subtitle change between sidecars in place (spec 9.7) | 2026-10-23 | 55R625 / 15.3.4 | TV | same | Options Subtitles English → Forced, Forced → SDH, SDH → Forced; English → Forced again | FAIL | Each sent one `track_change` and switched in place (no reload, no sidecar request), and Options checked the new track, but Roku kept drawing the sidecar selected at load: English dialogue at the cue times and none of Forced's sign or lyrics (defect 1). Forced → English reloaded (721 ms) and drew English. |
| T3 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC (Trending's first card) | 10 × Home → Detail → Play 20 s → Back → Back, then 3 more | PASS | Every cycle started at 0 (201), was playing at 20 s, and stopped (200) at 20.6–21.2 s, below 5%. `sgnodes/all` at Home: 928 before, 970 after 10 cycles and 970 after 13, with the same count of each node type after 10 and 13 (a one-time difference in Home's state, no growth per cycle). No BrightScript error, backtrace, `[WARN]`, or `[ERROR]` line in the run's console (1,789 lines). |

### Defects found in run 17

1. **Client:** an in-place subtitle change between two sidecars the content carries does not change what Roku draws.
   The player sends the `track_change`, keeps the content, and (read from the code, `selectSubtitle`) sets
   `Video.subtitleTrack` to the new sidecar, and Options checks it, but Roku goes on drawing the sidecar that was
   selected when the content loaded (T2f, four switches). Runs 7 and 16 proved in-place changes only between Off and the one sidecar of a single-track title. A
   change that reloads draws the new track.
2. **Client:** On mute on a Roku TV is not kept. Under `When mute` the TV's caption-mode events report the effective
   state, `On` while muted and `Off` while unmuted, so the write from an unmuted TV produced `Off` twice, past the
   guard that skips one stale repeat (AG-123), and each unmute and later mute read as the viewer choosing Off or On
   (T2c). Options then shows Captions Off, a mute reloads the title as if captions came on, the first reload carried
   sidecars as if captions were Off, and choosing a subtitle writes On over On mute.

Observations for review, not counted as defects: a series' pill reads "Resume S1:E10" without a time (spec section
5.6); after the player closed, focus landing on the already-active episode card did not switch the hero to it until
focus moved away and back; SYNTHETIC's detail metadata line shows only the year while the Home hero shows its runtime;
Forced → English reloaded while English → Forced switched in place; each caption-mode Off write was followed by a stale
first event and then `Off`, and the client ended on Off; run 16's credential-less segment request did not recur in 613
media and subtitle requests.

## Run 18 — run 17 fixes: in-place switches between sidecars, On mute

Eighteenth hardware pass on the same TV: the device checks of AG-193 (a sidecar selected by the `TrackName` Roku lists
for it) and AG-194 (the caption mode read as Roku's setting, `GetCaptionsOption("Mode")`), and stability. Lab stack on
silo-server `roku/client-support` at `c166d16d1`.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the picture could not be observed remotely and are not
  claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `b02ef14`, no override and no patch, installed at the start and left installed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. Roku's caption mode was On at the start and On at the
  end. For On mute the TV was muted with the remote's mute key (six presses, ending unmuted). Ended on Roku Home with
  nothing playing.
- **Lab:** no container was touched and no setting written; the plays changed the watch state of the titles used.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, ECP `device-info` for the caption
  mode, the API-origin header probe (15 starts, 15 stops, 15 `track_change`, 2 `quality_change`, 1 `seek_reanchor`;
  1,334 media and subtitle requests, all with `Authorization` and `X-Profile-Id`), and screenshots taken when ECP
  reported a target position. The tracks were told apart in two windows of the episode: dialogue at 253–289 s, where
  English and SDH have cues (SDH adds speaker labels such as "Tornado:" and a "♪" cue) and Forced has none, and
  Forced's title-card sign (80–84 s) and opening lyrics (103–114 s), where English has none.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a subtitle changes between sidecars in place (AG-193) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S1E10) as `original_http` MKV (Detail audio Japanese) with three server sidecars (Forced, English, SDH) | caption mode On; Options Subtitles English → Forced → SDH → Forced → Off → English; screenshots in both windows after each change | PASS | English, chosen while the content carried no sidecars (captions On, no subtitle), reloaded (677 ms, three sidecar requests). Roku then listed the sidecars as `/tmp/plugin/<dir>/tmp:/subtitles/track1.srt` to `track3.srt`, each containing the path the client gave, beside the MKV's own `mkv/5` and `mkv/6`. Each of the five later changes sent one `track_change` and stayed in place: no new plan, no reload, no sidecar request, no "Roku did not switch" line. Drawn: Forced's sign and lyrics and no dialogue (twice), SDH's dialogue with its speaker labels and "♪", nothing in 14 shots after Off (caption mode written Off), and English's dialogue without labels after English (caption mode written On), with nothing in Forced's window. |
| T1b the same on a copy remux (AG-193) | 2026-10-23 | 55R625 / 15.3.4 | TV | same episode, `server_remux_hls` (Options Audio English), three sidecars | English selected by the audio change's reload; then Forced → SDH → Forced → Off → English; seeks inside the playlist | PASS | Roku listed only the three sidecars. All five changes stayed in place as in T1a; Forced's cues drew pixel for pixel as on the original, SDH drew its labels and "♪", Off drew nothing in 13 shots, English drew its dialogue without labels. Seeks inside the playlist made no replan. |
| T1c subtitle change on a transcode (spec 9.7) | 2026-10-23 | 55R625 / 15.3.4 | TV | same episode, `server_transcode_hls` (Options Video 720p Medium) | English → Forced | PASS | The transcode carries no sidecars, so the in-place check does not apply: Roku listed only the stream's own `webvtt/1`. The change reloaded at the position (659 ms), as for any sidecar the content does not carry, and Forced's lyrics drew from the stream's WebVTT rendition. |
| T2 caption mode On mute (AG-194) | 2026-10-23 | 55R625 / 15.3.4 | TV | same episode, `server_remux_hls`, English sidecar selected | Options Captions On mute; the remote's mute key six times, 4–8.5 s apart, at 254.7–283.7 s; then Options Captions Off | PASS | The write logged `caption mode chosen {"mode":"When mute"}`; Roku's first event repeated `On` (ignored as stale), then `{"effective":"Off","mode":"When mute"}`; `device-info` read `When mute`; no replan. Each press produced one event reading `When mute`, with `effective` alternating On and Off, and the player kept `When mute`: no replan, no reload, and no "the plan follows the caption mode" line in the run. Cues drew in the three shots taken while muted and in none of the five taken unmuted, four of them at English cue times. Options kept On mute checked. Captions Off: one write, events `Off`, `Off`, no replan, Off checked. |
| T3 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC (Trending's first card) | 10 × Home → Detail → Play 20 s → Back → Back, then 3 more | PASS | Every cycle started at 0 (201), was playing at 20 s, and stopped (200) at 20.55–21.59 s. `sgnodes/all` at Home: 928 before, 970 after 10 cycles (+4.5%) and 970 after 13, with the same count of each node type after 10 and 13, as in run 17. No BrightScript error, backtrace, `[WARN]`, or `[ERROR]` line in the run's console (1,326 lines). |

### Defects found in run 18

None.

Observations for review, not counted as defects: Roku lists an MKV's own text tracks as `mkv/<n>` (`mkv/5` and `mkv/6`,
two of the file's three); whether `n` is the Matroska track number (AG-190) was not checked. The transcode's WebVTT
rendition drew Forced's lyrics in italics, and the SRT sidecars drew the same lyrics upright (cause not traced). After
each caption-mode Off write, the original reported `Off` twice and the remux a stale `On` and then `Off`; the client
ended on Off each time. One remux segment request was answered 416 during seeks, with no replan and nothing visible.

## Run 19 — W11 fixes: outage budget, explicit decoder error, held subtitle switch; slow link, renewal while buffering, start time

Nineteenth hardware pass on the same TV: the device checks of AG-197 (an explicit decoder diagnosis), AG-198 (the
outage's two-minute budget), and AG-199 (a subtitle check held through another track change), AG-187's optional slow
link pass and W10-1's renewal while buffering (AG-177), both with the lab's `throttle-media` mode (AG-196), the
bitmap and ASS subtitle routes, the plan section 1 copy-remux start time, and stability. Lab stack on silo-server
`roku/client-support` at `c166d16d1`, 1-hour access tokens except during T4, proxy node disabled.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane, so burned-in subtitles cannot be seen in them.
- **Build:** stock dev build of `9ab4b23`, installed at the start and left installed. T2 used the dev build with a
  temporary local patch (G10 `development`, and the AV1 probe answer ignored) and T7 the `perf` build with run 10's
  gate patch (G1, G13, G14 `on`); both were reverted before the stock build went back on and are not committed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. Roku's caption mode was On at the start and at the
  end. Ended on Roku Home with nothing playing.
- **Lab:** no container was touched. For T4 only, `auth.access_token_expiry` was set to 3 minutes and set back to 1
  hour about 22 minutes later (verified by the admin settings read and a login answering `expires_in` 3600). The probe's
  `refuse-media`, `throttle-media`, and `hold-replan` files were created and removed by a controller that always
  removes them; none was left, and both probes kept running. The plays changed the watch state of the titles used.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s (its `buffering current` is the
  buffer reading quoted below), ECP key accept times, screenshots, and the API-origin header probe with
  `--playback-bodies` (12:23–13:50: 40 starts, 40 stops, 22 `track_change`, 2 `quality_change`, 2
  `failure_recovery`; 2,665 media and subtitle requests, all with `Authorization` and `X-Profile-Id`).

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 outage budget (AG-198) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode, H.264 with AAC 2.0, `server_remux_hls` (`hls_packaging_required`), Auto | (a) reset 150 s from the first refused request, then Retry; (b) reset until the first `Video` error, then `throttle-media` 50 kbit/s (170 s from its creation), then Retry | PASS | (a) First drop `Video error −5 … buffer:loop:demux:Errors seen on all bitrates:last_err:961` (`network`) 3.4 s after the first refused playlist; "Reconnecting"; 11 `track_change`s, all 200 at the outage position (at once, then 1, 2, 4, 8, and 15 s after each plan's `−3 … mpr zero length playlist`); stop and "Can't reach the server" with Retry only 120.0 s after the first drop. Retry after the refusal ended: `start` 201 at the outage position, first frame 2.2 s after the key. (b) The same first drop; each of the four reconnect loads, throttled, held its reading at 33 and ended in `no progress for 20 s {"buffer":33,"kind":"stall"}`; the error came 120.0 s after the first drop, while the fifth try waited. Retry after the throttle ended played 2.1 s after the key. No `failure_recovery` in either. |
| T2 explicit decoder error (AG-197) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-030 MKV AV1 1080p, AAC 2.0 | temporary G10 override (AV1 claimed on `original_http`); deep link | PASS | `original_http` with `av1`; 0.8 s later `Video error −5: :pump:Unsupported video format: AOMedia Video 1 codec:extra:err_clip_idx:0:program_id:` (`mediaerror`, no status), classed `decode`; `plan_failed`, then `failure_recovery` with `decoder_failure` (attempt 1); the server answered `server_transcode_hls` (`copy_routes_exhausted`), and the first-frame event reported `first_frame_ms` 3,449. No "Reconnecting", no `track_change`. |
| T3 slow link under Auto (AG-187, AG-196) | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC MP4 H.264 + AAC, `original_http`, 4,026 kbps, Auto | `throttle-media` 2,400 kbit/s (60%) from just before the start, 240 s | PASS | The start took 18.3 s (the load's own start); 11 s of play, then a rebuffer whose readings rose 32, 107, 199, 288, 369, 447 over 7.6 s; 7.6 s after the first rise one Auto `quality_change` (`bandwidth_estimate_kbps` 2,818, 70% of the original's bitrate) moved the session to `server_transcode_hls` (`quality_bandwidth_limit`) at the stall position, first frame 7.2 s after the replan; then 3 min 13 s of steady play under the throttle, no stall and no other replan. |
| T4 renewal while buffering (W10-1, AG-177) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode, `server_remux_hls`, Auto | 3-minute access tokens; the throttle drained Roku's buffer at 8 kbit/s so a rebuffer began just before a renewal, then rose to 1,500 or 2,500 kbit/s for the reload, and was removed once it played | PASS | The device refreshed its token every 90 s and renewed the media credential every 90 s (`renewing the media credential before it expires {"seconds":60}`, seven times), each a local reload without a replan. Cycle 3: rebuffer 2.7 s before the renewal (reading held at 16), renewal during it, reload assigned 0.6 s later; it buffered under the throttle with readings rising from 5.4 s after assignment (0 → 50 → … → 880 over 18.2 s) and played 25.6 s after assignment (`VODStartComplete` 25.4 s). Cycle 1: rebuffer 15.9 s before the renewal (reading held at 20), the reload played 10.3 s after assignment. No `quality_change` or other replan and no `no progress` line in either cycle or after. The cycle between them had no rebuffer before its renewal and is not counted. |
| T5 subtitle switch under a held replan (AG-199) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S1E10), `server_remux_hls` from 0, three SRT sidecars | caption mode On; Options English, then `hold-replan` 5 s, Forced and, 2.9 s later, SDH | PASS | English, picked while the content carried no sidecars, reloaded once (601 ms, three sidecar requests). Forced's `track_change` was held 5.1 s; SDH's went after Forced's answer and was held 5.1 s; neither made a plan line, a reload, a sidecar request, or a "Roku did not switch" line. Options showed SDH, and SDH's cues drew at 253–289 s with its speaker labels, "♪", and its own line at 289 s. The refusal path stays headless (the lab cannot refuse a track change). |
| T6 bitmap and ASS subtitles (spec 12.5) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-004 MKV H.264 1080p, FLAC ja + en, PGS only; FX-034 and FX-028 MKV with an embedded ASS track; library series episode (S3E1) MKV H.264 + E-AC-3 2.0 with eight ASS tracks | caption mode On; Options Subtitles; screenshots at fixed positions | FAIL | FX-004 (`server_remux_hls`, then an Auto step-down to a transcode on the lab link): English PGS gave `server_transcode_hls` (`subtitle_burn_in_required`), one reload (631 ms), first frame 3.5 s after the key; the Captions rows showed only Off and On; the burned-in cues are on the video plane and were not seen. FX-034 starts as a `server_transcode_hls` (`quality_auto_source`), so English ASS reloaded into the stream's WebVTT rendition (`webvtt/1`), cues drawn unstyled. FX-028 (`original_http`): English ASS reloaded without its sidecar ("Loading subtitles…"); the sidecar came 28.8 s later and playback stopped (defect 1); after the reopen its cues drew unstyled as SRT. S3E1 (`original_http`): the sidecar came 5.0 s after the pick, playback stopped, and `failure_recovery` moved the session to `server_remux_hls` (defect 1); on that remux the ASS cues drew unstyled, a sign and a line of dialogue merged at the bottom. No ASS fixture in the lab is planned as a remux otherwise. |
| T7 copy-remux start time (plan section 1) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episodes (S1E9–S1E12), `server_remux_hls` (English audio) | `perf` build with run 10's gate patch; Detail Resume, Start Over, and Play; two re-resumes 6.6 and 6.9 s after Back | PASS | 14 starts, keypress to `VODStartComplete` (device clock): median 1.71 s, maximum 2.39 s, minimum 1.36 s. Resumes 1.42–2.39 s; from 0 1.36–2.10 s (2.10 s on a growing playlist without a keyframe index); the re-resumes 1.59 and 1.37 s; keypress to `start` 201 0.36–0.68 s. Run 10's slow re-resumes (11.7 and 16.3 s) did not recur. |
| T8 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC (Trending's first card) | 10 × Home → Detail → Resume 20 s → Back → Back, then 3 more | PASS | Every cycle played 20 s and closed on the first Back. `sgnodes/all` at Home: 930 before, 972 after 10 cycles (+4.5%) and 972 after 13, with the same count of each node type after 10 and 13. No BrightScript error, backtrace, or `[ERROR]` line in the run's console (1,958 lines); no `[WARN]` during the cycles. |

### Defects found in run 19

1. **Client:** a selected sidecar that arrives after its content was assigned stops playback on an original. The player
   adds it to the playing content (`applySubtitle` rewrites the content's `subtitleTracks`); Roku then lists only
   that sidecar and stops. FX-028: the ASS sidecar arrived 28.8 s after the pick, while the original played; ECP went
   to `close` 1 s later and stayed there about 18 s, until `no progress for 20 s {"buffer":0,"kind":"stall"}` took
   the plan's reopen, which restarted 9.6 s earlier with the sidecar drawn. S3E1: the sidecar arrived 5.0 s after the
   pick, while the reload still buffered; ECP went from `buffer` to `close` for 21 s, then `no progress for 20 s
   {"buffer":100,"kind":"no_output"}`, a `plan_failed` route event, and `failure_recovery` with `decoder_no_output`,
   so the server excluded a playable original and moved the session to a remux. Spec section 9.7 and plan section 6.8
   expect the player to start without the sidecar and show it when it arrives; AG-193 marked this path unproven.

Observations for review, not counted as defects: AG-153's first play from 0 without a keyframe index still starts at
8.041 s and the seek back does not land (8.166 s), on two episodes (run 10's defect 3). AG-198's case of a reconnect
load that buffers without ever playing did not occur at 50 kbit/s: each throttled load held its reading and ended at
the 20 s stall clock, so T1b shows the budget ending a try that waited, not a load that buffered. The Auto estimate
is 70% of the stalled stream's bitrate, not Roku's measured rate (2,818 kbps under a 2,400 kbit/s link), and the
transcode it chose played steadily. In the perf build a Back about 40 s into an episode did not leave the player and
a second one did, consistent with Back dismissing Skip Intro first (spec 5.7; not captured). Under the 8 kbit/s
throttle the copy remux played 43.4 s from its buffer.

## Run 20 — run 19 fix: late subtitle sidecars; playback regression and stability

Twentieth hardware pass on the same TV: the device check of AG-201 (a sidecar that comes after its content started
reloads once, and the client never changes playing content), a regression pass over an original, a copy remux, and a
transcode after the fixes of runs 16 to 19, and stability. Lab stack on silo-server `roku/client-support` at
`c166d16d1`, 1-hour access tokens, proxy node disabled.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `fb4c489`, installed at the start and left installed. After the tests, two temporary
  local builds checked defect 1's cause (T1f): one that only adds log lines, and one that also skips one subtitle
  selection; both were reverted before the stock build went back on and are not committed.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. Roku's caption mode was On at the start; choosing
  subtitle Off in T1d and T2 wrote Off, and Options' Captions rows set it back to On, which `device-info` read at the
  end. Ended on Roku Home with nothing playing.
- **Lab:** no container was touched and no setting written. `refuse-media.8180` (empty, reset) was created and
  removed five times by a controller that always removes it; none was left, and both probes kept running. The plays
  changed the watch state of the titles used.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, ECP key accept times, screenshots
  taken when ECP reported a target position, and the API-origin header probe with `--playback-bodies` (14:19–15:39,
  T1f's builds included: 34 starts, 34 stops, 36 `track_change`, 5 `failure_recovery`, 2 `quality_change`, 2 `seek_reanchor`; 4,177 media
  and subtitle requests, all with `Authorization` and `X-Profile-Id`). The sidecars that FX-028 and S3E1 converted in
  run 19 are cached on the server, so their English ASS arrived in 0.1–0.5 s; the late path was run on library
  episodes and a library feature whose sidecars had not been converted.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a English (ASS) on an original whose sidecar is ready (AG-201) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-028, `original_http` (`validated_original_playback`) | caption mode On; deep link, Options Subtitles English at 37 s; twice | FAIL | The sidecar is cached, so the `track_change`'s content waited for it and loaded with it (`content assigned after the stop {"ms":718}`); no late path. First try: Roku listed the sidecar, then 1.0 s later listed it again beside the container's tracks; 80 ms after that its last media read was aborted (65,536 bytes) and none followed; ECP stayed in `buffer` with `current="0"` for 20 s and the screen stayed black without "Buffering"; then `no progress for 20 s {"buffer":100,"kind":"no_output"}`, a `plan_failed` route event, and `failure_recovery` `decoder_no_output`; the server moved the session to `server_remux_hls` (defect 1). Second try (a new session): first frame 1.7 s after assignment, and the sidecar's cues drew at 87 and 105 s. |
| T1b the same on S3E1 (AG-201) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S3E1), MKV H.264 + E-AC-3 2.0 with eight ASS tracks, `original_http` | caption mode On; Options Subtitles English at 215 s | FAIL | Four cached sidecars in 0.5 s, content assigned with them 1.9 s after the pick; the same sequence as T1a's first try: second listing, last media read aborted 84 ms later, 20 s in `buffer` at `current="0"`, `no_output` with buffer 100, `failure_recovery` `decoder_no_output`, `server_remux_hls` (defect 1). |
| T1c late sidecar on an original (AG-201) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S3E2), the same file class, sidecar not converted before | caption mode On; Options Subtitles English at 34 s | FAIL | As AG-201 intends up to the reload: the content waited 3 s and was assigned without the sidecar; the sidecar came 5.7 s after the pick and the player logged `the subtitle came after its content started; the plan reloads at the position {"replan":false}` (a local reload, no replan); `the Video node is still stopping {"ms":3000}`, then `content assigned after the stop {"ms":3361}` with the sidecar. That load then failed as in T1a: last media read aborted 64 ms after the second listing, `no_output` with buffer 100 20 s later, `failure_recovery` `decoder_no_output`, `server_remux_hls` (defect 1). FX-022, another file of the class (sidecars cached), failed the same way. |
| T1d English, then Off before the sidecar (AG-201) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S3E3), the same file class, sidecar not converted before | caption mode On; English, then Off 4.8 s later | PASS | English's content was assigned without the sidecar 3.9 s after the pick; Off 0.9 s later wrote caption mode Off and sent a `track_change` without the subtitle. That content had not played yet, so Off loaded new content (the player switches in place only on content that has played, `playback.session.canRetrack`): stopping took 3.4 s, first frame 11 s after Off. The English sidecar's download ended 0.4 s after Off's plan; no "came after its content started" line, no reload for it, no `no progress`, no `failure_recovery`; the original stayed. |
| T1e late sidecar on a copy remux (AG-201) | 2026-10-23 | 55R625 / 15.3.4 | TV | library feature, MKV H.264 13.7 GB, AC-3 5.1 + AC-3 2.0 commentary, five SRT tracks; commentary gives `server_remux_hls` (`hls_packaging_required`) | caption mode On; Options Audio commentary, then Subtitles English | PASS | English's `track_change` reloaded without the sidecar (first frame 9.5 s after the pick). The sidecar came 78.1 s after the pick: `{"replan":true}` and exactly one `track_change` at the position keeping the selection; its content fetched the sidecar again in 0.45 s, Roku listed it, first frame 3.8 s after assignment, and ECP read `captions="srt"`; no further replan for the subtitle and no `failure_recovery`. Drawing on this load was not captured: eight shots over its first 30 s showed no cue, and a 16 s rebuffer 91 s after its first frame moved Auto to a transcode (`quality_change`, estimate 12,317 kbps), whose cues drew. Episode S1E11's English sidecar on a copy remux was cached and came in time. |
| T1f defect 1 cause check (temporary builds) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-022; S3E1 | logging build, then the same with one selection skipped; English picked with the sidecar cached | — | Logging build on FX-022: at assignment the player selected the sidecar by its listed name, and Roku then reported `subtitleTrack` as the bare path the player gave (`tmp:/subtitles/track1.srt`), never the listed name. At the second listing Roku reported `currentSubtitleTrack` `mkv/3` (the container's track) and the player selected the sidecar again while the node buffered; 0.17 s later `bufferingStatus` read 100 and `Video.state` became `finished`, before any frame; 20 s later the same `no_output` and `failure_recovery`. With the selection skipped when Roku's `subtitleTrack` already equals the path: FX-022 and S3E1 both played (first frame 8.3 s after assignment), and after the next frame's selection their sidecar cues drew (`captions="srt"`). Two tries, so the cause is inferred, not proven. |
| T2a copy remux regression | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episodes (S1E9, S1E10), MKV H.264 + AAC ja/en with SRT Forced, English, SDH; English audio gives `server_remux_hls` (`hls_packaging_required`) | deep link; Right, Left, Fwd + OK; Subtitles Off → English → SDH → Off; 10 s refusal; Play ×2; Options Audio Japanese; Back | PASS | Start: first frame 1.6 s after `start`. Right +30 s and Left −10 s local; the ladder (»1×) showed a thumbnail and committed 63 s on locally. A skip before the playlist sent `seek_reanchor`. English reloaded with three sidecars (647 ms) and drew its dialogue; SDH switched in place and drew its speaker labels; Off switched in place, wrote caption mode Off, and nothing drew over the cue times. Refusal: `Video error −5 … Errors seen on all bitrates` (`network`), "Reconnecting", five no-op `track_change`s at the outage position (at once, then 1, 2, 4, 8 s), played 8.5 s after the refusal ended at the same position; no `failure_recovery`. Pause held the position and the 10 s progress said `is_paused` true. Audio Japanese: `track_change` → `original_http`, first frame 2.3 s after the key. Back stopped (200) and left. |
| T2b original regression | 2026-10-23 | 55R625 / 15.3.4 | TV | the same S1E10 as `original_http` MKV (Japanese audio); the library feature of T1e for the outage | Right, Left, Rev + OK; Subtitles Off → English → SDH → Off; 10 s refusals; Play ×2; Options Video 720p Medium | PASS | Skips +30/−10 s and the reverse ladder all local, no replan. English (the content carried the three sidecars, loaded while captions were Off) switched in place and wrote caption mode On; SDH in place with labels; Off in place, nothing drawn. A 10 s refusal while playing cut the open range request and Roku played on from its buffer: no `Video error`, no replan. A second one right after a skip (+300 s) refused 763 requests in 10 s while ECP sat in `buffer`; Roku's own retry then played at the skip target 2.8 s after the refusal ended, with no `Video error` and no replan, so the client's reconnect was not needed on the original. Pause and resume as in T2a. 720p Medium: `quality_change` → `server_transcode_hls` (`quality_fixed_rung`), first frame 2.2 s after the key. |
| T2c transcode regression | 2026-10-23 | 55R625 / 15.3.4 | TV | the same S1E10 as `server_transcode_hls` 720p Medium | Right, Left, Fwd + OK; Options Audio English; Subtitles Off → English → SDH → Off; 10 s refusal; Play ×2; Back | PASS | Skips and the ladder local. Audio English: `track_change`, reload 643 ms, transcode kept. English and SDH each reloaded into the stream's WebVTT rendition (673 and 665 ms) and drew (SDH with labels and "♪"); Off in place, nothing drawn. A 60 s refusal while playing saw no media request (Roku held over a minute of buffer). A 10 s refusal during a ladder seek: `Video error −5` (`network`), "Reconnecting", four no-op `track_change`s, the later ones at the ladder target the viewer committed during the outage, played there 2 s after the refusal ended; no `failure_recovery`. Pause and resume; Back stopped (200) and left. |
| T2d Resume of a partly watched title | 2026-10-23 | 55R625 / 15.3.4 | TV | S1E10 (copy remux); the library feature (original) | Home → Continue Watching → Detail → Resume | PASS | S1E10: Detail read "Resume S1:E10"; `start_position` 536.165, 7 s before the stop at 543.165; first frame 1.6 s after `start`. Feature: `start_position` 499.397, 7 s before the stop at 506.397. |
| T2e Up Next to the next episode | 2026-10-23 | 55R625 / 15.3.4 | TV | S1E10 → S1E11, copy remux | skips into the credits; Play Now | PASS | Up Next opened at the credits with the next episode's still and "S1 · E11 · 24 min", Play Now, a countdown of 35 (the runtime left), Keep Watching, Back, and "Auto-play is On". Play Now: `playing the next episode {"auto":false,"streak":0}`, stop (200), `start` (201) at 0, first frame 2.4 s later in the same player. Back left the player to the series' Detail, which showed S1·E11 ("Resume S1:E11"). |
| T2f Home return focus after playback | 2026-10-23 | 55R625 / 15.3.4 | TV | after T2e; after the feature's Resume | Back from Detail; screenshots 0.3, 2, 4, 8 s | PASS | After T2e the ring was on the series' card at 0.3 and 2 s; at 4 s Continue Watching loaded again with the feature first and the series second (its card now names S1E11), and the ring stayed on the first position, as spec 5.3 has it when the focused card's item is gone. After the feature's Resume and Back, the ring was on the feature's card. |
| T3 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC (Trending's first card) | 10 × Home → Detail → Resume 20 s → Back → Back, then 3 more | PASS | Every cycle started (201), played 20 s, and closed on the first Back (200). `sgnodes/all` at Home: 931 before, 973 after 10 cycles (+4.5%) and 973 after 13, with the same count of each node type after 10 and 13. No BrightScript error, backtrace, or `[ERROR]` line in the run's console; no `[WARN]` during the cycles. |

### Defects found in run 20

1. **Client (with Roku behaviour):** on an MKV original whose container carries ASS tracks, a load that carries the
   selected sidecar stops before its first frame and the session excludes the playable original. 4 of 5 such loads on
   the stock build (T1a's first try, T1b, T1c's late-sidecar reload, FX-022), so AG-201's reload cannot show a late
   sidecar on these files, and a sidecar that is ready in time fails the same way. Each time: content assigned with
   the sidecar; Roku lists it; about 1 s later Roku lists it again beside the container's tracks; within 0.1 s its
   last media read is aborted and no request follows; ECP stays in `buffer` at `current="0"` and the screen is black
   without "Buffering" for 20 s; then `no progress for 20 s {"buffer":100,"kind":"no_output"}`, `plan_failed`, and
   `failure_recovery` `decoder_no_output`, and the server moves the session to `server_remux_hls`. T1f's logging
   build shows what happens at the second listing: Roku reports `currentSubtitleTrack` `mkv/3` and `subtitleTrack`
   as the bare path, so `onVideoSubtitles` finds the listed name different and selects the sidecar again while the
   node buffers; 0.17 s later `bufferingStatus` reads 100 and `Video.state` is `finished`. Skipping that selection
   played both tries. Cause inferred from two tries. The stall clock also takes the `finished` load's 100 reading as
   a decoder with its media, a state the client's own write caused (AG-200 decision 2).

Observations for review, not counted as defects: S3E4 and later episodes now open a second version (HEVC 2160p, AAC,
SRT only) by deep link, so the lab's ASS originals are S3E1–S3E3 and FX-022 (whose sidecars match S3E3's); sidecar
conversion took 5.5 s for a 1.5 GB episode and 77.3 s for the 13.7 GB feature; a 10 s refusal on an original never
reached the client (Roku's buffer, then Roku's own retries, covered it), so the original's reconnect was not
exercised; reloads of content that had not played waited 3.4 s for the stop (T1c, T1d); a pause sends no progress
of its own (the 10 s cadence reported it); after a local seek back on the transcode two segment requests were
answered 404, with nothing visible; T1e's copy remux rebuffered 16 s at 165 s with media arriving, and Auto stepped
down to a transcode as spec 9.7 intends.

## Run 21 — run 20 fix: no re-selection of a selected sidecar, client-caused stops

Twenty-first hardware pass on the same TV: the device check of AG-203 (the player never selects again a sidecar Roku
reports selected and leaves a track Roku found in the stream alone; a `finished` right after a client write reloads) on
the run 20 fixtures, the late path on an episode whose sidecar had not been converted, subtitle switches in place, and
stability. Lab stack on silo-server `roku/client-support` at `c166d16d1`, 1-hour access tokens, proxy node disabled.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `2f7f4a1`, installed at the start and left installed; no temporary build.
- **Start state:** the dev app signed in to the lab on the "no-PIN" profile; Roku Home, nothing playing, the HDMI 1
  device idle (A-10), two minutes of ECP polling without change. Roku's caption mode was On at the start; subtitle Off
  in T3 wrote Off, and Options' Captions rows set it back to On, which `device-info` read at the end. Ended on Roku Home
  with nothing playing.
- **Lab:** no container was touched, no setting written, and no probe control file created; one login and logout for a
  read-only scan of the lab's versions that carry ASS. The plays changed the watch state of the titles used.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s (its `format` element's `captions`
  attribute is quoted below as Roku's caption format), ECP key accept times, screenshots taken when ECP reported a
  target position, and the API-origin header probe (16:17–17:11: 27 starts, 27 stops, 25 `track_change`, no
  `failure_recovery`, `quality_change`, or `seek_reanchor`; 245 media and subtitle requests, all with `Authorization`
  and `X-Profile-Id`). The English sidecars of FX-028, S3E1, FX-022, S3E2, S3E3, and S3E8 were already converted, and
  S3E4–S3E7 and S3E9–S3E11 open a version without ASS, so the late path ran on S3E12.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a English (ASS) on an original whose sidecar is ready (AG-203) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-028, `original_http` (`validated_original_playback`), English sidecar cached | caption mode On; deep link, Options Subtitles English at 25–37 s; three sessions | PARTIAL | Each load: content assigned with the sidecar 2.2–2.3 s after the key (`content assigned after the stop` 671–687 ms); Roku listed the sidecar, then about 1 s later the sidecar beside `mkv/3` and `mkv/4`; `Roku reports a track of its own as playing while the sidecar is selected; left as it is {"playing":"mkv/4"}` at that listing and again at the first frame, 4.7, 4.8, and 7.1 s after assignment. No selection is logged or left pending after the first frame (the check found the sidecar selected). English cues at 87 and 105 s in all three (6 of 6 shots). No `no progress`, `failure_recovery`, or `finished right after` line. ECP read `captions="ssa"` through each load's play, where run 20's sidecar loads read `srt`, and the cues are pixel-identical to run 20's sidecar cues at the same positions, so the screen cannot tell which track drew them; T5 points to the file's own track. |
| T1b the same on S3E1 (AG-203) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S3E1), MKV H.264 + E-AC-3 2.0 with seven ASS tracks, `original_http`, sidecars cached | caption mode On; English at 393, 494, and 565 s | PARTIAL | Three sidecars (English, Arabic, Spanish) on content assigned 1.9 s after the key; the second listing about 1 s later added `mkv/3` to `mkv/9`; `left as it is {"playing":"mkv/3"}` at it and at the first frame, 3.6–5.6 s after assignment. English cues in 22 of 28 shots (the rest between lines); no failure line; ECP `ssa` throughout. A fourth load in T3, whose content carried only the English sidecar, went the same way (first frame 9.3 s after assignment, cues in 3 of 6 shots). |
| T1c the same on FX-022 (AG-203) | 2026-10-23 | 55R625 / 15.3.4 | TV | FX-022, the same file class, sidecars cached | caption mode On; English at 484, 548, and 609 s | PARTIAL | Four sidecars on content assigned 1.8 s after the key; second listing with `mkv/3` to `mkv/9`; `left as it is {"playing":"mkv/3"}` twice per load; first frame 3.4–4.5 s after assignment; English cues in 20 of 24 shots; no failure line; ECP `ssa` throughout. |
| T2 late sidecar on an original (AG-201, AG-203) | 2026-10-23 | 55R625 / 15.3.4 | TV | library series episode (S3E12), MKV H.264 + AAC 2.0 with fifteen ASS tracks, `original_http`, English sidecar never converted before | caption mode On; deep link from 0; English at 31.7 s | PARTIAL | `track_change` at 31.74 s; content assigned without the sidecar 3.9 s after the key, which went from `startup` to `buffer` and never played; the sidecar came 5.2 s after the `track_change`: `the subtitle came after its content started; the plan reloads at the position {"replan":false}`, `the Video node is still stopping {"ms":3000}`, `content assigned after the stop {"ms":3376}` with the sidecar, two listings, first frame 2.5 s later; progress read 31.74 and then 34.08 s, the same position. No "left as it is" line and ECP `srt` from the first frame: Roku played the sidecar. Cues from the first shot after the reload (8 of 13 shots). No `no progress`, `failure_recovery`, or `finished right after` line. Not observed: play without cues, since the sidecar came before the sidecar-less content's first frame (as in run 20 T1c). A second episode of the class (S3E8) turned out to be converted already; its content carried the sidecar, Roku played it (`srt`), and cues drew after the opening. |
| T3 subtitle switches in place (AG-193, AG-203) | 2026-10-23 | 55R625 / 15.3.4 | TV | S3E1 as in T1b | caption mode On; Options Subtitles; two sessions | PASS | First session: English's content carried only its own sidecar (Arabic and Spanish came 0.1–0.3 s after it, while that content waited for the stop, and were not added), so English → Arabic reloaded, as for any sidecar the content does not carry; Arabic → English then switched in place (ECP `ssa` → `srt` 0.5 s after the key). The next English → Arabic came with the access token's renewal 30 min after launch and reloaded with the new media credential, as designed (`canRetrack`). On that content Arabic → English → Arabic → English → Off, and in a second session (started under caption mode Off, so its content carried four sidecars) English → Arabic → English → Off: nine switches, each one `track_change` with no new plan, no new content, no stop, and no "did not switch" or "own as playing after the switch" line. English drew after each English (19 of 27 shots); Arabic drew its own cues after each Arabic in place (16 of 26 shots), as boxes (observations); Off wrote caption mode Off and nothing drew in 18 shots. Captions On afterwards wrote On and reloaded without the carried tracks (`the plan follows the caption mode`). |
| T5 a non-English sidecar selected as content loads (found in T3) | 2026-10-23 | 55R625 / 15.3.4 | TV | S3E1 (T3's two reloads with Arabic); S3E12 (Italian, cached) | caption mode On; Options Subtitles Arabic, Italian | FAIL | Arabic, twice: Roku listed the Arabic, English, and Spanish sidecars and `mkv/3` to `mkv/9`, reported `mkv/3` (the file's English track) as playing, the player logged `left as it is {"playing":"mkv/3"}` at the second listing and the first frame, ECP read `ssa`, and English cues drew in 13 of 14 shots while Options showed Arabic checked (defect 1). Italian on S3E12: the content carried the Italian and English sidecars; no "left as it is" line, ECP `srt`, and English cues drew in 9 of 16 shots with Italian checked. A switch to Arabic in place on the same content drew Arabic (T3). |
| T4 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | SYNTHETIC (Trending's first card) | 10 × Home → Detail → Resume 20 s → Back → Back, then 3 more | PASS | Every cycle started (201), played 20 s, and closed on the first Back (200). `sgnodes/all` at Home: 940 before, 974 after 10 cycles (+3.6%) and 974 after 13. No BrightScript error, backtrace, or `[ERROR]` line in the run's console (1,824 lines); its one `[WARN]` is T2's stop wait. |

### Defects found in run 21

1. **Client (with Roku behaviour):** on MKV originals, a sidecar selected as its content loads is not the track Roku
   draws when its language differs from Roku's caption language; Roku draws an English track and the player leaves it.
   S3E1 with Arabic selected (two loads): Roku reported `mkv/3`, the file's English ASS track, as playing, ECP read
   `captions="ssa"`, and English cues drew with Options showing Arabic; the player logged `Roku reports a track of its
   own as playing while the sidecar is selected; left as it is {"playing":"mkv/3"}` at the second listing and at the
   first frame and selected nothing (AG-203 fix 1). S3E12 with Italian selected: Roku drew the English sidecar the
   content also carried (ECP `srt`, no line). Switches in place to the same tracks drew them (T3). So AG-203's
   assumption that `mkv/3` in `currentSubtitleTrack` while `subtitleTrack` names the sidecar does not mean Roku draws
   the file's track does not hold on these files, and T1's English cues (ECP `ssa` on all nine loads) were most likely
   the file's own English track rather than the sidecar. AG-203's named next step, one selection after the settle time
   while Roku reports another track, was not tried; the stock build does not log `subtitleTrack`.

Observations for review, not counted as defects: the Arabic sidecar's cues drew as boxes, so Roku's caption font on
this TV has no Arabic glyphs (the TV's caption settings were not changed). Roku's pick when content carrying the
selected sidecar opens differs by file: the file's own track (`ssa`) on FX-028, S3E1, and FX-022, a sidecar (`srt`) on
S3E12 and S3E8; cause not traced. Content built when the selected sidecar arrives does not take the other sidecars
that arrive while it waits for the stop, so the first switch to one of them reloads. The server appears to convert all
of an episode's text tracks with the first (S3E12's others came 0.5–1.9 s after English, and Italian was cached 20
minutes later). The late path's reload waited 3.0 s for the stop of content that had not played (run 20 the same).

## Run 22 — run 21 fix: one corrective subtitle selection after the settle window

Twenty-second hardware pass on the same TV: the device check of AG-205 (after the settle window the player selects the
chosen sidecar once when Roku plays another track, and accepts the file's own track in the sidecar's language) on two
anime episodes, English choices, switches, logging, and stability. This run used a non-lab Silo development server at the
server owner's request, as already signed in; the lab header probe was not in the path, so the console and ECP are the
only sources.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `35bf1c2`, installed at the start and left installed; no temporary build.
- **Start state:** the dev app signed in on the profile it opens without a picker; Roku Home after the A-10 check (dev
  app in front, nothing playing, the HDMI 1 device idle, two minutes of ECP polling without change). Roku's caption
  mode was On; subtitle Off in T3 wrote Off, choosing a track wrote On again, and `device-info` read On at the end.
  Ended on Roku Home with nothing playing, still signed in (every session line after the install reads `signed_in`).
- **Server:** no sign-in, sign-out, server switch, API call, or setting change; the plays changed the watch state of
  the two episodes used, and one session switched an episode's audio track in Options.
- **Sources:** the dev console (local time; the new `subtitleTrack written` and `Roku's subtitle tracks` debug lines),
  ECP `query/media-player` every 0.5 s (`captions` is Roku's caption format), ECP key accept times, and screenshots
  taken when ECP reported a target position. Times below are seconds after the load's first frame.
- **Files:** A, an anime episode, MKV original (`original_http`), AAC audio, with two built-in English ASS tracks
  (Roku lists them as `mkv/2` "Full Subtitles" and `mkv/3` "Signs & Songs"), a built-in PGS track, and external SRT
  sidecars in seven languages including English and Arabic. B, an anime episode, MKV with two built-in English ASS
  tracks (one Forced) and external SRT sidecars in seven languages (English twice, one Forced); with the profile's
  English audio the server plays it as a copy remux (`server_remux_hls`, `hls_packaging_required`), and with its
  default Japanese audio as an original. Every anime episode checked in the library (five) carries more than one
  built-in English track; on B Roku lists only one of them (`mkv/4`, the full track, not the Forced one), which gives
  AG-205's accepted case.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1a a non-English sidecar after a reload (AG-205, run 21 T5) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original | caption mode On; Options Subtitles German, Spanish, Arabic during play, each not carried by the playing content | PASS | Each pick reloaded (content assigned 0.75–0.95 s after the stop) with only the chosen sidecar; Roku listed it, then about 4 s later beside `mkv/2` and `mkv/3`, and reported `playing` `mkv/3` at that listing and at the first frame. At 3.67, 3.45, and 3.34 s: `Roku plays another subtitle track once the content settled; the sidecar is selected {"playing":"mkv/3"}` and one `subtitleTrack written` with the listed name (`/tmp/plugin/<dir>/tmp:/subtitles/trackN.srt`); ECP `ssa` → `srt` 0.2–0.5 s later; 3.0–3.5 s after the write `Roku's subtitle tracks` `after the selection` reported the sidecar playing, and no further line. The chosen track drew in 3 of 3 loads: German 3 of 8 shots, Spanish 7 of 7 after the write, Arabic as boxes 6 of 8 (Roku's font has no Arabic glyphs; shape and timing differ from English). One write per load; no `left as it is`, `finished right after`, reload loop, `no progress`, `failure_recovery`, or route exclusion. |
| T1b the same on a second file (AG-205) | 2026-10-23 | 55R625 / 15.3.4 | TV | B: one load as a copy remux, four as an original | caption mode On; German (remux); Options Audio Japanese with German kept, then Spanish, French, French (original) | PASS | Copy remux: Roku listed only the sidecars (German, Arabic, Danish), played German from the first frame, and the settle check wrote nothing (German 4 of 10 shots). Original, four loads: Roku listed the sidecars and `mkv/4`, reported `playing` `mkv/4` at the first frame, and at 3.39, 3.40, 3.28, and 3.01 s the settle line and one write followed, after which Roku reported the sidecar playing (ECP `ssa` → `srt`). German 9 of 18 shots, Spanish 6 of 8, French 5 of 8 and 2 of 10 (a quiet stretch). Shots taken between the first frame and the write (six loads) showed no cue. No failure line. |
| T2a English where the file has two English stream tracks (AG-205 decision 2) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original | caption mode On; Options Subtitles English (external SRT), twice | PASS | Not the accepted case: Roku lists two English stream tracks, so as designed the settle check wrote the sidecar once (3.39 and 3.42 s) and Roku then played it (ECP `srt`). English sidecar cues drew in both loads (5 of 10, after 8 shots in a pause, and 7 of 7 after the write). Roku's own pick here was `mkv/3`, the "Signs & Songs" track. |
| T2b English accepted where the file has one English stream track (AG-205 decision 2) | 2026-10-23 | 55R625 / 15.3.4 | TV | B, original | caption mode On; Options Subtitles English (external SRT), three loads at about 459, 424, and 577 s | FAIL | Each load as intended in the console: Roku listed the English sidecar and `mkv/4`, reported `mkv/4` playing, and at 3.36, 3.53, and 3.31 s logged `Roku plays the file's own subtitle track in the sidecar's language; accepted {"playing":"mkv/4"}`, with no write after the first frame; ECP `ssa` throughout. No English cue drew: 0 of 50 shots across the three loads (464–609 s and 430–457 s; the last 10 of the first load full-frame with the Options panel closed). A German sidecar load over 600–627 s on the same file drew 8 of 10, including at 603 and 609 s where the third English load drew nothing (defect 1). |
| T3 subtitle switches in place (AG-193, AG-203) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original; B, original | caption mode On; A: English → German → Off → English; B: German → Arabic (carried), and Off | FAIL | No switch ran in place: every `track_change` reloaded, including Off (B at 535 s, A at 956 s) and German → Arabic while the content carried Arabic (B). Each load drew its own track or none: English 1 of 10 then 5 of 10, German 8 of 10, Off none in 8 (caption mode written Off, then On again with English); the last English sidecar arrived 0.1 s after its content was built (after the 3 s wait) and AG-201's local reload carried it. No stop, `failure_recovery`, or `no progress`. No renewal line, and 37 local seeks on the same content stayed local; the plans name `"origin":"proxy"`, where the lab ran with the proxy disabled. Cause not traced (defect 2). |
| T4 logging hygiene (AG-205 fix 3) | 2026-10-23 | 55R625 / 15.3.4 | TV | the run's console (2,700 lines) | grep for `://`, `token`, `st=`, `Authorization` | PASS | No `token`, `st=`, or `Authorization` anywhere. No `subtitleTrack written`, `Roku's subtitle tracks`, `Roku lists subtitle tracks`, settle, `accepted`, or `left as it is` line contains `://`; their values are listed names, `tmp:/` paths, and `mkv/N`. `://` appears only in the existing debug `api: start` lines (857, one request URL each), one `api: server changed` origin line replayed from before the run, and four Roku texture warnings. |
| T5 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | A once, then B (A's position neared its credits) | 10 × Home → Continue Watching → Detail → Resume 20 s → Back → Back | PASS | Every cycle played 20 s and closed on the first Back. `sgnodes/all` at Home: 1,187 before, 1,189 after 10 cycles (+0.2%). No BrightScript error, backtrace, or `[ERROR]` line in the run's console. Warnings during the cycles: A's subtitle `too_large` (below) and B's copy-remux start lines (below). |

### Defects found in run 22

1. **Client (with Roku behaviour):** AG-205's acceptance of a stream track in the sidecar's language leaves the viewer
   with no subtitles on file B. With English chosen, Roku lists one English stream track (`mkv/4`, the file's full ASS
   track) beside the English sidecar, reports it playing, ECP reads `captions="ssa"`, and the player logs `accepted`;
   but nothing draws on the caption plane (0 of 50 shots over three loads), where a sidecar draws cues at the same
   positions. So `currentSubtitleTrack` naming a track in the right language does not show that Roku draws it; the
   decision's premise came from run 21's files, whose English track drew. Run 21's open question (whether ECP `ssa`
   meant the file's track drew) is answered for this file: it did not.
2. **Client (cause not traced):** on this server no subtitle switch runs in place. Off, and a switch to a sidecar the
   content carries, each send a `track_change` whose plan the player does not treat as the same media, and the content
   reloads at the position (about 9 s from the pick to the next first frame, and a corrective write when Roku picks its own track).
   Local seeks stay local and no credential renewal is logged. These plans name the proxy origin; the in-place check
   compares stream URLs with only the `st` token removed.

Observations for review, not counted as defects: after a pick that reloads, the Options panel stays open over the new
content, and a Back 1 s after the pick or at the reload's first frame did not close it (a later Back did), so a Back
meant to leave the player only closed the panel. Before each settle write, a shot showed no cue in every load (Roku
reported `mkv/3` or `mkv/4`). On file A the profile's Auto subtitle (the built-in full English ASS) fails `too_large` on
every start ("Subtitles are too large to show."; 21.8 s the first time). On B's copy remux, every start logged `the
load started past its start; seeking back` (11 times on 10 starts) and `the seek back did not land` (10), so each resume
began about 8 s late, and its English ASS sidecar came after the content started twice per start (`it shows after the
next reload`). B's first remux start also re-anchored after the intro skip (`timeline_offset_seconds` 89.131), then
logged `Video error -5 … 410` on the replaced load and loaded again without `failure_recovery`. Each pick with a
sidecar still logs two setup writes before content starts (the listed name, then the bare `tmp:/` path).

## Run 23 — run 22 fixes: English corrective write, in-place switches on proxy plans, Options Back, sidecar budget

Twenty-third hardware pass on the same TV: the device checks of AG-207 to AG-210 on run 22's two files, a regression
check of run 22 T1, logging, and stability. Like run 22, this run used the non-lab Silo development server at the
server owner's request, as already signed in, with plans routed through a proxy node; the console and ECP are the only
sources.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `5ab23bc`, installed at the start and left installed; no temporary build.
- **Start state:** Roku Home after the A-10 check (nothing playing, the HDMI 1 device idle, two minutes of ECP polling
  without change); the dev app signed in, opening its remembered profile without a picker. Roku's caption mode was On;
  subtitle Off wrote Off, choosing a track wrote On again, and `device-info` read On at the end. Ended on Roku Home with
  nothing playing, still signed in (every session line after the install reads `signed_in`).
- **Server:** no sign-in, sign-out, server switch, API call, or setting change. The plays changed the watch state of
  the two episodes. File B's audio was switched to Japanese for its original route and back to English, as found; each
  file's subtitle was put back to the profile's pick (the built-in English ASS) before leaving it.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s (`captions` is Roku's caption
  format), ECP key accept times, `query/chanperf` (it answers on this dev build) and `query/sgnodes/all?count_only=true`,
  and screenshots taken when ECP reported a target position. Times below are seconds after the load's first frame;
  positions are media seconds.
- **Files:** A and B as in run 22. B plays as a copy remux with its English audio and as an original with Japanese.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 English on file B (AG-207) | 2026-10-23 | 55R625 / 15.3.4 | TV | B, original | caption mode On; Options Subtitles English (external SRT) during play, three loads at about 450, 609, and 755 s (the third from an Off → English switch that reloaded) | PASS | Each load's content carried only the English sidecar; Roku listed it, then beside `mkv/4`, and reported `playing` `mkv/4` at that listing and at the first frame. At 3.46, 3.43, and 3.41 s: `Roku plays another subtitle track once the content settled; the sidecar is selected {"playing":"mkv/4"}` and one `subtitleTrack written` with the listed name; ECP `ssa` → `srt` within 0.5 s; 3.0–3.5 s later `after the selection` reported the sidecar playing. English cues in 6 of 20 shots (1 of 10 over 472–499 s, where no shot showed a cue after the first, then 5 of 10 over 513–539 s), 6 of 10 (643–670 s), and 4 of 6 (762–777 s). No `accepted`, `left as it is`, or `finished right after` line in the run; each load still logged the two setup writes before its content started. |
| T2 subtitle switches in place on proxy plans (AG-208) | 2026-10-23 | 55R625 / 15.3.4 | TV | B, original; A, original | caption mode On; Options Subtitles; B: English → Off → English → Off → German → Arabic → Off; A: English → Off → English → Off → Arabic → Off; then a local seek on each | FAIL | 3 of 11 switches ran in place, all to Off (B English → Off, A English → Off, A Arabic → Off): one request, no plan, no new content, no stop (B showed one 0.5 s `buffer` reading), caption mode written Off and `subtitleTrack` written empty, and no cue in 12 shots; ECP `captions` did not change to `none` (B `srt` → `ssa`, A stayed `srt`). The other 8 each got a plan and reloaded at the position (8.6–11.3 s from the pick to the next first frame): English → Off twice, Arabic → Off on B, and five switches to a sidecar the playing content carried and Roku listed (Off → English twice, back to the English sidecar still on the content, and Off → German, German → Arabic, and Off → Arabic). No `did not switch` line, so the reducer refused to keep the content when the plan arrived (`canRetrack`). The reloads' plan lines read `"origin":"proxy"`, `original_http`, `validated_original_playback`, `http_progressive`, `mkv`, with the same codec fields as the plan before. Whether the proxy node changed cannot be seen from the client: the build logs neither the stream URL nor the condition that failed, every request the app logs goes to the configured origin, and ECP reports no URL. No timing pattern: in place 38–107 s after the content's plan, reloads 52–158 s; the Roku clock matched an NTP-synchronized clock within 0.1 s. Local seeks stayed local (Instant Replay −10 s on B, a ladder seek from 1,126 to 736 s on A, three ladder seeks on B). Each English load carried only the English sidecar, so carried-language switches were tried from contents loaded with Off or German. |
| T3 Options Back (AG-209) | 2026-10-23 | 55R625 / 15.3.4 | TV | B, original and copy remux; A, original | caption mode On; one Back after each Options pick: 0.93–1.60 s after six reloading picks (two audio, four subtitle), at the reload's first frame (0.62–0.74 s after it) on three, and 2.1 s after eleven switches (three in place, eight reloading) | PASS | The panel closed on the first Back 20 of 20 times (a screenshot after each), and playback went on (ECP `play`, the next shots taken). |
| T4 sidecar budget, file A's Auto subtitle (AG-210) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original, the profile's subtitle (the built-in full English ASS) | caption mode On; two starts from Detail, one pick of the track during play, and the ten T7 starts | FAIL | All 13 attempts: `api: request failed {"kind":"too_large",…,"size":10736314,"status":200}` after a 2.4–2.7 s download, then `player: subtitles failed {"format":"ass","kind":"too_large","selected":true}`. `size` is the completed download's file size: the file is 10.24 MiB, 2.24 MiB over the 8 MiB budget. No cue drew (0 of 15 shots over 1,086–1,160 s), so there is no time to the first cue; Roku reported `mkv/3` playing. "Subtitles are too large to show." did not appear in shots 0.6–4 s after the failure: the status line read "Buffering", which outranks notices, until the 4 s notice expired. Memory (`chanperf` used / anon, node count): Detail before the start 43.0 / 20.6 MB, 789; playing without cues 104.9–108.0 / 19.6–20.4 MB, 808; Detail after Back 39.8 / 17.2 MB, 782. |
| T5 a non-English sidecar after a reload (run 22 T1) | 2026-10-23 | 55R625 / 15.3.4 | TV | B, original; A, original | caption mode On; French on B, Spanish on A, each not carried by the playing content | PASS | French: content carried French, Arabic, Danish, and German; `mkv/4` at the first frame; one write at 3.33 s; ECP `ssa` → `srt`; French cues in 8 of 10 shots (594–621 s). Spanish: the sidecar came after its content started and AG-201's local reload carried it; `mkv/3` at the first frame; one write at 3.35 s; Spanish cues in 7 of 10 (760–787 s). T2's reloads to German and Arabic on B and Arabic on A also wrote once, at 3.38, 3.43, and 3.40 s. |
| T6 logging hygiene | 2026-10-23 | 55R625 / 15.3.4 | TV | the run's console (1,995 lines) | grep for `://`, `token`, `st=`, `Authorization` | PASS | No `token`, `st=`, or `Authorization` anywhere (case-insensitive). `://` appears only in the existing debug `api: start` lines (591). No player, subtitle, or media line contains `://`; their values are listed names, `tmp:/` paths, and `mkv/N`. |
| T7 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | A (the first Continue Watching card) | 10 × Home → Continue Watching → Detail → Resume 20 s → Back → Back | PASS | Every cycle played 20 s and closed on the first Back. `sgnodes/all` at Home: 1,198 before, 1,189 after 10 cycles (−0.8%); `chanperf` 46.1 / 23.5 MB before, 42.8 / 20.1 MB after. No BrightScript error, backtrace, or `[ERROR]` line in the run's console. Warnings: A's `too_large` on every start (T4) and B's copy-remux start lines (below). |

### Defects found in run 23

1. **Client (AG-210):** file A's built-in English ASS is 10,736,314 bytes as served, over the new 8 MiB sidecar budget,
   so its Auto subtitle still never shows (13 of 13 starts, `too_large`). The warning's new `size` answers AG-210's open
   question: 8 MiB is short by 2.24 MiB for this file. Its cue count is unknown, since the client refuses the file
   before converting it.
2. **Client (cause not traced; AG-208):** on proxy-routed plans most subtitle switches still reload: 3 of 11 in place,
   all three to Off, and none of the five switches to a sidecar the content carried. The reducer refuses to keep the
   content when the plan arrives, and nothing in the console or ECP says which condition failed: another proxy node in
   the URL (AG-208's known case with two or more proxies), the kept URL's renewal margin, or another plan field. The
   stock build cannot tell them apart; a debug line naming the failing `canRetrack` condition would.

Observations for review, not counted as defects: when a sidecar fails while its content buffers, the 4 s notice
expires behind "Buffering" and the viewer sees no reason for the missing subtitles. After Off in place, ECP `captions`
kept reporting a format (`srt` or `ssa`) while nothing drew. On B's copy remux, both starts logged `the load started
past its start; seeking back` and `the seek back did not land`, and the remux's English ASS sidecar came after its
content started twice per start, as in run 22. The audio switch from the remux to the original logged `Video error -5
… 410` on the replaced load and went on without `failure_recovery`, as in run 22. English loads on both files carried
only the English sidecar: the content waited the 3 s for it, and the others, past their 1 s wait, were left out.

## Run 24 — run 23 fixes: retrack refusal reasons, bounded ASS conversion, memory-aware sidecar budget, notice after buffering

Twenty-fourth hardware pass on the same TV: the device checks of AG-212 to AG-215 on run 22's two files, a regression
check of runs 22–23, logging, and stability. Like runs 22 and 23, this run used the non-lab Silo development server at
the server owner's request, as already signed in, with plans routed through proxy nodes; the console and ECP are the
only sources.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `28d524c`, installed at the start and left installed; no temporary build.
- **Start state:** Roku Home after the A-10 check (nothing playing, the HDMI 1 device idle, two minutes of ECP polling
  without change); the dev app signed in, opening its remembered profile without a picker. Roku's caption mode was On;
  subtitle Off wrote Off, choosing a track wrote On again, and `device-info` read On at the end. Ended on Roku Home
  with nothing playing, still signed in (every session line after the install reads `signed_in`).
- **Server:** no sign-in, sign-out, server switch, API call, or setting change. The plays changed the watch state of
  the two episodes and, by mistake, of a third: file A's third start ran it past the server's watched mark, Detail's
  main button moved to the next episode, and the next Resume played that episode for 32 s before Back. File B's audio
  was switched to Japanese for its original route and back to English, as found; each file's subtitle was put back to
  the profile's pick (its built-in English ASS) before leaving it.
- **Sources:** the dev console (local time; the console's replayed history from before the install is left out), ECP
  `query/media-player` every 0.5 s (`captions` is Roku's caption format), ECP key accept times, `query/chanperf` and
  `query/sgnodes/all?count_only=true`, and screenshots taken back to back during starts and when ECP reported a target
  position. Cue counts are shots with caption-plane text over shots taken. Times below are seconds after the load's
  first frame unless stated; positions are media seconds.
- **Files:** A and B as in run 22. A's Auto subtitle, its built-in full English ASS, is 10,736,314 bytes as served
  (run 23). B plays as a copy remux with its English audio and as an original with Japanese.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 file A's large ASS (AG-214) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original, the profile's subtitle (the built-in full English ASS) | caption mode On; three Resumes from Detail and one start from the episode card (from the start, intro skipped automatically) with the profile's Auto subtitle; two picks of the track during play from Off (not carried); then the ten T6 starts | PASS | All 16 attempts: `api: download budget {"availableKb":…,"budget":16777216,…,"tmpFreeBytes":null}` (16 MiB; `availableKb` 484,616–518,888 at each attempt's first download), no `too_large`, then 7.6–8.3 s after that download began `media: subtitle converted {"cues":329,"dropped":8345,"error":null,"format":"ass","merged":373,"size":10736314}`. The sidecar came after its content started, so AG-201's local reload carried it; the first frame followed 17.9–19.5 s after the start's plan (15.1 and 15.4 s after the picks' plans), Roku reported `mkv/3` playing, and the one settle write came 3.28–3.53 s after the first frame. First cue in shots 22.3–26.1 s after the four starts (2.5–6.7 s after the first frame) and 19.6 s after the first pick; after the second pick no shot over 712–751 s showed a cue, then cues from 754 s. Cues: 24 of 39 shots (941–1,016 s), 17 of 32 (1,094–1,147 s), 17 of 27 (1,176–1,221 s), 27 of 52 (93–180 s), 6 of 20 then 11 of 12 (437–516 s), 7 of 14 (749–781 s). Dialogue and signs both drew as plain bottom-centred text (an on-screen disclaimer and a place-name caption among them); no vector shapes or repeated stacked lines; songs not observed (opening skipped, ending not reached). The status line read "Buffering" through each load; "Loading subtitles…" never showed. Memory (`chanperf` used / anon MB, nodes): Detail before 31.1 / 13.6, 789; while the sidecars downloaded and converted 33.4–42.6 / 14.0–21.1 (anon peak 21.1, during a pick); playing with cues 100.6–105.9 / 15.0–19.6, 803–808; Detail after Back 36.0–39.3 / 15.0–17.9, 782–786. No BrightScript error, freeze, or watchdog restart. |
| T2 retrack refusal reasons on proxy plans (AG-212, AG-213) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original; B, original | caption mode On; Options Subtitles; A: English → Off → English → Off → Arabic → Off; B: English → Off → English → Off → German → Arabic → Off (run 23's sequences); then Instant Replay on each | PASS | 3 of 11 switches ran in place, all on B: English → Off and Arabic → Off (one request, no plan line, no new content, `subtitleTrack` written empty, one 0.5 s `buffer` reading), and German → Arabic, a sidecar the content carried (one `subtitleTrack written` of the Arabic sidecar, no buffer reading; run 23 had none of five such switches in place). Each of the other 8 logged one `the track change's plan does not keep the playing content` line and reloaded at the position: 5 switches to Off or a carried sidecar named only `stream_origin` with `sameOrigin` false (A English → Off twice, Off → Arabic, Arabic → Off; B English → Off); 3 switches to a sidecar the content did not carry named `in_place` (the player's own reload request) with `stream_origin` and `sameOrigin` false twice (A Off → English, B Off → German, the latter because the in-place Off had kept the English-only content) and alone with `sameOrigin` true once (B Off → English). No other condition named anywhere in the run (no `url_expiry`, `credential_aging`, `renewal_owed`, or plan field on a subtitle switch), so no seconds-left values. On A every plan in the run came back on another origin (all 5 switches, the restoring pick, and the Auto `track_change` at each of 14 starts); on B, 5 of 8 subtitle plans came back on the content's origin, and those to Off or a carried sidecar ran in place. Arabic drew as boxes, as in run 22. Instant Replay stayed local on both (A 681 → 671 s, B 1,093 → 1,082 s: no plan, no new content, one 1 s `buffer` reading), as did a ladder seek on B (1,220 → 596 s). |
| T3 notice after buffering (AG-215) | 2026-10-23 | 55R625 / 15.3.4 | TV | — | no failure forced | NOT TESTED | No subtitle failure occurred with this build: no `too_large`, `subtitles failed`, or other sidecar failure after the install (the only such lines are in the console's replayed history from the previous build). |
| T4 regression: English on file B, a non-English pick after a reload, Options Back (runs 22–23) | 2026-10-23 | 55R625 / 15.3.4 | TV | B, original and copy remux; A, original | caption mode On; B: English (external SRT) from the English ASS content, German from Off (not carried); one Back 2.1 s after every Options pick | PASS | English: the content carried only the English sidecar; Roku listed it, then beside `mkv/4`, reported `mkv/4` playing at the first frame, and at 3.49 s `Roku plays another subtitle track once the content settled; the sidecar is selected {"playing":"mkv/4"}` with one `subtitleTrack written`; ECP `ssa` → `srt` within 0.5 s; 3.5 s later `after the selection` reported the sidecar playing; English cues in 6 of 11 shots (654–679 s). The two other English loads on B wrote once at 3.35 and 3.38 s. German: content carried German, Arabic, and Danish; `mkv/4` at the first frame; one write at 3.45 s; German cues in 2 of 5 (931–943 s). No `accepted`, `left as it is`, or `finished right after` line in the run. The panel closed on the first Back after all 16 picks (11 switches, the two restoring subtitle picks, the two audio picks, the English pick). |
| T5 logging hygiene | 2026-10-23 | 55R625 / 15.3.4 | TV | the run's console (2,563 lines, 80 of them replayed history) | grep for `://`, `token`, `st=`, `Authorization` | PASS | No `token`, `st=`, or `Authorization` anywhere (case-insensitive). `://` appears only in the existing debug `api: start` lines (614). No player, subtitle, or media line contains `://`; the refusal lines carry only condition names and `sameOrigin`, the budget lines numbers, and the conversion lines format and counts; other values are listed names, `tmp:/` paths, and `mkv/N`. |
| T6 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | A (the first Continue Watching card; each Detail checked to be A's before Resume) | 10 × Home → Continue Watching → Detail → Resume 20 s → Back → Back | PASS | Every cycle played 20 s and closed on the first Back; each converted A's sidecar (329 cues) with no `too_large`. `sgnodes/all` at Home: 1,206 before, 1,189 after 10 cycles (−1.4%); `chanperf` 42.0 / 19.5 MB before, 41.3 / 18.7 MB after. No BrightScript error, backtrace, or `[ERROR]` line after the install. Warnings: `the Video node is still stopping {"ms":3000}` at the late-sidecar reload of all 14 A starts (and no other load), B's copy-remux start lines (below). |

### Defects found in run 24

None in the fixes under test. AG-214's budget, conversion, and filtering work on file A's 10.24 MiB track, and the
AG-212 lines name only `stream_origin` (or the player's own `in_place`) on every reload, as AG-213 predicted.

Observations for review, not counted as defects: (1) file A's starts now take 17.9–19.5 s from the plan to the first
frame (10–11 s in run 23): the sidecar converts in about 8 s, arrives after its content started, and AG-201's local
reload then waits 3.3–3.6 s for the Video node to stop (`still stopping` at 3 s, then `content assigned after the
stop`); the other 35 stops in the run took 0.09–0.94 s. The status line shows "Buffering" throughout. (2) A's plans
never landed on the content's origin (20 of 20, starts included), while B's subtitle plans kept it 5 of 8 times; with
two proxies, strict alternation between consecutive plans would give A's pattern, but the client cannot see the nodes.
(3) B's copy remux this time logged `the seek back landed` after `the load started past its start; seeking back`, and
its English ASS sidecar again came after its content started (`it shows after the next reload`). (4) The unintended
third episode is a harness gap: a run that resumes a file near its end has to check Detail's main button before
Select.

## Run 25 — run 24 fixes: content kept across proxy nodes, wait for the selected sidecar, sidecar reuse, faster ASS conversion

Twenty-fifth hardware pass on the same TV: the device checks of AG-218 to AG-221 on run 22's two files, a regression
check of runs 22–24, logging, and stability. Like runs 22–24, this run used the non-lab Silo development server at the
server owner's request, as already signed in, with plans routed through proxy nodes; the console and ECP are the only
sources.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `aeb09b2`, installed at the start and left installed; no temporary build.
- **Start state:** the dev app in the foreground (allowed by A-10) after the A-10 check (nothing playing, the HDMI 1
  device idle, two minutes of ECP polling without change), then `key Home`; the dev app signed in, opening its
  remembered profile without a picker. Roku's caption mode was On; subtitle Off wrote Off, choosing a track wrote On
  again, and `device-info` read On at the end. Ended on Roku Home with nothing playing, still signed in (every session
  line after the install reads `signed_in`, through six launches).
- **Server:** no sign-in, sign-out, server switch, API call, or setting change. The plays changed the watch state of
  the two episodes only. File B's audio was switched to Japanese for its original route and back to English, as found;
  each file's subtitle was put back to the profile's pick (its built-in English ASS) before leaving it. A harness bug
  (the stability script's Detail check always passed) played file B twice for about 20 s instead of file A; both were
  file B's own episode, checked afterwards from the Detail shots.
- **Sources:** the dev console (local time; the console's replayed history from before the install is left out), ECP
  `query/media-player` every 0.5 s (`captions` is Roku's caption format), ECP key accept times, `query/chanperf` and
  `query/sgnodes/all?count_only=true`, and screenshots taken back to back during starts and when ECP reported a target
  position. Cue counts are shots with caption-plane text over shots taken. Times are from the plan line unless stated;
  positions are media seconds.
- **Files:** A and B as in run 22. A's Auto subtitle is its built-in full English ASS (10,736,314 bytes as served); its
  other sidecars are external SRTs. B plays as a copy remux with its English audio and as an original with Japanese.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 wait for the selected sidecar (AG-219) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original, the profile's subtitle (the built-in full English ASS) | caption mode On; first start of a fresh app session (the install's launch), Resume from Detail; repeated as the first start of two later sessions | PASS | One load carrying the sidecar: `the content waits for its subtitle; the Video node stops` 0.20 s after the plan, ASS download 2.55 s, `subtitle converted {"cues":329,"dropped":8345,"error":null,"format":"ass","merged":373,"size":10736314}` 4.56 s after the plan, then content listing only that sidecar 0.04 s later. No `the subtitle came after its content started`, no `it shows after the next reload`, no `still stopping` anywhere in the run. First frame 11.76 s after the plan (12.32 s after the keypress); the two repeats 11.91 and 11.57 s (run 24: 17.9–19.5 s). Status line "Loading subtitles…" in the shots at 1.3 and 3.0 s, "Buffering" from the sidecar's arrival. One settle write at 3.44 s after the first frame (`mkv/3` playing), then `after the selection` reported the sidecar playing. First cue in the shot 14.79 s after the plan (3.0 s after the first frame); cues in 14 of 20 shots (925–957 s). Memory (`chanperf` used / anon MB, nodes): Detail 31.2 / 13.6, 789; converting 34.3–38.1 / 14.3–17.7; playing 103.5–103.7 / 18.2–18.4, 808. |
| T2 sidecar reuse in an app session (AG-220) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original, the profile's subtitle | caption mode On; Back and Resume twice in the same session; then Home, relaunch, Resume; also in-play picks of the ASS and two later starts in another session | FAIL | Reuse works: each later start logged `subtitle reused from this session {"format":"ass","selected":true}` 0.17 s after its plan, with no download or conversion of the ASS; content was assigned 1.31 s after the plan (the 1 s wait for the other sidecars and a 130–140 ms stop) and the first frame came 9.45 and 9.32 s after the plan (two later reused starts: 8.33 and 9.05 s; AG-220 expected about 7–8 s; Roku took 8.0–8.1 s from content to first frame). The three external sidecars (an Arabic SRT and two 652 KB SRTs) downloaded and converted again on every start, as AG-220 designs. In-play picks of the ASS (one per file, restoring it) also reused it. After the relaunch the ASS converted again (new session), and the app then stopped on a BrightScript error 0.011 s later, the player frozen on "Loading subtitles…" (defect 1). |
| T3 content kept across proxy nodes (AG-218) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original; B, original | caption mode On; Options Subtitles; A: English ASS → Off → English ASS → Off → Arabic → Off; B: English SRT → Off → English SRT → Off → German → Arabic → Off (run 24's sequences); a ladder seek on A and on B and Instant Replay on B; then 60 s of play | PASS | 9 of 11 switches ran in place, every switch to Off or to a sidecar the content carried (run 24: 3 of 11): one request, no plan line, no new content, `subtitleTrack` written (empty for Off), and one `kept the content on its proxy node` line each (9 in the run; every one of those plans named another node). B's three switches to Off each showed one 0.5–1 s `buffer` reading; A's showed none. English drew after A's Off → English ASS (cues from 755 s, after a dialogue gap from 712 s also seen in run 24) and after B's Off → English SRT (4 of 8 shots, 875–897 s); Arabic drew as boxes, as in runs 22–24; no cue after any Off (0 of 25 shots). The 2 reloads were the switches to a sidecar the content did not carry (A Off → Arabic, B Off → German), each with one `the track change's plan does not keep the playing content {"refused":["in_place","stream_origin"],"sameorigin":true}` (`sameorigin` true: the plan on the content's own node; `stream_origin` compares it with the newest kept plan's node, AG-218), the content waiting for its sidecar and one write 3.35–3.39 s after the first frame. Seeks stayed local (A 916 → 600 s, B 1,314 → 682 s, B 1,088 → 1,077 s: no plan, no new content, one 1–1.5 s `buffer` reading). Play went on 76 s (A) and 85 s (B) after the last kept switch with no error, outage, reconnect, or plan line, and ECP `error="false"` throughout. |
| T4 conversion speed (AG-221) | 2026-10-23 | 55R625 / 15.3.4 | TV | A, original; B, original and copy remux | the run's conversions | PASS | File A's ASS (5 conversions): `subtitle converted` 1.75–1.89 s after its 2.55–2.70 s download ended, 4.36–4.46 s after it began (run 24: 7.6–8.3 s, about 5.3 s of conversion); counts unchanged (329 kept, 8,345 dropped, 373 merged). A's 652 KB SRTs: 2.89–3.29 s each (run 24: 3.3–3.6 s; AG-221 expected about 2.8 s). B's 1,590,194-byte ASS: 2.0–2.4 s after a 0.43–0.64 s download (744 cues, 448 dropped, 6,298 merged). No late reload in the run, so AG-221's slow-stop inference was not exercised. |
| T5 regression: English on file B, a non-English pick after a reload, Options Back (runs 22–24) | 2026-10-23 | 55R625 / 15.3.4 | TV | B, original and copy remux; A, original | caption mode On; B: English SRT from the English ASS content (not carried), German from Off (not carried); A: Arabic from Off; one Back after every Options pick | PASS | English: the content carried only the English sidecar; `mkv/4` playing at the first frame; at 3.48 s `Roku plays another subtitle track once the content settled; the sidecar is selected {"playing":"mkv/4"}` with one `subtitleTrack written`; ECP `ssa` → `srt` within 0.5 s; 3.0 s later `after the selection` reported the sidecar playing; English cues in 9 of 10 shots (744–767 s). German: content carried German, Arabic, Danish, and English; one write at 3.35 s; German cue in 1 of 6 shots. Arabic on A: one write at 3.39 s. No `accepted`, `left as it is`, or `finished right after` line. The panel closed on the first Back after all 16 picks (11 switches, two subtitle restores, two audio picks, the English pick). |
| T6 logging hygiene | 2026-10-23 | 55R625 / 15.3.4 | TV | the run's console (2,177 lines, 72 of them replayed history) | grep for `://`, `token`, `st=`, `Authorization` | PASS | No `token`, `st=`, or `Authorization` anywhere (case-insensitive). After the install, `://` appears only in the existing debug `api: start` lines (439). No player, subtitle, media, or playback line contains `://`; the new lines (`kept the content on its proxy node`, `subtitle reused from this session`, `the content waits for its subtitle`) carry no fields beyond format and selection; other values are listed names, `tmp:/` paths, and `mkv/N`. The replayed history holds three Roku OS texture warnings (`sdkl [sg.scene.bitmap.big]`, from before the install) that print artwork URLs in full: Roku's own logging, kept private. |
| T7 stability | 2026-10-23 | 55R625 / 15.3.4 | TV | A (each Detail checked to be A's before Resume, after the fix below) | 10 × Home → Continue Watching → Detail → Resume 20 s → Back → Back | FAIL | Two tries after relaunches: the first stopped at cycle 1 (BrightScript error when the conversion was kept), the second after cycle 3 (BrightScript error on the player's release after Back). Cycles 1–3 each played 20 s and closed on the first Back. Home: 29.9 / 12.9 MB and 1,187 nodes after a fresh launch; 38.7 / 17.8 MB, 1,197 after cycle 1; 41.2 / 19.7 MB, 1,197 after cycle 2. Before these, the script's Detail check passed whatever it read (the pipeline returned `tee`'s status), so its first try played file B twice; fixed and checked (B refused, A accepted) before the later tries. |

### Defects found in run 25

1. **Client (AG-220): the sidecar cache crashes the app.** `playback.sidecarCache.exists` creates `roFileSystem` on
   the render thread; Roku refuses it there, intermittently, and the next call fails:
   `BRIGHTSCRIPT: ERROR: roFilesystem: creating MAIN|TASK-only component failed on RENDER thread:
   pkg:/source/playback/sidecarCache.brs(135)`, then `'Dot' Operator attempted with invalid BrightScript Component or
   interface reference. (runtime error &hec)` at `return CreateObject("roFileSystem").Exists(path)`. Four times in five
   app sessions, each followed by `EXIT_BRIGHTSCRIPT_CRASH` at the next launch: twice when a session's first conversion
   was kept (`onMediaResult` → `cacheSidecar` → `trimCache` → `evict` → `exists`; the player froze on "Loading
   subtitles…" before its first frame), twice on the player's release after Back (`onVideoState` → `closeWhenStopped`
   → `nav_pop` → `onRelease` → `trimCache` → `evict` → `exists`; the screen went black). The same call ran without error
   in the install's session (a keep, two reuses, three closes) and for about 24 minutes in another session before failing.
   The debug build stops in the Micro Debugger; a release build would exit to Roku Home (expected, not observed). The
   Task threads (`MediaTask`, `ApiTask`) create `roFileSystem` themselves.

Observations for review, not counted as defects: (1) reused starts took 8.3–9.5 s from the plan to the first frame,
not AG-220's 7–8 s: content is assigned 1.3 s after the plan while the unselected sidecars get their 1 s, and Roku took
8.0–8.1 s from content to first frame. (2) After the first crash's relaunch, file A's first Detail showed only "Play"
with no episode list for 45 s (two catalog requests done, the third logged only when Back cancelled it); reopening
worked and it did not recur. (3) B's copy remux again logged `the load started past its start; seeking back` and `the
seek back did not land` at each of its four remux starts. (4) Each switch kept in place named another node than the
newest plan's; both reloads came back on the content's own node (`sameorigin` true).

## Run 26 — tvOS layout parity (AG-222 to AG-285) and the run 25 sidecar-cache fix (AG-236)

Twenty-sixth hardware pass on the same TV: screenshots of the rebuilt UI against the tvOS reference and spec section
5, the device check of AG-236 on run 22's file A, the detail page's version, audio, and subtitle hand-off (AG-223 to
AG-231) on file B, a regression smoke of runs 22–25, performance, and stability. Like runs 22–25, this run used the
non-lab Silo development server at the server owner's request, as already signed in, with plans routed through proxy
nodes; the console and ECP are the only sources.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `c3d474f`, installed at the start and left installed; no temporary build.
- **Start state:** the dev app in the foreground (allowed by A-10) after the A-10 check (nothing playing, the HDMI 1
  device idle, two minutes of ECP polling without change); the dev app signed in, opening its remembered profile
  without a picker. Roku's caption mode was On; subtitle Off wrote Off, choosing a track wrote On again, and
  `device-info` read On at the end. Ended on Roku Home with nothing playing, still signed in (every session line
  after the install reads `signed_in`, through two launches) on the profile found.
- **Server:** no sign-in, sign-out, server switch, API call, or setting change. The Sign Out confirmation was opened
  once and cancelled with Back; Switch Profile opened the picker and the current profile was chosen again. The plays
  changed the watch state of the two episodes only. File B's detail-page audio and subtitle preferences were changed
  for T3 and put back (English audio, Auto subtitles), checked on a freshly opened page; file A's were not changed.
  A harness fault (T6) restarted file A from its beginning once; it was seeked back near its earlier position.
- **Sources:** the dev console (local time; the old build's exit during the install is left out), ECP
  `query/media-player` every 0.5 s, ECP key accept times, `query/chanperf`, `query/sgnodes/all?count_only=true`, and
  `query/graphics-frame-rate` every 0.25 s while scrolling, and screenshots. Positions are media seconds.
- **Files:** A and B as in run 22. Neither has sprite sheets; each has one version.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 layout parity (AG-222 to AG-285) | 2026-10-24 | 55R625 / 15.3.4 | TV | the server's library: Home, a movie and a series library, Search, a 4K movie with three versions, two anime series, a live-action series; player on A | FHD screenshots of every screen and state in the brief; compared with the tvOS reference images and the parity audit's numbers | FAIL | Positions match spec section 5 within a few pixels on Home (band 596, cards 674, lift 432×240 and 201×302), the top bar, menus, library list, Browse, sort menu, Search, both detail pages, the track menus, and the player (scrubber y 820, buttons 906–972, Options panel 410–1510 × 152–532). Not recorded in 5.9 and visible: (1) Roku's caption plane draws subtitles across the shown controls (scrubber and time row); (2) the Quality dialog sits over the Options tab row and the dimmed tabs read through behind its title, with no check on the focused checked row; (3) Options Info cuts the overview's last line through the glyphs at the panel's edge (5.9 says it stops at the lines left), and the Subtitles and Quality lists end on a half row; (4) on a detail page a long Subtitles menu pins to the screen's foot over its own button and the readout, which read through the panel; (5) a lifted card shows a 1–2 px white line down its right edge past the rounded corners and a short tick under its bottom-left corner; (6) after choosing Auto in Subtitles the readout names the track just left until the page is reopened; (7) the AUDIO readout shows Auto for a moment before the remembered track. Recorded deviations seen: the black page behind the hero, no card overlays, no Cast & Crew/trailer/Watchlist/More, the text rating and scores, menus without blur, the DynamicKeyboard Search, square scrubber with no previews, boxes for a CJK title, the Sort pill above the grid. Not reached: Up Next (would reach A's credits marker and risk playing the next episode), skip pills, PIN, notices |
| T2 sidecar cache off the render thread (AG-236) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original, the profile's subtitle (the built-in full English ASS) | caption mode On; Resume from Detail, Back, Resume, Back in the install's session; `key Home`, ECP launch, Resume, Back | PASS | Start 1: the ASS converted (329 cues, 8,345 dropped, 373 merged, 10,736,314 bytes) and was kept; first frame 14.4 s after the key; Back closed the player to Detail. Start 2: `subtitle reused from this session {"format":"ass","selected":true}` 0.6 s after the key, no conversion; first frame 11.0 s. Start 3 (new session, `lastExitOrTerminationReason` `EXIT_USER_NAV`): converted and kept again; first frame 14.9 s. Whole post-install console (2,400 lines, 21 starts and 21 stops, the player released after each): `MAIN\|TASK-only`, `BRIGHTSCRIPT: ERROR`, `Backtrace`, `runtime error`, `Micro Debugger`, `EXIT_BRIGHTSCRIPT_CRASH`, and `sidecarCache` 0; every exit `EXIT_USER_NAV` |
| T3 detail selections reach the start (AG-223 to AG-231) | 2026-10-24 | 55R625 / 15.3.4 | TV | B, original (Japanese) | caption mode On; on Detail: Audio Tracks → Japanese, Subtitles → the English external SRT; Resume; then English and Auto again | PASS | Each pick wrote its preference at once (`PUT` audio-prefs and subtitle-prefs, 204); the readout read Japanese · FLAC · Stereo and English · SRT. The plan was the Japanese original (`audio_codec` `flac`); the English SRT sidecar was downloaded and selected before the first frame (10.4 s after the key) and played after one corrective write; Options Audio showed Japanese checked. The start body is not logged by this build (the API log names method and URL only), so its `audio_track_index` and `subtitle_track_index` fields were not seen; no version was chosen (one version). Restored with `PUT` (English) and `DELETE` (Auto), 204 each; a reopened page and both menus read as found. Roku's Video node and ECP report AAC audio on the FLAC plan, as in run 25 |
| T4 regression: in-place switch on a proxy plan, a non-English pick after a reload, Options Back (runs 22–25) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original | caption mode On; Options Subtitles: the English ASS → Off → Arabic → the English ASS; Quality picker open, then Back twice | PASS | Off ran in place: one `kept the content on its proxy node`, `subtitleTrack` written empty, no plan line, no new content. Arabic (not carried) reloaded the plan; after the first frame one corrective `subtitleTrack` write at settle and the Arabic sidecar playing 3.5 s later. Back closed the Quality picker at the first press and the panel at the next; every Options exit in the run took one Back |
| T5 performance | 2026-10-24 | 55R625 / 15.3.4 | TV | Home rows; A's and a never-opened series' Detail; A's player | screenshots at set offsets after the key; 19 Rights at 0.33 s on a 20+ poster row with `graphics-frame-rate` at 0.25 s; `chanperf` | PASS | Detail, revisited: fully drawn in every shot taken 0.3–1.5 s after the key (≲0.9 s). Detail, first visit: catalog reads done 0.75 s after the key; text, logo, and placeholders in the first shot, fully drawn by the shot requested 1.74 s after the key (≤≈2.1 s); A's first visit of the session read for 1.39 s. Row scroll: median 53.5 fps (min 36.9, max 59.4, 24 samples), no visible stall, every card's art loaded. Memory used/anon: Home 41.0 / 19.6 MB (1,203 nodes), Detail 42.3–44.7 / 20.4–23.4 MB (816–818), player 97.2–103.8 / 18.0–22.0 MB (921–923) |
| T6 stability | 2026-10-24 | 55R625 / 15.3.4 | TV | A (each Detail checked to be A's) | 10 × Home → Continue Watching → Detail → Resume 20 s → Back → Back | PASS | 10 of 10 cycles; every Back closed the player at the first press; Resume to the first ECP `play` 9.2–11.0 s. Home before 42.6 / 22.2 MB and 1,214 nodes, after 41.0 / 20.4 MB and 1,214 nodes (used −3.8%, nodes unchanged); 39.5–42.5 MB and 1,214 nodes after every cycle. No BrightScript error or backtrace. A first attempt stopped after cycle 5: the relay lost ECP for 45 s, two Back presses failed, and the harness's next keys landed on Detail and the player (see the fault below); its four complete cycles read 38.8–43.5 MB and 1,213–1,214 nodes |

### Defects found in run 26

1. **Client: subtitles over the player's controls.** Roku draws the caption plane at its own place, so with the
   controls shown a two-line cue covered the scrubber and the time row. tvOS raises subtitles above its controls;
   spec 5.9 records no deviation.
2. **Client: the Quality picker over the Options tabs.** The 620 px dialog (y 60–690) covers the tab row, and the
   dimmed tabs show through behind its "Quality" title; the focused row that is the current choice shows no check.
3. **Client: clipped text at the Options panel's edge.** Info's overview shows half of its fourth line at the panel's
   bottom edge; the Subtitles track list and the Quality list end on a half row.
4. **Client: a long detail track menu covers its button.** With seven or more rows the Subtitles menu pins to the
   screen's foot (y 466–1032), over the focused Subtitles button and the readout, which read through the panel.
5. **Client: a line at a lifted card's edge.** Focused posters and landscape cards show a 1–2 px white line down the
   right edge, past the rounded corners, and a short tick under the bottom-left corner.
6. **Client: a stale readout after Auto.** Choosing Auto in Subtitles after an explicit track left the readout naming
   that track ("Auto · English · SRT") until the page was opened again ("Auto · English · ASS").

Observations for review, not counted as defects: (1) the AUDIO readout shows "Auto · …" for a moment on each visit
before the remembered track replaces it, shifting the slots; (2) Search's segmented control changes its filter on OK,
not on focus, and a library tab loses its selected look while focus is in its own library list (tvOS's behaviour
not confirmed); (3) without sprite sheets the hold indicator shows only its chip, with no "Previews aren't available"
line; (4) Roku reports AAC audio on file B's FLAC original plan (also run 25).

Harness fault (not the client): during the first stability attempt the relay could not reach ECP for 45 s, so two
Back presses were refused and the player closed to Detail late; the script then pressed keys without checking the
screen, starting file A once from its resume point and once from Start Over. File A was seeked back near its earlier
position before stopping. The script now stops on any refused key, any ECP error, or a screen that is not Home before
a cycle; the second attempt ran clean.

## Run 27 — W12 fixes (AG-286 to AG-291), run 26 player fixes (AG-293 to AG-296), run 26 UI fixes (AG-297 to AG-302)

Twenty-seventh hardware pass on the same TV: captions while the player controls show, the player's Options panes,
the rebuilt hero wash, card edges, detail readout, meta line, and track menus against run 26 and the tvOS reference,
the W12 preference-write fixes, Up Next, a regression smoke of runs 22–26, and stability. Like runs 22–26, this run
used the non-lab Silo development server at the server owner's request, as already signed in, with plans routed
through proxy nodes; the console and ECP are the only sources.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `72ab4c1`, installed at the start and left installed; no temporary build.
- **Start state:** the dev app in the foreground (allowed by A-10) after the A-10 check (nothing playing, the HDMI 1
  device idle, two minutes of ECP polling without change); the dev app signed in, opening its remembered profile
  without a picker. Roku's caption mode was On; the player's subtitle Off wrote Off, the next track On again, and
  `device-info` read On at the end. Ended on Roku Home with nothing playing, still signed in (every session line
  after the install reads `signed_in`, through two launches) on the profile found.
- **Server:** no sign-in, sign-out, server switch, API call, or setting change. The plays changed the watch state of
  file A only (file B was not played). Detail-page audio and subtitle preferences of both files were changed for T2
  and T4 and put back as found (English audio, Auto subtitles), checked on freshly opened pages.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, ECP key accept times,
  `query/chanperf`, `query/sgnodes/all?count_only=true`, and screenshots. Positions are media seconds.
- **Files:** A and B as in run 22. Neither has sprite sheets; each has one version.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 captions under the controls (AG-293) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original; the German SDH external SRT chosen on Detail, then the English SDH external SRT chosen in Options | caption mode On; 6 × show the controls (Up) and hide them (auto-hide or Back), with a pause and resume; then 4 × on English | PASS | No cue in any shot with the controls shown, paused or playing; a cue in the chosen language in the first shot after Back (requested at once after the key) and after auto-hide, German text on German and English text on English, the sidecar reported playing. Console during the cycles: only `player: focus` "controls shown" / "controls hidden" pairs and the 10 s progress posts; no `subtitleTrack` write, plan, stop, `finished`, reload, or recovery line; ECP play, pause, play only. With Options open the cue still shows (by design) |
| T2 player Options and the start body (AG-294 to AG-296) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original | Options: Video → Quality picker, Info, Subtitles (11 tracks); dev-build start-body log after choosing a version and tracks on Detail | PASS | The Quality picker sits inside the panel under the tab row (tabs readable), four whole rows, scrolling by a row; Info's overview stops at three whole lines, the last ellipsized; the Subtitles list shows whole rows only and scrolls by one row. With the version pinned and German chosen: `start body {"absent":"","present":"allow_alternate_versions,audio_track_index,…,file_id,…,subtitle_track_index"}`; on a fresh page (version Auto, subtitles Auto) `absent` lists `allow_alternate_versions` and `subtitle_track_index`. Observations: no Quality row is checked while the Quality row reads Auto (AG-294's possible cause not confirmed); the player's subtitle list holds a Spanish track the detail menu does not, in another order |
| T3 hero wash, card edges, readout, meta line, track menus (AG-297 to AG-302) | 2026-10-24 | 55R625 / 15.3.4 | TV | the server's library: Home rows, a movie library's Browse grid, a 4K movie's and two episodes' Detail, A's episode rail | FHD screenshots, pixel means and 5–8× crops against run 26 and the tvOS reference images | FAIL | The hero wash shows on every title (RGB ≈20–24 at the top left where run 26 was 0, fading to 0 by y 640 on Home and y 700 on Detail, cards on black) and cross-fades with the backdrop. A lifted row poster (run 26's light poster), a grid poster, and an episode still have clean rounded corners and no edge line. The readout flows inline and follows a version pin, a track, and Auto at once ("Auto · English · ASS" 0.2 s after the key; a reopened page agrees); the meta line leads with the rating chip. Long Subtitles menus (movie and series) open above the readout with five whole rows and scroll, the button and readout visible. Not fixed: the 1 px white tick under the bottom-left corner of the lifted first card of Continue Watching, as in run 26 (cards in other positions are clean). Recorded deviations seen: the wash ends in black above the cards, the chip first (tvOS's code), menus without blur, no card overlays or Cast & Crew |
| T4 preference writes (AG-286 to AG-288) | 2026-10-24 | 55R625 / 15.3.4 | TV | B (Detail only) | Audio Tracks → Japanese → Auto → Back within 3 s; reopen; subtitles Off, Off again, Auto; A's remembered English chosen again | PASS | `PUT audio-prefs` (204) then `DELETE` (204) in that order, the page's re-read cancelled by Back; the reopened page reads Auto (Auto's resolved track marked beside it, by design). Off wrote one `PUT subtitle-prefs`; Off again and the unchanged English sent nothing; Auto one `DELETE`. The server answered in about 0.1 s, so a slow-server race was not reproduced. Both files' preferences restored and checked |
| T5 Up Next | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original, about 210 s before its credits marker | the controls' Up Next button; Back | PASS | The panel opened without a countdown: the next episode's title and overview, Play Now (focused), Keep Watching, Back, "Auto-play is On", the video in its box. Back closed the player; nothing else started. The countdown (crossing the credits) was not tried, to avoid marking A played |
| T6 regression: in-place switch on a proxy plan, a non-English pick after a reload, the sidecar-cache crash path (runs 22–26) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original | caption mode On; Options Subtitles → Off → French; Resume, Back, Resume, `key Home` and ECP launch, Resume | PASS | Off ran in place: `kept the content on its proxy node`, one empty `subtitleTrack` write, no plan, ECP `play` throughout. French reloaded the plan; one corrective write at settle and French playing 3.6 s later. Crash path: the embedded ASS converted (329 cues), then `subtitle reused from this session {"format":"ass","selected":true}`, then converted again after the relaunch (`EXIT_USER_NAV`); T7's ten starts reused it. Whole post-install console: `MAIN\|TASK-only`, `BRIGHTSCRIPT: ERROR`, `Backtrace`, `runtime error`, `Micro Debugger`, `EXIT_BRIGHTSCRIPT_CRASH`, and `sidecarCache` 0 |
| T7 stability | 2026-10-24 | 55R625 / 15.3.4 | TV | A (each Detail checked to be A's) | 10 × Home → Continue Watching → Detail → Resume 20 s → Back → Back; Home measured before, after each cycle, and idle after | FAIL | 10 of 10 cycles; every Back closed the player at the first press; Resume to the first ECP `play` 9.6–11.4 s. Home before 37.3 / 16.8 MB used/anon and 1,203 nodes (taken two minutes after a relaunch), after 41.5 / 20.9 MB and 1,206 nodes (used +11%, outside the 5% bound; nodes +0.25%), idle 42.6 / 21.8 MB, flat over 80 s. After every cycle 38.1–43.0 MB with no trend (cycle 1 41.2, cycle 10 41.5); 1,204–1,206 nodes. No BrightScript error or backtrace |

### Defects found in run 27

1. **Client: a tick under the lifted first card.** The lifted first card of Continue Watching still shows a 1 px white
   mark under its bottom-left corner (run 26 defect 5's second half); AG-297's whole-pixel lift removed the edge line
   but not this, and cards in other positions are clean.
2. **Stability bound: Home memory after ten cycles.** Used memory on Home rose 11% over a baseline taken soon after a
   relaunch; it was flat from the first cycle on (41.2 to 41.5 MB) and node counts moved by 3, so the bound, not a
   trend, failed.

Observations for review, not counted as defects: (1) the player's Quality picker checks no row while its row reads
Auto; (2) the player's subtitle list and the detail menu disagree (a Spanish track only in the player; order; pinning
the version moves the chosen track up the detail menu); (3) a seek committed at the moment the content settled was
followed by Roku's `finished` 0.69 s later and a reload at the position, the player's designed path (it came from a
harness slip, below).

Harness slips (not the client): a stray Fast Forward before Rewind ran a climbing ladder that seeked file A to about
90 s; it was skipped back to its earlier position at once. An Up Next Select landed after the controls had hidden and
only showed them; the next attempt sent the keys together.

## Run 28 — run 27 fixes: whole-pixel lift from the corner (AG-303), the Quality row names the setting (AG-304), the player's subtitle list in the detail order (AG-305)

Twenty-eighth hardware pass on the same TV, a short one: the lifted card edges, the player's Quality row and picker,
the detail and player subtitle lists, stability with a warm-up cycle before the baseline, and a regression smoke of
runs 22–27. Like runs 22–27, this run used the non-lab Silo development server at the server owner's request, as
already signed in, with plans routed through proxy nodes; the console and ECP are the only sources.

- **Device / sink:** 55R625 / 15.3.4, TV speakers. Audio and the video plane could not be observed remotely and are
  not claimed; screenshots show the UI plane and Roku's caption plane.
- **Build:** stock dev build of `1cda0cd`, installed at the start and left installed; no temporary build.
- **Start state:** Roku Home after the A-10 check (nothing playing, the HDMI 1 device idle, two minutes of ECP polling
  without change); the dev app signed in, opening its remembered profile without a picker. Roku's caption mode was On;
  the player's subtitle Off wrote Off, the next track On again, and `device-info` read On at the end. Ended on Roku
  Home with nothing playing, still signed in (every session line after the install reads `signed_in`, through two
  launches) on the profile found.
- **Server:** no sign-in, sign-out, server switch, API call, or setting change; the profile's quality setting was only
  read. The plays changed the watch state of file A only; it was skipped back near its starting position and Home
  shows the remaining time it showed at the start. No detail-page preference was changed. File B was not opened.
- **Sources:** the dev console (local time), ECP `query/media-player` every 0.5 s, ECP key accept times,
  `query/chanperf`, `query/sgnodes/all?count_only=true`, and screenshots. Positions are media seconds.
- **Files:** A and B as in run 22. Neither has sprite sheets; each has one version.

| Test | Date | Device / OS | Sink | File class | Harness settings | Result | Observed facts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 lifted card edges (AG-303) | 2026-10-24 | 55R625 / 15.3.4 | TV | the server's library: Home's first Continue Watching card, two row posters, a movie library's Browse grid (a white-bordered poster and a first-column poster), file A's episode rail (two stills) | FHD screenshots; pixel bands 1–3 px outside each lifted card's four edges and 8× corner crops, against run 27's shot of the first card | PASS | The first Continue Watching card's left edge is clean: column x 43, where run 27 had the white tick (max 240), now reads at most 19, and every band outside its four edges stays at or below 34 (shadow and JPEG). The row posters (202×302 lifted), the grid poster (286×428), and the episode stills (388×216) show clean rounded corners and no line on any edge (bands at or below 45, the highest a blue sky's chroma bleed above one poster); a black-art grid poster shows no outline. The same first card read clean again after the stability cycles |
| T2 the player's Quality row (AG-304) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original | Options → Video while paused; the Quality picker opened, scrolled to its end, and closed with Back (nothing chosen) | PASS | The row reads "Quality 4K", the name AG-304 gives a saved 2160p preference. The picker lists Auto and nine rungs (1080p High 10 Mbps down to 360p 300 kbps), four rows visible, scrolling by one; no row is checked, Auto included, focused or not. Back closed the picker with the row unchanged and no request |
| T3 the detail and player subtitle lists (AG-305) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original, version Auto | the detail Subtitles menu scrolled end to end and closed with Back; Options → Subtitles scrolled end to end | PASS | The detail menu lists Auto, Off, and 10 tracks; the player lists Off and the same 10 tracks in the same order with the same names and detail lines (three English tracks: an external SDH SRT, the embedded signs-and-songs ASS marked Default, and the embedded full ASS; seven external SDH SRTs and a PGS track by language). The player checks the embedded full ASS, the track Auto resolves to. No track is in only one list: the Spanish sidecar run 27 saw only in the player is in the detail menu too (the server's projection now lists it) |
| T4 stability | 2026-10-24 | 55R625 / 15.3.4 | TV | A (each Detail checked to be A's by its logo, meta line, and main button) | one warm-up cycle, then 10 × Home → Continue Watching → Detail → Resume 20 s → Back → Back; Home measured about 10, 16, and 27 s after the Back to Home that ended the warm-up and cycle 10, after every cycle, and idle | FAIL | 11 of 11 cycles; every Back closed the player at the first press; Resume to the first ECP `play` 9.2–11.1 s; every start reused the session's converted subtitle. Baseline after the warm-up 42.4 / 21.8 MB used/anon (mean of three) and 1,206 nodes; final after cycle 10 38.8 / 18.3 MB and 1,206 nodes: nodes unchanged, used −8.3% (outside the ±5% bound, by falling), idle 70 s later 39.0 MB. After every cycle 38.5–43.3 MB with no trend and 1,206 nodes. Detail 40.8 MB / 825 nodes, player 103.6 MB / 930. No BrightScript error or backtrace |
| T5 regression: an in-place switch, a non-English pick after a reload, the sidecar-cache crash path (runs 22–27) | 2026-10-24 | 55R625 / 15.3.4 | TV | A, original | caption mode On; Options Subtitles → Off → French; Resume, Back, Resume, `key Home` and ECP launch, Resume | PASS | Off ran in place: the track-change answer kept the content without a refusal, one empty `subtitleTrack` write, no reload or stop, ECP `play` throughout. French reloaded the plan (`refused` in_place, stream_origin); the content waited for the sidecar, one corrective write at settle, French playing 3.0 s later. Crash path: the embedded ASS converted (329 cues), then `subtitle reused from this session {"format":"ass","selected":true}` 0.5 s after the key, then converted again after the relaunch (`EXIT_USER_NAV`); T4's 11 starts reused it. Whole post-install console: `MAIN\|TASK-only`, `BRIGHTSCRIPT: ERROR`, `Backtrace`, `runtime error`, `Micro Debugger`, `EXIT_BRIGHTSCRIPT_CRASH`, `sidecarCache`, and `[ERROR]` 0 |

### Defects found in run 28

No client defect. **Stability bound:** Home's used memory after ten cycles was 8.3% below the post-warm-up baseline,
outside the ±5% bound in the falling direction; node counts did not move and single readings vary by about ±6%
between cycles with no trend, so the bound sits inside the reading noise (run 27 missed it by rising after a baseline
taken soon after a relaunch).

Observations for review, not counted as defects: (1) the in-place Off was adopted without the `kept the content on its
proxy node` line run 27 logged, because this time the track-change plan kept the content outright; (2) after the app
exited, Roku Home played its own 15 s preview clip (ECP `native-ui`) and then stopped; the app was not involved.

Harness slip (not the client): during the closing skip-back on file A, a Back sent after the −10 s skips only hid the
controls the skips had shown, so file A played 16 s longer before the second Back stopped it.
