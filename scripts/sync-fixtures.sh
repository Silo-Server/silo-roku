#!/usr/bin/env bash
# Copy the contract the client is tested against from a pinned silo-server
# commit into tests/fixtures/ (implementation plan section 5): the v2 playback,
# server setup, sign-in, profile, and catalog fixtures with their index
# entries; a self-contained subset of contracts/api/v2/openapi.json holding the
# playback request bodies the client sends and every schema they reference;
# and the method, path, and query parameters of each catalog operation the
# browse screens and the player's previews call (source/catalog/requests.bs,
# source/playback/trickplay.bs). The server checkout is only read with git; this
# never checks out, fetches, or edits anything there. Writes
# tests/fixtures/SOURCE; running it again at the same commit changes nothing.
#
# Usage: scripts/sync-fixtures.sh <silo-server checkout> [commit]
# The commit defaults to the pin below; fetch it in the checkout first.
set -euo pipefail
cd "$(dirname "$0")/.."
pinned=3bc9e58c51970f261d41848ff411713894d53243
server=${1:?usage: scripts/sync-fixtures.sh <silo-server checkout> [commit]}
commit=${2:-$pinned}

sha=$(git -C "$server" rev-parse --verify --quiet "$commit^{commit}") ||
    { echo "commit $commit is not in $server; fetch it there first" >&2; exit 1; }

python3 -I - "$server" "$sha" tests/fixtures <<'PY'
import json
import pathlib
import subprocess
import sys

REPOSITORY = "https://github.com/Silo-Server/silo-server"
# Request bodies the client serializes; their $ref closure is kept.
ROOTS = ["PlaybackStartBody", "PlaybackReplanBody", "PlaybackProgressBody", "PlaybackStopBody", "PlaybackRouteEventBody"]
OPERATIONS = {
    "getPlaybackCapabilities", "startPlayback", "replanPlayback", "updatePlaybackProgress", "stopPlayback", "reportPlaybackRouteEvent",
    # Server setup, sign-in, and profiles (source/auth/).
    "getSystemInfo", "getSetupStatus", "listAuthProviders", "login", "refreshSession", "logout", "getCurrentUser", "listProfiles", "verifyProfilePIN",
}
# Browse, search, and detail (source/catalog/), and the player's seek-bar
# previews (source/playback/trickplay.bs); their parameters are kept too.
CATALOG = {
    "listUserLibraries", "listHomeSections", "getHomeSectionItems", "listLibrarySections", "getLibrarySectionItems",
    "listCatalogItems", "getCatalogSearchCapabilities", "getCatalogItem", "listSeriesSeasons", "listSeasonEpisodes",
    "getWatchState", "getBranding", "getWatchTrickplay",
    # The detail page's remembered audio and subtitle tracks (catalog.request.savePreference).
    "getAudioPreference", "updateAudioPreference", "deleteAudioPreference", "updateSubtitlePreference", "deleteSubtitlePreference",
}
OPERATIONS |= CATALOG
OPENAPI = "contracts/api/v2/openapi.json"
FIXTURES = "contracts/api/v2/fixtures"
SCHEMA_OUT = "openapi/playback-v3.json"
OPERATIONS_OUT = "openapi/catalog-operations.json"
FIXTURE_OUT = "v2"

server, sha, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])


def show(path):
    return subprocess.run(["git", "-C", server, "show", f"{sha}:{path}"], check=True, capture_output=True).stdout


def refs(node):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield ref
        for value in node.values():
            yield from refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from refs(value)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def dump(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


openapi = json.loads(show(OPENAPI))
schemas = openapi["components"]["schemas"]
kept = {}
pending = list(ROOTS)
while pending:
    name = pending.pop()
    if name in kept:
        continue
    kept[name] = schemas[name]
    for ref in refs(schemas[name]):
        prefix = "#/components/schemas/"
        if not ref.startswith(prefix):
            sys.exit(f"{name}: unsupported reference {ref}")
        pending.append(ref[len(prefix):])
write(out / SCHEMA_OUT, dump({"openapi": "3.1.0", "components": {"schemas": kept}}))


operations = {}
for path, item in openapi["paths"].items():
    for method, operation in item.items():
        if not isinstance(operation, dict) or operation.get("operationId") not in CATALOG:
            continue
        query = {}
        for entry in item.get("parameters", []) + operation.get("parameters", []):
            if "$ref" in entry:
                sys.exit(f"{operation['operationId']}: unsupported parameter reference {entry['$ref']}")
            if entry["in"] == "query":
                query[entry["name"]] = {key: entry["schema"][key] for key in ("type", "enum", "minimum", "maximum") if key in entry["schema"]}
        operations[operation["operationId"]] = {"method": method.upper(), "path": path, "query": query}
missing = CATALOG - operations.keys()
if missing:
    sys.exit(f"operations not in {OPENAPI}: {', '.join(sorted(missing))}")
write(out / OPERATIONS_OUT, dump({"operations": operations}))

index = json.loads(show(f"{FIXTURES}/index.json"))
entries = [entry for entry in index["fixtures"] if entry.get("operation_id") in OPERATIONS]
bodies = sorted({entry["body_file"] for entry in entries if entry.get("body_file")})
write(out / FIXTURE_OUT / "index.json", dump({"fixtures": entries}))
for body in bodies:
    write(out / FIXTURE_OUT / body, show(f"{FIXTURES}/{body}"))
expected = {"index.json", *bodies}
for stale in (out / FIXTURE_OUT).iterdir():
    if stale.name not in expected:
        stale.unlink()

date = subprocess.run(["git", "-C", server, "show", "-s", "--format=%cI", sha], check=True, capture_output=True, text=True).stdout.strip()
lines = [
    f"repository: {REPOSITORY}",
    f"commit: {sha}",
    f"date: {date}",
    "synced by: scripts/sync-fixtures.sh",
    "files:",
    f"  {OPENAPI} -> tests/fixtures/{SCHEMA_OUT} (schemas {', '.join(ROOTS)} and their references)",
    f"  {OPENAPI} -> tests/fixtures/{OPERATIONS_OUT} (method, path, and query parameters of {', '.join(sorted(CATALOG))})",
    f"  {FIXTURES}/index.json -> tests/fixtures/{FIXTURE_OUT}/index.json (entries for {', '.join(sorted(OPERATIONS))})",
]
lines += [f"  {FIXTURES}/{body} -> tests/fixtures/{FIXTURE_OUT}/{body}" for body in bodies]
write(out / "SOURCE", ("\n".join(lines) + "\n").encode())
print(f"synced {len(kept)} schemas, {len(operations)} catalog operations, and {len(entries)} fixtures from {sha}")
PY
