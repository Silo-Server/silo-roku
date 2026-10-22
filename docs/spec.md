# Silo Roku client specification

**Status:** Draft for implementation planning

**Last updated:** 2026-10-09

**Owner:** Silo Roku client

**Target:** Native Roku SceneGraph application using BrightScript

## 1. Decision summary

Silo Roku will be a native SceneGraph/BrightScript client for Silo's native
`/api/v2` API and playback protocol v3. Roku cannot run the Apple, Android,
React Native, or jellycompat client code, so none of it is reused. Consistency
with the other first-party clients comes from three things: the shared server
contract, test fixtures vendored from the server repository, and the design
reference in section 5, which records how the existing Silo TV apps (tvOS and
Android TV) look and behave.

The first release is deliberately small. A viewer signs in, picks a profile,
browses Movies and TV, searches, opens a title, and plays it. Everything else
waits until that path is reliable on low-memory and 4K Roku hardware.

`/api/v1` is a frozen alpha bridge that Silo 1.0 replaces with a `410 Gone`
tombstone. This client never calls `/api/v1` and contains no v1 fallback. A
server that does not serve `/api/v2` gets a "server update required" screen.

The first implementation proves the riskiest platform boundaries before
building the full browse experience:

1. On-device sign-in to a user-supplied Silo server through Roku's voice
   keyboard.
2. Protocol-v3 playback through Roku's `Video` node, with account
   authentication on every media request: file, HLS manifest, HLS segments, and
   subtitles.
3. Side-loaded subtitles and audio-track selection through replan.
4. Acceptable performance on a currently supported 512 MB Roku device.
5. Roku certification of a self-hosted client whose catalog is private to each
   installation.

Until those gates pass, the repository remains a private prototype and no
public release date is implied.

## 2. Product principles

- **Playback correctness first.** A smaller client that reliably starts,
  seeks, resumes, changes tracks, reports progress, and recovers is preferable
  to a broad client with fragile playback.
- **Match the existing TV apps.** Screen structure, navigation, focus, and
  player controls follow the Silo tvOS and Android TV apps. Every Roku
  difference is listed in section 5.9 with its reason.
- **Server-owned decisions.** The Roku reports facts about itself; the Silo
  server selects direct play, remux, or transcode and publishes the quality
  menu. Viewer preferences come from the server's settings store, so a profile
  behaves the same on Roku as on its other devices.
- **A real ten-foot interface.** Every screen is operable using directional,
  OK, Back, Replay, Options, and play/pause input with visible, deterministic
  focus.
- **Conservative capability claims.** An unknown decoder, audio sink, subtitle
  path, or HDR mode is unsupported until it is verified on hardware.
- **Small-device discipline.** Retain only visible and near-visible artwork and
  content nodes; respond deliberately to Roku memory-monitor events.
- **No Roku-only product loopholes.** Silo's access policy, profile model, and
  permanent non-goals apply unchanged.

## 3. Release scope

### 3.1 Feasibility build

The feasibility build is sideloaded and deliberately plain. It must support:

- manual entry of a Silo server URL, checked with `GET /api/v2/system/info`;
- password sign-in through the Roku voice keyboard, token refresh, and logout;
- household profile selection and profile PIN verification;
- one API-loaded playable item;
- protocol-v3 capabilities, start, sequenced progress, stop, and one
  failure-driven replan;
- direct play and HLS playback through a `Video` node with account
  authentication on the manifest, every segment, and the subtitle sidecar;
- a diagnostic overlay containing only non-secret plan and Roku player state.

This build answers platform questions. It is not a UI prototype for release.

### 3.2 First public release

The first public release contains only what a viewer needs to find something
and watch it.

Account and setup:

- one Silo server, entered as a URL;
- on-device password sign-in for local accounts and password-based sign-in
  providers such as LDAP;
- profile picker, profile PIN entry, and child-profile restrictions;
- switch profile, switch server, and sign out.

Browse:

- Home built from the server's home sections, including the Continue Watching
  and Next Up rows the server provides;
- Movies and Series library tabs, each with Recommended rows and a Browse
  grid with sort and an alphabet rail;
- search across movies, series, and episodes;
- movie detail, and series detail with season and episode lists.

Play:

- play, resume, or start over from server watch state;
- direct play, HLS remux, and HLS transcode, as protocol v3 plans them;
- play/pause, skip, the rate ladder, scrubbing, Replay, and stop;
- audio, subtitle, and quality selection through replan;
- skip intro using server markers;
- Up Next at the credits, with autoplay;
- periodic and final progress reporting;
- the profile's server-stored playback preferences (section 8.5).

Platform:

- deep links and Direct to Play as Roku certification requires;
- Roku's caption and accessibility settings respected.

Section 5 describes how each of these looks and behaves.

### 3.3 Deferred until after the first release

- multiple saved Silo servers;
- phone-to-TV pairing, local-network discovery, and the SiloControl receiver;
- favorites, watchlist, and watched toggles; the history screen (server rows
  that contain this data still display on Home);
- collections, people pages and search results, cast, trailers, extras,
  related titles, and version/edition pickers;
- library filters and shuffle;
- requests, calendar, the For You tab, and notifications;
- music and audiobooks;
- settings screens beyond account, profile, and server (preferences come from
  the server);
- profile creation and editing, and home-row editing;
- subtitle search, download, translation, and sync;
- chapters, playback speed, aspect, sleep timer, and audio or subtitle delay;
- seek-preview thumbnails (trickplay);
- hosted diagnostics upload;
- Roku Search feed and Continue Watching integration;
- theme catalog integration beyond server branding.

### 3.4 Excluded from the first release

- browser-based (OIDC/OAuth) sign-in, account sign-up, and device-code sign-in
  in public builds (section 7.2);
- ebooks, comics, and document reading;
- downloads or offline playback;
- Silo server first-run setup and administration;
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
- Roku voice keyboards for every username, password, and PIN field, as
  certification criterion 4.12 requires;
- an FHD (1920×1080) layout. Roku scales it for HD devices, which include the
  current 512 MB models.

