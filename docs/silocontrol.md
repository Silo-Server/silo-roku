# SiloControl receiver for Roku

**Status:** Implemented in every build (bs_const `silocontrol` and
`handoff`, on since 2026-10-25, decision D-7). Tested on a Roku Ultra with
the development phone script (`scripts/silocontrol-phone.mjs`), after the
discovery spike on a TCL Roku TV (section 5.1); not yet with the Silo phone apps or on low-memory hardware

**Last updated:** 2026-10-25

**Companion to:** [`spec.md`](spec.md) (product and platform rules) and
[`silocontrol-plan.md`](silocontrol-plan.md) (build order). This document
says what the Roku app does as a SiloControl receiver: a Silo phone app on
the same network controls playback on the Roku, starts titles on it, and can
play them as the phone's own profile (profile handoff).

## 1. Decision summary

| Topic | Decision |
| --- | --- |
| Scope | Control what is playing, launch a title from the phone, and profile handoff, all against the Roku's own Silo server. Cross-server handoff comes later (section 8.4) |
| Protocol | SiloControl v2 messages and framing as the Apple and Android TVs speak them (section 6), with the Roku differences in section 12 |
| Finding the Roku | Automatic: the app runs its own multicast DNS responder and advertises `_silocast-roku._tcp`, which updated phone apps browse beside `_silocast._tcp`. A hardware spike on 2026-10-24 showed it works beside Roku OS's own responder. The Connect a Phone screen's address and QR code are the fallback for networks that block multicast. No DIAL, no ECP (section 5) |
| Transport security | No TLS: Roku sockets have none. Level `plain` is the default, so a phone connects with no setup, as with the other Silo TVs. Level `sealed` (a pairing key from a one-time QR scan, AES-128-CBC with HMAC-SHA256) follows as an opt-in, "Require pairing" (section 9) |
| Handoff | Silo's existing `remote_playback` device login. No server change (section 8) |
| Identity | The handoff identity lives only in memory, is used only by the handoff's player, and never replaces the Roku's saved sign-in (section 8.3) |
| When it runs | Only while the Silo app is open on the Roku and signed in. The phone cannot open the app (section 2.1) |
| Release | On in every build, handoff included, by the project owner's decision of 2026-10-25 (decision D-7 in [`implementation-assumptions.md`](implementation-assumptions.md)), which accepts the risk before Roku confirms it (section 2.3) |

## 2. Roku policy

Read from Roku's developer pages on 2026-10-24.

### 2.1 External Control Protocol

Roku's [ECP page](https://developer.roku.com/docs/developer-program/dev-tools/external-control-api.md)
(updated 2026-10-15) says "ECP commands may not be sent from 3rd-party
platforms (for example, mobile applications)", and Static Analysis blocks
publishing any app that contains code to send ECP commands. Apps may still
receive deep links and voice commands that the Roku OS delivers.

So a Silo phone app never sends `launch`, `keypress`, or `input` to port 8060,
and this app contains no ECP client code. The consequence is that the phone
cannot start the Silo app on the Roku: the viewer opens it with the Roku
remote, and the phone app says so when it cannot connect (section 4.4).

### 2.2 Criterion 4.15

Criterion 4.15 bars using the device "to route network traffic for third
parties", operating "as a proxy, relay, or exit node", or using it "for any
purpose not directly related to the app's stated purpose" (that last clause
arrived with Roku's Fall 2026 update). The receiver serves the app's own
playback, accepts connections only from the local network (section 5.5), and
forwards nothing. No criterion mentions listening sockets or companion apps.
Roku has not confirmed this yet.

### 2.3 Criterion 2.2 and profile handoff

Criterion 2.2 requires on-device authentication and bars "any other 1st or
3rd-party off-device sign-up/sign-in/authentication/activation mechanism".
Roku's [rendezvous linking page](https://developer.roku.com/docs/developer-program/authentication/authentication-and-linking.md)
(updated 2026-05-08) says "Only TVE apps may use rendezvous linking". A
handoff is a device login approved on the phone, so it reads as covered.

What other apps did:

- Plex removed its plex.tv/link code sign-in from Plex for Roku 7.6.1 in 2023,
  citing "Roku cert requirement 2.2".
- Jellyfin for Roku still offers Quick Connect (a code approved in another
  signed-in Jellyfin app) beside on-device password sign-in; release 3.2.4,
  scheduled for the store on 2026-09-30, contains it. That shows Roku has not
  rejected it, not that Roku approves.

How this design limits the exposure:

