# Companion sign-in on Roku

Status: in public and development builds, behind the `companion` build
switch (on in `manifest` and `bsconfig.dev.json`). The phone apps' side ships
in their own repositories.

A new Roku on the server or sign-in screen can be signed in from a phone that
already uses Silo, as an Apple TV or Android TV can: the phone sees the Roku,
offers to sign it in, the Roku shows a code, the phone's user approves it, and
the Roku goes on to the profile picker. Password sign-in on the Roku stays
available beside it.

## 1. Policy

Roku certification criterion 2.2 requires on-device authentication and bars
off-device sign-in and activation, and Plex removed its code sign-in from
Plex for Roku over it (see [`silocontrol.md`](silocontrol.md) section 2.3).
This feature is device-code sign-in approved on a phone, which 2.2 names.
The project owner decided to ship it in public builds, as comparable apps
offer phone sign-in; password sign-in on the Roku stays beside it. The
`companion` switch is on in every build and stays only as a way to turn
the feature off. Spec section 7.2 records the same decision.

## 2. Why Roku needs its own service type

The Apple and Android TVs advertise `_silopair._tcp` and speak the pairing
protocol over TLS with a pre-shared key compiled into the apps. Roku has no
TLS for sockets an app listens on, so it cannot accept those connections. The
Roku advertises `_silopair-roku._tcp` instead and speaks the same messages
over plain TCP. Phones browse both types and connect to the Roku one without
TLS.

This loses nothing. The PSK is public (it ships in every app), so TLS gave
only opportunistic confidentiality, and no message carries a token: the
server delivers tokens to the TV over HTTPS. What keeps a LAN impostor from
having a phone approve its own device request is the code the TV shows,
which the person compares with the code the phone reads from the server, and
the Roku's consent prompt before it contacts any pushed server.

## 3. Discovery

The Roku runs the receiver only while one of these screens is current:

| Screen | `st` | Condition |
|---|---|---|
| Server address (first run, or Change server) | `setup` | always |
| Sign in with a password | `login` | the server's deployment identity is known (`GET /api/v2/system/identity`); otherwise no advertisement |

It advertises through the app's own mDNS responder (as SiloControl does,
[`silocontrol.md`](silocontrol.md) section 5.1):

- PTR `_silopair-roku._tcp.local` → `Silo-<id8>._silopair-roku._tcp.local`;
  SRV to `silo-<id8>.local` and the listening port; A with the Roku's address.
- TXT, the same keys as `_silopair._tcp`:
  - `v` `1`
  - `name` the Roku's name (`roDeviceInfo.GetFriendlyName()`)
  - `id` the Roku's app device ID (the same ID SiloControl's `id` carries)
  - `sid` a fresh UUID each time the receiver starts; phones key "Not Now" on it
  - `st` `setup` or `login`
  - `srv` for `login`, the server's deployment identity
- The listener takes the first free port of 52827–52836, else any port.
- Leaving the screen stops the receiver and sends goodbye records, so phones
  withdraw the offer.

SiloControl's receiver (`_silocast-roku._tcp`) runs only while signed in, so
the two never advertise at once.

## 4. Wire protocol

Frames are a 4-byte big-endian length and a UTF-8 JSON object, as on the
other TVs, at most 65,536 bytes. Messages are the pairing protocol's, flat
objects with `type` and `v: 1`:

| Direction | `type` | Fields |
|---|---|---|
| TV → phone, first | `hello` | `tvName`, `tvDeviceId`, `state` (`setup`/`login`), `supportedVersions` `[1]` |
| phone → TV | `pushServer` | `serverURL`, `serverName`?, `serverIdentity`?, `endpoints`? (`[{url, kind, ...}]`) |
| TV → phone | `deviceStarted` | `serverURL` (as pushed), `userCode`, `matchCode` |
| TV → phone | `serverResult` | `serverURL` (as pushed), `status` `signedIn`/`failed`, `error`? |
| phone → TV | `done` | |
| either | `cancel` | `reason` |

- The Roku sends `hello` on accepting. It takes one phone at a time and
  closes any other connection at once.
- A phone that sends nothing for 180 seconds, with no attempt in flight, gets
  `cancel` `idle_timeout` and is closed.
- `serverResult.error` is one of `auth_failed`, `denied`, `expired`,
  `unreachable`, `identity_mismatch`, `update_required`.
- A Roku keeps one server. Phones push one server to it (their chooser is
  single-select for a Roku). A push after a sign-in in the same session gets
  `serverResult failed auth_failed`. A push while one is in flight replaces
  it, as on the other TVs.
