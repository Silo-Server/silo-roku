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
locale/          Localized strings
tests/           Unit and contract tests
docs/            Product and architecture documentation
manifest         Roku package manifest
```

## Development

Requirements: Node.js locally, plus curl and Python 3 on the machine that uploads
to the Roku. That machine must reach the developer installer (port 80) and ECP
(port 8060); enable ECP network access on the Roku.

1. Enable Developer Mode on the Roku: with the remote, press Home three times,
   Up twice, then Right, Left, Right, Left, Right. Enable the installer, accept
   the SDK license, and set a password. The username is always `rokudev`.
2. Copy `.env.example` to `.env` and set `ROKU_HOST` and `ROKU_PASSWORD`. If
   this machine cannot reach the Roku, set `ROKU_DEPLOY_VIA` to a command that
   runs a shell command on a host that can (for example an SSH wrapper).
3. Install the tooling and sideload:

```sh
npm install
npm run lint       # BrighterScript validation, no package
npm run sideload   # build out/silo-roku.zip and install it as the dev app
npm run console    # stream the BrightScript debug console (port 8085)
```

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
npm run roku -- active              # print the foreground app
npm run roku -- query device-info   # any /query/<path> ECP endpoint
npm run roku -- screenshot shot.jpg # capture the screen (dev app only)
```

If an install keeps reporting "Install timeout" and the dev app never appears in
`query apps`, the device's installer can get stuck; a software restart may not
clear it. Unplug the device for 60 seconds, then sideload again.

## License and trademarks

The implementation is intended to use `AGPL-3.0-or-later`, matching the other
first-party Silo clients. A license and the standard Silo trademark notice will
be added before implementation begins.