- Only the Roku's own sign-in, password on the device or companion sign-in
  ([`companion-pairing.md`](companion-pairing.md)), saves an account on the
  Roku. A handoff never writes the Roku's registry, never changes its saved
  account or remembered profile, and ends when its playback ends.
- A phone on the profile the Roku already has open needs no handoff at all
  (section 8.1).
- A build switch, `handoff`, is on in every build: the project owner
  accepted the risk before Roku confirms it (decision D-7, 2026-10-25). Turned
  off, control still works, and so does a launch on the profile open on the
  Roku.

Discovery and the Connect a Phone pairing (section 5) carry no credential
and sign nothing in, so neither is a sign-in mechanism.

## 3. Roku platform facts

| Need | Roku | Consequence |
| --- | --- | --- |
| TCP listener | `roStreamSocket` with `listen`, `accept`, and `roSocketEvent` on a message port | The receiver runs in its own `Task` node |
| TLS | None on raw sockets | No TLS-PSK; section 9 |
| Symmetric crypto | `roEVPCipher`: AES-128/192/256 CBC, CFB, OFB, ECB on every supported OS; `aes-gcm-128` only from Roku OS 15.2, and `ifEVPCipher` has no tag or AAD methods | GCM is unusable; `sealed` uses AES-128-CBC with `roHMAC` SHA-256 |
| Key agreement | None (`roDSA` signs only) | The `sealed` key comes from the pairing QR code |
| Randomness | `GetRandomUUID()` returns a v4 UUID; Roku does not say it is cryptographically random | Section 9.3 limits what depends on it; Roku has not said |
| Local address | `GetIPAddrs()`, `GetConnectionInfo()`, `EnableLinkStatusEvent` | The Connect a Phone screen shows the current address and follows changes |
| Multicast DNS | No advertising API, but `roDataGramSocket` binds UDP 5353 with `SetReuseAddr` beside Roku OS's own responder, joins 224.0.0.251, receives queries, and its answers reach Bonjour (spike, section 5.1) | The app runs its own responder (section 5.1) |
| Background | Apps do not run in the background; Instant Resume suspends them | The receiver exists only while the app is open (section 10) |
| Volume | Apps cannot set the TV's volume; the `Video` node can only mute | Section 6.5 |

## 4. User experience

### 4.1 Connect a Phone

The Connect a Phone screen remains implemented but has no avatar-menu entry.
Its setup layout (spec section 5.4) contains:

- the heading "Control Silo from your phone" and the line "Open Silo on a
  phone on this Wi-Fi network and choose this TV";
- the phones connected now, by device name;
- under "Phone can't find this TV?", a QR code of the pairing link (section
  5.3) and the address (`192.168.1.20:52817`);
- in development builds only, Require Pairing (off by default, section
  9.4); when on, the QR code also carries the pairing key, the key shows in
  groups of four, and Reset Pairing Code disconnects every phone and draws a
  new key. Until the phone apps speak `sealed`, release builds have no
  Require Pairing control; every build has Done.

The screen follows address changes as they happen. Back returns to the
previous screen. Connected phones stay connected while the viewer browses.

### 4.2 On the Roku while a phone is connected

- When a phone connects, a four-second notice in the top bar's area says
  "<phone> connected". Nothing else changes; the Roku remote keeps working.
- A launch opens the player above the current screen. Back returns there.
- A handoff's player shows "Playing as <profile> · From <phone>" in the
  player's notice card for four seconds, where tvOS shows a card of its own
  for six; the notice card is the player's one non-focusable card.
- Starting a launch while a title plays for a different profile needs the
  phone to confirm (section 7.2).

### 4.3 What the phone can do

Play, pause, seek, stop, next episode, audio and subtitle tracks, quality,
mute, and launch with a chosen version, tracks, and start point. Speed,
aspect, subtitle timing and position, and a volume level are not on Roku
(section 6.5).

### 4.4 Phone-side expectations

These belong to the phone apps (phase C7 in
[`silocontrol-plan.md`](silocontrol-plan.md)) and are listed here because
the Roku design depends on them:

- The TV picker browses `_silocast-roku._tcp` beside `_silocast._tcp` (iOS
  lists it in `NSBonjourServices`) and shows Rokus with the other TVs.
- A target found as `_silocast-roku._tcp` is dialed over plain TCP, or
  `sealed` when its TXT says so, never TLS.
- As a fallback, Connect to TV accepts a scanned pairing link or a typed
  address.
- A remembered Roku is found again by its `id` over DNS-SD, as the other TVs
  are. When it is not there, the phone says "Open Silo on your Roku".
- The phone never sends ECP to the Roku.

## 5. Connection

### 5.1 Discovery

