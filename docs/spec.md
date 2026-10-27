# Silo Roku client specification

**Status:** Draft for implementation planning

**Last updated:** 2026-10-25

**Owner:** Silo Roku client

**Target:** Native Roku SceneGraph application using BrightScript

## 1. Decision summary

Silo Roku will be a native SceneGraph/BrightScript client for Silo's native
`/api/v2` API and playback protocol v3. Roku cannot run the Apple, Android,
React Native, or jellycompat client code, so none of it is reused. Consistency
with the other first-party clients comes from three things: the shared server
contract, test fixtures vendored from the server repository, and the design
reference in section 5, which records how the existing Silo TV apps look
and behave: tvOS first, and Android TV where tvOS is silent or Roku shares its
constraints (section 5.1).

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
  player controls follow the Silo tvOS app, and the Android TV app where tvOS
  is silent (section 5.1). Every Roku difference is listed in section 5.9
  with its reason.
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
- switch profile, switch server, and sign out;
- companion sign-in: a Silo phone app on the network signs a new Roku in
  from the server or sign-in screen ([`companion-pairing.md`](companion-pairing.md)).

Browse:

- Home built from the server's home sections, including the Continue Watching
  and Next Up rows the server provides;
- Movies and Series library tabs, each with Recommended rows, a Browse
  grid with sort and an alphabet rail, and read-only Collections pages;
- search across movies, series, and episodes;
- movie detail, and series detail with season and episode lists, cast, and
  recommendations;
- on the heroes, the detail page's credit line ("Directed by", "Starring")
  and the server's external ratings, Home's quality badges, and the
  profile's title-art preference (`ui.title_art`).

Play:

- play, resume, or start over from server watch state;
- the version, audio track, and subtitle to start with, chosen on the detail
  page (section 5.6), with audio and subtitle picks saved to the server's
  track preferences (section 8.5);
- direct play, HLS remux, and HLS transcode, as protocol v3 plans them;
- play/pause, skip, the rate ladder, scrubbing, Replay, and stop;
- seek-preview thumbnails (trickplay) from the server's sprite sheets;
- audio, subtitle, and quality selection through replan;
- Skip Intro, Skip Recap, and Skip Credits using server markers, with the
  profile's recap and credits auto-skip (`playback.auto_skip_recap`,
  `playback.auto_skip_credits`);
- Up Next near the end of every movie and episode, with autoplay and On Deck;
- periodic and final progress reporting;
- the profile's server-stored playback preferences (section 8.5).

Platform:

- deep links and Direct to Play as Roku certification requires;
- Roku's caption and accessibility settings respected;
- the SiloControl receiver: a Silo phone app on the network controls
  playback, launches titles, and hands off its profile
  ([`silocontrol.md`](silocontrol.md)), on in every build since 2026-10-25
  (decision D-7, section 15).

Section 5 describes how each of these looks and behaves.

### 3.3 After the first release

The owner chose this list on 2026-10-26 (decision D-8 in
[`implementation-assumptions.md`](implementation-assumptions.md)), after
comparing the Roku client with the tvOS and Android TV apps (silo-apple
`2c8f2e1b`, silo-android `9867edfa4`). The order is not set. Each item names
the Silo TV app that already ships it; that app is the reference when the
item is built, tvOS first where both have it (section 5.1).

Planned:

- Watchlist, Favorites, and History screens, with the add and remove
  toggles and mark watched or unwatched (tvOS, Android TV); until then,
  server rows that contain this data still display on Home;
- full person pages with filmography (tvOS, Android TV), replacing the
  first release's person panel (section 5.9);
- trailers and extras in the detail page's Trailers & More rail (tvOS,
  Android TV); tvOS opens remote trailers in the YouTube app, which
  criterion 5.3 rules out on Roku, so remote trailers need another route;
- library filters and Shuffle (tvOS, Android TV);
- Requests, Calendar, and the For You tab (tvOS, Android TV); Shuffle and
  Requests show only when the server offers them;
- chapters, playback speed, and aspect in the player's Options (tvOS,
  Android TV);
- a sleep timer in the video player (Android TV; tvOS sets one only in its
  audio player);
- episode spoiler hiding (tvOS, Android TV);
- theme music on detail pages (tvOS, Android TV);
- the buffering-quality pill and its prompts, with
  `playback.buffering_quality_mode` (the pill on tvOS and Android TV; the
  mode setting on Android TV);
- the marker on AI-translated subtitle tracks (Android TV);
- subtitle search and download (tvOS, Android TV);
- multiple saved Silo servers, with Switch Server (tvOS, Android TV);
- profile creation (tvOS, Android TV) and editing (Android TV).

Not decided yet, and deferred until the owner chooses:

- audio delay (Android TV) and subtitle delay (tvOS, Android TV);
- subtitle translation and sync (tvOS, Android TV);
- local-network discovery of Silo servers (tvOS, Android TV), and DIAL;
- Home row editing (Android TV);
- an edition picker (Android TV); the Version menu names each version's
  edition (section 5.6);
- hosted diagnostics upload (tvOS, Android TV);
- Home's hero line for the focused item's air date and cast, which costs an
  item read per card the viewer rests on.

Roku platform work, still deferred:

- SiloControl's Require Pairing (the `sealed` level), offered only in
  development builds until the phone apps speak it, and cross-server handoff
  ([`silocontrol.md`](silocontrol.md) section 13);
- Roku Search feed and Continue Watching integration;
- theme catalog integration beyond server branding.

Settings for features this client does not implement stay out of Settings;
supported settings are available there (section 5.8.1).

### 3.4 Excluded from the first release

- browser-based (OIDC/OAuth) sign-in, account sign-up, and device-code sign-in
  in public builds other than companion sign-in (section 7.2);
- music and audiobooks (decision D-8), although tvOS and Android TV play
  them;
- a notifications inbox, and collection creation and editing, which no Silo
  TV app offers;
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
`rsg_version=1.3`, the Developer Dashboard's Package page sets a minimum
firmware version of 15.1.0 (it is not a manifest key; release checklist
section 3), and the app registers for the memory monitor APIs
(`roAppMemoryMonitor`). Roku's Static Analysis page schedules all three to
become publishing-blocking errors on 2026-10-01.
Memory threshold events arrive only from Roku OS 15.2, so the client also
handles the general low-memory event. The package must stay within Roku's
4 MB limit. The support claim covers every model that runs the minimum Roku OS
and must be backed by real-device testing.

Development uses Developer Mode sideloading (one sideloaded app per device),
then a Roku beta app (up to 20 testers per app, 120-day lifetime, no
certification), then public submission. App Behavior Analysis runs only on a
public app, not a beta.

Tooling:

- BrighterScript (`.bs` sources) for compilation and checks, with `bslint` and
  `brighterscript-formatter`;
- `scripts/sideload.sh` for sideloading, which keeps the device password off the
  command line (`roku-deploy` only if signed `.pkg` builds need it);
- Rooibos for unit tests, run headless under `brs-node` in CI and on device for
  suites that need real threads or platform events;
- `scripts/check-thread-rules.js` in CI, which fails when a script on the
  render thread creates a component Roku allows only in a Task node or on the
  main thread: `brs-node` does not enforce Roku's thread rules, and
  hardware run 25's app stopped on one (assumption AG-237);
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

The Silo tvOS app is the reference for the Roku client's layout, sizes,
typography, copy, and focus behavior (decision AG-222, D0). Roku lays out at
1920×1080, and one tvOS point is one Roku pixel. The Android TV app is
consulted only where tvOS is silent, or where Roku shares a constraint with
Android TV that tvOS does not have:

- Roku draws its own focus on low-cost hardware;
- it has no blur, material, or live shadows;
- it uses platform keyboards.

Several Android TV controls use tvOS's point values as dp, which puts them at
twice tvOS's size on screen, so Roku does not take sizes from Android TV where
tvOS gives them. Section 5.9 lists every place Roku differs from tvOS, and
why; its rows marked "To build" are places where this section already
describes the target and the code does not match it yet.

The values below were read from silo-apple `b90a86ea` and silo-android
`0545b85de` on 2026-10-23. When tvOS changes a first-release screen, this
section changes with it. Screens outside the first-release scope are not
described. Where a deferred control has a fixed place on tvOS (Watchlist and
More in the detail action row; Collections in the library list; Trailers &
More above Details), Roku leaves that place free. The card captions and
detail cast and recommendations were checked against silo-apple `b514800f`
on 2026-10-25.

### 5.2 Design tokens

| Token | Value |
| --- | --- |
| Background | `#000000` |
| Surface / surface variant / raised surface | `#0A0A0A` / `#0E0F12` / `#15171C` |
| Text / secondary text | `#EDEDED` / `#EDEDED` at 60% |
| Hairlines | white at 12% (Details rows white 8%) |
| Resting chrome (chips, pills, menus) | white 7% fill, 1 px white 9% border; selected white 14% fill, white 10% border |
| Accent | none; the UI is monochrome. Errors `#FF6961`, warnings `#F4C869`, Sign Out the system red `#FF453A` at 90% |
| Progress bar | `#EDEDED` over white 20%, 3 px on tvOS (Roku 4 px, even for HD scaling), on the artwork's bottom edge |
| Font | Inter: Regular, Medium, SemiBold, Bold (Heavy and Black fall back to Bold, 5.9) |
| Side inset | 88 px for the top bar and Home hero; 80 px for row headers and Browse; 100 px on detail pages |
| Poster card | 176×264 px in rows; 260×390 in Browse; 240×360 in Search results |
| Landscape card | 360×200 px, for Continue Watching, in-progress, and "next" rows only (5.5) |
| Card gap / row spacing | 40 px / 10 px between rows (each strip has 14 px padding above and below) |
| Card corner radius | 12 px (detail episode stills 18) |
| Card focus | A lift with no ring (D4) over a shadow, black 50% with tvOS's 20 px radius, 10 px lower: posters grow 38 px in height as tvOS's card lift does (1.14 in rows, 1.10 in Browse), landscape cards scale 1.20, detail episode stills 1.08, each side by whole px, every edge of the lifted card on a whole pixel (5.9). The low tier keeps the list's ring without scaling (5.9) |
| Round button (detail, 76 px) | Rest white 10%, no ring; focused pure white fill with black content, no scale |
| Pill focus | Pure white fill with black text; the Sort pill and first-run buttons use `#EDEDED`. Scale: Sort 1.04, first-run buttons 1.06, fields 1.04, others none |

Type sizes in px (weight), named in `theme.textStyle`:

- Home hero: title 84 (Heavy), meta line 20 (Medium, secondary), synopsis 22
  (Regular, secondary), badges 15 (SemiBold).
- Rows and cards: row title 36 (SemiBold); card title 24 (Medium; SemiBold
  white when focused); card second line 20 (Regular).
- Top bar: tab label 26 (SemiBold).
- Detail page: title 92 uppercase (Black Compressed on tvOS; Roku 84 Bold,
  5.9); metadata line 24 (Medium); synopsis 26 (Regular); credit line 23
  (Regular); section header 36 (SemiBold).
- First run: headline 88 (Heavy); body 28 (Regular).
- Profile picker: title 64 (Heavy).
- Player: title 36 (SemiBold); series line 20 (Medium).

Inter is licensed under the OFL and is what Android TV ships. Roku ships four
weights, subset to Latin, Latin Extended, Greek, Cyrillic, and Vietnamese.
Timecodes use monospaced digits.

Generated player, detail, settings, search, watched-mark, and first-run symbol
assets use two raster pixels per logical FHD pixel. Their displayed sizes
and placement remain fixed by the components; the higher-resolution source
preserves edges when scaled. Stretchable backgrounds and focus rings retain
their existing HD/FHD assets.

### 5.3 Shell, top bar, and Back

- **Top bar.** It sits 56 px from the top, 64 px tall, with 88 px side insets
  and no background band. Left to right:
  - the Silo wordmark, 96 px wide;
  - then, centred on the screen, a 58 px Search circle, then Home, Movies,
    and Series, 8 px apart;
  - the 58 px profile avatar, at the right inset.

  The avatar, here and in its menu's header, is drawn as on the profile
  picker (section 5.4). A library tab appears only when the profile can see a
  library of that type. The bar appears on root pages only: Search is a pushed
  page without it (D3), and detail pages have none.
- **Tabs** are capsules 56 px tall with 29 px side padding and 26 px labels:
  - focused: a pure white fill with black text;
  - selected: a white 14% fill with a white 10% border;
  - resting: no fill, with labels white at 62%.

  The Search circle follows the same states. The avatar has no ring at rest;
  focused, it gets a 3 px white ring inside the circle and scales to 1.05. The
  bar dims to 70% over 0.2 s while focus is in the content.
- **Panels.** Resting 250 ms on Movies, Series, or the avatar opens that
  item's panel as a passive preview, with no row highlighted. Down or OK
  enters it. Moving to another bar item closes the preview. Panels are drawn
  as gradients from `#23252C` at 92% to `#141519` at 95% with a 1 px border
  from white 22% to 5%, radius 22 (the library flyout 18).
- **Avatar menu.**
  - Panel: 460 px wide, top at 132, right edge at the right inset, padding 14.
  - Header: a 44 px avatar; the profile's name in 24 px SemiBold; the
    server's display name in uppercase, 14 px, letter-spaced, at 38%.
  - Rows: Switch Profile, Settings, Switch Server, and Sign Out, 54 px tall (22 px
    SemiBold, 16 px inset), 10 px apart. A focused row gets a white fill with
    radius 14; resting labels are at 86%, and Sign Out is red at 90%.
  - A divider separates groups only.
  - Sign Out asks for confirmation (Sign Out / Cancel).
- **Library list** (Movies or Series).
  - Level 1: a 460 px column at y 132, centred under the tab and kept within
    88–1832 together with its flyout. Padding 14. Header ("MOVIE LIBRARIES"):
    14 px, letter-spaced, 38%. Library rows: 58 px (22 px SemiBold, 18 px
    padding), no spacing, radius 14. At most 6 rows show before the list
    scrolls.
  - Level 2: a 300 px flyout, 18 px to the right. Padding 10. Section rows
    Recommended and Browse: 50 px (20 px SemiBold), radius 12.
  - The flyout follows the highlighted library after it rests 150 ms, or at
    once on Right. Its first section row is centred on that library's row.
  - Up past the first row closes the list onto the tab. Down past the last
    row closes it and enters the content.
  - There is no hint line.
- **Moving between the bar and the content.** Down from Home's tab, or from
  the bar on Home, goes to the first row's first card and scrolls to the top.
  Up from the first content row moves focus to the selected tab.
- **Back** closes an open list or overlay first. From content on a tab page, it
  moves focus to the selected tab. On the bar it goes to the Home tab; on
  Home's tab it exits the app. On a pushed screen it returns to the previous
  screen.
- **Row scrolling.** Rows scroll as the focus moves, as on tvOS: focus moves
  along a row until it nears the screen's edge, then the row scrolls.
- On return to a screen, focus goes back to the same item in the same row.
  If the item is gone, focus goes to the same position, then the nearest row.
  When the target is on a page that hasn't loaded yet, focus waits for it.
  The item is the card focused when the screen was covered, found by its ID
  wherever its row now puts it, including when the row loads again after the
  return (Continue Watching puts the title just played first). As on tvOS and
  Android TV, neither the item a player played nor its series is used, and an
  item is not followed into another row. A move the viewer makes while focus
  is still waiting or on its way back wins: the restoration is dropped, so
  it never takes focus back from the card the viewer chose. Where new rows
  or items put the list's own ring (their first card, or the place it had,
  which run 14's TV kept after a quiet refresh) is not a move, so a viewer
  who lands on one of those places in the 50 to 150 ms before the jump
  takes still sees focus restored.

### 5.4 Setup, sign-in, and profiles

- **First-run layout.**
  - Background: the brand mesh (`#0034FB`, `#F50B4F`, `#FD7403`) over black,
    darkened on the left, as a packaged image.
  - Frame: padding 90 px at the sides and 60 px at the top. A 64 px top row
    holds the Silo wordmark, 150 px wide, on the left; on the server screen it
    also holds a chip with the TV's name on the right.
  - Below the top row: a 900 px column on the left and a 640 px card on the
    right (radius 40, `#1F1F1F` at 72%, 1 px white 14% outline), 80 px apart.
    They are centred in the space below the top row (centre y 572).
  - The column holds the whole form (D6). The card holds Roku help: the
    remote, or the Roku mobile app's keyboard, in place of tvOS's "Type on
    your phone". Message screens have no card.
  - Type: headlines 88 px Heavy, two or three lines. Body 28 px Regular at
    62%, 22 px below the headline.
  - Fields: 760×84, radius 16, text 30 px with a 30 px inset. At rest, a white
    8% fill with a 1 px white 12% outline. Focused, a `#EDEDED` fill with
    black text, scaled 1.04. In error, a 3 px `#FF6961` outline at 75%.
  - Errors: 24 px `#FF6961`, directly under their field.
  - Buttons: 76 px tall, labels 29 px SemiBold, 40 px side padding, sized to
    their labels, in one row 22 px apart.
    - Primary: a white 8% fill with a white 14% outline.
    - Plain (Back, Change server, Cancel): no capsule at rest, labels at 62%.
    - Focused: an `#EDEDED` fill with black text, scaled 1.06.
