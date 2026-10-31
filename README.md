# Silo Roku

Native Roku client for the [Silo](https://github.com/Silo-Server/silo-server)
self-hosted media server: sign in, browse your movies and shows, and play them
with server-planned direct play, remux, or transcode.

> **Status:** Pre-release; not yet submitted to Roku. The app signs in to a
> Silo server, browses, searches, and plays movies and TV through playback
> protocol v3. Every build runs companion sign-in and, since decision D-7 in
> [`implementation-assumptions.md`](docs/implementation-assumptions.md), the
> SiloControl receiver.
> Hardware testing so far used a Roku TV and a Roku Ultra, nearly all of it
> in development builds; [`release-checklist.md`](docs/release-checklist.md)
> lists what still blocks a beta.

## Table of contents

- [What's inside](#whats-inside)
- [Install](#install)
- [Features](#features)
- [Layout](#layout)
- [Prerequisites](#prerequisites)
- [Build and sideload](#build-and-sideload)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License and trademarks](#license-and-trademarks)

## What's inside

| | |
|---|---|
| **Platform** | Roku OS, FHD (1920×1080) layout scaled for HD models |
| **Language / UI** | BrightScript and BrighterScript · Roku SceneGraph |
| **Playback** | Roku `Video` node driven by Silo playback protocol v3 over `/api/v2` |
| **Tests** | Rooibos specs, run headless under brs-node |
| **Tooling** | Node.js 22 · bsc and bslint · Roku Static Analysis |
| **Platform floor** | `rsg_version=1.3`, minimum firmware 15.1.0 (set on the Developer Dashboard) |

The server owns the library, metadata, playback decisions, and auth. The
client renders what the server returns and plays the plan it chooses.

## Install

There is no store or beta release yet. To run the app, sideload a
development build onto a Roku in Developer Mode (see
[Build and sideload](#build-and-sideload)).

## Features

The first public release covers what a viewer needs to find something and
watch it. [`docs/spec.md`](docs/spec.md) section 3 has the full scope.

- **Setup and accounts:** several saved Silo servers, sign-in with a QR code
  or an activation code, password sign-in, companion sign-in from a Silo
  phone app on the network, and the profile picker with PINs and child
  profiles.
- **Browse:** Home from the server's sections (including Continue Watching
  and Next Up), Movies and Series library tabs with Recommended rows and a
  Browse grid with sort, filters, and an alphabet rail, read-only
  Collections, For You, Calendar, Requests, Search, movie and series detail
  pages, and person pages.
- **Playback:** direct play, remux, or transcode as the server plans it, with
  audio and subtitle selection, resume, and Up Next.
- **Roku integration:** deep links for movies, episodes, series, and
  seasons, and the SiloControl receiver, so a Silo phone app can act as a
  remote and hand playback off to the TV.
- **Diagnostics:** Settings > Diagnostics sends a redacted log to Silo
  Diagnostics, and Home offers to after a crash.

## Layout

```text
components/      SceneGraph components and their BrightScript controllers
source/          Entry point and non-visual BrightScript modules
images/          Packaged Roku artwork
fonts/           Subset Inter TTFs with their license and SOURCE
locale/          Localized strings
tests/           Rooibos specs, mirroring source/ paths
scripts/         Build, sideload, signing, device, and asset scripts
docs/            Product and architecture documentation
manifest         Roku package manifest
```

## Prerequisites

- Node.js 22 (`.nvmrc`) and Python 3
- A Roku in Developer Mode that this machine (or a relay host with curl and
  Python 3) can reach on ports 80 and 8060
- A running Silo server for sign-in, browsing, and playback

## Build and sideload

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
npm run sideload       # build out/silo-roku.zip and install it as the dev app
npm run sideload:dev   # the dev build, with the diagnostic screen and dev tools
npm run console        # stream the BrightScript debug console (port 8085)
npm run roku -- key Home   # drive the device over ECP
```

`npm run build`, `build:beta`, `build:perf`, and `build:dev` make the four
package variants in `out/`. Sideloading replaces the device's single
developer app slot, and sideloaded builds are not release evidence.

## Testing

```sh
npm test               # Rooibos specs, headless under brs-node, in shards
npm run format:check   # brighterscript-formatter check (npm run format rewrites)
npm run ci             # the pull request checks: lint, format, build, size,
                       # hygiene, Static Analysis, contract, and tests
```

Static Analysis needs Java 21 and unzip. Headless results are not device
evidence; `scripts/device-check.sh` runs the cold-launch, performance, and
deep-link checks on a real Roku.

## Documentation

- [`docs/development.md`](docs/development.md): the full development
  procedure: build variants, theme and navigation internals, the test
  shards, CI checks, signed packages, remote control, deep links,
  diagnostics, SiloControl, and the device check
- [`docs/spec.md`](docs/spec.md): the client specification (scope,
  architecture, Silo API use, playback, certification risks)
- [`docs/implementation-plan.md`](docs/implementation-plan.md) and
  [`docs/implementation-assumptions.md`](docs/implementation-assumptions.md)
- [`docs/release-checklist.md`](docs/release-checklist.md) and
  [`docs/hardware-evidence.md`](docs/hardware-evidence.md)
- [`docs/silocontrol.md`](docs/silocontrol.md) and
  [`docs/companion-pairing.md`](docs/companion-pairing.md)

## Contributing

Right now, the most helpful way to contribute is a clear, accurate issue. We
implement and review changes through our own workflow, and pull request volume
has outgrown what we can review carefully, so a good issue usually helps us
more than a pull request.

Pull requests are still welcome from contributors who've had one merged in a
Silo repository, or when a maintainer asks for one. We close other pull
requests without review.

## License and trademarks

Silo Roku is licensed under `AGPL-3.0-or-later`. See [LICENSE](LICENSE).

The **Silo name, logo, and wordmark are trademarks of Silo Media L.L.C.** and
are **not** covered by the AGPL. You're free to fork and redistribute the code,
but forks and redistributions must not use the Silo brand as their identity and
must remove or replace the brand assets. Publishing a Silo-branded app to an app
store requires written permission. See [TRADEMARK.md](TRADEMARK.md) for what's
permitted — including referential use like "compatible with Silo."