The app answers multicast DNS (RFC 6762) for one DNS-SD service (RFC 6763)
from `ControlTask`, while the receiver runs:

| Record | Value |
| --- | --- |
| PTR | `_silocast-roku._tcp.local` → `Silo-<first 8 of deviceId>._silocast-roku._tcp.local` |
| SRV | priority 0, weight 0, the listener's port, target `silo-<first 8 of deviceId>.local` |
| TXT | `v=2`, `name`, `id`, `server`, `serverName`, `playing` (`1` or `0`), `serverIdentity`, `sec` (`plain` or `sealed`), and at `sealed` `kid` (the key ID, section 9.2): the other TVs' keys plus the last two |
| A | the host name → the Roku's IPv4 address |

- The service type is separate from the other TVs' `_silocast._tcp` so that
  phones which only speak TLS never list a Roku they cannot reach.
- The instance and host names carry the installation ID, so two Rokus with
  the same friendly name never collide; phones show TXT `name`. The app
  does not probe for conflicts.
- The socket is a `roDataGramSocket` with `SetReuseAddr(true)`, bound to
  port 5353, joined to 224.0.0.251, TTL 255, multicast loop off. The receive
  buffer is an `roByteArray` filled to its full length first: after
  `SetResize` alone its `Count()` is 0, every `receive` returns 0 bytes, and
  the readable event repeats without end (spike, below).
- It reads each query's questions, following name compression, and answers a
  PTR question for the service type with all four records, a PTR question
  for `_services._dns-sd._udp.local` with a PTR to the service type, and an
  SRV, TXT, or A question for its own names with that record (an SRV with
  the A record too). Answers go to 224.0.0.251:5353 from port 5353, including for
  questions that ask for a unicast reply. Known-answer suppression is not
  implemented.
- It announces the four records at start and on any change (address, port,
  `playing`, server, `sec`), three times: at once, then one and two seconds
  apart (RFC 6762's doubling), and sends them with TTL 0 when the receiver
  stops.
- TTLs: 120 seconds for PTR, SRV, and A; 4500 for TXT.

**Spike, 2026-10-24.** A 55" TCL Roku TV (55R625, Roku OS 15.3.4), which
advertises AirPlay and so runs Roku OS's own responder, ran a probe app:

- binding 5353 with `SetReuseAddr` and joining the group both succeeded;
- the socket received the network's own mDNS traffic (about 10 packets and
  3.5 KB a second on a network with nine AirPlay devices);
- from a Mac on the same network, `dns-sd -B` found a fresh service type
  with no announcements sent, so through the query path, and `dns-sd -L` and
  `dns-sd -G` resolved its SRV, TXT, and address;
- the Roku's own `_airplay._tcp` record still resolved;
- a TCP connection to the advertised port reached the app, which read the
  peer's address (`getReceivedFromAddress`; the port prints as a signed
  16-bit number).

Still to show: a Roku streaming player, a 512 MB device, an iPhone and an
Android phone browsing, and a network change (plan C0-7).

### 5.2 Listener

- The receiver listens on TCP port 52817, or the first free port up to
  52826, then any port the OS assigns. DNS-SD, the screen, and the link carry
  the bound port.
- It listens on IPv4 only. IPv6 is out of scope until the phones dial it.
- It starts when the app is signed in and stops on sign-out, server change,
  low memory at the critical level, and suspension (section 10).

### 5.3 Pairing link

```text
silo://cast?v=2&host=192.168.1.20&port=52817&id=<deviceId>&name=<name>&server=<serverId>&security=plain
silo://cast?v=2&host=...&port=...&id=...&name=...&server=...&security=sealed&key=<base32 key>
```

- `id` is the installation ID (spec section 7.4); `server` is the hello's
  `serverId` (section 6.2); `name` is URL-encoded.
- `key` is the 16-byte pairing key in RFC 4648 base32 without padding (26
  characters), shown on screen in groups of four.
- Phones ignore parameters they do not know. The link carries no credential.
- A phone that scans it remembers the Roku by `id` and the key, then finds
  it over DNS-SD like any other TV, or dials `host:port` when DNS-SD finds
  nothing.

### 5.4 QR code

The Roku draws the QR code itself: byte mode, error correction M, at most
version 10 (213 bytes). An encoder in BrightScript writes a 1-bit PNG to `tmp:/` for a
`Poster`. It runs in a `QrTask`, which keeps the encoding and the file off the
render thread. Nothing leaves the device to draw it. Spike C0-4 in the plan
chooses between the PNG and a grid of `Rectangle`s.

### 5.5 Accepting connections

