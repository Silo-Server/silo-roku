# Silo Roku

Native Roku client for the [Silo](https://github.com/Silo-Server/silo-server)
self-hosted media server.

> **Status:** Design and platform-validation phase. The repository does not yet
> contain a runnable Roku app.

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

## License and trademarks

The implementation is intended to use `AGPL-3.0-or-later`, matching the other
first-party Silo clients. A license and the standard Silo trademark notice will
be added before implementation begins.
