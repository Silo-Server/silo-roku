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

- Silo servers entered as URLs, several saved at once, each keeping its
  sign-in, with Change server switching between them (section 5.4);
- sign-in with a code: a QR code and a code approved at the server's
  `/activate` page or on a phone, leading the sign-in screen (section 7.2;
  decision D-9);
- on-device password sign-in for local accounts and password-based sign-in
  providers such as LDAP;
- profile picker, profile PIN entry, and child-profile restrictions;
- creating a profile from the picker's Add profile, as the household's
  primary profile (sections 5.4 and 7.3);
- profile at launch: Profile Selection (Automatic, Every Time, After 1 Hour,
  After 12 Hours) and, on a new TV, "Open {name} automatically?" after the
  first pick (sections 5.4 and 7.3);
- switch profile, switch server, and sign out;
- companion sign-in: a Silo phone app on the network signs a new Roku in
  from the server or sign-in screen ([`companion-pairing.md`](companion-pairing.md)).

Browse:

- Home built from the server's home sections, including the Continue Watching
  and Next Up rows the server provides;
- Home and library rows of at most 20 cards, each ending with an Explore all
  card that opens the row's full, paged page (section 5.5; added at the
  owner's request on 2026-10-28, after tvOS and Android TV);
- Movies and Series library tabs, each with Recommended rows, a Browse
  grid with sort, filters, and an alphabet rail, and read-only Collections
  pages;
- search across movies, series, and episodes;
- movie detail, and series detail with season and episode lists, cast, and
  recommendations;
- a person page from the detail page's cast: biography and the person's
  movies and series, filtered by All, Movies, or Series;
- the detail page's Trailers & More rail: the item's local trailers and
  extras, which play in the player from their start;
- theme music on detail pages, when the profile turns it on for the Roku
  (`ui.theme_music_enabled`) and the server offers it
  (`GET /api/v2/catalog/themes/capabilities`);
- on the heroes, the detail page's credit line ("Directed by", "Starring")
  and the server's external ratings, Home's quality badges, and the
  profile's title-art preference (`ui.title_art`);
- the For You tab, with the server's recommendation rows, and the Calendar
  tab, with a week of releases and airings for the profile's followed,
  trending, or all titles (section 5.10);
- episode spoiler hiding: the profile's settings blur an unwatched
  episode's still and hide its description, where the server's settings
  contract serves them (section 5.6).
- AI description translation, added at the owner's request on 2026-10-28:
  when the server translates descriptions for the profile
  (`GET /api/v2/capabilities/metadata-ai`), a description missing in the
  profile's metadata language is translated on view or from the detail
  page's More menu (Translate Description), "Translated by AI" marks AI
  text, and Settings sets the profile's Metadata Language (sections 5.5,
  5.6, and 5.8.1).

Requests, shown only when the server offers them to the profile
(`GET /api/v2/requests/status`):

- the Requests tab: the account's requests and the server's Discover rows,
  in the admin's order, with See all and the studio, network, and genre
  rows;
- a title's request page: Request, Cancel Request, Notify Me, and the
  request's status;
- My Requests, and Search's Request segment for titles the library lacks
  (section 5.11).

Personal lists:

- Watchlist, Favorites, and History pages, opened from the avatar menu;
  Watchlist and Favorites show only when the server offers them
  (`GET /api/v2/capabilities/personal-lists`);
- the detail page's Watchlist button and More menu: add to or remove from
  the Watchlist and Favorites, and mark a movie, a series, the season shown,
  or the episode Play plays watched or unwatched;
- Options (*) on a list page's card removes it from that list, or its
  watches from History.

Play:

- play, resume, or start over from server watch state;
- the version, audio track, and subtitle to start with, chosen on the detail
  page (section 5.6), with audio and subtitle picks saved to the server's
  track preferences (section 8.5);
- direct play, HLS remux, and HLS transcode, as protocol v3 plans them;
- play/pause, skip, the rate ladder, scrubbing, Replay, and stop;
- seek-preview thumbnails (trickplay) from the server's sprite sheets;
- chapters from the watch projection: a Chapters tab in Options that seeks
  to a chapter, the chapter playing in Info, and ticks on the scrubber
  (section 5.7);
- audio, subtitle, and quality selection through replan;
- Search Subtitles… in the player's Options: the server's subtitle
  providers searched for the playing file in a language the viewer picks,
  and the result chosen downloaded and turned on, when the server offers
  it (`GET /api/v2/subtitles/providers/status`, section 5.7);
- Skip Intro, Skip Recap, and Skip Credits using server markers, with the
  profile's recap and credits auto-skip (`playback.auto_skip_recap`,
  `playback.auto_skip_credits`);
- Up Next near the end of every movie and episode, with autoplay and On Deck;
- Shuffle of a library from Browse, of a collection from its page, and of
  a series or the season shown from a series' More menu, when the server
  offers it
  (`GET /api/v2/shuffles/capabilities`); Up Next offers the shuffle's
  picks;
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

- a sleep timer in the video player (Android TV; tvOS sets one only in its
  audio player);
- the marker on AI-translated subtitle tracks (Android TV);
- profile editing (Android TV); profile creation has shipped (section 3.2).

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

- remote (YouTube) trailers in Trailers & More, which tvOS and Android TV
  open in the YouTube app: criterion 5.3 rules that out, and the server
  gives only the video's site and key, no stream it hosts or relays
  (section 5.9);
- SiloControl's Require Pairing (the `sealed` level), offered only in
  development builds until the phone apps speak it, and cross-server handoff
  ([`silocontrol.md`](silocontrol.md) section 13);
- Roku Search feed and Continue Watching integration;
- theme catalog integration beyond server branding.

Settings for features this client does not implement stay out of Settings;
supported settings are available there (section 5.8.1).

### 3.4 Excluded from the first release

- browser-based (OIDC/OAuth) sign-in and account sign-up (section 7.2);
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
- playback speed and the Aspect choice in the player's Options (tvOS,
  Android TV), which Roku has no supported way to draw (section 5.9);
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
  Profile Selection, and tokens, and a second section for the other saved
  servers and theirs;
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
described. Where a deferred control has a fixed place on tvOS (Collections
in the library list), Roku leaves that place free. The card captions and
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
    Series, For You, Calendar, and Requests, 8 px apart;
  - the 58 px profile avatar, at the right inset.

  The avatar, here and in its menu's header, is drawn as on the profile
  picker (section 5.4). A library tab appears only when the profile can see a
  library of that type; For You and Calendar always appear, as on tvOS,
  whose default menu ends with them (`TVPrimaryMenuProjection`). Requests
  trails them while the server offers Requests to the profile (section
  5.11). Opening any of them from the bar starts in its content. The bar appears on root pages only: Search is a pushed
  page without it (D3), and detail pages have none.
- **Tabs** are capsules 56 px tall with 29 px side padding and 26 px labels:
  - focused: a pure white fill with black text;
  - selected: a white 14% fill with a white 10% border;
  - resting: no fill, with labels white at 62%.

  The Search circle follows the same states. The avatar has no ring at rest;
  focused, it gets a 3 px white ring inside the circle and scales to 1.05. The
  bar dims to 70% over 0.2 s while focus is in the content.
- **Panels.** Resting 250 ms on Movies, Series, For You, or the avatar opens that
  item's panel as a passive preview, with no row highlighted. Down or OK
  enters it. Moving to another bar item closes the preview. Panels are drawn
  as gradients from `#23252C` at 92% to `#141519` at 95% with a 1 px border
  from white 22% to 5%, radius 22 (the library flyout 18).
- **Avatar menu.**
  - Panel: 460 px wide, top at 132, right edge at the right inset, padding 14.
  - Header: a 44 px avatar; the profile's name in 24 px SemiBold; the
    server's display name in uppercase, 14 px, letter-spaced, at 38%.
  - Rows: Switch Profile, Watchlist, Favorites, and History; then Settings;
    then Switch Server and Sign Out. They are 54 px tall (22 px SemiBold,
    16 px inset), 10 px apart. A focused row gets a white fill with radius
    14; resting labels are at 86%, and Sign Out is red at 90%.
  - Watchlist and Favorites show only when
    `GET /api/v2/capabilities/personal-lists` answers `state` `available`
    and `allowed` true for the profile. Each page with the bar reads it as
    it starts; a failed read or an older server without the document leaves
    them out. A menu open before the read lands is built again when it
    does, keeping its highlighted row. History always shows.
  - A divider separates groups only.
  - Sign Out asks for confirmation (Sign Out / Cancel).