- **Server address.** "Enter your server address", "Type the address you use
  for Silo.", then the field (placeholder `media.example.com`). Then shortcut
  chips `https://`, `http://`, and `.com` (Android TV's; 5.9), a note line,
  then Connect and Back. An address without a scheme tries HTTPS, then HTTP.
  Before using plain HTTP, the client asks "Connect without encryption?".
- **Sign-in.**
  - A server card sits above the headline: an 80 px mark (the server's
    initial), the name in 34 px Bold, the address in 23 px at 40%, and a
    "SECURE" or "HTTP" badge. Padding 24, radius 30.
  - Headline "Sign in with a password"; body "Use your {server} username and
    password."
  - Username, then Password with a 76 px show/hide button beside it, then the
    error line, then Sign in and Change server.
  - A failure shows "Invalid username or password".
- **Server not ready.** When `GET /api/v2/system/setup` reports
  `needs_setup`, sign-in becomes tvOS's message screen: the server card with
  a "SETUP NEEDED" badge in the warning colour, "This server isn't ready",
  "Ask the server administrator to finish setup. When it is ready, check
  again.", then Check again and Change server. Check again reads the setup
  status once more ("Checking…" meanwhile): a server now set up goes on to
  sign-in; otherwise "This server still needs administrator setup." or
  "Couldn't reach the server. Check it's running and try again." shows 20 px
  under the body. The client offers no setup itself (section 3.4).
- **Profile picker.**
  - Heading: "Who's watching?" in 64 px Heavy; "Signed in as {username}" in
    28 px at 62%, 14 px below.
  - Grid, 84 px below: 220 px round avatars in 240 px columns 44 px apart, up
    to six per row, rows 60 px apart, centred.
  - Names: 30 px SemiBold, at 62% at rest and 100% when focused. They sit
    26 px below the avatar at rest and 44 px when focused.
  - Focused avatar: scale 1.12 with a 6 px `#EDEDED` ring 12 px outside it.
  - A profile without an image shows its initial on its colour.
  - Badges: PIN profiles carry a lock badge. Child profiles carry a KIDS badge
    (a white capsule with black text, top right).
  - Change server and Sign out, compact buttons 20 px apart, are pinned 60 px
    above the bottom edge, centred. The heading and grid are centred in the
    space above them. Sign out asks for confirmation (Sign out / Cancel).
  - A list that fails to load shows the error as section 5.8 does, with Try
    again.
  - Focus starts on the profile last opened on this device, else the first.
  - An account with a single profile and no PIN skips the picker.
  - Ordinary launches reopen the last profile chosen on this device without
    asking again (D5). Both other apps now ask on a new TV (5.9).
- **PIN.**
  - Full screen, over the mesh darkened by black 35%.
  - One centred column: the profile avatar (160 px); the name in 38 px Bold,
    14 px below; four 26 px dots 28 px apart, 34 px below the name; one
    status line 18 px under the dots; the PIN pad, 30 px below; Cancel (a
    compact plain button), 30 px below that.
  - Dots: an empty dot is a ring at 70%.
  - Status line: 34 px tall, 26 px text, reading "Enter your PIN" at 62%,
    "Checking…", or the error in `#FF6961` (a lockout gives the minutes left).
  - The PIN submits on the fourth digit. A wrong PIN turns the dots red. Back
    deletes the last digit, then cancels.

### 5.5 Home and libraries

- **Hero.** The top of Home is display-only and shows the focused card.
  - Backdrop: 1229×756 at the top right, filling its box. It fades
    horizontally from opaque at x ≥ 1527 to clear at x 691. Vertically it is
    opaque to y 287, then 88% at 393, 58% at 514, 24% at 612, and clear at
    680.
  - A full-width 190 px scrim, from black 50% to clear, sits under the top
    bar.
  - Wash (tvOS's ambient backdrop wash, silo-apple #829): three tints from
    the shown card's picture (its `backdrop_thumbhash`, or `poster_thumbhash`
    when the poster stands in), decoded at 12×12 and sampled as tvOS's
    `HeroBackdropPalette` samples: the average (base), the strongest hue
    weighted by saturation times value squared (accent), and the darkest
    quarter (shadow), each moved to luminance 0.22, 0.22, and 0.07. Where
    cards round their own corners (Roku OS 16 `Effect`, not the low tier),
    the base at 42% over black fills the whole page; the accent glows up
    from the page's foot, an ellipse 0.3 of the page across and high
    centred at x 1344, at 30%; the shadow pools in the bottom-left corner,
    0.42 of the page across and high, at 55%. Elsewhere only the base, at
    42%, fills the hero to y 287 and fades to black at the row band
    (y 596), above the cards' painted corners. The backdrop's fades blend
    the art into the base, and the colours change with the backdrop's
    0.24 s cross-fade. Without a ThumbHash the page stays black (5.9).
  - Once focus rests on a card, the backdrops and logos of the cards on
    either side are decoded ahead at the hero's sizes (not on the low
    tier), so moving to either shows them at once.
  - Text block: 880 px wide at x 88, its bottom at y 536 (D12: from the repo's
    tvOS screenshot; check it against a tvOS frame when one can be captured),
    with 14 px between items, top to bottom:
    - the title logo, fitted within 880×200; or the title in 84 px, at most
      two lines (always the text title when the profile turns title art off,
      `ui.title_art`);
    - a 27 px meta line in 20 px Medium at 60%: the content rating as a chip,
      then year · first genre · runtime · IMDb (else TMDB) score, and on
      Continue Watching "Nm left". Episodes read "S2 E7 · title · runtime ·
      Nm left";
    - the synopsis, 22 px Regular at 60% with 6 px line spacing, 780 px wide,
      three lines (two with a logo or a wrapped title);
    - a 27 px badge line of up to three chips: resolution, Dolby Vision or HDR,
      Atmos or the audio format. Chips are 15 px SemiBold, letter-spaced, at
      92%, on a white 7% fill with a white 24% border and radius 6.
  - tvOS's line for the air date and top three cast is deferred (section 3.3).
  - Text follows focus at once. The backdrop changes after focus rests 150 ms,
    with a 0.24 s cross-fade; the first backdrop appears without a fade.
  - With focus in the top bar, the hero keeps the last focused card: after the
    rows are read again, the same card wherever it moved.
- **Rows.**
  - Band: rows appear in server order, the band's top at y 596. The focused
    row aligns to that top, so one row and the top of the next show.
  - Header: 36 px SemiBold, one line. Cards start 34 px below it, 40 px apart.
  - Card shapes: landscape cards (360×200) for Continue Watching, in-progress,
    and any "next" section; every other row shows posters, including rows of
    episodes (section 5.9).
  - Captions sit 22 px under posters and 14 px under landscape cards. The
    title is 24 px Medium at 45%, white SemiBold when focused. A second line,
    4 px below it, shows the year for movies and series, or "S01E02 · Pilot"
    beneath an episode's series name. Metadata is 20 px Regular at 32%, white
    at 92% and Medium when focused. Both lines stay single-line and truncate
    at the tail; they drop together clear of focused artwork. Rows and grids
    reserve space for both lines and the focus drop. The low tier keeps both
    lines without scaling or dropping them.
    Focus does not change caption width, horizontal position, or font size.
    The vertical drop is 5 px under row posters and 13 px under landscape
    cards, matching tvOS's fixed 19 px overhang and 8 px clearance.
    Episodes use their own title when the series name is missing, omit an
    episode title that repeats the series name, and show whichever metadata
    is available (the code requires both season and episode numbers). Missing
    years leave the second line empty. This follows Apple TV's card captions
    at `silo-apple` revision `b514800f`.
  - Played items carry a watched check (a 40 px `#EDEDED` disc with a black
    check, 12 px from the top right; 14 px on landscape cards).
  - OK on any card opens the detail page; from Continue Watching, the detail
    page opens with that episode selected.
- **Library landing.**
  - A library tab opens on Recommended: the same feed as Home, built from the
    library's sections without its featured ones.
  - On a mixed library, each section shows only the tab's type.
  - Within a session, a tab reopens the sub-page it last showed.
- **Browse.**
  - Page: the Sort pill at (80, 248), then the grid 32 px below it. The grid
    has six columns of 260×390 posters, 40 px apart across and 60 px down.
  - Captions: centred, 16 px below the poster, with the same two-line title
    and metadata treatment as Home. The vertical spacing includes both lines
    and their focus drop.
  - Focus: entering Browse focuses Sort. Down goes to the first poster.
  - Sort pill: "Sort · Title A–Z", 24 px Medium, padding 22. At rest, a white
    7% fill and a 9% border. Focused, an `#EDEDED` fill with black text,
    scaled 1.04.
  - Sort menu: a centred 460 px panel over black 55%. Header "SORT BY" in
    18 px SemiBold at 60%. Rows are 57 px with 26 px Regular labels. A
    focused row is `#EDEDED` with radius 12, and the current sort shows its
    direction and arrow.
  - Sort options: Title, Date Added, Release Date, Year, Rating, Runtime, and
    Resolution. Choosing the active sort again reverses it.
  - Paging: the next page loads when focus is within eight rows of the end
    (five rows while memory pressure keeps three pages, so a page read at one
    end does not drop rows the other end then reads again).
  - Alphabet rail: All, #, and A–Z, beside the grid under every sort. A chosen
    letter stays when the sort changes. The rail sits 32 px from the right
    edge:
    - resting: an 18 px strip of 10 px letters at 35%, the current letter as
      an `#EDEDED` chip;
    - focused: 96 px wide, with 38×38 letter chips 4 px apart in 15 px
      SemiBold. Lit chips are `#EDEDED` with black letters; the others are at
      60%. No panel.
- **Collections.**
  - The Movies and Series library menus offer Collections alongside
    Recommended and Browse. Each opens the selected library's ordered
    collections, including profile-visible personal collections.
  - Posters show the collection title and a nonzero item count. Missing
    artwork uses the existing poster placeholder. Relative artwork resolves
    against the API origin; failed images retain that placeholder. One
    background renewal preserves the current navigation focus.
  - The server supplies the complete collection index. Roku retains only
    lightweight card metadata and materializes a bounded grid window.
    Groups retain server order, including the ungrouped section's declared
    position; empty groups are omitted.
  - A pill labeled "Collection groups" selects one group at a time through
    a scrollable menu. The ungrouped curated section is labeled "Server
    collections", distinct from "My collections".
    Opening a collection shows a paginated poster grid in server order;
    opening a title uses the existing detail page. Back restores the group
    and selected collection or title. Ordinary libraries retain all visible
    collection members; only a typed mixed-library view narrows membership.
    Empty and failed reads use the
    standard empty state or Retry.
  - These pages are read-only. Creating, editing, and deleting collections
    remain deferred.
- **Empty states.**
  - Home: "Nothing to watch yet" / "Add media to your libraries or start
    watching to see it here."
  - Library: "{Library} is empty" / "Add media to this library on the server
    to see it here."
  - Browse: "This library is empty" / "There is nothing in this library yet."
  - Browse with a letter that matches nothing: "No titles match your filters",
    with Clear filters.

### 5.6 Search and detail

- **Search.**
  - The Search circle in the top bar opens Search as a pushed page without the
    bar (D3). The keyboard sits in a column on the left, from x 80, and the
    results in a 1080 px column on the right, from x 760; both start at
    y 232 (5.9).
  - Once a query exists, a 760 px segmented control (All, Movies, Series)
    appears at the top of the results column (D7).
  - 48 px below it, "N results" in 22 px Regular at 60%. 48 px below that, a
    grid of four 240×360 posters across, 40 px across and 60 px down.
  - Queries run 300 ms after typing stops, with 40 results per page (5.9) and
    at most 200 characters. Choosing a segment runs the query again at once.
  - Copy: before a query, "Search Silo" / "Find movies and series"; with no
    matches, "No results" / "Try a different search term".
  - Right from the keyboard's right edge moves to the results, or to the
    filter when there are none to focus; Left from the results' first column or
    the filter's first segment returns to the keyboard. Focus on results
    that come back empty moves to the keyboard, and on a failed search to
    Retry. Back from the results returns to the keyboard; the next Back
    leaves Search.
  - Captions use Browse's two-line treatment: title and year, or series
    name and "S01E02 · Pilot" for episodes. Both lines truncate at the tail.
  - An episode result opens its series' page with that episode selected.