- The receiver accepts a connection only from a private, link-local, or
  loopback IPv4 peer (RFC 1918, 169.254/16, 127/8), and closes any other at
  once. The spike showed Roku reports the peer address.
- At most four controllers are connected. Past four, the receiver evicts in
  tvOS's order: a connection that never sent hello, then an unauthorized
  controller not mid-handoff, then the oldest passive controller; otherwise
  it answers the newcomer with hello, `error too_many_controllers`, and
  `close too_many_controllers`.
- A connection that sends nothing valid within 5 seconds of connecting is
  closed with `close timeout`.

## 6. Protocol

### 6.1 Framing

As the other Silo TVs: a 4-byte big-endian unsigned length, then that many
bytes of UTF-8 JSON in the envelope `{"type": "<kind>", "v": 2, "<payloadKey>":
{...}}`. Roku accepts frames up to 64 KiB, not 1 MiB, to bound memory; it
answers a larger length with `close` and drops the connection. No phone
sends a frame near that size today.

At level `sealed` each frame body is sealed (section 9.2); the length prefix
counts the sealed body.

### 6.2 Hello

The Roku writes its hello as soon as a connection is accepted (and, at
`sealed`, the session is keyed), without waiting for the phone's:

| Field | Roku value |
| --- | --- |
| `role` | `"tv"` |
| `deviceName` | The Roku's friendly name (`GetFriendlyName()`), clamped as `X-Silo-Device-Name` is |
| `deviceId` | The installation ID |
| `serverId` | base64url without padding of the configured origin, normalized as the phones do (whitespace and trailing slashes trimmed) |
| `serverName` | The server's name from `GET /api/v2/system/info` |
| `serverIdentity` | `server_id` from `GET /api/v2/system/identity`, read at sign-in and each launch |
| `supportedVersions` | `[2]` |
| `features` | `multi_controller`, `close_reason`, `resume_token`, `replace_confirmation`, `presence`, `volume_mute_only`, `no_playback_speed` (section 6.5) |

A phone hello must have `role: "phone"`, a non-empty `serverId`, and list 2;
otherwise the Roku sends `error version_unsupported` and `close
unauthorized`. A second connection from the same `deviceId` closes the older
one with `close replaced`.

A controller is authorized for control when its `serverId` equals the
Roku's or its `serverIdentity` equals the Roku's. An unauthorized controller
stays connected so it can complete a handoff; it gets no `state`, and its
`launch` or `control` gets `error unauthorized`.

### 6.3 Messages

Every message type, field, error code, and close reason is as the Apple TV
and Android TV receivers define them. The receivers' sources are the
reference (`Control/SiloControlProtocol.swift` in silo-apple,
`shared/.../cast/SiloCastMessage.kt` in silo-android); the plan vendors their
wire examples as test fixtures. The Roku:

- ignores an unknown `type` and an unknown `control.name`, and closes on a
  known type with a malformed payload;
- answers `ping` with `pong`, pings every 3 seconds, and closes a controller
  after more than 3 missed pongs; only a `pong` that arrives after a ping has
  left the Roku's socket resets that count, so a peer that reads nothing
  cannot stay connected by sending unasked pongs;
- closes a controller at once, without a `close`, when more than 128 KB
  waits to be sent to it or its socket takes nothing for 10 seconds while
  frames wait;
- applies tvOS's command budget: 20 commands a second, bursts of 40,
  `error rate_limited` at most once a second;
- sends `close` with its reason before closing, under a 500 ms limit, and
  sends a reason only to peers that list `close_reason`.

### 6.4 State

The Roku sends `state` to every authorized controller every 500 ms while a
title plays, after every command, and once on connecting. While earlier
frames to a controller still wait to be sent, only the newest `state` waits
behind them; it is sealed and numbered when it is queued, ahead of any later
reply, so sealed sequence numbers stay consecutive. With no player it
sends the idle state tvOS sends. Fields:

- `contentId`, `sessionId`, `title`, `subtitle` (the episode line),
  `currentTime`, `duration`, `isPlaying`, `isLoading`, `isBuffering`,
  `error`, from the player;
- `audioTracks` and `subtitleTracks` as `{kind, trackId, title, detail}`,
  from the player's Options panel (`playback.options.model`), and the
  selected IDs. An audio `trackId` is the server's audio ordinal (`index`,
  as `source/playback/intent.bs` uses it); a subtitle's is its plan
  inventory's `combined_index`, which `select_subtitle_track` maps back to
  the inventory's `track_id`;
- `qualityOptions`, `activeQualityId`, and `isQualitySwitching` from the
  player's quality menu, `"auto"` included;
