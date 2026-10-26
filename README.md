# Silo Roku

Native Roku client for the [Silo](https://github.com/Silo-Server/silo-server)
self-hosted media server.

> **Status:** Design and platform-validation phase. The repository contains a
> sideloadable feasibility app that reports the device's display and decoder
> capabilities; it does not talk to a Silo server yet.

The client will be built with Roku SceneGraph and BrightScript. The proposed
MVP, architecture, Silo API integration, playback behavior, certification
risks, and delivery milestones are captured in the
[client specification](docs/spec.md).

## Intended project layout

```text
components/      SceneGraph components and their BrightScript controllers
source/          Entry point and non-visual BrightScript modules
images/          Packaged Roku artwork
fonts/           Subset Inter TTFs with their license and SOURCE
locale/          Localized strings
tests/           Rooibos specs, mirroring source/ paths
docs/            Product and architecture documentation
manifest         Roku package manifest
```

## Development

Requirements: Node.js 22 (`.nvmrc`) and Python 3 locally, plus curl and
Python 3 on the machine that uploads to the Roku. That machine must reach the developer
installer (port 80) and ECP (port 8060); enable ECP network access on the Roku.

1. Enable Developer Mode on the Roku: with the remote, press Home three times,
   Up twice, then Right, Left, Right, Left, Right. Enable the installer, accept
   the SDK license, and set a password. The username is always `rokudev`.
2. Copy `.env.example` to `.env` and set `ROKU_HOST` and `ROKU_PASSWORD`. If
   this machine cannot reach the Roku, set `ROKU_DEPLOY_VIA` to a command that
   runs a shell command on a host that can (for example an SSH wrapper).
3. Install the tooling and sideload:

```sh
npm ci
npm run lint           # BrighterScript and bslint validation, no package
npm run format:check   # brighterscript-formatter check (npm run format rewrites)
npm test               # Rooibos specs, headless under brs-node
npm run sideload       # build out/silo-roku.zip and install it as the dev app
npm run console        # stream the BrightScript debug console (port 8085)
```

Three build variants come from one source. `npm run build` makes the release
package, `out/silo-roku.zip`. `npm run build:perf` makes `out/silo-roku-perf.zip`,
which adds `run_as_process=1` (needed by `chanperf`, Resource Monitor, and
Perfetto) and sets the `perf` `bs_const`. `npm run build:dev` makes
`out/silo-roku-dev.zip`, which sets `debug` and is the only package that
contains `source/dev/` and `components/dev/`. `npm run sideload:dev` installs the
dev build; `scripts/sideload.sh out/silo-roku-perf.zip` installs any other
package. The variants are `bsconfig.perf.json` and `bsconfig.dev.json`: bsc
drops inactive `#if` blocks at build time, and `scripts/bsc-manifest-entries.js`
writes each variant's manifest keys into its package. `npm run lint` checks the
release and dev builds. `scripts/brand-art.py` regenerates the channel
poster, splash screens, and wordmark in `images/` from a silo-branding checkout.

Screens take colours, sizes, focus scales, art, and the shared `Font` nodes from
`components/theme/` (`tokens.bs` for the spec's tokens, `helpers.bs` for
`theme.font(style)`). `scripts/ui-art.py` regenerates the shared art in
`images/ui/`: card frames, focus rings, the card shadow, the hero scrims, badge
chips, menu panels, tab capsules, and the watched check. `scripts/subset-fonts.sh`
rebuilds `fonts/` from the Inter release pinned by sha256, using a hash-pinned
fontTools in a throwaway virtualenv, and records the result in `fonts/SOURCE`;
pass an already downloaded release zip to skip the download. It also writes
`Inter-SemiBold-Tabular.ttf` with `scripts/tabular-font.py`: a timecode font
whose default digits are Inter's tabular figures, used by
`theme.textStyle.TIMECODE`. Do not set a Label's `monospacedDigits`, which
renders Inter's digits as boxes. In the dev build, Fast Forward on the
diagnostic screen (`npm run roku -- key Fwd`) opens the theme check, which
shows the type scale, sample cards, proportional and tabular timecodes, and
non-Latin titles in Inter beside Roku's system font.

Screens are child components of `AppScene` that extend
`components/screens/Screen.xml`. `source/nav/phase.bs` picks the root screen
from the account session (server setup, sign-in, profile, Home, or "server
update required"), and `source/nav/stack.bs` is the navigation stack: a pure
reducer that decides which screens to create, hide, release, or rebuild,
keeps at most two pushed screens alive beneath the top, and settles Back
(spec section 5.3). `components/AppSceneNav.bs` carries out its plans through
each screen's hooks (`onShow`, `onHide`, `onPressure`, `onRelease`,
`focusKey`, `backContext`, `onBack`). Screens navigate with `nav.push`,
`nav.pop`, and `nav.replace` (`source/nav/client.bs`), find their focus target
on return with `nav.focus.target`, and give back artwork and list content
while hidden with `nav.textures`. In the dev build, Options (`*`) on Home
(`npm run roku -- key Info`), or Diagnostics in the avatar menu, pushes the
diagnostic screen, which reports what the Roku and its display support and
opens the dev tools below; Back returns to Home. Release builds never open
it. OK on the diagnostic screen starts the navigation check: placeholder
detail screens, where OK pushes another, Play pushes a placeholder player,
and Back pops.

Before Home come server setup, sign-in, the profile picker, and PIN
(`components/screens/setup/` and `components/screens/profiles/`), built from
the views in `components/views/`. Text entry uses Roku's `DynamicKeyboard`
in a panel over the screen (Down from the keyboard reaches the chips and
Done; Play is Done too), and PINs use `DynamicPinPad`. Their decisions live
in pure helpers under `source/onboarding/` with specs: address chips and
the HTTPS-then-HTTP rule, sign-in errors, which profile opens without the
picker, the lockout message, and the dialog beacons each screen's
`prompting` field drives (`AppSceneNav.bs` counts the changes of one
navigation step once). All copy is in `locale/en_US/strings.json`, read
with `i18n.text(key, values)` (`source/util/i18n.bs`); a locale file added
beside it overrides English key by key. JSON has no comments, so the file's
one rule lives here: a change adds keys only under the prefix of the screens
it owns, so parallel work merges cleanly. Shell and Home use `home.`,
`topBar.`, `menu.`, and `catalog.`; detail `detail.`; libraries and Search
`library.`, `browse.`, and `search.`; the player `player.`, `options.`,
`upNext.`, and `skipIntro.`; first run and profiles `firstRun.`, `setup.`,
`signIn.`, `update.`, `passwordOff.`, `profiles.`, `pin.`, and `states.`. The shared
`common.` and `language.` keys change in a change of their own.
`scripts/first-run-art.py`
regenerates `images/firstrun/`: the brand mesh behind these screens (the
Android TV backdrop's colour mesh at rest, with its scrim), and the capsule,
field, card, server-card, badge, avatar, PIN-dot, spinner, help-symbol, and
warning-triangle art.

Browse screens build on `source/catalog/` and the views in
`components/views/`. `catalog.request` builds the `/api/v2` catalog requests
(rows, section items, Browse and Search pages, detail, seasons, episodes)
with the artwork widths in `catalog.art`; each names a map step that `ApiTask`
runs before posting the result (`source/catalog/map.bs`), so lists arrive as
ready `CardContent` and `RowContent` trees and the raw body never reaches the
render thread. `catalog.rows` and `catalog.grid` are the data budgets (lazy
rows two ahead, ten grid pages with cursor checkpoints) as pure functions with
specs; `BrowseRows`, `BrowseGrid`, `TopBar`, `Hero`, `CatalogCard`,
`LoadingSpinner`, and `StatusView` are the components screens assemble.
Home (`components/screens/home/`) and the library tab pages
(`components/screens/library/`) share the main shell in
`components/screens/home/shell.bs`: the top bar with its library tabs
(`user/libraries` without the profile's hidden libraries), the avatar menu
(Switch Profile, Settings, Switch Server, Sign Out), each library tab's list of
libraries with Recommended and Browse, and focus between bar and content.
Settings uses the TV clients’ split category rail and detail pane. It exposes
the preferences already supported by Roku, reads the server settings contract,
and saves typed profile or device values through the central API client.
Playback and subtitle overrides can be reset with Use profile setting.

A library page shows Recommended (the library's sections as rows under the
hero) or Browse (the Sort pill and sort menu over the poster grid, with the
alphabet rail under every sort). The shell's and Home's decisions are
pure helpers in `source/home/`, and the library pages' (which library a tab
opens, the Browse request for a sort and letter, where the arrow keys and
Back move focus) in `source/library/`, all with specs. Home fires `AppLaunchComplete` once the hero and the visible rows'
artwork have loaded or failed, or its empty or error state shows. In the
dev build, Right on the diagnostic screen (`npm run roku -- key Right`) opens
the browse gallery: Home rows with the hero, a 1,000-title Browse grid, and the
loading, empty, error, and episode views, all on fixture data answered by
`DevApiTask` and mapped by the real map step. Replay turns the page, Play
switches to the signed-in server's data, Options (`*`) switches to the
low-tier focus, and Back closes. `scripts/sync-fixtures.sh` also vendors the
catalog fixtures and `tests/fixtures/openapi/catalog-operations.json`, the
methods, paths, and query parameters the request specs check built requests
against.

Lint and build fail on any warning. Specs live under `tests/`, mirroring the
module they cover (`tests/util/log.spec.bs` for `source/util/log.bs`), and are
staged into `source/tests/` of a separate test package. Shared helpers and
base suites live in `tests/helpers/`, and every spec imports what it uses, so it
compiles alone. Specs run in `TestScene` (`tests/components/TestScene.xml`),
which stands in for AppScene's router, navigation, and platform state: it
records what a screen sends, and `tests/helpers/scene.bs` answers it. `npm test` (`scripts/test-headless.sh`) runs the specs in
shards: each shard in `SHARDS` (`scripts/test-headless.py`) is its own test
package and brs-node process, four at a time (`TEST_JOBS=1 npm test` runs them
one after another; use 2 on an 8 GB machine). brs-node keeps every component a
process creates until it exits, so a shard's memory grows with the players and
detail pages its specs build; the largest peaks near 1.8 GB. A new spec
directory needs a place in `SHARDS`, which the run checks. The run passes only
when every shard finishes within 5 minutes and reports
`[Rooibos Result]: PASS` after at least one test; it prints each shard's output
and a table of their counts and times. `npm test -- --junit` also merges the
shards' reports into `reports/junit.xml`. Headless results are not device
evidence.

`npm run ci` runs the pull request checks (`.github/workflows/ci.yml`) locally:
lint, format, build, then `check:size` (the package stays under 3.5 MB),
`check:hygiene` (no `/api/v1`, banned APIs, bare `print`, or missing manifest
keys in the package), `check:sca` (Roku Static Analysis, failing on any error or
memory-monitoring warning; report in `reports/sca.xml`), `check:contract`,
`check:device-check` (the device lane's parser and its exit handling, without a
device), `check:header-probe` (the header probe's unit tests), and the tests.
Static Analysis needs Java 21, unzip, and Python 3; it downloads `sca-cmd` once
into `~/.cache/silo-roku/sca-cmd` (override with `SCA_CMD_CACHE_DIR`) and runs
it only when its sha256 matches the pin in `scripts/sca.sh`. CI packages carry
the run number as `build_version`; local builds keep the manifest's value.

Sideloading replaces the single developer app slot on the device. The script
checks the installer status, verifies the expected title and version in ECP,
and launches the dev app if necessary. It only reports success when the app
remains active. An upload receipt or installer timeout alone is not success;
use `npm run console` to inspect startup errors. Credentials travel over stdin
and are stored only in a temporary, private curl configuration during upload.

Sideloaded builds are for development only; they are not release evidence.

### Remote control

`npm run roku -- <command>` drives the device over ECP, using the same `.env` and
`ROKU_DEPLOY_VIA` relay as sideloading. ECP network access must be set to
Permissive (Settings > System > Advanced system settings > Control by mobile
apps) for keypresses and launches.

```sh
npm run roku -- key Home            # press keys in order: Up Down Left Right Select Back
                                    # Home Play Rev Fwd Info InstantReplay ...
npm run roku -- text "the matrix"   # type into the focused text field
npm run roku -- launch              # relaunch the dev app (optional: app id, key=value params)
npm run roku -- input key=value     # send an input event to the running app
npm run roku -- active              # print the foreground app
npm run roku -- query device-info   # any /query/<path> ECP endpoint
npm run roku -- screenshot shot.jpg # capture the screen (dev app only)
```

If an install keeps reporting "Install timeout" and the dev app never appears in
`query apps`, the device's installer can get stuck; a software restart may not
clear it. Unplug the device for 60 seconds, then sideload again.

### Deep links

The app takes Roku deep links at launch and while running: `contentId` is a
Silo content ID (at most 255 characters) and `mediaType` is `movie`,
`episode`, `series`, `season`, `shortFormVideo`, `tvSpecial`, or `special`;
`live` and other types are refused. Test them over ECP with IDs from the
connected server (the script URL-encodes values):

```sh
npm run roku -- launch dev contentId=<id> mediaType=movie   # POST /launch/dev?contentId=…&mediaType=…
npm run roku -- input contentId=<id> mediaType=episode      # POST /input?contentId=…&mediaType=…
```

A movie or episode plays from its server position without a resume prompt,
and a series or season plays its play target episode. Signed out, the link
waits through setup and sign-in. With no profile open, it skips the picker:
the profile last chosen on this device opens if it is not a child profile,
otherwise the account's first non-child profile, skipping PIN-locked
profiles (`source/deeplink/route.bs`). An invalid or inaccessible link
leaves the app on Home at launch and on the current screen while running.
The console logs each link's validity and outcome, never its values;
`AppLaunchComplete` fires once per launch: for a deep-link launch, when
playback starts or the player shows an error.

### Phone remote (SiloControl)

Development builds (`npm run sideload:dev`) run the SiloControl receiver
(`docs/silocontrol.md`): once signed in, the app listens on TCP 52817 and
advertises `_silocast-roku._tcp` over multicast DNS, and the avatar menu has
Connect a Phone. Release builds leave it out until the build switches
`silocontrol` and `handoff` in `manifest` are turned on.

`npm run silocontrol -- <options> <steps>` plays a phone's part against the
Roku in `.env`, through `ROKU_DEPLOY_VIA` when set. It prints every frame the
Roku sends, masking handoff codes and resume tokens; by default its hello
names the Roku's own server.

```sh
npm run silocontrol -- wait 10                              # connect, hello, and watch state
npm run silocontrol -- control seek '{"seconds":120}' wait 3 # a control command
npm run silocontrol -- offer <profileId> wait 2 launch <contentId> wait 10
npm run silocontrol -- --key <pairing code> wait 5          # level sealed, after Require Pairing
dns-sd -B _silocast-roku._tcp                               # on a Mac: is the Roku advertised?
```

With the `companion` switch (on in every build), the server and sign-in
screens also run companion sign-in (`docs/companion-pairing.md`):
they advertise `_silopair-roku._tcp` on TCP 52827, and a Silo phone app on
the network offers to sign the Roku in. `--pairing` plays the phone's part:

```sh
npm run silocontrol -- --pairing push https://silo.example '{"serverIdentity":"<server_id>"}' wait 30 cancel
```

On macOS, Homebrew's `node` started over SSH has no Local Network permission
and gets `EHOSTUNREACH` for LAN addresses; run the script on the Mac's own
terminal, or relay through a loopback port with the system `python3` or
`nc`.

### Device check

`scripts/device-check.sh` is the device lane of plan sections 1, 7, and 8: cold
launches timed by the port 8085 beacon report, ECP snapshots, and the deep-link
matrix. It uses the same `.env` and relay as sideloading and needs Developer
Mode, "Control by mobile apps" set to Permissive, Roku OS 13 or later (for ECP
`exit-app`), and Python 3 on the relay host. The debug console on port 8085
serves one connection at a time, so close `npm run console` (or any telnet or
IDE debugger session) first; the check stops with that advice when the console
refuses it or stays silent. Each session's console is saved to `--out` instead.

```sh
scripts/device-check.sh                        # 10 cold launches
scripts/device-check.sh --launches 1 --perf    # one launch, then the snapshots
scripts/device-check.sh --launches 0 --deeplinks --ids .env.deeplinks
```

It runs only when the TV shows Roku Home or the dev app with its display on,
and nothing is playing. If the TV is on `ROKU_IDLE_INPUT` (default
`tvinput.hdmi1`), it runs `ROKU_IDLE_CHECK` through the relay. Only when that
command prints `Device state: Idle` does it press Home to reach Roku Home. Any
other input or app stops it before it sends a command. Between runs it checks
again, and if the TV has left Roku Home and the dev app, it stops without
pressing anything.

- **Launches** (`--launches N`, default 10): each run exits the dev app, waits
  up to 15 s for it to leave the foreground (stopping if it does not), launches
  it, and keeps the console from the launch on. The summary gives
  the median and maximum time from the first `AppLaunchInitiate` to
  `AppLaunchComplete` by the device clock. It also gives Roku's own beacon
  value, which on a sideloaded app leaves out the first compile pass. It
  records any `AppDialogInitiate`/`AppDialogComplete` pairs and the exit beacon
  report. The 3810X/3921X and 3840X are judged against the Milestone 1 exit and
  other models against the 15 s certification limit. Milestone 1 numbers need
  a restored session with a PIN-free remembered profile, so a run that shows
  dialog beacons waited for the viewer. The launches also set up
  `fwbeacons/track` and save `query/fwbeacons`, which shows whether that query
  lists app beacons. Sideloaded release builds give an upper bound; confirm on
  a beta install.
- **Reboot:** ECP cannot restart a Roku, and the keypress routes run through
  Settings or the system menu, so the script never restarts one itself.
  `--await-reboot` waits up to 10 minutes for a restart done by hand
  (Settings > System > Power > System restart), then 30 s more, before the
  launches. `--no-reboot` is the default.
- **Snapshots** (`--perf`): one more cold launch, then, 8 s after
  `AppLaunchComplete`, `query/chanperf`, `query/r2d2-bitmaps`,
  `query/sgnodes/all?count_only=true` (and `&sizes=true`), and
  `query/graphics-frame-rate`. `chanperf` answers only for the perf build
  (`run_as_process=1`); the others need only Developer Mode. Memory is judged
  against 80% of the foreground limit, which the app logs only in the dev
  build, and texture memory against 70% of the `r2d2-bitmaps` maximum. The
  frame rate is sampled on an idle Home; scrolling needs a hold script.
- **Deep links** (`--deeplinks`): for each of `movie`, `episode`, `series`, and
  `season`, `launch/dev?contentId=…&mediaType=…`, and a plain launch followed
  by `input?contentId=…&mediaType=…`. A made-up ID tried as a movie covers the
  "invalid or inaccessible" row. The content IDs come from a gitignored file
  (`--ids`, default `.env.deeplinks`) of `DEEPLINK_MOVIE=`, `DEEPLINK_EPISODE=`,
  `DEEPLINK_SERIES=`, and `DEEPLINK_SEASON=` lines, and a type without an ID is
  skipped. Run it once signed in and once signed out. The routing lines are
  `log.info` output, which only the dev build (`npm run sideload:dev`) prints.
  Rows come out as `(judge)` for a PASS or FAIL against the plan's section 7
  table.

Output goes to `--out` (default
`.local/evidence/silo-roku/device-check-<timestamp>/`, gitignored and private).
That folder holds the console from each launch (`launch-NN.log`, `perf.log`,
`deeplink-<type>-<launch|input>.log`), the ECP XML, the step statuses
(`steps.tsv`), and `summary.md`. The summary uses the row format of
`docs/hardware-evidence.md` and leaves out addresses, credentials, signed URLs,
and content IDs; check it before appending it there. The raw files stay private
because bitmap names can carry server addresses. A run that stops early still
writes `summary.md` from what it saved. Unit tests:
`python3 -I -B -m unittest discover -s scripts/device-check`.

## License and trademarks

Silo Roku is licensed under `AGPL-3.0-or-later`. See [LICENSE](LICENSE).

The **Silo name, logo, and wordmark are trademarks of Silo Media L.L.C.** and
are **not** covered by the AGPL. You're free to fork and redistribute the code,
but forks and redistributions must not use the Silo brand as their identity and
must remove or replace the brand assets. Publishing a Silo-branded app to an app
store requires written permission. See [TRADEMARK.md](TRADEMARK.md) for what's
permitted — including referential use like "compatible with Silo."