- **Detail hero.**
  - Frame: 690 px tall, 100 px side inset, text starting 116 px from the top
    in a 1080 px column. The backdrop, its fades, and its wash are the Home
    hero's (5.5). The ambient wash stays fixed behind the page as it
    scrolls; without it the wash reaches black at the hero's foot, y 690,
    above the first content below the action row. The logo decodes at
    Home's size, so a page opened from Home reuses the hero's bitmap.
  - Title: the logo, fitted within 650×160 (small logos are enlarged), or the
    title in uppercase, split at ": ", " — ", " – ", or " - " into a main line
    and a 40 px subtitle. The text title shows when the profile turns title
    art off (`ui.title_art`).
  - Below it, 14 px apart:
    - the metadata line, as tvOS's `factsRow` sets it: the content rating
      in Home's hero chip (5.5), then 14 px apart with a white 45% "·"
      between each two, in 24 px Medium at 88%: year (an episode's air
      date) · runtime or "N Seasons" · external ratings (the server's
      `ratings`: IMDb, RT, TMDB, as text) · first two genres ("Season N ·
      Episode M" on an episode). The genres give way first, ending in an
      ellipsis; a rating that still does not fit drops from the end;
    - the synopsis, 26 px Regular at 92%, three lines, 4 px line spacing (an
      episode's reads "Title · overview");
    - the credit line, 23 px Regular at 70%: "Directed by A, B" (movies, up
      to two directors) or "Starring A, B, C" (series, the first three cast);
    - the playback readout (below).
  - Action row: 20 px under the readout on a movie. On a series, the text sits
    in a fixed 435 px block, so the row stays at y 557.
- **Action row.** Play, or "Resume 1:02:03" ("Resume 12:34" under an hour), or
  for a series "Play S2:E3" or "Resume S1:E3", then Start Over when a resume
  point exists, then Versions, Audio Tracks, and Subtitles. Resume appears
  once the saved position passes 30 seconds and is more than 5 seconds from
  the end, whether or not the server counts the item played: the server
  zeroes the position when it marks an item played and keeps it played
  through a rewatch, so a played item with a position is a rewatch stopped
  partway, which both existing apps resume.
  - Play is a 340×76 pill on movies and series, its glyph and 29 px label
    always shown, its content centred, so the buttons after it keep their
    places as the active episode changes its label. At rest it is white 10%
    with white content; focused, a white fill with black content.
  - The other buttons are 76 px circles: white 10% at rest, no ring. Focused,
    they fill white and widen to show their 26 px label. Buttons are 18 px
    apart. On the normal tier, focusing a circle animates its width and
    neighboring button positions over 280 ms with cubic ease-in/out,
    approximating tvOS’s smooth curve with Roku’s native interpolator. Its
    label fades in over 180 ms after a 60 ms delay, and fades out over 80 ms.
    Rapid focus changes retarget from the current geometry. The low tier
    snaps to the same layout. A selector stays expanded while its menu is
    open, and the menu follows the button during expansion.
  - Focus starts on Play; Left and Right move along the row. Play and Resume
    start where the watch state says (section 5.7); Start Over starts at 0.
- **Version, audio, and subtitles.** As tvOS ships them (D1; silo-apple
  `b90a86ea`, `TVPlaybackSelectorRow.swift` and `TVDetailHero.swift`; the
  design spec's squared selector row with an Edition selector was not
  what shipped, and Roku ships no Edition control). On a movie, and on a
  series for its active episode, the three circles after Play and Start Over
  choose what the start plays, and a readout above the action row shows the
  choice. The readout takes no focus: the labels VERSION, AUDIO, and
  SUBTITLES at white 48% (23 px Bold), each followed 6 px later by its
  value at white 82% (23 px Medium), inline, 20 px from one value to the
  next label, within 1031 px, 44 px tall, 18 px above the row (5.9). When
  the line would pass 1031 px, the longest values share what is left and
  end in an ellipsis. Until the item's watch state is read, each value is
  a white 14% bar and the three circles are dimmed and passed over by Left and Right
  (tvOS disables them); once read, Versions and Subtitles always open, and
  Audio Tracks opens when the version has an audio track. Each opens its
  menu, tvOS's 560 px popover: 14 px under the button when its rows fit
  above the screen's 48 px inset, else 14 px above the readout when they
  fit there, else on the side with room for more rows, showing those and
  scrolling the rest, so it never covers the button or the readout (5.9).
  In it, the menu's name in capitals, then up to seven rows at a time,
  each a title over its detail,
  the current choice checked, the highlighted row white with black text.
  OK chooses, and Back, Left, or Right closes it, leaving focus on the
  button, which stays drawn focused while its menu is open. Track rows use
  tvOS's vocabulary (`TrackLabels`): a track's own title shows only when it
  says something its language, codec, layout, and flags do not.
  - Versions offers Auto ("Best match for this device") and every version:
    "2160p · HEVC · DV · TrueHD" (resolution, video codec, DV or HDR, audio
    codec) over its edition, video codec, container, and size ("Director's
    Cut · HEVC · MKV · 58.31 GB"). Auto plays the version the start path
    chooses (the one last played, else the server's default variant, else
    the first). The readout shows resolution and range: "Auto · 2160p · DV",
    or "1080p" for a version chosen. A version chosen is pinned: the start
    sends `allow_alternate_versions: false`, as tvOS does.
  - Audio Tracks offers Auto ("Use your Playback audio preference") and
    each track in the version's order, by language, with its title,
    codec, layout, Default, and Preferred (the server's
    `effective_audio_track_index`); under Auto the menu marks Auto and the
    track the readout names, as tvOS does. The readout names that track
    ("Auto · English · EAC3 · 5.1": the server's effective track, else the
    default, else the first) or the one chosen ("Japanese · AAC · Stereo").
    The effective track knows no device, so under Auto playback can start on
    another track in its language that the Roku plays unconverted (section
    9.7); the player's Audio tab names the track that plays.
  - Subtitles offers Auto ("Use your subtitle preferences"), Off ("Start
    without subtitles"), and each track in tvOS's order: the subtitle
    language the watch projection reports in effect
    (`effective_subtitle_language`, which a pick here can move to the
    series) first, the others by name, tracks without a language last, and
    within a language by format (SRT first, bitmap formats last), then full
    dialogue, forced, and SDH, the default first; Options' Subtitles list
    (5.7) has the same order and words (5.9). The readout names what Auto plays beside the audio in effect,
    by the profile's preferences (section 9.7) over the version's tracks
    ("Auto · English (Forced) · PGS", or "Auto · None"), "Off", or the track
    chosen ("English (SDH) · SRT").
  - Changing the version keeps an audio or subtitle choice the new version
    has at the same ordinal and otherwise goes back to Auto; Auto stays
    Auto, as tvOS re-resolves them.
  - An audio or subtitle pick that changes the choice is saved to the
    server's track preferences, for the series on an episode (D2, section
    8.5); picking Auto clears it, and OK on the value already chosen saves
    nothing (section 5.9). After Auto in Subtitles, the readout at once
    names what Auto plays without the subtitle the profile chose on the
    item; once an Auto pick's write lands, the page reads the item's tracks
    again and the readout follows what the server now resolves (5.9). The
    page starts each item on Auto, except where the profile chose before:
    the subtitle the server reports the profile last chose on the item
    (`effective_subtitle_track_signature`), or Off when its subtitle mode is
    off and forced subtitles are hidden, as tvOS seeds it; and the audio
    track the profile chose for the series or movie. A version lasts while
    the page does, as on tvOS; the server records the version played as
    `last_file_id`, which Auto plays next time.
  - Play, Resume, and Start Over start the version and tracks chosen
    (section 9.3); Auto leaves each to the start path. After the player
    closes, the page keeps the choice where the item still has it.
- **Series below the hero.**
  - Season pills: 52 px tall at y 694, 22 px text (SemiBold when selected),
    padding 24, 12 px apart. Selected: white 20%; resting: white 5%; focused:
    white with black text. No outline and no scaling. The selected pill is
    centred.
  - Season order: numbered seasons in order, then Specials. Resting on a pill
    switches to that season (after 300 ms on Roku; 5.9).
  - The episode rail is one row across adjacent seasons. The pill follows
    focus across a season boundary; a pill moves the row to its season.
  - Stills: 360×200, radius 18, 40 px apart. The first sits at x 116, and
    nothing shows left of x 100. The focused still holds the leading slot
    until the last one is fully visible.
  - Played episodes are dimmed by black 35% and carry a 40 px check disc. A
    5 px progress bar shows the resume point.
  - Captions, 18 px below: "S01E02 · Title" in 20 px SemiBold at 92% (100%
    when focused or current), over "Feb 18, 2026 · 52m" in 17 px Medium at
    60%.
  - A focused episode updates the hero's metadata line (series rating · air
    date · runtime · ratings · Season N · Episode M) and synopsis. The air
    date and runtime come from its card at once; its ratings follow when
    its item is read, once focus rests 150 ms (assumption AG-270). OK
    plays it.
  - On a series, Play targets the active episode: first the play target
    (section 8.3) or the episode card that opened the page (Continue Watching
    or a search result), in that episode's season, then the last episode
    focused; switching season makes its first episode active, as both
    existing apps do.
- **Cast and recommendations.**
  - After the hero on movies, or the episode rail on series, show Cast &
    Crew, then Related Movies or Recommended Series, then Details. Cast
    preserves server order and displays up to 24 people with 200 px
    portraits, names, and characters. Missing portraits use initials;
    entries without a person ID remain readable but cannot open a person.
    Focus follows Home's card treatment: a centred 38 px lift with a round
    shadow and highlighted captions, without an outline. The low tier uses
    an outline without lifting. Names wrap to at most two lines, with the
    character 6 px below; both captions stay clear of the lifted portrait.
    All supporting rails use floating focus: cards remain stationary until
    selection crosses the visible edge. Selection and viewport position
    survive Back and screen reconstruction. Poster cards use Home's
    ringless lift and shadow, or an outline without lift on the low tier.
  - Recommendations preserve server order, show up to 12 movie/series
    poster cards, and open the existing detail route. Their two-line captions
    are centred 16 px under each poster, dropping 11 px with the Home-style
    focus lift. Their request starts
    900 ms after primary detail loading; placeholders are not focusable,
    and empty or failed responses remove the whole section. Up and Down
    move between available sections; late responses do not take focus.
  - Selecting a person opens a panel containing their biography,
    birth/death information, and up to 24 visible movie/series titles under
    In Your Library. The biography displays at most six lines. Back returns
    to the selected cast card. Person errors stay within the panel and
    offer Retry for transient failures. Full person pages, pagination,
    external links, and metadata-refresh controls remain deferred.
- **Details.**
  - The header "Details" is 36 px SemiBold, 14 px above the table.
  - The table is one column, up to 1400 px wide. Labels are 260 px wide,
    uppercase 18 px Bold, letter-spaced, at 50%; values sit 64 px to the right
    in 22 px Regular. Rows have 22 px vertical padding and 1 px white 8%
    hairlines between them.
  - Rows: Director; Writer (or "Written by" without a Screenplay credit);
    Studio, Network, and Country (up to three names each); Genres (5.9); and
    the release or air dates in long form ("December 15, 1995").
  - The table is one focus stop, drawn with a white 6% fill.
  - Sections are 64 px apart, with 140 px below the last.
- **After the player closes** (D8). Focus stays on the same episode when it
  was stopped partway, a rewatch included. When this playback finished it
  (its video ended, Up Next was showing in its prompt window, or Skip
  Credits skipped credits that run to the end and playback was still in
  them), whether or not the server already counted it watched, focus moves
  to the next episode in play order, played or not. If that episode is in the next numbered season (by
  number, so gaps are skipped), the page shows that season. A finished
  finale stays, and play never moves into Specials. After Up Next played on,
  the same rule applies to the last episode played, and the page switches to
  that episode's season if the chain crossed into another.

### 5.7 Player

The player's chrome follows tvOS (D9), keeping Roku's caption modes in the
Subtitles tab (criterion 4.8).

- **Controls overlay.**
  - Gradient: covers the bottom 600 px, clear to black 94% with cubic
    ease-out coverage. It reaches about 72% behind the series line and 76%
    behind the title and episode tag, keeping all three readable over bright
    video without changing their size or placement (5.9).
  - Layout: left-aligned on the tvOS safe area, x 160 to 1760. Top to bottom:
    - on an episode, the series title in 20 px Medium at 65%;
    - the title in 36 px SemiBold, with "S1 · E2" in 20 px Regular at 60%
      10 px after it on the same line (a movie shows its title only);
    - the scrubber;
    - the time row;
    - the buttons.
  - Scrubber: 7 px tall, 12 px while scrubbing, white at 24% (35% focused,
    48% scrubbing) with the played part white. A 30 px knob shows while the
    scrubber is focused, or 42 px with an 8 px white 55% ring while
    scrubbing. Intro, recap, and credits ranges are bands (5.9).
  - Time row: elapsed on the left and "−12:34" on the right, both white,
    28 px SemiBold with monospaced digits. While the viewer scrubs or the rate
    ladder runs, both follow the position being chosen and change with it;
    cancelling returns them to the playing position.
  - Buttons: 66 px circles with no labels.
    - Left: skip back, play/pause, and skip forward, 10 px apart.
    - Right: Up Next (while it has something to show: a next episode or an
      On Deck item, or either still loading), Options, and Close.
    - At rest they are black 35% with a 1 px white 22% ring; focused, they are
      pure white with a black glyph, without scaling.
  - Focus: the controls open with focus on the scrubber.
  - They are not drawn while Options is open.
  - Captions: Roku's are hidden while the controls show and return as they
    hide (5.9).
  - Showing and hiding: a title starts on black behind the spinner, with
    the controls hidden and only Back working; from its first frame keys
    show them, and Left and Right skip. A stall later neither shows nor
    hides them. They hide 5 seconds after the last key unless playback is
    paused, buffering, or seeking, a seek is pending, or a panel is open.
- **Status and notices.**
  - A start, a stall, or a reconnection's reload shows the 128 px spinner
    (5.8) without text, centred on the picture (Up Next's frame while it
    shows, and 28 px under an open Options panel). It appears after 0.5 s
    of loading or buffering and stays at least 0.5 s.
  - Roku's own busy states (5.9) show by name with a small spinner in a
    capsule at the top right (y 124, right edge 1760), in 20 px Medium at
    82%, after 1.5 s.
  - Notices and Reconnecting show as a centred card at y 140, at most 760 px
    wide, radius 28, filled `#1A1A1A` at 88%. The card holds a symbol, a
    30 px SemiBold title, and a 24 px message at 72%, for example
    "Reconnecting…" / "The connection to the server was lost. Playback will
    continue where you left off."
  - Notices draw over the Options panel. The busy capsule moves to y 560
    while Options is open.
  - The buffering-quality pill and its prompts are deferred (section 3.3).
- **Options panel.**
  - Tabs: pills above the panel, centred at y 92, 12 px apart, 22 px
    SemiBold, about 46 px tall. The active tab is white with black text, and
    stays white while focus is in its pane. Other tabs are black 45% with a
    1 px white 18% ring.
  - Panel: 14 px below the tabs, 1100×380, padding 28/22, radius 28, filled
    `#1A1A1A` at 88%, with a 1 px white 14% stroke.
  - Tabs shown: Info, Stats, Video, Audio (when the version lists audio
    tracks), and Subtitles (always on Roku; 5.9). When an update drops the
    tab shown, the tab that takes its place (else the last) shows.
  - Columns: each tab is laid out in columns 48 px apart, each under a 14 px
    SemiBold uppercase header at 50%.
    - Info: TITLE (series, title, "S1 · E2", "2024 · 1h 42m", overview,
      which takes the whole lines left, the last ending in an ellipsis) and
      STREAM (resolution, HDR, codec, and audio badges, then Route, Audio,
      and Subtitles rows).
    - Stats: two columns of the plan's and player's non-secret state.
    - Video: PLAYBACK and SYNC.
      - PLAYBACK holds the Quality row, shown only when the plan offers a
        choice beyond Auto and source aliases. Its value is the checked
        choice ("1080p (8 Mbps)"); with no row checked, the session's
        quality preference as tvOS names it ("Up to 1080p HD", "4K"), so it
        reads Auto only while Auto is checked; "Switching…" while a switch
        runs. OK opens a 620 px picker centred in the panel, over the pane
        dimmed to 28%, with the tabs clear above it: four whole rows at
        most, 24 px Medium, the checked row washed white 14% with a check
        (black on the focused row), opening on the checked row near the
        middle. Each entry is named by its display name, else its label.
        The check, as tvOS lights a row: Auto under an Auto preference;
        else the plan's `active_quality`; else the row a preference names
        exactly (a rung chosen here). A saved resolution under a plan that
        reports no rung checks nothing.
      - SYNC holds the Auto-play next toggle for episodes, which lasts for
        the session.
    - Audio: TRACKS, each track's own title cleaned as the detail Audio
      Tracks menu cleans it (5.6), and OPTIONS (Channels, Codec).
    - Subtitles: TRACKS (Off, then the plan's tracks) and CAPTIONS (Roku's
      caption modes, section 9.7 and 5.9). The tracks are in the detail
      Subtitles menu's order and words (5.6): the watch projection's
      `effective_subtitle_language` first, the other languages by name,
      those without one last, and within a language SRT, ASS, SSA, WebVTT,
      TX3G, PGS, then the rest, full before forced before SDH, the default
      first (tvOS's `SubtitleDisplayOrder`). A track only the plan lists (a
      sidecar the projection does not name) takes its language's place
      here and is not in the detail menu, as on tvOS.
  - Rows:
    - A track row has its language first in 22 px Medium, then a second line
      of title · format · Default · Forced · SDH in 17 px at 55%. It is about
      72 px tall.
    - A setting row is 48 px.
    - A focused row has a white fill with radius 10.
    - A check at the right marks the current choice.
    - A column shows whole rows only; it scrolls to keep the focused row in
      view, with a row's top at the column's (5.9).
  - Opening:
    - Options opens on the tab used last in this player (Info the first
      time).
    - Down with the controls hidden opens Video.
    - `*` reaches the panel only on Roku players that pass the key on
      (section 5.9).
  - Keys: Left and Right move along the tabs. Down enters a tab's first
    column on the row last focused there; Left and Right move between
    columns; Up from a column's top returns to the tabs. Back closes the
    picker first, then the panel, at the first press, wherever focus is.
  - After a pick, the panel stays open with focus on the row, as in both
    apps, whether the new plan switches in place or reloads the title, and
    the panel keeps focus across the reload.
- **Remote keys.**

  | Roku key | Controls hidden | Controls shown |
  | --- | --- | --- |
  | Left / Right | Skip back / forward on release (the profile's values, default 10 s / 30 s); hold 300 ms for the rate ladder | On the scrubber, skip and hold as when hidden; elsewhere, move focus |
  | OK | Show controls | Activate the focused button; on the scrubber, commit a pending seek, else toggle play/pause |
  | Up | Show controls | Move focus |
  | Down | Open Options on Video | Move focus to the buttons |
  | `*` (Options) | Roku's caption and audio overlay: the `Video` node keeps focus (implementation plan section 6.10) | Open Options on Video on a Roku player that passes the key on; a Roku TV opens its own menu instead (section 5.9) |
  | Play/Pause | Toggle | Toggle; while a seek is pending, commit it and resume |
  | Replay | Skip back by the skip-back value clamped to 10–25 s (criterion 4.9) | Same |
  | Rewind / Fast-forward | Start the rate ladder; each press steps up | Same |
  | Back | See below | See below |

  Rapid skips merge into one seek 200 ms after the last. Holds are timed from
  the press and release Roku reports, never from key repeats. Play that
  commits a seek while paused resumes with it, so a load the seek opens (a
  credential renewal's reload, a reanchor) plays, while OK's commit stays
  paused; Play/Pause leaves alone content that a newer load is about to
  replace (hardware run 9).
- **Rate ladder.** Speeds are 1, 2, 4, 8, 16, and 32× each way. Every 100 ms
  the position moves by speed × 2 seconds. Holding climbs 1→2→4→8 every 1.2
  seconds, and taps step up or down: the ladder is signed, so a tap against
  its direction steps down and a step past 1× reverses. After the release it
  runs on at its speed. OK (or Play) commits the new position; Back cancels
  it; Up and Down do nothing meanwhile. The rate chip sits at the scrubber's
  right end, its top 62 px above the scrubber's centre line (tvOS's 34 pt
  over the scrubber's 56 pt box): a 36 px white capsule with a black glyph
  and "2×" in 18 px Bold. A hold, or Rewind or Fast-forward, with the
  controls hidden runs the ladder without them and shows tvOS's top-centre
  indicator: the 480 px thumbnail at y 180, the direction, rate, and time
  in a chip under it, a 520 px progress line, and the keys' hint.
- **Seek previews.** While the viewer scrubs, with Left/Right or at any
  rate-ladder speed, a 340 px card shows above the scrubber, centred on the
  scrub point and kept within the scrubber's ends. The card holds the
  thumbnail at 320×180 (radius 14) with the time under it in 24 px SemiBold,
  has radius 20, and is filled `#1A1A1A` at 88%; the title hides meanwhile.
  Thumbnails come from the server's trickplay sprite sheets for the file
  playing. A title without them shows the time where a thumbnail's would be,
  under "Previews aren't available for this title".
- **Back, first match wins:** cancel a seek or scrub; dismiss Skip Intro's
  pill; from Up Next, Keep Watching (tvOS); close the Quality picker, then
  Options; hide the controls while playing; otherwise stop and exit. The
  segment pill (Skip Recap or Skip Credits) stays through Back, as tvOS's
  stays through Menu (assumption AG-291).
- **Skip pills.**
  - The profile chooses never, ask, or always for intros (default ask).
  - Skip Intro is a 72 px pill at the bottom right: right edge 1760, bottom
    156 px from the screen's bottom, or 460 px while the controls show. Its
    label is 28 px SemiBold at 62%. At rest it is black 65% with a 2 px white
    25% border; lit, it is white with a 3 px white border, scaled 1.06. A fill
    grows from left to right over 5 s and pauses while playback is paused.
  - Always skips, then shows "Intro skipped" in 22 px at 72% above a Watch
    Intro pill for 5 s.
  - Recaps and credits share tvOS's segment pill (76 px, compact): "Skip
    Recap" while playback is inside a recap, "Skip Credits" inside credits,
    Skip Recap first if both apply. It shows once the title has played its
    first frame and stays while playback is in the range. Recaps are
    skipped automatically when the profile's `playback.auto_skip_recap` is
    on (D10), credits when `playback.auto_skip_credits` is on (default
    off); a range skipped automatically is not skipped again when the
    viewer seeks back into it, or in Keep Watching's replay of the end, and
    the pill shows there instead.
  - Skip Credits seeks to the end of the credits. Credits that run to the
    end of the file (ending within 0.5 s of the runtime, or past it) open
    Up Next instead, as tvOS does: the credits keep playing in Up Next's
    video box, its countdown is 10 seconds, and the title counts as
    finished (section 5.6) while playback stays in those credits, after
    Keep Watching too. With nothing for Up Next to show, the skip seeks to
    the end, and the end opens Up Next as Finished.
  - The pills are focusable while the controls show and take focus as they
    appear. The segment pill is not drawn while Up Next shows, as tvOS
    hides its controls there.
  - As on Android TV, each intro range is offered once per title: Skip Intro,
    Watch Intro (which seeks back to the start), Back, or Watch Intro's 5
    seconds running out settle it for good, while an Ask pill whose time ran
    out comes back only after playback leaves the range and returns. A skip
    is a seek like any other (local or `seek_reanchor`).
- **Up Next**, as tvOS's Next Up screen. It opens for movies and episodes
  alike, inside the last `playback.next_up_prompt_seconds` of the runtime
  (default 30, 0 for never), whenever it has something to show; a resume or a
  seek into that window opens it too. It does not open at the credits marker,
  only when Skip Credits skips credits that run to the end (above).
  It offers an episode's next episode; with none (a movie, a series finale),
  the first On Deck item is the pick instead, unless the next-episode lookup
  failed. The countdown is the runtime left, its ring counting from the
  prompt window: it stops while paused, and the pick starts as it reaches
  the end. A seek the viewer makes while it shows, spoken or from a phone
  (the remote's keys are the panel's), is Keep Watching first, so no
  countdown, over skipped credits included, starts the next item after it;
  after the end such a seek plays the title again from there. The video's
  end always opens Up Next, as "Playing Next", or as "Finished" with "End of playback" and why
  there is nothing to play; an end with Up Next already counting starts the
  pick at once, and otherwise a 10 second countdown runs. While the
  next-episode lookup runs, the panel says "Finding the next episode". The
  controls' Up Next button opens it with no countdown until 100 seconds are
  left, then one from 100. Keep Watching and Back close it until playback
  leaves the prompt window (a seek back), and turn the countdown off for
  that opening; after the end they play the last 10 seconds again (Back
  leaves the player instead when there is nothing to play), which
  stay dismissed while inside the window, so with the default window the end
  that follows opens without a countdown (a window under 10 seconds starts
  the replay outside it, and entering it counts down again, as on tvOS).
  Play/Pause is Play Now.
  Auto-play needs the profile's `playback.auto_play_next`, Roku's autoplay
  setting, and the panel's toggle, which writes `playback.auto_play_next`
  for this device and starts or stops the countdown at once. The next item
  starts where its watch state resumes, in the same player, so Back from it
  returns to the page the first item was played from, which then selects
  the last episode of that series played (section 5.6). On Deck is the
  profile's Home sections Continue Watching, In Progress, and Next Up, in
  server order, without the playing item, its series, or a repeat, up to 12;
  its row shows all of them but the pick, as Home's landscape cards with
  their progress (episodes with their own still), and OK on a card plays it
  as the viewer's own start. Layout:
  - a 1560 px column centred on the screen, its top at y 112;
  - the video in a 760×428 box at x 180, with radius 8 and a 1 px white 16%
    outline;
  - the panel at x 980, 760 px wide, centred vertically against the video.
    Top to bottom:
    - "UP NEXT" or "PLAYING NEXT" ("MORE TO WATCH" or "FINISHED" with
      nothing to play), 18 px SemiBold at 52%;
    - the series title, 34 px Bold;
    - "S1:E2" at 62% followed by the episode title, 25 px SemiBold, on one
      line (two at most); a movie's title alone, 34 px Bold;
    - the air date · runtime, 19 px Medium at 46% (an On Deck pick's
      runtime alone, as tvOS has no air date for it);
    - the overview, 22 px Regular at 58%, three lines, 620 px wide;
    - Play Now, a 76 px pill 260 px wide at rest and 360 px focused, with a
      58 px countdown ring (3 px) 56 px to its right;
    - 18 px below: Keep Watching (330 px) and Back (200 px), 20 px apart;
    - 22 px below: the toggle "Auto-play is On/Off", text only, 19 px
      SemiBold at 54% (92% with a 1.5 px outline when focused).
    - With nothing to play, "Almost finished" or "End of playback" (42 px
      Bold) and its reason (22 px Medium at 62%, 560 px wide) in place of
      the metadata, and no Play Now or toggle; while the lookup runs, a
      spinner and "Finding the next episode" (42 px SemiBold).
  - 34 px under the taller of the video and the panel, the On Deck row: its
    header at x 180, tvOS's play.circle.fill (32 px) 14 px before "On Deck"
    (36 px SemiBold), then 44 px to Home's 360×200 landscape cards, 40 px
    apart, four across the column; focus moves across them and the strip
    scrolls past the fourth or the first, and home when focus leaves. With
    focus in the row, the screen moves up until its captions clear the safe
    area, the video's box with it. Down from the buttons goes to the toggle,
    then the row; Up from the row to the toggle, else the first button; Up
    from the toggle to Play Now.
  - The rest of the screen is black (5.9).
- **Resume.** The player never asks whether to resume. The detail page's
  Resume and Start Over buttons decide. Resume starts 7 seconds before the
  saved position, the default of the device-local
  `player.resume_rewind_seconds` setting. The start reads the saved position
  by the rule the detail page's Resume shows (section 5.6), played or not,
  and sends it as `start_position`; Play on a saved position of 30 seconds or
  less starts there too, as both existing apps do. With no saved position, or
  one within 5 seconds of the end, the start omits `start_position`. When
  Roku starts an HLS load more than 3 seconds past the plan's
  `player_start_seconds` (or a reload's position), the player seeks back
  there once (hardware run 8) and logs whether it landed, from the first
  position once the node plays again after the seek's rebuffering, or 3
  seconds after the seek (Roku reports position 0 while it rebuffers, run
  10). That seek is not the viewer's: playback does not count as seeking
  meanwhile, and a seek the viewer makes replaces it. In hardware run 9 it
  never landed (Roku rebuffered and played on from the late position); the
  fix is the server's (a complete playlist at start, or `#EXT-X-START`).
- **Waiting and errors.** The spinner shows while the player buffers, and
  the Reconnecting card while recovery (section 9.6) runs. A failure shows,
  centred, a 40 px warning triangle in `#B00020`, the message in 26 px
  Regular, then buttons 16 px apart, 62 px tall with 28 px SemiBold labels:
  Retry ("Try again" when the connection was lost), "Try Anyway" when the
  server can't be reached (no answer, or a gateway's `502`, `503`, or `504`:
  a reverse proxy in front of a stopped server), and Go Back. There, as on
  Android TV, Retry first checks the server (`GET /api/v2/system/info`) and
  keeps the message while it is still unreachable, and Try Anyway starts a
  new attempt at once. A failure that can't be retried shows Go Back only.

### 5.8 Loading, empty, and error states

Each screen's loading state:

- Home: an empty page that takes focus, as on tvOS.
- Detail: opens at once with the opening card's backdrop, logo or title,
  metadata, and synopsis. Placeholder blocks (white 10%) stand in for the
  actions and the rail until the page loads.
- Library Recommended and Browse: a centred 128 px spinner, which never traps
  focus. tvOS draws skeletons here (5.9).

A screen-level error shows a centred stack: a 48 px warning triangle in
`#B00020`, the message title in 36 px SemiBold 48 px below it, the message in
26 px at 60% 48 px below that, and Try Again 64 px under the message. Empty
states use a 28 px SemiBold title 12 px over a 22 px line at 60%. Screens draw
both with `StatusView`'s `kind` (`"error"` or `"empty"`). A Home or library
row that fails to load is left out, as Android TV does, and the other rows
stay usable.

### 5.8.1 Settings

Settings opens from the avatar menu. It follows `TVSettingsView` on tvOS and
`SettingsSplitLayout` on Android TV: a left rail with the active profile,
General, Playback, Subtitles, Server, Sign Out, and the app version; the right
pane shows the selected category. Entry focuses General. Up/Down changes the
rail selection or the focused setting; Right/OK enters the pane; Left/Back
returns to the rail; Back from the rail restores the originating avatar.
Profile and server actions reuse the existing screens, and Sign Out reuses
its confirmation. Pickers open over a dimmed screen with the current value
selected; Back dismisses without saving. Audio Guide announces the focused
label, value, and scope. Lists keep only a bounded window visible.

At 1920×1080, the rail is 490 px wide from x=108 and the detail content
starts at x=646, on black with no divider, as tvOS draws it. The page title is
48 px Bold. The rail's profile row shows a 68 px avatar, the name (27 px
SemiBold), the server's host (19 px), and a chevron; each category shows an
icon, its name (25 px Medium), and a one-line description (16 px at 62%); Sign
Out has an icon. The pane header puts the category's icon in a 72 px graphite
tile (`#3A3A3C`) beside its title (42 px Bold) and description. Rows are
26 px Regular with values 24 px Regular; at rest each sits on a card (white 7%
fill, 1 px white 9% border, radius 14), and rows that open a picker or screen
end in a chevron. Section headers are 19 px SemiBold and footers 20 px
Regular. Focus fills the row with the existing light Silo focus color, and
Sign Out with its red; the selected rail category retains a dim fill while
focus is in the pane. The icons are generated by `scripts/settings-art.py`.
The existing option-list component is centered for Settings and retains its
seven-row scrolling window.

- General: Show Title Art.
- Playback: Resolution, Maximum Bitrate, Audio Language, Auto-Play Next
  Episode, Skip Intros, Skip Credits, Auto-Skip Recaps, Skip Back, and Skip
  Forward.
- Subtitles: Language, Behavior, and Show Forced Subtitles. A footer points
  to Roku's caption visibility and appearance controls.
- Server: the connected server address and Change Server; app version is
  always visible in the rail. No server administration controls.

Platform differences: Roku exposes only controls already consumed by its
player and shell. It does not expose Apple/Android decoder switches, caches,
poster/layout customization, subtitle appearance, or other unsupported
features. Subtitle defaults can be overridden for this Roku and reset to the
profile, rather than editing only the roaming profile as the tvOS pane does.
Settings apply to subsequent playback sessions; title art updates existing
heroes immediately. Roku's three-consecutive-episode limit stays fixed.

### 5.9 Roku differences

Each row is a place Roku differs from tvOS (or, where tvOS is silent, from
Android TV, named), with its reason. A reason that reads "To build: WPn"
marks a place where sections 5.1–5.8 already describe the tvOS target
(decisions AG-222) and the client does not match it yet: the row describes
Roku as it is, and the work package that builds the change deletes the row.

| tvOS (or as named) | Roku | Reason |
| --- | --- | --- |
| QR or device-code sign-in is the default; password is the alternative | Password sign-in, or a code shown only when a Silo phone app on the network offers to sign the Roku in (companion sign-in) | Certification criterion 2.2 (section 7.2) |
| "Set up with your phone" and network discovery lead server setup | Address entry, or a Silo phone app pushes the server (companion sign-in); no discovery of servers | Discovery deferred (section 3.3) |
| The TV's remote-control standby screen takes over while a phone is connected | No Connect a Phone entry is exposed in the avatar menu; the pairing route remains implemented. A phone connecting shows "<phone> connected" for four seconds and nothing else changes | The avatar menu omits the pairing entry for the first release. Roku apps cannot be opened by a phone (no ECP from phone apps), so there is nothing to stand by for; `docs/silocontrol.md` section 4 (every build since decision D-7) |
| A phone's profile handoff shows a "Playing as" card for six seconds | The player's notice card says "Playing as <profile> · From <phone>" for four seconds | The notice card is the player's one non-focusable card; `docs/silocontrol.md` section 4.2 |
| The sign-in screens offer phone sign-in over TLS (`_silopair._tcp`) and show the code in their own card | A phone push opens a Companion screen over the server or sign-in screen: Allow / Don't Allow, the check, then the code and match words; the card says "Use your phone"; the service is `_silopair-roku._tcp` over plain TCP | Roku has no TLS on listening sockets, and the sign-in screen shows no code until a phone asks for one; `docs/companion-pairing.md` |
| Custom PIN keypad | Roku `DynamicPinPad` inside the same layout | Criterion 4.12 requires Roku keyboards for PINs |
| Platform or custom text fields | Roku dynamic keyboards, with voice entry | Criterion 4.12 for credentials; Roku's standard for search |
| tvOS's keyboard is full screen; Android TV's rises over the lower screen | A `DynamicKeyboard` panel covers the screen, with the address chips, Show/Hide, and Done below it | Roku sizes `DynamicKeyboard` itself; the panel keeps the text, voice entry, and shortcuts together |
| The scheme shortcuts sit behind an Advanced options toggle | Chips `https://`, `http://`, and `.com` always show under the field (Android TV) | Typing a scheme on a Roku remote's keyboard is slow; the chips are one press each |
| A welcome step leads to address entry, and Back returns to it | Address entry opens first; its Back button shows only when Change server opened it, and the remote's Back exits | Nothing comes before address entry on Roku: server discovery is deferred, and a phone sets the Roku up from address entry itself (companion sign-in) |
| "Connect without encryption?" appears once the HTTP address has answered (Android TV) | It appears before the first plain-HTTP request | The setup check stores a server as soon as it answers, so the viewer agrees first |
| An older server is an inline error on address entry | A "Server update required" screen, whose Change server returns to the typed address | Section 7.1 |
| A server without password sign-in offers only the code | An explanation with Try again and Change server | Section 7.2; Roku allows no off-device sign-in |
| Both apps ask "Who's watching?" on a new TV and offer "Open {name} automatically?" after the first pick (tvOS since `03a937c7`) | The profile last chosen on this device reopens at launch, with no offer | Decision D5 (AG-222): the first release has no profile-at-launch setting to change the answer later (sections 5.4 and 7.3) |
| A PIN lockout shows the server's text (Android TV) | The minutes left from `Retry-After`, as tvOS words them | Section 7.3 |
| The brand light drifts slowly | A still image of the same mesh at rest | Packaged art (section 5.4) costs no frame time on low-memory devices |
| Preset (SVG), emoji, and DiceBear avatars are drawn | The name's initial on the profile's colour | Roku cannot draw SVG or colour emoji, and the client does not rewrite avatar URLs |
| The top bar's avatar and the avatar menu's header draw a profile without an image as its initial on white at 16–18% | The initial on the profile's colour, as on the picker | One avatar drawing from the picker to the shell keeps a profile's colour after the picker (parity review P-17) |
| Avatar images are round everywhere | Square on devices without OpenGL | `MaskGroup` does not clip there (implementation plan section 4.6) |
| The PIN screen's avatar is a near-black disc with the initial in `#EDEDED` | The profile's colour, as on the picker | One avatar drawing from the picker to the shell (parity review P-17) |
| The brand light changes stage for sign-in and for the profiles, and takes the server's accent or the colour of the profile being opened or PIN-checked | Setup, sign-in, and messages share one mesh, the picker and PIN another, without a server's or profile's colour | Each stage or colour would be another packaged image of about 60–80 KB |
| The card beside a text form says "Type on your phone" (a keyboard on nearby iPhones and iPads) | It says "Use your phone": open Silo on a phone to sign the Roku in, or type with the remote or the Roku mobile app's keyboard (D6) | tvOS's phone keyboard has no Roku counterpart; companion sign-in takes its place |
| Fields lead with an icon (globe, person, lock), inline errors with an exclamation mark, and Show/Hide is an eye; the server badge, the TV's chip, and the picker's buttons carry icons | Text only; Show/Hide is a text button as wide as its longer label | No icon art ships for them |
| The server card names the server (its branding or system name) over its host, and its mark can be the server's logo | The host over the server's URL, and the host's initial on the warm tile; over setup, the update screen's card shows the host just checked | The session keeps only the server's origin (section 7.1), and server branding is not read |
| "This server isn't ready" marks its server card with a server glyph on a dark tile | The host's initial on the warm tile, as on sign-in | No icon art ships for it |
| First-run headlines and the picker's title are set 2 px and 1.6 px tighter than the font | Inter at its own spacing | Roku `Label` has no letter-spacing field |
| Compact buttons (the picker's buttons, PIN's Cancel, the address chips) are 57 px tall | 56 px, the top bar's tab capsule | Even heights scale to HD without half pixels, and the art is shared |
| Sign Out's confirmation also offers "Sign Out & Remove Server" | Sign out and Cancel, in the avatar menu and on the picker alike | Roku keeps one server: Change server replaces it, and several saved servers are deferred (section 3.3) |
| The picker loads behind the wordmark, a spinner, and "Loading profiles…" on black | The 128 px spinner over the brand light | One spinner serves loading the list and reopening the last profile, so the screen does not change between them |
| A list that fails to load shows the error with Try Again only | The error with Try again, and Change server and Sign out pinned below | An account the server refuses (a password that must change) has no Try again; the buttons are its only way out |
| A profile that fails to open leaves the picker as it was | The account line shows the error in `#FF6961` until the next choice | Without it, OK on a profile would seem to do nothing |
| Try Again on an error state rests as a light pill (`#EDEDED` at 72%, black text) | The first-run button: glass at rest, `#EDEDED` when focused | Roku draws its own focus, and a light pill at rest would read as focused |
| A wash from three tints sampled from the backdrop (base, accent, shadow): on Home the base runs from full at the top right to 18% at the bottom left; on detail the base at 42% fills the whole page; the accent and shadow glow under the rows on both | The tints sampled from the backdrop's `backdrop_thumbhash` decoded at 12×12, not from its pixels. Where cards round their own corners (Roku OS 16 `Effect`, not the low tier), the base is flat at 42% on Home as on detail, with the accent and shadow glows. Elsewhere only the base, at 42%, fills the hero to y 287 and fades to black at Home's row band (y 596) and at the detail hero's foot (y 690); the rows sit on black. Without a ThumbHash the page stays black | BrightScript cannot read image pixels. A full-screen texture or shader gradient under the rows cost the Ultra 4850X about 10 fps of row scrolling (median 59.9 to 47–50), where a flat Rectangle costs none. Cards' rounded corners without an `Effect` are painted black by a 9-patch frame (plan section 4.6), so there the wash ends above the first cards (AG-253, AG-292, AG-317) |
| SF Pro, and SF Mono for small uppercase headers | Inter, as on Android TV | SF Pro and SF Mono cannot ship outside Apple platforms |
| Heavy and Black titles; the detail title in Black Compressed at 92 px | Inter Bold; the detail title at 84 px | Package size: four weights only, and Inter ships no compressed width at that weight |
| Letter-spaced small text (badge chips, uppercase headers) | Spacing approximated with hair spaces (`theme.tracked`) | Roku `Label` has no letter-spacing field |
| System fonts cover every script | Titles in scripts outside Latin, Greek, Cyrillic, and Vietnamese (for example CJK and Arabic) render as boxes | Neither the packaged Inter subset nor Roku's system font covers them, and a CJK font does not fit the 4 MB package |
| Panels, buttons, cards, and the hero's title cast soft shadows, and a focused card's caption glows; focused controls change over 120 ms or more | Cards use a shadow 9-patch (5.2) and lift with the list's own focus animation; panels open with tvOS's 0.12 s fade; panels, buttons, and the title have no shadow, captions no glow; detail action circles animate width and label reveal on the normal tier (5.6), while the low tier snaps | Roku has no blur, and animations cost frames on 512 MB devices |
| Focused cards lift on every device | On the low tier, cards do not scale and the list draws a 9-patch ring | Plan section 4.6: frame rate on 512 MB and non-OpenGL devices |
| Cast and recommendation cards use an outline and a smaller scale than Home | Detail supporting rails use Home's ringless lift and caption highlighting; cast retains round portraits and a round shadow. Low-tier cards keep an outline without lifting | Consistent focus treatment across Roku's Home and detail rails |
| A focused card scales by one factor (a poster 1.14) about its centre | Each side grows by whole px, so the two axes differ slightly: a row's poster lifts to 202×302, Browse's to 286×428, Search's to 266×398, a landscape card to 432×240, a detail episode still to 388×216. The card scales about its top-left corner and moves back by that lift (a landscape card 36 and 20 px), so its left and top edges are whole px exactly | At a fractional edge Roku drew the art a pixel past the 9-patch frame that rounds the corners, a white line down a lifted card's right edge (hardware run 26). Scaled about its centre, a float's 1.2 put the first Continue Watching card's left edge at x 43.99998, and Roku drew its progress bar, a Rectangle, from x 43, a tick left of the frame's corner (runs 26 and 27) |
| The detail Subtitles menu leads with the profile's subtitle language; the player's list with the watch projection's effective subtitle language | Both lead with the projection's `effective_subtitle_language`, so the detail menu and Options' Subtitles list the same tracks in the same order and words. Each lists its own source, as on tvOS: the detail menu the version's tracks, Options the plan's inventory, so a sidecar only the plan names shows only in Options | The two lists disagreed on hardware run 27: Options listed the server's order and hid titles the detail menu showed. A detail pick is an ordinal into the projection's list, so the detail menu cannot offer a track the projection does not name |
| A subtitle's title shows unless it is a release name, a format, a flag, or its language | A title that is a subtitle file's name ("Heat (1995).en.srt") is dropped too, on the detail menu and in Options | The server gives an untitled sidecar its file's name as its title and its inventory label (hardware run 6) |
| Avatar menu rows have an icon before the label | Labels without icons | No icon art ships for the menu |
| The library list marks the current library with a check mark and gives each library and section an icon; the sort menu checks the current sort | The current library has the selected tab's white 14% fill, without icons; the current sort shows only its direction and arrow | The packaged Inter subset has no check mark, and no icon art ships |
| Switching tabs cross-fades the page over 200 ms while the top bar stays | The new page appears at once | Each root page draws its own top bar (one root page alive, plan sections 4.5 and 4.7), so fading the page would blink the bar |
| The hero's logo shows as soon as it is decoded | The logo loads once focus rests 150 ms on the card, with the backdrop; the text title shows until then | Decoding a logo for every card passed while scrolling churns texture memory on 512 MB devices |
| The hero's meta line shows the IMDb or TMDB mark before the score | The source's name as text ("IMDb 8.3") | No logo art ships for rating sources |
| Runtimes read "45m" and "1h 0m" | "45 min" and "1h", as Android TV writes them | The `catalog.` runtime strings serve Home, detail, and Up Next alike; a copy change of its own moves them |
| Cards carry resolution, HDR, audio, and release-type overlays | No overlays | The node budget per card (plan section 4.6); the server's overlay preferences are not read |
| A row whose items are all episodes, seasons, or series shows landscape stills (`SectionRow.isEpisodeRow`) | Only Continue Watching, in-progress, and "next" sections show landscape cards; a row of episodes, such as Recently Added TV, shows posters | Maintainer's choice (PR #38): landscape cards mark the rows that resume or continue watching, and the rest of Home stays posters |
| Continue Watching's header has an icon | Text only | No icon art ships, and `RowList` row labels are text |
| A card without artwork shows its ThumbHash, or brand glows with a film or TV icon | The brand glows without an icon | Decoding a ThumbHash image costs CPU per card on low-cost hardware, and an icon would add a node to every card |
| The hero backdrop decodes at the size it is shown | On the low tier it decodes at 819×504 and is stretched to 1229×756, on Home and detail pages alike | Plan section 4.6: texture memory on low-memory devices |
| Home and a library's Recommended show every nonempty section the server returns, each with the items it sends | At most 20 rows with cards, 40 cards each; later sections and items do not show | Implementation plan section 4.8 bounds the metadata the rows keep, as well as their textures, on 512 MB devices |
| Search reads 60 results a page and Browse 100 | 40 each | Implementation plan section 4.8 bounds the metadata kept on 512 MB devices |
| Home re-reads its sections whenever it is shown again, except from detail, and on the server's push events | Home re-reads its sections quietly 3 seconds after it is next shown once the player has closed | The first release has no push channel; plan section 4.5 ties the refresh to playback |
| A failed Home shows the server's message, or "Failed to load home sections" | The message every browse page uses for a failed load, with Retry | Section 5.8; the client's copy lives in `locale/` |
| Library pages draw skeletons while they load | A centred 128 px spinner | One `Poster` instead of a placeholder per card on 512 MB devices |
| On a mixed library, each Recommended section shows only the tab's type | Both tabs show every item of a mixed library's sections | Not built (AG-280): the server's section reads refuse a type, so the client would filter each section and refill it page by page, as tvOS does, which `BrowseRows`' loading and dropping of rows around focus does not yet support |
| Collection groups appear as vertically stacked grids with uppercase headers | One group at a time, selected with a group pill and scrollable menu | Reuses the bounded Roku grid and keeps only one group's rendered cards active |
| The Sort pill, with a swap icon, is the first item of the Browse grid and scrolls away with it | The pill stays above the grid, without the icon, and the grid keeps its focused row at the top (fixed focus) instead of scrolling the page | `MarkupGrid` has no full-width header item, and no icon art ships |
| The focused alphabet rail is a 96 px column the grid makes room for, its chips centred in it | The grid stays where it is under the rail, and the 38 px chips keep to the column's right edge (x 1850–1888), clear of the grid's last column | Reflowing the grid as focus enters the rail would lay out every card again |
| Focus enters the rail at the letter nearest to where it was (the focus engine) | At the chosen letter, else All | Roku has no geometric focus engine; the chosen letter is where a viewer filtering by letter goes next |
| A library tab opens the library chosen last, and Browse its last sort, across launches (tvOS and Android TV) | The library chosen last is remembered until the app closes; Browse opens sorted by Title, and keeps its sort and letter only while its page stays on the stack | The registry holds only the session and profiles (plan section 4.3) |
| The Search keyboard is full screen, with a single row of results under it | A `DynamicMiniKeyboard` (a–z, 0–9, clear, space, delete, and voice) in a column on the left has focus when Search opens and stays on screen; the filter, count, and a grid of four 240×360 posters across fill a column to its right. Both columns start at y 232 | While a keyboard has focus, Roku OS draws a "Skip the remote. Use your phone." banner with a QR code over x 720–1920, y 0–203, and apps cannot turn it off; it covered the old top keyboard's text field (Ultra, OS 16.0.4). Roku draws `DynamicKeyboard` at its own size, which left room for most of one row of posters beneath it (AG-319) |
| The keyboard's Search key runs the query and moves focus to the results (Android TV) | Play on the keyboard runs the query and moves focus to the results, or to the filter when there are none; from results still loading, focus goes to Retry if the search fails and back to the keyboard if nothing matches | Roku keyboards have no Search key |
| While results load, Search shows only a spinner | The count line reads "Searching…" above the spinner | The audio guide reads it after the keyboard's own speech (plan section 4.9) |
| The result count reads "About N results" or "N+ results" when the server's total is estimated or missing (Android TV) | "N results" from the server's total, and no count without one | The grid drops pages it no longer shows (plan section 4.8), so it cannot count what it has loaded |
| Leaving Movies or Series for Home returns to Home as it was (Android TV) | Home and each library page are separate stack roots: Home loads again, with focus on its Home tab, as tvOS rebuilds it | One root screen alive keeps the 512 MB player within its memory budget (plan sections 4.5 and 4.7) |
| The detail metadata line leads with the content rating in an outlined 18 px Bold chip, and its 45% dots are 22 px SemiBold | The rating sits in Home's hero chip (15 px SemiBold on a white 7% fill, 5.5), and the dots are in the line's 24 px Medium | One chip for both heroes (AG-292), and the type scale has no 22 px SemiBold dot style |
| TMDB's score in the metadata line carries TMDB's logo | "TMDB 7.8" in text, as IMDb and RT are | No logo art ships |
| The detail title's subtitle is letter-spaced 1.5 pt | It is not letter-spaced | Roku `Label` has no tracking, and hair spaces (`theme.tracked`) would space 40 px capitals about twice as wide |
| A focused round button (Start Over, Versions, Audio Tracks, Subtitles) widens with an animation | Native 280 ms width and position animation with delayed label reveal on the normal tier; immediate layout on the low tier | Native interpolators keep motion off script-driven per-frame layout; low-memory devices avoid the extra animation work |
| The Versions, Audio Tracks, and Subtitles menu is Liquid Glass tinted black 45%, with a 14 px monospaced header, and opens and closes over 0.18 s | The menu panel's gradient art (`theme.art.PANEL`), the header in Inter Medium spaced with hair spaces, shown and hidden at once | Roku has no blur and ships no monospaced face; animations cost frames on 512 MB devices |
| The readout's items sit in slots 313, 364, and 338 px wide (`TVPlaybackSelectionSummaryView`), a value too long for its slot shrinks to 75%, and its labels are letter-spaced | The items flow inline, 20 px apart, as tvOS's `movie-detail.jpg` shows them; a line that would pass 1031 px cuts its longest values with an ellipsis; the labels are not letter-spaced | Decision AG-292 (3) from the reference screenshots; Roku `Label` has neither a minimum scale nor tracking |
| A menu that fits neither below its button nor above it is pinned 48 px from the screen's foot | It opens below the button or above the readout, on the side with room for more rows, and shows as many rows as fit there, scrolling the rest | Pinned, a long Subtitles menu covered its own button and the readout (hardware run 26, AG-292) |
| After Auto clears a title's subtitle choice, the readout resolves Auto with the profile's subtitle language from the app's preference store, without a mode or the item's remembered track | At once it resolves Auto without the remembered track, with the language and mode the page read; once an Auto pick's write lands (audio or subtitles), the page reads the item's tracks again and names what the server's preferences now play | The watch projection carries the series' own language and mode without the profile's, and the client keeps no preference store; until the read answers, a series' language or mode can still show (AG-292) |
| A version's row in the Versions menu names its codec, container, and size | It names the version's edition first ("Director's Cut · HEVC · MKV · 58.31 GB") | tvOS ships no Edition selector (section 3.3), so two cuts at the same quality would otherwise read the same (assumption AG-223) |
| A selector that cannot open yet is disabled | It is dimmed to 40%, and Left and Right pass over it | Roku draws its own focus (section 5.1) and has no disabled state |
| A remembered audio track applies through the server whenever a start names none | The page reads the remembered track (`GET /api/v2/audio-prefs/{key}`) and starts on it as the viewer's choice | Built when Roku's start named the profile's language's track under Auto (assumption AG-227); Auto now names the server's effective track (section 9.7), which follows the remembered one, so the read only changes how the page marks it (assumption AG-284) |
| OK on the value a Subtitles or Audio Tracks menu already shows saves it again, so a seeded Off becomes the title's own preference (`TVActionPopoverMenu`, `persistSubtitleSelection`) | A pick that changes nothing saves nothing | The page seeds Off from the profile's settings; saving it again would keep the title Off after the profile's subtitle setting changes (assumption AG-288) |
| The episode rail keeps the five seasons nearest the one shown, and reads the seasons either side in the background | It keeps three, and reads the next (or previous) season once focus is two cards from the rail's end | Implementation plan section 4.8 bounds the metadata and cards kept on 512 MB devices |
| Resting on a season pill switches season after 70 ms | After 300 ms | A season not yet read is read when the viewer stops on it, and its cards replace the rail's; switching only where the viewer stops keeps requests and texture churn down on 512 MB devices |
| While a series' episodes load, Play reads "Loading episodes…" and is disabled | Play plays the server's play target at once and names its episode when the episodes arrive | The server names the play target (section 8.3), so nothing has to wait |
| More › Show Series Info (tvOS) or a Show capsule (Android TV) puts the series back in the hero | The hero keeps the last episode focused | Section 5.6 lists only season pills, and More is not in the first release |
| Both apps hide episode spoilers per the profile's settings | Episode titles, stills, and synopses always show | Spoiler hiding is deferred (section 3.3, D10) |
| The Details table has no Genres row | Genres is a row (Android TV) | The metadata line shows only the first two genres |
| A detail page visited lately paints at once from a cache of 20 pages and refreshes quietly | Every visit reads the page again, painting the card's seed meanwhile | Implementation plan section 4.8 bounds the metadata kept on 512 MB devices |
| Rewind and fast-forward skip (Android TV) | Rewind and fast-forward drive the rate ladder | Roku remote convention |
| The player has a bottom-240 px gradient ending at black 55%, with a shadow behind the title footer | A bottom-600 px gradient ending at black 94%, reaching 72–76% behind the series, title, and episode tag | Covers Roku's fixed title block and preserves muted-text contrast over bright video without additional text nodes |
| A start or a stall shows only the centred spinner | Roku's own states also show by name in a capsule at the top right: "Stopping…", "Playback progress is pending…", and "Loading subtitles…"; a notice waits while the spinner or the capsule shows | The player's durable stop and sidecar downloads have no tvOS counterpart, and a notice that came during a stall expired unseen behind it (hardware run 23; assumption AG-262) |
| The hold indicator's thumbnail has radius 20 corners and a 1 px white 18% outline; its hint names Siri Remote gestures | Square corners without the outline; the hint names Roku keys ("← → Speed, OK Play, Back Cancel") | Over video Roku can round an image only with a `MaskGroup`, which does not clip on devices without OpenGL (plan section 4.6); a square outline would cross rounded art |
| The segment pill (Skip Recap, Skip Credits) sits 96 px up, or 156 px over the controls | It sits where Skip Intro does (156 px up, 460 px over the controls, on the safe area), and above it while both show | At tvOS's raised place it would cover the scrubber's right end and the time left; Skip Intro's place clears the controls (assumption AG-260) |
| Skip Credits on credits that run to the end, with nothing for Next Up to show, ends the item there | It seeks to the end, and the end follows when the Video node reaches it, a moment later (a `seek_reanchor` on a remux), then opens Up Next as Finished | The player has no end of its own: Roku's `finished` drives the session's stop and Up Next's end (section 9.5), so the skip reaches it as Skip Forward to the end does (assumption AG-321) |
| A SiloControl seek moves the playhead under Next Up and leaves it open: over skipped credits its 10 s countdown runs on and starts the next item, and after the end the seek is refused | A phone's seek while Up Next shows is Keep Watching, then the seek; after the end it plays the title again from there, as a new session, as a spoken seek does | The viewer chose to stay with this title, and over skipped credits the countdown counts the clock, not the playhead; every viewer seek takes one path (`viewerSeek`, assumption AG-321) |
| An item that Skip Credits finished, or that closes with Next Up open in its window, reports its runtime as the final position | The stop's final sample is the position playing (section 9.5) | The session reducer reports only the Video node's position; whether the server then counts the item watched follows its own rule, not checked here (assumption AG-321) |
| Focused pills grow (Play Now 1.085×, Keep Watching and Back 1.06×, Skip Recap and Skip Credits 1.025×, the failure screen's buttons 1.055×) | They change fill and width only | Section 5.2's pill rule: only the Sort pill, first-run buttons, fields, and Skip Intro scale; the owner's call is open (audit U3, assumption AG-265) |
| The failure screen shows one message at the top of the safe area, as coded | A 30 px title over the message, the stack centred on the screen | Roku's failure copy is a title and a message (`playback.player.errorCopy`), as its other errors are; centred, the stack stays clear of overscan (assumption AG-266) |
| Info's STREAM column lists Route, Audio, Subtitles, and the chapter; Stats shows buffer, network, and engine figures; Info and Stats page with Down and Up | STREAM adds a File row (container, the plan's bitrate, size) and Route names the plan's delivery; Stats shows the plan's source and the `Video` node's state; the panes do not take focus, and the overview takes the whole lines left, the last ending in an ellipsis | Roku's player reports neither tvOS's buffer and network figures nor an engine name; the device runs read the file facts; with the overview clamped both panes fit the 380 px panel |
| The HUD's lists scroll natively and end on part of a row at the panel's edge; the Quality picker centres the checked row and shows about four and a quarter rows | Columns and the Quality picker show whole rows only, a column scrolling a row's top to its own and the picker a row at a time; the picker opens with the checked row second of its four where the list allows | Hardware run 26: a row or line cut at the panel's edge read as a fault (decision AG-292 (1); assumptions AG-294, AG-295) |
| Subtitles draw under the controls: the controls and their gradient cover a cue while they show | Roku's captions are hidden while the controls show (not over Options or Up Next), and return as they hide; content within 3 s of its first frame is left as it is | Roku draws captions above the UI at a place of its own, so a cue crossed the scrubber and the time row (hardware run 26). The node's own `suppressCaptions`, which Roku documents for UI drawn where captions are, hides them without touching the caption mode or the subtitle selected (assumption AG-293) |
| The Video tab always has rows (Speed, Aspect) | Without a choice of quality its PLAYBACK column shows the quality as a line, and a movie's Video tab has no rows | Speed and Aspect are not in the first release (section 3.3) |
| Options' Subtitles tab shows only with tracks or a subtitle tool | Stats and Subtitles always show | A fixed set of tabs keeps Left and Right predictable while the player's stats arrive, and Subtitles holds Roku's caption modes even for a title without subtitle tracks (criterion 4.8) |
| Options' Subtitles tab has TRACKS and OPTIONS columns | Its second column is CAPTIONS: Off, On, On replay, and On mute (Roku TVs only), Roku's global caption mode; while a subtitle is burned into the video, or captions Off set one aside, only Off and On, and Off asks the server for the stream without it. On mute is checked whether Options or Roku's own menu set it, and stays checked as the TV is muted and unmuted | Criterion 4.8 (plan section 6.10); burned-in pixels cannot follow a caption mode |
| The remote's Menu or Settings key opens the player's options (Android TV) | Options opens from the controls' Options button and from Down with the controls hidden; on a Roku TV, `*` during playback opens Roku's own menu, whose Accessibility entry holds the caption setting | Roku TVs take `*` during full-screen playback whatever has focus (hardware run 6, assumption AG-117); Roku remotes have no Menu key |
| Tracks change only in the app's menus | Roku's own `*` overlay, reached with the controls hidden, can change audio and subtitles; a change that names one inventory track becomes a `track_change`, and any other is undone | Criterion 4.4 keeps the overlay; the plan owns track identity (section 9.7) |
| Turning captions on has no effect on the playing stream | With subtitles Off, turning Roku's captions on (in Options or Roku's own menus) reloads the title at its position, without the subtitle sidecars it carried | With captions on, Roku shows a carried track in the caption language whenever none is selected (`Video.currentSubtitleTrack`) |
| A subtitle the profile's preferences choose shows at once | It is selected, and shows while Roku's caption mode is on | Roku's caption mode governs captions (criterion 4.8), and the client does not turn it on at load |
| A sign that an SRT cue places at the top with an override tag (`{\an8}`) shows at the top (Android TV, whose Media3 SubRip decoder reads the tag) | It shows at the bottom, without the tag | Roku documents no placement for SRT cues and prints override tags as text (hardware run 16, Roku drawing an MKV's own track), with no documented way to hide them; the client removes the tags from SRT sidecars and never lets Roku draw a container's track itself (section 9.7) |
| One intro, credits, recap, and preview per file (Android TV) | Every `marker_segments` range, each skipped or drawn on its own | Section 9.8; the server's collection replaces the single markers |
| The scrubber has rounded ends, a buffered range, chapter ticks, and one band, the intro's, in cyan | A square track with the played range and the intro (tvOS's cyan), recap, and credits bands | Chapters are not in the first release; sections 5.7 and 9.8 name three bands; the ladder's 100 ms tick only moves `Rectangle`s |
| Holding Left or Right on the focused scrubber starts a fixed-rate auto-seek; OK there commits a scrub and then toggles play/pause | The same 300 ms hold and rate ladder as with the controls hidden; OK commits, or toggles when nothing is pending | Section 5.7's key table; Roku documents no key repeats for a held key |
| No Replay key | Replay skips back by the skip-back value clamped to 10–25 s, with "Instant replay" captions for the replayed span once its seek commits; a Replay that Back cancels, or whose merged seek lands past where it was pressed, shows none | Certification criteria 4.8 and 4.9 (implementation plan section 6.10) |
| Scrub previews come from the server's sprite sheets or, without them, from frames the player cuts from the stream | The server's sheets only; a title without them shows the time and "Previews aren't available for this title" | Roku apps cannot read frames from the `Video` node |
| A sheet decodes at full size, and only the latest one stays decoded | A sheet decodes within 1600 px on each side (a default 300 px thumbnail at 160 px, drawn 320 px wide on the card and 480 px held); the sheet in use and the next one in the direction of travel stay loaded, the sheet in use alone on the low tier | Texture memory on 512 MB devices and sheet changes at 32× (plan sections 4.8 and 6.9; hardware test H20); the drawn size costs no texture |
| The next episode's still fills the screen behind Up Next, dimmed, around the video | No still: the rest of the screen is black | Roku draws video beneath the UI, so a full-screen image would cover the shrunken video |
| The auto-play toggle shows with any pick | It is hidden, and nothing counts down, while Roku's autoplay setting is off | Plan section 6.10 (certification) |
| Back on Finished (nothing to play) replays the end, as Keep Watching does | It leaves the player | Roku's Back leaves playback; replaying would keep the viewer on a screen whose only button replays |
| Keep Watching after the end replays the last 10 s in the same session | It starts the item again 10 s before its end, as a new session | Roku's session has stopped by the time its video ends |
| Siri (tvOS) and the Google Assistant (Android TV) drive the system player's transport | Roku voice transport commands (`roInput.EnableTransportEvents`) take the remote's paths: "play" and "pause", "fast forward" and "rewind" start the speed ladder, "replay" is Replay, "rewind 30 seconds" or "forward 10 minutes" seeks, "start over" seeks to the start, "skip intro" presses Skip Intro, or else the Skip Recap or Skip Credits pill, "next" is Up Next's Play Now, and "stop" leaves the player. A seek or scan while Up Next shows closes it as Keep Watching does; after the end, "start over" and a seek replay the title as a new session. "Turn on captions" changes Roku's global caption mode, which the player already follows (spec 9.7) | Roku delivers voice commands to the app as transport events and expects an answer for each within 5 s (`source/playback/voice.bs`); criterion 4.11 does not require them below its threshold |
| An On Deck item without a backdrop or still reads its detail for one, and is left out without | It shows as Home's Continue Watching card does, its poster standing in | A detail read per card is avoided; Home's cards make the same choice |
| A screen-level error puts a headline for its cause ("Something went wrong", "Not found") over its message, with Try Again | Home, the libraries, detail, and the profile picker show their one-sentence message as the error's title, without a second line, and Search its own title over a line; the button reads Retry (Try again on the picker) | The client's error copy is one sentence per screen (`locale/`); a copy change of its own adds headlines by cause (assumption AG-285) |
| Full person page | A person panel with six biography lines and up to 24 mixed movie/series titles | Keeps person navigation within detail-page scope and bounded memory |
| Watchlist and More buttons; trailers; Filter and Shuffle; people, the Audiobooks chip, and "Available to request" in search; Home row reordering; Watchlist, Favorites, and History in the avatar menu; Chapters, Speed, and Aspect; Manage on the profile picker; Create Account on sign-in; the Home hero's air date and cast line; spoiler hiding; the AI-translation marker; theme music; the buffering-quality pill and prompts | Not in the first release | Scope (sections 3.3 and 3.4); deferred controls keep their positions when added |

## 6. Application architecture

### 6.1 Proposed repository layout

```text
manifest
source/
  main.bs                  app entry point and launch arguments
  api/                     centralized /api/v2 requests, Problem Details, URLs
  auth/                    session, refresh, profile, and registry state
  playback/                v3 DTO mapping, capability probe, plan execution
  settings/                supported settings contract, options, and scoped writes
  storage/                 typed registry access
  util/                    bounded shared helpers
components/
  AppScene.xml/.bs         root state machine and navigation stack
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
screen may infer its previous screen from global flags. A screen's own
navigation acts only while that screen is on top: a change it asks for while
another screen covers it, such as an answer that arrives under the Companion
screen, waits until it is on top again and is dropped if it is released first.
A server check or sign-in under way when another screen covers its screen
stops, as Back stops it, so its answer cannot change the session under it.

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
- A refresh that fails without a refusal waits `Retry-After`, or 30 s, before
  the next. When it got no answer, or only a gateway's `502`, `503`, or `504`
  without `Retry-After`, the next answer from the configured origin (such as
  Retry's `system/info` or the `401` itself) ends that wait, so a `401` after
  an outage refreshes at once.
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

Roku follows HTTP redirects without telling the app and re-sends a login body
on a `307`, so the same check also confirms where its request arrived. When
the answer carries `request_origin` (`scheme://host[:port]`, the origin the
server saw the request reach), it must equal the configured origin once both
are normalized (lowercase scheme and host, numeric port, default port
removed). An answer without it, from a server too old to report it, is
accepted with a warning (the exception below). Until the check passes in the
current app run, nothing that carries a credential is sent: sign-in, token refresh, PIN checks, sign-out, authenticated requests,
and media headers wait for the check and then fail if it refuses.

- The check runs at server setup and again at every launch for the stored
  server, a restored session included.
- A server without `request_origin`, too old to report it, is accepted in
  every build with a logged warning (decision of 2026-10-25; release builds
  used to refuse it).
- A different origin, or a value that is not an origin, is refused in every
  build: inline on the setup screen, and with the "server update required"
  screen for a stored server.
- A check that gets no answer refuses nothing for good; the next request that
  needs credentials checks again. Try again on the update screen checks a
  refused server again.
- This confirms the check's route only. Keeping authenticated `/api/v2` and
  media routes on that origin is the server's guarantee (S-20), verified by
  hardware test H1.

No Roku rule found so far addresses plain HTTP. Self-hosted installations
suggest allowing LAN HTTP. As in the existing apps, the client asks "Connect
without encryption?" before using plain HTTP (section 5.4), and it never
silently downgrades an HTTPS URL. Roku trusts only its system CA
bundle and certificates packaged with the app, so private-CA and self-signed
HTTPS servers are unsupported in the first release. The client will not ship a
bypass for certificate validation.

### 7.2 Account sign-in

The public release uses on-device credential entry. Sign-in first reads
`GET /api/v2/system/setup`; a server that still needs its first
administrator (`needs_setup`) gets the "This server isn't ready" screen
(section 5.4) instead of the form. Any other answer, including an older
server's 404, goes on:

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
prohibits off-device sign-in or activation, and Roku's rendezvous-linking
page says "Only TVE apps may use rendezvous linking". Silo's device-code login
(`/api/v2/auth/device/*`) and browser-based OAuth sign-in are therefore
excluded from public builds. Profile handoff reuses the device login for
a temporary session; it is on in every build by the project owner's
decision of 2026-10-25, before Roku confirms it
([`silocontrol.md`](silocontrol.md) section 2.3). Device-code login may remain in development and
beta builds. Companion sign-in, where a phone on the network signs a new
Roku in with a device login it approves, is the exception: it ships in
public builds by the project owner's decision, as comparable apps offer it
([`companion-pairing.md`](companion-pairing.md) section 1).
The server and sign-in screens' card then says "Use your phone" beside the
remote and Roku mobile app keyboard help. When a password sign-in and a
companion approval overlap, the first to finish keeps the session: the
other's tokens are dropped, and an open device login is withdrawn.

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
profile on its own. The one exception is a deep link with no profile open,
which may use the account's first non-child profile (section 10.1).

PIN-locked profiles use `POST /api/v2/profiles/{id}/verify-pin`. A wrong PIN
answers `200` with `valid: false`. Five wrong PINs lock the profile for five
minutes, and the server answers `429` with `Retry-After`. The client shows
the remaining time, as the server's auth guide recommends ("Too many
incorrect PINs. Try again in 5 minutes."), and never retries a PIN check on
its own. The issued profile token is bound to the current login session; the
client stores it with the remembered profile and asks for the PIN again only
when the server refuses it.

When the server refuses the open profile's token (`403
profile_verification_required`, for example after the PIN changed):

- the client forgets that token alone, keeps the remembered profile, and
  answers the refused request as it is, without replaying it;
- no profile counts as open, so the app returns to profile selection, which
  reopens that profile and asks for its PIN; opening it again always needs a
  new PIN;
- its playback is closed, and the session's stop waits for the new PIN's
  token; it is never sent with another profile's credentials.

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

Settings reads and writes also send `X-Silo-Client-Family: tv`.

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
- `GET /api/v2/library/{id}/collections` for the library's collection index;
- `GET /api/v2/catalog?source=library_collection&collection_id={id}` or
  `source=user_collection` for collection titles, with `limit=40`, cursor
  pagination, and supported artwork widths. Only explicitly typed mixed-library
  views add `library_id` and `type=movie|series`; ordinary and untyped views
  preserve collection membership across libraries;
- `GET /api/v2/catalog` for paginated browse, with `type`, `sort`, and
  `name_prefix` for the alphabet rail;
- `GET /api/v2/catalog` with `q` for search, using `type=video_with_episodes`
  when `GET /api/v2/catalog/search/capabilities` advertises it, and `video`
  otherwise;
- `GET /api/v2/catalog/items/{id}` for detail;
- `GET /api/v2/recommendations/similar/{item_id}?limit=12` for detail
  recommendations;
- `GET /api/v2/catalog/people/{id}` for person information;
- `GET /api/v2/catalog?source=person&person_id={id}&type=video&limit=24`
  for the person panel's library titles;
- `GET /api/v2/catalog/series/{id}/seasons` and
  `GET /api/v2/catalog/series/{id}/seasons/{num}/episodes`;
- `GET /api/v2/watch/{id}` for the playable projection, including
  `marker_segments`;
- `GET /api/v2/audio-prefs/{key}`, and `PUT` and `DELETE` on it and on
  `/api/v2/subtitle-prefs/{key}`, for the audio and subtitle tracks the
  profile chose on a detail page (section 8.5);
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
| `playback.audio_language` | Under Auto, against a server with per-codec channel ceilings, the start names no audio track, and the server resolves this setting and the track the profile chose for the series or movie, preferring a track in that language the device plays unconverted; against another server it names the version's `effective_audio_track_index`, else the track in this language the device plays best (section 9.7); a track chosen on the detail page is sent as `audio_track_index`, its position, since the watch projection gives audio tracks no ID (below) |
| `playback.subtitle_mode`, `playback.subtitle_language`, `playback.show_forced_subtitles` | The client picks the initial subtitle track from the first plan's subtitle inventory (section 9.7) |
| `playback.preferred_quality`, `playback.max_bitrate_kbps` | `quality_preference` and `bandwidth_cap_kbps` sent with start; the cap goes with every later start and replan too, and a quality chosen in Options replaces the preference for that title |
| `playback.intro_skip_mode` | Skip button versus automatic skip (`playback.auto_skip_intro` is deprecated) |
| `playback.auto_skip_recap` | Recaps skip automatically instead of offering Skip Recap (section 5.7) |
| `playback.auto_skip_credits` | Credits skip automatically instead of offering Skip Credits (section 5.7) |
| `ui.title_art` | Off shows the text title instead of the title logo on Home and detail heroes (sections 5.5 and 5.6); the top bar's shell reads it when Home or a library page starts, and the detail page uses that read |
| `playback.auto_play_next` | Up Next countdown and autoplay; the player's toggle (Up Next's and Options') writes it for this device (`profile_device`), as tvOS does |
| `playback.next_up_prompt_seconds` | How long before the end Up Next opens, and what its countdown counts from (0 to 120 s; 0 opens it only at the end) |

Start has no language member, so language preferences are applied by choosing
tracks, as Android TV does. Settings marked `client_local` in the server's
settings manifest, such as `player.resume_rewind_seconds`, are not served by
the effective-settings endpoint; the client uses their manifest defaults.
Subtitle appearance is left to Roku's system caption settings (section 9.7).
Settings writes supported preferences through `PUT /api/v2/settings/values/{key}`
with a typed `{ "value": ... }` body and an explicit `scope` query. Playback
and subtitle controls use `profile_device`, with “Use profile setting” sending
`DELETE` at that scope. Title art and video skip intervals use `profile`, as
required by their resolution order or allowed scopes. The screen explains
which scope a change affects. It reads the server contract first and offers
only supported remote definitions; after each write it rereads effective
values, showing policy constraints rather than treating the write receipt as
the applied value. Failed reads disable editing; failed writes retain the
previous display and offer retry. Requests use the central API coordinator,
with ordered, identity-fenced writes.

The client also writes the audio and subtitle picks below, as tvOS saves them
(decision D2, AG-222).

A detail page's Audio Tracks and Subtitles choices (section 5.6) are
remembered as tvOS remembers them (silo-apple `b90a86ea`,
`TrackSelectionPersistence`), in the server's per-series track preferences
rather than settings: the key is the episode's series, else the movie
itself, as on tvOS and the web. Choosing a track sends `PUT
/api/v2/audio-prefs/{key}` with its ordinal, language, and signature (its
language, title, embedded title, codec, layout, channel count, and default
flag), or `PUT /api/v2/subtitle-prefs/{key}` with mode `always`, the
version's own index for the track (not the combined ordinal a start
names), an external track's file name, and its signature (source,
language, codec, label, forced, hearing impaired); subtitles Off sends mode
`off` and index -1; Auto sends `DELETE`, so the profile's own preferences
apply again. A pick that changes nothing (OK on the value already chosen)
sends nothing. Writes for one kind and key go one at a time, in the order
picked, whichever page sent them and whether or not it is still open (the
API router's `orderKey` lines, as tvOS's `WriteOrder`); a newer pick
replaces one still waiting, and each goes only with the account and
profile it was picked under. The server has no conditional write, so this
order is what makes the latest pick the one it keeps (assumption AG-286).
A failure is logged and not retried: it costs the remembered track, never
playback. The server folds a remembered subtitle into the watch
projection's `effective_subtitle_track_signature`, which the page starts
on; a remembered audio track is read from `GET /api/v2/audio-prefs/{key}`
once per page (a 404 means none), behind the writes to that key still on
their way, and matched as the server matches it: the same signature, else
the same ordinal still in its language, else the best track in its
language. An audio pick made before that read answers cancels it, so the
pick, not the older answer, carries to the series' later episodes
(assumption AG-287). The version is not
remembered beyond the page, as on tvOS; the server's `last_file_id` makes
the version played Auto's next time.

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

Every build claims what the probe finds, on every device class; there are
no per-build or per-cohort switches (decision D-7 of
2026-10-25 in `implementation-assumptions.md`):

- video: H.264 and HEVC at the measured levels, and VP9 (profiles 0 and 2)
  and AV1 where `CanDecodeVideo` passes them. `CanDecodeVideo` takes no
  size or frame rate, Roku documents no VP9 level, and no recorded probe
  shows an AV1 level answered, so both take the largest H.264 or HEVC shape
  the ladder proved, and neither is claimed when the ladder proved none.
  That bound, and AV1's 8 and 10 bits from a bare `av1` answer (AV1's Main
  profile covers both), are inferred rather than probed. HEVC levels above
  5.1 are recorded but never counted;
- audio: AAC and MP3, AC-3 and E-AC-3 when every container passes, FLAC,
  Opus, and `pcm_s16le` and `pcm_s24le` when their probes pass (one `pcm`
  answer covers both: `CanDecodeAudio` takes no bit depth). DTS is not
  claimed until the server matches DTS variants (implementation plan S-8),
  because it would send a DTS-HD MA or DTS:X source as `dts`; DTS 5.1
  passthrough is still probed and names the output context. TrueHD, MLP, and
  DTS-HD are never claimed;
- output: HDR10 and HLG where the display reports them, HDR10+ beside HDR10
  where the display reports it, under the HDR output rule (an HEVC Main 10
  decoder, a 2160-line output, and an exact display answer);
- Dolby Vision P5 on the output and on `original_http` where the Roku is
  shown to output it, at the Dolby Vision level the HEVC Main 10 shape allows
  (9 at 2160p60, 7 at 2160p30, 5 at 1080p60). Roku has no Dolby Vision
  decoder probe, so that level is inferred from the HEVC ladder. P8 is never
  claimed: a P8.1 TS remux showed a green picture on the Ultra, and Roku
  documents only `dvhe.05` for HEVC Dolby Vision, so a P8 source plays its
  base layer (below). A Roku TV's panel does
  the Dolby Vision processing, so `GetVideoMode()` never shows it (run 11 read
  `2160p60` throughout) and the display's Dolby Vision flag is the evidence. A
  player shows it in its mode string: the Ultra 4850X reads `2160p60dv`
  outside playback too, and a player without Dolby Vision output never does;
- HLS explicitly advertises no Dolby Vision profiles while retaining the
  output's HDR10, HDR10+, and HLG support. A Dolby Vision P8.1 TS remux
  produced a green picture on the Ultra; the server chooses the supported
  HDR10 base-layer or tone-mapped fallback rather than sending native DV
  through that route. Direct originals keep P5;
- on an HDR10 output, with or without Dolby Vision, `original_http` sends
  `client_dv8_base_layer_fallback_v1` with `dv8_base_layer_compatibility_ids:
  [1]`, so a P8.1 original plays as its HDR10 base layer, and only when the
  capabilities document's `features` lists
  `dv8_base_layer_compatibility_ids_v1`: a server without it ignores the list
  and would also admit ID 2 (SDR) and ID 4 (HLG) sources, neither tested.

Hardware run 30 played one example of each claim the Ultra makes, not every
format and bound: Dolby Vision P8.1 as a TS copy remux decoded, but its colour
was not independently confirmed; a later P8.1 TS remux showed a green picture.
P5 as an MKV original engaged Dolby Vision with correct colours, confirmed
on the TV. Other exercised formats were
HDR10 and E-AC-3 5.1 as a copy remux, HLG, AV1 at 2160p50, and VP9 profile 0
at 2160p24 and profile 2 HDR10 as originals, and Opus, FLAC, and 16-bit PCM
decoded. 24-bit PCM, VP9 and AV1 at 60 fps, and HDR10+ were not exercised.
Dolby Vision on AV1 (profile 10) is not claimed.

### 9.3 Start and plan execution

1. Send `POST /api/v2/playback/start`: the v3 start request plus
   `installation_id`. Required members include `protocol_version: 3`,
   `client_features`, `file_id`, the active `profile_id`, a fresh
   `playback_attempt_id`, `quality_preference`,
   `subtitle_fidelity_preference`, `metered`, `client_capabilities`, and
   `client_playback_context`. `file_id` is the version the detail page's
   Versions menu chose, else the start path's (the version last played,
   else the server's default variant, else the first); a version the
   viewer chose also sends `allow_alternate_versions: false`, as tvOS's
   pinned version does, so a buffering search keeps it, and Auto omits the
   member. The audio and subtitle chosen go as `audio_track_index` and
   `subtitle_track_index` (section 9.7).
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

Access tokens last eight hours by default (`auth.access_token_expiry`), and
on the configured origin they are the media's only credential: the media
routes check `Authorization` and ignore `st` while the session lives, so
segments and range requests answer `401` from the moment the token in the
content's headers expires. A proxy URL's path token lasts as long as its
plan (`expires_at`, 24 hours; the server signs both from a fixed
`MaxTokenTTL`, never from the access token). The access token is never sent
to a proxy, so its expiry decides nothing about a proxy URL: neither its
renewal nor whether a track change may keep it (hardware run 23, assumption
AG-213). The client cannot assume that new headers
reach a stream that is already playing, and protocol section 4.1
(`header_refresh: none`) says to refresh the token out of band and reload
the same URL with the new header. So the client renews the content's
credential:

- before a start or reload, inside the account session's refresh window
  (30 minutes before expiry, or halfway through a shorter lifetime);
- at the next local seek or in-place track change once the content's token
  is past that refresh time (a quiet moment: the content reloads anyway);
- 60 seconds before it expires, while playing, wherever playback is; paused
  content makes no requests and renews when it plays on;
- when the media answers `401` or `403`, or the content stalls or buffers
  once the credential has expired (a progressive original's refused range
  request raises no error).

A renewal refreshes the token through the single-flight coordinator and
reloads the current plan at the current position, or sends a
`seek_reanchor` there when the timeline does not allow a local reload (a
copy remux) or the credential is a proxy's path token. It excludes no route,
is not the plan's one transport reopen, and its rebuffering is not a stall
for Auto quality (section 9.7). On a copy remux the reanchor replays up to
one keyframe interval: the new load's `PlayStart` is the plan's
`player_start_seconds`, but Roku starts it at its playlist's first segment
(hardware run 9: 0.7–4.1 s replayed). A local reload of the playing
remux's own playlist is not used instead: Roku's start on a playlist that
is still growing is the unreliable case (8 s late in run 9), and the
server's fix for it (`#EXT-X-START`, section 5.7) would serve the
reanchor too. Renewed headers that are refused
again before they play show the playback error with Retry. A renewal counts
as done only once a load with refreshed headers is scheduled: one needed
while a replan is in flight is carried by the load that replan's answer
brings, whatever its operation (section 9.6). Roku reports a
segment's status only inside `Video` error −5's text
(`…:last_err:401:…`), and a progressive original's inside error −1's,
after the URL (`…error response code:(<url>):502:…`); the client reads
both (hardware runs 8 and 10), so a media `5xx` after the first frame
reconnects (section 9.6) whichever error carries it.

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
- After a reload of the same plan, positions count only once the new load
  plays; until then progress and the stop keep the saved position.
- A new attempt the client starts by itself (an ended session, a changed
  installation, a persistent conflict) opens paused when the viewer had
  paused. Retry and Play always play.
- Such a new attempt, and Retry, name the playing plan's `selected_tracks`
  with the file they belong to. After the server fell back to another
  version (the plan's `effective_media_file_id` is not the `file_id` the
  start sent), the start sends that file's ID, and the interim AAC rule
  reads that file's audio tracks from the watch projection. When the
  projection does not list that file, the start sends the original file
  and its tracks instead. It never pairs one file with another file's
  track IDs.
- A session that a start creates after its player has closed is stopped by
  the network task, which replays an uncertain start up to five times to
  find it. A session the client gave up because the server no longer had it
  (a replan or progress post answered `404` or `410`, or the player started
  a new attempt in its place) is never stopped later: the server would
  rebuild it from its stored attempt and write its last progress over the
  newer session's position (hardware run 8, T2c). Nor is a start the
  player gave up for a newer attempt replayed, whatever its answer was: a
  session it did create is left to the server's expiry (hardware run 9,
  T3d). A start whose player closes while the network task is still
  reading capabilities is never sent.