- `hasNextEpisode` and `nextEpisodeTitle` from Up Next;
- `volume` 1 or 0 and `isMuted` (section 6.5);
- `playbackSpeed` 1, `videoGravity` `"fit"`, `supportsVideoGravity`,
  `supportsSubtitleDelay`, and `supportsSubtitlePosition` false;
  `supportsHDRToggle` and `hdrEnabled` false (the Android phone requires
  both fields; no phone shows an HDR toggle without `supportsHDRToggle`).

`posterUrl` is never sent: image URLs can carry signed query strings, which
spec section 11 keeps out of logs and displays, and the LAN channel is
treated the same way. The phone already has the title's artwork from its own
server. `overview` is left out to keep frames small.

### 6.5 Controls on Roku

| `control.name` | Roku |
| --- | --- |
| `play`, `pause`, `play_pause` | The player's own play and pause |
| `seek` | The player's seek path, as a committed scrub; under Up Next, Keep Watching first, and after the end a replay from there (spec section 5.7) |
| `stop` | Closes the player as Back does, final progress included |
| `play_next` | Up Next's next episode; `error command_failed` without one |
| `select_audio_track`, `select_subtitle_track` | The Options menu's track change (a replan where the plan needs one); `trackId` absent means subtitles off |
| `set_quality` | The Options menu's quality change |
| `set_muted` | The `Video` node's `mute` |
| `set_volume` | 0 mutes, anything above 0 unmutes; Roku cannot set a level |
| `set_playback_speed`, `set_video_gravity`, `set_subtitle_sync_ms`, `set_subtitle_position` | `error command_failed` "Not available on Roku" |
| `set_hdr_enabled` | Ignored, as on the other TVs |

`volume_mute_only` in the Roku's hello tells phones that understand it to
show a mute button instead of a slider, and to leave the phone's volume
buttons alone. `no_playback_speed` tells them to hide the speed menu. Phones
that do not know them show both, and the Roku answers as above.

## 7. Launch

### 7.1 Who may launch

A controller may launch only after the Roku has sent it `handoff_ready` on
this connection. That covers the own-profile path (section 8.1) and reuse
through a `resumeToken` (section 8.2), so every launch has an identity the
Roku has accepted.

### 7.2 What a launch does

- `playback` maps onto the player's existing intent: `contentId`; `fileId`
  with `pinsVersion`; `audioTrackIndex` and `subtitleTrackIndex` as server
  ordinals (`nav.player.withTracks`), applied to the version the player
  chooses when `fileId` is absent; `startFromBeginning` or
  `resumePosition`. `libraryId` is ignored.
- Phones send a Roku the server's ordinals: `audioTrackIndex` the position
  in the version's `audio_tracks`, `subtitleTrackIndex` the combined index
  `/api/v2/playback/start` takes (external subtitles first), negative for
  none. The other TVs get the phones' own values unchanged: an FFmpeg stream
  index from iOS and the catalog position from Android, which those TVs'
  players convert; the Roku cannot tell them apart, so the phones convert
  for it.
- From any screen of the signed-in shell, the player opens on top; Back
  returns to that screen. On the profile picker, sign-in, or setup, the
  answer is `error player_not_ready`.
- A launch while one is starting gets `error launch_pending`. A title that
  fails to start sends `error launch_failed` with the player's message.
- Replacing what plays: if a title plays under another profile, the
  handoff that precedes the launch answers `handoff_cancel
  replace_confirmation_required` with `nowPlaying`, and the phone resends
  with `replaceConfirmed` and `replacingContentId`. The current player keeps
  playing until the server approves the handoff (at once for the own
  profile), then closes, final progress included, before the identity
  changes.
- A deep link that arrives while a handoff title plays closes that player
  first, as Back would, then runs under the Roku's own identity.

## 8. Profile handoff

### 8.1 Own profile: no handoff

When the offer's server matches the Roku's (section 6.2) and its `profileId`
is the profile open on the Roku, the Roku answers `handoff_ready` with
`reused: true`, a `sessionExpiresAt` 24 hours on, and a new `resumeToken`, and
makes no server request. Playback uses the Roku's own identity. Android TV
does the same.

### 8.2 Another profile: server handoff

For any other profile on the Roku's server:

1. `GET /api/v2/auth/device/capability` must show `state` `available`,
   `allowed` not false, `remote_playback_handoff` true, and 2 in
   `protocol_versions`. Otherwise `handoff_cancel handoff_failed`.
