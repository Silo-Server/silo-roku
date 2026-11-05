# Companion sign-in on Roku

Status: in public and development builds, behind the `companion` build
switch (on in `manifest` and `bsconfig.dev.json`). The phone apps' side ships
in their own repositories.

A Roku on the server or sign-in screen can be signed in from a phone that
already uses Silo, as an Apple TV or Android TV can: the phone sees the Roku,
offers to sign it in, the Roku shows a code, the phone's user approves it, and
the Roku goes on to the profile picker. From the server screen one phone can
sign the Roku in to several accounts, on one server or several, each kept as
its own saved account (spec section 7.5). Password sign-in on the Roku stays
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
which the person compares with the code the phone reads from the server, the
session binding that lets one comparison cover a session's later requests
(section 5.1), and the Roku's consent prompt before it contacts any pushed
server.

## 3. Discovery

The Roku runs the receiver only while one of these screens is current:

| Screen | `st` | Condition |
|---|---|---|
| Server address (first run, Change server, or Change Account's Add server) | `setup` | always |
| Sign in | `login` | signed out, and the server's deployment identity is known (`GET /api/v2/system/identity`); otherwise no advertisement |

Sign-in pushed over the picker or Change Account to add an account, with
another account open, advertises nothing and leaves out the "Have Silo on
your phone?" hint. The receiver on the sign-in screen recognises a sign-in by
the session going from signed out to signed in, which cannot happen with an
account open. Change Account's Add server advertises `setup` instead, and
the phone may push any server there, the one in use included.

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
  - `acct` `1` for `setup`: the Roku takes any number of `pushServer` in a
    session, the same server again included, and keeps each sign-in as its
    own account, matched by the poll's `tokens.user.id`
  - `lim` for `setup`: the most sign-ins one session keeps, 8 today
    (`storage.sessionSignIns`). Each sign-in becomes the most recently used
    account on the most recently used server, so it survives the registry
    budget (spec section 7.5) while the session's sign-ins fit 12 accounts,
    their servers fit 8, and their entries fit the budget. A Silo sign-in
    stores about 1 KB, so 8 fit; tokens the registry keeps can be up to
    4 KB each, so a session of large sign-ins can be refused sooner
    (section 4).
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
| phone → TV | `pushServer` | `serverURL`, `serverName`?, `serverIdentity`?, `accountName`?, `endpoints`? (`[{url, kind, ...}]`) |
| TV → phone | `deviceStarted` | `serverURL` (as pushed), `userCode`, `matchCode` |
| TV → phone | `serverResult` | `serverURL` (as pushed), `status` `signedIn`/`failed`, `error`? |
| phone → TV | `done` | |
| either | `cancel` | `reason` |

- The Roku sends `hello` on accepting. It takes one phone at a time and
  closes any other connection at once.
- A phone that sends nothing for 180 seconds, with no attempt in flight, gets
  `cancel` `idle_timeout` and is closed.
- `serverResult.error` is one of `auth_failed`, `denied`, `expired`,
  `unreachable`, `identity_mismatch`, `update_required`, `limit_reached`.
- `accountName` is the username the phone will approve with. The Roku only
  shows it ("Signing in sam on Home") and never matches on it: the account
  that signs in is the poll's.
- On the server screen a session takes a push after each sign-in, on any
  server and as often as the phone sends one, up to `lim` sign-ins; the
  next gets `serverResult failed limit_reached` and changes nothing. So
  does a push before that when the registry could not keep one more
  sign-in, taken at the most an entry holds, without an account the
  session signed in losing its session (`storage.roomForSignIn`). Each
  sign-in makes its server the current one and its account the open one;
  the servers and accounts it leaves stay saved with their sessions
  ([`spec.md`](spec.md) section 7.5). Signing in again as an account
  already saved refreshes it, keeping its remembered profile, and adds
  none. The sign-in screen signs in one account, and a push after it gets
  `limit_reached` too. A push while one is in flight replaces it, as on
  the other TVs; a push while the session is ending gets `auth_failed`.
- Unknown types are ignored; a frame that is not JSON, or larger than the
  limit, closes the connection.

## 5. Flow on the Roku

The Companion screen draws each step as tvOS's `TVPairingReceiverView`
does (spec section 5.4): a status chip over the headline where tvOS has
one, and a card on the right for each step.

1. **Consent.** The first push of a session shows, over the current screen,
   the chip "A nearby phone is signing in this Roku" (on the server screen,
   "…is setting up this Roku"), "Allow this sign-in?" ("Allow this
   setup?"), and "A nearby phone or tablet wants to sign this Roku in to
   {server}." For an `http` address it adds "This connection isn't
   encrypted." Buttons Allow and Don't Allow, and under them "Only allow it
   if you started this on your own phone or tablet." The card shows the
   phone, waiting dots, and the server's mark over its name: "After you
   allow it, a code appears here to compare with your phone." Nothing is
   contacted before Allow. Don't Allow sends `cancel` `consent_denied` and
   closes. Consent covers the rest of the session.
2. **Check the server.** The pushed address goes through the same checks as a
   typed one (spec section 7.1): `GET /api/v2/system/info` with `api_major`
   2 and, when the server reports it, `request_origin` equal to the address
   (a server too old to report it is accepted with a warning, decision D-7
   in [`implementation-assumptions.md`](implementation-assumptions.md)).
   Failing those is `update_required` (an old server) or `unreachable` (no
   answer). When the push names a `serverIdentity`,
   `GET /api/v2/system/identity` must answer with it, else
   `identity_mismatch`. Then `GET /api/v2/auth/device/capability` says
   whether the server takes session binding (`session_binding`); a failed
   read, a missing key, or a plain-HTTP server counts as no (section 5.1).
   - **Unreachable with alternates.** If the pushed address gives no answer
     and the push listed `endpoints`, the Roku checks them in order for the
     same identity and offers the first that matches: "Can't reach
     {server}", "{server} also answers at {alternate}.", with "Use
     {alternate}", Try again, and Cancel; the card says "No answer". While
     it checks, the chip says "Checking the address" over "Connecting to
     {server}". Nothing switches without that
     choice. With no alternate the same screen offers Try again and Cancel;
     Cancel sends the phone `serverResult failed unreachable`, then
     `cancel` `receiver_cancelled`.
   - **Sign-in screen (`login`).** The push must carry `serverIdentity`
     (else `update_required`: the phone predates sign-in TVs) equal to the
     Roku's server's identity (else `identity_mismatch`). Nothing else is
     checked: that server is already confirmed.
3. **Start.** On the server screen, `POST /api/v2/auth/device/start` with
   `device_name`, `device_platform: "roku"`, and, on a server that takes
   it, the session's `binding` (section 5.1). On the sign-in screen
   there is no second request: the phone confirms the code that screen
   shows, as on tvOS and Android TV. The sign-in screen keeps polling it
   under the Companion screen and reports it to the receiver on each
   change; the receiver waits up to 15 seconds for one, and a code that
   ended (paused, declined, or approved but unusable) is replaced once
   when a phone asks. The Roku sends `deviceStarted` and shows the
   chip "Waiting for your phone" over "Confirm on your phone", "Check that
   your phone or tablet shows this code, then approve." ("Signing in
   {account} on {server}. Check …" when the push named an account), for
   every push of the session, not only the first; the card holds
   "Sign-in code", the `user_code` grouped 4+4 in 72 px, "Older phones show
   {match words} instead." when the server sent `match_code`, and the
   server's mark and name under a divider.
4. **Poll.** `POST /api/v2/auth/device/poll` at `poll_after` (else
   `interval`) until `expires_in` runs out, with `binding_secret` when the
   start carried a binding. A `403 device_binding_mismatch` fails
   `auth_failed` and withdraws the request. `denied` fails `denied`;
   `expired`, `consumed`, `canceled`, or the deadline fail `expired`. On
   the sign-in screen that screen polls, so its code signs the Roku in
   whoever approves it first, the phone or a browser; a new code on that
   screen (an expired one replaced) fails the phone's attempt `expired`.
5. **Signed in.** On `approved`, the tokens go into the registry exactly as
   after a password sign-in (`installAccount`: the saved account with the
   poll's `tokens.user.id` on that server takes them, otherwise a new one),
   with the server saved as the Roku's server, and the phone gets
   `serverResult signedIn`. The screen says "Signed in" ("{account} is
   signed in on {server}. Finishing up…", with the account that signed in)
   and waits for the phone's next push (step 2 again, without asking
   consent), its `done`, its close, or 10 seconds without a push. Back ends
   the session there too. Then it says "You're all set" ("Signed in to
   {server}. Taking you to your profiles…", or "{n} accounts are signed
   in. Next, choose which one to open." after several; tvOS's completed
   state) with Continue, and at Continue or after 2 seconds:
   - one account signed in this session (the same one twice counts once):
     its profile picker, as before;
   - several: the first one to sign in becomes the open account
     (`useAccount` with its picker waiting for the viewer, which closes
     its profile if it also signed in last and opened one), so it is
     marked Current and Back from Change Account opens its picker; then
     Change Account shows over that picker, on its server with focus on
     its card.
   A later push that fails shows its failure until the next push or the
   end of the session, which goes on as above with the accounts that did
   sign in.
6. **Abandoned.** A request the Roku opened for the phone and did not
   collect (the phone cancelled, pushed again, or left; the person pressed
   Cancel or Back) is withdrawn with `POST /api/v2/auth/device/cancel`,
   best effort: a server without that route answers 404, which changes
   nothing. A sign-out or a server change ends the attempt the same way,
   and an approval collected after it is dropped. On the sign-in screen
   the code belongs to that screen and stays on it, still valid.

A failure stays on screen ("Sign-in didn't finish", or "Setup didn't
finish", with its reason in tvOS's words and a "Not finished" card) with
Try again (back to waiting for a phone, or after a sign-in, the end of the
session) until the person acts or the phone pushes again; the phone gets
`serverResult failed` with the code. On a new step the highlight
starts on its first button. While waiting, the server screen opens on "Set
up with your phone" with the chip "Looking for a phone or tablet…" and the
three setup steps, and the sign-in screen says "Have Silo on your phone?
Open it on the same Wi‑Fi to sign in this TV." under its code (spec
section 5.4).

Tokens, device codes, the binding secret, and the poll answer stay inside
the auth coordinator (`ApiTask`); the receiver and screens see only the
user code, match words, outcomes, and the local ID and username of each
account signed in. Nothing logs codes, tokens, or the secret.

### 5.1 Session binding

One code comparison covers every request a phone's session starts
(companion multi-account contract, part B). When a phone connects, the
receiver names its session; the coordinator's first server check in that
session makes a 32-byte secret `s`, which every later attempt of the session
uses, on every server.

- On an `https` server whose `auth/device/capability` has
  `session_binding: true`, `device/start` sends `binding` = base64url without
  padding of SHA-256(`s`), and every poll sends `binding_secret` = base64url
  without padding of `s` (43 characters each). Other servers get neither: a
  capability without `session_binding` counts as no, and a plain-HTTP server
  never gets them, even when it takes binding, because `s` would reach the
  on-path attacker that binding defends against. On those servers the phone
  compares each request's code.
- The phone reads `binding` from each request's lookup and approves a later
  request without a new comparison only when it equals the one it trusted
  after the first comparison. An attacker can copy a binding but cannot
  poll without `s`.
- The sign-in screen's code is that screen's, started before any phone
  connected and shown to browsers too, so it carries no binding. A phone on
  that screen signs in one account and compares its code, as before.
- Roku exposes no documented cryptographic random generator to channels:
  `roEVPCipher`, `roEVPDigest`, and `roHMAC` take keys but make none, and
  `Rnd()` is a seeded pseudo-random generator. `s` is SHA-256 of eight
  `roDeviceInfo.GetRandomUUID()` values, the uptime, the wall clock in
  milliseconds, and the installation ID (`api.auth.binding.newSecret`), as
  the SiloControl pairing key is made ([`silocontrol.md`](silocontrol.md)
  section 9.3). It is as unpredictable as Roku's UUID generator, which Roku
  does not document; the clocks and the installation ID add almost nothing
  secret. Encrypting the material with `roEVPCipher` would add nothing,
  since its key would come from the same UUIDs. Whether `GetRandomUUID()` is
  cryptographically secure is unconfirmed.

## 6. Components

| Piece | Where |
|---|---|
| Pairing frames and validation | `source/control/pairing.bs` |
| Socket, framing, mDNS | `components/tasks/ControlTask.bs`, started with `service: "pairing"` |
| mDNS records for either service | `source/control/mdns.bs` (`config.service`) |
| Device sign-in operations (server screen) | `source/auth/companion.bs` (auth coordinator) |
| Session binding secret | `source/auth/binding.bs` |
| Sign-ins a session keeps (`lim`) | `source/storage/registry.bs` (`storage.sessionSignIns`) |
| The sign-in screen's code | `components/screens/setup/SignInScreen.bs` (`reportCode`) |
| Flow | `components/AppSceneCompanion.bs` |
| Companion screen (route `companion`) | `components/screens/companion/CompanionScreen.*` |
| A phone's part, for development | `npm run silocontrol -- --pairing` ([`development.md`](development.md)) |

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

Several accounts in one session, `acct` and `lim`, `accountName`,
`limit_reached`, the end of a session on Change Account, session binding,
and the sign-in screen without the nearby hint while an account is open are
covered by the headless tests (`tests/control/companionScene.spec.bs`,
`tests/control/pairing.spec.bs`, `tests/auth/companion.spec.bs`,
`tests/auth/savedServers.spec.bs`, `tests/views/signInNearbyHint.spec.bs`)
and not yet verified on hardware.