- A title's queued progress and stop jobs from an older session are dropped
  once a newer session of that title has a position queued or a progress
  post accepted, and while one session's job or live progress post for a
  title is in flight no other session's job or post for that title is sent:
  a newer session's post waits, in the order the posts came, for an older
  session's stop on its way, at most one request's timeout for each request
  ahead of it. A title is the content under
  one server, account, and profile: a job handed over after its identity
  has gone is released at once, with a logged reason, before it can queue,
  hold, or retire anything, and a progress answer for such an identity
  retires nothing.
- An account, profile, or server change waits up to 10 seconds while
  playback is in progress: starts and replans in flight answer, the current
  sessions are stopped with the old identity's credentials, and no new start
  goes out for it. Work left after that is dropped, never sent with the new
  identity's credentials.

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
tried. A network drop is recovered with a `track_change` that changes
nothing, never with `failure_recovery`, which would exclude a route that did
not fail. A media connection that failed is a drop whenever it fails, before
or after the first frame. Roku reports one in the `Video` error's text
(hardware run 14, with the lab refusing media): a transfer error from its
reader (`Transfer error: Failure when receiving data from the peer`, `Server
returned nothing`), a playlist it read empty (`mpr zero length playlist`),
downloads that failed on every variant (`Errors seen on all bitrates`, with
a `last_err` such as `961` that is not an HTTP status), a reset, or a
timeout; or as error −1 or −2, or the `http` category, without a status.
An HTTP status decides first, then a failed connection. A media error (−5)
that names a decoder, a codec, or something unsupported
(`decoder:video:unsupported profile`) is `decoder_failure` whenever it
comes. One that names no cause is the decoder's once media reached the
load; before any did, the connection is tried once (a reconnect), and if a
load fails that way again while the API answers, it is `decoder_failure`,
so the server can choose another delivery. While the API does not answer
either, it is part of the outage. After the stream
has shown frames, a media `5xx` (a gateway's `502` for a stopped server
included) and a stall while the API is unreachable are drops as well;
before the first frame those take the normal failure path. One outage lasts
from its first drop until a load plays, with "Reconnecting" shown
throughout: its first `track_change` goes at once, and when the plan that
brings fails again (a drop, or a stall), the next waits protocol section
6.2's delay (1 s doubling to 15 s). A `track_change` the server does not
answer is replayed on the same schedule: an answer of no response, `5xx`,
`408`, or `429` waits for the next try, and a `404` (a server restart lost
the session) starts a new attempt at the position. Two minutes after the
outage began, without a load that has played since, the client shows "Can't
reach the server" with Retry, whatever its reconnects are doing then: a try
waiting, a replan the server has not answered, or a load that is not on the
`Video` node yet or still buffers (its media restarting the stall timeout).
An answer or a player callback that comes after it is ignored.