2. `POST /api/v2/auth/device/start` with `device_name` (the Roku's name),
   `device_platform: "roku"`, `client_purpose: "remote_playback"`, and
   `temporary: true`. The answer must echo the purpose and `temporary`.
3. The Roku sends `handoff_challenge` with `requestId`, `userCode`,
   `matchCode`, and `expiresAt`. The phone looks the code up, approves it with
   `approve-handoff` under its own profile, and the Roku shows nothing.
4. The Roku polls `POST /api/v2/auth/device/poll` at the answer's
   `poll_after` (else `interval`) until `expires_in` runs out. `denied`,
   `expired`, `canceled`, and `consumed` end it with `handoff_cancel
   handoff_failed`.
5. On `approved`, the Roku checks `profile_id` equals the offer's
   `profileId`, installs the borrowed identity (section 8.3), and sends
   `handoff_ready` with `serverId`, `profileId`, `sessionExpiresAt` (the
   answer's `session_expires_at`), `reused: false`, and a new `resumeToken`.
6. If the phone closes or sends `handoff_cancel` first, the Roku calls
   `POST /api/v2/auth/device/cancel` and drops the request.

A later offer for the same profile from the same `deviceId`, with the issued
`resumeToken` or on the same connection, reuses the identity: `handoff_ready`
with `reused: true` and no server request.

These requests go through the app's one API path (`ApiTask` and the auth
coordinator), not through the receiver's task. They use the Roku's configured
origin only, already confirmed by spec section 7.1. The offer's `serverURL`
and `serverEndpoints` are never contacted in this phase.

### 8.3 The borrowed identity

- The auth coordinator holds it as a second identity beside the Roku's own:
  access and refresh tokens, `profile_id`, `profile_token`, and the session's
  end. It is memory only: nothing reaches the registry, and the remembered
  profile does not change.
- The handoff's player and its jobs use it: playback start, plan execution
  and media headers, progress, stop, replans, markers, trickplay, preferences,
  and Up Next's catalog reads. Every one of these is on the server's
  `remote_playback` route list. Screens below the player keep the Roku's own
  identity.
- Requests send `X-Profile-Id` and, for a PIN profile, `X-Profile-Token` from
  the poll answer.
- It refreshes through the coordinator's single-flight refresh, in its own
  lane. A refused refresh, or reaching `session_expires_at`, stops playback,
  sends `error temporary_session_expired`, and drops the identity.
- It ends when its player closes for any reason: after the final progress and
  stop, the Roku calls `POST /api/v2/auth/logout` once, without retrying,
  and forgets the tokens. It also ends 60 seconds after `handoff_ready` if no
  launch came (`error launch_timeout`), and on sign-out, server change, and
  app exit. On app exit the server's 24-hour cap ends the session; the
  account owner can also revoke it from the session list.
- One borrowed identity exists at a time. A handoff for a different profile
  ends the current one first, after replace confirmation.
- Nothing logs the device code, user code, match code, tokens, or the
  resume token.

### 8.4 Another server

An offer whose server matches neither by `serverId` nor `serverIdentity`
gets `handoff_cancel handoff_failed` with the message "This Roku plays from
<server name>." Cross-server handoff needs the API layer to run a second
origin, with its own origin check (spec section 7.1) and "Connect without
encryption?" rule. It is planned after the first handoff release (plan
phase C9 in [`silocontrol-plan.md`](silocontrol-plan.md)).

## 9. Transport security

### 9.1 Threat model

The other Silo TVs use TLS-PSK with a fixed key, `"silo-cast-v1"`, that is
in public source. Their code calls it "opportunistic confidentiality only,
NOT an authentication boundary". Against someone on the same network it
gives no more protection than plain TCP. Any device on the network can
control their playback, and an attacker in the path of a handoff can swap in
its own device-login request, which the phone then approves.

The Roku's levels:

| Level | Protection | Status |
| --- | --- | --- |
| `plain` | None on the wire. The same practical exposure as the other TVs today. The channel never carries tokens, signed URLs, or the device code | Ships first; stays the default |
| `sealed` | Only a phone that holds the pairing key can connect; frames are encrypted and authenticated, so neither control nor handoff can be read, forged, or replayed | Follows, as the Require Pairing option |

`plain` stays the default because a key that has to be scanned once per
phone is the one step discovery cannot remove. The plan records the
handoff exposure at `plain` as an accepted risk, matching the other TVs.

### 9.2 `sealed`

**Pairing key.** 16 bytes, made when Require Pairing is turned on and on
Reset Pairing Code, kept in the app's registry section (`pairing_key`,
written by ApiTask like every registry value, through the session's
`pairing` operation), kept across sign-outs, and shown only on the Connect a
Phone screen and in its QR code.

