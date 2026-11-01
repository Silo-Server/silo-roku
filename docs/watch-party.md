# Watch Party for Roku

**Status:** Specified, not built. The transport needs spike W0-1 (section 12.1)
before any other work.

**Last updated:** 2026-10-31

**Companion to:** [`spec.md`](spec.md) (product and platform rules). This
document says how the Roku app takes part in a Silo Watch Party: a room of
viewers on any Silo client who watch one title in step, with one of them as
host.

**References** (read 2026-10-31):

- silo-server `1e4ca21bf`: `internal/watchtogether/`,
  `internal/apiv2/watch_together_*.go`,
  `internal/api/handlers/watch_together*.go`, `docs/realtime-api.md`,
  `docs/architecture/watch-party-synchronization.md`,
  `docs/architecture/watch-together-rooms.md`. The server calls the
  feature Watch Together; every client calls it Watch Party.
- silo-apple `15f4153e`: tvOS is the UI reference (section 5.1 of
  `spec.md`). `iosApp/iosApp/WatchParty/`, `Screens/WatchParty/`,
  `Screens/Player/WatchPartyPlaybackAdapter.swift`.
- silo-android `77e316ff5`: the seek-only correction path and its tests.
  `shared/src/commonMain/kotlin/org/siloserver/silo/watchtogether/`
  (`RoomCatchup.kt`, `RoomPlaybackBinding.kt`, `RoomClock.kt`).

## 1. Decision summary

| Topic | Decision |
| --- | --- |
| Scope | Full tvOS parity: host and join, host-pick and vote rooms, suggestions, the party picker with Who's Seen It, Rejoin, the invite screen, party options, and the in-player room panel (owner, 2026-10-31; decision D-10) |
| Release | On in every build, gated only by the device and the server (section 3). No bs_const switch and no Settings toggle (owner, 2026-10-31; D-10) |
| Transport | The server's existing room socket (`silo.room.v2`) through Roku OS's native `roWebSocket`. No second server API (owner, 2026-10-31; D-10) |
| Platform floor | Roku OS 16.0, the first with `roWebSocket`. Older devices show no Watch Party. The app tests `CreateObject("roWebSocket")`, never the version number |
| Correction | Seek only. Roku's `Video` node has no playback rate, so the Roku corrects drift as Apple TV and rate-incapable Android players do (section 7.5) |
| Playback | Each member plays its own protocol v3 session of the room's file, started paused and attached to the room (section 8) |
| Joining | By the 8-character code on a code keypad, or Rejoin. A Roku cannot open invitation links (section 4.2) |

## 2. Transport

### 2.1 `roWebSocket`