A media failure that arrives while a replan is in flight waits for that
replan's answer, which may retire the failed transport. A new plan replaces
the failed content with a new load; an in-place track change never keeps
failed content playing. An answer that leaves it in place (a refused change)
is followed by the failure's own recovery, at the viewer's seek target if
the viewer sought meanwhile. A session that ends or a viewer who leaves
during the wait ends it.

Route events go to `POST /api/v2/playback/route-events` with the v3 event,
`installation_id`, and a client-minted `event_id`. Only route events carry the
allowlisted `diagnostics` map. They are never retried; a `429` drops the
event. The first-frame event includes `first_frame_ms` in `diagnostics`,
except for autoplay starts such as Up Next.

The Roku client never constructs a transcode request, guesses a fallback URL,
or repeats a failed plan without telling the server. The Android TV client is
the reference for the client-side policy this section leaves open: one-shot
local retries before a replan, the stall timeout, repeated-key detection, seek
re-anchoring, and progress and stop retries. The stall timeout (20 s without
position progress) starts for each load when its content goes onto a stopped
`Video` node, not when its plan is adopted: the wait for the previous content
to stop (3.3 s in hardware run 10) does not count against a start. What the
client does to the player itself is never evidence: a reload, a content
swap, or a stop starts a new load (or ends the session), whose clock waits
for its own content, and what the replaced content reports belongs to the
load before. The client changes nothing on content the `Video` node has but
seeks, track selections, the caption mode and its suppression, pause, and
the node's size (section 9.7):
hardware run 19's player, closed by Roku after the client added a subtitle
track to it, reached the clock as a full buffer without output and sent
`decoder_no_output` for a playable original. A `finished` within 2 seconds
of one of those changes (a seek or pause excepted) is the client's doing
too, unless the load has played to within 5 seconds of the plan's runtime:
the plan reloads at the position as a credential renewal does (a local
reload, else a `seek_reanchor`), not as the plan's one reopen. Hardware run
20's content, stopped by Roku 0.17 s after the client selected its
subtitle again and before its first frame, otherwise reached the clock and
sent `decoder_no_output` 20 s later.