**Session keys.** Each side opens with one plain frame:

```json
{"type": "sealed_hello", "v": 1, "keyId": "<first 8 hex of SHA-256(key)>", "nonce": "<16 bytes, base64url>"}
```

The phone sends first; the Roku answers. A wrong `keyId` gets `close
unauthorized` in plain text, and a phone treats a Roku answer with another
`keyId` as a refusal. Then:

```text
prk      = HMAC-SHA256(salt = phoneNonce || tvNonce, key)
encKey   = HMAC-SHA256(prk, "silo-cast-sealed-1 enc" || 0x01)[0..15]
macKey   = HMAC-SHA256(prk, "silo-cast-sealed-1 mac" || 0x01)
ivKey    = HMAC-SHA256(prk, "silo-cast-sealed-1 iv"  || 0x01)[0..15]
```

(HKDF-SHA256 with one output block each.)

**Frames.** Every later frame body is:

```text
seq (8 bytes, big-endian, from 0 per direction) || iv (16) || ciphertext || tag (32)
ciphertext = AES-128-CBC(encKey, iv, JSON, PKCS#7 padding)
tag        = HMAC-SHA256(macKey, "silo-cast-sealed-1" || direction || seq || iv || ciphertext)
```

`direction` is the byte `0x01` from the phone and `0x02` from the Roku. The
receiver checks the tag before decrypting and requires `seq` to be exactly
one more than the last. Any failure closes the connection without an answer.
A sender may choose any unpredictable IV. The Roku uses
AES-128-ECB(ivKey, direction || seq, padded with zeros to 16 bytes), so it
needs no random numbers per frame; it computes it as one block of CBC with
a zero IV, which is the same value, because the headless test engine's ECB
needs an IV. `tests/control/sealed.spec.bs` holds vectors from Node's
`crypto`, which `scripts/silocontrol-phone.mjs --key` also implements.

### 9.3 What depends on randomness

Only the pairing key needs secret randomness. The Roku makes it as SHA-256 of
four `GetRandomUUID()` values, the installation ID, and the uptime in
milliseconds, and keeps the first 16 bytes. Nonces only need to be unique,
and the Roku makes its nonce from a registry counter plus a UUID. Roku does
not say whether `GetRandomUUID()` comes from a secure generator. If it does not,
the pairing key comes from the phone instead: the phone's first plain frame
proposes it, and the Roku shows a six-digit confirmation the viewer compares
on both screens. That alternative is not designed further unless Roku says
no.

### 9.4 Require Pairing

Once both phone apps speak `sealed`, the Connect a Phone screen offers
Require Pairing, off by default. Turned on, it draws a pairing key, TXT `sec`
becomes `sealed` with the key's `kid`, and a phone connects only after
scanning the QR code once; a `plain` connection gets `close unauthorized`.
Turned off, it forgets the key and returns to `plain`. A phone that holds a
key still connects to a Roku that now advertises `plain`, so a forged
advertisement can downgrade it; that is the same exposure as `plain`
itself, accepted while `plain` is the default.

### 9.5 Alternatives not taken

- **TLS 1.2 PSK in BrightScript**, to match the other TVs' transport
  unchanged: a TLS state machine and GCM written in BrightScript, slow on
  512 MB devices, for a key that is public. The phones need changes to dial
  a Roku anyway.
- **AES-GCM:** only from Roku OS 15.2, and without tag access.
- **A relay through the Silo server:** the server has no device-to-device
  command route, and Roku has no WebSocket client.

## 10. Lifecycle

- `ControlTask` starts once the app is signed in and stops on sign-out and
  server change, closing each controller with `close tv_disconnected`.
- A new address (checked every five seconds) sends the old records with TTL
  0, announces the new ones, and updates the Connect a Phone screen. The
  listener is bound to every address, so it stays; controllers on the old
  address end when their heartbeat does.
