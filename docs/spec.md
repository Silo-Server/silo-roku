# Silo Roku client specification

**Status:** Draft for product and feasibility review

**Last updated:** 2026-08-25

**Owner:** Silo Roku client

**Target:** Native Roku SceneGraph application using BrightScript

## 1. Decision summary

Silo Roku will be a native SceneGraph/BrightScript client using Silo's native
`/api/v1` API and playback protocol v3. It will not reuse the SwiftUI, Kotlin,
React Native, or jellycompat client implementations. Cross-client consistency
will come from the shared server contract, product behavior, conformance
fixtures, and coordinated design—not shared UI code.

The first implementation should prove the riskiest platform boundaries before
building the full browse experience:

1. Public-store feasibility for a self-hosted authenticated media client.
2. On-device login to a user-supplied Silo server.
3. Protocol-v3 playback through Roku's `Video` node, including runtime replan.
4. Side-loaded subtitles, audio-track selection, and authenticated media URLs.
5. Acceptable performance on a currently supported 512 MB Roku device.

Until those gates pass, the repository remains a private prototype and no
public release date is implied.

## 2. Product principles

- **Playback correctness first.** A smaller client that reliably starts,
  seeks, resumes, changes tracks, reports progress, and recovers is preferable
  to a broad client with fragile playback.
- **Server-owned decisions.** The Roku reports facts about itself; the Silo
  server selects direct play, remux, or transcode and publishes the quality
  menu.
- **A real ten-foot interface.** Every screen is operable using directional,
  OK, Back, Replay, and Options input with visible, deterministic focus.
- **Conservative capability claims.** An unknown decoder, audio sink, subtitle
  path, or HDR mode is unsupported until it is verified on hardware.
- **Small-device discipline.** Retain only visible and near-visible artwork and
  content nodes; recover deliberately from Roku low-memory events.
- **No Roku-only product loopholes.** Silo's access policy, profile model, and
  permanent non-goals apply unchanged.

## 3. Proposed release scope

### 3.1 Feasibility build

The feasibility build is sideloaded and deliberately plain. It must support:

- manual entry of a Silo server URL;
- server health validation and actionable connection errors;
- on-device username/password login;
- account token refresh and logout;
- household profile selection and profile PIN verification;
- one hard-coded or API-loaded playable item;
- protocol-v3 capability, start, progress, stop, and one failure-driven replan;
- direct/progressive playback and HLS playback through a `Video` node;
- a diagnostic overlay containing only non-secret plan and Roku player state.

This build answers platform questions. It is not a UI prototype for release.

### 3.2 First public MVP

The proposed MVP contains:

- one configured Silo server;
- on-device account login;
- household profile selection, child restrictions, and PIN handling;
- Home using server-defined sections;
- Movies and TV library browsing with pagination;
- search across the visible video catalog;
- movie, series, season, and episode details;
- resume/start playback from server watch state;
- direct play, progressive remux, HLS remux, and HLS transcode as planned by
  playback protocol v3;
- play/pause, seek, Replay, transport overlay, quality selection, audio-track
  selection, subtitle selection, and stop;
- periodic and terminal progress reporting;
- favorites and watchlist display and mutation;
- profile switching, sign-out, server replacement, and app-data reset;
- accessibility-aware captions, focus, labeling, and system-setting behavior;
- deep-link launch handling required for Roku certification.

### 3.3 Deferred after MVP

- multiple saved Silo servers;
- music and audiobook browsing/playback;
- calendar, ratings, requests, notifications, and richer recommendations;
- collections beyond read-only rows;
- SiloControl receiver and phone-to-Roku handoff;
- automatic local-network discovery;
- Roku Search catalog feed integration, if a privacy-safe per-install design is
  accepted by Roku;
- hosted diagnostics upload;
- theme catalog integration beyond basic server branding.

### 3.4 Explicitly excluded from the first release

