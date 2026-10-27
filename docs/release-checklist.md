# Silo Roku release checklist

**Status:** Draft for Milestone 4 (beta and public readiness)

**Last updated:** 2026-10-25 (section 1 items 1 and 2, rows 2.2 and 4.15, and section 7's device, token-refresh, and API-restart rows; other rows still as of 2026-10-22, against integration commit `f1d9d9b`)

**Companion to:** [`spec.md`](spec.md) sections 10–13 and
[`implementation-plan.md`](implementation-plan.md) sections 7, 9.1, and 9.2.

This checklist lists what the Roku client must show before a beta with real
households and before public submission: every Roku certification criterion
that applies, Static Analysis, the Deep Linking Tester, App Behavior Analysis,
store assets, the device matrix, the beta, and the public-submission
prerequisites. Each row says how the app meets the requirement, where the
evidence is, and its status.

- **Met:** evidence exists. Hardware evidence means a row in
  [`hardware-evidence.md`](hardware-evidence.md); headless tests alone are not
  hardware evidence.
- **Partial:** evidence on some devices or some parts.
- **Open:** no evidence yet, or the last run failed.
- **N/A:** the requirement does not apply to this app.

Roku requirements were read from Roku's own pages on 2026-10-22 (section 11).
Anything Roku's pages did not settle is marked **unconfirmed**.

## 1. Blockers

These stop a beta with households, and therefore public submission:

1. ~~**Release builds play nothing.**~~ Resolved 2026-10-25 (decision D-7):
   the hardware gates are gone, so release builds play, copy-remux, and send
   subtitle sidecars like development builds, and every format claim follows
   the device's probe. Hardware run 30 checked the claims on the Ultra 4850X
   in a dev build; no release build has run on hardware yet.
2. ~~**Release builds cannot sign in to a stock Silo server.**~~ Resolved: the
   server serves `request_origin` (S-20, silo-server #3023, merged
   2026-10-25), and since D-7 every build also accepts an older server
   without it, with a warning. A mismatch is still refused.
3. **Milestone 3 has not exited.** Nearly every hardware row comes from one
   Roku TV (section 7); runs 29 and 30 added the Ultra 4850X. Only run 30's
   Dolby Vision picture has been seen (P5, on the Ultra); no one has listened
   to the output (Atmos), and output changes (H13) are untested. Token refresh
   during playback, which failed in hardware run 8, passed in runs 9, 10, and
   19.
4. **No written permission for the store.** The channel poster and splash
   screens now use the official wordmark (`scripts/brand-art.py`,
   `images/NOTICE`), but the trademark policy still needs written permission
   for a Silo-branded store app.
5. **Roku may not allow a typed server address.** The Roku Distribution
   Agreement says an application must not "allow end users to enter web
   addresses" (Exhibit A §3.2(a)). Silo's setup asks for one; this needs
   Roku's confirmation before submission.
6. **Roku limits beta apps to "internal testing only"** (Distribution
   Agreement Exhibit A §2.1). Spec section 13 wants real households in the
   beta; this also needs Roku's confirmation.
7. ~~**Beta builds report the wrong channel.**~~ Resolved: `npm run build:beta`
   sets the `beta` build constant, and an installed beta package reports
   `X-Silo-Client-Channel: beta` (assumption AG-38, `source/auth/headers.bs`).
8. **No owners** for the Roku developer account, signing key custody, the
   reviewer server, or the store listing (plan section 9.1, assumption A-7).

## 2. Certification criteria

Source for every row: Roku certification criteria,
<https://developer.roku.com/dev/docs/certification> ("Last updated: October,
2026"), unless the row names another page.

| Criterion | Roku requirement (short) | How Silo meets it | Evidence | Status |
| --- | --- | --- | --- | --- |
| 1.1 | Video ads follow Roku's ad requirements | No ads | — | N/A |
| 2.1 | Transactional apps use Roku Pay | Free, nothing for sale | — | N/A |
| 2.2 | On-device authentication only; no off-device sign-up, sign-in, or activation | Password sign-in with Roku's `DynamicKeyboard` (spec 7.2). Companion sign-in (a phone approves a device login) ships in public builds by the owner's decision (spec 7.2), and profile handoff by D-7, both before Roku answers Q10. A server without password sign-in gets an explanation and stops | Hardware runs 4 and 5, onboarding rows | At risk, owner-accepted |
| 2.3 | Instant Signup for SVOD above 10M hours a month | Not SVOD | — | N/A |
| 2.4 | No nested apps, browsers, embedded screens, or cross-app features | None. The typed server address is a separate question (section 1, item 5) | Code | Met, pending Roku's answer on the typed address |
| 2.5 | Disclose any payment SDK | None | — | N/A |
| 3.1 | Available on every device that receives the current Roku OS, and free of frequent crashes and rebuffering | Minimum firmware 15.1.0 (dashboard field); `roAppMemoryMonitor` with the general-memory fallback for models without it (`source/main.bs`, plan 4.7) | Stability rows in runs 5–8 (node counts flat, no crash), Roku TV only | Open (device matrix, section 7) |
| 3.2 | Launch to a fully rendered home screen within 15 s on the 3810X or 3921X; `AppLaunchComplete` required | `AppLaunchComplete` once Home's hero and first two rows' art settle, or after the first frame of a deep link (`components/AppSceneNav.bs`, AG-57); one dialog-beacon pair before Home (AG-59) | Run 5: release cold launch median 2.39 s, max 2.61 s (Roku TV, sideloaded, no reboot); run 5 dialog beacons PASS | Partial (reference device, reboot-and-wait method, and a beta install not run) |
| 3.3 | Screen transitions within 3 s | Request deadlines and spinners (plan section 1) | No `perf`-build timing run | Open |
| 3.4 | Loading indicator after 3 s; respond within 10 s | As above | Not measured | Open |
| 3.5 | Respond to key presses within 250 ms | — | Not measured (run 5: no Perfetto trace) | Open |
| 3.6 | Start playing within 8 s | Roku OS fires the video start beacons itself ([measuring channel performance](https://developer.roku.com/dev/docs/measuring-channel-performance)) | Roku TV values 1.9–4.3 s, one 8.5 s (run 4, R74); no reference-device or 512 MB measurement | Open |
| 3.7 | Package 4 MB or less | CI fails above 3.5 MB (`scripts/check-size.sh`) | Release zip built right after `f1d9d9b` merged: 1,116,245 bytes | Met |
| 4.1 | Updates never require re-login and keep saved data | Versioned registry layout whose later versions only add keys, so older and newer builds read the same session (`source/storage/registry.bs`); the same signing key for every build, since Roku keys the registry by developer ID ([roRegistry](https://developer.roku.com/dev/docs/roregistry)) | No install-over-existing-data rehearsal yet (plan 9.1) | Open |
| 4.2 | Automatic Account Link above 1M hours a month | Below the threshold (Roku's signup page says 5M; the pages conflict) | — | N/A at launch |
| 4.3 | Apps that require authentication (SVOD, TVE, other subscription services) use the Roku Event Dispatcher; AVOD is exempt ([prioritizing authenticated apps](https://developer.roku.com/dev/docs/prioritizing-authenticated-channels-in-roku-search)) | Not implemented. Contingency in plan 7: `roku_analytics` and `Roku_Authenticated` | — | Open: Roku answer (Q4) |
| 4.4 | `*` is Roku's during video playback; the app may use it only over its own UI | With the controls hidden the `Video` node keeps focus. On a Roku TV, Roku takes `*` even over Silo's controls, so Options opens from its button and from Down (AG-117) | Run 6 T2, run 7 T1g (Roku TV) | Partial (no Roku player run, H15) |
| 4.5 | Do not override the screensaver | The app never sets `disableScreenSaver` (no match in `source/` or `components/`) | Code | Met |
| 4.6 | Back returns to the previous screen and exits from Home; one confirmation dialog allowed | Spec 5.3 Back routing | Run 4 navigation check: Back from Home exits to Roku Home | Met on the Roku TV |
| 4.7 | Trick-play thumbnails for VOD over 15 minutes | The server's sprite sheets (decision D-5); a file without sheets shows the time and "Previews aren't available for this title" | Run 7 T4 PASS where sheets exist; H20 not run | Partial: Roku answer on servers without sheets (Q6) |
| 4.8 | Follow accessibility law; captions follow the global setting; Options offers On, Off, On instant replay, On mute (Roku TVs only); captions in sync; follow Roku's autoplay policy | Options' Captions rows write `Video.globalCaptionMode` (spec 9.7); Up Next honours `IsAutoplayEnabled()` (plan 6.10); Audio Guide text on focusables (plan 4.9) | Run 7 T1a rows shown; run 7 T1e On mute FAIL 1 in 3 (fix `7bc7362`, not rechecked); Roku autoplay off never run (run 6 T6c); Audio Guide never checked on hardware | Open |
| 4.9 | Instant replay rewinds 10–25 s | Replay uses the skip-back value clamped to 10–25 s, with replay captions (spec 5.9) | Run 6 T1 (11 s back), run 6 T3 replay captions PASS | Met on the Roku TV |
| 4.10 | Bookmarks for VOD over 15 minutes, kept at least 30 days | Server-stored resume from progress and stop (spec 9.5) | Runs 4–5 resume rows PASS. The server stores nothing for a stop below 5% of the runtime (AG-125); 30-day retention is a server property, unconfirmed | Partial |
| 4.11 | Voice controls above 5M hours a month | Below the threshold. Basic and enhanced transport commands are handled anyway (play, pause, fast forward, rewind, replay, seek, start over, next, skip, stop; spec 5.9); nowplaying, like, dislike, shuffle, and loop are left to the OS | ECP transport events on the Roku Ultra (OS 16.0.4), 2026-10-26; no spoken command on hardware yet | N/A at launch |
| 4.12 | Roku voice keyboards for email, PIN, and password | `DynamicKeyboard` for address, username, and password, `DynamicMiniKeyboard` for search; `DynamicPinPad` for PINs (plan 7) | Runs 4–5 onboarding | Met on the Roku TV |
| 4.13 | Continue Watching integration above the hours thresholds | Below the thresholds (spec 10.2) | — | N/A at launch |
| 4.14 | Instant Resume for US apps above 5M hours | Below the threshold; no `sdk_instant_resume` (plan 3) | — | N/A at launch |
| 4.15 | Never route traffic for third parties or act as a proxy, relay, or exit node | The app talks only to the configured server and the media and image hosts it names. The SiloControl receiver and companion listener accept local phones on TCP and answer mDNS on UDP 5353 in every build (D-7); they relay nothing | Code | Open, pending Roku's answer on the receiver |
| 5.1 | Deep linking for all media types | `contentId` and `mediaType` at launch and through `roInput` (`source/deeplink/`); movie, episode, series, season play, a season like its series; invalid or inaccessible links fall back to Home (spec 10.1) | Runs 4–5 ECP matrix PASS (Roku TV), signed in and signed out | Partial (Deep Linking Tester not run, section 4) |
| 5.2 | Direct to Play | The link plays directly, resuming without a prompt, using the profile rule in spec 10.1 | Runs 4–5 | Partial: Roku's Direct to Play page ties it to a Roku Search catalog ([Direct to Play](https://developer.roku.com/dev/docs/direct-to-play)), which Silo has no global form of (Q5) |
| 5.3 | No deep links into other apps | None | Code | Met |
| 6.1 | Non-zero version, increased for every submitted build | Manifest version 0.1; CI stamps `build_version` from the run number (`scripts/stamp-build-version.sh`); a version-increase check is planned for release tags (plan 8) | — | Partial |
| 6.2 | Kids and family rules | Not listed as made for kids | — | N/A |
| 6.3 | No pornographic content in public apps; anything shown outside the app suitable for all ages | The app shows each household's own library; store art and descriptions will be generic | — | Open: Roku answer (Q3) |
| 6.4 | Splash in FHD and HD; artwork identifies the app, uses broadcast-safe colours, and is not transparent | `splash_screen_fhd` 1920×1080, `_hd` 1280×720, `_sd` 720×480, the official wordmark opaque on `#161616` (`scripts/brand-art.py`) | Not yet seen on hardware | Open (hardware check) |
| 6.5 | CVAA for apps pre-selected at device activation | Not pre-selected | — | N/A |

Test credentials: the publishing guide says "Authenticated SVOD, AVOD, TVE, and
free apps must select 'Yes'" to signing in and provide a test account
([publishing guide](https://developer.roku.com/dev/docs/channel-publishing-guide)).
The criteria page itself names only TVE, TVOD, PVOD, and vMVPD apps; plan for
the publishing guide's stricter reading.

## 3. Static Analysis

Source: [Static Analysis](https://developer.roku.com/dev/docs/static-analysis-tool)
and the [`sca-cmd` changelog](https://devtools.web.roku.com/static-channel-analysis/CHANGELOG.md).
Errors block publishing; warnings do not, today.

- [x] Local `sca-cmd` 14.16.0 in CI, sha256-pinned (`scripts/sca.sh`,
  assumption AG-7); CI fails on errors and on Monitoring warnings. The weekly
  job flags a new upstream build (`.github/workflows/sca-weekly.yml`).
- [ ] Dashboard Static Analysis on a signed package. Never run: there is no
  developer account or signing key yet. It covers categories local `sca-cmd`
  skips (Authentication among them). Record a redacted report.
- [x] `rsg_version=1.3` in `manifest`.
- [ ] Minimum firmware 15.1.0 set in the dashboard's Package page. Roku made
  this and `rsg_version=1.3` blocking from 2026-10-01; its table still says
  "Warning" while the 14.16.0 changelog reports them as errors.
- [x] Memory monitor registered (`EnableMemoryWarningEvent`, with
  `EnableLowGeneralMemoryEvent` as the fallback, `source/main.bs`); also
  blocking from 2026-10-01
  ([roAppMemoryMonitor](https://developer.roku.com/dev/docs/roappmemorymonitor)).
- [x] Errors the app already avoids: missing `AppLaunchComplete`, missing
  `supports_input_launch=1` and `roInput`, missing `mm_icon_focus_hd`,
  version 0.0.0, package size, `roAppManager.LaunchApp()`, ECP calls from the
  app, in-app screensavers, and `InitClientCertificates()` (blocking from
  2027-04-01; `scripts/hygiene.sh` rejects it).
- [ ] "Customer Account Requirement": the dashboard reports an error when it
  finds on-device authentication and the app record does not select "A
  customer account is required". Select it.
- [ ] `getUserData`: Static Analysis reports an error unless "all
  authenticated channels" call Roku's Request for Information API, citing the
  Roku Pay rules for subscription and ad-monetized apps. Whether it fires for
  a free app with its own accounts is **unconfirmed** (Q4).

## 4. Deep Linking Tester

Source: [implementing deep linking](https://developer.roku.com/dev/docs/implementing-deep-linking)
and [developer tools](https://developer.roku.com/dev/docs/dev-tools).

- [ ] Device keyed with the app's developer key (required for production
  apps).
- [ ] The tester's web page and its companion Roku app installed.
- [ ] For each of `movie`, `episode`, `series`, and `season` from the reviewer
  server: Launch and Input. Expected: plays directly at the server's resume
  point, with no profile picker and no resume prompt; a series plays its play
  target (spec 8.3); a season plays its series' target.
- [ ] A made-up `contentId` opens Home (spec 10.1).
- [ ] Signed out: the link waits through sign-in, then plays.
- [ ] Profile rule (spec 10.1): never a child profile; PIN-locked profiles
  skipped until Roku rules on PIN prompts.
- [ ] One set of sample parameters per media type entered at submission; the
  publishing guide says apps without them "will not pass certification
  testing".

Evidence so far: `scripts/device-check.sh --deeplinks` ECP matrix (hardware runs
4 and 5), not the Deep Linking Tester. Status: **Open**.

## 5. App Behavior Analysis

Sources: [App Behavior Analysis](https://developer.roku.com/dev/docs/channel-behavior-analysis-tool)
and [authenticated certification testing](https://developer.roku.com/dev/docs/authenticated-cert-testing).

- [ ] A **public** app record, left unpublished. Sign-in and sign-out scripts
  "cannot be used with beta apps".
- [ ] App record: "A customer account is required" selected, which is what
  shows the sign-in/out script fields.
- [ ] Sign-in and sign-out scripts recorded in the Roku Remote Tool as
  `.rasp` files, typing `script-login` and `script-password` in place of the
  real credentials, with at most 10 pause steps. The sign-in script also
  types the reviewer server's address, since the test-credentials form has
  no server field.
- [ ] ABA checks launch to Home within 15 s, playback start within 8 s, and
  deep linking for every media type, `series` included. Each must report
  "Passed".
- [ ] ABA runs on Roku's own test device, so the reviewer server must be
  reachable from the internet (an inference; Roku does not say so). Use HTTPS
  with a publicly trusted certificate: no HTTPS server has been tested yet
  (hardware evidence, H1 step 6).

Plan section 7 asked for ABA at the Milestone 2 and 3 exits. It has not run.
Status: **Open**.

## 6. Store listing and assets

Sources: [publishing guide](https://developer.roku.com/dev/docs/channel-publishing-guide),
[manifest](https://developer.roku.com/dev/docs/channel-manifest),
[graphics](https://developer.roku.com/dev/docs/graphics).

| Item | Roku requirement | Silo status |
| --- | --- | --- |
| App poster | 540×405 JPEG or PNG (graphics diagram: 486×365 safe zone) | `images/icon_focus_fhd.png` serves; the wordmark sits inside the safe zone |
| Screenshots | Up to six, 1920×1080 JPEG or PNG | Not made; take them on a server with content the project may show, suitable for all ages (6.3) |
| `mm_icon_focus_fhd` | 540×405 | Official wordmark on the radial blue field of the Android TV banner (`images/icon_focus_fhd.png`) |
| `mm_icon_focus_hd` | 290×218 | The same (`images/icon_focus_hd.png`) |
| `splash_screen_fhd` | 1920×1080; the manifest page calls it optional, criterion 6.4 requires FHD | Official wordmark on `#161616` |
| `splash_screen_hd` | 1280×720, required | The same |
| `splash_screen_sd` | 720×480, required | The same |
| Side icons, `mm_icon_focus_sd` | No longer required | None |
| App name | At most 30 characters; must not include "Roku" | `Silo` (`manifest` `title`); needs the trademark owner's permission (`images/NOTICE`) |
| On-device description | At most 300 characters | Not written |
| Online description | At most 1,500 characters | Not written |
| Release notes | At most 1,500 characters | Per release |
| Category, age rating, "Made for kids?" | Required listing fields | Not chosen; "Made for kids" is no |
| Countries and default language | Required | English first (`locale/en_US`); countries not chosen |
| Privacy policy URL | Roku displays it; required before publishing ([provider data policy](https://docs.roku.com/published/providerdatapolicy/en/us)) | Draft in [`privacy-policy.md`](privacy-policy.md); needs review and a hosted URL |
| Terms and conditions URL | Field in the app profile; whether it is mandatory is **unconfirmed** | None |
| Customer support URL, email, phone | App profile fields; the Distribution Agreement (Exhibit A §3.4) also says support contacts must be "easily discoverable by end users" | None; whether the store listing is enough or the app must show them is **unconfirmed** |
| "Do customers sign in to your app?" | Yes, with test credentials and a "Valid until" date | Reviewer server not set up (section 9) |
| Pricing | Free or pay-to-install | Free |
| Minimum firmware | Package page field | 15.1.0 |
| Deep-linking parameters | One set per media type | From the reviewer server's seed |
| Scheduling | Publishing at the earliest on the second business day, not on Fridays or weekends; rollback within four days | Plan the release date around it |

Plan section 9.1 wanted the store listing inputs by Milestone 3. Status:
**Open**.

## 7. Device matrix

Spec section 12.4 and plan section 3. Every hardware row so far comes from
dev builds, except runs 4 and 5's release cold launches and the `perf` builds
(the release configuration with `perf` on) of runs 10 and 19's T7. Runs 1–28
used the Roku TV: through run 21 against the lab server, whose proxy node was
off except for run 10's T5, and from run 22 against a Silo development server
that routes plans through proxy nodes. Runs 29 and 30 used the Ultra, run 30
against that development server (run 29 does not name its server).

| Role | Device | Tested |
| --- | --- | --- |
| Roku TV | TCL 55R625 (A109X), Roku OS 15.3.4, 4K panel with HDR10, HLG, and Dolby Vision, TV speakers | Runs 1–28 |
| 512 MB current player | Streaming Stick 3840X | No |
| 512 MB slow CPU | Express 3930X or 3900X | No |
| Non-OpenGL | Express 3710X/3700X or Roku TV 5000X | No |
| Certification reference | Streaming Stick+ 3810X or Premiere+ 3921X (Roku measures 3.2–3.6 on these) | No |
| 4K player without Dolby Vision | Streaming Stick Plus 3830X or Express 4K+ | No |
| 4K Dolby Vision player | Streaming Stick 4K 3820X | No |
| Flagship | Ultra 4850X/4850R | Ultra 4850X, Roku OS 16.0.4: runs 29 (Settings, TV layout) and 30 (format claims) |
| Sinks | Dolby Vision TV on a player, HDR10-only TV, SDR 1080p TV, Atmos AVR or soundbar, DTS sink | Dolby Vision TV on the Ultra (run 30); no other sink (TV speakers only; audio never heard) |
| Roku OS | 15.1 floor, current 15.x, 16.0 | 15.3.4 (Roku TV) and 16.0.4 (Ultra); not the 15.1 floor |

Spec 12.4 per-device list, on the Roku TV:

| Check | Roku TV result |
| --- | --- |
| Cold and warm launch | Cold launch PASS (runs 4, 5, 8 T4b); warm launch not recorded |
| Logout, token expiry, profile PIN | PASS (runs 4, 5, 8 T4b) |
| Server replacement | Not run (one lab server) |
| Long rows, large grids, fast navigation | PASS (run 5); texture at 90% of the maximum against a 70% target (run 5) |
| Image failures | Not run |
| H.264/AAC direct play | PASS (runs 4, 5) |
| HEVC and VP9 eligibility | HEVC partial (HEVC Main 10 original never observed); VP9 claimed from the probe (run 30 on the Ultra: profiles 0 and 2 played as originals) |
| HLS remux and transcode | PASS in dev builds (runs 3–5) |
| AC-3/E-AC-3 fallback, output-route changes | Decode reported (runs 2, 4, 5); output changes never run (H13) |
| Seek, pause/resume, Replay | PASS (runs 5, 6) |
| Long playback across a token refresh | FAIL in run 8 (T1a, T1b); PASS after the fix in runs 9 and 10 (T1a) and run 19 (T4, renewal while buffering) |
| API restart during playback | PASS (run 8 T2a, T2b); run 8's T2c resume-point regression PASS after the fix in run 9 |
| Quality, audio, subtitle, forced burn-in replans | PASS or PARTIAL (runs 6, 7) |
| Skip markers, next-episode countdown | PASS (run 7) |
| Unicode metadata and subtitles | Partial: CJK and Arabic render as boxes (assumption A-17) |
| Memory-monitor events, app resume | Events PASS (run 5 memory check); app resume not run |
| Valid, invalid, inaccessible, unauthenticated deep links | PASS (runs 4, 5) |

Status: **Open**. At least the 512 MB player, the certification reference
device, and a 4K streaming player must run this list before beta.

## 8. Beta

Sources: [publishing guide](https://developer.roku.com/dev/docs/channel-publishing-guide)
and the [Roku Distribution Agreement](https://docs.roku.com/published/developerdistribution/en/us)
(last updated 2026-08-28).

Roku's limits: a beta app lasts 120 days; an account may hold up to 10 beta
apps at a time and up to 20 testers per beta app; beta apps need no
certification and "cannot be published to the public Streaming Store"; testers
install with the beta's access code; the Distribution Agreement allows the
beta environment "for internal testing only".

- [ ] Section 1 blockers 1, 2, 4, 6, 7, and 8 resolved.
- [ ] Roku developer account owned by the Silo-Server organization.
- [ ] Signing key made with `genkey` on one designated device; developer ID,
  password, and a signed reference package in the team's secret manager with
  two custodians; never in git (plan 9.1). Losing it means a new app and a
  forced sign-in for every viewer (criterion 4.1).
- [ ] Release build from a clean checkout: `npm ci`, `npm run ci` green,
  `build_version` stamped, debug and test components excluded
  (`scripts/hygiene.sh`), then packaged and signed with the key. The Package
  workflow (`.github/workflows/package.yml`) does this for beta and release
  packages; see the README's "Signed packages".
- [ ] Uploaded to a beta app; dashboard Static Analysis run and its
  authentication findings triaged (section 3).
- [ ] Install-over-existing-data rehearsal: a newer package signed with the
  same key keeps the saved server, tokens, remembered profile, profile PIN
  token, and installation ID (plan 9.1, criterion 4.1).
- [ ] The beta's expiry date recorded; the beta is re-created before 120 days
  and testers get the new access code.
- [ ] Testers (at most 20) recorded by household label only. Each report
  notes device model, Roku OS, server version, HTTP or HTTPS, and whether
  proxy nodes serve media; never addresses, accounts, or titles.
- [ ] Results added to [`hardware-evidence.md`](hardware-evidence.md) as rows.

Status: **Open**; nothing above is done.

## 9. Public-submission prerequisites

- [ ] Roku's answers, or a reduced fallback scope for each "no". Plan
  section 9.2 requires answers on LAN HTTP, private catalogs, criterion 4.3, the authentication
  rules, and PINs on deep links.
- [ ] Milestone 3 exit met on hardware (spec section 13, plan section 9.2).
- [ ] Milestone 4 gates (spec section 13): performance, memory,
  accessibility, privacy, store assets, Static Analysis, and App Behavior
  Analysis.
- [ ] A Roku beta exercised by real Silo households, if Roku allows it.
- [ ] Server releases that include S-20 (`request_origin` and no off-origin
  redirects), S-22 (playlists under 4 MiB), and S-15 (TS copy remux), or a
  recorded decision to ship a narrower claim.
- [ ] Reviewer server (spec 10.2, plan 7): an owner and a host; reachable from
  the internet over HTTPS with a publicly trusted certificate; one PIN-free
  adult profile; a seeded movie, series, and episode suitable for all ages,
  with trickplay sheets and server-generated markers; test credentials with a
  "Valid until" date; the address in the credentials' description and typed
  by the ABA script.
- [ ] Privacy policy reviewed by the project owner, published at a stable
  URL, and its findings resolved ([`privacy-policy.md`](privacy-policy.md)).
- [ ] Terms URL and support contacts.
- [x] Official artwork (`scripts/brand-art.py`).
- [ ] The trademark owner's written permission.
- [ ] Dashboard Static Analysis with no errors; Deep Linking Tester and App
  Behavior Analysis passed on the public app record.
- [x] Version and channel mapping: `X-Silo-Client-Channel` `release` for the
  store package, `beta` for beta packages (`npm run build:beta`).

## 10. Milestone 4 gates without a section above

| Gate | Target | Evidence | Status |
| --- | --- | --- | --- |
| Performance | Plan section 1 table on the reference and 512 MB devices | Launch only, on the Roku TV (run 5) | Open |
| Memory | Below 80% of the limit, no memory exit; texture below 70% in browse | Memory events PASS (run 5); texture 90% (run 5) | Open |
| Accessibility | Audio Guide on every focusable; Roku caption settings | Never checked on hardware | Open |
| Privacy | Policy matches the code; spec 11 holds | [`privacy-policy.md`](privacy-policy.md) lists the mismatches | Open |

## 11. Roku sources

Read on 2026-10-22. developer.roku.com pages also serve raw Markdown when
`.md` is added to the URL; docs.roku.com legal pages render only with
JavaScript, and their text is served at
`https://docs.roku.com/api/v1/published/<document>/en/us`.

- Certification criteria: <https://developer.roku.com/dev/docs/certification>
- Certification tests: <https://developer.roku.com/dev/docs/cert-tests>
- Static Analysis: <https://developer.roku.com/dev/docs/static-analysis-tool>
- `sca-cmd` changelog: <https://devtools.web.roku.com/static-channel-analysis/CHANGELOG.md>
- Publishing guide (beta apps, listing, test credentials): <https://developer.roku.com/dev/docs/channel-publishing-guide>
- App Behavior Analysis: <https://developer.roku.com/dev/docs/channel-behavior-analysis-tool>
- Authenticated certification testing: <https://developer.roku.com/dev/docs/authenticated-cert-testing>
- Deep linking: <https://developer.roku.com/dev/docs/implementing-deep-linking>
- Direct to Play: <https://developer.roku.com/dev/docs/direct-to-play>
- Developer tools: <https://developer.roku.com/dev/docs/dev-tools>
- Manifest: <https://developer.roku.com/dev/docs/channel-manifest>
- Graphics: <https://developer.roku.com/dev/docs/graphics>
- Measuring performance (beacons): <https://developer.roku.com/dev/docs/measuring-channel-performance>
- Memory monitor: <https://developer.roku.com/dev/docs/roappmemorymonitor>
- Registry: <https://developer.roku.com/dev/docs/roregistry>
- On-device authentication and linking: <https://developer.roku.com/dev/docs/authentication-and-linking>
- Roku Event Dispatcher: <https://developer.roku.com/dev/docs/prioritizing-authenticated-channels-in-roku-search>
- Roku Distribution Agreement: <https://docs.roku.com/published/developerdistribution/en/us>
- Provider data policy: <https://docs.roku.com/published/providerdatapolicy/en/us>

Not found on Roku's pages: any rule on media-server apps that play a
household's own library, LAN or plain-HTTP origins, a minimum amount of content
for review, a data-practices questionnaire, whether the privacy policy URL is
required for beta apps, and whether beacon timings leave the device.
