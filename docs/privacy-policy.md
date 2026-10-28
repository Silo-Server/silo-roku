# Silo for Roku privacy policy

> **DRAFT. Not published and not reviewed.** The project owner must review
> this text, fill in the bracketed placeholders, and resolve the findings in
> the last section before it is published or given to Roku. It is not legal
> advice. Written 2026-10-22 against integration commit `f1d9d9b`; the
> behaviour it describes was read from the code (`source/`, `components/`)
> and must be checked again before each release.

**Effective date:** [to be set on publication]

**Publisher:** [the project owner's legal name and contact address]

## Summary

Silo for Roku is an app for watching your own movies and TV from a Silo
server. Silo is self-hosted: you, or someone you trust, run the server, and
you type its address into the app.

- The app sends your sign-in details, what you browse and search for, and
  what you watch **only to the Silo server you entered**, and to the media and
  image hosts that server tells it to use.
- The app sends nothing to the Silo project, to [the publisher], or to any
  other company. It contains no analytics, crash reporting, advertising, or
  tracking software.
- On the Roku device the app keeps the addresses of the servers you saved, a
  random installation ID, and the sign-in tokens each server issued. It never stores your
  password or PIN. Signing out removes the tokens at once, even when the
  server cannot be reached.

## Who handles your data

- **Your Silo server's operator** decides what the server records and keeps:
  your account, profiles, watch history and resume points, the list of
  signed-in devices, and server logs. That may be you, a member of your
  household, or someone else who runs a server for you. Ask them how they
  handle data. This policy covers only what the Roku app does.
- **Roku** runs the device and its operating system. Roku's own collection is
  covered by Roku's privacy policy, not this one (see "Roku" below).
- **The publisher** of this app receives no data from it.

## What the app stores on your Roku

The app keeps its sign-ins in Roku's registry, readable only by apps signed
with this app's developer key: one area for the server in use and one for
the other servers you saved. They hold:

| Item | Why |
| --- | --- |
| The Silo server address you entered, and the server's name once the app has read it | To connect to it at each launch, and to name it in the server list |
| Up to seven other Silo servers you saved, each with the same items as the server in use (its address and name, account identifier, tokens, remembered profile, and profile tokens) and when you last used it | To switch back to one without signing in again. Its tokens are sent only to that server: once it is the server in use again, or, when you remove it, to end its session there if the app reached that server since it was opened |
| An installation ID: a random identifier the app makes once on this device | Your server lists this device as one of your signed-in devices with it. It is not the Roku serial number, the Roku advertising ID, or your Roku account |
| Your Silo account's identifier (not your username) | To reopen the right profile after you sign in again |
| The access and refresh tokens your server issued at sign-in, and when they expire | To keep you signed in |
| The profile last chosen on this device | To reopen it at launch |
| Up to six profile tokens your server issued after a correct PIN | So a PIN-locked profile does not ask for its PIN every time |

The app does **not** store your password, your PIN, your username, your
search history, your watch history, or your settings. Your server keeps your
watch progress and settings; the app reads them when it needs them.

While it runs, the app also writes short-lived files to the Roku's temporary
storage: server responses while they download (deleted once read),
downloaded subtitle files (at most a few, deleted as playback moves on), and
playback requests in transit. Roku clears this storage when the app exits.
Artwork, catalog details, and your choices on screen stay in memory only.

## What the app sends, and where

### To your Silo server

Everything below goes only to the server address you entered:

- **Setup:** a check of the server's version, sent before any credential.
- **Sign-in:** your username and password as you type them, and the device
  details below. The PIN of a PIN-locked profile is sent to the server to be
  checked and is never kept.
- **With every request:** the app's name ("Silo Roku"), version, build, and
  release channel. Signed-in requests also carry your sign-in token, the
  chosen profile and its PIN token, the installation ID, the device platform
  ("roku"), and the device name, which is the Roku model's name (for example
  "Roku Ultra"), not a name you gave the device.
- **Browsing and searching:** what you open and the words you search for.
  When you start the app from a Roku link to a title, the link's title ID is
  looked up on your server.
