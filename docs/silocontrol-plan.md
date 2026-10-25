# SiloControl receiver: implementation plan

**Status:** Draft, not yet reviewed

**Last updated:** 2026-10-24

**Companion to:** [`silocontrol.md`](silocontrol.md), which says what the
receiver does; this plan says in what order it is built and how each step is
shown to work. It is Milestone 5 and starts after the first public release
(spec section 3.3), except the spikes in phase C0 and the Roku question,
which can run earlier.

A section number with an R (R8.1) is in [`silocontrol.md`](silocontrol.md);
"spec section" means [`spec.md`](spec.md).

## 1. Goal and exit

A Silo phone app on the same network as a Roku running Silo can:

1. find the Roku in its TV list with no setup, and connect (or, on a
   network that blocks multicast, scan or type the Roku's address);
2. control what plays, with state on the phone within one second;
3. start a title on the profile open on the Roku;
4. start a title as the phone's own profile through a handoff, which leaves
   the Roku's sign-in and remembered profile untouched;
5. do all of this at level `sealed`, after one QR scan, when the household
   turns on Require Pairing.

Milestone 5 exits when items 1–4 pass on the 512 MB and 4K devices with the
iOS and Android phone apps, item 5 passes or has a dated phone-app plan, the
beta has run with real households, and Roku has confirmed the receiver
or the owner has recorded a decision.

## 2. Principles

- The receiver asks the player to act; it never touches the `Video` node.
- Handoff HTTP goes through `ApiTask` and the auth coordinator, like every
  other request (AGENTS.md: no feature-local auth retry).
- Nothing on the control channel or in logs carries a token, a signed URL, a
  device code, a user code, a match code, or a resume token.
- Policy and protocol logic are pure functions with Rooibos tests; the task
  only moves bytes.
- No ECP client code anywhere (Static Analysis blocks it; R2.1).

## 3. Phases

### C0 — Spikes (hardware; can start now)

Each spike is a throwaway branch with a written result in
[`hardware-evidence.md`](hardware-evidence.md). The 2026-10-24 probe app
(R5.1) is the starting point for C0-1, C0-2, and C0-7.

| ID | Question | Pass |
| --- | --- | --- |
| C0-1 | Does a `roStreamSocket` listener in a `Task` accept and serve a client on 512 MB and 4K devices while a `Video` plays 4K HEVC, and across Instant Resume? Is port 52817 free? | Accepts within 100 ms; no dropped frames attributable to it; rebinds after resume |
| C0-2 | Does Roku report an accepted socket's peer address? | **Passed 2026-10-24** on the TCL Roku TV: `getReceivedFromAddress` gives the peer (R5.1) |
| C0-3 | Cost of AES-128-CBC plus HMAC-SHA256 for a 2 KB frame on the 512 MB device | Under 5 ms per frame; four controllers at 2 Hz under 5% CPU |
| C0-4 | Can BrightScript write a 1-bit PNG to `tmp:/` and show it in a `Poster` sharp enough to scan at 3 m? Encoder time? | Scans on iOS and Android cameras; under 300 ms to encode on the 512 MB device |
| C0-5 | Does the `Video` node's `mute` field work on Roku TVs and players, with passthrough audio too? | Mutes and unmutes on both devices |
| C0-6 | Does Static Analysis flag a listening socket or a socket on UDP 5353? | No error or warning |
| C0-7 | Does the app's mDNS responder work beyond the first device? First device **passed 2026-10-24** (TCL Roku TV 55R625, Roku OS 15.3.4, with AirPlay; R5.1). Still: a Roku streaming player, a 512 MB device, an iPhone and an Android phone browsing, a network change, and two Rokus on one network | Each finds and resolves the Roku within 3 s of opening the picker; Roku OS's own AirPlay record still resolves |

### C1 — Receiver core and the development controller

| PR | Content |
| --- | --- |
| C1-1 | `source/control/protocol.bs`: envelope, every message type, validation; Rooibos tests against wire fixtures vendored from silo-apple's `SiloControlWireCompatibilityTests.swift` and silo-android's cast tests, with a `SOURCE` pin |
| C1-2 | `source/control/policy.bs`: hello negotiation, authorization, eviction, rate limit, close-reason rules; tests |
| C1-3 | `components/tasks/ControlTask`: listener with port fallback, peer check, framing with the 64 KiB cap, hello watchdog, heartbeat, `close`; starts and stops with the session (R10) |
| C1-4 | `source/control/mdns.bs` and the mDNS socket in `ControlTask` (R5.1): query parsing with name compression, the four records, announce and goodbye; Rooibos tests on packets captured from macOS and Android queries |
| C1-5 | `scripts/silocontrol-phone.mjs`: a Node controller that plays the phone role (hello, ping, control, launch, and later handoff and `sealed`) against `host:port` from `.env`; documented in the README's Development section |

Exit: `dns-sd` on a Mac finds and resolves the Roku; the Node controller
finds it, connects, negotiates v2, sees idle `state`, survives an hour of
heartbeat, and is closed correctly on sign-out (R10), after which the
records are gone; four controllers plus a fifth exercise the eviction order.

### C2 — Control what plays

| PR | Content |
| --- | --- |
| C2-1 | Player bridge: `remoteCommand` and `remoteState` fields on `Player.xml`; `source/control/state.bs` builds `state` |
| C2-2 | R6.5's command table, reusing the player's own seek, track, quality, Up Next, and Back paths |

Exit: from the Node controller, on both devices: play, pause, seek, track and
quality changes, next episode, mute, and stop behave as with the Roku remote;
`state` arrives at 2 Hz and after each command; unsupported commands answer
`command_failed`.

### C3 — Connect a Phone

| PR | Content |
| --- | --- |
| C3-1 | `source/util/qr.bs` from spike C0-4, with test vectors |
| C3-2 | Connect a Phone screen and avatar-menu row; the connected-phone notice; address-change updates |
| C3-3 | Spec section 5.9 and `locale/` strings |

Exit: a phone camera reads the link; the address and DNS-SD records follow a
network change;
before/after screenshots in the evidence folder.

### C4 — Launch on the open profile

| PR | Content |
| --- | --- |
| C4-1 | Own-profile `handoff_ready` (R8.1), `resumeToken`, launch authorization |
| C4-2 | Launch into `nav.player.withTracks` from any shell screen; `launch_pending`, `launch_failed`, `player_not_ready`; replace confirmation; deep links closing a controller's player |

Exit: a launch with each combination of version, tracks, and start point
plays as the same choice from the detail screen would.

### C5 — Profile handoff

| PR | Content |
| --- | --- |
| C5-1 | Auth coordinator: the borrowed identity lane (R8.3): memory only, its own refresh lane, the player's requests tagged to it, logout on end; tests that the registry and remembered profile never change |
| C5-2 | `source/control/handoff.bs` (R8.2): capability, start, challenge, poll, cancel, ready, reuse, the 60-second launch timeout, `temporary_session_expired` |
| C5-3 | "Playing as" card; the `handoff` build switch (on in `dev` and `beta`, off in `release` until the decision in section 6) |
| C5-4 | Node controller: handoff with a second test account's profile (approve-handoff), including a PIN profile |

Exit, on both devices:

- a non-PIN and a PIN profile play, report progress to the phone's profile,
  and end with one logout;
- the account's session list shows the handoff session during playback and
  not after;
- an expired or revoked handoff session stops playback with the error;
- Back, stop, end of title, next episode, a deep link, sign-out, and
  leaving the app each end the identity correctly;
- after every case, the Roku's own profile, Continue Watching, and remembered
  profile are as before.

### C6 — `sealed`

| PR | Content |
| --- | --- |
| C6-1 | `source/control/sealed.bs`: key derivation and frame seal and open, with published test vectors the phone apps share |
| C6-2 | Pairing key creation, Reset Pairing Code, `sealed_hello`, the "Allow phones without a code" toggle |
| C6-3 | Node controller speaks `sealed` |

Exit: the vectors pass on both devices; tampered, replayed, reordered, and
wrong-key frames close the connection; C0-3's budget holds.

### C7 — Phone apps (silo-apple and silo-android)

Work in those repositories, agreed with their maintainers. Each item can
start once the Roku phase it depends on works with the Node controller.

| Item | After |
| --- | --- |
| Browse `_silocast-roku._tcp` beside `_silocast._tcp` (iOS `NSBonjourServices`) and list Rokus with the other TVs | C1 |
| Dial a Roku target over plain TCP, never TLS | C1 |
| "Open Silo on your Roku" when a remembered Roku is not found | C1 |
| Fallback: Connect to TV by scanned `silo://cast` link or typed address | C3 |
| Hide the volume slider for `volume_mute_only` | C2 |
| Confirm `audioTrackIndex` and `subtitleTrackIndex` are server ordinals in both apps | C4 |
| `sealed` with the shared vectors | C6 |

### C8 — Beta and release

- Privacy policy: the app listens on the local network while open and shows
  connected phones' names; nothing new leaves the device
  ([`privacy-policy.md`](privacy-policy.md)).
- Release checklist rows for the receiver
  ([`release-checklist.md`](release-checklist.md)).
- Hardware matrix (section 4) on the current Roku OS and the one in beta.
- Beta with real households: at least one iOS and one Android phone each,
  one household with two phones.
- Static Analysis and App Behavior Analysis clean with the receiver on.
- Section 6's decision recorded before a public build turns on `handoff`.

### C9 — Later

- Cross-server handoff (R8.4): a second origin in the API layer
  with its own origin check.
- A TV list kept by the Silo server, only if beta households report
  networks that block multicast. It needs a server route and phone work.

## 4. Hardware tests

| ID | Test |
| --- | --- |
| HC-1 | Listener during 4K HEVC HDR playback on the 4K device and H.264 on the 512 MB device; frame drops and memory against the spec section 4 budgets |
| HC-2 | Four controllers at 2 Hz for an hour; memory flat within 5% |
| HC-3 | Network change, DHCP renewal to a new address, Wi-Fi off and on |
| HC-4 | Instant Resume suspend and resume; leaving and reopening the app |
| HC-5 | Handoff end paths (C5 exit list) |
| HC-6 | `sealed` cost (C0-3) at four controllers |

## 5. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Roku reads handoff as off-device authentication (criterion 2.2) | Rejection of an update | The owner accepted the risk on 2026-10-25 (D-7): `handoff` is on in every build; turning the switch off removes it without touching control or own-profile launch |
| A Roku reviewer reads the listener as against 4.15 | Rejection | Roku's confirmation; private-peer-only accept; nothing forwarded |
| `plain` handoff on a hostile network | An attacker in the path could get a 24-hour session for the phone's profile | Same as the other TVs today; `sealed` closes it; recorded as accepted for beta |
| `GetRandomUUID()` is not a secure generator | Guessable pairing keys | Roku's confirmation; the phone-proposed key in R9.3 |
| Phone apps do not take the changes | No controller can reach a Roku | C7 coordinated before C1 merges; the Node controller keeps the Roku work testable |
| CPU on 512 MB devices | Playback stutter while phones are connected | C0-1, C0-3; four controllers; 64 KiB frames |
| Address changes | Phones lose the Roku | The responder announces the new address; phones find the Roku again by `id` |
| Networks that block multicast (guest Wi-Fi isolation, some mesh systems, VLANs) | Phones do not list the Roku | Address and QR code on Connect a Phone; a server-kept list in C9 if needed |
| A Roku OS update takes UDP 5353 exclusively | Discovery stops | C0-7 on each new Roku OS; the fallback above |

## 6. Questions and decisions

- **Open with Roku:** handoff under 2.2, the listener under 4.15, and
  `GetRandomUUID()`.
- **Handoff in public builds:** decided 2026-10-25: the project owner
  accepted the risk before Roku confirms these, and `handoff` is on in every build (D-7, spec
  section 15).

## 7. Spec changes

Landed with this plan (2026-10-24):

- Spec section 3.3: the receiver, with its own DNS-SD advertisement, is
  planned in [`silocontrol.md`](silocontrol.md); setup by phone, server
  discovery, and DIAL stay deferred.
- Spec section 7.2: device-code sign-in stays out of public builds because
  Roku allows rendezvous linking only in TVE apps; handoff is gated
  separately.
- Spec section 10.2: the ECP rule for phone apps and the receiver's 4.15
  reading.
- Spec section 15: the device-code and SiloControl rows.

Lands with C3: spec section 5.9 rows for Connect a Phone and the avatar
menu.