Roku OS 16.0 adds `roWebSocket` and `roWebSocketEvent`
([developer.roku.com/dev/docs/rowebsocket](https://developer.roku.com/dev/docs/rowebsocket),
[/dev/docs/web-sockets](https://developer.roku.com/dev/docs/web-sockets)).
It is a client only, opens `ws://` and `wss://` URLs, verifies TLS peers and
host names, configures its HTTP handshake through `ifHttpAgent`, and reports
open, close, text, and timer events through a message port. The Roku Ultra
4850X in the test set runs 16.0.4 (build 852); the TCL 55R625 runs 15.3.4
and shows no Watch Party until it updates.

Roku's page does not say whether the app can set `Sec-WebSocket-Protocol`,
whether the object answers the server's ping frames, how large a text
message it accepts, or whether it offers compression. Spike W0-1 answers
each; the design below assumes yes to the first two.

### 2.2 What the server requires of the socket

From `internal/api/handlers/watch_together_socket_v2.go:74-166` and
`ws_shared.go`:

- `GET {origin}/api/v2/watch-together/rooms/{room_id}/ws` with no query
  string. HTTPS servers use `wss://`, plain-HTTP servers `ws://`, on the
  configured origin only.
- `Sec-WebSocket-Protocol: silo.room.v2, silo.ticket.{ticket}`, exactly
  those two, in that order. The server answers with `silo.room.v2`; any
  other answer ends the attempt.
- No `Origin` header (native clients may omit it), no bearer header. The
  ticket is the credential: single use, at most 30 s old, spent even when
  the upgrade fails. It comes from `POST .../rooms/{room_id}/ws-ticket`
  with the account headers and `X-Room-Token`.
- Text frames only. Compression is optional; the Roku does not ask for it,
  so no message arrives fragmented.
- The server pings at connect and every 20 s and closes a socket that has
  not answered with a WebSocket pong for 30 s. A JSON `pong` does not count.
  If `roWebSocket` cannot answer ping frames, Watch Party cannot ship on
  Roku without a server change; W0-1 decides this first.
- The server closes every socket after at most 5 minutes, or sooner at the
  access token's or room proof's expiry, without a close frame or message.
  The client treats that as routine (section 6.4).
- Client messages are at most 64 KiB. A server `suggestions_update` carries
  the whole list and can approach 5 MB at the 200-suggestion cap; W0-1
  measures what `roWebSocket` and a 1 GB Roku hold.

### 2.3 Credentials

The ticket request carries the same headers as every authenticated request
(spec section 7.4), and only to the configured origin. Neither the ticket
nor the room proof is logged, stored in the registry, or put in a URL. A
ticket needs an access-token login session; the borrowed identity of a
SiloControl handoff (`silocontrol.md` section 8.3) is refused, so a handoff
player never joins a party.

## 3. Availability

Watch Party shows, in every build, when all of these hold:

- `CreateObject("roWebSocket")` returns an object;
- `GET /api/v2/watch-together/capabilities` reports `state` `available`,
  `allowed` true, `socket_protocol` `silo.room.v2`, and
  `connection_replaced` true;
- `GET /api/v2/playback/capabilities` lists `watch_party_coordinator_v1`
  and `fixed_media_file_v1`;
- the session is an account sign-in, not a handoff.

Optional capabilities change the UI as on tvOS: `staged_selection` (hosting
needs it; without it a host's pick plays at once), `lobby_ready`,
`selection_mode_switch`, `stop_playback`, `vote_host_override`, `picker`,
`member_state` with `max_member_state_ids`, and the playback feature
`watch_party_source_fallback_v1`.

The capabilities are read at sign-in, on a server or profile change, when
the Watch Party page opens without a party, and on Check Again. A failed
read keeps the last answer. The capabilities endpoint supports `ETag`.

## 4. User experience

Every screen follows tvOS at `15f4153e` in layout, wording, focus, and
order, measured on the 1920×1080 canvas, except where section 10 lists a
Roku difference. tvOS's metrics: seat 128, seat gap 36, page inset 88,
hero title 88, body 26, caption 20, eyebrow 17 (uppercased, tracking 2.04),
code 30, ballot poster 220×330, pill buttons 76 tall (29 SemiBold primary,
26 secondary), disabled controls at 45% (`WatchPartyComponents.swift:17-40`).

### 4.1 Entry points

- **Avatar menu**: "Watch Party", or "Return to Watch Party" while in a
  party, after History and before the divider (tvOS `TVTopMenuBar.swift`
  1191-1206; the slot `source/home/shell.bs` reserves). It opens the Watch
  Party page.
- **Movie detail More**: the last item. "Watch Party" when not in a party or
  when managing a host-pick room; "Suggest to Party" otherwise. It carries
  the detail page's chosen version's file.
- **Series detail More**: the same item for the episode the action row names
  (spec section 5.6), shown when there is one.
- **Card Options (`*`)**: none. tvOS's episode-rail context item has no Roku
  equivalent (spec section 5.9: Roku's episode rail has no context menu).

From a title (`WatchPartyEntry.open`):

- not in a party: create a host-pick room, then select the title (the
  "Starting your party" hold, section 4.2);
- managing a host-pick room: select it; staged in the lobby, played for
  everyone at once during playback;
- otherwise: add it as a suggestion. tvOS suggests only in the lobby and
  does nothing during playback; the Roku says "You can suggest titles
  from the party's lobby." instead (section 10).

Joining a different party while in one is refused with "You're already in a
party. Leave it to join a different one."

### 4.2 Watch Party page, not in a party

Left column (760 wide): eyebrow "WATCH PARTY", "Watch something\ntogether"
(88 Bold), "Pick a title, share the code, and everyone's playback stays in
step.", and the status banner. Right column (640 wide):

- HOST: "Start a party" (primary), "Start a party and let everyone vote",
  and the Rejoin row (section 4.3);
- JOIN: "Join with a code" opens the code keypad (section 10); "Check
  again" shows while the server's support is unknown or refused.

Initial focus is Rejoin when there is a recent party, else Start a party.
Back leaves the page and never leaves a party. Banners: the last error in
the warning tone, else "Checking Watch Party support…" or "Watch Party is
not available for this profile on this server." in the neutral tone.

Creating sends `POST /rooms` with a fresh UUID `room_id`, reused if the
outcome was uncertain. While a party starts from a title, the page holds
the title's backdrop with a centred spinner that owns focus ("Starting your
party"), so Back can leave a slow request.

### 4.3 Recent party and Rejoin

The registry keeps one recent party per server, account, and profile: its
room ID, code, and selected title, with the time it was written. Never a
token or proof. It lasts 24 hours, is renewed at most hourly while a party
runs, and is deleted when the party ends, a rejoin is refused for good,
the viewer signs out, or the server is removed.

The Rejoin button reads "Rejoin {title}", "Rejoin recent party" without a
title, or "Continue here" after another device took the profile over, with
"Rejoining here disconnects this profile's other device from the party."
under it. Rejoin sends `POST /join {code}` and requires the stored room ID
back.

### 4.4 Lobby

- **Top row:** "Watch Party" with the connection dot ("Host away",
  "Open", "{n} here", "Connecting", "Reconnecting", "Disconnected"); on
  the right the code pill ("JOIN WITH", the code, a QR glyph), which opens
  the invite screen, and the Options circle button.
- **Hero:** eyebrow, title, and caption as tvOS's table
  (`WatchPartyHubView.swift:558-603`): "UP NEXT · TOGETHER" or "NOW
  WATCHING · TOGETHER" with the title, a facts line (subtitle, year,
  runtime, quality chips "4K"/"1080p"/"720p"/"HDR"), a three-line overview,
  and "You chose this" or "{Host} chose this"; "A title you can't see" or
  "Loading title…" before the item reads; "YOUR PARTY IS OPEN" with "Pick
  something\nto watch" (manager) or "Waiting for\n{Host}" (guest) and their
  captions; in a vote lobby "VOTING · {n} TITLE(S)", "What are we
  watching?" at 60, and "Everyone votes. You start the leader." or "Tap a
  title to vote. {Host} starts the winner.". `{Host}` falls back to "The
  host". Spoiler rules hide an unwatched episode's still and overview
  (spec section 5.6), and a hidden still uses the Roku's small-decode blur.
- **Backdrop:** the item's backdrop, else its poster dimmed, else (vote)
  the leading suggestion's poster, under tvOS's two gradients.
- **Status banner**, first match: the last error; "This title isn't
  available to your profile. Choose something else so everyone can watch."
  (manager) or "…{Host} will need to pick something else." (guest);
  "{Host} lost connection. The party holds for two minutes while they come
  back."; "Reconnecting to the party…".
- **Seats** ("HERE NOW" with "nobody connected", "only you so far", "{r}
  of {n} ready", or "{w} of {n} watching"): host first, then you, then by
  name. A seat is a gradient disc (palette pair by djb2 of
  `"{user_id}:{profile_id}"` mod 6) with the name's first letter, a ring
  for its state, a check for ready or watching, the name, and "Host",
  "You", and a state ("not ready", "reconnecting", "buffering",
  "syncing", "joining"). Seats are not focusable; the dashed "Invite" seat
  after them is, and opens the invite screen. Vote lobbies draw seats at 80.
- **Buttons** (bottom right, secondary then primary, initial focus on the
  primary), from `WatchPartyLobbyState.swift:274-296`:
  - playing: "Return to playback"; in the room panel after the end of the
    file, "Return everyone to lobby" for a manager with `stop_playback`,
    else none; a guest who cannot see the title gets none;
  - lobby, manager, vote: "Start {winner}" when there is one, else
    "Suggest a title"; secondary "Suggest";
  - lobby, manager, host pick: "Choose a title", "Start for everyone" once
    staged (disabled while a pick is unconfirmed), or "Change title";
    secondary "Change title" beside Start;
  - lobby, guest with `lobby_ready`: "I'm ready" / "You're ready" (with
    "tap to undo"), sending `lobby_ready`; vote rooms add "Suggest a title";
  - playing, manager, host pick: secondary "Choose something else".
  Start is enabled only while connected. Play/Pause on the remote presses
  Start when Start is the primary and enabled.
- **Hints** under the buttons (lobby only): "Suggest a title to get the vote
  going.", "Nobody has voted yet.", "Everyone's ready.", "{A}[ and {B}][ and
  others] hasn't/haven't marked ready. You can still start.", "{Host}
  starts {winner|the winner} when voting settles.", "{Host} starts the
  movie when everyone's set.".

The winner is the highest `vote_count` above zero, ties to the earliest
`created_at`, then the lowest ID. A vote room's Start promotes it (`POST
/suggestions/promote`).

### 4.5 Ballot (vote lobby)

A row of candidate cards (220×330 posters) in server order, then the
"Suggest a title" / "Anyone can add one" card. A card shows its votes
("{n} VOTE(S)", inverted on the leader), a check when you voted, a leader
outline, the title, and the note in quotes or the subtitle. OK toggles your
vote (`POST`/`DELETE .../vote`); it waits while your own vote is unknown or
the socket is down. Options (`*`) offers "Start this one" to a manager
(with `vote_host_override`) and "Remove suggestion" to a manager or the
suggester (same user and profile).

Your own votes come only from `GET /suggestions`; `suggestions_update`
says `voted_by_me` false for every row, so the client keeps its rows'
votes from the last read and reads again after the frame. The list is read
after each connect, as the server sends none then. Errors: "Your change was
saved, but the suggestions could not be refreshed. {error}" and "Could not
refresh suggestions. {error}".

### 4.6 Suggestions in a host-pick lobby

When a host-pick lobby has suggestions, a strip to the right of the hero:
"SUGGESTIONS · {n}" and "Queue one to put it up next." (manager) or "The
host decides what plays." (guest), with 120×180 posters. OK on a card
stages it (or plays it without `staged_selection`); Options offers "Remove
suggestion" under the ballot's rule. Only cards that can be queued or
removed take focus.

### 4.7 Invite screen

Full screen over the selected item's backdrop. Left: "INVITE FRIENDS",
"Join with this code" (70.4 Bold), "Anyone with a profile on this Silo
server can enter it from Watch Party.", the code (72, tabular), "Or scan to
open the invitation on a phone.", and "Done", which has focus. Right: a
560 px QR code of `invite_path` resolved against the configured origin,
drawn by the app's `QrCode` view (`QrTask`). Without an invite path (a
guest) there is no QR and no scan line. Back closes it.

### 4.8 Picker

"Choose a title" (select) or "Suggest a title" (suggest), full screen, with
Search and Close in its top strip. Shelves, empty ones left out, movies,
series, and episodes only:

1. "Continue Together": `GET /rooms/{id}/picker` `continue_together`
   (needs `picker`);
2. "On Your Watchlists": `watchlist_union`, or without `picker`
   `GET /api/v2/catalog?type=video&limit=40&source=watchlist`;
3. up to four Home discovery rows from `GET /api/v2/home/sections`,
   leaving out tvOS's excluded types (recently added and released, new to
   library, continue watching, next up, next in series, watchlist,
   favorites, activity, because you watched, recommended for you, similar
   users, taste match, forgotten favorites);
4. "Recently Added Movies" and "Recently Added Series":
   `GET /api/v2/catalog?type={movie|series}&limit=24&sort=added_at&order=desc`.

Empty: "Nothing to pick from yet" / "Search for a title, or add something
to a watchlist.", focus on Search. Search uses the app's Search page
keyboard and grid ("Search movies and series…", "No results" / "Try a
different search term"), without audiobooks.

Choosing: an episode or movie opens the confirm page; a series with a
group `next_up` opens the confirm page for that episode; another series
opens the episode browser ("WATCH PARTY · CHOOSE AN EPISODE" or "…
SUGGEST AN EPISODE", the series title, season tabs, the episode rail, the
focused episode's line and overview under spoiler rules, "No episodes in
this season" with "Reload episodes").

Confirm page: backdrop, 260-wide poster, "WATCH TOGETHER" or "SUGGEST TO
THE PARTY", the title (79.2 Bold), facts, a six-line overview, and the
button with focus: "Add suggestion" (`POST /suggestions`), "Choose for the
party" (`PUT /staged-selection`, lobby with `staged_selection`), or "Play
for everyone" (`PUT /selection`). "See all episodes" opens the browser
when the choice belongs to a series. Success closes the picker.

**Who's Seen It** (needs `member_state`): `POST /rooms/{id}/member-state
{content_ids:[id]}` when the confirm page opens; "Checking viewing
history…", then a row per connected member: "Watched", "In progress",
"Not watched", or "No viewing history", with " · Watchlist" when it is on
theirs. Error: "Could not load member watch history. {error}".

### 4.9 Party options and ending

Options opens "Party options" (a 900-wide card over a 62% scrim; focus on
Close; Back closes it). A manager sees "Who chooses" ("Everyone votes" /
"Host chooses"; lobby with `selection_mode_switch`), "Playback controls"
("Guests can play and pause" / "Host only"), "Return everyone to lobby"
(playing with `stop_playback`), and "End party for everyone". Everyone sees
"Leave party" and "Close".

End party asks "End this party for everyone?" (Cancel, End Party) through
the app's `ConfirmDialog` and sends `DELETE /rooms/{id}`. Leave party closes the socket and
forgets the room; the server learns from the socket. A host who leaves
keeps the room open for two minutes.

### 4.10 In the player

- **Start:** the room opens the player when it plays, and closes it when
  the room returns to the lobby or ends. It starts paused and moves only
  on room commands.
- **Back:** every step of the player's Back ladder (spec section 5.7) that
  would close the player opens the room panel instead: the lobby over the
  player with "Return to playback" as the primary. Back in the panel
  returns to the player. The error screen's Go Back opens the panel too.
- **Status pill** (top right, after 500 ms): "Reconnecting to the party…",
  or "Syncing with the party…" while the room waits, the player buffers or
  seeks for the room, or this member is syncing. It replaces the
  buffering-quality pill, which a party never shows.
- **Off in a party:** Up Next, autoplay, On Deck, and next-episode
  controls; auto-skip of intros, recaps, and credits; the buffering-quality
  pill and every quality step-down; network-change replans; the version
  menu; Shuffle; voice commands other than play and pause, which follow the
  permissions below.
- **Permissions:** play and pause follow `self_can_control_transport`;
  seeking (scrubbing, skip, Replay, chapters, voice seeks, Skip Intro and
  the other skip buttons) is the host's alone. Allowed actions become
  `transport_request`; a seek holds the scrubber on its target until the
  room's command runs. A refused press shows "Only the host can seek." or
  "Only the host can play or pause." for 3 s (section 10).
- **End of file:** the player pauses at the end with no Up Next; the
  manager's panel offers "Return everyone to lobby". A load that ends
  early reloads where it stopped.
- **Tracks:** audio, subtitles, and quality stay each member's own choice.
- **Errors:** "The Watch Party's selected media version is unavailable."
  when the plan names another file; source fallback as section 8.3.

### 4.11 When a party ends for this device

| Trigger | Message | Rejoin |
| --- | --- | --- |
| `room_closed`, phase `ended`, `409` on a read or ticket, or End party | "This party has ended." | No; the recent party is deleted |
| `connection_replaced` | "This profile joined the party on another device. Rejoin here to take over playback." | "Continue here" |
| `401`/`403`/`404`/`410` on a read or ticket, or a wrong protocol | "The party connection expired or is no longer available. Join again to continue." | Yes |

The player and panel close, and the Watch Party page shows the message
(section 10). A sign-out, profile switch, or server switch leaves the
party silently.

## 5. Server contract

All routes are under `/api/v2/watch-together`, with the account headers.
Room routes for members add `X-Room-Token`, the room proof (a 24-hour JWT)
that every snapshot response renews; host routes check the host's account
and profile instead. Errors are `application/problem+json`.

| Route | Who | Notes |
| --- | --- | --- |
| `GET /capabilities` | any | `ETag` |
| `POST /rooms {room_id, selection_mode}` | any | `201`; replay-safe with the same UUID |
| `POST /join {code}` | any | `404` unknown, `409` closed; membership starts on the socket |
| `GET /rooms/{id}` | member | `403` bad proof, `404`, `409` closed |
| `DELETE /rooms/{id}` | host | `204` |
| `PATCH /rooms/{id}/policy {guest_control_policy}` | host | Read the policy back from the response |
| `PUT /rooms/{id}/staged-selection {content_id, file_id?, library_id?}` | host | Lobby only |
| `PUT /rooms/{id}/selection {...}` | host | Plays at once; never retried |
| `POST /rooms/{id}/playback/start` | host | Never retried |
| `POST /rooms/{id}/playback/stop` | host | To the lobby, item kept |
| `PATCH /rooms/{id}/selection-mode {selection_mode}` | host | Lobby only; clears the stage and readiness |
| `GET /rooms/{id}/suggestions?limit=100&cursor=` | member | Creation order |
| `POST /rooms/{id}/suggestions {suggestion_id, content_id, content_type, title, subtitle?, poster_url?, note?}` | member | `content_type` `movie` or `episode`; 200 per room |
| `DELETE /rooms/{id}/suggestions/{sid}` | host or suggester | |
| `POST`/`DELETE /rooms/{id}/suggestions/{sid}/vote` | member | Approval voting: one vote per suggestion, several suggestions |
| `POST /rooms/{id}/suggestions/promote {suggestion_id}` | host | Any suggestion; never retried |
| `POST /rooms/{id}/member-state {content_ids}` | member | 1 to `max_member_state_ids` |
| `GET /rooms/{id}/picker` | member | |
| `POST /rooms/{id}/source-fallback {selection_revision, failed_file_id, reason}` | connected member | |
| `POST /rooms/{id}/ws-ticket` | member | `{ticket, expires_in, max_connection_seconds, protocol}` |

Start, selection, and promote are not idempotent: the API client must not
replay them after a `401` refresh or a timeout (spec section 6.4).

**Socket messages.** Client to server: `attach_session {session_id}`,
`state_report {session_id, position_seconds, is_paused, command_id?,
is_ready?}`, `ready {session_id, command_id?, position_seconds,
is_paused}`, `buffering {session_id, position_seconds, is_paused}`,
`transport_request {action, position_seconds?, is_paused}`,
`lobby_ready {ready}`, `ping {client_sent_at}`. Server to client:
`snapshot {room}`, `transport_command {command}`, `pong {client_sent_at,
server_received_at, server_sent_at}`, `suggestions_update {suggestions}`,
`room_closed {reason}`, `connection_replaced {reason}`, and `error {code,
message}`, after which the socket stays open.

**Snapshots.** A snapshot older by `generation` than the one held is
dropped; an equal one from the socket wins. `selection_revision` changes
only on start, select, promote, stop, item end, and source fallback, and a
new value means a new playback session. On the socket `user_id`,
`selected_file_id`, and `selected_library_id` are numbers; over HTTP they
are strings. The client stores them as strings. `anchor_position_seconds`
is already projected to when the snapshot was built, and
`anchor_updated_at` has whole-second precision, so the client never syncs
from a snapshot (section 7.2).

## 6. Room connection

### 6.1 Order

Join or create, then: read the room, request a ticket, open the socket. On
open, start the clock (section 7.1), read the suggestions, and attach the
playback session when there is one.

### 6.2 Snapshots and the room's state

The client keeps the newest snapshot and derives the page and the player
from it: phase `lobby` shows the lobby (a set `selected_content_id` is the
staged item), `playing` opens the player for `selected_file_id`, `ended`
ends the party (section 4.11). Membership flags (`is_ready`,
`is_buffering`, `is_syncing`, `lobby_ready`, `connected`) drive the seats.

### 6.3 Errors on the socket

`bad_request` before the attach is confirmed goes to the banner; after it,
to the log only. `internal_error` goes to the banner. A message the client
does not know is ignored.

### 6.4 Reconnect

- A socket that was open for 30 s or more reconnects at once and shows no
  "Reconnecting": that is the server's 5-minute rotation.
- Otherwise the client waits 0.5, 1, 2, then 5 s with up to 25% jitter
  between attempts, showing "Reconnecting", and gives up after 6 failures
  and 150 s without a healthy socket, as Android does.
- `409` on the read or ticket ends the party; `401`/`403`/`404`/`410`, a
  wrong protocol, or `connection_replaced` stop reconnecting
  (section 4.11). A `401` first refreshes the access token through the
  single-flight coordinator (spec section 6.4), once.
- A pending command is dropped when its socket closes. After a reconnect
  the client attaches again; the server answers with a sync command.

## 7. Synchronization

The server keeps the room's position and sends timed commands; each member
decides how to meet them. These rules are the ones Web, Apple, and Android
share (`watch-party-synchronization.md`), with the seek-only path.

### 7.1 Clock

`ping` on connect, every 2 s until 4 samples, then every 15 s. For each
`pong`: round trip = (receive − send) − (server sent − server received);
offset = ((server received − send) + (server sent − receive)) / 2. Keep
the last 8 samples under 5 s round trip and use the offset of the fastest.
When a new sample's offset differs from the best by more than
(rtt₁ + rtt₂) / 2 + 50 ms, the clock stepped: drop the samples.
Timestamps are RFC 3339 with up to nine fractional digits, parsed by hand
to milliseconds; local time comes from a monotonic `roTimespan` anchored to
`roDateTime` at start. Without a clock the client waits paused, and after
3 s says "Waiting for party timing. If this continues, leave and rejoin."
(section 10).

### 7.2 The room's position

The reference is the last command this member executed, never a snapshot:
`room = position_seconds + (server_now − execute_at)` while playing, or
`position_seconds` while paused. A command runs at its `execute_at`
converted to local time, at once if that has passed (a late Play is
projected forward), and play state and seeks change only when it runs,
never when it arrives. Positions are source positions
(`source/playback/seek.bs`).

### 7.3 Reports

- `attach_session` as soon as the playback session is committed, again
  every 1.5 s until a snapshot names it in `attached_session_id`, and after
  every reconnect.
- `state_report` every 1.5 s with the last executed `command_id`, only when
  the player has a real position: none while stalled, seeking, loading,
  or within 250 ms of a pending command. After a command, reports wait
  until the player shows that command's play state (at least 250 ms, at
  most 3 s).
- `ready` (and `state_report {is_ready: true, command_id}`) every 500 ms
  while the room waits on a seek this member must acknowledge, or while
  this member catches up (`self_ignore_wait`, or its own buffering).
  Never otherwise: a `ready` in a playing room causes another sync seek.
- `buffering` once per stall, after 2 s without progress while the room
  plays. The 2 s restarts after each seek and command.

### 7.4 Seek barrier

A room seek sets the room waiting. The member seeks exactly to the
target and acknowledges. The server accepts a guest within 1 s of the
target (5 s for a stalled guest's own seek naming the command), a host
within 15 s, and after 10 s, once any member is ready, continues without
the rest, who catch up alone. Roku seek precision (W0-2) decides whether a
Roku guest makes the 1 s window. If it lands short, the member plays muted
to the target and pauses there before it acknowledges.

### 7.5 Correction without a rate

Drift = player position − room position, checked every 500 ms after 1 s
of settle from the last command or seek. Constants from
`RoomCatchup.kt:36-80` and `WatchPartyPlaybackAdapter.swift:62-205`:

| Situation | Action |
| --- | --- |
| Playing, drift ≤ 1 s | Nothing (the server's band is 1 s) |
| Playing, drift > 1 s and ≤ 5 s (2 s for the host executing a command) | Seek in place to room + lead. Lead starts at 0; after each correction seek settles, lead = clamp(lead + residual, 0, 2 s). A residual over 1 s doubles the wait before the next seek, 1 s up to 16 s; a hit resets it to 1 s |
| Playing, drift > 5 s, or an in-place seek is a reload on this plan | Budgeted reload aimed ahead (below) |
| Command while paused or stopped | Seek first only if drift > 5 s, or > 1 s when an in-place seek is possible; joining a playing room, seek once more aimed ahead by the first seek's duration if it left more than 0.4 s |
| Room `seek` command | Exactly to the target, no lead |

**In place on Roku.** Roku reports no buffered range (spec section 9.6), so
"reachable in place" is a property of the plan: a `Video.seek` on a direct
or transcode plan, which the server serves where it is asked. On a copy
remux, where a seek outside the remuxed window becomes a `seek_reanchor`
that replays up to a keyframe interval (hardware run 9: 0.7–4.1 s), a
correction counts as a reload. W0-2 measures each plan type and may change
this.

**Reload budget** (`RoomReloadBudget`): one at a time; the next 10 s after
the last one played, doubling to 60 s; a reload that never lands is stale
after 30 s; each aims ahead by the previous load's time, at most 10 s;
landed means within −0.4 to +2 s; drift under 0.4 s resets the back-off.

The server re-sends a correction every 10 s or so while a member stays
over 1 s off; executing one is idempotent.

### 7.6 Late join and background

A member joining a playing room loads paused at the snapshot's anchor and
attaches; the server's sync command does the rest. The Roku has no
background: Home closes the app and the socket with it. Roku's own
overlays over the player do not pause the room.

## 8. Playback

### 8.1 Start

The room's playback uses the normal protocol v3 start
(`source/playback/capabilities.bs`) with `file_id` = `selected_file_id`,
`library_id` = `selected_library_id`, `start_position` = the anchor, no
resume rewind, `allow_alternate_versions` false, mounted paused. A plan
whose `effective_media_file_id` names another file fails with "The Watch
Party's selected media version is unavailable." and stops its session.

### 8.2 Sessions

A new `selection_revision`, a replan, or a reload makes a new playback
session, which the client attaches again. Progress and stop reporting
follow spec section 9.5 as for any session.

### 8.3 Source fallback

With `watch_party_source_fallback_v1`, a start refused for
`no_alternate_version`, `hdr_transcode_unsupported`,
`subtitle_conversion_unsupported`, or `transcoding_disabled` sends
`POST /rooms/{id}/source-fallback {selection_revision, failed_file_id,
reason}`. The room moves every member to a new revision.

## 9. Interactions

- **SiloControl.** A phone controlling the Roku during a party gets the
  room's permissions: play and pause per `self_can_control_transport`,
  seek for the host only, through `transport_request`. Launch, replace,
  and play-next are refused with "This Watch Party does not allow this
  playback action." A phone's Stop leaves the party, as on tvOS
  (`PlayerViewModel.swift:10323`). The rules go in
  `source/control/policy.bs`.
- **Deep links.** A deep link during a party leaves it and plays the link:
  Roku requires a deep link to play at once (criterion 5.2), and the room
  cannot play another title for one member. tvOS has no equivalent to
  compare.
- **Profile, server, sign-out.** Each leaves the party first.
- **Diagnostics.** The log records room ID, revision, command IDs, drift,
  corrections, and reconnects, never codes, tickets, or proofs (spec
  section 11.1).

## 10. Roku differences from tvOS

| tvOS | Roku | Reason |
| --- | --- | --- |
| Watch Party is a per-device Extra Features toggle, off in Release | On in every build | Owner's decision (D-10) |
| Drift of 0.4–5 s closes by rate on iOS; tvOS seeks | Seeks, as tvOS | `Video` has no rate |
| Join field "Party code or invite link" on the system keyboard | "Join with a code" opens an 8-slot code keypad (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, 8 keys per row), as Android TV's `TvJoinCodeDialog` | Typing a URL on a remote is impractical, and a Roku cannot receive a link to paste |
| Invitation links open the party | None | A Roku has no URL handler; Roku deep links carry only `contentId` and `mediaType` |
| Episode-rail context item | Series detail More only | Roku's episode rail has no context menu (spec section 5.9) |
| Long press on a ballot or strip card | Options (`*`) | Roku has no press and hold (spec section 5.9) |
| "Suggest to Party" during playback opens the page and does nothing | Opens the page with "You can suggest titles from the party's lobby." | A silent no-op reads as a fault |
| A refused press is dropped silently | "Only the host can seek." / "Only the host can play or pause." for 3 s, as Android TV | A remote press with no response reads as a fault |
| The ended and replaced messages show only if the Watch Party page is on the stack | The app opens the Watch Party page with the message | Otherwise the viewer lands on Home with no explanation |
| Without a clock the player waits silently | "Waiting for party timing. If this continues, leave and rejoin." after 3 s, as Android TV | Same |
| The background keeps the party player | Home closes the app and leaves the party; a host's room holds 2 minutes | No background execution without Instant Resume |
| The code in monospaced type | Tabular Inter, as the sign-in code (spec section 5.9) | No monospaced face ships |
| Blurred episode stills | The small-decode blur (spec section 5.9) | SceneGraph has no blur |

## 11. Components

| Part | Where | Owns |
| --- | --- | --- |
| Room task | `components/tasks/RoomTask` | The `roWebSocket`, tickets, reconnect, clock, report loop, and command timing. Writes snapshots, commands, and notices to fields |
| Room logic | `source/watchparty/` | Pure functions: wire parsing, RFC 3339 parsing, clock estimator, snapshot acceptance, command bookkeeping, stall timer, readiness, correction and reload budget, lobby button and hint rules, winner |
| REST | `source/api/` | The routes in section 5, through the shared client |
| Room session | `AppScene` | One party per app run, adopted by screens, never owned by them |
| Watch Party page, lobby, ballot, invite, options | `components/screens/watchParty/` | Section 4 |
| Picker | `components/screens/watchParty/picker/` | Section 4.8, reusing Home rows, Search, and the episode rail |
| Player | `components/player/` | Room start, Back to the panel, status pill, permissions, command execution on the render thread |
| Recent party | `source/storage/registry.bs` | Section 4.3 |

The room task waits on its message port with a timeout to the next due
event (a command's `execute_at`, a report, a ping), so commands reach the
render thread on time without a busy loop. The render thread applies a
command when its field changes; W0-3 measures that hop.

## 12. Testing

### 12.1 Spikes (Roku Ultra 4850X, Roku OS 16.0.4)

| ID | Question | Pass |
| --- | --- | --- |
| W0-1 | `roWebSocket`: can the app send `Sec-WebSocket-Protocol: silo.room.v2, silo.ticket.{t}` and read the server's choice; does it answer ping frames; does `wss://` verify with the system CA bundle; how large a message arrives; does it run in a Task; what close events look like | A sandbox room socket stays open past 60 s and receives a snapshot; a 5 MB message arrives or fails cleanly |
| W0-2 | Where `Video.seek` lands for direct, remux, and transcode plans, and how long it takes | Landing error per plan type, to set section 7.4's acknowledgement and 7.5's in-place rule |
| W0-3 | Delay from the task's field write at `execute_at` to the render thread's `Video` call, on the Ultra and a 1 GB device | Under 50 ms at the 95th percentile |
| W0-4 | Memory with the room task, the lobby, and a 200-suggestion ballot open | Within the memory monitor's budget (spec section 4) |

### 12.2 Unit tests

Rooibos specs for `source/watchparty/`, ported from Android
`RoomCatchupTest`, the rate-unsupported cases of `RoomPlaybackBindingTest`
(:667-1015), `WatchPartyWireTest`'s clock cases, and tvOS
`WatchPartyStateTests` and `WatchPartyCatchupTests`, with server-shaped
fixtures for snapshots, commands, and suggestions.

### 12.3 Party matrix

The `watch-party-matrix` harness (`wpm`) gains a `roku` member: physical
only, signed in by device-code approval, joined through a development
deep link the harness launches over ECP, measured by the proxy's tap
(reported drift), ECP `query/media-player` polls, and the console's
`[WP]` lines. Roku screenshots omit the video plane, so the film's frame
barcode cannot be read from them. Rooms: a web host with the Roku; a web
host with tvOS, Android TV, and the Roku; the `stall` timeline. A Roku
member passes when its steady reported drift matches tvOS's in the same
room (`references/baseline-2026-10.md`).

### 12.4 Hardware

Every row of section 4 on the Ultra, hosting and as a guest, against a
server on HTTPS and one on plain HTTP; the 1 GB device once it runs Roku
OS 16.

## 13. Open decisions

| Decision | Leaning | Needs |
| --- | --- | --- |
| A Roku without `roWebSocket` | No Watch Party | Roku OS 16's release and device list |
| `roWebSocket` cannot answer pings or set the subprotocol | Ask the server to accept the ticket another way, or a JSON pong | W0-1 |
| Guest seek landing outside 1 s | Play muted to the target | W0-2 |
| Children's profiles see suggestions' raw titles and posters, which the server does not filter | Show them, as tvOS does | Server owner's view |
