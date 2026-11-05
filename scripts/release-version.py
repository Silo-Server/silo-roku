#!/usr/bin/env python3
"""Pick the version, build number and tag for a release from the repo's tags.

The same scheme as silo-apple and silo-android. Every Release run makes a
tester build tagged vX.Y.Z-beta.B:

- X.Y.Z is the store version the build belongs to. It stays the same for
  every tester build until that version is promoted; the next run then starts
  a new version with bump=minor/patch.
- B is the build number: one counter for the whole repository, one higher
  than the highest build in any existing tag. It never resets.

A store release (promote.yml) later tags the same commit vX.Y.Z.

Roku's manifest has no patch field, and Roku requires major.minor.build to
rise with every package submitted. Packages carry major_version=X,
minor_version=Y and build_version=B, which always rises because B never
resets, and the full X.Y.Z in the custom key silo_version, which the app
reports.

Commands print key=value lines for $GITHUB_OUTPUT:

    release-version.py next --bump build|minor|patch [--version X.Y.Z] [--draft vX.Y.Z ...]
    release-version.py beta vX.Y.Z-beta.B
    release-version.py store-notes LIMIT < generated-notes.md
"""

import argparse
import re
import subprocess
import sys

TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?")
VERSION = re.compile(r"(\d+)\.(\d+)\.(\d+)")


class ReleaseError(Exception):
    pass


def parse_tag(name):
    """Return (version, build) for vX.Y.Z-beta.B, (version, None) for vX.Y.Z, else None."""
    match = TAG.fullmatch(name)
    if not match:
        return None
    version = tuple(int(part) for part in match.group(1, 2, 3))
    build = match.group(4)
    return version, int(build) if build else None


def version_text(version):
    return ".".join(str(part) for part in version)


def next_release(tags, bump, version=None, drafts=()):
    parsed = [tag for name in [*tags, *drafts] if (tag := parse_tag(name))]
    released = {tag[0] for tag in parsed if tag[1] is None}
    latest_release = max(released, default=None)
    betas = [(tag[1], tag[0]) for tag in parsed if tag[1] is not None]
    previous_build, previous_version = max(betas, default=(0, None))
    # A hotfix can ship while a newer version is still in testing, so continue
    # the newest version that hasn't been released.
    unreleased = [beta[1] for beta in betas if beta[1] not in released]

    if version:
        match = VERSION.fullmatch(version.removeprefix("v"))
        if not match:
            raise ReleaseError(f"Version must look like 1.2.0, got {version!r}.")
        target = tuple(int(part) for part in match.groups())
    elif bump == "build":
        if not betas:
            raise ReleaseError("There is no tester build to continue yet. Pass the version to start with, for example 1.0.0.")
        if not unreleased:
            raise ReleaseError(
                "There is no unreleased version to add a build to. "
                "Run with bump=minor (new features) or bump=patch (fixes only) to start the next version."
            )
        target = max(unreleased)
    elif latest_release is None:
        raise ReleaseError("Nothing has been released yet, so there is nothing to bump. Pass an explicit version.")
    elif bump == "minor":
        target = (latest_release[0], latest_release[1] + 1, 0)
    elif bump == "patch":
        target = (latest_release[0], latest_release[1], latest_release[2] + 1)
    else:
        raise ReleaseError(f"Unknown bump {bump!r}.")

    if latest_release is not None and target <= latest_release:
        raise ReleaseError(
            f"{version_text(target)} is not newer than the latest release, {version_text(latest_release)}."
        )

    build = previous_build + 1
    previous_tag = f"v{version_text(previous_version)}-beta.{previous_build}" if previous_version else ""
    return {
        "version": version_text(target),
        "build": str(build),
        "tag": f"v{version_text(target)}-beta.{build}",
        "previous_tag": previous_tag,
    }


def beta_release(name):
    tag = parse_tag(name)
    if not tag or tag[1] is None:
        raise ReleaseError(f"{name!r} is not a tester build tag like v1.2.0-beta.42.")
    version, build = tag
    return {
        "version": version_text(version),
        "build": str(build),
        "tag": name,
        "release_tag": f"v{version_text(version)}",
    }


ENTRY = re.compile(r"\* (.+?)(?: by @\S+)?(?: in https://\S+)?")
CONVENTIONAL = re.compile(r"([a-z]+)(?:\([^)]*\))?!?: ", re.IGNORECASE)
USER_FACING = {"feat", "fix", "perf"}


def store_notes(markdown, limit):
    """Plain-text store notes from GitHub's generated release notes.

    Keeps the entries filed under Features or Fixes, plus any other entry whose
    Conventional Commit type is feat, fix or perf (not every pull request is
    labeled). Drops PR links, authors and the type prefix, and fits the result
    into the store's length limit.
    """
    lines, labeled = [], False
    for line in markdown.splitlines():
        if line.startswith("#"):
            labeled = "Features" in line or "Fixes" in line
            continue
        match = ENTRY.fullmatch(line.strip())
        if not match:
            continue
        text = match.group(1)
        prefix = CONVENTIONAL.match(text)
        if not labeled and not (prefix and prefix.group(1).lower() in USER_FACING):
            continue
        if prefix:
            text = text[prefix.end():]
        lines.append(f"• {text[:1].upper()}{text[1:]}")
    if not lines:
        return "Bug fixes and improvements."

    more = "• And more."
    notes = []
    for line in lines:
        reserve = 0 if len(notes) + 1 == len(lines) else len(more) + 1
        if len("\n".join(notes + [line])) + reserve > limit:
            notes.append(more)
            break
        notes.append(line)
    return "\n".join(notes)


def git_tags():
    return subprocess.run(
        ["git", "tag", "--list", "v*"], check=True, capture_output=True, text=True
    ).stdout.split()


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    next_parser = commands.add_parser("next")
    next_parser.add_argument("--bump", choices=["build", "minor", "patch"], default="build")
    next_parser.add_argument("--version", default="")
    # A draft store release (vX.Y.Z) has no git tag yet but counts as released.
    next_parser.add_argument("--draft", action="append", default=[])
    beta_parser = commands.add_parser("beta")
    beta_parser.add_argument("tag")
    notes_parser = commands.add_parser("store-notes")
    notes_parser.add_argument("limit", type=int)
    args = parser.parse_args(argv)

    try:
        if args.command == "store-notes":
            print(store_notes(sys.stdin.read(), args.limit))
            return 0
        if args.command == "next":
            result = next_release(git_tags(), args.bump, args.version, args.draft)
        else:
            result = beta_release(args.tag)
    except ReleaseError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