Every `failure_recovery` excludes the failed plan's route on the server,
whatever its classification, so neither a failed connection nor a slow
network that still delivers media may send one: in hardware run 14 a 30 s
media outage sent each new plan's first refused request to
`failure_recovery` and exhausted every route in 2 to 4 s. Media that reaches a node waiting for it (before the
load's first frame, or while it rebuffers) restarts the stall timeout while
the buffer still fills: a rise in `bufferingStatus.percentage`, or a
downloaded segment below a full buffer. A slow start or rebuffer therefore
waits, and with Auto selected Auto quality steps down after the first frame
(section 9.7); a rebuffer that nothing reaches is an outage, which this
timeout and the reconnect handle, never a step down. Roku reports no decoder counters, so a stall is
`decoder_no_output` only when the decoder had its media: the buffer was full,
or media arrived while the node reported playing, and 20 s passed without
position progress. A rebuffer is judged on its own media: what arrived while
the node played before it says nothing about an empty buffer, which is
starved rather than stuck. Any other stall is `transport_stall`, with the
plan's one reopen first, except during an outage, when it is a drop. Android TV restarts its clock on buffer growth only before its
decoder has input and reads a frozen decoder from its counters; a rebuffer
that keeps filling also waits here, because hardware run 11 lost a Dolby
Vision copy remux whose buffer was at 74% and filling, and a Dolby Vision
original 0.6 s before its first frame, to `decoder_no_output`.

### 9.7 Quality, tracks, and subtitles

- The quality menu displays `playback_plan.available_qualities` exactly as
  published and sends the selected label in a `quality_change` replan. It
  checks Auto only under an Auto preference; a saved resolution the plan
  reports no rung for checks no row and names itself on the Quality row
  (5.7).
- With Auto selected, sustained buffering after a load's first frame steps
  the quality down (implementation plan section 6.7). A load's own start
  never counts: a plan's, or a reload of a plan already playing (a reopen or
  a credential renewal, section 9.4), and neither does stall time in the ten
  seconds after either's first frame (hardware run 9). Buffering under way
  when a load fails or a reload replaces it is the failure's, not a
  bandwidth shortage, so it never counts, and Auto makes no decision until
  the replacement plays, however long its headers or the old content's
  stop take; stalls recorded earlier still count.