- ebooks, comics, and document reading;
- downloads or offline playback;
- server setup and administration;
- library creation, scanning, metadata editing, or user management;
- Watch Together;
- plugin administration surfaces;
- live TV, OTA/DVB tuners, IPTV, EPG/XMLTV, DVR, `.strm`, or arbitrary remote
  stream playback.

## 4. Roku platform baseline

The first implementation uses:

- one `roSGScreen` and a single root `Scene`;
- SceneGraph XML for visual components and BrightScript for behavior;
- `Task` nodes for API and other blocking work;
- `RowList`, `MarkupGrid`, and small custom components for browse surfaces;
- the SceneGraph `Video` node for VOD playback;
- `roDeviceInfo` capability probes, especially `CanDecodeVideo()` and
  `CanDecodeAudio()`, rather than model lookup tables;
- `roRegistrySection` for the active server, installation ID, last profile,
  and tokens;
- an FHD/HD design with packaged artwork at the resolutions required by Roku;
- Developer Mode sideloading during implementation, followed by a Roku beta
  app before any public submission.

The exact minimum Roku OS version remains a gate decision. It must be selected
from features actually required by the player—not merely from the newest SDK.
The support claim must include every model still targeted by the chosen Roku OS
floor and must be backed by real-device testing.

Official platform references:

- [Roku app structure and languages](https://developer.roku.com/dev/docs/getting-started)
- [SceneGraph](https://developer.roku.com/dev/docs/scenegraph)
- [Video node](https://developer.roku.com/dev/docs/video)
- [Streaming formats and codecs](https://developer.roku.com/dev/docs/media)
- [Device capabilities](https://developer.roku.com/dev/docs/ifdeviceinfo)
- [Manifest](https://developer.roku.com/dev/docs/channel-manifest)
- [Authentication](https://developer.roku.com/dev/docs/authentication)
- [Deep linking](https://developer.roku.com/dev/docs/implementing-deep-linking)
- [Certification criteria](https://developer.roku.com/dev/docs/certification)

## 5. Application architecture

### 5.1 Proposed repository layout

```text
manifest
source/
  main.brs                 app entry point and launch arguments
  api/                     centralized API request and response handling
  auth/                    session, refresh, profile, and registry state
  playback/                v3 DTO mapping, capability probe, plan execution
  storage/                 typed registry access
  util/                    bounded shared helpers
components/
  AppScene.xml/.brs        root state machine and navigation stack
  screens/                 setup, login, profiles, home, browse, detail
  player/                  Video node wrapper and playback chrome
  tasks/                   network and decoding Task nodes
  views/                   reusable rows, cards, dialogs, empty/error states
images/                    packaged icons and splash artwork
locale/                    localized strings
tests/                     pure logic, contract, and device-flow tests
docs/
  spec.md                  this specification
```

### 5.2 State and navigation

`AppScene` owns a small explicit state machine:

```text
server setup -> account login -> profile selection -> main shell -> detail -> player
```

The scene owns one navigation stack. Each stack entry records its route,
parameters, and focus restoration key. Back removes exactly one entry, except
inside playback where Back first exits overlays and then asks to stop playback.
No screen may infer its previous screen from global flags.

The main shell begins with Home, Movies, TV, and Search. Tabs that cannot be
served by the active profile are absent rather than disabled. Home row order
and membership come from the server's section APIs.

### 5.3 Threading and ownership

- SceneGraph components own rendering and focus only.
- HTTP, JSON parsing of large responses, and other potentially blocking work
  run in `Task` nodes.
- A task publishes an immutable result envelope containing request ID, status,
  headers needed by the caller, decoded body, and normalized error.
- Screens ignore results whose request ID is no longer current. Navigating away
  therefore cancels ownership even if Roku cannot cancel the underlying HTTP
  operation immediately.
- One auth coordinator owns access-token refresh. Concurrent `401` responses
  join the same refresh operation, and each original request is retried at most
  once.
- The player owns the active playback attempt. No browse screen retains or
  mutates a `Video` node.

## 6. Server connection and authentication

### 6.1 Server origin

The client accepts only an `http` or `https` origin. It removes trailing
slashes and rejects paths containing credentials. It validates the origin with
`GET /api/v1/health` before presenting login.

Whether plain HTTP is allowed in the public build is an open product and
certification decision. Supporting self-hosted installations suggests allowing
LAN HTTP, but the UI must make the transport state clear and must never silently
downgrade an HTTPS URL. Self-signed/private-CA HTTPS behavior must be tested on
real Roku hardware; the client will not ship a bypass for certificate
validation.

### 6.2 Account login

The public MVP uses on-device credential entry:

1. `GET /api/v1/auth/providers` determines available login modes.
2. Local login posts the on-screen username/password to
   `POST /api/v1/auth/login`.
3. Access and refresh tokens are written to an app-specific registry section
   only after login succeeds.
4. `GET /api/v1/auth/me` validates a restored session.
5. `POST /api/v1/auth/refresh` rotates both tokens through the centralized
   single-flight coordinator.
6. Logout calls `POST /api/v1/auth/logout` when reachable and then clears all
   local credentials regardless of the network result.

Silo's QR/device-code login is appropriate for other TV platforms but cannot
be assumed here: Roku's current public certification rules say that non-TVE
apps must complete authentication on-device and prohibit off-device activation.
The existing `/api/v1/auth/device/*` flow may be retained only in development
or beta builds until Roku approves a compliant use.

The Roku registry is treated as app-scoped persistence, not as a general secret
manager. Tokens must never appear in logs, error dialogs, crash breadcrumbs,
analytics, or copied diagnostic payloads.

### 6.3 Profiles

After account login the client loads `GET /api/v1/profiles/`. It remembers the
last adult profile for ordinary launches but still validates that the profile
exists and remains permitted. It does not silently default to a child profile.

PIN-locked profiles use `POST /api/v1/profiles/{id}/verify-pin`. Subsequent API
calls attach:

- `Authorization: Bearer <access token>`;
- `X-Profile-Id: <active profile>`;
- `X-Profile-Token: <verified PIN token>` when one is required;
- `X-Silo-Device-Id: <random per-install ID>`;
- `X-Silo-Device-Name` and `X-Silo-Device-Platform: roku` where supported.

The installation ID is generated once and stored in the registry. A Roku
hardware serial number or advertising ID is not used as Silo's device identity.

## 7. Catalog and browse behavior

The MVP consumes these existing native API surfaces:

- `GET /api/v1/home/sections` and
  `GET /api/v1/home/sections/{id}/items`;
- `GET /api/v1/catalog` for paginated browse and search;
- `GET /api/v1/catalog/items/{id}` for item detail;
- series/season/episode resources under `/api/v1/catalog/series/...`;
- `GET /api/v1/watch/{id}` for the playable detail projection;
- the profile-scoped favorites, watchlist, watched, history, and progress
  endpoints used by the other first-party clients.

The client never loads an entire large library to sort or filter locally.
Pagination, access filtering, section composition, and search stay server-side.
Rows retain a bounded window around visible content, and image requests use
server-provided image resources sized for their presentation.

Every primary surface defines loading, empty, recoverable error, authorization
error, and stale-session states. A failed row does not blank the entire home
screen; it renders an inline retry while other rows remain usable.

## 8. Playback protocol v3

The normative playback contract remains in the
[Silo server repository](https://github.com/Silo-Server/silo-server/blob/main/docs/architecture/playback-protocol-v3.md).
This document defines only the Roku execution mapping.

### 8.1 Capability discovery

Before the first playback attempt, and again when Roku reports a relevant codec
or output change, the client builds a conservative device context from
`roDeviceInfo`:

- video codecs are included only after `CanDecodeVideo()` succeeds for the
  relevant profile/level/resolution combination;
- audio formats are included only after `CanDecodeAudio()` confirms the path;
- HDR is advertised only when both decoder and connected display evidence
  agree;
- AAC stereo is the baseline audio path;
- passthrough claims are initially empty until receiver-change behavior is
  proven;
- the supported resolution is the lesser of decode and current-output limits;
- `original_http`, `progressive`, and `hls` are advertised independently;
- unsupported subtitle features remain false rather than being inferred from a
  related Roku capability.

Initial codec probes should cover H.264, HEVC, VP9, AAC, AC-3, and E-AC-3.
AV1, Dolby Vision, HDR10+, HLG, DTS variants, and lossless audio are later
capability increments backed by fixtures and hardware evidence.

### 8.2 Start and plan execution

1. Confirm `GET /api/v1/playback/capability` advertises protocol v3.
2. Send `POST /api/v1/playback/start` with `protocol_version: 3`, the active
   profile, source selection, resume position, device evidence, delivery
   capabilities, and a fresh playback-attempt ID.
3. Treat `playback_plan`, `plan_id`, `plan_attempt_key`, stream URL, track
   inventory, subtitle artifact, and quality entries as opaque server output.
4. Construct one `ContentNode` for the plan and assign it to the `Video` node.
5. Set the explicit stream format from the plan delivery/container; never infer
   it from a URL suffix because Silo media URLs need not have one.
6. Use Roku's system CA bundle for HTTPS. In the default signed-URL mode, do
   not attach the account bearer token to the media request: a plan may send
   signed media to a proxy or transcode-node origin, and forwarding account
   credentials there would cross an unnegotiated trust boundary. Signed stream
   URLs remain opaque and are replayed byte-for-byte.
7. Observe player state, buffering, position, duration, selected tracks, and
   error details and translate them to Silo route events.

The first implementation does not advertise
`header_authenticated_media_v1` or `authorized_media_origins_v1`. It uses the
default signed-URL mode so playback sessions remain reconstructible across API
restarts. Those features may be added only after manifest, segment, subtitle,
token-refresh, replica, and proxy behavior is validated together.

### 8.3 Progress and lifecycle

While playing, the client posts progress to
`POST /api/v1/playback/{session_id}/progress` at a bounded cadence, initially
every 10 seconds, and immediately after meaningful seeks and pause transitions.
It sends a final best-effort progress update before
`DELETE /api/v1/playback/{session_id}` when playback ends or the user exits.

The client deduplicates progress by attempt/session and never lets a late event
from an old `Video` node update the new session. Network outages retain only the
latest unsent position. Recovery sends that latest observation rather than
replaying a queue of obsolete positions.

### 8.4 Failure and replan

Player failures are classified into the protocol-v3 failure vocabulary and
reported through route events and `POST /api/v1/playback/{session_id}/replan`.
For each failed plan the client:

1. echoes the exact `plan_id` and `plan_attempt_key`;
2. appends the unchanged key to `attempted_plan_keys`;
3. reports only bounded, allowlisted diagnostics;
4. executes the returned plan from a clean `Video` node state;
5. stops when the server returns a terminal result or the protocol's bounded
   attempt limit is reached.

The Roku client never constructs a transcode request, guesses a fallback URL,
or repeats a failed plan without telling the server.

### 8.5 Quality and track changes

- The quality menu displays `playback_plan.available_qualities` exactly as
  published and sends the selected label in a `quality_change` replan.
- Audio selection sends the server track identity in a `track_change` replan.
  The first release does not claim client-side original-file audio selection;
  the server may choose a remux that makes selection deterministic.
- Subtitle selection sends the inventory's `track_id` or `combined_index` in a
  `track_change` replan. The client never derives combined subtitle ordinals.
- A newly returned plan replaces the entire previous track and subtitle state.

### 8.6 Subtitles

Roku supports embedded and side-loaded caption paths, but Silo's exact
WebVTT/authorization/timeline combination must pass the feasibility matrix.
The spike must verify side-loaded WebVTT for direct, progressive, remux-HLS,
and transcode-HLS playback; authenticated subtitle download; seeking; resume
offsets; Unicode; position; and Roku caption-mode changes.

In signed-URL mode the media URL may use a different trusted execution origin,
while subtitle artifacts remain authenticated API resources. The client must
not solve that mismatch by applying its bearer header to every `Video` request.
The preferred spike downloads the chosen subtitle through the centralized API
client into bounded `tmp:/` storage, then supplies the local sidecar to Roku's
caption metadata. If Roku cannot render that path reliably, the alternatives
are a server-issued signed subtitle artifact or carefully scoped
header-authenticated playback; either alternative requires a coordinated server
contract decision before implementation.

Until that proof exists, the Roku capability declaration is conservative:

- `sidecar_text`: false in production capability reports;
- `ass_styling`: false;
- `embedded_bitmap` and `sidecar_bitmap`: false;
- `font_attachments`: false.

If the WebVTT matrix passes, `sidecar_text` becomes true for the validated
delivery classes. ASS/SSA and bitmap subtitles continue to request server
conversion or burn-in as protocol v3 plans. The client respects Roku's global
caption mode and accessibility settings instead of creating a second competing
caption preference.

## 9. Focus, input, and accessibility

- Every interactive element has a visible focused state with sufficient
  contrast and a stable focus target.
- Directional navigation is explicit where geometry is ambiguous; focus must
  not jump between rows because artwork finished loading.
- Back closes the topmost overlay, returns to the previous screen, or exits the
  app from its root—never all three.
- Replay performs the Roku-standard replay action during playback and must not
  conflict with Silo seek controls.
- The Options button integrates with Roku's player and caption behavior where
  required rather than shadowing system UI accidentally.
- Labels, descriptions, caption state, audio-description state, and focus order
  follow Roku accessibility and global-setting requirements.
- Animations are short, bounded, and nonessential. Loading indicators never
  trap focus.

## 10. Deep links and certification

Public Roku apps containing video must handle deep links. `Main(args)` and
in-app input-launch events will accept `contentId` and `mediaType`, validate
them, and either:

- resume/play a movie or episode directly using the last eligible adult
  profile;
- open the required series/season detail behavior;
- defer the requested destination through on-device authentication; or
- fall back to Home when the request is invalid or inaccessible.

No child profile is selected implicitly for a deep link. Content IDs are opaque
Silo identifiers and must not embed a server origin, access token, profile ID,
or title metadata.

Milestone 0 must obtain a written or dashboard-backed answer to these public
distribution questions:

1. Is on-device username/password against a user-supplied self-hosted server
   sufficient for the current authentication criteria?
2. What deep-link and Direct-to-Play evidence is required when each installation
   has a different private catalog and no global Roku Search feed?
3. May the public app connect to LAN HTTP origins, and what disclosure is
   required?
4. Which content-rating, accessibility, privacy, and test-account materials are
   required for certification of a self-hosted client?

The release gate includes Roku Static Analysis, App Behavior Analysis where
applicable, deep-link tests, store artwork, privacy disclosures, and testing on
multiple current/updatable devices with materially different memory and
playback capabilities.

## 11. Security and privacy

- Accept API and media URLs only from the configured Silo server and opaque
  server-issued playback plans. Never add a general URL player.
- Reject URL schemes other than HTTP and HTTPS.
- Never follow an HTTPS-to-HTTP downgrade as an automatic recovery action.
- Do not log or display credentials, tokens, PINs, signed query strings, or
  complete authenticated response bodies.
- Clear tokens, profile state, cached personal metadata, and installation-scoped
  settings on app-data reset. Logout clears credentials even when the server is
  offline.
- Do not use the Roku serial number, advertising identifier, or household
  account identity as Silo's installation ID.
- Do not add analytics, crash reporting, advertising, or third-party tracking
  SDKs without a separate privacy and dependency review.
- Images and metadata remain bounded in memory and are dropped on account,
  profile, or server changes so one identity cannot see another's cache.

## 12. Testing and release evidence

### 12.1 Automated tests

- URL normalization and resolution;
- JSON model decoding with missing, null, extra, and malformed fields;
- auth refresh single-flight and one-retry limit;
- profile/PIN header composition;
- navigation-stack and focus-restoration reducers;
- playback-v3 request serialization and response fixtures;
- exact preservation of plan IDs, attempt keys, track IDs, and URLs;
- error-to-replan classification;
- progress deduplication and old-session event rejection;
- deep-link parsing and authenticated deferral;
- secret redaction.

Playback JSON fixtures should be versioned from the normative server contract
with their source revision recorded. Do not hand-simplify fixtures until they
no longer exercise the real wire shape.

### 12.2 Real-device matrix

At minimum, validation needs:

- a currently supported 512 MB non-4K device;
- a mainstream 4K/HDR streaming player;
- a Roku TV or a materially different audio/output path;
- current Roku OS and the selected minimum supported Roku OS where obtainable.

Each device runs:

- cold/warm launch, logout, token expiry, profile PIN, and server replacement;
- long Home rows, large grids, fast directional navigation, and image failures;
- H.264/AAC direct play;
- HEVC and VP9 eligibility where supported;
- progressive remux and HLS remux/transcode;
- AC-3/E-AC-3 fallback and output-route changes;
- seek, pause/resume, Replay, long playback, and API restart during playback;
- quality, audio, subtitle, and forced burn-in replan;
- Unicode metadata and subtitles;
- low-memory notification and app resume;
- valid, invalid, inaccessible, and unauthenticated deep links.

Tests wait on player or API state and never use a fixed sleep as their success
condition.

## 13. Milestones and exit criteria

### Milestone 0 — policy and playback feasibility

- Certification questions have authoritative answers.
- On-device login works against a real Silo server.
- Capability probe, direct play, HLS transcode, progress, stop, and one replan
  work on low-memory and 4K devices.
- Subtitle and authenticated-header results are recorded.
- The team chooses a minimum Roku OS and public/beta distribution posture.

### Milestone 1 — client foundation

- Repository build, package, sideload, lint/static analysis, and test commands
  are reproducible.
- Registry, API client, auth refresh, profiles/PIN, app state, navigation, error
  envelopes, and secret-safe logging are implemented and tested.

### Milestone 2 — browse MVP

- Home, Movies, TV, Search, details, seasons, and episodes operate with bounded
  pagination and deterministic focus.
- Loading, empty, offline, unauthorized, and partial-row failure states are
  usable.

### Milestone 3 — playback MVP

- The protocol-v3 matrix passes on every target device.
- Quality and track replans, progress/resume, server restart, output changes,
  and terminal errors behave predictably.
- Accessibility and captions pass the chosen supported matrix.

### Milestone 4 — beta and public readiness

- Deep links and Direct to Play satisfy Roku requirements.
- Performance, memory, accessibility, privacy, store assets, static analysis,
  and behavior analysis gates pass.
- A Roku beta is exercised by real Silo households before public submission.

## 14. Open decisions

| Decision | Initial leaning | Needed evidence |
| --- | --- | --- |
| Public Store or beta-first | Beta-first | Roku policy answers and household testing |
| Minimum Roku OS | Undecided | Player/subtitle APIs and hardware coverage |
| Plain LAN HTTP | Allow only if certifiable, with warning | Roku policy and device behavior |
| QR/device login | Development only | Roku approval for non-TVE authentication |
| MVP media kinds | Movies and TV | Product priority; audiobook/audio spike later |
| Multiple servers | Defer | Registry/UX cost after single-server reliability |
| Side-loaded WebVTT | Disabled until proven | Full delivery and seek/resume matrix |
| AC-3/E-AC-3 passthrough | Disabled until proven | Codec/output-change hardware tests |
| Dolby Vision and advanced HDR | Defer | Exact Roku probe-to-v3 mapping and fixtures |
| Roku Search feed | Undecided | Privacy-safe private-catalog design and Roku guidance |
| SiloControl receiver | Defer | Foreground networking and discovery feasibility |

## 15. Definition of done for this draft

This draft is ready to become an implementation plan when Milestone 0 has an
owner, target devices, a Roku developer account, and explicit answers for the
distribution, authentication, minimum-OS, LAN transport, and first-release
media-kind decisions above.