- **For You menu** (tvOS's `TVForYouDropdown`). The avatar menu's panel,
  460 px wide at y 132, centred under the tab within the side insets,
  headed "FOR YOU" in the library list's header style, then
  Recommendations, Watchlist, and Favorites as the avatar menu's rows, each after a
  26 px glyph (bookmark, heart, sparkles) in a 30 px column, 14 px before
  its label. Watchlist and Favorites show only when the avatar menu lists
  them. Entering it highlights its first row; Up past the first row closes
  it onto the tab, and Down past the last closes it into the content.
  Watchlist and Favorites open their pages, as from the avatar menu;
  Recommendations opens the For You page, or on that page enters its
  content.
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
    holds the Silo wordmark, drawn 122×64 4 px in from the column as tvOS's
    150 pt `SiloWordmarkView` draws its letters, on the left; on the server screen it
    also holds a chip with the TV's name on the right.
  - Below the top row: a 900 px column on the left and a 640 px card on the
    right (radius 40, `#1F1F1F` at 72%, 1 px white 14% outline), 80 px apart.
    They are centred in the space below the top row (centre y 572).
  - The column holds the whole form (D6). The card holds tvOS's "Type on
    your phone" (a phone in a 112 px glass circle), with Roku's way of
    typing on a phone: the Roku mobile app's keyboard. The phone-first
    setup screen puts the setup steps there, the code sign-in its QR code,
    and the Companion screen a card for each stage. Message screens have no
    card.
  - Type: headlines 88 px Heavy, two or three lines, their lines about
    105 px apart as tvOS sets them. Body 28 px Regular at 62%, 22 px below
    the headline.
  - Status chips (tvOS's `MarqueeTVStatusChip`): 52 px capsules, white 8%
    under a white 14% outline, 22 px Medium text at 62% after a small
    spinner or glyph. One sits over a headline where tvOS has one ("Looking
    for a phone or tablet…", the Companion screen's stages).
  - Glyphs: fields and buttons carry tvOS's symbols (globe, person, lock,
    eye, key, QR code, gear), drawn as packaged white line art.
  - Fields: 760×84, radius 16, text 30 px with a 30 px inset. At rest, a white
    8% fill with a 1 px white 12% outline. Focused, a `#EDEDED` fill with
    black text, scaled 1.04. In error, a 3 px `#FF6961` outline at 75%.
  - Errors: 24 px `#FF6961`, directly under their field.
  - Buttons: 76 px tall, labels 29 px SemiBold, 40 px side padding, sized to
    their labels, in one row 22 px apart.
    - Primary: a white 8% fill with a white 14% outline.
    - Plain (Back, Change server, Cancel): no capsule at rest, labels at 62%.
    - Focused: an `#EDEDED` fill with black text, scaled 1.06.
- **Set up with your phone.** Server setup opens here, as tvOS's
  `TVServerSetupView` does, while the Roku waits for a phone (companion
  sign-in, [`companion-pairing.md`](companion-pairing.md)): the chip
  "Looking for a phone or tablet…" with a spinner, 36 px over "Set up with
  your phone"; "It's the easiest way. There's nothing to type with the
  remote." in 32 px; "No phone nearby?" 64 px under it in 26 px at 40%; and
  Enter server address (globe) 18 px under that. On the right, without a
  card, the three setup steps 30 px apart, 700 px wide: a 168 px tile
  (radius 34, white 6% under a white 14% outline) holding a picture (the
  app icon; the phone's setup card with its Set Up button ringed in
  orange; a green check), its number on a 52 px white disc 16 px outside
  the tile's top left, and the title in 38 px Bold 34 px to its right:
  "Open Silo on your phone", "Tap Set Up", "Finish on your phone". The TV's
  name sits in the top row's chip with a TV glyph.
- **Server address.** Enter server address swaps in the address entry in
  place: "Enter your server address", "Type the address you use for Silo.",
  then the field (globe; placeholder `media.example.com`), then Advanced
  options (a compact plain button with a gear, "Hide advanced options" while
  open), which shows the protocol (Auto, HTTPS, HTTP; compact buttons 14 px
  apart, the chosen one checked) and a 250 px Port field ("Port: auto"),
  then Connect and Back, which returns to the phone (as does the remote's
  Back). A chosen protocol replaces a typed one; a port typed in the address
  wins over the Port field. An address without a scheme tries HTTPS, then
  HTTP. Before using plain HTTP, the client asks "Connect without
  encryption?". The address keyboard keeps its `https://`, `http://`, and
  `.com` chips (5.9).
- **Saved servers.** Change server (sign-in, the picker, the message
  screens, Settings, and the avatar menu's Switch Server) opens this list
  when another server is saved, and server setup ("Set up with your phone")
  otherwise. Message
  screen layout with no card: "Choose a server", "Switch to a saved server,
  or add another.", then one row per server, then Add server and Back.
  - Rows: the server card at 760 px, its badge at the right edge: CURRENT
    for the server in use, first; then the others, most recently used first,
    SIGNED OUT on one without a kept session. The name is the server's own
    (theme/branding's `server_name`, read once for a server without one),
    else its host. Rows are 16 px apart, four at a time; more scroll.
  - Focus starts on the current server. A focused row is `#EDEDED` with
    black text, scaled 1.03. A compact plain Remove sits 22 px right of each
    row; Options (*) on a row removes it too.
  - OK on the current server goes back. On another, its row says
    CONNECTING… while `system/info` checks it as address entry checks a
    typed address; the app then starts over on that server
    with the sign-in it kept, so its remembered profile reopens. A server
    that does not answer shows "Couldn't reach {server}…" under the list;
    one too old shows "Server update required".
  - Remove asks "Remove {server}?" (Remove / Cancel). Removing the current
    server signs it out and switches to the most recently used saved
    server, which the dialog names, or to address entry when none is left.
- **Sign-in.** As tvOS's `TVLoginView`:
  - A server card sits above the headline: an 80 px mark (the server's
    initial), the server's own name (theme/branding's `server_name`, read
    as the screen opens; its host until then) in 34 px Bold, its host in
    23 px at 40%, and a "SECURE" (lock) or "HTTP" (open lock) badge.
    Padding 24, radius 30.
  - With a code (the server's `auth/device/capability` says available):
    "Sign in to {server}"; "Scan the code with your phone's camera, or go
    to {host}/activate and enter it. Approve on your phone and this Roku
    signs in by itself."; the nearby hint (a phone glyph, "Have Silo on your
    phone? Open it on the same Wi‑Fi to sign in this TV.", 22 px at 40%);
    then the state's action (Try again, or Show a new code), Sign in with a
    password (key; when the server takes passwords), and Change server. The
    card holds the QR code (360 px on a white frame, radius 24, 30 px
    margin), the code grouped 4+4 in 72 px, `{host}/activate` in 24 px, and
    the status line with a small spinner ("Waiting for approval", "Continue
    on your phone", "Signed in as {account}", …); a state that ended shows a
    symbol in place of the QR code. Section 7.2 runs the code.
  - A declined or paused code has none on screen, so the lead reads "Show a
    new code to try again, or sign in with a password." ("Show a new code to
    try again." when the server takes no passwords) and the status "Sign-in
    was declined." (the TV cannot tell a phone's decline from a browser's).
    With Show a new code, Sign in with a password, and Change server in one
    row, the row is drawn in the compact button size when it would reach
    the card, so a focused Change server stays clear of it (a Roku fit
    adjustment: tvOS cuts the labels off instead).
  - Sign in with a password swaps in the form: "Sign in with a password";
    "Use your {server} username and password." (or "This server only
    supports password sign-in." without codes); Username (person), then
    Password (lock) with a 76 px eye button beside it (eye with a slash
    while shown), then the error line, then Sign in, Use your phone instead
    (QR code; back to the code, as Back is), and Change server.
  - A failure shows "Incorrect username or password." (tvOS's wording).
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
  - Add profile, tvOS's last tile, follows the profiles when the household
    has a primary profile (the one marked `is_primary`, or an only profile),
    as Android TV shows it: a 220 px circle with a 2 px dashed outline at
    25% and a 66 px plus at 40%, the name "Add profile"; focused, the circle
    fills white at 14%, the outline goes to 70%, the plus to 100%, and it
    takes the profiles' ring, scale, and name. It opens the primary
    profile's PIN when it has one, then New Profile; back on the picker, the
    list is read again and a new profile joins it with focus.
  - An account with a single profile and no PIN skips the picker, except
    when Profile Selection asks at launch; right after a sign-in it skips
    it then too, as tvOS does.
- **Profile at launch.** Whether a launch reopens the profile last chosen on
  this device or asks "Who's watching?" follows Profile Selection (Settings
  > General, section 5.8.1), as tvOS's `ProfileLaunchPreferences` and
  Android TV's decide it:
  - Automatic reopens it; a PIN-locked profile reopens with the token this
    device keeps for it, without asking for the PIN.
  - Every Time shows the picker at every launch, after every sign-in, and
    after a change of server.
  - After 1 Hour and After 12 Hours show it once Silo has been away that
    long (below), or when the TV's clock reads earlier than Silo's last use.
  - Whenever the picker is shown this way, focus starts on the remembered
    profile, and the device forgets its profile tokens, so a PIN-locked
    profile asks for its PIN again.
  - A new TV starts on Every Time. The first profile opened from the picker
    on it is offered as tvOS offers it: one the viewer picks, on the picker
    or with its PIN (a child profile too), or the account's only profile
    when the picker skips itself after a sign-in (tvOS's
    `skipPickerIfSingleProfile` goes through the same selection). The
    offer reads "Open {name} automatically?", "Silo can skip Who's Watching
    and open this profile when it starts on this Roku. You can change this
    later in Settings > General > Profile Selection.", with
    Remember (Profile Selection becomes Automatic) and Ask Every Time (it
    stays Every Time). Back answers Ask Every Time, as Menu does on tvOS.
    Choosing in Settings answers the offer too. A TV that already
    remembered a profile before this setting starts on Automatic, with no
    offer.
  - The offer is a dialog over the first screen after the picker, shown
    once that screen has rendered (5.9). A profile a deep link opens is
    never offered.
  - Time away is time since Silo was last in use on this device with a
    profile open (assumption AG-572). A Roku app is closed when the viewer
    leaves it, so a launch measures from the last use the app stamped: at
    each choice of profile and, under a timed choice, every five minutes
    while a profile is open. A Roku that sleeps with Silo still open (a
    player's suspend) counts as away from the last moment before the
    sleep: on waking, Every Time asks at once and a timed choice asks when
    the sleep ran past it, after closing the player.
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
  - For Add profile, the screen takes the primary profile's PIN the same
    way; it chooses no profile, and gives way to New Profile.
- **New Profile** (tvOS's `CreateProfileView`).
  - Full screen on black. "New Profile" in 48 px SemiBold and "Give it a
    name." in 20 px at 55%, 4 px below, 60 px from the top and 80 px from
    the left; Cancel, a compact button, at the right.
  - 32 px below, the preview column, 360 px wide: the picker's tile at rest
    with the name typed (or "Your Name"), its initial, and the lock and KIDS
    badges the PIN and Child Profile give it; "Your tile will look like
    this." 24 px under the name while there is none.
  - 80 px to its right, the form, which scrolls to keep the highlighted
    control 60 px inside the screen. Sections 32 px apart, each under an
    uppercase caption (19 px SemiBold, letter-spaced, 50%), 10 px above it:
    - Name: a first-run field, "Profile name", typed with the Roku keyboard,
      at most 64 characters;
    - PIN (optional): a field, "4-digit PIN", typed with the keyboard's
      digits; a partial PIN shows "Enter all 4 digits, or clear the field
      for no PIN." 10 px under it;
    - Child Profile, "Restricts content to kid-friendly ratings": a switch
      row (20 px Medium title, 16 px detail at 55%, a 58 px switch, white
      with a dark puck when on); highlighted, it fills white at 8% with a
      white 35% outline;
    - for a child, a panel (radius 16, 14 px inside, rows 14 px apart):
      Maximum content rating, whose OK opens Settings' centred menu with
      G / TV-G, PG / TV-PG / TV-Y7 (the default), PG-13 / TV-14, and R /
      TV-MA / NC-17; Restrict libraries, on by default; and, while it is on,
      "Allowed libraries" with a switch for each of the account's libraries,
      or "Loading libraries…", "Couldn't load libraries." with Try again, or
      "No libraries are available to assign.";
    - Create Profile, a first-run button, 40 px below.
  - Create Profile with no name, a partial PIN, or a restricted child profile
    without a library shows tvOS's alert (Name Required, PIN Too Short,
    Choose a Library) and highlights what is missing. Otherwise it reads
    "Creating…" and nothing else acts until the server answers. A created
    profile returns to the picker. A taken name, a full household, or
    another refusal shows "Can't Create Profile" with the server's reason;
    no answer shows "Profile May Have Been Created" and returns to the
    picker, so the list shows whether it was; a refused primary token returns
    to the picker to enter its PIN again.
  - tvOS's "Allow requests" switch shows only on servers that accept
    `requests_allowed`; none does on silo-server `main` (f133b241f), so
    Roku leaves it out until one does.

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
  - Description translation (tvOS's `CardDescriptionTranslation`): section
    cards carry `pending_translation_language` when their description is
    missing in the profile's metadata language. In the server's `auto`
    on-view mode, a card of a featured section (`featured`) translates once
    per item and language after focus rests on it for 1.5 s: the hero sends
    `POST /api/v2/catalog/items/{id}/translate-description` with that
    language and reads the item again on the detail page's schedule (5.6)
    until the language clears, then shows its text. Meanwhile the meta line
    leads with "Translating…" and the synopsis dims to 50%; over AI text
    (`machine_translated_fields` holds `overview`) it leads with
    "Translated by AI", on any card. Other rows, and the `button` mode,
    leave the action to the detail page, as the marquee takes no focus.
    One translation runs at a time (5.9).
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
  - Explore all (tvOS's `SectionExploreAllCard`, silo-apple `a65867ef`; Android
    TV's `TvExploreAllCard`): Home's and a library's Recommended rows show at
    most 20 cards, and every row with cards ends with an Explore all card,
    even a row that shows all it has, since Home drops titles another row
    already shows. The card is the row's only way to its page; row titles
    take no focus. It has the row's card shape (a 176×264 poster, or a
    360×200 landscape card in a landscape row) and lifts like the cards
    beside it, on the raised surface (`#15171C`) with no artwork and no
    caption: tvOS's mark, a 30 px arrow on a 66 px white 12% disc, centred
    18 px above "Explore all" in the focused card title style at `#EDEDED`.
    The audio guide says "Explore all, {row title}". Focus on it leaves the
    hero on the card it showed; Options (*) on it does nothing. OK opens the
    row's page; Back returns focus to the card. A row loaded later (5.8)
    gets its card with its items. For You and the Calendar have no card.
  - Short rows: when `GET /api/v2/home/capabilities` reports
    `section_item_limit_max`, the Home and library section reads carry
    `item_limit` of 20 (or that maximum, if lower), so the server sends no
    more cards than a row shows. The answer is read once per server for the
    session before Home's or a library's first rows; a read that fails or
    takes over 3 seconds counts as none, as on Android TV. A section read
    the server refuses with 422 for the unknown `item_limit` parameter is
    read again without it, and that server gets none for the session. The
    client cuts each row to 20 cards either way; a section's own items read
    (`.../sections/{id}/items`) takes no `item_limit`.
- **Row page** (tvOS's `SectionCatalogView`). Pushed from a row's Explore
  all card, without the top bar.
  - The row's title at (80, 88) in the collection page's title style, its
    count at y 184 ("1 item", "57 items") once known: the server's `total`
    when exact (not `total_exact: false`, which a row listed past 200 items
    answers), else the cards read once the whole row has been.
  - The library Browse grid from `theme.browse.GRID_TOP`: six columns of
    260×390 posters with centred captions, paged 40 at a time with the
    server's cursor and held as Browse holds its pages. The cards are the
    row's, in its order: `GET /api/v2/catalog?source=section&section_id=
    {id}&scope=home`, or `scope=library&library_id={id}` for a library's
    row. OK opens a card's detail page as the row does; Options (*) opens
    its menu (section 5.6); once the server takes a change from that menu,
    the page reads the row again, which may have lost the card (a Watchlist
    row, or Continue Watching after Mark as Watched). Shown again after the
    player closes, or after a personal change elsewhere, the page reads the
    row again and returns to the card that was focused, as Home and the
    list pages do.
  - States: a spinner while the first page loads; "Nothing here yet" /
    "This row does not have any items right now." with Back; "Row
    unavailable" / "This row is no longer available." with Back when the
    server answers 404 (the row was removed or hidden, or its library is no
    longer accessible); the Browse error with Retry otherwise.
  - Requests' Discover rows open the same page with their own request (their
    "See all" card is this card with that label).
- **Library landing.**
  - A library tab opens on Recommended: the same feed as Home, built from the
    library's sections without its featured ones.
  - On a mixed library, each section shows only the tab's type.
  - Within a session, a tab reopens the sub-page it last showed.
- **Browse.**
  - Page: the Sort pill at (80, 248), Filter 16 px after it and Shuffle 16
    px after Filter (tvOS's `TVBrowseControlRow`), then the grid 32 px
    below them. The grid has six columns of 260×390 posters, 40 px apart
    across and 60 px down.
  - Captions: centred, 16 px below the poster, with the same two-line title
    and metadata treatment as Home. The vertical spacing includes both lines
    and their focus drop.
  - Focus: entering Browse focuses Sort. Down from any pill goes to the
    first poster, Up to the tab; Left and Right move along Sort, Filter,
    and Shuffle, and Right from the last goes to the alphabet rail.
  - Sort pill: "Sort · Title A–Z", 24 px Medium, padding 22. At rest, a white
    7% fill and a 9% border. Focused, an `#EDEDED` fill with black text,
    scaled 1.04.
  - Sort menu: a centred 460 px panel over black 55%. Header "SORT BY" in
    18 px SemiBold at 60%. Rows are 57 px with 26 px Regular labels. A
    focused row is `#EDEDED` with radius 12, and the current sort shows its
    direction and arrow.
  - Sort options: Title, Date Added, Release Date, Year, Rating, Runtime, and
    Resolution. Choosing the active sort again reverses it.
  - Filter pill: "Filter" in the Sort pill's style. While filters are set,
    their number (facets with a value; HDR and Dolby Vision count once)
    follows the label 10 px after it, 18 px Bold in a 26 px black 25%
    capsule, and the pill rests at white 14% (tvOS's selected chrome).
  - Filter panel (tvOS's `TVBrowseFilterPanel`): a centred 680×680 panel
    over black 55%, in the menus' panel art with 22 px of padding. On top
    the eyebrow (16 px SemiBold, letter-spaced, at 60%) and the title (34 px
    SemiBold), then a divider with 12 px above and below. Rows are 56 px,
    4 px apart, labels 24 px Regular 16 px in; a focused row fills
    `#EDEDED`, radius 12, with black text and marks.
    - The filter list ("FILTER BY" / "Filters"): the facets the library
      offers, in tvOS's order, each with its value ("Any", the one chosen,
      or "3 selected") at 68% and a chevron: Genre, Decade (2020s to
      1960s), Watch Status (Unwatched, In Progress, Watched, Favorited,
      Watchlist), Content Rating, Resolution, Dynamic Range (HDR, Dolby
      Vision), Studio, Network, Country, Audio Language, Subtitle Language,
      and Original Language. A facet whose values the server does not list
      is left out; until `GET /api/v2/catalog/filters?library_id={id}`
      answers, only Decade, Watch Status, and Dynamic Range show, and the
      rest join the open panel as the answer lands. Then MATCH, "All
      selected filters" and "Any selected filter" as radio rows; OPTIONS,
      "Preserve sort & filters" (a box), "Reset filters" (dimmed and passed
      over while nothing is set), and "Done".
    - OK on a facet opens its values ("FILTER" / the facet's name): "All
      filters", then "Clear <facet>" while it holds a value, then its
      values, each with a radio mark, as the server lists them. OK toggles
      a value; Watch Status holds one, the others any number. Left or Back
      return to the filter list, on that facet.
    - The panel edits a copy: Done, or Back from the filter list, sends a
      changed choice, keeping the sort and letter, and focus returns to
      Filter. Preserve takes effect at once. Reset filters clears every
      facet and Match and moves to Done.
  - Filters on the wire, as tvOS's `CatalogQueryBuilder` sends them: every
    Browse read carries `match=all` or `any`, and with a filter `groups`,
    the JSON of one group per facet, each value a rule and any of them
    matching: `genre contains`; `studio`, `network`, `country`,
    `content_rating`, `resolution`, `audio_language`, `subtitle_language`,
    and `original_language is`; each decade a `year between [start,
    start+9]` with numbers; HDR and Dolby Vision `hdr` and `dolby_vision is
    true`; a watch status one rule (`watched is false` or `true`,
    `in_progress`, `favorited`, or `in_watchlist is true`). Filters work
    with the sort and the letter.
  - Remembered, as tvOS's `BrowsePrefsStore`: the sort, the filters, and
    Match for each server, profile, and library (a mixed library's Movies
    and Series tabs apart) across launches while Preserve is on, which it
    is until the viewer turns it off for that library; off forgets them.
    The letter is not remembered. ApiTask reads and writes them, with
    their JSON (assumption AG-382); Browse's first read waits for the saved
    choice, and a sort or filter chosen before it arrives wins.
  - Shuffle pill: "Shuffle", on a movie or series library (not a mixed
    library's tab, whose shuffle would play both kinds) when
    `GET /api/v2/shuffles/capabilities` answers `available`, not refused,
    and lists `library`. OK sends `POST /api/v2/shuffles` with `{ scope: {
    kind: "library", id } }`, then plays the shuffle's first pick from its
    beginning in the player (section 5.7). While the start is out the pill
    rests at 60% and a press does nothing; a refusal shows "Couldn't
    Shuffle." with why ("Nothing here can be played." for 409, "This is no
    longer available to shuffle." for 404, else "Couldn't start the
    shuffle. Try again.") top centre for four seconds (5.9).
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
  - One poster grid holds every group's collections (personal and server
    ones together) in the groups' order, each collection once, from y 150
    under the bar, as the personal lists' grid: eight 176×264 posters (the
    rows' size) with the same captions and gaps;
    there is no group pill, sort, or alphabet rail. Up from the grid goes to the bar.
    Opening a collection shows a paginated poster grid in server order;
    opening a title uses the existing detail page. Back restores the
    selected collection or title. Ordinary libraries retain all visible
    collection members; only a typed mixed-library view narrows membership.
    Empty and failed reads use the
    standard empty state or Retry.
  - Shuffle on a collection's page, as tvOS's
    `LibraryCollectionDetailView` and `CollectionDetailView` and Android
    TV's `TvLibraryCollectionDetailScreen` offer it: Browse's Shuffle pill
    at (80, 248), where Browse has Sort, between the count and the grid.
    It shows once the grid has items, when the shuffle capability lists
    the collection's kind (`library_collection` for a server collection,
    `user_collection` for a personal one), and never on a mixed library's
    Movies or Series view of a collection, since a shuffle carries no media
    type and would play both. Up from the grid's first row reaches it and
    Down returns to the grid; Back from the shuffle's player lands on it
    again. OK sends `POST /api/v2/shuffles` with `{ scope: { kind, id } }`
    (the collection's ID) and plays the first pick as Browse's pill does,
    with the same 60% while it starts and the same notices for 409 and
    404. The server draws from the collection's visible movies, every
    episode of its series, and any episodes it holds, so a mixed
    collection shuffles movies and episodes together; Up Next, Pick
    Another, and Stop shuffling work as for any shuffle (section 5.7),
    with the collection's title as the scope.
  - These pages are read-only. Creating, editing, and deleting collections
    remain deferred.
- **Watchlist, Favorites, and History.** The avatar menu's rows, and For
  You's, push one page each, without the top bar (5.9).
  - The list's name ("Watchlist", "Favorites", "History") in 64 px Bold at
    (80, 48), as tvOS's `WatchlistView` titles it; History adds a count of
    the items read so far at y 132, "40+ items" while more remain and "523
    items" or "1 item" once the end is read, as tvOS counts it.
  - From y 184, tvOS's grid of eight 176×264 posters, 40 px apart across
    and 48 px down with their captions (titles 20 px over 18 px metadata,
    12 px below the poster), the top half of a third row showing, newest first: the list's
    own endpoint (`/api/v2/watchlist`, `/api/v2/favorites`,
    `/api/v2/history`), 40 a page, held and paged as Browse is. History
    lists one card per title, a series for its episodes' watches.
  - OK on a card opens its detail page. Options (*) on a card opens a
    one-row menu under the card's title: Remove from Watchlist, Remove from
    Favorites, or Remove from History (5.9). OK sends the removal, and the
    card leaves the grid once the server agrees, the cards after it moving
    up; when the grid no longer holds the card (it is reading the list
    again after a change elsewhere, a read that may predate the removal),
    the page reads the list again instead. A refusal keeps the card and
    shows the failure notice (section 5.6).
  - Empty: "Watchlist is empty" / "Add titles from a detail page and they
    will appear here."; "No favorites" / "Add favorites from a detail page
    and they will appear here."; "No watch history" / "Items you watch will
    appear here", each with a Back button. A failed first read shows the
    Browse error with Retry.
  - After a personal change anywhere in the app (a detail page's toggle,
    including one that lands after its page closed), the page reads its
    list again and returns focus to the card it was on: at once while it
    shows, else when shown again. It also reads again when shown after the
    player closes, since playback moves History's order and a card's
    progress.
- **Empty states.**
  - Home: "Nothing to watch yet" / "Add media to your libraries or start
    watching to see it here."
  - Library: "{Library} is empty" / "Add media to this library on the server
    to see it here."
  - Browse: "This library is empty" / "There is nothing in this library yet."
  - Browse with filters or a letter that match nothing: the page first reads
    one unfiltered item of the library (`limit=1`, `skip_total=true`, the
    tab's type; tvOS's `BrowseEmptyReason`), the spinner showing meanwhile.
    With none it says "This library is empty"; else, or when that read
    fails, "No titles match your filters", with Clear filters, which clears
    every filter and the letter, keeps the sort, and focuses Sort.

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
  point exists, then Versions, Audio Tracks, and Subtitles, then Watchlist
  and More once the item is read. Resume appears
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
- **Watchlist and More.** As tvOS's `TVDetailActionRow` ends a movie or
  series row. A series with nothing to play keeps the two.
  - Watchlist is a circle with a bookmark, filled while the item is on the
    list, labelled "Watchlist" when focused; the audio guide says "Add to
    watchlist" or "Remove from watchlist". OK changes it at once and sends
    `PUT` or `DELETE /api/v2/watchlist/{id}`. It shows only when the server
    offers the lists (section 5.3).
  - More is a circle with three dots. OK opens its menu, the Versions
    menu's popover with the title "MORE" and no check marks: on a series
    first "Shuffle Season 2" (the season shown, named by its number even
    when the server titles it, Specials by its title; once its episodes
    are read, when two of them have a file and the server's shuffle
    capability lists `season`) and "Shuffle Series" (when its seasons
    count more than one episode and the capability lists `series`), as
    tvOS's
    `TVSeriesDetailView` leads with them; then Add to Favorites or Remove
    from Favorites (only when the server offers the lists), then on a
    movie Mark as Watched or Mark as Unwatched; on a series Mark Series
    Watched or Unwatched, Mark Season Watched or Unwatched for the season
    shown, and Mark Episode Watched or Unwatched for the episode Play plays
    (5.9); last, Translate Description, while the page offers it
    (Description translation, below). The menu holds nothing else (5.9).
    Each row does what it said when the menu opened, even if a read that
    lands while it is open, such as the seasons read after a mark, turns
    the state it names; Shuffle <season> shuffles the season it named.
  - A Shuffle row starts a shuffle of the season (its content ID) or the
    series as Browse's Shuffle pill does (section 5.5): one start at a
    time, the first pick from its beginning, a refusal as a notice. The
    page reads the shuffle capability when it opens unless a page before
    it this session already did.
  - The flags come from the item's `user_state` (`in_watchlist`,
    `is_favorite`) and watched state (`user_data.played`, a season's counts
    of unplayed and watched episodes, an episode card's `played`). A change
    shows at once and sends `PUT`/`DELETE /api/v2/favorites/{id}` or
    `POST`/`DELETE /api/v2/watched/{id}`; the writes for one item and list
    go one at a time, the latest replacing one still waiting.
  - Once the last write for a watched change lands, the page reads the
    touched episodes again (a series' loaded seasons, else the season) for
    their check marks; on a series its seasons, for each season's counts
    and whether the series counts as watched (every season with episodes
    watched, as tvOS's `refreshWatchedSeason`), which More's Mark Season
    and Mark Series rows follow; and the action row's target for Play or
    Resume, since the server clears a resume point it marks. A series page
    also reads its seasons again when the player closes over it, with the
    watch state. A read that lands while a write is still out keeps what
    the page shows for what that write covers: a movie's watched flag, an
    episode card's flag under a mark for the episode, its season, or the
    series, a season's counts under one for the season or the series. Of
    two reads of the same thing (a watch state, a season's episodes, the
    series' seasons), one that lands after a newer one is dropped, and a
    first read of the seasons or of a season's episodes that left before a
    watched change landed is read again.
  - A refused change goes back to what the server last confirmed for it,
    once no newer write for it is out, and the page reads again what it
    covers when an earlier write was applied or a read was held back for
    it. "Couldn't update item. Your change wasn't saved." shows top centre
    over every screen for four seconds, drawn as a phone's connection
    notice is (5.9).
  - A write outlives its page: Back can take the page before the answer.
    The scene hears every write land, so an applied one still makes the
    list pages read again and a refused one still shows the notice. A page
    open on the same item, such as the item opened again before the write
    landed, shows a Watchlist or Favorites change as applied, unless a
    write of its own for it is out, and reads again what a watched change
    moves. While its own write is out, the other page's applied change
    becomes what a refusal of that write puts back.
- **Description translation.** As tvOS's
  `ItemDetailViewModel+DescriptionTranslation` and
  `DescriptionTranslationCoordinator`, gated on
  `GET /api/v2/capabilities/metadata-ai` (`state` `available` and
  `allowed`; its `on_view` mode `off`, `button`, or `auto`, anything else
  read as `off`), read once per server and profile in a session by Home,
  the detail page, or Settings, whichever opens first.
  - A page can miss up to two translations in the profile's metadata
    language: its own description (the item's
    `pending_translation_language`) and, on a series, the season shown's
    episode descriptions (any of its episode rows'
    `pending_translation_language`), which the season's job translates
    together.
  - In `auto` mode each starts once per item and language while the page
    shows. In `button` mode, and after a run fails in `auto`, More offers
    Translate Description, which starts every missing one. Neither shows
    while a run is under way, or when the server answers `off`.
  - A run sends `POST /api/v2/catalog/items/{id}/translate-description`
    (the item's or the season's content ID) with
    `{ "target_language": <the reported language> }`. The server has no job
    read for viewers, so the page reads the item, or the season's episodes,
    again after 1, 2, 2, 3, 3, 4, 5, 5, 5, 5, 5, and 5 seconds until the
    language no longer shows, and puts the new overview, tagline, and AI
    mark on the page. After 45 s, or a 202 job already `failed` or
    `canceled`, the run fails. A refused request (422 when nothing is left
    to translate, 429 when rate limited) is read once and ends well if the
    text is there.
  - The hero says what happens under the synopsis, 6 px below it in 22 px
    Regular at 70%, taking its line from the synopsis: "Translating…" with
    the synopsis at 50% while the run for the description shown is under
    way, "Translated by AI" when `machine_translated_fields` holds
    `overview`. An episode the hero describes follows its season's run and
    its own row's fields. A failure says nothing; More offers the action
    again.
  - The player over the page, or Back, stops a run; an automatic one starts
    again when the page shows. A failed run does not start again on its own.

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
    Crew, then Trailers & More, then Related Movies or Recommended Series,
    then Details. Cast
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
  - OK on a cast card with a person ID opens the person's page; Back from
    it returns to that card.
- **Trailers & More** (tvOS's `TVTrailersRail`).
  - The item's local extras (`extras` on `GET /api/v2/catalog/items/{id}`:
    trailers, teasers, featurettes, behind the scenes, and the rest) in
    server order, up to 24 (assumption AG-360). The rail shows only when
    the item has one, and needs no request of its own. Remote videos
    (`videos`, YouTube) are left out (5.9).
  - Cards are 470×264 at radius 18, 48 px apart, the first at x 116, with
    the extra's still (`still_url`, a root-relative signed path read
    against the server's origin); without one, `#15171C` with a 48 px
    film glyph at `#EDEDED` 60% in the centre (tvOS's `TrailerCardLabel`).
    A 60 px black disc at 55% (72% focused) with a 24 px play glyph sits
    at the centre. Centred 14 px under the card: the extra's title (21 px
    SemiBold, `#EDEDED` at 92%), else its kind ("Trailer", "Featurette",
    "Behind the Scenes"; "Extra" for a kind the client does not know), and
    5 px under it its runtime ("2:31", "1:02:03"; 17 px Medium at
    `#EDEDED` 60%).
  - Focus draws a 3 px white ring at 90% inside the card's edge (2 px in
    HD) and brightens the title to full `#EDEDED`, with Home's shadow; the
    card does not lift and the caption does not drop, as both tvOS detail
    pages pass `TVTrailersRail` `focusScale: 1.0`. The same on every tier.
    Floating focus and the selection kept across Back and rebuilding, as
    on the other supporting rails.
  - OK plays the extra in the player from its start, through protocol v3
    like any item; Back returns to its card. The page does not read its own
    watch state again afterwards.
- **Theme music** (tvOS's `ThemeMusicCenter` and `ThemeMusicController`).
  - It plays while the profile's `ui.theme_music_enabled` is on for this
    Roku and `GET /api/v2/catalog/themes/capabilities` answers `available`
    with `allowed` not false. The theme is the first song of the item's
    `themes` set. On a series it is the season's, once the season shown is
    read (`GET /api/v2/catalog/items/{season}`), the series' playing on
    meanwhile; a season item without a set keeps the series' theme, and an
    empty set plays nothing. A series page starts nothing before its
    seasons are read.
  - `POST /api/v2/catalog/items/{owner}/themes/{theme_id}/playback` gives a
    short-lived grant for the theme, the request listing what the Roku's
    Audio node plays (MP3, AAC in MP4, M4A, or ADTS, and FLAC; AG-362); the
    server converts any other theme to AAC in MP4. The grant's URL,
    relative to the server or on a proxy's origin, plays in an Audio node
    without account credentials and is never logged.
  - It plays only while its page is the screen on top, and waits, paused,
    while the page is still loading. Any screen over the page (a person,
    another detail page, Settings, the player) stops it at once, as tvOS's
    page stops its theme when a route is pushed over it, and the page
    starts it again from the beginning when it is back on top. Leaving the
    page (Back, a deep link, a phone's launch), switching profile, and
    signing out stop it. The screen host reports every navigation, whatever
    caused it, through one call (`themeMusicNavigated`); a page that is
    not shown reports nothing, so a late answer under another page cannot
    take the player from the page on top.
  - It plays once to its end and then stays silent while the page stays
    open; shown again after another screen, the page plays it again. With
    `ui.theme_music_loop` on, an original file loops in place and a
    converted one replays with a new grant. A refused grant leaves the
    page silent until it is shown again; a stream that fails is retried
    once with a new grant.
  - Reads (AG-363). The two settings (`GET /api/v2/settings/values/effective`)
    and the capability are read when a page needs them, and each answer
    stands for 60 s; a failed read counts as off. Each read carries the
    profile it was asked for and is dropped once another profile or server
    is open. One read of each kind is on its way at a time. Settings' own
    read of the values replaces the player's and drops one sent before it.
    Each grant carries the player's generation, so a grant that lands after
    a newer theme, a stop, or the page's release is dropped; a season's
    set is read once per profile.
- **Person page** (tvOS's `PersonDetailView`), a pushed page without the
  bar.
  - Header: a 300×450 portrait at (80, 48), radius 12 with a 1 px white
    10% outline, on `#15171C` with the name's initials (up to two letters,
    84 px SemiBold at 60%) when there is no photo or the photo fails to
    load. The
    text column starts 48 px right of it and 10 px lower: the name in
    72 px Bold, up to two lines; 22 px below, the badges; 22 px below them,
    the biography in 26 px Regular at 60%, up to seven lines, 920 px wide.
  - Badges, in order: "Born Apr 25, 1940", then "Died Jul 1, 2004" or,
    without a death date, "86 years old", then the birthplace. Each is 20 px
    Regular text in a 36 px `#0E0F12` capsule with 16 px of padding, 12 px
    apart. A date that does not parse shows as the server sent it.
  - 48 px below the taller of the portrait and the text: "Filmography" in
    36 px SemiBold, with the count 16 px after it in 22 px at 60% ("57
    titles", "1 title", "0 titles"; "40+ titles" while the server gives no
    total and more remain). 20 px below, the filter pills All, Movies, and
    Series, drawn as the season pills; Movies and Series show unless a
    one-card read finds the person has none of that type. A pill that
    drops out leaves the highlight on the same filter; if it was the
    chosen one, All is chosen and read. 28 px below the pills,
    Browse's six-column grid of 260×390 posters, the person's credits
    newest first, 40 a page.
  - Focus opens on the selected pill. Left and Right move along the pills
    and OK reads that filter's titles; resting on a pill does nothing.
    Down enters the grid, and the page moves up in 0.25 s (at once on the
    low tier) so the grid sits at Browse's place (y 332) with the pills
    above it; Up from the grid's first row returns to the pills and the
    page moves back. OK on a card opens its detail page. Back returns to
    the detail page below.
  - The page waits for the person read behind the spinner. A missing
    person says "Person not found" with Back; another failure says "Can't
    load this person." with Retry. A person without titles shows "No
    titles found" / "There are no movies or series linked to this person
    yet." in the grid's place; failed titles show "Can't load this
    person's titles." with Retry, which Down reaches from the pills, and
    the page moves up as it does for the grid, so Retry stays on screen
    under the tallest header. Both centre 210 px below the grid's top
    (tvOS's 420 px minimum height), except that under a tall header the
    empty state, which takes no focus and so never moves the page, rises
    to end at the action-safe line (y 1026).
  - Returning to the page, or rebuilding it after memory pressure, keeps
    the filter and the focused card.
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

**Episode spoiler hiding.** Two profile settings, as tvOS
(`EpisodeSpoilers`, `EpisodeSpoilerPreferences`) and Android TV apply
them: `catalog.hide_unwatched_episode_images` ("Blur unwatched episode
images") and `catalog.hide_unwatched_episode_overviews` ("Hide unwatched
episode descriptions"). Both default to off and roam with the profile
(section 8.5). The server never changes catalog answers for them; the
client hides, and only an episode's own still and description. Series and
season artwork and overviews always show.

- **Unwatched.** An episode with no watch state, or one neither played,
  in progress (`is_in_progress`), nor at a saved position
  (`position_seconds` > 0). An in-progress episode shows everything. A card
  marked watched since it was read (its Options menu, or the detail page)
  shows its still when it is next drawn, and one marked unwatched hides it
  again, as tvOS's played override does.
- **Which picture.** The provenance the server gives for the picture
  shown: `still_is_episode_still` on an episode row's still,
  `poster_is_episode_still` on a poster card, and on a landscape card
  `backdrop_is_episode_still`, or the poster's when the backdrop falls back
  to it. `false` is never hidden; `true` or an absent field is hidden, as
  the server asks for unknown sources.
- **Cards.** The series page's episode rail, Home and library rows
  (Continue Watching, Next Up, and episode posters), Browse and list grids,
  Search results, and Up Next's On Deck cards blur a hidden still in
  place: the card, its frame, check disc, progress bar, and caption stay
  as they are (tvOS blurs at radius 24; section 5.9 for Roku's blur).
- **Home hero.** For a card whose hero backdrop is the episode's own
  picture, the hero shows no backdrop and no wash, as tvOS's marquee drops
  it; an episode card with its series' backdrop (`series_backdrop_url`)
  keeps that. A hidden description leaves the synopsis empty; the series
  title and the "S1 E3 · Title" line stay.
- **Series hero.** The backdrop is always the series', so only the
  description hides: the synopsis line reads the episode title alone, not
  "Title · overview".
- **Up Next.** The pick's overview is left out; the series title,
  "S1:E2" and title, and air date and runtime stay.
- **Settings.** Playback's Spoilers section, after Episodes (section
  5.8.1).
- **When it applies.** Each page with the top bar (Home, a library tab,
  For You, Calendar) reads the settings when it starts: first
  `GET /api/v2/settings/contract/capabilities`, and only where that is
  available at manifest revision 17 or later with batched effective reads,
  `GET /api/v2/settings/values/effective` for the two keys, on their own
  so an older server's 422 cannot fail another read. A server without them
  hides nothing, and Settings shows no rows for them. A failed read keeps the
  profile's last answer this session. Settings applies what it reads and
  saves at once: the rows, grid, and hero beneath it draw their episode
  cards again. Before a profile's first answer in a session nothing is
  hidden (section 5.9).

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
    scrubbing. Intro, recap, and credits ranges are bands (5.9). Each
    chapter start after the first is a tick, as tvOS draws it: 3 px wide
    (4 px while scrubbing), 14 px taller than the track, white 85%, over
    the played part.
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
  - The buffering card follows tvOS's (`TVBufferingQualityPill`): a glass
    card at the top right, at y 140, below any notice. The prompt reads
    "Playback keeps buffering" over "Try a lower quality to keep watching",
    with Lower quality and Keep quality; the undo card reads "Quality
    lowered to stop buffering" with Restore quality. A 4 px track along its
    bottom drains over 15 s and stands still while paused. Skip Intro, Skip
    Recap, Up Next, Options, and the error screen hold it back with its time
    left. With the controls hidden, OK presses the lit capsule and Left and
    Right move between the prompt's two; with them shown, the card takes
    focus as it appears and Down returns to the scrubber. Back on the
    prompt keeps the quality and on the undo card only hides it, after a
    pending seek and before Skip Intro. "Quality lowered to stop buffering"
    and "Can't lower quality for this video" show as information notices
    for 5 s (section 9.7).
- **Options panel.**
  - Tabs: pills above the panel, centred at y 92, 12 px apart, 22 px
    SemiBold, about 46 px tall. The active tab is white with black text, and
    stays white while focus is in its pane. Other tabs are black 45% with a
    1 px white 18% ring.
  - Panel: 14 px below the tabs, 1100×380, padding 28/22, radius 28, filled
    `#1A1A1A` at 88%, with a 1 px white 14% stroke.
  - Tabs shown: Info, Stats, Video, Audio (when the version lists audio
    tracks), Subtitles (always on Roku; 5.9), and Chapters (when the
    playing version has chapters, as on both TV apps). When an update drops the
    tab shown, the tab that takes its place (else the last) shows.
  - Columns: each tab is laid out in columns 48 px apart, each under a 14 px
    SemiBold uppercase header at 50%.
    - Info: TITLE (series, title, "S1 · E2", "2024 · 1h 42m", overview,
      which takes the whole lines left, the last ending in an ellipsis) and
      STREAM (resolution, HDR, codec, and audio badges, then Route, Audio,
      and Subtitles rows, and Chapter, the chapter playing, once the first
      has begun).
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
      CAPTIONS ends with Search Subtitles…, a setting row with a chevron,
      while a plan plays and the server has not said its subtitle
      providers are unavailable (Search Subtitles, below).
    - Chapters: CHAPTERS, a row for each chapter of the playing version
      (the watch projection's `chapters`, section 8.1): its number ("01")
      in a 44 px column at 55%, its title (an untitled one "Chapter 2", by
      its place), and its start time ("12:05") at the right at 65%, with a
      play glyph 10 px before the time on the chapter playing, the last
      whose start has passed. Focus enters on that row. OK seeks to the
      chapter's start, the one playing included, and closes Options so
      the seek shows, as tvOS's HUD dismisses.
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
  - After a pick other than a chapter, the panel stays open with focus on
    the row, as in both apps, whether the new plan switches in place or reloads the title, and
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
  | Rewind / Fast-forward | Show the controls on the scrubber and start the rate ladder; each press steps up | Start the rate ladder; each press steps up |
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
  and "2×" in 18 px Bold. Rewind and Fast-forward show the controls and
  run the ladder on the scrubber, as a Left or Right press does (section
  5.9). A hold of Left or Right with the controls hidden runs the ladder
  without them and shows tvOS's top-centre indicator: the 480 px thumbnail
  at y 180, the direction, rate, and time in a chip under it, a 520 px
  progress line, and the keys' hint.
- **Seek previews.** While the viewer scrubs, with Left/Right or at any
  rate-ladder speed, a 340 px card shows above the scrubber, centred on the
  scrub point and kept within the scrubber's ends. The card holds the
  thumbnail at 320×180 (radius 14) with the time under it in 24 px SemiBold,
  has radius 20, and is filled `#1A1A1A` at 88%; the title hides meanwhile.
  Thumbnails come from the server's trickplay sprite sheets for the file
  playing. A title without them shows the time where a thumbnail's would be,
  under "Previews aren't available for this title".
- **Search Subtitles**, as tvOS's SubtitleSearchMenu (silo-apple
  `791b1e0e`; assumptions AG-490 to AG-495).
  - Offered: the Subtitles tab's Search Subtitles… row shows while a plan
    plays a file. The player reads `GET /api/v2/subtitles/providers/status`
    each time Options opens, and only an answer hides the row: `enabled`
    false, a `state` other than `available`, or `allowed` false. Before
    the first answer, and after a failed read, the row shows, as tvOS's
    `SubtitleProvidersStore` does. An answer of no that arrives while the
    panel sits on its language list replaces the list with "Subtitle
    search is not set up on this server." and Back.
  - The panel opens over the Options panel, which stays open but hidden: a
    900 by 780 px glass panel centred over the video dimmed to 45%, radius
    28 with a 1 px white 18% outline, padding 34 by 28. The title "Search
    Subtitles" is 30 px SemiBold, the line under it 17 px at white 65%,
    and a hint at the foot 17 px at 55%. Rows are the Options panel's
    track rows (72 px, name over details), section names are 14 px
    SemiBold uppercase at 50%, and lines of copy 22 px. The rows scroll to
    keep focus in view.
  - Languages: "Choose a language to find subtitles for this video." The
    profile's subtitle language for the title (the watch projection's
    `effective_subtitle_language`, else `playback.subtitle_language`)
    leads under PREFERRED LANGUAGE, marked Preferred; then ALL LANGUAGES,
    the 43 languages the client names, by name. Focus opens on the
    preferred language. There is no query text: the server searches by
    the file.
  - OK on a language is the search (`POST /api/v2/subtitles/search` with
    the playing file's `effective_media_file_id` and that one language;
    60 s timeout). Meanwhile "Finding subtitles in French", "Searching
    providers…", "This can take up to half a minute.", and Cancel.
  - Results, in the server's order, under "French · 12 results": the
    release name ("Untitled release" without one) over "88% match ·
    French · 1234 downloads · HI · SRT", with the provider's name at the
    right (OpenSubtitles, SubDL, Subsource, else as the server names it).
    The server's warning shows first, in amber. With none: "No subtitles
    found for French." and Choose another language. The hint says "Select
    a subtitle to download and use it".
  - OK on a result sends `POST /api/v2/subtitles/download` once, echoing
    the result. Its row says "Adding subtitle…" at the right, the others
    dim and take no focus, and Back does nothing until it settles. A
    stored subtitle is brought into playback (section 9.7); once its plan
    selects it, with Roku's captions On, the panel and Options close.
  - A refusal shows its message with Back: "Subtitle providers are busy.
    Try again in a minute." (429), "This server does not allow subtitle
    downloads here." (403), "That subtitle is no longer available. Try
    another result." (404), else "Couldn't add that subtitle. Try another
    result." A failed search shows "Subtitle search could not finish. Try
    again." or the busy message, with Try Again and Back.
  - A subtitle stored but not brought into playback says "The subtitle
    was saved but couldn't be turned on now. It will be available the next
    time you play this video."; one listed but not selected (the choice
    refused) says "The subtitle was saved but couldn't be turned on.
    Choose it under Tracks in Subtitles."; a download with no usable answer (a
    timeout, a lost connection, a gateway's error) says "Silo couldn't
    confirm the download. If it was saved, it will be available the next
    time you play this video." Either result is not sent again while the
    panel stays open; choosing it shows the message again.
  - Back from results, a failure, or a search returns to the languages
    (a search in flight is cancelled); from the languages it returns to
    Options on the Search Subtitles… row. Anything that closes Options
    closes the panel; a download on its way still completes, and its
    subtitle is still brought in. A search or its results for a file that
    no longer plays (playback moved to another version) give way to the
    languages, so a result is only ever downloaded for the file it was
    found for.
- **Back, first match wins:** cancel a seek or scrub; dismiss Skip Intro's
  pill; from Up Next, Keep Watching (tvOS); step Search Subtitles back to
  its languages, then close it; close the Quality picker, then
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
- **Shuffle in the player**, as tvOS's `PlayerViewModel` plays one
  (`PlayerShuffleState`). The player entry of a shuffle names it, and every
  item it plays belongs to it until the viewer leaves the shuffle; each
  plays from its beginning. In place of the next episode, Up Next offers
  the shuffle's next item, through the same panel, countdown, and start
  of the next item as any title; On Deck still shows in its row but never
  becomes the pick, and OK on one of its cards leaves the shuffle (the
  server deletes a shuffle left this way). After the first plan, and
  each time the panel opens, the player reads the shuffle again
  (`GET /api/v2/shuffles/{id}`): the server may replace a pick that can no
  longer play, and 409 means nothing can, which shows "More To Watch" or
  "Finished" with "Nothing else in this shuffle can play." An item counts
  as played at its first frame.
  - The panel adds, above the eyebrow, a 36 px white 10% capsule reading
    "Shuffling Movies" ("Shuffling Severance · Season 1" for a season) at
    78%; the eyebrow reads "UP NEXT AT RANDOM" with a pick and while one
    loads ("Picking at random"); Pick Another, a 330 px pill (Keep
    Watching's width, as on tvOS) 56 px after Play Now, the countdown ring
    56 px after it; and Stop shuffling, the
    toggle's style, 12 px after the toggle. A movie pick shows its release
    date and runtime as an episode shows its air date and runtime.
  - Play Now, the countdown, Play/Pause, and the phone's next-item command
    first send `POST /api/v2/shuffles/{id}/advance` with the item that
    played, then start the shuffle's new current item; Play Now and Pick
    Another are dimmed and do nothing until it answers. A failed advance
    leaves the panel open without a countdown and says "Couldn't continue
    the shuffle." (nothing for 409). Keep Watching or Back while it is out,
    from the panel or the remote's Back key, or a seek or scan from the
    phone or voice, gives it up, and its late answer starts nothing.
    Auto-play next turned while it is out holds: the pick starts with the
    viewer's choice, and a failed advance opens the panel with it.
  - Pick Another (`POST /api/v2/shuffles/{id}/skip` with the pick shown)
    stops the countdown until the answer, which starts it over with the
    new pick; a failure says "Couldn't pick another." and keeps the pick.
    While it is out, Pick Another stays lit and a repeat press does
    nothing, and Play Now or Play/Pause still advances, giving it up (tvOS
    disables Play Now only for an advance, `isStartingNextUp`).
  - A failed action's line (white 70%) sits 12 px under Keep Watching and
    Back, above the toggle, where tvOS puts `shuffleActionErrorText`.
  - Stop shuffling sends `DELETE /api/v2/shuffles/{id}` without waiting and
    closes the player. A shuffle's pages are not told which episode
    played: Back returns to the page the shuffle started from as it was.
  - One shuffle request is out at a time: an advance or Pick Another
    replaces the one before and any read, and an answer counts only while
    it is the one out and names the same shuffle.
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

- General: Profile Selection first, under Profile at Launch (section 5.4),
  with Automatic, Every Time, After 1 Hour, and After 12 Hours and the
  choice's description in the footer ("Use the last profile selected on
  this Roku. A protected profile can reopen without asking for its PIN.",
  "Show Who's Watching whenever you return to Silo.", "Show Who's Watching
  when you've been away from Silo for 1 hour.", and for 12 hours). It is
  this device's, saved on the Roku, and shows even when the server's
  settings fail to load. Then Show Title Art; Play Theme Music and Loop
  Theme Music, under
  Theme Music, when the server offers theme music
  (`GET /api/v2/catalog/themes/capabilities`), each written for this Roku
  (`profile_device`) as tvOS writes them, with Use profile setting.
- Playback: Resolution, Maximum Bitrate, Lower Quality When Buffering
  (where the server's contract lists `playback.buffering_quality_mode`),
  Audio Language, Auto-Play Next Episode, Skip Intros, Skip Credits,
  Auto-Skip Recaps, then, under Spoilers where the server's contract lists
  them, "Blur unwatched episode images" and "Hide unwatched episode
  descriptions" (profile scope; the focused row's footer gives tvOS's
  description and "Applies to episodes you have not started, on every
  device that uses this profile."), Skip Back, and Skip Forward; then a
  Connection section,
  where the server has it: the learned limit ("Limited to 44 Mbps after
  buffering on Oct 17") with Reset, hidden in Never, and Connection Speed
  ("48 Mbps · measured 3 minutes ago on Ethernet"), where OK runs Test speed
  and the footer gives the Auto budget, "Try again in N seconds" after a
  429, and a failed test, save, or reset (`docs/buffering-quality.md`
  section 5.5).
- Subtitles: Language, Behavior, and Show Forced Subtitles. A footer points
  to Roku's caption visibility and appearance controls. Then, under
  Metadata, Metadata Language (`catalog.metadata_language`, written for
  the profile), when the server translates descriptions for it
  (`GET /api/v2/capabilities/metadata-ai`, `available` and `allowed`), as
  tvOS shows its METADATA section. The options are "Library default" (no
  value) and the contract's suggested languages; its footer says
  "Translates descriptions and taglines into your preferred language when
  available. Titles are never translated." After a change Home reads its
  rows again the next time it shows.
- Server: the connected server address and Change Server (section 5.4's
  saved servers when another is saved); app version is
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
| Servers found on the network or the tailnet are listed under "No phone nearby?", above Enter server address | Enter server address alone | Discovery deferred (section 3.3); a Roku cannot join a tailnet |
| A server reached through a network identity provider (Tailscale) offers "Continue as {owner}" | Not offered | A Roku cannot join a tailnet, so no provider can name its owner |
| Auto with no port also tries `http://{host}:8090`, the stock compose port | HTTPS, then HTTP on the typed port once the viewer agrees | Each plain-HTTP attempt asks "Connect without encryption?" first (below); a silent extra HTTP probe would skip that |
| "Type on your phone": a keyboard notification appears on nearby iPhones and iPads | The same title over the Roku mobile app's keyboard | Roku's phone keyboard is its mobile app's |
| A code approved on a phone shows "Signed in as {account}" for a second before the profiles | The profiles open as soon as the session is installed, as after a password sign-in | The session's change moves the app on (section 6.2); a held navigation would be a second path into the picker |
| A failed password sign-in shakes the fields | The error line alone | Roku `Group` animations would add a frame-time cost to the form for one cue |
| The code is 72 pt Bold monospaced, its slashed zero apart from O | 72 px SemiBold tabular Inter, two spaces between its groups; letter codes from older servers in Bold | No monospaced face ships (the Versions menu row below) |
| The spinner is the system's spokes | The packaged arc spinner (section 5.8) | No system spinner on Roku |
| Choosing HTTP, or typing `http://`, connects without asking | "Connect without encryption?" asks first | Plain HTTP always asks on Roku (row below) |
| The Companion screen's consent and unreachable steps say nothing more | An `http` address adds "This connection isn't encrypted."; an alternate adds "{server} also answers at {alternate}." | `companion-pairing.md` section 5: the Roku reads both before its consent or choice |
| The pairing screens have no exit command; their buttons end them | Back denies at consent, closes a failure, and cancels the other steps | Back returns from every screen on Roku (criterion 4.6) |
| The TV's remote-control standby screen takes over while a phone is connected | No Connect a Phone entry is exposed in the avatar menu; the pairing route remains implemented. A phone connecting shows "<phone> connected" for four seconds and nothing else changes | The avatar menu omits the pairing entry for the first release. Roku apps cannot be opened by a phone (no ECP from phone apps), so there is nothing to stand by for; `docs/silocontrol.md` section 4 (every build since decision D-7) |
| A phone's profile handoff shows a "Playing as" card for six seconds | The player's notice card says "Playing as <profile> · From <phone>" for four seconds | The notice card is the player's one non-focusable card; `docs/silocontrol.md` section 4.2 |
| The sign-in screens offer phone sign-in over TLS (`_silopair._tcp`), and a phone on the sign-in screen approves the code it already shows | A phone push opens the Companion screen over the server or sign-in screen, drawn as tvOS's pairing screens (chip, copy, and card for each stage), which starts its own device login for the phone; the service is `_silopair-roku._tcp` over plain TCP | Roku has no TLS on listening sockets; `docs/companion-pairing.md` |
| A phone's setup ends on "You're all set" with Continue, which moves on after a short dwell | "Signed in", then the profiles once the phone says done or three seconds pass | The receiver stops after the sign-in (`docs/companion-pairing.md` section 5) |
| Calendar shows all seven days, an empty one titled at reduced opacity over "Nothing scheduled" | Only days with events have a row; the week strip's dots mark them, and the audio guide says "Nothing scheduled" on a day without | A `RowList` row needs a focusable item, and a placeholder card would take focus for nothing |
| An empty Calendar week offers the other two filters as buttons | The message alone; the filter is two presses up | The empty state has one button (section 5.8), and either filter is already on screen |
| The Calendar's filter is kept on the device | It is kept until the app closes | The registry keeps the session and Browse's choices (AG-382); a filter is one press to set again |
| The Calendar sends the device's IANA time zone | Roku's own zone name (`roDeviceInfo.GetTimeZone`, such as "US/Eastern" or "Europe/United Kingdom") mapped to its IANA zone; else a whole-hour `Etc/GMT` zone from the TV's offset; else none, which the server reads as UTC | Roku does not report IANA names (AG-400) |
| The For You menu lists Watchlist, Favorites, then Recommendations | Recommendations first, then Watchlist and Favorites | The owner's order (2026-10-28): the tab's own page leads its menu |
| Custom PIN keypad | Roku `DynamicPinPad` inside the same layout | Criterion 4.12 requires Roku keyboards for PINs |
| Platform or custom text fields | Roku dynamic keyboards, with voice entry | Criterion 4.12 for credentials; Roku's standard for search |
| tvOS's keyboard is full screen; Android TV's rises over the lower screen | A `DynamicKeyboard` panel covers the screen, with the address chips, Show/Hide, and Done below it | Roku sizes `DynamicKeyboard` itself; the panel keeps the text, voice entry, and shortcuts together |
| The address keyboard has no shortcuts | Chips `https://`, `http://`, and `.com` under the keyboard (Android TV) | Typing a scheme on a Roku remote's keyboard is slow; the chips are one press each |
| "Connect without encryption?" appears once the HTTP address has answered (Android TV) | It appears before the first plain-HTTP request | The setup check stores a server as soon as it answers, so the viewer agrees first |
| An older server is an inline error on address entry | A "Server update required" screen, whose Change server returns to the typed address | Section 7.1 |
| A server with neither password sign-in nor device sign-in offers only "Continue as" (network sign-in) | An explanation with Try again and Change server | No network sign-in on Roku (above) |
| "Open {name} automatically?" is an alert over the picker, before Home | A dialog over Home, once Home has rendered | Choosing a profile moves the app to Home at once (section 6.2), and Home's loading and `AppLaunchComplete` never wait for the answer (AG-574) |
| Time away runs from the moment Silo goes to the background, and a return to the foreground applies it | From the last use the app stamped (at a pick, then every five minutes under a timed choice), and from the last tick before a Roku player's suspend | Roku apps are closed rather than backgrounded, and give no notice when the viewer presses Home (AG-572) |
| An explicit Switch Profile marks the picker as required, so quitting on the picker never reopens the previous profile | Switch Profile keeps the open profile while the picker shows, and Back returns to it; quitting there reopens it under Automatic | Roku's Switch Profile pushes the picker over the open profile rather than closing it (section 5.3, AG-576) |
| Showing the picker this way forgets the one profile token tvOS keeps | It forgets every profile token the device keeps | Roku keeps tokens for several profiles of the login session (section 7.3), and any of them would open its profile without a PIN (AG-573) |
| A PIN lockout shows the server's text (Android TV) | The minutes left from `Retry-After`, as tvOS words them | Section 7.3 |
| The brand light drifts slowly | A still image of the same mesh at rest | Packaged art (section 5.4) costs no frame time on low-memory devices |
| Preset (SVG), emoji, and DiceBear avatars are drawn | The name's initial on the profile's colour | Roku cannot draw SVG or colour emoji, and the client does not rewrite avatar URLs |
| New Profile has Style and Avatar sections: DiceBear presets in an 18-avatar grid with Shuffle | No avatar choice; a new profile has none, so every client draws its initial | The previews are PNG URLs the clients build on api.dicebear.com: AGENTS.md allows no client-invented URLs, and the privacy policy says the app sends nothing to a third party. The server's own preset URL is SVG, which Roku cannot draw (assumption AG-520) |
| Add profile is always the picker's last tile | It shows only when the household has a primary profile (Android TV) | Only the primary profile may create profiles (section 7.3) |
| Create Profile is disabled until there is a name and a whole PIN | It stays enabled, and answers with tvOS's own alerts for what is missing | CapsuleButton has no disabled state, and the alerts say what to fix |
| New Profile's section captions are 13 pt, over a soft white glow | 19 px (Settings' section captions), on plain black | 13 px is hard to read across a room; the glow would be another packaged image |
| The PIN field types with the number pad | The Roku keyboard, its digits kept | Roku's keyboard; the field keeps four digits as tvOS does |
| The top bar's avatar and the avatar menu's header draw a profile without an image as its initial on white at 16–18% | The initial on the profile's colour, as on the picker | One avatar drawing from the picker to the shell keeps a profile's colour after the picker (parity review P-17) |
| Avatar images are round everywhere | Square on devices without OpenGL | `MaskGroup` does not clip there (implementation plan section 4.6) |
| The PIN screen's avatar is a near-black disc with the initial in `#EDEDED` | The profile's colour, as on the picker | One avatar drawing from the picker to the shell (parity review P-17) |
| The brand light changes stage for sign-in and for the profiles, and takes the server's accent or the colour of the profile being opened or PIN-checked | Setup, sign-in, and messages share one mesh, the picker and PIN another, without a server's or profile's colour | Each stage or colour would be another packaged image of about 60–80 KB |
| Inline errors lead with an exclamation mark, and the picker's buttons carry icons | Errors and the picker's buttons are text only | No icon art ships for them |
| The server card's mark can be the server's logo | The name's initial on the warm tile; over setup, the update screen's card shows the host just checked | The logo would be one more image per first-run screen |
| "This server isn't ready" marks its server card with a server glyph on a dark tile | The host's initial on the warm tile, as on sign-in | No icon art ships for it |
| First-run headlines and the picker's title are set 2 px and 1.6 px tighter than the font | Inter at its own spacing | Roku `Label` has no letter-spacing field |
| Compact buttons (the picker's buttons, PIN's Cancel, the address chips) are 57 px tall | 56 px, the top bar's tab capsule | Even heights scale to HD without half pixels, and the art is shared |
| Sign Out's confirmation also offers "Sign Out & Remove Server" | Sign out and Cancel, in the avatar menu and on the picker alike; servers are removed from the saved servers list (section 5.4) | One place removes a server, and it names the server that takes its place |
| Manage Servers has a trash button beside each server | A compact plain Remove beside each row, and Options (*) on the row | Roku has no trash icon art; Options is the remote's usual way to act on an item |
| Change Server always opens the server list | It opens the saved servers only when another server is saved, otherwise address entry | A list holding only the current server would add a step before typing a new address |
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
| Avatar menu rows, and the detail page's More menu rows, have an icon before the label | Labels without icons; More's rows keep the Versions menu's empty check column | No icon art ships for the menus; More reuses the Versions menu (section 5.6) |
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
| Home and a library's Recommended show every nonempty section the server returns, each with at most 20 cards and an Explore all card | At most 20 rows with cards; later sections do not show. Rows hold 20 cards and the Explore all card, as on tvOS; For You and Calendar rows hold 40 cards | Implementation plan section 4.8 bounds the metadata the rows keep, as well as their textures, on 512 MB devices |
| The row page reads 60 cards a page | 40, as Browse | Implementation plan section 4.8, as Browse (AG-631) |
| The Explore all card has a 0.5 px white 8% outline | No outline | Half a pixel does not draw at 1080p, and the card's frame already rounds its corners (AG-632) |
| A server's `section_item_limit_max` is remembered across launches, so the first Home read asks for short rows | Read once per server each session, before the first rows, as Android TV does | No registry write for a value one request finds; the first rows wait at most 3 seconds for it (AG-633) |
| The row page's empty and unavailable states have no button; Menu goes back | They have Back | A Roku state view needs a focus target, as the collection page's empty state has (AG-634) |
| A mixed library's Movies or Series view keeps its type on the row page, reading on until six new cards match | Both types show, as on the rows | The rows do not narrow a mixed library's sections yet (AG-280), and the page shows what the row shows (AG-635) |
| The row page keeps the pages it read when it shows again | It reads the row again after playback or a personal change | Continue Watching and Next Up move with playback, and Home and the list pages read again then too (AG-637) |
| Search reads 60 results a page and Browse 100 | 40 each | Implementation plan section 4.8 bounds the metadata kept on 512 MB devices |
| Home re-reads its sections whenever it is shown again, except from detail, and on the server's push events | Home re-reads its sections quietly 3 seconds after it is next shown once the player has closed | The first release has no push channel; plan section 4.5 ties the refresh to playback |
| A failed Home shows the server's message, or "Failed to load home sections" | The message every browse page uses for a failed load, with Retry | Section 5.8; the client's copy lives in `locale/` |
| Library pages draw skeletons while they load | A centred 128 px spinner | One `Poster` instead of a placeholder per card on 512 MB devices |
| On a mixed library, each Recommended section shows only the tab's type | Both tabs show every item of a mixed library's sections | Not built (AG-280): the server's section reads refuse a type, so the client would filter each section and refill it page by page, as tvOS does, which `BrowseRows`' loading and dropping of rows around focus does not yet support |
| Collection groups appear as vertically stacked grids with uppercase headers | One grid of every group's collections in order, without headers | The owner's choice (2026-10-28): no toggle between groups; Roku's bounded grid has no section headers |
| The Sort, Filter, and Shuffle pills, each with its icon, are the first item of the Browse grid and scroll away with it | The pills stay above the grid, without icons, and the grid keeps its focused row at the top (fixed focus) instead of scrolling the page | `MarkupGrid` has no full-width header item, and no icon art ships |
| A collection's Shuffle button, with its shuffle icon, stands beside the item count above the grid | The Shuffle pill, without an icon, has the place Browse's Sort pill has, and the count stays on its own line under the title | Section 5.5; the collection page's title and count already sit where tvOS's large title does, and no icon art ships (AG-550) |
| The filter panel's rows carry SF Symbols: chevrons, a cross on Clear, an arrow on Reset filters, and a check on Done | Its radio, box, and check marks are drawn art; the chevrons and Clear's cross are Inter's ‹, ›, and ×; Reset filters has no mark | No icon art ships for the rest, and the packaged Inter subset has those three glyphs (assumption AG-380) |
| A filter set whose `groups` pass 32,768 characters goes to `POST /api/v2/catalog/query` | Every Browse read is a `GET` | A remote picks a value at a time; it takes hundreds of values to pass the limit (assumption AG-380) |
| A shuffle that cannot start shows the alert "Couldn't Shuffle" with why | "Couldn't Shuffle." and why show top centre for four seconds | Roku's passive notice line needs no focus, as for a refused personal change (assumption AG-381) |
| The Shuffle pill, Up Next's "Shuffling" badge, and Pick Another carry a shuffle symbol | Text only | No icon art ships for it |
| The focused alphabet rail is a 96 px column the grid makes room for, its chips centred in it | The grid stays where it is under the rail, and the 38 px chips keep to the column's right edge (x 1850–1888), clear of the grid's last column | Reflowing the grid as focus enters the rail would lay out every card again |
| Focus enters the rail at the letter nearest to where it was (the focus engine) | At the chosen letter, else All | Roku has no geometric focus engine; the chosen letter is where a viewer filtering by letter goes next |
| A library tab opens the library chosen last across launches (tvOS and Android TV) | The library chosen last is remembered until the app closes; Browse's sort and filters are remembered across launches, as on tvOS, and its letter only while its page stays on the stack | The session's registry section holds only the session and profiles (plan section 4.3); Browse's choices have a bounded section of their own (assumption AG-382) |
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
| More › Show Series Info (tvOS) or a Show capsule (Android TV) puts the series back in the hero | The hero keeps the last episode focused | More ships without Show Series Info (the "More also offers" row below; scope, sections 3.3 and 3.4), and section 5.6 lists only season pills |
| A hidden episode still is blurred at radius 24 (Android TV: a blur over a 256 px decode, or the ThumbHash alone before Android 12) | The still decodes at most 16 px wide (catalog.spoilers.blurSize) and is stretched to the card, which Roku's renderer smooths into a blur of about the same strength | SceneGraph has no blur, the server's image API has no blurred variant, and a ThumbHash drawn as a picture would need a decoded file per card on a Task; the small decode also costs less texture memory than the sharp card (AG-462) |
| The spoiler settings the server last confirmed are cached per server and profile across launches, so a cold start hides at once | Kept only for the session: a cold start hides nothing until the shell's read answers (two small requests, usually before Home's rows); returning to a profile read earlier in the session applies its answer at once | Roku's 32 KB registry is already split between the session, saved servers, and Browse's preferences (AG-465) |
| The spoiler settings refresh on return to the foreground | They refresh when a page with the top bar starts, and when Settings reads or saves them | A Roku channel is not resumed from the background (AG-466) |
| The series hero hides an episode's description only when both its rail row and its playback detail say it is unwatched | The rail card's watch state decides | The page reads an episode's watch detail only once focus rests on it (section 5.6); the rail card is the state on screen |
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
| Info's STREAM column lists Route, Audio, Subtitles, and the chapter; Stats shows buffer, network, and engine figures; Info and Stats page with Down and Up | STREAM adds a File row (container, the plan's bitrate, size) after the chapter, and Route names the plan's delivery; Stats shows the plan's source and the `Video` node's state; the panes do not take focus, and the overview takes the whole lines left, the last ending in an ellipsis | Roku's player reports neither tvOS's buffer and network figures nor an engine name; the device runs read the file facts; with the overview clamped both panes fit the 380 px panel |
| The HUD's lists scroll natively and end on part of a row at the panel's edge; the Quality picker centres the checked row and shows about four and a quarter rows | Columns and the Quality picker show whole rows only, a column scrolling a row's top to its own and the picker a row at a time; the picker opens with the checked row second of its four where the list allows | Hardware run 26: a row or line cut at the panel's edge read as a fault (decision AG-292 (1); assumptions AG-294, AG-295) |
| Subtitles draw under the controls: the controls and their gradient cover a cue while they show | Roku's captions are hidden while the controls show (not over Options or Up Next), and return as they hide; content within 3 s of its first frame is left as it is | Roku draws captions above the UI at a place of its own, so a cue crossed the scrubber and the time row (hardware run 26). The node's own `suppressCaptions`, which Roku documents for UI drawn where captions are, hides them without touching the caption mode or the subtitle selected (assumption AG-293) |
| The Video tab always has rows: Speed (0.75× to 2×) and Aspect (Fit, Fill, Stretch), kept in `player.playback_speed` and `player.video_gravity` | No Speed or Aspect rows: video plays at 1× and fits the screen, as Roku draws it. Without a choice of quality the PLAYBACK column shows the quality as a line, and a movie's Video tab has no rows. A phone's `set_playback_speed` and `set_video_gravity` are refused ([`silocontrol.md`](silocontrol.md) section 6.5) | Roku documents no playback-rate control and no scaling or cropping for the `Video` node (developer documentation and Roku OS 12.0–15.3 release notes, read 2026-10-28). Its one rate field, `playbackSpeed`, is undocumented: Roku switched it off for every app in 2024 and says not every device can play at other speeds, and other channels report models that stop at 2× (assumption AG-433). The node keeps the picture's shape inside its rectangle, so Stretch cannot be drawn; Fill would rest on a node larger than the screen, which nobody has shown to crop on hardware and which screenshots cannot show, since they never capture the video plane (assumption AG-434) |
| Options' Subtitles tab shows only with tracks or a subtitle tool | Stats and Subtitles always show | A fixed set of tabs keeps Left and Right predictable while the player's stats arrive, and Subtitles holds Roku's caption modes even for a title without subtitle tracks (criterion 4.8) |
| A downloaded subtitle is registered on the playing stream at once, at a stream URL the player builds, and selected without a reload | The player asks the server for a plan that lists it (a `track_change` keeping the selection), then chooses its row; the title reloads at the position to carry the new sidecar (section 9.7) | The client never builds a stream URL (AGENTS.md), and content on the `Video` node never takes another track (hardware run 19) |
| Search Subtitles… sits in the Subtitles pane's OPTIONS column, beside AI Subtitles… | It ends the CAPTIONS column | Roku's second column holds the caption modes (the row below); AI subtitles are not built (section 3.3) |
| A search result's score is a badge coloured by tier (70 and up green, 40 amber, else red) over "Match" | "88% match" leads the result's second line | The panel reuses the Options panel's text rows; `playback.subtitleSearch.scoreTier` keeps tvOS's tiers for a badge later |
| The language list is the app's whole playback-language catalog | 43 languages, the ones the client's strings name | The client names no others (`language.*` in `locale/`); a search takes any language the server knows, so the list can grow with the strings |
| Options' Subtitles tab has TRACKS and OPTIONS columns | Its second column is CAPTIONS: Off, On, On replay, and On mute (Roku TVs only), Roku's global caption mode; while a subtitle is burned into the video, or captions Off set one aside, only Off and On, and Off asks the server for the stream without it. On mute is checked whether Options or Roku's own menu set it, and stays checked as the TV is muted and unmuted | Criterion 4.8 (plan section 6.10); burned-in pixels cannot follow a caption mode |
| The remote's Menu or Settings key opens the player's options (Android TV) | Options opens from the controls' Options button and from Down with the controls hidden; on a Roku TV, `*` during playback opens Roku's own menu, whose Accessibility entry holds the caption setting | Roku TVs take `*` during full-screen playback whatever has focus (hardware run 6, assumption AG-117); Roku remotes have no Menu key |
| Tracks change only in the app's menus | Roku's own `*` overlay, reached with the controls hidden, can change audio and subtitles; a change that names one inventory track becomes a `track_change`, and any other is undone | Criterion 4.4 keeps the overlay; the plan owns track identity (section 9.7) |
| Turning captions on has no effect on the playing stream | With subtitles Off, turning Roku's captions on (in Options or Roku's own menus) reloads the title at its position, without the subtitle sidecars it carried | With captions on, Roku shows a carried track in the caption language whenever none is selected (`Video.currentSubtitleTrack`) |
| A subtitle the profile's preferences choose shows at once | It is selected, and shows while Roku's caption mode is on | Roku's caption mode governs captions (criterion 4.8), and the client does not turn it on at load |
| A sign that an SRT cue places at the top with an override tag (`{\an8}`) shows at the top (Android TV, whose Media3 SubRip decoder reads the tag) | It shows at the bottom, without the tag | Roku documents no placement for SRT cues and prints override tags as text (hardware run 16, Roku drawing an MKV's own track), with no documented way to hide them; the client removes the tags from SRT sidecars and never lets Roku draw a container's track itself (section 9.7) |
| One intro, credits, recap, and preview per file (Android TV) | Every `marker_segments` range, each skipped or drawn on its own | Section 9.8; the server's collection replaces the single markers |
| The scrubber has rounded ends, a buffered range, chapter ticks, and one band, the intro's, in cyan | A square track with the played range, the chapter ticks, and the intro (tvOS's cyan), recap, and credits bands | Sections 5.7 and 9.8 name three bands; the ladder's 100 ms tick only moves `Rectangle`s |
| A chapter row's number is 20 pt rounded SemiBold and its time 20 pt; the playing chapter's glyph is SF Symbols' `play.fill` | Both 22 px SemiBold, the setting value's style; the player's own play glyph, 18 px | Roku ships no rounded face, and the panel's existing styles keep the font set small (assumption AG-432) |
| A seek session started with the controls hidden shows only the top-centre hold indicator | Only a held Left or Right does; Rewind and Fast-forward show the controls and scan on the scrubber, with the 340 px preview card over the scrub point | Testers read the indicator's 480 px thumbnail as small next to the scrubber that Left and Right bring up, and the transport keys are the Roku remote's usual way to scan |
| Holding Left or Right on the focused scrubber starts a fixed-rate auto-seek; OK there commits a scrub and then toggles play/pause | The same 300 ms hold and rate ladder as with the controls hidden; OK commits, or toggles when nothing is pending | Section 5.7's key table; Roku documents no key repeats for a held key |
| No Replay key | Replay skips back by the skip-back value clamped to 10–25 s, with "Instant replay" captions for the replayed span once its seek commits; a Replay that Back cancels, or whose merged seek lands past where it was pressed, shows none | Certification criteria 4.8 and 4.9 (implementation plan section 6.10) |
| Scrub previews come from the server's sprite sheets or, without them, from frames the player cuts from the stream | The server's sheets only; a title without them shows the time and "Previews aren't available for this title" | Roku apps cannot read frames from the `Video` node |
| A sheet decodes at full size, and only the latest one stays decoded | A sheet decodes within 1600 px on each side (a default 300 px thumbnail at 160 px, drawn 320 px wide on the card and 480 px held); the sheet in use and the next one in the direction of travel stay loaded, the sheet in use alone on the low tier | Texture memory on 512 MB devices and sheet changes at 32× (plan sections 4.8 and 6.9; hardware test H20); the drawn size costs no texture |
| The next episode's still fills the screen behind Up Next, dimmed, around the video | No still: the rest of the screen is black | Roku draws video beneath the UI, so a full-screen image would cover the shrunken video |
| A shuffle's next pick that fails to start returns to Up Next with "Couldn't start the next pick. Try again or go back." | The player's failure screen shows, with Retry and Go Back, as for any next item | Roku starts the next item as a new session of the same player (assumption AG-100), whose failure screen serves every start (assumption AG-381) |
| A shuffle plays every part of a multi-part item before moving on | A multi-part pick plays as its start plans it, from its beginning | The Roku player chains no parts on any start (assumption AG-381) |
| The auto-play toggle shows with any pick | It is hidden, and nothing counts down, while Roku's autoplay setting is off | Plan section 6.10 (certification) |
| Back on Finished (nothing to play) replays the end, as Keep Watching does | It leaves the player | Roku's Back leaves playback; replaying would keep the viewer on a screen whose only button replays |
| Keep Watching after the end replays the last 10 s in the same session | It starts the item again 10 s before its end, as a new session | Roku's session has stopped by the time its video ends |
| Siri (tvOS) and the Google Assistant (Android TV) drive the system player's transport | Roku voice transport commands (`roInput.EnableTransportEvents`) take the remote's paths: "play" and "pause", "fast forward" and "rewind" start the speed ladder, "replay" is Replay, "rewind 30 seconds" or "forward 10 minutes" seeks, "start over" seeks to the start, "skip intro" presses Skip Intro, or else the Skip Recap or Skip Credits pill, "next" is Up Next's Play Now, and "stop" leaves the player. A seek or scan while Up Next shows closes it as Keep Watching does; after the end, "start over" and a seek replay the title as a new session. "Turn on captions" changes Roku's global caption mode, which the player already follows (spec 9.7) | Roku delivers voice commands to the app as transport events and expects an answer for each within 5 s (`source/playback/voice.bs`); criterion 4.11 does not require them below its threshold |
| An On Deck item without a backdrop or still reads its detail for one, and is left out without | It shows as Home's Continue Watching card does, its poster standing in | A detail read per card is avoided; Home's cards make the same choice |
| A screen-level error puts a headline for its cause ("Something went wrong", "Not found") over its message, with Try Again | Home, the libraries, detail, and the profile picker show their one-sentence message as the error's title, without a second line, and Search its own title over a line; the button reads Retry (Try again on the picker) | The client's error copy is one sentence per screen (`locale/`); a copy change of its own adds headlines by cause (assumption AG-285) |
| The person page scrolls as one view: the header scrolls away as focus moves down the filmography grid | The page moves up once as focus enters the grid, so the grid sits at Browse's place (y 332) with the pills above it; the grid then keeps its focused row at the top (fixed focus), as Browse does | `MarkupGrid` has no header item; one move keeps the pills and the grid's two rows on screen (assumption AG-340) |
| A person page reads 60 credits a page into a lazy grid, and All sends no media type, so a person's audiobooks and books list too | 40 a page into Browse's bounded grid (`catalog.grid`), holding at most the memory policy's pages; All sends `type=video` (movies and series) | One memory budget for every paged grid (plan section 4.8); this client has no audiobook or book pages to open |
| A person whose biography, photo, or birth date is missing gets a provider refresh (`POST /api/v2/catalog/people/{id}/refresh`) and a "Loading metadata" capsule while the page polls the person every 3 s for up to two minutes | The person is read once; what the refresh finds shows the next time the page opens | The phase keeps server writes out of person pages; a plain person read already queues a refresh when one is due (`prefetch` in the contract) (assumption AG-341) |
| The filter pills grow 1.06× with a 2 px outline when focused, rest at `#15171C` 55%, and are `#0E0F12` when selected | They are the season pills: white 5% at rest, white 20% selected, white with black text when focused, without an outline or a scale | Section 5.2's pill rule; one pill row component on detail and person pages |
| A portrait photo that fails to load shows the image view's missing-art placeholder: the person's ThumbHash, or a symbol | The name's initials show, as they do without a photo | One fallback for both cases, as the profile avatars do; the page does not decode the person's photo ThumbHash (assumption AG-340) |
| The person page is blank until the person is read; a failure shows the error's headline for its cause | A spinner shows until then; "Person not found" with Back, or "Can't load this person." with Retry | Section 5.8's loading state; the client's one-sentence error copy (assumption AG-285) |
| Watchlist and Favorites are root pages under the top bar, which stays with the avatar; History is a pushed page | All three are pushed pages without the bar; Back returns to the page below with focus on the avatar | One page type for the three lists; the bar's selected tab has no state for a page that belongs to no tab |
| Watchlist and Favorites read the whole list (up to 100 pages of 200) into an 8-column grid of 176 px posters; History reads `GET /api/v2/catalog?source=history` 60 at a time | Each list reads its own endpoint (`/api/v2/watchlist`, `/api/v2/favorites`, `/api/v2/history`) 40 at a time into Browse's six-column grid of 260×390 posters, holding at most the memory policy's pages | One bounded grid (`catalog.grid`) and its memory budget for every paged list (plan section 4.8); the contract's own list endpoints |
| Watchlist's empty state says "Tap the bookmark icon on any item to add it here", Favorites' "Tap the heart icon on any item to add it here" | "Add titles from a detail page and they will appear here." and "Add favorites from a detail page and they will appear here." (the iOS words), with a Back button | A remote has no tap, and a page without the bar needs a way out from its empty state |
| A card's context menu (press and hold) offers Play or Resume on Continue Watching, Mark as Watched, Favorites, and Watchlist, and on Home Remove from Continue Watching or Next Up; a Watchlist or Favorites page drops a card whose flag turns off. History offers no removal | Options (*) on a focused card opens the same menu, in the same order, on Home, the library tabs, Browse, collections, Search, person pages, More Like This, and the Watchlist, Favorites, and History pages (`source/catalog/cardMenu.bs`); Favorites and Watchlist show only when the server offers the lists. History adds Remove from History (`POST /api/v2/history/remove`, the card's item, which for a series covers its episodes). A change shows on the card at once and goes back with the notice if refused; Home and Recommended read their rows again after one. A card read before another page's change takes the change when its menu opens | Roku has no press and hold: a list consumes OK on press. `*` is Roku's options key. Development builds keep `*` on Home's bar for the diagnostic screen |
| An episode card's context menu marks that episode watched or unwatched | More on a series page has Mark Episode Watched or Unwatched for the episode Play plays (the active one) | Roku's episode rail has no context menu; the action row already names that episode |
| More also offers Find Trailers, Show Series Info, and Watch Party where they apply | Shuffle, Favorites, the watched rows, and Translate Description while the page offers it (section 5.6) | Scope (sections 3.3 and 3.4); Find Trailers (`POST /api/v2/catalog/items/{id}/trailers/refresh`, offered by `GET /api/v2/capabilities/trailers`) fetches remote videos, which Roku leaves out (next row) |
| Trailers & More also lists the item's remote trailers and clips (`videos`, YouTube only), captioned "YouTube" with YouTube's still, which open in the YouTube app; tvOS drops them when the app is not installed | Only the local extras, which play in Silo's player | Certification criterion 5.3 forbids opening another app, and the server gives a remote video only as its site and key (`ItemVideoInfo`), with no stream it hosts or relays (silo-server `3e2d306b2`; assumption AG-361) |
| A theme fades in to 35% of the volume over 300 ms and fades out as it stops | It plays at the TV's volume and starts and stops at once | Roku's `Audio` node has no volume or gain field, only `mute` (AG-363) |
| A theme pauses while the app is in the background and resumes on return | Pressing Home closes the app, and the theme with it | Roku keeps no app running in the background without Instant Resume, which this client does not use |
| Themes in MP3, AAC or ALAC in MP4, FLAC, and WAV play as they are | MP3, AAC in MP4, M4A, or ADTS, and FLAC play as they are; the server converts the rest to AAC in MP4 | The `Audio` node's stream formats are mp3, mp4, es.aac-adts, flac, and hls (assumption AG-362) |
| Play Theme Music and Loop Theme Music show whenever the server knows the settings, and Loop is disabled while Play is off | Both show only when `GET /api/v2/catalog/themes/capabilities` answers available, and Loop can be set while Play is off; each also offers Use profile setting | Section 3.3: Settings shows only what the client can use here, and Roku's Settings rows have no disabled state (assumption AG-364) |
| Watchlist and Favorites always show (neither tvOS nor Android TV reads a capability) | They show only when `GET /api/v2/capabilities/personal-lists` answers `available` and `allowed`: the avatar rows, the Watchlist button, and More's Favorites row | The phase gates them on the server's capability (assumption AG-323); an older server without the document hides them |
| A refused change shows the alert "Couldn't Update Item" / "Your change wasn't saved. Please try again."; an unanswered one is held until the viewer discards it | The change goes back and "Couldn't update item. Your change wasn't saved." shows top centre for four seconds; an unanswered write counts as refused and nothing is held | Roku's passive notice line needs no focus; no held-change list is kept (assumption AG-326) |
| The connection speed test times one streamed download in 500 ms windows, following the probe's redirect without credentials | Back-to-back chunks, each timed whole and spread over the windows, which reads low by the gaps; only against a server with `bandwidth_probe_location_v1`, whose credential-free URL is fetched without the redirect | Roku shows no bytes inside a transfer, and forwards profile headers across a redirect (assumptions AG-391 and A-14) |
| Buffering is told from a slow device by the buffered duration, and plan summaries survive the app's exit | No renderer waits; a progressive plan measures no throughput, so it lowers before its first frame only on its 20 s deadline's failure path; a plan the Home button ends sends no summary; no foreground check | Roku reports only a fill percentage and segment downloads, and gives a channel no exit callback or background state (AG-390, AG-391; Android TV keeps no exit journal either) |
| Search lists "Available to request" under the library's results: the first 12 titles of the first page, while the query is longer than one character | A fourth segment, Request, searches titles to request page by page into the same grid | Search's results are an endless grid, so nothing below them would ever show; a segment is one press from the query (assumption AG-406) |
| The Requests hub has no See all for Discover rows (`.requestDiscoverRow` draws nothing on tvOS; Android TV has it on phones only) | A trimmed Discover row ends in See all, which opens the whole row page by page | The server pages any row since #3193, and a trimmed row otherwise hides titles the admin chose (assumption AG-402) |
| tvOS and Android TV skip the studio, network, and genre rows | They show as rows of brand cards, and a brand opens its titles (a genre's movies) | The contract has a client draw a brand row from its brand list; the web does (assumption AG-403) |
| The hub reads every page of the account's requests, and fails whole if either read fails | "Your requests" reads the 50 newest, loads as its own row, and is left out when its read fails; See all opens the rest in My Requests | One page of 50 bounds the row's memory (plan section 4.8); one row's failure does not hide Discover (assumption AG-404) |
| My Requests (`.mine`) groups the requests in rows by In progress, Needs you, and Available; tvOS reaches it only from iOS | A grid of every request, newest first, opened from See all on "Your requests" | A cursor-paged list cannot be grouped without reading it all; the row on the hub already groups the newest (assumption AG-405) |
| A long press on one of the viewer's pending requests offers Cancel Request | Options (*) does | Roku has no press and hold (as the card menu, section 5.3) |
| The first Discover row carries the eyebrow "DISCOVER" over its title | Each row shows its title alone | A `RowList` row has one label (assumption AG-409) |
| The hero shows a request's stage on the four-step track, and the request page an eyebrow ("Not in your library", "Requested") | The hero shows the stage as its badge; the request page's status strip has the track; no eyebrow | The hero's badge line is the place for a short status; the library hero has no eyebrow (assumption AG-409) |
| The request page finds the viewer's request among every page of `GET /api/v2/requests/mine` | It reads `GET /api/v2/requests/{id}`: the request the title names, or the one the opened card was | One small read in place of up to 100 pages; Request Again needs the ended request, which only a card of it names (assumption AG-407) |
| Notify Me's notices end with a period (tvOS); Android TV says "Notify me when available" | tvOS's words | tvOS is the reference (section 5.1) |
| People and the Audiobooks chip in search; Home row reordering; Watch Party in the avatar menu; Manage on the profile picker; Create Account on sign-in; the Home hero's air date and cast line; the marker on AI-translated subtitle tracks | Not in the first release | Scope (sections 3.3 and 3.4); deferred controls keep their positions when added |
| The description translation's status ("Translating…", "Translated by AI") follows the translate symbol | The words alone, under the detail synopsis and leading Home's meta line | No symbol art ships for it; the words carry the meaning |
| Each Featured card on the marquee runs its own translation, so several can run while focus moves along the row | One at a time: resting on another Featured card stops the run before it starts the next, which may start again when its card shows again | Keeps the requests and timers a 1 GB Roku holds to one run; the server's on-view budget per account is small (5 a second, 30 a minute) |
| A metadata language change drops every cached item, section, and grid, and Home re-reads its rows | Home reads its rows again when it next shows; library pages and pages under Settings keep their text until they are read again | Roku keeps no item cache; a library page reads its rows each time it opens |
| The AI capability is read again on every foreground and session refresh | Read once per server and profile in a session, by the first of Home, the detail page, or Settings | A Roku channel has no foreground event short of a relaunch, which reads it again (assumption AG-603) |

### 5.10 For You and Calendar

Both are tab pages and stack roots like Home (section 5.3), built from tvOS
at silo-apple `ec9278f8` (`RecommendationsView`, `CalendarView`).

- **For You.** Drawn as Home is (tvOS draws both with its Skyline feed):
  the hero over the rows in the bottom band, from
  `GET /api/v2/recommendations/discover` with Home's artwork widths. The
  answer holds every row with all its items and is never paged, so its rows
  are never dropped or loaded one by one; a failed image, or rows older than
  the signed URLs' lifetime, reads the whole answer again quietly, once per
  load. The server titles the rows ("Because you enjoy Crime", "Top Drama",
  "Profiles Like You Enjoyed"); as on tvOS, a row titled "For You" goes
  first, empty rows are left out, and a row of episodes shows stills. OK on
  a card opens its detail page. With no rows the page says "No
  recommendations yet" / "Watch or rate a few titles to build your
  personalised recommendations." with Refresh; a failed read offers Retry.
- **Calendar.** Under the bar, at the side inset:
  - the filter, Search's segmented control (section 5.6) with Following,
    Trending, and All (sent as `following`, `trending`, and `everything`),
    Following first;
  - the week strip, 90 px below: the previous-week chevron, the seven days
    Monday to Sunday as 88×96 tiles 12 px apart (the short weekday over the
    date, a dot when the day has events; white 6% at rest, the selected day
    white 14%, today with a white ring, the highlighted item `#EDEDED` with
    black text), the next-week chevron, Today while another week shows,
    and the week's month ("June 2026", from its Thursday) at the right
    inset;
  - from y 380, a row of posters for each day with events, titled "Today",
    "Tomorrow", or "Monday, June 9".

  The week is read with `GET /api/v2/calendar?start=&end=&filter=&timezone=`,
  Monday to Sunday in the TV's time zone, as an IANA name (section 5.9). A
  card shows the series' or movie's title over "S5 · E14 · Title",
  "Season 2", or "Movie"; up to two badges (PREMIERE, NEW SEASON, FINALE)
  as white pills down its top left, its air time as a dark pill at the
  bottom right
  (`air_at` on the TV's clock, else the network's `air_time`, in 12- or
  24-hour form as the TV's clock is set), and the check disc when watched.
  OK opens an episode's series with that episode selected, a season
  premiere's series on that season, and a movie itself.

  Down moves from the filter to the strip and from the strip to the
  week's first row; Up moves back, and from the filter to the bar. In the
  strip, OK on a day focuses its row (or the next day's with events),
  the chevrons move a week and select its Monday, and Today returns to
  this week and today. The selected day follows the focused card. An empty
  week says so for its filter: "Nothing from shows you follow", "Nothing
  trending this week", or "Nothing scheduled this week", each with tvOS's
  second line; a failed read offers Retry. Returning restores the week,
  the filter, and the focused card; after the player closes the week is
  read again quietly. A new day or time zone reads the week again when the
  page shows.

### 5.11 Requests

Built from tvOS at silo-apple `791b1e0e` (`TVRequestsPage`,
`RequestDetailView`, `RequestsFeatureStore`, `RequestMediaCard`,
`RequestDisplayState`, `RequestProgress`, `RequestErrorCopy`), with Android
TV at silo-android `bda6cbdd7` as the second reference, against the server's
contract at silo-server `f133b241f` (the admin's Discover layout, #3193;
cards that no longer request, #3094; `docs/architecture/media-requests.md`
and `request-discover-rows.md`). The pure decisions are
`source/requests/` (`state.bs`, `detail.bs`, `api.bs`, `cards.bs`,
`map.bs`), with specs in `tests/requests/`.

- **Gate.** Each page with the top bar reads `GET /api/v2/requests/status`
  as it starts, as it reads the personal lists' capability, and keeps the
  answer for the server and profile it was read for (`requestsUi`).
  Requests shows only when `requests_enabled` is true, `allowed` is true,
  and `state` is `available`; a missing `allowed` or `state` reads as off.
  A failed read keeps what was known. Notify Me needs `follow_supported`
  too. When an answer turns Requests off, the bar drops the tab and a
  Requests page under it goes to Home; a request page whose action the
  server refuses with `capability_*` or `permission_denied` reads the
  status again and goes to Home if it is now off. Child profiles and
  quotas are the server's: a profile it does not allow gets `allowed`
  false, and a title over its rating ceiling is left out of every list.
- **The Requests tab** (`RequestsScreen`, `nav.route.REQUESTS`), last of the
  tabs, is a stack root drawn as For You is (section 5.10): the hero shows
  the focused card (its title, year and media type, TMDB rating or when it
  was requested, synopsis, and backdrop, with the request's status as the
  hero's badge), over these rows:
  - **Your requests**: the account's 50 newest requests
    (`GET /api/v2/requests/mine?limit=50`), in tvOS's order: in progress
    (pending, approved, queued, downloading, partly in the library), then
    needing the viewer (declined, failed), then in the library, newest
    first within each, without the cancelled. A card shows the poster and,
    under the title, a dot in the state's colour and the stage
    ("Pending", "Queued", "Downloading", "Partly in library", "Adding to
    library", "In library", "Declined", "Failed"). The row ends in See
    all, which opens My Requests, when the account has more. The row loads
    on its own, so a failed read leaves it out rather than failing the
    page; with no requests it is left out.
  - **The Discover rows**, from `GET /api/v2/requests/discover`, in its
    `row_order`. A title row (`tmdb_chart`, `tmdb_discover`, `tmdb_list`,
    `mdblist`) shows its `items` entry, up to 40 cards; a row without an
    entry or titles is left out. A card shows the poster (TMDB's `w342`)
    with the title and year under it, and a corner badge while the title
    has a request: a clock on amber (pending), an arrow on sky (on its
    way), a check on emerald (in the library), or "!" on rose (declined or
    failed). A row the server trimmed (`total_pages` over 1, or
    `total_results` over its titles) ends in **See all**, which opens the
    whole row (`GET /api/v2/requests/discover/rows/{key}?page=N`). A brand
    row (`studios`, `networks`, `genres`) loads its cards from
    `GET /api/v2/requests/discover/{studios|networks|genres}`: landscape
    cards with the brand's logo on its colour, or its name; OK opens its
    titles (`GET /api/v2/requests/discover/browse/{studio|network|genre}/{slug}`,
    a genre's movies). An unknown row type is skipped. A server without
    `row_order` gets its `items` in order.

  OK on a title or request opens its request page, or its library page
  when it is in the library and the server names the item
  (`library_content_id`). Options (*) on one of the viewer's pending
  requests offers Cancel Request (`POST /api/v2/requests/{id}/cancel`); a
  refusal shows as the notice line. While the page has nothing else it
  shows the spinner over "Loading Requests"; with no rows, "Nothing here
  yet" / "Use Search to find a movie or series to request" with Refresh;
  a failed read, the error with Retry. The rows are read again, focus
  staying on the same card, when the page shows after a request was made,
  cancelled, or confirmed elsewhere in the app.
- **Row page** (section 5.5's row page, `RowScreen`, `nav.route.ROW`): See
  all on a Discover row, a brand, and See all on "Your requests" (My
  Requests) open it with the row's title, reading page by page as focus
  nears the end. Discover rows and brands page by number: the row's
  `next_page` when it moves on and stays within `total_pages` (at most
  500), else the next page, reading past a page its filters emptied (three
  in a row at most); My Requests pages by cursor, 40 at a time, newest
  first. OK on a card opens it as on the Requests tab.
- **Request page** (`RequestDetailScreen`, `nav.route.REQUEST_DETAIL`),
  read from `GET /api/v2/requests/detail/{movie|series}/{tmdb_id}`: the
  library detail page's hero (section 5.6) with the title, the content
  rating's chip, year, seasons or runtime, TMDB rating, and up to three
  genres, the synopsis, and "Directed by" or "Created by" (two creators).
  The card's text and backdrop paint it before the read. Below it the
  action row:
  - the primary pill: **Request** (one press; no seasons, quality, or 4K
    choice, so the server requests every aired season the library lacks
    and the qualities its policy gives); **Request Again** after the
    viewer's own request was declined or failed; **Requesting…** while the
    request is out; **Open in Library** once the title is there; else the
    status, which does nothing: "Requested · Pending", "Queued for
    download", "Downloading", "Partly in your library", "Declined ·
    <reason>", or why the title cannot be requested ("Request limit
    reached", "You can't request media right now");
  - **Notify Me** / **Stop Notifying Me** (`PUT` and `DELETE
    /api/v2/requests/follows/{media_type}/{tmdb_id}`) when another
    profile's request for the title is pending or on its way and the
    server supports following; the line under the row then says "We'll
    let you know when it's available." or "Notification turned off.";
  - **Cancel Request** while the viewer's own request waits for approval.

  The viewer's own request is read from `GET /api/v2/requests/{id}`: the
  request the title names (`request_id`, given only to the account that
  made it), or the one the card was. While a request is out and not in the
  library, the status strip shows STATUS (a dot and the stage's long
  label, with the reason or the qualities), REQUESTED ("Sep 24"), and
  QUALITY ("1080p · 4K"), over the four-step track Requested, Approved,
  Downloading, In your library. More like this lists the server's
  recommendations. A refused action shows the server's own detail (a
  quota's counts, a conflict), or the client's words for validation,
  Requests turned off, a lost connection, or a refusal; it shows on the
  line under the row. `POST /api/v2/requests` is never sent again after an
  answer that leaves it unsure (a lost connection, a timeout, a gateway
  error without a problem, an unexpected success status): the button says
  "Not confirmed yet", the line says "We couldn't confirm the request.
  Check My Requests before trying again.", and the title is read again; a
  read that shows the request releases the hold. An unsure cancel hides
  Cancel Request and says "We couldn't confirm the cancellation. Reopen My
  Requests to check it.". A title the server no longer has, or one over
  the profile's rating ceiling (404), shows "This title is no longer
  available".
- **Search** (section 5.6) adds a fourth segment, **Request**, while the
  server offers Requests: it searches `GET /api/v2/requests/search?q=&media_type=all`
  page by page, leaving out titles the library has, into the same grid.
  OK opens the title's request page. With nothing found it says "No titles
  to request match your search."
- **Images.** The server sends TMDB image paths; the client puts TMDB's
  image base before them (`https://image.tmdb.org/t/p/w342` for posters,
  `w1280` for backdrops, `w780` on the low tier), as tvOS, Android TV, and
  the web do. Brand logos come as full URLs.

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
A server check or password sign-in under way when another screen covers its
screen stops, so its answer cannot change the session under it. A code
already approved still signs the Roku in: its poll in flight answers, and
the first sign-in to finish keeps the session (section 7.2). While a check
or sign-in runs on screen, the remote's keys wait for it, Back included, as
tvOS disables its buttons.

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

Sign-in leads with a code, as tvOS's does, and offers the password as the
alternative (section 5.4). Sign-in first reads
`GET /api/v2/system/setup`; a server that still needs its first
administrator (`needs_setup`) gets the "This server isn't ready" screen
(section 5.4) instead of the form. Any other answer, including an older
server's 404, goes on:

1. `GET /api/v2/auth/providers` lists sign-in modes, and
   `GET /api/v2/auth/device/capability` says whether the server offers
   sign-in with a code (`state` "available"). With a code, the screen
   starts a device login (`POST /api/v2/auth/device/start`) and polls it
   (`/poll`) as tvOS's `QRLoginViewModel` does: at once, then after each
   answer's `poll_after`, or the start's `interval` when an answer gives
   none, at least a second apart; an expired code is replaced in place for up to an hour,
   then the screen pauses until Show a new code; failures back off from the
   interval to 30 s, and a streak of 10 s (getting a code) or 30 s
   (polling) shows "Can't reach", 60 s of 429s "Too many sign-in attempts",
   while retrying goes on. A password sign-in stops the polling while it
   runs and withdraws the code when it succeeds; leaving the screen, Change
   server, or a new code withdraws the one before (`/cancel`). An approval
   installs the session as a password sign-in does. When `password_login`
   is false and there is no code, the server offers only browser sign-in,
   which Roku does not allow: the client explains that the server
   administrator must enable password sign-in, and stops there.
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
page says "Only TVE apps may use rendezvous linking". By the project
owner's decision of 2026-10-29, sign-in with a code (`/api/v2/auth/device/*`)
leads sign-in in every build anyway, so the Roku matches tvOS; the owner
accepts that this may fail criterion 2.2 at submission. Browser-based OAuth
sign-in stays excluded. Profile handoff reuses the device login for a
temporary session; it is on in every build by the project owner's decision
of 2026-10-25, before Roku confirms it
([`silocontrol.md`](silocontrol.md) section 2.3). Companion sign-in, where
a phone on the network signs a new Roku in with a device login it
approves, ships in every build too
([`companion-pairing.md`](companion-pairing.md) section 1). When a password
sign-in, the code on screen, and a companion approval overlap, the first to
finish keeps the session: the others' tokens are dropped, and open device
logins are withdrawn.

Saved servers: changing the server keeps the one left behind, with its
tokens, profile tokens, account, and remembered profile, in a second
registry section (`silo.servers`, 8 KB, at most seven servers besides the
current one). Switching back restores that sign-in after `system/info`
confirms the origin again, with no new login. Past the section's budget,
the least recently used servers lose their tokens first (they stay saved,
signed out), then go. Credentials go only to the configured server; a
saved server's are sent nowhere until it is current again. Removing a
saved server ends its session on that server only when this run confirmed
its origin; otherwise its tokens are just forgotten here. The three
registry sections together stay within Roku's 32 KB.

An app update must not force the viewer to sign in again (criterion 4.1).
Registry layout changes migrate stored sessions instead of discarding them.

The Roku registry is treated as app-scoped persistence, not as a general secret
manager. Tokens must never appear in logs, error dialogs, crash breadcrumbs,
analytics, or copied diagnostic payloads.

### 7.3 Profiles

After sign-in the client loads `GET /api/v2/profiles`. Under Profile
Selection's Automatic, launches reopen the last profile chosen on this
device (section 5.4), after checking that it still exists and remains
permitted; Every Time and the timed choices show the picker instead, as
section 5.4 says, and forget the device's profile tokens first. Profile
Selection, the offer, and the time of last use are kept in the registry on
this device only, across sign-outs, and are never sent to the server, as
on tvOS and Android TV. The client never picks a profile
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

Creating a profile takes the household's primary profile, which the
picker has not chosen (Add profile, section 5.4). As tvOS and Android TV do,
the client acts as it without opening it: for a PIN-locked primary, the PIN
screen sends `verify-pin` once, and the token stays in the account session's
memory, never in the registry. `POST /api/v2/profiles` then carries the
primary's `X-Profile-Id` and that token. The session forgets it when New
Profile closes, when the server refuses it (`403
profile_verification_required`; the request is not replayed), or when the
session ends; the remembered profile and the open one are untouched, and
opening the primary to watch still needs its PIN. The create is never
retried (`non_retryable`): a request without an answer may have created the
profile, so the picker reads the list again instead.

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
- `GET /api/v2/home/capabilities` for `section_item_limit_max`, and then
  `item_limit=20` on `GET /api/v2/home/sections` and
  `GET /api/v2/library/{id}/sections` (section 5.5);
- `GET /api/v2/catalog?source=section&section_id={id}&scope=home`, or
  `scope=library&library_id={id}`, 40 cards a page with cursor pagination
  and the poster width, for a row's page;
- `GET /api/v2/library/{id}/collections` for the library's collection index;
- `GET /api/v2/catalog?source=library_collection&collection_id={id}` or
  `source=user_collection` for collection titles, with `limit=40`, cursor
  pagination, and supported artwork widths. Only explicitly typed mixed-library
  views add `library_id` and `type=movie|series`; ordinary and untyped views
  preserve collection membership across libraries;
- `GET /api/v2/catalog` for paginated browse, with `type`, `sort`,
  `name_prefix` for the alphabet rail, and `match` and `groups` for the
  filters, and with `limit=1&skip_total=true` for whether a filtered
  library that shows nothing is empty;
- `GET /api/v2/catalog/filters?library_id={id}` for a library's filter
  values;
- `GET /api/v2/catalog` with `q` for search, using `type=video_with_episodes`
  when `GET /api/v2/catalog/search/capabilities` advertises it, and `video`
  otherwise;
- `GET /api/v2/catalog/items/{id}` for detail;
- `GET /api/v2/recommendations/similar/{item_id}?limit=12` for detail
  recommendations;
- `GET /api/v2/catalog/people/{id}` for the person page's header;
- `GET /api/v2/catalog?source=person&person_id={id}&type={video|movie|series}&sort=-year`,
  40 cards a page with cursor pagination and the poster width, for the
  person page's titles, and the same with `limit=1` and `type=movie` or
  `series` for whether its Movies and Series pills show;
- `GET /api/v2/catalog/series/{id}/seasons` and
  `GET /api/v2/catalog/series/{id}/seasons/{num}/episodes`;
- `GET /api/v2/watch/{id}` for the playable projection, including
  `marker_segments` and each version's `chapters`;
- `GET /api/v2/audio-prefs/{key}`, and `PUT` and `DELETE` on it and on
  `/api/v2/subtitle-prefs/{key}`, for the audio and subtitle tracks the
  profile chose on a detail page (section 8.5);
- `GET /api/v2/settings/values/effective` for the profile's preferences;
- `GET /api/v2/settings/contract/capabilities` for whether the server
  serves the episode spoiler settings (section 5.6);
- `GET /api/v2/theme/branding` for server branding;
- `GET /api/v2/capabilities/personal-lists` for whether Watchlist and
  Favorites show;
- `GET /api/v2/watchlist`, `/api/v2/favorites`, and `/api/v2/history`, 40
  cards a page with cursor pagination and the artwork widths, for the list
  pages; `PUT` and `DELETE` on `/api/v2/watchlist/{id}` and
  `/api/v2/favorites/{id}`; `POST /api/v2/history/remove` with one target;
- `POST` and `DELETE /api/v2/watched/{id}` to mark a movie, episode,
  season, or series watched or unwatched;
- `GET /api/v2/shuffles/capabilities` for whether and what Shuffle is
  offered; `POST /api/v2/shuffles` to start one (scope `library`,
  `series`, `season`, `library_collection`, or `user_collection`); `GET`, `DELETE`, and
  `POST .../advance` and `.../skip` on `/api/v2/shuffles/{id}` in the
  player (section 5.7);
- `GET /api/v2/recommendations/discover` for the For You tab's rows, and
  `GET /api/v2/calendar` for the Calendar tab's week (section 5.10);
- `POST /api/v2/profiles` to create a profile as the household's primary
  profile, and `GET /api/v2/user/libraries` without profile headers for the
  libraries a child profile may be given (sections 5.4 and 7.3);
- `GET /api/v2/catalog/themes/capabilities` for whether theme music plays,
  and `POST /api/v2/catalog/items/{id}/themes/{theme_id}/playback` for a
  theme's grant, whose URL the Audio node plays (section 5.6);
- for Requests (section 5.11): `GET /api/v2/requests/status`;
  `GET /api/v2/requests/discover`, `.../discover/rows/{row_id}?page=`,
  `.../discover/{studios|networks|genres}`, and
  `.../discover/browse/{studio|network|genre}/{slug}?page=` (a genre with
  `media_type=movie`); `GET /api/v2/requests/search?q=&media_type=all&page=`;
  `GET /api/v2/requests/detail/{media_type}/{tmdb_id}`;
  `GET /api/v2/requests/mine` (`limit` up to 50, cursor) and
  `GET /api/v2/requests/{id}`; `POST /api/v2/requests`;
  `POST /api/v2/requests/{id}/cancel`; and `PUT` and `DELETE
  /api/v2/requests/follows/{media_type}/{tmdb_id}`;
- `GET /api/v2/subtitles/providers/status` for whether Search Subtitles…
  shows, `POST /api/v2/subtitles/search` for one language of the playing
  file, and `POST /api/v2/subtitles/download` for the result chosen,
  sent once (section 5.7);
- `GET /api/v2/capabilities/metadata-ai` for whether and how descriptions
  translate, and `POST /api/v2/catalog/items/{id}/translate-description`
  to translate an item's, a season's, or an episode's descriptions into
  the language its read reported missing (sections 5.5 and 5.6).

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
| `catalog.hide_unwatched_episode_images`, `catalog.hide_unwatched_episode_overviews` | Blur an unwatched episode's still and hide its description (section 5.6); read on their own when a page with the top bar starts, where the settings contract serves them (revision 17), and written by Settings for the profile (`profile`, the only scope the manifest allows) |
| `ui.theme_music_enabled`, `ui.theme_music_loop` | Whether detail pages play their theme music, and whether it repeats (section 5.6); the theme player reads them when a page needs them, and Settings writes them for this device (`profile_device`), as tvOS does |
| `catalog.metadata_language` | The language the server returns descriptions and taglines in, and reports missing for translation (sections 5.5 and 5.6); Settings reads it for its Metadata Language row and writes it for the profile (section 5.8.1); nothing else in the client uses it |

Profile Selection (section 5.4) is not a server setting: as on tvOS and
Android TV, it is this device's alone and lives in the registry.

Start has no language member, so language preferences are applied by choosing
tracks, as Android TV does. Settings marked `client_local` in the server's
settings manifest, such as `player.resume_rewind_seconds`, are not served by
the effective-settings endpoint; the client uses their manifest defaults.
Subtitle appearance is left to Roku's system caption settings (section 9.7).
Settings writes supported preferences through `PUT /api/v2/settings/values/{key}`
with a typed `{ "value": ... }` body and an explicit `scope` query. Playback
and subtitle controls use `profile_device`, with “Use profile setting” sending
`DELETE` at that scope. Title art, video skip intervals, the spoiler
settings, and the metadata language use `profile`, as required by their
resolution order or allowed scopes. The screen explains
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
- Lowering quality when playback keeps buffering follows the shared Silo
  design every client runs (silo-server
  `docs/design/2026-10-17-buffering-quality.md`), with the Roku specifics in
  `docs/buffering-quality.md`. `playback.bufferingQuality` is the shared
  controller and replays the vendored vectors
  (`tests/fixtures/buffering-quality/vectors.json`); `playback.buffering`
  turns the Video node's reports into its events. On Auto in Automatically
  (the default), two counted stalls within two minutes or one of 6 s, after
  a plan's 10 s grace, send a `quality_change` with `floor(delivered × 7 /
  10)` as `observed_rebuffer`, then the undo card; a quality the viewer
  picked, or Ask first, gets the prompt; Never only reports.
- A wait is an outage, never a stall, while no media arrives: no
  `bufferingStatus.percentage` above the wait's last reading and no
  downloaded segment for 4 s on a progressive plan, 15 s on HLS, counted
  from the wait's start, and for a reconnect from its start until a load
  plays. Hardware run 15's cut original, its reading held at 2%, is an
  outage and never steps down. Buffering after the session's own seek is
  the seek's, a load of a plan that has played is a source reload, and
  neither counts; a reload has no grace of its own. Roku reports no
  buffered duration, so no wait is taken for the renderer's
  (`docs/buffering-quality.md` section 5.2).
- The session never queues a lowering behind a start or replan in flight;
  the controller watches the plan again a minute later. After a lowering,
  the client's own Auto replans repeat its estimate without a source until
  Restore quality, a quality change, or a new attempt (Retry, a restart),
  whose starts carry the connection's speed reading instead and the server
  plans under its learned limit. Restore quality sends `learned_limit:
  "clear"`, owed to the next request when another replaces it; Never sends
  `"ignore"` on every request. A start that has not played lowers at its
  20 s deadline only when its segments arrived more slowly than it plays;
  otherwise, and on a second 20 s, the failure path runs.
- `buffering_quality_v1` and its fields go only to a server that
  advertises it, and `plan_summary` only to one with
  `playback_plan_summary_v1`.
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
- A subtitle Search Subtitles downloads (section 5.7) reaches playback only
  through a plan, never through a URL the client builds (tvOS synthesizes
  the session's stream URL for it). The server announces no provider
  download in realtime, but every plan lists the file's stored subtitles
  again, after the file's external and embedded tracks, as `source:
  "downloaded"`. So, unless the playing plan lists it already, the player
  sends a `track_change` that keeps the plan's audio and subtitle (in
  place when the content carries that subtitle, so the content plays on),
  or waits for a `track_change` already on its way. In the first plan
  after the download it finds the inventory row whose `sync_key` is
  `stored-{id}`, the download's `subtitle.id`, else the one downloaded
  row in the result's language that the plan before the download did not
  list, and chooses it as Options chooses a subtitle: a `track_change`
  naming its `track_id` and `combined_index`, captions On, and, since the
  content does not carry it, a reload at the position. It counts as
  added, and the panel and Options close, only once a plan selects it; a
  refused choice, a plan that selects another track, or no such plan
  within 30 seconds says it was saved and is listed under Tracks. A plan
  after the refresh that does not list it, a refused refresh, a plan of
  another file, or no plan within 30 seconds leaves it stored for the
  next time the file plays, and the panel says so (assumption AG-492).

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
none can, it stays on Home. While a profile is open, a deep link keeps it.
Profile Selection does not apply to a deep link, which never shows the
picker; under Every Time and the timed choices the device holds no profile
token at launch, so PIN-locked profiles are skipped. Content IDs are opaque Silo identifiers and
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
| Device-code sign-in | Leads sign-in in every build, as on tvOS (owner, 2026-10-29; section 7.2) | Roku's ruling on criterion 2.2 at submission: Roku allows rendezvous linking only in TVE apps |
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