- **Playback.** These are the only reports the app makes about viewing, and
  they exist so your server can stream the title and remember where you
  stopped:
  - the start of each title: which title and version, the profile, the start
    position, your audio, subtitle, and quality choices, and a description of
    what this Roku can play (model number and maker, Roku OS version, screen
    resolution, whether the TV supports HDR, and which video and audio
    formats it decodes);
  - your position, and whether you paused, every 10 seconds while a title is
    open, and your final position when you stop;
  - requests to change tracks, quality, or position, and, when playback
    fails, a short description of the failure with any credentials and
    signed addresses removed;
  - three playback events: the first frame shown (with how long it took),
    a failed stream, and a playback error.
- **Signing out:** a request to end the session on the server.

The app never changes your settings on the server.

### To media and image hosts your server names

- Video and subtitles normally come from your server. Your server may
  instead send video from a separate streaming server its operator set up
  (a proxy node). Those requests carry no account credentials, only the
  signed address your server issued.
- Posters, backgrounds, logos, and scrub-preview images load from the
  addresses your server's responses give. These may be your server or a
  storage service it uses. Image requests carry no account credentials.

### To Roku

- The app tells the Roku operating system when it finishes launching and when
  a sign-in or profile screen opens and closes. Roku requires these signals
  to measure launch time; they carry no account or viewing details. Whether
  Roku sends them anywhere is up to Roku.
- If you use voice entry on Roku's keyboard, Roku turns your speech into text
  under Roku's privacy policy. The app receives only the text.
- The app reads and changes Roku's own caption setting when you turn captions
  on or off in the app.

### What the app never does

- It contains no analytics, crash reporting, advertising, or tracking
  software, and sends nothing to the publisher or any third party.
- It does not read the Roku advertising ID, the device serial number, or your
  Roku account details, and it uses no Roku billing.
- It attaches your sign-in token and profile details only to requests
  addressed to the server you entered, never to a proxy node or image host.
  Roku follows a server's redirects on its own, so a server set up to
  redirect those requests to another host would pass them on; Silo servers
  are expected not to.
- It does not upload logs. Diagnostic messages stay in the Roku device's
  local debug console, with tokens, PINs, and signed addresses removed.

## Signing out, changing servers, and removing the app

| Action | What the app clears | What stays |
| --- | --- | --- |
| Sign out | Sign-in tokens, profile PIN tokens, the account identifier, and the remembered profile, even if the server cannot be reached. If a title was playing, the app first waits up to 10 seconds to send its final position with the old sign-in; anything still unsent is discarded, never sent with another sign-in | The server address and the installation ID, so you can sign in again |
| Change server (once the new server answers) | Nothing is cleared: the old server is kept in the app's saved servers with its sign-in, so you can switch back without signing in again | The installation ID, and every saved server with its sign-in |
| Remove a saved server | That server's address, sign-in tokens, profile PIN tokens, account identifier, and remembered profile. Removing the server in use also signs it out, as Sign out does | The installation ID and the other saved servers |
| Switch profile | Nothing is cleared; the new profile becomes the remembered one | Other profiles' PIN tokens for this sign-in |
| The server ends your session (for example, it was revoked) | Sign-in tokens and profile PIN tokens | The server address, the installation ID, the account identifier, and the remembered profile, so signing in to the same account reopens it |
| Remove the app from the Roku | Roku deletes the app's stored data | Nothing on the device. Your server keeps its own records until its operator removes them |

On every sign-out, server change, or profile change the app also closes its
screens, so artwork and details loaded for one account or profile are not
shown to the next.

## Unencrypted connections

If your server's address starts with `http://`, the app asks "Connect without
encryption?" before it sends anything. On such a connection your password,
tokens, and viewing reports cross your network unencrypted. Use an `https://`
address with a publicly trusted certificate where you can. The app never
switches an `https://` address to `http://` by itself.

## Children

Profiles, including child profiles and their restrictions, are set up on your
Silo server. The app does not knowingly collect information from children
beyond what any profile's viewing sends to your own server. When a Roku link
opens a title, the app never picks a child profile on its own.

## Changes and contact

We will post changes to this policy at [the policy URL] and change the
effective date. Questions: [support email], [support URL].

---

## Findings for the project owner (remove before publishing)

Places where the code, the spec, and this policy disagree, or where the
policy depends on something not yet confirmed. Paths are repository-relative.

1. **Registry contents differ from the spec.** Spec section 4 lists "the
   active server, installation ID, last profile, and tokens", and plan
   section 4.3 adds profile tokens. The code also stores the account ID and
   the token's expiry and refresh times (`source/storage/registry.bs`, keys
   `account`, `expires_at`, `refresh_at`; assumption AG-37). The policy
   follows the code; the spec text should be updated.