- Roku's critical memory level closes every controller with `close
  tv_disconnected` and stops the listener until memory recovers
  (`controlMemoryLevel`).
- Instant Resume: not handled yet. A suspended app's sockets stop; phones
  see the connection end and reconnect after the app resumes only if the
  receiver is still listening. Hardware test HC-4 decides what is needed.
- Every stop sends the DNS-SD records with TTL 0 first, so phones drop the
  Roku from their lists. Leaving the app closes everything; when Roku ends
  the app too fast for that, the records expire within 120 seconds. Phones
  see the connection end and say "Open Silo on your Roku".

## 11. Components

| Piece | Where | Does |
| --- | --- | --- |
| `ControlTask` | `components/tasks/ControlTask.xml/.bs` | Listener, sockets, framing, sealing, and the mDNS socket; runs the connection rules and exchanges events and commands with `AppScene` through fields |
| Connections | `source/control/receiver.bs` | Hello, authorization, heartbeat, hello watchdog, command budget, eviction, and closing (a pure reducer) |
| DNS-SD | `source/control/mdns.bs` | Query parsing with name compression, record building, announce and goodbye (pure functions) |
| Protocol | `source/control/protocol.bs` | Framing, message encode, decode, and validation, server matching |
| Policy | `source/control/policy.bs` | Peer check, eviction order, command budget, identity reuse, replace consent, launch intent (pure functions) |
| Sealing | `source/control/sealed.bs` | Key derivation and frame seal and open |
| Hub | `components/AppSceneControl.bs` | Starts and stops the receiver with the session; state ticks; commands, launch, and section 8's handoff flow; Connect a Phone's status, pairing, and the connected notice |
| State | `source/control/state.bs` | Builds `state` from the player's snapshot |
| Borrowed identity | `source/auth/handoff.bs` (part of the coordinator) | The device-login operations and the second identity lane (section 8.3); `AppScene.apiSend` fences a borrowed player's requests by owner, and the playback worker keeps that identity's jobs live |
| Player bridge | `components/player/PlayerRemote.bs` | `remoteState()` and `remoteCommand()` interface functions; commands take the Options and key paths |
| Screen | `components/screens/connect/` | Connect a Phone and its QR code |
| QR encoder | `source/util/qr.bs` | Byte-mode encoder and PNG writer |
| `QrTask` | `components/tasks/QrTask.xml/.bs` | Writes Connect a Phone's QR code to `tmp:/` and deletes the previous one |
| Development controller | `scripts/silocontrol-phone.mjs` | A phone's part, plain or `sealed`, for device tests |

The `silocontrol` build switch (bs_const) builds the receiver into the app;
`handoff` adds section 8.2. Both are on in `manifest`, so every build has
them (decision D-7).

The player keeps sole ownership of the `Video` node (spec section 6.3); the
receiver only asks it to act.

## 12. Roku differences from the other TVs

| Apple TV and Android TV | Roku | Reason |
| --- | --- | --- |
| Advertised as `_silocast._tcp` by the OS | Advertised as `_silocast-roku._tcp` by the app's own responder, with TXT `sec` | Roku has no DNS-SD advertising API; a separate type keeps TLS-only phones from listing a Roku they cannot reach (section 5.1) |
| TLS-PSK with a fixed public key | `plain`, then `sealed` with a per-Roku pairing key | No TLS on Roku sockets (section 9) |
| Eight controllers | Four | Memory on 512 MB devices |
| Frames up to 1 MiB | Up to 64 KiB | Memory; no phone frame comes near it |
| Volume as a 0–1 level | Mute only, with `volume_mute_only` | Roku apps cannot set a level |
| Speed, aspect, subtitle timing, and position from the phone | Not available | Not in the Roku player (spec section 5.9) |
| `posterUrl` and `overview` in `state` | Not sent | Signed URLs stay off the LAN |
| Cross-server handoff | Own server only, for now | Section 8.4 |
| tvOS: every launch needs a handoff | The open profile plays without one, as Android TV | Fewer device logins; criterion 2.2 |

## 13. Open decisions

| Decision | Leaning | Needed evidence |
| --- | --- | --- |
| Handoff in public builds before Roku confirms it | Yes: the project owner accepted the risk on 2026-10-25 (D-7) | Roku's answer; revert the switch if Roku reads it under 2.2 |
| Require Pairing | Offered once both phone apps ship `sealed`; off by default | Phone release dates |
| Discovery on other hardware | Works as on the TCL Roku TV | Spike C0-7: a Roku player, a 512 MB device, iPhone and Android browsing, a network change |
| A fallback for networks that block multicast | Address and QR code on Connect a Phone; a server-kept TV list only if beta households need it | Beta reports |
| Port | 52817 with fallbacks | Spike C0-1 |
| QR drawing | PNG in `tmp:/` | Spike C0-4 |
| Track index meaning in `launch` | Server ordinals, which the phones convert to for a Roku (section 7.2) | Phone-app changes in C7; iOS sends FFmpeg stream indexes and Android catalog positions to the other TVs |
| Peer address check | Private and link-local IPv4 only | Done: Roku reports the peer (section 5.1) |
| Pairing key source | The Roku, per section 9.3 | Roku's answer on randomness |
| Cross-server handoff | After the first handoff release | Demand; second-origin API work |
