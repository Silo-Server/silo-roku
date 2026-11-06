# Releasing

Releases run from GitHub Actions on `main` and use the same numbers as
silo-apple and silo-android: each run picks its own version and build number
from the repository's tags. Roku has no upload API, so the packages go to the
Roku Developer Dashboard by hand.

## Tester build

Actions → **Release** → Run workflow, leaving `bump` on `build`.

The run tags the commit `v1.0.0-beta.12` and builds two packages of it with
the same version and build: a beta package, which reports
`X-Silo-Client-Channel: beta`, and the store package. It signs both on the
Roku behind the `roku-signer` runner ("Signed packages" in
[`development.md`](development.md)), keeps them as run artifacts for 90 days,
and publishes a GitHub prerelease, `Silo Roku 1.0.0 (12)`, whose notes list
the pull requests merged since the previous build, grouped by label
(`.github/release.yml`).

Download the `silo-roku-1.0.0-12-beta.pkg` artifact from the run and upload
it to the beta app in the Roku Developer Dashboard. Release builds before
1.0.0 (2) stored packages zipped (artifacts named without `.pkg`): unzip
those and upload the `.pkg` inside, since the dashboard rejects the zip as
"incorrectly packaged". The run's summary has
release notes cut to Roku's 1,500 characters. Packages never go on the public
prerelease.

It requires **CI** to have passed on the commit, so run it once `main` is
green. The build job runs Static Analysis on the stamped store package.

The very first run has no tester build to continue from: enter `1.0.0` as
`version`.

If a run fails, use **Re-run failed jobs**: it keeps the same tag and build
number. Delete the tag instead only if no package of that run reached the
Roku Developer Dashboard. If one did, or you can't tell, keep the tag: Roku
refuses a package whose version is not higher than the last one uploaded.
The next run refuses to start while the newest tag has no release, so its notes
don't skip changes no tester got.

## Store release

1. Actions → **Promote** → enter the tester build, such as `v1.0.0-beta.12`.
   Nothing is rebuilt: GitHub gets a draft release `v1.0.0` on the same
   commit, with the store package that build's Release run signed. Drafts are
   visible only to maintainers.
2. Upload that `.pkg` to the public app in the Roku Developer Dashboard, paste
   the release notes from the run's summary, and submit it for certification
   ([`release-checklist.md`](release-checklist.md)).
3. On GitHub → Releases, edit the `v1.0.0` draft notes.
4. When Roku approves and publishes the app, publish the GitHub release.

Release runs keep packages for 90 days. Promote a build older than that by
running Release again with its version (`version: 1.0.0`) and promoting the
new build.

While the draft exists, version 1.0.0 counts as released: Release refuses
`bump: build`, and `bump: minor` starts 1.1.0. If Roku rejects the build,
delete the GitHub draft and fix the problem. Then run Release with
`version: 1.0.0`, because once 1.1.0 has started, `bump: build` continues that
one. Promote the new build.

## After a store release

The next Release run needs `bump: minor` (the next version has new features)
or `bump: patch` (fixes only). `bump: build` refuses a version that's already
released.

## Numbers

- `1.0.0` is the version people see. It stays the same for every tester build
  until that version is promoted. Settings shows `Silo 1.0.0 (12)`, and the
  app sends `1.0.0` and `12` as `X-Silo-Client-Version` and
  `X-Silo-Client-Build`.
- `12` is the build number: one counter for the whole repository that never
  resets.
- Roku's manifest has only `major_version`, `minor_version`, and
  `build_version`, and Roku requires that version to rise with every package
  uploaded to an app (certification criterion 6.1). Release packages carry
  `1`, `0`, and the build number `12`, which always rises, and the full
  `1.0.0` in the manifest key `silo_version`, which the app reports
  (`scripts/stamp-build-version.sh`, `source/util/version.bs`). Roku's own
  screens show `1.0.12`.
- A hotfix (`bump: patch`) uploaded to the beta app while a newer minor
  version is in testing there is lower to Roku (`1.0.20` after `1.1.19`):
  upload hotfixes to the public app only.
- Tags: `vX.Y.Z-beta.B` for tester builds (GitHub prereleases) and `vX.Y.Z`
  for store releases.
- Local and pull request builds keep the committed manifest version (`0.1`);
  CI stamps its run number as `build_version`.