2. **The installation ID is never reset.** It survives sign-out and server
   changes (`source/auth/coordinator.bs`, `endSession`; generated once in
   `components/tasks/ApiTask.bs`), so every server ever configured on the
   device receives the same `X-Silo-Device-Id`, and two server operators
   could match their records. Spec sections 7.4 and 11 allow this. Decide
   whether a server change should make a new one.
3. **Artwork URLs are not checked.** Spec section 11 says to accept URLs only
   from the configured server and its plans and to reject schemes other than
   HTTP and HTTPS. Posters, backdrops, and logos from catalog responses are
   used as given (`source/catalog/cards.bs`, `source/catalog/detail.bs`);
   only trickplay sheets, avatars, and media pass `api.request.isHttpUrl`.
   No credentials go with them, which the policy relies on, but images can
   load from any host and scheme the server names.
4. **"Progress and route events are the only telemetry" (plan section 9.2)
   is narrower than what is sent.** Start and replan bodies also describe the
   device (model number, maker, Roku OS version, model type, UI and output
   resolution, display HDR support, codec answers; `source/playback/capabilities.bs`,
   `deviceContext`), and failure replans carry a redacted Roku error message
   of up to 512 characters (`components/player/Player.bs`,
   `source/playback/session.bs`). All of it goes only to the configured
   server. The policy lists it; the plan's wording should too.
5. **Cache separation between identities is unverified on hardware.** Spec
   section 11 says images and metadata are dropped on account, profile, or
   server changes. The navigation stack resets and the playback capabilities
   cache is keyed by identity, but Roku's own image cache keeps bitmaps from
   screens already left (hardware run 5, texture row), and plan step M1-4's
   "no previous-account artwork after a server change" has no hardware row.
   The policy's "not shown to the next" claim needs that check.
6. **Credential confinement and downgrades are not fully in the client's
   control.** Roku follows redirects without telling the app, forwards
   `X-Profile-Id` and `X-Profile-Token` (and a login body on a 307) to the
   new origin, and the `Video` node sends all three credential headers to
   absolute cross-origin playlist children (hardware run 1, H1 steps 3–5;
   assumption A-14). A server that redirects `https` to `http` would also be
   followed; H1 step 6 has not run. AGENTS.md says credentials go only to the
   configured origin; today that holds only for servers that never redirect
   authenticated routes and keep playlist children relative (server issue
   S-20, prototype only). The policy therefore promises what the app
   attaches, not where Roku may forward it.
7. **Two platform data flows are not in spec section 11:** Roku's voice
   keyboard, and the launch and dialog beacons to Roku OS. Whether Roku
   uploads beacon timings is unconfirmed: Roku's performance page says only
   that "the Roku OS records key app performance metrics"
   (<https://developer.roku.com/dev/docs/measuring-channel-performance>).
8. **Signed playback URLs and response bodies pass through temporary files**
   (`tmp:/api`, assumption AG-42; `components/tasks/ApiTask.bs`). Login,
   refresh, and PIN bodies stay in memory. Roku documents that `tmp:` is not
   kept after the app exits
   (<https://developer.roku.com/dev/docs/file-system>); the files are local
   only.
9. **Sign-out waits for playback reports.** An identity change waits up to
   10 seconds for the old identity's playback jobs (`source/playback/worker.bs`,
   `deferSession`; spec section 9.5) before tokens are cleared. Spec section
   11 says sign-out clears credentials even when the server is offline; that
   holds, after at most that wait.
10. **No support contact or policy link in the app.** The Roku Distribution
    Agreement, Exhibit A §3.4, says support contacts must be "easily
    discoverable by end users"
    (<https://docs.roku.com/published/developerdistribution/en/us>). Whether
    the store listing satisfies it is unconfirmed. Roku's provider data
    policy requires a privacy policy link before publishing
    (<https://docs.roku.com/published/providerdatapolicy/en/us>).
11. **Registry removal on uninstall** is Roku's documented behaviour ("the
    user uninstalls the application",
    <https://developer.roku.com/dev/docs/roregistry>). The same page says
    apps signed with the same developer ID share one registry, so a beta and
    a public app signed with one key would share stored sign-ins (an
    inference; Roku does not name beta apps there).
12. **Placeholders to fill:** publisher, effective date, policy URL, support
    email and URL, and whether a terms-of-use document exists.