- Only a rebuffer that media still reaches is a bandwidth shortage. Its
  stall time counts from the first media to arrive in it to the latest: a
  `bufferingStatus.percentage` above the rebuffer's previous reading, a
  downloaded segment, or the node playing again. The rebuffer's first
  reading only says where the buffer stands. A rebuffer that nothing
  reaches is an outage: Auto never steps down on it, and the stall timeout
  and the reconnect (section 9.6) handle it. Hardware run 15 cut an
  original's connection; Roku played 88 s from its buffer, rebuffered with
  its reading held at 2%, and the client stepped down to a transcode six
  seconds in, with an estimate the reconnect and Retry then carried.
- An estimate no media has followed (no rising reading, segment, or load
  playing since it was taken) may have been measured across an outage. It
  is discarded when one begins (the reconnect's first drop, a stall
  timeout with nothing arriving, or an unreachable server): later replans,
  reconnects, starts, and Retry carry the estimate before it, or none, and
  its step down holds nothing off. A `quality_change` already sent keeps
  its body when it is replayed.
- A step down the server refuses leaves the plan playing without a notice,
  since the viewer asked for nothing. Its estimate is dropped for the one
  before it, and Auto judges the plan again from a fresh stall history once
  a hold ends: five minutes, doubling with each refusal in a row until a
  plan starts, up to 30 minutes. This holds when the plan of a request
  queued ahead of it starts first, and Auto asks no other step down until
  it is answered. A step down that another request
  replaces or keeps out of the queue, or that an error leaves unsent, is
  dropped the same way, without a hold.
- Audio and subtitle selection send `selected_tracks.audio` or
  `selected_tracks.subtitle` as `{id, index}` in a `track_change` replan. `id`
  is the inventory's track identity and is required; `index` is sent only when
  the inventory provides one. The client never derives combined subtitle
  ordinals.
- Neither the watch projection nor the plan gives audio tracks an `id`, so an
  audio change names the track by the server's address for it,
  `file:{effective_media_file_id}:audio:{index}` (playback protocol section
  8, as Android TV builds it), with `index` its position in the playing
  version's `audio_tracks`, the server's audio ordinal. The server refuses
  `index` alone (`TrackIdentityV3` requires `id`; hardware run 6). A start
  names Detail's audio pick by `audio_track_index`, which the start body
  accepts, for the version Detail read: the version chosen in its Versions
  menu, which the player then starts (`nav.player.pinnedFile`), or Auto's
  when it is still the one the player chooses. Under Auto, against a server
  whose capabilities list `codec_channel_ceilings_v1`, it names no audio
  track: the server resolves the profile's audio language and the series'
  or movie's remembered track, then, unless that remembered track decides,
  prefers a same-language main track this start's capabilities play
  unconverted over one it would convert (an AC-3 or E-AC-3 track over a
  TrueHD default), and the plan's `selected_tracks` names it. The version's
  `effective_audio_track_index` knows no device, so the start does not echo
  it, unlike tvOS (assumption AG-320). Against another server it names that
  index, else the track the profile's audio language and the device's
  codecs choose (section 8.5), so decision D-6 knows the track. The other kind keeps the
  plan's own `selected_tracks` member, since a `track_change` without a
  subtitle means subtitles off, or, while another `track_change` is in
  flight or waiting, the member that one asks for: an audio and a subtitle
  chosen before either's plan arrives are both requested.