- Unknown types are ignored; a frame that is not JSON, or larger than the
  limit, closes the connection.

## 5. Flow on the Roku

1. **Consent.** The first push of a session shows, over the current screen:
   "Sign in to {server}?", "A phone on your network wants to sign this Roku
   in to {server} at {address}." For an `http` address it adds "This
   connection isn't encrypted." Buttons Allow and Don't Allow. Nothing is
   contacted before Allow. Don't Allow sends `cancel` `consent_denied` and
   closes. Consent covers the rest of the session.
2. **Check the server.** The pushed address goes through the same checks as a
   typed one (spec section 7.1): `GET /api/v2/system/info` with `api_major`
   2 and `request_origin` equal to the address. Failing those is
   `update_required` (an old server) or `unreachable` (no answer). When the
   push names a `serverIdentity`, `GET /api/v2/system/identity` must answer
   with it, else `identity_mismatch`.
   - **Unreachable with alternates.** If the pushed address gives no answer
     and the push listed `endpoints`, the Roku checks them in order for the
     same identity and offers the first that matches: "Can't reach
     {server}", "{server} also answers at {alternate}.", with "Use
     {alternate}", Try again, and Cancel. Nothing switches without that
     choice. With no alternate the same screen offers Try again and Cancel;
     Cancel sends the phone `serverResult failed unreachable`, then
     `cancel` `receiver_cancelled`.
   - **Sign-in screen (`login`).** The push must carry `serverIdentity`
     (else `update_required`: the phone predates sign-in TVs) equal to the
     Roku's server's identity (else `identity_mismatch`), and runs at the
     Roku's saved address.
3. **Start.** `POST /api/v2/auth/device/start` with `device_name` and
   `device_platform: "roku"`. The Roku sends `deviceStarted` and shows the
   code: "Approve on your phone", the `user_code` large, and the match words
   (`match_code`) under it, "Check that your phone shows the same code."
4. **Poll.** `POST /api/v2/auth/device/poll` at `poll_after` (else
   `interval`) until `expires_in` runs out. `denied` fails `denied`;
   `expired`, `consumed`, `canceled`, or the deadline fail `expired`.
5. **Signed in.** On `approved`, the tokens go into the registry exactly as
   after a password sign-in, with the server saved as the Roku's server, the
   phone gets `serverResult signedIn`, and after the phone's `done`, its
   close, or 3 seconds, the Roku goes on to the profile picker.
6. **Abandoned.** A request the Roku opened and did not collect (the phone
   cancelled, pushed again, or left; the person pressed Cancel or Back) is
   withdrawn with `POST /api/v2/auth/device/cancel`, best effort: a server
   without that route answers 404, which changes nothing.

A failure stays on screen with its reason and Try again (back to waiting for
a phone) until the person acts; the phone gets `serverResult failed` with
the code. On a new step the highlight starts on its first button. While
waiting, the server and sign-in screens' card reads "Use your phone": "Open
Silo on a phone on this network to sign this Roku in. Or type with the
remote, or the Roku mobile app's keyboard."

Tokens, device codes, and the poll answer stay inside the auth coordinator
(`ApiTask`); the receiver and screens see only the user code, match words,
and outcomes. Nothing logs codes or tokens.

## 6. Components

| Piece | Where |
|---|---|
| Pairing frames and validation | `source/control/pairing.bs` |
| Socket, framing, mDNS | `components/tasks/ControlTask.bs`, started with `service: "pairing"` |
| mDNS records for either service | `source/control/mdns.bs` (`config.service`) |
| Device sign-in operations | `source/auth/companion.bs` (auth coordinator) |
| Flow | `components/AppSceneCompanion.bs` |
| Companion screen (route `companion`) | `components/screens/companion/CompanionScreen.*` |
| A phone's part, for development | `npm run silocontrol -- --pairing` (README) |

## 7. Verified on hardware

On a Roku Ultra (OS 16.0.4) with the Node script as the phone, 2026-10-24:
discovery (`st`, `srv`, `sid` in the TXT record), hello, consent with Allow
and Don't Allow, the server and identity checks, an unreachable address
with its alternate offered and chosen, the code and match words on screen
and in `deviceStarted`, polling, withdrawal on the phone's cancel, a push
without an identity on the sign-in screen (`update_required`), and a second
phone closed at once. With the Silo iOS app on an iPhone: an approval from
the sign-in screen, after which the Roku went on to the profile picker and
the phone reported the Roku signed in. The Android app is not yet verified
on a device.
