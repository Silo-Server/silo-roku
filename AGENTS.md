# Repository Guidelines

## Purpose

This repository owns the first-party Roku client for Silo. It is a native Roku
SceneGraph and BrightScript application. The Silo server owns authentication,
catalog policy, metadata, playback planning, and transcoding decisions; this
client renders the ten-foot experience and executes server-issued playback
plans.

The current product and technical direction lives in `docs/spec.md`. Keep that
document current when an implementation decision materially changes the scope,
wire behavior, platform floor, or certification plan.

## Product boundaries

- The first release is sign-in, profiles, browse, search, and playback of
  movies and episodic TV. Section 3 of `docs/spec.md` lists what is deferred;
  do not add deferred features without updating it.
- Ebooks, offline downloads, server administration, and library management
  are not part of the first release. Watch Party is in it, on Roku OS 16 or
  later; `docs/watch-party.md` is its specification.
- Live TV, OTA/DVB tuners, IPTV, EPG/XMLTV, DVR, `.strm` files, and equivalent
  arbitrary remote-stream shortcuts are permanent Silo non-goals. Do not add
  them here or expose them through a Roku-only path.
- Use Silo's native `/api/v2` API. Never call `/api/v1`, which retires at Silo
  1.0, and never add a v1 fallback. Do not build this client on jellycompat.
- Match the existing Silo TV apps (tvOS and Android TV) in layout, navigation,
  focus, and player behavior, using the design reference in `docs/spec.md`.
  Record every Roku-specific deviation, with its reason, in that document.

## Architecture rules

- Keep one `roSGScreen` and one root `Scene`; model screens as child components.
- Keep rendering, focus, and navigation on the SceneGraph render thread.
- Perform HTTP and JSON work in `Task` nodes and communicate through observed
  fields. Never block the render thread.
- Centralize API requests, token refresh, profile headers, error decoding, and
  URL resolution. Feature components must not implement their own auth retry.
- Treat playback protocol v3 plans and their URLs as authoritative. Do not
  invent stream URLs, transcode recipes, quality ladders, track ordinals, plan
  IDs, or attempted-plan keys in the client.
- Probe the actual Roku and connected display. Advertise conservative playback
  capabilities and never infer support from model names alone.
- Send account credentials only to the configured Silo server's origin, never
  to a proxy or other origin named in a playback plan.
- Never log access tokens, refresh tokens, profile tokens, device-login codes,
  signed stream URLs, credentials, or server responses that contain them.

## Development workflow

- `docs/development.md` is the procedure for building, sideloading,
  the debug console, and remote control (`npm run roku`). Device address,
  password, and relay come from the gitignored `.env`; see `.env.example`.
- Run `npm run lint` before committing. After `npm run sideload`, confirm the
  change on the device with `npm run roku -- screenshot` or the console; the
  sideload script's success means installed and active, not visually correct.

## Repository hygiene

- Do not commit packaged channels, signing keys, developer-device credentials,
  registry dumps, local server addresses, media fixtures, or tool state.
- Use repository-relative paths in committed documentation.
- Keep third-party code and generated artifacts out of the repository unless
  their license and update process are documented.
- Test on real low-memory and 4K/HDR Roku hardware before claiming support;
  simulators and sideloading alone are not release evidence.