Roku's Static Analysis rules fix the platform floor. The manifest declares
`rsg_version=1.3` and a minimum firmware version of 15.1.0, and the app
registers for the memory monitor APIs (`roAppMemoryMonitor`). Roku's Static
Analysis page schedules all three to become publishing-blocking errors on
2026-10-01.
Memory threshold events arrive only from Roku OS 15.2, so the client also
handles the general low-memory event. The package must stay within Roku's
4 MB limit. The support claim covers every model that runs the minimum Roku OS
and must be backed by real-device testing.

Development uses Developer Mode sideloading (one sideloaded app per device),
then a Roku beta app (up to 20 testers per app, 120-day lifetime, no
certification), then public submission. App Behavior Analysis runs only on a
public app, not a beta.

Tooling:

- BrighterScript for compilation and checks, with `bslint`;
- `roku-deploy` for packaging and sideloading;
- Rooibos for unit tests;
- Roku Static Analysis (`sca-cmd` locally, and the dashboard on submission);
- the Roku Deep Linking Tester and App Behavior Analysis before release.

Official platform references:

- [Roku app structure and languages](https://developer.roku.com/dev/docs/getting-started)
- [SceneGraph](https://developer.roku.com/dev/docs/scenegraph)
- [Video node](https://developer.roku.com/dev/docs/video)
- [Streaming formats and codecs](https://developer.roku.com/dev/docs/media)
- [Closed captions](https://developer.roku.com/docs/specs/media/closed-caption.md)
- [Device capabilities](https://developer.roku.com/dev/docs/ifdeviceinfo)
- [Memory monitor](https://developer.roku.com/dev/docs/roappmemorymonitor)
- [Manifest](https://developer.roku.com/dev/docs/channel-manifest)
- [Static Analysis](https://developer.roku.com/dev/docs/static-analysis-tool)
- [On-device authentication](https://developer.roku.com/docs/developer-program/authentication/authentication-and-linking.md)
- [Deep linking](https://developer.roku.com/docs/developer-program/discovery/implementing-deep-linking.md)
- [Certification criteria](https://developer.roku.com/docs/developer-program/certification/certification.md)
- [Certification tests](https://developer.roku.com/dev/docs/cert-tests)
- [Publishing and beta apps](https://developer.roku.com/docs/developer-program/publishing/channel-publishing-guide.md)

## 5. UI and UX reference

### 5.1 Source and rule

The Silo tvOS and Android TV apps share one design. Most Android TV layout
sizes are the tvOS 1920×1080 point values halved (corner radii are not), and
Roku lays out at 1920×1080. Where the two apps differ, Roku follows Android
TV, which, like Roku, draws its own focus on low-cost hardware. Section 5.9
lists the places where Roku differs from both.

The values below were read from the tvOS app (silo-apple `5c1dcfb0`) and the
Android TV app (silo-android `05b3f91`) on 2026-10-09. When those apps change
a first-release screen, this section changes with them. Screens outside the
first-release scope are not described.

### 5.2 Design tokens

| Token | Value |
| --- | --- |
| Background | `#000000` |
| Surface / raised surface | `#0A0A0A` / `#15171C` |
| Text / secondary text | `#EDEDED` / `#EDEDED` at 75% |
| Hairlines | white at 12% |
| Accent | none; the UI is monochrome |
| Progress bar | `#EDEDED` over white at 20% |
| Font | Inter: Regular, Medium, SemiBold, Bold, Black |
| Side inset | 88 px (detail pages 100 px) |
| Poster card | 176×264 px |
| Landscape card | 360 px wide, 16:9 |
| Card gap / row gap | 40 px / 28 px |
| Poster focus | scale 1.10, 4 px `#EDEDED` ring |
| Landscape and episode card focus | scale 1.04, 4 px `#EDEDED` ring |
| Round button focus | `#EDEDED` fill with black text, no scale |
| Pill focus | white fill with black text, scale 1.025 |
| Card corner radius | 16 px |

Type sizes in px: hero or detail title without a logo 76 (detail 72), Black;
setup and sign-in headline 76, Black; row title 31, SemiBold; tab label 26,
SemiBold; info line 24, Medium; synopsis 27, Regular; player title 46, Bold;
player context line 19, uppercase with letter spacing.

Inter is licensed under the OFL and is what Android TV ships. If the five
weights strain Roku's 4 MB package limit, Black falls back to Bold first.

### 5.3 Shell, top bar, and Back

- The top bar sits 56 px from the top, 64 px tall, with 88 px side insets.
  Left to right: Silo wordmark, Search icon, Home, Movies, Series, profile
  avatar. A library tab appears only when the profile can see a library of
  that type. The bar appears on root pages and Search; detail pages have none.
  The avatar opens Switch Profile, Switch Server, and Sign Out.
- Tabs are 60 px capsules with 26 px labels. A focused tab has an `#EDEDED`
  fill and black text. The selected tab has a white-14% fill and a white-10%
  border. Resting labels are white at 62%. The bar dims to 70% while focus is
  in the content. Page content starts 188 px from the top.
- Resting on Movies or Series for about 200 ms, or pressing Down, opens that
  type's library list with Recommended and Browse for each library.
- Up from the first content row moves focus to the selected tab.
- Back closes an open list or overlay first. From content on a tab page, it
  moves focus to the selected tab. On the bar, it goes to Home; on Home's bar,
  it exits the app. On a pushed screen, it returns to the previous screen.
- Rows keep the focused card pinned at the row's start (`RowList` fixed focus).
- On return to a screen, focus goes back to the same item in the same row.
  If the item is gone, focus goes to the same position, then the nearest row.
  When the target is on a page that hasn't loaded yet, focus waits for it.

### 5.4 Setup, sign-in, and profiles

- **First-run layout.** The brand mesh (`#0034FB`, `#F50B4F`, `#FD7403`) sits
  over black, darkened on the left, and ships as a packaged image. Padding is
  90 px at the sides and 60 px at the top. Text sits in a 900 px column on the
  left, and a 640 px card on the right (radius 40, `#1F1F1F` at 72%). Headlines
  are 76 px Black, buttons are 76 px capsules, and fields are 84 px tall.
- **Server address.** The screen opens on address entry: placeholder
  `media.example.com`, shortcut chips `https://`, `http://`, and `.com`, then
  Connect and Back. An address without a scheme tries HTTPS, then HTTP. Before
  using plain HTTP, the client asks "Connect without encryption?", as both
  existing apps do.
- **Sign-in.** Username and password fields with show/hide, then Sign in and
  Change server. A failure shows "Invalid username or password".
- **Profile picker.** "Who's watching?" above round 220 px avatars, up to six
  per row. A focused avatar scales 1.12 with a 6 px white ring. Focus starts
  on the first profile. Change server and Sign out sit below the avatars. An
  account with a single profile and no PIN skips the picker. Ordinary launches
  reopen the last profile chosen on this device without asking again, which
  is both apps' default ("Automatic") profile-at-launch behavior.
- **PIN.** Full screen: the profile avatar, four dots, and the PIN entry. The
  PIN submits on the fourth digit. A wrong PIN turns the dots red. A lockout
  shows the server's message. Back cancels.

### 5.5 Home and libraries

- **Hero.** The top of Home is display-only and shows the focused card. Its
  backdrop sits top-right at about 64% width and 70% height, fading out to the
  left and bottom. A bottom-left block 880 px wide shows the title logo (up to
  880×168 px) or a 76 px title, a 24 px info line, and a 27 px synopsis. The
  hero changes after focus rests for 150 ms, with a 500 ms cross-fade.
- **Rows.** Rows appear in server order in a band at the bottom of the screen,
  taking at most 58% of its height. Continue Watching and Next Up rows use
  landscape cards with a progress bar; other rows use posters. OK on any card
  opens the detail page; from Continue Watching, the detail page opens with
  that episode selected.
- **Library landing.** A library tab opens on Recommended, the same row feed as
  Home, built from the library's sections.
- **Browse.** A six-column poster grid with 40 px column and 60 px row gaps,
  below a Sort pill. Sort options are Title, Date Added, Release Date, Year,
  Rating, Runtime, and Resolution; choosing the active sort again reverses it.
  The next page loads when focus is within eight rows of the end. When sorted
  by Title, an alphabet rail (All, #, A–Z) sits on the right edge as a narrow
  strip that widens when focused.
- **Empty states.** Home shows "Nothing to watch yet" with Refresh. An empty
  library shows "This library is empty".

### 5.6 Search and detail

- **Search** opens from the Search icon in the top bar. The keyboard and query
  sit at the top, then
  All, Movies, and Series chips once a query exists, then a result count and a
  six-column poster grid. Queries run 300 ms after typing stops, with 40
  results per page and at most 200 characters. Before a query the page shows
  "Search your library"; with no matches, "No matches for “query”" and "Try a
  shorter title or a different filter." The first Back returns to the
  keyboard; the next leaves Search.
- **Detail hero.** 690 px tall, 100 px side inset, text starting 116 px from
  the top in a 1080 px column. The backdrop sits top-right and fades out to
  the left and bottom. The title logo is up to 650×160 px, or a 72 px title
  without one. Below it are a metadata line separated by "·" (rating · year ·
  runtime or "N Seasons" · first two genres) and a three-line synopsis.
- **Action row.** Play, or "Resume 1:02:03" ("Resume 12:34" under an hour), or
  for a series "Play S2:E3" or "Resume S1:E3", then Start Over when a resume
  point exists, then Audio and
  Subtitles. Resume appears once progress passes 30 seconds and is more than 5
  seconds from the end. Buttons are 76 px circles that widen to show their
  label when focused. Focus starts on Play. Audio and Subtitles set the tracks
  sent with start.
- **Below the hero.** Series show season capsules (52 px tall, 24 px text);
  resting on one switches to that season. Episode cards are landscape, 40 px
  apart, captioned "S1 · E2". A focused episode updates the hero, and OK
  plays it. A Details section follows. After the player closes, focus moves
  to the next episode if the viewer finished one, or stays on the same episode
  otherwise (tvOS behavior; Android TV's is unconfirmed).

### 5.7 Player

- **Controls overlay.** A dark gradient covers the bottom 540 px. It holds a
  context line ("SHOW · S1:E2" or "MOVIE · 2024"), the 46 px title, and the
  scrubber: 8 px tall (14 px while scrubbing), with intro, recap, and credits
  ranges drawn as bands. Elapsed time is on the left; time left and end time
  are on the right. Below are round 88 px buttons: skip back, play/pause, and
  skip forward on the left; Up Next (episodes only), Subtitles, Options, and
  Close on the right. Focus fills a button `#EDEDED` without scaling. The
  controls hide after 5 seconds of playback.
- **Options panel.** Top-centered, up to 1560 px wide, with tabs Info, Stats,
  Video, Audio, and Subtitles. Video holds Quality (Auto plus the server's
  list) and Auto-play next. Stats shows the non-secret plan and player state.
- **Remote keys.**

  | Roku key | Controls hidden | Controls shown |
  | --- | --- | --- |
  | Left / Right | Skip back / forward (default 10 s / 30 s); hold 300 ms for the rate ladder | On the scrubber, skip and hold as when hidden; elsewhere, move focus |
  | OK | Show controls | Activate the focused button; on the scrubber, commit a pending seek, else toggle play/pause |
  | Up | Show controls | Move focus |
  | Down | Open Options on Audio (else Subtitles, else Video) | Move focus to the buttons |
  | `*` (Options) | Open Options on Video | Open Options on Video |
  | Play/Pause | Toggle | Toggle |
  | Replay | Skip back | Skip back |
  | Rewind / Fast-forward | Start the rate ladder; each press steps up | Same |
  | Back | See below | See below |

  Rapid skips merge into one seek after 200 ms.
- **Rate ladder.** Speeds are 1, 2, 4, 8, 16, and 32×. Every 100 ms the
  position moves by speed × 2 seconds. Holding climbs 1→2→4→8 every 1.2
  seconds, and taps step up or down. OK commits the new position; Back cancels
  it.
- **Back, first match wins:** cancel a seek or scrub; dismiss the skip button;
  close an open picker; from Up Next, exit the player; close Options; hide the
  controls while playing; otherwise stop and exit.
- **Skip intro.** The profile chooses never, ask, or always (default ask).
  Ask shows "Skip Intro" at the bottom right (112 px up, or 400 px when the
  controls show) for 5 seconds, with a fill that grows from left to right;
  the timer pauses while playback is paused. Always skips, then shows "Intro
  skipped" with a "Watch Intro" button for 5 seconds. Recaps are marked on the
  scrubber but not skipped, and there is no Skip Credits button.
- **Up Next** (episodes). It opens when playback passes the start of the
  credits, or when the video ends. The video shrinks to a 16:9 box on the left;
  the panel on the right holds Play Now, Keep Watching, Back, an auto-play
  toggle, and a countdown ring. The countdown is the remaining runtime when Up
  Next opens at the credits, and 10 seconds when it opens at the end. After
  three automatic advances in a row, Up Next appears without a countdown so
  the viewer must choose; Play Now resets the count.
- **Resume.** The player never asks whether to resume. The detail page's
  Resume and Start Over buttons decide. Resume starts 7 seconds before the
  saved position, the default of the device-local
  `player.resume_rewind_seconds` setting.
- **Waiting and errors.** "Buffering" shows while the player buffers, and
  "Reconnecting. Playback will resume automatically." while recovery
  (section 9.6) runs. A failure shows a full-screen message with Retry, plus
  "Try Anyway" when the server can't be reached.

### 5.8 Loading, empty, and error states

Screens load behind a centered 128 px spinner that never traps focus. A
screen-level error shows the message at 38 px with a Retry button. A Home or
library row that fails to load is left out, as Android TV does, and the other
rows stay usable.

### 5.9 Roku differences

| Existing apps | Roku | Reason |
| --- | --- | --- |
| QR or device-code sign-in is the default; password is the alternative | Password sign-in only | Certification criterion 2.2 |
| "Set up with your phone" and network discovery lead server setup | Address entry only | Deferred (section 3.3) |
| Custom PIN keypad | Roku `DynamicPinPad` inside the same layout | Criterion 4.12 requires Roku keyboards for PINs |
| Platform or custom text fields | Roku dynamic keyboards, with voice entry | Criterion 4.12 for credentials; Roku's standard for search |
| Backdrop tint sampled from the artwork | Fixed black scrim | BrightScript cannot read image pixels, and the server publishes no artwork color |
| SF Pro on tvOS | Inter, as on Android TV | SF Pro cannot ship outside Apple platforms |
| Rewind and fast-forward skip (Android TV) | Rewind and fast-forward drive the rate ladder | Roku remote convention |
| Skip Credits button (tvOS) | Up Next at the credits (Android TV) | The apps differ; Roku follows Android TV |
| Versions, Watchlist, and More buttons; cast, trailers, and related sections; Collections in the library list; Filter and Shuffle; people in search; Home row reordering; Watchlist, Favorites, History, and Settings in the avatar menu; Chapters, Speed, and Aspect | Not in the first release | Scope (section 3.3); deferred controls keep their positions when added |

## 6. Application architecture

### 6.1 Proposed repository layout

```text
manifest
source/
  main.brs                 app entry point and launch arguments
  api/                     centralized /api/v2 requests, Problem Details, URLs
  auth/                    session, refresh, profile, and registry state
  playback/                v3 DTO mapping, capability probe, plan execution
  settings/                effective server preferences for the active profile
  storage/                 typed registry access
  util/                    bounded shared helpers
components/
  AppScene.xml/.brs        root state machine and navigation stack
  theme/                   design tokens from section 5
  screens/                 setup, sign-in, profiles, home, library, search, detail
  player/                  Video node wrapper and playback chrome
  tasks/                   network and decoding Task nodes
  views/                   reusable rows, cards, dialogs, empty/error states
images/                    packaged icons and splash artwork
locale/                    localized strings
tests/                     Rooibos unit, contract, and device-flow tests
  fixtures/                vendored server fixtures with a SOURCE pin
docs/
  spec.md                  this specification
```

### 6.2 State and navigation

`AppScene` owns a small explicit state machine:

```text
server setup -> sign-in -> profile selection -> main shell -> detail -> player
      \-> server update required
```

The scene owns one navigation stack. Each stack entry records its route,
parameters, and focus restoration key. Back behavior follows section 5.3. No
screen may infer its previous screen from global flags.

### 6.3 Threading and ownership

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

### 6.4 API client rules

- v2 errors are RFC 9457 Problem Details (`application/problem+json`). The
  client reads the problem identifier from the final path segment of `type`
  and never parses `detail` for control flow. The diagnostic overlay may show
  the request ID from `instance`.
- `401 invalid_token` (an expired or invalid access token) or
  `401 token_refresh_required` (the account's role changed) on an
  authenticated request: refresh once through the coordinator and retry the
  request once.
- Only a refused refresh signs the user out: `401 session_expired` (session
  revoked) or `401 invalid_token`.
- `503 dependency_unavailable` (with `Retry-After`) or
  `503 provider_unavailable`: keep the tokens, wait, and retry. A server
  outage never signs the user out.
- `422 validation_failed` is a client bug. It is shown as a generic error and
  recorded in the diagnostic overlay without request bodies.
- Login, PIN verification, and device-login start are never replayed
  automatically after an uncertain response.
- Collections use cursor pagination: pass `page.next_cursor` back unchanged as
  `cursor`.
- Feature detection uses each domain's capability document. `server_version`
  and `contract_digest` are diagnostic only.

## 7. Server connection and authentication

### 7.1 Server origin

The client accepts only an `http` or `https` origin. It removes trailing
slashes and rejects URLs containing credentials. It checks the origin with the
unauthenticated `GET /api/v2/system/info` before presenting sign-in and
requires `api_major` 2. Any other answer, including a v1-only server, shows the
"server update required" screen.

No Roku rule found so far addresses plain HTTP. Self-hosted installations
suggest allowing LAN HTTP. As in the existing apps, the client asks "Connect
without encryption?" before using plain HTTP (section 5.4), and it never
silently downgrades an HTTPS URL. Roku trusts only its system CA
bundle and certificates packaged with the app, so private-CA and self-signed
HTTPS servers are unsupported in the first release. The client will not ship a
bypass for certificate validation.

### 7.2 Account sign-in

The public release uses on-device credential entry:

1. `GET /api/v2/auth/providers` lists sign-in modes. When `password_login` is
   false, the server offers only browser sign-in, which Roku does not allow.
   The client explains that the server administrator must enable password
   sign-in, and stops there.
2. The username and password are entered with the Roku voice keyboard and
   posted to `POST /api/v2/auth/login`.
3. Access and refresh tokens are written to an app-specific registry section
   only after sign-in succeeds.
4. `GET /api/v2/account/me` validates a restored session.
5. `POST /api/v2/auth/refresh` rotates both tokens through the centralized
   single-flight coordinator.
6. Logout calls `POST /api/v2/auth/logout` when reachable and then clears all
   local credentials regardless of the network result.

Every sign-in sends `X-Silo-Device-Id`, `X-Silo-Device-Name`, and
`X-Silo-Device-Platform: roku`, so the session appears correctly in the
account's session list.

Roku certification criterion 2.2 requires on-device authentication and
prohibits off-device sign-in or activation. Silo's device-code login
(`/api/v2/auth/device/*`) and browser-based OAuth sign-in are therefore
excluded from public builds. Device-code login may remain in development and
beta builds.

An app update must not force the viewer to sign in again (criterion 4.1).
Registry layout changes migrate stored sessions instead of discarding them.

The Roku registry is treated as app-scoped persistence, not as a general secret
manager. Tokens must never appear in logs, error dialogs, crash breadcrumbs,
analytics, or copied diagnostic payloads.

### 7.3 Profiles

After sign-in the client loads `GET /api/v2/profiles`. Ordinary launches
reopen the last profile chosen on this device (section 5.4), after checking
that it still exists and remains permitted. The client never picks a profile
the viewer has not chosen on this device, so it never falls back to a child
profile on its own.

PIN-locked profiles use `POST /api/v2/profiles/{id}/verify-pin`. A wrong PIN
answers `200` with `valid: false`. Five wrong PINs lock the profile for five
minutes, and the server answers `429` with `Retry-After`. The client shows
the remaining time, as the server's auth guide recommends ("Too many
incorrect PINs. Try again in 5 minutes."), and never retries a PIN check on
its own. The issued profile token is bound to the current login session; the
client stores it with the remembered profile and asks for the PIN again only
when the server refuses it.

### 7.4 Request headers

Every authenticated request carries:

- `Authorization: Bearer <access token>`;
- `X-Profile-Id: <active profile>` once a profile is selected;
- `X-Profile-Token: <verified PIN token>` when the profile requires one;
- `X-Silo-Device-Id: <random per-install ID>`, made only of letters, digits,
  `.`, `_`, `:`, and `-`, at most 128 characters;
- `X-Silo-Device-Name` and `X-Silo-Device-Platform: roku`;
- `X-Silo-Client: Silo Roku`, `X-Silo-Client-Version`, `X-Silo-Client-Build`,
  and `X-Silo-Client-Channel` (`release`, `beta`, `sideload`, or `dev`).

Settings reads also send `X-Silo-Client-Family: tv`.

The installation ID is generated once and stored in the registry. A Roku
hardware serial number or advertising ID is not used as Silo's device identity.

## 8. Catalog and browse behavior

### 8.1 Endpoints

The first release consumes:

- `GET /api/v2/user/libraries` to decide which library tabs exist;
- `GET /api/v2/home/sections` and `GET /api/v2/home/sections/{id}/items`;
- `GET /api/v2/library/{id}/sections` and
  `GET /api/v2/library/{id}/sections/{section_id}/items` for a library's
  Recommended rows;
- `GET /api/v2/catalog` for paginated browse, with `type`, `sort`, and
  `name_prefix` for the alphabet rail;
- `GET /api/v2/catalog` with `q` for search, using `type=video_with_episodes`
  when `GET /api/v2/catalog/search/capabilities` advertises it, and `video`
  otherwise;
- `GET /api/v2/catalog/items/{id}` for detail;
- `GET /api/v2/catalog/series/{id}/seasons` and
  `GET /api/v2/catalog/series/{id}/seasons/{num}/episodes`;
- `GET /api/v2/watch/{id}` for the playable projection, including
  `marker_segments`;
- `GET /api/v2/settings/values/effective` for the profile's preferences;
- `GET /api/v2/theme/branding` for server branding.

### 8.2 Loading rules

The client never loads an entire large library to sort or filter locally.
Pagination, access filtering, section composition, and search stay server-side.
Rows retain a bounded window around visible content, and image requests use
server-provided image resources sized for their presentation.

Every primary surface defines loading, empty, recoverable error, authorization
error, and stale-session states, presented as section 5.8 describes. A failed
row does not blank the entire home screen; it is left out while the other
rows remain usable.

### 8.3 Series play target

A series or season detail whose `play_content_id` names an episode also carries
`play_season_number`. The detail screen opens on that season, and the primary
action plays that episode. Deep links to a series use the same target
(section 10).

### 8.4 Images

Artwork comes from the image URLs in server responses, sized for the card that
shows it. Images are dropped from memory when their row leaves the retention
window and on any account, profile, or server change.

### 8.5 Server-stored preferences

The client reads the active profile's effective settings and applies the
playback keys the existing TV apps honor:

| Setting key | Roku behavior |
| --- | --- |
| `player.video_skip_back_seconds`, `player.video_skip_forward_seconds` | Left/Right and Replay skip step |
| `playback.audio_language` | The client picks the initial audio track from the watch projection and sends it as `audio_track_id` |
| `playback.subtitle_mode`, `playback.subtitle_language`, `playback.show_forced_subtitles` | The client picks the initial subtitle track the same way |
| `playback.preferred_quality`, `playback.max_bitrate_kbps` | `quality_preference` and `bandwidth_cap_kbps` sent with start |
| `playback.intro_skip_mode` | Skip button versus automatic skip (`playback.auto_skip_intro` is deprecated) |
| `playback.auto_play_next` | Up Next countdown and autoplay |

Start has no language member, so language preferences are applied by choosing
tracks, as Android TV does. Settings marked `client_local` in the server's
settings manifest, such as `player.resume_rewind_seconds`, are not served by
the effective-settings endpoint; the client uses their manifest defaults.
Subtitle appearance is left to Roku's system caption settings (section 9.7).
The client does not write settings in the first release.

## 9. Playback protocol v3 over `/api/v2`

The normative contracts are in the Silo server repository:
[playback protocol v3](https://github.com/Silo-Server/silo-server/blob/main/docs/architecture/playback-protocol-v3.md)
and the [v2 playback API](https://github.com/Silo-Server/silo-server/blob/main/docs/playback-api.md).
This section defines only the Roku execution mapping.

### 9.1 Capabilities and installation

Before the first playback attempt, the client reads
`GET /api/v2/playback/capabilities` (with `If-None-Match`). It requires
`state: "available"`, `allowed: true`, `protocol_versions` containing 3, and
`features` containing `sequenced_progress_v1`, and it stores
`installation_id`. Every playback
mutation carries that `installation_id`. A `409 installation_changed` means the
server was replaced or restored: the client re-reads capabilities and starts a
new attempt.

### 9.2 Device capability probe

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
- `original_http` and `hls` are advertised independently. `progressive` is
  advertised as disabled, as the Android TV client does
  (`disabled_pending_seekable_transport`), until a seekable progressive
  transport exists;
- unsupported subtitle features remain false rather than being inferred from a
  related Roku capability.

Initial codec probes cover H.264, HEVC, VP9, AAC, AC-3, and E-AC-3. AV1, Dolby
Vision, HDR10+, HLG, DTS variants, and lossless audio are later capability
increments backed by fixtures and hardware evidence.

### 9.3 Start and plan execution

1. Send `POST /api/v2/playback/start`: the v3 start request plus
   `installation_id`. Required members include `protocol_version: 3`,
   `client_features`, `file_id`, the active `profile_id`, a fresh
   `playback_attempt_id`, `quality_preference`,
   `subtitle_fidelity_preference`, `metered`, `client_capabilities`, and
   `client_playback_context`.
2. Start answers `201` even when the decision is terminal. The client shows
   `terminal.message`. A retryable `session_expired` mints a new attempt.
3. After an uncertain response, the client may replay the identical body; the
   server returns the stored decision. Reusing an attempt ID with a different
   body is `409 idempotency_conflict`.
4. Treat `playback_plan`, `plan_id`, `plan_attempt_key`, stream URL, track
   inventory, subtitle artifact, and quality entries as opaque server output.
5. Construct one `ContentNode` for the plan and assign it to the `Video` node.
6. Set the explicit stream format from the plan delivery and container; never
   infer it from a URL suffix, because Silo media URLs need not have one.
7. Observe player state, buffering, position, duration, selected tracks, and
   error details, and translate them to route events and replans.

### 9.4 Media authentication

The first release keeps the default signed-URL mode, so sessions survive API
restarts, and advertises neither `header_authenticated_media_v1` nor
`authorized_media_origins_v1`. In that mode a plan's media URL is one of two
kinds:

- **On the configured server's origin.** These routes sit behind the server's
  authentication gate and answer `401` without a user. The signed `st`
  parameter they carry is a transport token that lets the server rebuild a
  session after an API restart; it does not replace account authentication.
- **On a proxy-node origin**, with a signed token in the path. That token is
  the credential.

The client sets `Authorization`, `X-Profile-Id`, and `X-Profile-Token` as
`HttpHeaders` on the plan's `ContentNode` only when the media URL is on the
configured server's origin, as the Android TV client does. Account credentials
are never sent to any other origin. Roku documents that the `Video` node sends
these headers to the server, but not whether HLS playlist, segment, and caption
requests carry them. The feasibility build must prove that every request
carries them, including after a seek.

Access tokens last eight hours by default. The client cannot assume that new
headers reach a stream that is already playing. It refreshes the token before a
start when expiry is near. If media requests fail with `401` mid-playback, it
refreshes and reloads the content at the current position.

If Roku cannot attach headers to every media request, the fallback needs a
server decision before implementation. `docs/playback-api.md` allows a media
element that cannot set headers to send the account token as a `token` query
parameter, and the server copies a manifest's query string onto its segment
URIs, so a token on the manifest reaches the segments. Protocol section 4.2,
however, limits media URLs to `seek` and forbids clients from composing URLs.
The profile headers would also need a header-free form, and the access token
would then appear in URLs that proxies and server logs may record.

### 9.5 Progress and stop

- While playing or paused, the client posts
  `POST /api/v2/playback/{session_id}/progress` with
  `{installation_id, sequence, position, is_paused}` every 10 seconds, as
  Android TV does. The server ends a session after about 45 seconds without
  any activity (start, a playable replan, progress, or media requests), about
  5 minutes when a proxy node serves the media, and 30 minutes when the last
  report said paused.
- `sequence` increases for every sample in a session. `applied`,
  `stale_sample`, and `replayed` are all success. `409 progress_conflict`
  means the client reused a sequence with a different sample, which is a client
  bug.
- Stop is `DELETE /api/v2/playback/{session_id}` with `{installation_id,
  stop_id}` and the final `{sequence, position, is_paused}`. `stop_id` is a
  UUID minted once (`roDeviceInfo.GetRandomUUID()`, lowercased, since the
  server accepts only the lowercase canonical form) and reused on every retry.
  `200` with `outcome: "replayed"` is success.
- The client deduplicates progress by attempt and session and never lets a late
  event from an old `Video` node update the new session. During a network
  outage it keeps only the latest unsent sample and sends that on recovery.

### 9.6 Failure, replan, and route events

Replans use `POST /api/v2/playback/{session_id}/replan` with the v3 body plus
`installation_id` and a fresh `replan_request_id`. The `operation` is one of
`failure_recovery`, `seek_failure_recovery`, `seek_reanchor`, `track_change`,
`quality_change`, or `output_change`. For each replan the client:

1. echoes the exact `failed_plan_id` and `plan_attempt_key` from the server,
   and sends the `plan_attempt_id` it minted when it adopted that plan;
2. sends `attempted_plan_keys` (at most 16) and `attempt_count` (1 to 8);
3. for `failure_recovery` and `seek_failure_recovery`, sends `failure` with a
   classification of at most 64 characters, using the values the existing
   clients send, and a message of at most 512; track, quality, and output
   changes carry no `failure`;
4. executes the returned plan from a clean `Video` node state;
5. stops when the server returns a terminal result or the attempt limit is
   reached.

A track, quality, or output change may legitimately return a plan key already
tried. A network drop after the stream has shown frames is recovered with a
`track_change` that changes nothing, not with `failure_recovery`; a failure
before the first frame takes the normal failure path.

Route events go to `POST /api/v2/playback/route-events` with the v3 event,
`installation_id`, and a client-minted `event_id`. Only route events carry the
allowlisted `diagnostics` map. They are never retried; a `429` drops the
event. The first-frame event includes `first_frame_ms` in `diagnostics`,
except for autoplay starts such as Up Next.

The Roku client never constructs a transcode request, guesses a fallback URL,
or repeats a failed plan without telling the server. The Android TV client is
the reference for the client-side policy this section leaves open: one-shot
local retries before a replan, the stall timeout, repeated-key detection, seek
re-anchoring, and progress and stop retries.

### 9.7 Quality, tracks, and subtitles

- The quality menu displays `playback_plan.available_qualities` exactly as
  published and sends the selected label in a `quality_change` replan.
- Audio and subtitle selection send `selected_tracks.audio` or
  `selected_tracks.subtitle` as `{id, index}` in a `track_change` replan. `id`
  is the inventory's track identity and is required; `index` is sent only when
  the inventory provides one. The client never derives combined subtitle
  ordinals.
- The first release does not claim client-side audio selection within an
  original file; the server may choose a remux that makes selection
  deterministic.
- A newly returned plan replaces the entire previous track and subtitle state.

Subtitle artifacts are authenticated resources on the API origin, even when
media comes from elsewhere; there is no signed subtitle URL. Sidecars use
absolute source timestamps, and a VTT receiver can request `timestamp_offset`
when it cannot map its video clock.

Roku documents side-loaded SRT and TTML files, and WebVTT only inside HLS.
The feasibility build tests, in order:

1. the plan's WebVTT sidecar URL as a `Video` subtitle track, with the
   `ContentNode` headers;
2. original SRT through the `subrip_sidecar_v1` feature, which covers external
   and downloaded SRT tracks only;
3. downloading the sidecar through the API client into bounded `tmp:/` storage
   and supplying the local file.

Each path is tested for direct and HLS playback, seeking, resume offsets,
Unicode, position, and Roku caption-mode changes. If none works reliably, the
fallback requires a coordinated server contract change before implementation.

Until that proof exists, the Roku capability declaration is conservative:

- `sidecar_text`: false in production capability reports;
- `ass_styling`: false;
- `embedded_bitmap` and `sidecar_bitmap`: false;
- `font_attachments`: false.

ASS/SSA and bitmap subtitles always request server conversion or burn-in. The
client respects Roku's global caption mode and caption style settings instead
of creating a second competing caption preference.

### 9.8 Markers and next episode

`GET /api/v2/watch/{id}` returns `marker_segments` for each file version: an
ordered list of `{kind, start_seconds, end_seconds}` with kind `intro`,
`credits`, `recap`, or `preview`. A kind may occur more than once; the client
skips only the active range. Intro ranges drive the skip button and automatic
skip (section 5.7) according to `playback.intro_skip_mode`. Recap and credits
ranges are drawn on the scrubber, and the start of the credits range opens Up
Next.

The next episode is resolved as the Android TV client does. The client loads
the current season's episodes; if that fails, it offers no next episode. It
then tries the next regular season (specials are skipped); a failure there
only prevents rollover into that season. The next episode is the one after
the current episode in that combined list. The countdown and autoplay follow
section 5.7 and `playback.auto_play_next`.

## 10. Deep links and certification

### 10.1 Deep links

Public Roku apps with video must support deep linking for every media type and
Direct to Play (criteria 5.1 and 5.2). The manifest sets
`supports_input_launch=1`. `Main(args)` and in-app input events accept
`contentId` and `mediaType`, validate them, and:

- play a movie or episode directly, resuming from the server position, without
  a resume prompt;
- for a series, play the series' play target episode directly
  (`play_content_id`, section 8.3), as Roku's smart-bookmark rule requires;
- treat a season like its series (Roku Search no longer sends season links);
- defer the destination through on-device sign-in when no session exists;
- fall back to Home when the request is invalid or inaccessible.

A deep link may not show the profile picker. The client uses the last profile
chosen on this device (section 7.3); if that profile cannot see the content,
the client falls back to Home. Content IDs are opaque Silo identifiers and
must not embed a server origin, access token, profile ID, or title metadata.

### 10.2 Certification materials

Certification needs:

- a test account on a Silo server Roku's reviewers can reach from the public
  internet, seeded with a movie, a series, and an episode for the deep-link
  sample parameters, with a stated expiry date for the credentials;
- Roku Static Analysis with no errors, App Behavior Analysis (public app only),
  and the Deep Linking Tester;
- store artwork, privacy policy URL, and age rating;
- testing on several current devices with materially different memory and
  playback capabilities.

A Roku Search feed and Continue Watching integration are not required; Roku
requires Continue Watching only above 5 million monthly streaming hours in the
U.S. or 1 million elsewhere. Criterion 4.15 bars using the device as a proxy or
relay, which matters for any later SiloControl receiver.

Questions for Roku before public submission:

1. May the public app connect to LAN HTTP origins, and what disclosure is
   required?
2. May a deep link prompt for the remembered profile's PIN, or does that count
   as a disallowed screen?
3. Is a reviewer test server with seeded content sufficient for a self-hosted
   client with no global catalog?

## 11. Security and privacy

- Accept API and media URLs only from the configured Silo server and opaque
  server-issued playback plans. Never add a general URL player.
- Reject URL schemes other than HTTP and HTTPS.
- Never follow an HTTPS-to-HTTP downgrade as an automatic recovery action.
- Do not log or display credentials, tokens, PINs, signed query strings,
  media URLs, or complete authenticated response bodies.
- Sign-out and server changes clear tokens, profile state, and cached personal
  metadata. Sign-out clears credentials even when the server is offline.
- Do not use the Roku serial number, advertising identifier, or household
  account identity as Silo's installation ID.
- Do not add analytics, crash reporting, advertising, or third-party tracking
  SDKs without a separate privacy and dependency review.
- Images and metadata remain bounded in memory and are dropped on account,
  profile, or server changes so one identity cannot see another's cache.

## 12. Testing and release evidence

### 12.1 Automated tests

Rooibos unit tests cover:

- URL normalization and resolution;
- `system/info` gating and the "server update required" path;
- JSON model decoding with missing, null, extra, and malformed fields;
- Problem Details decoding and the `401`, `409`, `422`, `429`, and `503`
  handling in section 6.4;
- auth refresh single-flight and one-retry limit;
- profile/PIN header composition and PIN lockout handling;
- navigation-stack and focus-restoration reducers;
- playback-v3 request serialization and response fixtures;
- `installation_id` handling, progress sequencing, and stop idempotency;
- exact preservation of plan IDs, attempt keys, track IDs, and URLs;
- replan operation selection and error classification;
- progress deduplication and old-session event rejection;
- marker-range and next-episode selection;
- deep-link parsing and authenticated deferral;
- secret redaction.

### 12.2 Fixtures

Fixtures are copied from the Silo server repository, not from another client.
Wire shapes come from `contracts/api/v2/fixtures/`, including the
`playback_*.json` files for capabilities, start, progress, replan, route
events, and stop. `internal/playback/testdata/protocol_v3/conformance_matrix.json`
supplies planner and replan scenarios only; that directory's request and error
files use the v1 envelope. `tests/fixtures/SOURCE` records the server commit
the fixtures came from. Do not hand-simplify fixtures until they no longer
exercise the real wire shape.

### 12.3 UI parity review

Each first-release screen is compared side by side with the tvOS and Android
TV apps on the same server and profile. Differences are fixed or listed in
section 5.9.

### 12.4 Real-device matrix

At minimum, validation needs:

- a currently supported 512 MB HD device;
- a mainstream 4K/HDR streaming player;
- a Roku TV or a materially different audio/output path;
- the current Roku OS and the minimum supported Roku OS where obtainable.

Each device runs:

- cold/warm launch, logout, token expiry, profile PIN, and server replacement;
- long Home rows, large grids, fast directional navigation, and image failures;
- H.264/AAC direct play;
- HEVC and VP9 eligibility where supported;
- HLS remux and transcode;
- AC-3/E-AC-3 fallback and output-route changes;
- seek, pause/resume, Replay, long playback across a token refresh, and API
  restart during playback;
- quality, audio, subtitle, and forced burn-in replan;
- skip markers and next-episode countdown;
- Unicode metadata and subtitles;
- memory-monitor events and app resume;
- valid, invalid, inaccessible, and unauthenticated deep links.

Tests wait on player or API state and never use a fixed sleep as their success
condition.

## 13. Milestones and exit criteria

### Milestone 0 — policy and playback feasibility

- A Roku developer account, a 512 MB device, and a 4K/HDR device are available.
- Password sign-in, profiles, and PIN work against a real Silo server over
  `/api/v2`.
- Capability probe, direct play, HLS transcode, progress, stop, and one replan
  work on both devices.
- Every media request (file, manifest, segments, subtitles) is shown to carry
  the account headers, or a server-side fallback is agreed.
- The subtitle matrix in section 9.7 has a result.
- Someone owns the reviewer test server, and the Roku policy questions in
  section 10.2 have answers.

### Milestone 1 — client foundation

- Build, package, sideload, lint, Static Analysis, and test commands are
  reproducible.
- Manifest, memory monitor, registry, API client, auth refresh, profiles/PIN,
  app state, navigation, error envelopes, and secret-safe logging are
  implemented and tested.
- Design tokens from section 5 are in `components/theme/`.

### Milestone 2 — browse

- Home, Movies, Series, Search, details, seasons, and episodes match section 5
  with bounded pagination and deterministic focus.
- Loading, empty, offline, unauthorized, and partial-row failure states are
  usable.

### Milestone 3 — playback

- The protocol-v3 matrix passes on every target device.
- Quality and track replans, progress/resume, server restart, output changes,
  token refresh during playback, and terminal errors behave predictably.
- Skip markers, next episode, and server preferences match the existing apps.
- Accessibility and captions pass the chosen supported matrix.

### Milestone 4 — beta and public readiness

- Deep links and Direct to Play satisfy Roku requirements.
- Performance, memory, accessibility, privacy, store assets, Static Analysis,
  and App Behavior Analysis gates pass.
- A Roku beta is exercised by real Silo households before public submission.

## 14. Server coordination

No server change is needed for sign-in, browse, or playback:
`X-Silo-Device-Platform` is free text, and device registration, rate limits,
and CORS have no platform allowlist. The following follow-ups are tracked with
the server:

- add `roku` to the v2 migration ledger's consumers, with `silo-roku` as its
  source tree;
- add `roku` to the settings manifest's platform list (advisory only);
- add `roku` to the hosted-diagnostics platform allowlist before diagnostics
  upload is in scope;
- decide the media and subtitle authentication fallback if section 9.4 or
  9.7 fails on hardware.

## 15. Open decisions

| Decision | Initial leaning | Needed evidence |
| --- | --- | --- |
| Public Store or beta-first | Beta-first | Roku policy answers and household testing |
| Plain LAN HTTP | Allow after the "Connect without encryption?" confirmation | Roku reviewer answer |
| Password-less (OAuth-only) servers | Explain and stop; no browser sign-in | None; confirm product copy |
| Device-code sign-in | Development and beta only | Roku approval for public use |
| Reviewer test server | Required; owner not yet assigned | An owner and a host |
| Media authentication | `HttpHeaders` on the `ContentNode` | Milestone 0 header test |
| Side-loaded subtitles | Disabled until proven | Section 9.7 matrix |
| PIN prompt on deep link | Prompt for the remembered profile's PIN | Roku answer |
| AC-3/E-AC-3 passthrough | Disabled until proven | Codec/output-change hardware tests |
| Dolby Vision and advanced HDR | Defer | Exact Roku probe-to-v3 mapping and fixtures |
| Roku Search feed | Not planned | Roku guidance if usage grows |
| SiloControl receiver | Defer | Foreground networking, discovery, and criterion 4.15 |

## 16. Definition of done for this draft

This draft is ready to become an implementation plan when Milestone 0 has an
owner, target devices, a Roku developer account, an owner for the reviewer
test server, and results for the media-authentication and subtitle tests.