- A track or quality change the viewer asked for that the server refuses
  leaves the plan playing as it was, and a notice says so ("Can't switch to
  that track.", "Can't switch to that quality."). A `track_change` waiting
  behind a refused one asks for the plan's own member in place of the
  refused one it took.
- The first release does not claim client-side audio selection within an
  original file; the server may choose a remux that makes selection
  deterministic.
- The watch projection gives subtitles no combined ordinal, so a start names
  a subtitle only when Detail picked one, or started on the one the profile
  chose on the item (section 5.6). Otherwise, Detail's Auto included, the
  client applies the subtitle preferences (section 8.5) to the first plan's
  inventory against the audio that plan plays, as Android TV's player does,
  and sends a `track_change` when the result differs from the plan's.
  Detail's Off starts with no subtitle. Detail's readout predicts that
  choice with the same rules over the version's tracks, which can differ
  from the plan's inventory when the server adds or leaves out a track.
- Options' Captions rows write Roku's `Video.globalCaptionMode`: Off, On, On
  replay (`"Instant replay"`), and, on Roku TVs (`GetModelType()` is `"TV"`),
  On mute (`"When mute"`). Choosing a subtitle track turns captions On when
  they are Off, choosing Off turns them Off, and choosing the selected track
  again only turns them back on. The client reads the mode as Roku's
  setting, `roDeviceInfo.GetCaptionsOption("Mode")`, at launch and on each
  caption-mode event, and never as `GetCaptionsMode()`, which Roku
  documents as reporting On mute as On while the TV is muted and Off while
  it is not (hardware run 17): muting and unmuting change no plan, and On
  mute stays checked whoever set it. Roku's first event after the client
  writes a mode can still report the mode before it (hardware runs 7 and
  17); that one event, within 3 seconds, is ignored.
- A subtitle the plan burns into the video (`subtitle.mode: "burn_in"`, for
  a bitmap track, since Roku claims no bitmap subtitle support) cannot
  follow Roku's caption mode, so the plan follows it instead. When the mode
  becomes Off, in Options or in Roku's own menus, or a burned-in plan
  arrives while it is Off, the client sends a `track_change` without the
  subtitle and keeps the track aside; when the mode becomes anything else
  while the plan has no subtitle, it asks for that track again. On replay
  and On mute show a burned-in subtitle all the time, so Options offers
  only Off and On while one is burned in or set aside. A track the
  preferences choose that only a burn-in can show is set aside at the first
  plan while captions are Off, instead of being requested. Nothing writes
  the caption mode at load.
- A track change in Roku's own `*` overlay is observed on the `Video` node.
  An audio change is matched to the version's track in its language,
  narrowed by codec when the language has several; a subtitle change is
  matched by the sidecar the player gave Roku. A match to one inventory
  track becomes a `track_change`; anything else is written back.
- A newly returned plan replaces the entire previous track and subtitle state.
- Roku reads a content's subtitle tracks when the content loads. So the Roku
  client loads up to four text sidecars with each content, the plan's
  selected one first and then others from the inventory (`delivery:
  "sidecar"`, on the configured origin), and a `track_change` whose new plan streams the same media switches the
  `Video` node's subtitle track on the playing content instead of reloading
  it. The client selects a sidecar by the `TrackName` Roku lists for it in
  `availableSubtitleTracks`, the name that is, or else contains, the path
  the client gave it: Roku kept drawing the track the content loaded with
  when the client wrote its own path (hardware run 17). Roku then reports
  the sidecar by any name that contains that path: after the client wrote
  the listed name, `subtitleTrack` read the bare path (hardware run 20).
  While content is set up the client selects the sidecar unless Roku
  reports it selected, and it selects nothing on its own from the moment
  content starts until 3 seconds after its first frame; a viewer's choice
  is made when it comes. On MKV originals with text tracks of their own,
  Roku listed the tracks again about 1 second after the content started,
  with the file's own track (`mkv/3`) as `currentSubtitleTrack`;
  selecting the sidecar again there stopped the content before its first
  frame in 4 of 5 loads (hardware run 20). At the first position report
  after those 3 seconds, the client checks once per load what Roku
  reports. If Roku does not report the sidecar selected, or plays another
  track (another sidecar, or a track it found in the stream), the client
  selects the sidecar by its listed name once: after a reload that
  carried Arabic or Italian, Roku drew the file's English track or the
  English sidecar while Options showed the choice (hardware run 21). A
  track Roku found in the stream gets that selection too, whatever its
  language: with the English sidecar chosen, Roku reported a file's only
  English track playing (ECP `ssa`) and drew nothing in 50 screenshots
  where the sidecar drew cues (hardware run 22), so Roku reporting such a
  track does not show that it draws it. A track Roku still plays instead
  3 seconds after that selection is logged and left, with no further
  selection on that load; that check waits for a track change on its way,
  as the one after a switch in place does. A `finished` right after it is the client's doing and reloads
  at the position (section 9.6), and the reload checks once again; after
  two such stops in a row with the same subtitle selected, the client
  makes no selection of its own for it until the viewer chooses a track.
  In either case the client tells the viewer with the notice "Can't show
  the selected subtitles.", which waits behind a busy status and goes if
  Roku reports drawing the subtitle or the viewer chooses a track first,
  and not again on a reload Roku still does not draw it on until the
  viewer chooses a track. Until
  Roku reports drawing it, or a plan selects no sidecar (Off, burned in,
  or in the stream), Options and a phone's track list check no
  subtitle, and Options reads "Not showing" on the chosen one, also when
  the server refuses a track change meanwhile; choosing it again reloads
  the plan's selection.
  A viewer's switch in place within the 3 seconds replaces the check with
  its own. Development builds log each `subtitleTrack` write and Roku's
  selected and playing tracks at debug level (listed names and `tmp:/`
  paths only). A
  switch to a sidecar the content does not carry, or Roku does not list,
  reloads at the position, as does one after which Roku still reports
  another of the content's sidecars (by any name containing its path, not
  a track Roku found in the stream) as the track it plays
  (`currentSubtitleTrack`) 3 seconds later; until that reload draws it,
  or if the server refuses it, Options checks no subtitle as above. A
  track Roku found in the stream reported then is left, with the notice
  and Options as above.
  That check waits for another
  track change the viewer made meanwhile: if the server refuses it, the
  switch is checked at the next position report; if it is accepted, its
  own selection is checked, or its new content replaces the check. The
  selected sidecar is listed
  first in the content's `SubtitleTracks`, so Roku's own pick by the
  caption language, before it lists the tracks, matches it. Content waits
  for its selected sidecar (the viewer's pick or Auto's) while it
  downloads or converts, up to 10 seconds, and 1 second for the others;
  meanwhile the `Video` node plays nothing and the busy capsule says
  "Loading subtitles…". Played on, the content before it would play again
  from where the new plan starts, and stopped seconds later it may be
  stopping while Roku opens it: on hardware run 24 the late reload below
  cost file A a 3.3–3.6 second stop and a second start on every start
  (17.9–19.5 seconds from the plan to the first frame), and its 10.24 MiB
  ASS sidecar was ready 7.8–8.3 seconds after the plan. Past the 10
  seconds, as for a first extraction of embedded text (21.8 to about 65
  seconds), the content plays without the sidecar while it downloads
  (assumption AG-219). A converted sidecar of the file's own embedded
  text tracks is kept for the rest of the app session, so content that
  carries it again neither downloads nor converts it (section 12.5,
  assumption AG-220). It is kept for the configured server's origin and
  the track's stream in the file (the `embedded_stream_index` its sidecar
  URL names), never for its place in the inventory, which a rescan moves;
  a track whose URL names no stream is not kept, and the cache is emptied
  when the session ends (assumptions AG-289 and AG-290). Content on
  the `Video` node never gets
  another track: when the client added a late sidecar to playing content
  (5.0 and 28.8 seconds after the pick), Roku listed only that track and
  closed the player (hardware run 19). So the content plays on without the
  subtitle, and the sidecar, once ready, is carried by one reload of the
  plan at the position: a local reload with the downloaded sidecar where
  the timeline allows one, else (a copy remux) a `track_change` that keeps
  the selection, as for a sidecar the content does not carry, once per
  subtitle in an attempt. A track change on its way when it arrives
  supersedes the reload; one the server refuses leaves it to follow. Content
  still waiting for the previous content to stop takes the sidecar before
  it plays. The same media is the same file, named in both plans by
  `effective_media_file_id` and `source.media_file_id`, played the same way:
  delivery, stream, `effective_recipe`, transformations, audio track, and
  timeline mapping, with subtitles rendered by the client or off. The stream
  URL is compared without its signed stream token, which the server renews
  in every plan of a signed-URL session and which carries the file's
  recipe: the `st` parameter on the configured origin, and the path token
  that ends a proxy node's direct-play URL (`{proxy}/stream/direct/{token}`).
  The URL's origin, proxy node included, and route still count, and so does
  the token of a proxy's remux or transcode route, whose job a new token may
  replace. A proxy keeps serving the old direct-play URL until its token
  expires or the session stops (the server checks the token's signature,
  expiry, and egress node, and a denied session). On hardware run 22's
  server, whose plans went through a proxy, every switch reloaded while
  the comparison kept that token. Any other plan reloads. The server picks
  the node again for every plan, round-robin over one counter that every
  client's starts and replans share, so with two or more proxies a switch
  lands on another node by chance (hardware run 23: 8 of 11 switches;
  run 24: every plan of file A). A Roku deviation keeps the content there
  too: a subtitle-only `track_change` (one the player switches in place)
  whose plan differs from the playing content's only in the proxy node
  that serves its direct-play URL keeps the content on its own node, since that node serves the old URL until its token expires
  or the session stops, and a node that goes away is a network failure
  the reconnect recovers from with a new plan (section 9.6). Everything
  else about that plan still has to match, and it still reloads when the
  player asked for a reload (a sidecar the content lacks, every audio
  change), for a quality change, for another route (a proxy's remux or
  transcode, whose job the server replaces), and once the kept URL is
  within an hour of its plan's expiry. Development builds log `kept the
  content on its proxy node` at debug level when it applies (assumption
  AG-218). The rule can go once the server keeps an original's node on
  an intent replan (section 14). Development builds log, at debug level, the name of every
  condition a `track_change`'s plan fails, with whether its stream is on the
  content's origin, never a URL, host, or token (assumption AG-212). The playing content keeps the URL, and token, it
  loaded with, and that URL's expiry and renewal; once that URL's plan has
  less than an hour left before its `expires_at`, the next such
  `track_change` or local seek reloads into the newest plan's URL instead.
  With no subtitle
  selected, the extra sidecars load only while Roku's caption mode is Off,
  because with captions on Roku would show one of them by the viewer's
  caption language; content built, or handed to the `Video` node, after
  captions came on carries none of them, even when they were downloaded
  for it. A plan that switches to Off in place also clears the
  `Video` node's subtitle track, and when captions turn on while the plan
  selects no subtitle and the content carries sidecars, the client sends a
  `track_change` that keeps the selection and reloads into content without
  them.
- The client, not Roku, decides which subtitle Roku draws, including the
  text tracks embedded in an original's container, which no content can
  leave out. Whenever its caption mode is on and nothing it can draw is
  selected, Roku draws a track it picks by the viewer's caption language
  (`Video.currentSubtitleTrack`); hardware run 16 saw an MKV's own SRT drawn
  under Off. So the `Video` node's `suppressCaptions` (per node; Roku's
  caption mode is left alone) is set whenever the plan selects nothing Roku
  should draw: subtitles off, a burned-in subtitle, or a selected sidecar
  still downloading, failed, or off the configured origin. It is cleared
  only for the plan's sidecar on the content, selected by the `TrackName`
  Roku lists for it (above), and for the HLS rendition in the stream (a
  transcode's, or a copy remux's from a server that advertises
  `hls_remux_subtitle_renditions_v1`, assumption AG-316). Roku's caption
  modes (Off, On, On replay, On mute) then govern only that subtitle, and
  Off in Options shows none under any of them. An embedded text track the
  viewer chooses arrives as that rendition in those two cases and
  otherwise as the server's extracted sidecar (its inventory `url`), as
  any other sidecar: the client advertises no
  `native_embedded` subtitle capability and never selects one of Roku's own
  container tracks, because Roku documents no `TrackName` for them that
  could be matched to the server's `stream_index` or `container_track_id`
  (Android TV matches Media3's Matroska track number, tvOS its demuxer's
  stream index). A track picked from those in Roku's `*` overlay is written
  back, as any track that is not the plan's. The reload without carried
  sidecars when captions come on (above) is unchanged.

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

The third path is the one that shipped: the client downloads the plan's
sidecars on the configured origin into `tmp:/` and gives Roku local SRT
files (section 12.5). Every build declares, for `original_http` and `hls`
(`source/playback/capabilities.bs`):

- `sidecar_text`: true (false only on the disabled `progressive` delivery);
- `embedded_text`: false (no `native_embedded`, above);
- `ass_styling`: false;
- `embedded_bitmap` and `sidecar_bitmap`: false;
- `font_attachments`: false.

With `sidecar_text` advertised, the server sends an ASS/SSA track that
arrives as a sidecar as its extracted `.ass` (assumption AG-216), which the
client converts to SRT cues on the device, text and timing only (section
12.5); an embedded one carried as an HLS rendition (above) is converted to
WebVTT by the server. Bitmap subtitles request a server burn-in. The client
respects Roku's global caption mode and caption style settings instead of
creating a second competing caption preference.

### 9.8 Markers and next episode

`GET /api/v2/watch/{id}` returns `marker_segments` for each file version: an
ordered list of `{kind, start_seconds, end_seconds}` with kind `intro`,
`credits`, `recap`, or `preview`. A kind may occur more than once; the client
skips only the active range. Intro ranges drive the skip button and automatic
skip (section 5.7) according to `playback.intro_skip_mode`. Recap and credits
ranges are drawn on the scrubber and drive Skip Recap and Skip Credits, with
`playback.auto_skip_recap` and `playback.auto_skip_credits`.

The client reads the markers of the version it plays. A server without
`marker_segments` still sends each version's single `intro`, `credits`,
`recap`, and `preview`, which stand in. Ranges of an unknown kind, with a
negative start, or ending at or before their start are dropped. A range
holds positions from its start up to, not including, its end; when ranges
of one kind overlap, the one that started last is active.

The next episode is resolved as the Android TV client does, when an episode
starts playing. The client loads the current season's episodes, then, when
nothing follows the episode there, the season list and the next regular
season (specials are skipped). A failed read of any of them offers no next
episode and marks the lookup failed, as tvOS's does, so Up Next then offers
no On Deck item in its place. The next episode is the smallest (season, episode) after the current
one in that combined list: the current episode need not be listed, gaps in
the numbering are passed over, and from the specials (season 0) playback
moves through the later specials, then into season 1. The next regular
season is the lowest-numbered season above the current one; if its list is
empty, later seasons are not tried. The client reads the season list and
the next season only when the current season has nothing after the episode,
which gives the same answer with fewer requests. The countdown and autoplay
follow section 5.7 and `playback.auto_play_next`.

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

A deep link may not show the profile picker, and Roku's deep-linking rules
forbid a child profile as its default. When no profile is open, the client uses
the most recently used non-child profile on this device, else the account's
first non-child profile, skipping PIN-locked profiles whose token this device
does not hold until Roku says whether a PIN prompt is allowed; if that profile
cannot see the content (`403`/`404`), it tries the next allowed one, and when
none can, it stays on Home. While a profile is open, a deep link keeps it. Content IDs are opaque Silo identifiers and
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
relay; the SiloControl receiver serves only the app's own playback
([`silocontrol.md`](silocontrol.md) section 2.2). Since 2026-10-15 Roku's ECP
page forbids sending ECP commands from phone apps, and Static Analysis blocks
apps that contain code to send them, so no Silo app may launch or key the
Roku through ECP.

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

### 12.5 Captions and accessibility matrix (proposal)

**Proposal, pending the project owner's review** (assumption AG-173). Once
accepted, this is "the chosen supported matrix" of section 13's Milestone 3
criterion. The tables describe what the client does today (sections 5.7 and
9.7; implementation plan sections 4.9, 6.8, and 6.10); the last paragraph
records the Audio Guide gaps closed for Milestone 3 and proposes the ones
accepted for the first release.

Cohorts are classified from probes: Roku TV (`GetModelType()` is `"TV"`),
4K player, and HD player, which includes the 512 MB devices. A row is
supported once it passes on each cohort it names, on the section 12.4 devices
and Roku OS versions, in a release build. Evidence names runs in
`docs/hardware-evidence.md`; nearly all of it comes from one Roku TV and dev
builds.

Subtitle sources:

| Source | What the viewer gets | Cohorts | Evidence |
| --- | --- | --- | --- |
| External or downloaded SRT | The original file (`subrip_sidecar_v1`), downloaded to `tmp:/` with its cues moved onto the plan's timeline and their ASS override tags (`{\an8}`) removed, shown as a Roku SRT track | All | Roku TV: runs 1, 4, 6 (T3), 7 (T1d); tag removal headless only |
| Embedded text on an original, or on a copy remux from a server without `hls_remux_subtitle_renditions_v1` | The server's WebVTT sidecar, shifted with `timestamp_offset` and converted to SRT; "Loading subtitles…" until the server's first extraction ends (assumption A-15), then one reload at the position carries it (section 9.7). Roku never draws the container's own copy of the track (`suppressCaptions`, section 9.7), so Off shows none under any caption mode | All | Roku TV: runs 1 (first extraction about 65 s), 4; run 16 (T2l) failed before `suppressCaptions`, not yet re-run; run 19 (T6) stopped when the sidecar came, before the reload (AG-201), not yet re-run |
| Embedded text on a transcode, or on a copy remux from a server that advertises `hls_remux_subtitle_renditions_v1` | The WebVTT rendition inside the HLS stream (`hls_subtitle_renditions_v1`, with `hls_remux_subtitle_renditions_v1` for a remux), which Roku shows while captions are on | All | Roku TV: run 4 fetched a transcode's rendition; its cues were not checked. Ultra: a remux's rendition played (assumption AG-316); its cues were not checked |
| ASS/SSA | As a sidecar, the raw `.ass` (assumption AG-216), converted to SRT on the device: text and timing only; styling, positions, effects, and drawings are dropped, and a sign repeated per frame or layer is one cue. An embedded track on a transcode, or on a copy remux from a server that advertises `hls_remux_subtitle_renditions_v1`, arrives instead as the stream's WebVTT rendition, converted by the server (row above) | All | Roku TV: runs 24 (T1, a 10.24 MiB typeset track converted on all 16 starts and picks, cues drawn as plain text) and 26 (T2, reused in the session and converted again after a relaunch); runs 22 and 23 refused that track by size before converting it |
| Bitmap (PGS, VobSub) | Burned in by a server transcode, following captions as Off or On only (section 9.7) | All | Roku TV: runs 4, 6 (T3) |
| Forced subtitles | As their format; shown only while captions are on (assumption AG-75) | All | Roku TV: run 6 (T7) |

A content carries at most four text tracks, each at most 20,000 cues and,
as downloaded, at most the sidecar budget: an eighth of the memory the app
has free when the download starts (`roAppMemoryMonitor`), between 2 MiB
and 16 MiB, or 8 MiB when that cannot be read. Implementation plan section
4.8's 2 MB, which every other response body keeps, stopped a typeset ASS
track (the server serves an embedded ASS track as extracted, at any size)
on every start of a title in hardware run 22, and run 22's 8 MiB stopped a
10.24 MiB one in run 23. The client reads a sidecar in 256 KiB pieces, cut
at whole characters, so its memory holds at most the cues it keeps, and
the file's size costs `tmp:/` space, which Roku counts as the app's memory,
until it is converted and deleted (assumptions AG-210 and AG-214). The
SRT it is converted to goes when the player closes, but for a file's own
embedded text tracks, which the client keeps for the rest of the app
session (section 9.7): at most 4 MiB and 32 files of `tmp:/`, the least
recently used going first, never one that content carries, and only those
once Roku's memory level reaches pressure (assumption AG-220). The player
keeps the cache's index on the render thread, where Roku refuses
`roFileSystem` (hardware run 25), and its subtitle Task does the file work;
a kept file it finds gone is downloaded and converted again (assumption
AG-236). An
ASS track's drawings and its events with no text once their tags are
removed are dropped as they are read, and the events a sign repeats per
frame or layer become one cue. A larger selected track shows "Subtitles are
too large to show.", one that fails to download or convert shows
"Subtitles are not available.", and playback continues without it. Not supported in the first release: styled
ASS, subtitles drawn by the client from bitmaps, font attachments, and
captions carried inside the video stream (CEA-608/708), which the server's
inventory does not list. Cues are verified only in Latin script; other scripts
are not claimed until tested (section 5.9 records the same gap for titles).

Caption modes and styles:

| Behaviour | Cohorts | Evidence |
| --- | --- | --- |
| Options' Captions rows Off, On, and On replay write `Video.globalCaptionMode`; On with no subtitle selected reloads without the carried tracks | All | Roku TV: run 7 (T1e, T8) |
| Options' On mute row | Roku TV | Roku TV: run 7 (T1e) failed once in three; the fix is unchecked on hardware |
| Choosing a subtitle turns captions On from Off, choosing Off turns them Off, and nothing writes the mode at load | All | Roku TV: runs 6 (T3), 7 (T1d) |
| A mode changed in Roku's own menu is followed the same way, and a burned-in subtitle follows Off and On | All | Roku TV: run 6 (T3), partly |
| Replay in On replay shows captions for the replayed span | All | Roku TV: run 6 (T3) |
| Roku's caption style settings apply to every track Roku draws; the client sets no style and drops the source's | All, except burned-in subtitles | None |
| A track chosen in Roku's `*` overlay during playback becomes a `track_change` or is undone | 4K and HD players; a Roku TV opens its own menu (section 5.9) | None (implementation plan test H15) |

Audio Guide (the client never reads whether it is on; Roku speaks only when it
is):

| Behaviour | Cohorts | Evidence |
| --- | --- | --- |
| Roku's keyboards, PIN pad, and the "Connect without encryption?" dialog speak themselves | All | None |
| Lists read each card's `audioGuideText` (title, season and episode, rating, year, runtime) and each profile's name, PIN, and Kids marks | All | None |
| Custom controls say their label when focused, through `roAudioGuide`: setup and sign-in fields, the top bar and avatar menu, the library list, sort, alphabet rail, Search filter and result count, Detail's buttons (Versions, Audio Tracks, and Subtitles with their values), seasons, and menus, the player's controls with the position, Options tabs and rows (with "selected"), Skip Intro, Skip Recap, Skip Credits, Up Next, and the player error's buttons | All | None |
| Setup, sign-in, the profile picker, and PIN say their inline errors as they appear | All | None |
| Full-screen errors and empty states say their title and message, then the focused action, as they appear, at once and again when they repeat (assumption AG-176): the player's error with Retry (Try again for a lost connection), Try Anyway, or Go Back; the shared empty and error state on Home, a library, Search, and Detail, with its Retry or Refresh once it has focus; Detail's episode message; "Server update required" and the other first-run messages, on each show; sign-in's "Can't reach {server}" before Try again | All | Headless only (`tests/views/audioGuide.spec.bs`) |
| The spinner says "Loading" and the busy capsule its state once it shows ("Playback progress is pending…", "Loading subtitles…", "Stopping…"), after what is being said, at once when it replaces an earlier state; a notice card says its title and message ("Reconnecting… The connection to the server was lost…", a refused track or quality change); neither says anything while the player's error covers it | All | Headless only |
| Options says a tab as focus reaches its pill (Info and Stats with what they show), and a column's header with the first row focus reaches in it ("Captions, Off"), so Captions' Off is not heard as Tracks' Off | All | Headless only |
| Audio-description tracks are ordinary rows in the Audio picker, ranked with commentary, so they are never chosen automatically | All | None |

Closed for Milestone 3 (the rows with headless evidence only, assumption
AG-176; implemented, device check pending): error titles and messages (player,
Detail, first-run messages, and the shared Retry state), the busy capsule
and notice cards, and the column headers in Options. Speech carries only what
the screen shows, the server's host included where a message names it,
never a URL, token, PIN, or code. Proposed as accepted first-release gaps:
the scrub position while it moves, Detail's hero title and synopsis, and Up
Next's countdown number. Each cohort is checked with
one pass using a non-default Roku caption style and one pass with Audio Guide
on through setup, sign-in, a PIN profile, Home, a library, Search, Detail,
and playback with Options, Skip Intro, Up Next, and an error screen. Both
change device settings, and the Audio Guide pass needs someone who can hear
the TV.

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

Nothing in the server needs to change for sign-in, browse, or playback.
`request_origin` in `GET /api/v2/system/info` (S-20, merged 2026-10-25) is
checked when the server reports it, and a server too old to report it is
accepted with a warning (section 7.1). `X-Silo-Device-Platform` is free
text, and device registration, rate limits, and CORS have no platform
allowlist. The following follow-ups are tracked with the server:

- add `roku` to the v2 migration ledger's consumers, with `silo-roku` as its
  source tree;
- add `roku` to the settings manifest's platform list (advisory only);
- add `roku` to the hosted-diagnostics platform allowlist before diagnostics
  upload is in scope;
- decide the media and subtitle authentication fallback if section 9.4 or
  9.7 fails on hardware;
- keep a resume point from moving backwards across sessions: a stop for a
  session the server no longer holds (rebuilt from its stored attempt after
  a restart) writes that attempt's last progress with a last-write-wins
  upsert, over a newer session's position (hardware run 8, T2c). Refusing
  such a stop, or writing it only when newer (`SetProgressIfNewer`), would
  close the gap the client cannot (a stop whose request timed out but that
  still reaches the server after a newer session's progress);
- consider a media credential that lasts as long as the plan: today the
  access token in the content's headers is the only one on the configured
  origin, so a title that outlasts it needs a reload (section 9.4). A
  session-scoped media token for `HttpHeaders` (valid only for that
  session's media, until its plan expires or it stops) keeps credentials out
  of URLs; accepting `st` itself, as proxy path tokens are, would also work
  but puts a bearer credential in every segment URL;
- keep an original's proxy node on an intent replan: a `track_change` that
  only changes a client-rendered subtitle re-resolves the route, and with
  two or more eligible proxies the round-robin pick can name another node
  although the file, recipe, and audio are the same. Hardware run 23 found
  8 of 11 such switches reloading on a server routed through proxies
  (assumption AG-213). The Roku client now keeps its content on the old
  node instead (section 9.7, assumption AG-218), which relies on the old
  node serving its URL until the token expires or the session stops; with
  the node kept, that deviation can go;
- offer clients that cannot draw ASS a text-only subtitle rendition: a
  sidecar of an ASS track's dialogue as SRT or WebVTT, or an ASS sidecar
  without its drawing and typesetting-only events, named in the plan
  (protocol section 4.2 keeps the client from composing the URL). Today a
  `render` decision serves the track as extracted, at any size, and the
  client downloads and converts typesetting it then drops; hardware run 23's
  built-in English ASS was 10,736,314 bytes (10.24 MiB). The server's
  sidecar route already converts ASS to WebVTT with FFmpeg when asked for
  `.vtt`; what that conversion keeps of drawings and signs is FFmpeg's and
  was not checked (assumption AG-216).

## 15. Open decisions

| Decision | Initial leaning | Needed evidence |
| --- | --- | --- |
| Public Store or beta-first | Beta-first | Roku policy answers and household testing |
| Plain LAN HTTP | Allow after the "Connect without encryption?" confirmation | Roku reviewer answer |
| Password-less (OAuth-only) servers | Explain and stop; no browser sign-in | None; confirm product copy |
| Device-code sign-in | Development and beta only, except companion sign-in (section 7.2) | None: Roku allows rendezvous linking only in TVE apps (section 7.2) |
| Reviewer test server | Required; owner not yet assigned | An owner and a host |
| Media authentication | `HttpHeaders` on the `ContentNode` | Milestone 0 header test |
| Side-loaded subtitles | Advertised (`sidecar_text`); each sidecar is downloaded and shown as a local SRT track (section 9.7) | Section 12.5 matrix on the cohorts other than the Roku TV |
| PIN prompt on deep link | Prompt for the remembered profile's PIN | Roku answer |
| AC-3/E-AC-3 passthrough | Disabled until proven | Codec/output-change hardware tests |
| Dolby Vision and advanced HDR | Claimed where the probe and display report them (section 9.2) | Dolby Vision on AV1 (profile 10); HDR10+ on a display that reports it |
| Features after the first release | Section 3.3's planned list (D-8) | The order of the planned items, and a choice on each undecided one |
| Roku Search feed | Not planned | Roku guidance if usage grows |
| SiloControl receiver | Built behind bs_const `silocontrol` and `handoff`, on in every build since 2026-10-25; see [`silocontrol.md`](silocontrol.md) section 13 | Spikes C0-1 to C0-7, hardware tests HC-1 to HC-6, and Roku's confirmation |

## 16. Definition of done for this draft

This draft is ready to become an implementation plan when Milestone 0 has an
owner, target devices, a Roku developer account, an owner for the reviewer
test server, and results for the media-authentication and subtitle tests.
