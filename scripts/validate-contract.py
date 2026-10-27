#!/usr/bin/env python3
"""Validate the serializer's and session reducer's golden bodies, and the
History page's removal body, against the server contract.

Every tests/fixtures/golden/<kind>/*.json must be a valid body of its kind
(GOLDEN below: start, replan, progress, stop, route-event, and
history-remove, which is checked against its schema only), checked three ways:

1. The vendored schema subset (tests/fixtures/openapi/playback-v3.json, from
   scripts/sync-fixtures.sh): required members, additionalProperties, types,
   enums, patterns, lengths, bounds. Unknown schema keywords fail, so a
   server schema that starts using one is noticed rather than skipped.
2. Rules the server enforces beyond the schema at the pinned commit
   (internal/apiv2/playback.go, internal/playback/protocol_v3.go;
   implementation plan section 5).
3. The client's own rules from plan sections 5 and 6.1 and decision D-1.

The server's own request fixtures (tests/fixtures/v2/) are validated against
the schema too, and a self-test checks that broken bodies are rejected, so a
lenient walker cannot pass everything. Standard library only; run it with
python3 -I scripts/validate-contract.py.
"""
import copy
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMAS = json.loads((FIXTURES / "openapi" / "playback-v3.json").read_text())["components"]["schemas"]
# Members newer than the pinned schema, which the client sends only when the
# server advertises the feature that honors them (assumption AG-171):
# dv8_base_layer_compatibility_ids under dv8_base_layer_compatibility_ids_v1,
# from silo-server roku/dv8-bl-compat-ids (2110cf8ac, not on main yet). Drop an
# entry once scripts/sync-fixtures.sh brings the member in.
PROPOSED = {
    "DeliveryCapabilityV3": {
        "dv8_base_layer_compatibility_ids": {"type": "array", "maxItems": 16, "items": {"type": "integer", "minimum": 0, "maximum": 15}},
    },
}
for _schema, _members in PROPOSED.items():
    for _name, _member in _members.items():
        if _name in SCHEMAS[_schema]["properties"]:
            sys.exit(f"validate-contract: the pinned schema now has {_schema}.{_name}; drop it from PROPOSED")
        SCHEMAS[_schema]["properties"][_name] = _member
GOLDEN = {
    "start": "PlaybackStartBody",
    "replan": "PlaybackReplanBody",
    "progress": "PlaybackProgressBody",
    "stop": "PlaybackStopBody",
    "route-event": "PlaybackRouteEventBody",
    # The History page's removal (catalog.personal.removeHistory): the schema
    # alone, as the server adds no rule beyond it.
    "history-remove": "HistoryRemoveInputBody",
}
PLAYBACK = {"start", "replan", "progress", "stop", "route-event"}
REQUESTS = {
    "startPlayback": "PlaybackStartBody",
    "replanPlayback": "PlaybackReplanBody",
    "updatePlaybackProgress": "PlaybackProgressBody",
    "stopPlayback": "PlaybackStopBody",
    "reportPlaybackRouteEvent": "PlaybackRouteEventBody",
}
# Keywords the walker checks, and ones that only document a schema (format
# adds nothing here: every int64 and double member also has a type).
KEYWORDS = {"$ref", "type", "properties", "required", "additionalProperties", "items", "enum", "pattern",
            "minLength", "maxLength", "minimum", "maximum", "maxItems", "minItems", "maxProperties"}
ANNOTATIONS = {"description", "examples", "deprecated", "title", "format"}

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
ATTEMPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
EVIDENCE = {"exact", "platform_attested", "declared"}
NEVER_FEATURES = {"header_authenticated_media_v1", "authorized_media_origins_v1", "plan_invalidated_v1"}
NEVER_AUDIO = re.compile(r"^(truehd|mlp|dtshd|dts-hd|dts_hd|dtsx|dts:x|mat|pcm)$")
DELIVERIES = {"original_http", "progressive", "hls"}
DV8_CLAIM = "client_dv8_base_layer_fallback_v1"
FAILURE_OPERATIONS = {"failure_recovery", "seek_failure_recovery"}
INTENT_OPERATIONS = {"track_change", "quality_change", "output_change"}
# internal/api/handlers/playback_v3.go diagnosticKeysV3; other keys are dropped.
DIAGNOSTICS = {
    "decoder_name", "decoder_init_ms", "first_frame_ms", "device_model", "requested_quality", "effective_quality",
    "pcm_recovery", "retry_outcome", "replan_request_id", "video_mime", "video_codecs", "video_width", "video_height",
    "color_transfer", "color_range", "error_code", "error_code_name", "error_cause", "transformation_name",
    "transformation_version", "transformation_stage", "input_dv_profile", "output_dv_profile", "rpu_converted_count",
    "rpu_failed_count", "el_nal_dropped_count", "sample_count", "transform_buffer_peak_bytes", "requested_media_file_id",
    "effective_media_file_id", "audio_output_mode", "audio_mime", "audio_channels", "audio_decoder_name", "correction_id",
    "correction_stage", "network_transport", "network_metered", "network_validated", "bandwidth_estimate_kbps",
    "link_downstream_kbps", "target_source_position_seconds", "reason",
}


def json_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def walk(schema, value, path, errors):
    """Append every way value breaks schema to errors."""
    ref = schema.get("$ref")
    if ref is not None:
        prefix = "#/components/schemas/"
        if not ref.startswith(prefix) or ref[len(prefix):] not in SCHEMAS:
            errors.append(f"{path}: unresolved reference {ref}")
            return
        walk(SCHEMAS[ref[len(prefix):]], value, path, errors)
        return
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        errors.append(f"{path}: schema uses unsupported keywords {sorted(unknown)}")
        return

    actual = json_type(value)
    wanted = schema.get("type")
    if wanted is not None:
        allowed = set(wanted if isinstance(wanted, list) else [wanted])
        if "number" in allowed:
            allowed.add("integer")
        if actual not in allowed:
            errors.append(f"{path}: {actual} where {sorted(allowed)} is required")
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")

    if actual == "string":
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']}")
    elif actual in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above {schema['maximum']}")
    elif actual == "array":
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        for i, item in enumerate(value):
            if "items" in schema:
                walk(schema["items"], item, f"{path}[{i}]", errors)
    elif actual == "object":
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing required member {name}")
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            errors.append(f"{path}: more than {schema['maxProperties']} members")
        extra = schema.get("additionalProperties", True)
        for name, member in value.items():
            if name in properties:
                walk(properties[name], member, f"{path}.{name}", errors)
            elif extra is False:
                errors.append(f"{path}: unknown member {name}")
            elif isinstance(extra, dict):
                walk(extra, member, f"{path}.{name}", errors)


def hdr_problems(hdr, path):
    """protocol_v3.go validateHDRCapabilitiesV3."""
    errors = []
    if hdr is None:
        return errors
    profiles = set()
    for level in hdr.get("dolby_vision_profile_levels", []):
        if level["profile"] <= 0 or not 1 <= level["max_level"] <= 13:
            errors.append(f"{path}: invalid Dolby Vision profile level {level}")
        if level["profile"] in profiles:
            errors.append(f"{path}: duplicate Dolby Vision profile {level['profile']}")
        profiles.add(level["profile"])
        ids = level.get("bl_compatibility_ids", [])
        if len(set(ids)) != len(ids) or any(not 0 <= i <= 15 for i in ids):
            errors.append(f"{path}: invalid base-layer compatibility IDs {ids}")
    return errors


def server_problems(body, kind):
    """What the server rejects beyond the schema at the pinned commit."""
    errors = []
    context = body["client_playback_context"]
    caps = body["client_capabilities"]
    if body["protocol_version"] != 3 or context["protocol_version"] != 3:
        errors.append("protocol_version must be 3 on the body and on client_playback_context")
    if not UUID.match(body["installation_id"]) or set(body["installation_id"]) <= {"0", "-"}:
        errors.append("installation_id must be the canonical lowercase UUID from capabilities")
    if kind == "replan":
        errors += replan_problems(body)
    if kind == "start":
        if not ATTEMPT_ID.match(body["playback_attempt_id"]):
            errors.append("playback_attempt_id does not match the bounded identifier pattern")
        if not body["file_id"].isdigit() or int(body["file_id"]) <= 0:
            errors.append("file_id must be a positive integer in a string")
        if not body["profile_id"].strip():
            errors.append("profile_id is required")
        if body["subtitle_fidelity_preference"] not in ("preserve", "compatible"):
            errors.append("subtitle_fidelity_preference must be preserve or compatible")
        if "start_position" in body and not 0 <= body["start_position"] <= 31_536_000:
            errors.append("start_position is outside 0 to 31536000")
        for track in ("audio", "subtitle"):
            track_id, index = body.get(f"{track}_track_id"), body.get(f"{track}_track_index")
            if index is not None and not 0 <= index <= 10_000:
                errors.append(f"{track}_track_index is outside 0 to 10000")
            if track_id is not None and index is not None and track_id != f"file:{body['file_id']}:{track}:{index}":
                errors.append(f"{track}_track_id and {track}_track_index disagree")
    if caps["video_evidence"] not in EVIDENCE or caps["audio_evidence"] not in EVIDENCE:
        errors.append("video_evidence and audio_evidence must be exact, platform_attested, or declared")
    if len(body.get("client_features", [])) > 64:
        errors.append("more than 64 client_features")
    details = context["device"].get("platform_details", {})
    if len(details) > 16 or any(not k or len(k) > 128 or len(v) > 128 for k, v in details.items()):
        errors.append("platform_details exceeds 16 entries or 128 characters")
    output = context["output"]
    if len(output.get("output_context_id", "")) > 128:
        errors.append("output_context_id is longer than 128 characters")
    for name, hdr in (("client_capabilities.hdr_details", caps.get("hdr_details")), ("output.hdr_details", output.get("hdr_details"))):
        errors += hdr_problems(hdr, name)
    display = output.get("display")
    if display is not None:
        if display["hdr_evidence"] not in ("exact", "unknown"):
            errors.append("output.display.hdr_evidence must be exact or unknown")
        errors += hdr_problems(display.get("hdr_types"), "output.display.hdr_types")
        out = output.get("hdr_details")
        if display["hdr_evidence"] == "exact" and out is not None:
            panel = display.get("hdr_types") or {}
            for flag in ("hdr10", "hdr10_plus", "hlg"):
                if out.get(flag) and not panel.get(flag):
                    errors.append(f"output.hdr_details claims {flag}, which the exact display record does not carry")
            for profile in out.get("dolby_vision_profiles", []):
                if profile not in panel.get("dolby_vision_profiles", []):
                    errors.append(f"output.hdr_details claims Dolby Vision profile {profile} the display record does not carry")
            panel_levels = {level["profile"]: level["max_level"] for level in panel.get("dolby_vision_profile_levels", [])}
            for level in out.get("dolby_vision_profile_levels", []):
                if level["max_level"] > panel_levels.get(level["profile"], level["max_level"]):
                    errors.append(f"Dolby Vision profile {level['profile']} level exceeds the display record")
    for name, delivery in context["deliveries"].items():
        errors += hdr_problems(delivery.get("hdr_details"), f"deliveries.{name}.hdr_details")
        ids = delivery.get("dv8_base_layer_compatibility_ids", [])
        if len(set(ids)) != len(ids):
            errors.append(f"deliveries.{name}.dv8_base_layer_compatibility_ids repeats an ID")
    return errors


def replan_problems(body):
    """protocol_v3.go ReplanRequestV3.Validate."""
    errors = []
    for name in ("playback_attempt_id", "replan_request_id"):
        if not ATTEMPT_ID.match(body[name]):
            errors.append(f"{name} does not match the bounded identifier pattern")
    for name in ("failed_plan_id", "plan_attempt_id", "plan_attempt_key"):
        if not 8 <= len(body[name]) <= 128:
            errors.append(f"{name} must be 8 to 128 characters")
    keys = [body["plan_attempt_key"]] + body["attempted_plan_keys"]
    if any(not key.startswith("v3:") for key in keys):
        errors.append("plan attempt keys are the server's opaque v3: tokens")
    if not 0 <= body["position_seconds"] <= 31_536_000:
        errors.append("position_seconds is outside 0 to 31536000")
    for name in ("bandwidth_estimate_kbps", "bandwidth_cap_kbps"):
        if name in body and not 100 <= body[name] <= 1_000_000:
            errors.append(f"{name} is outside 100 to 1000000")
    if any(not m or len(m) > 64 for m in body.get("local_mutations", [])):
        errors.append("a local mutation is empty or longer than 64 characters")
    operation = body.get("operation")
    if operation in FAILURE_OPERATIONS and not body.get("failure", {}).get("classification"):
        errors.append(f"{operation} requires failure.classification")
    if operation in INTENT_OPERATIONS and "failure" in body:
        errors.append(f"{operation} must not include failure")
    if operation == "quality_change" and not body["quality_preference"].strip():
        errors.append("quality_change requires a quality_preference")
    return errors


def session_problems(body, kind):
    """internal/apiv2/playback.go and plan section 5 for progress, stop, and route events."""
    errors = []
    if not UUID.match(body["installation_id"]):
        errors.append("installation_id must be the canonical lowercase UUID from capabilities")
    if kind == "stop":
        if not UUID.match(body["stop_id"]):
            errors.append("stop_id must be a canonical lowercase UUID")
        if ("sequence" in body) != ("position" in body) or body.get("sequence", 1) == 0:
            errors.append("a final sample needs sequence and position together")
    if kind == "route-event":
        if not UUID.match(body["event_id"]):
            errors.append("event_id must be a canonical lowercase UUID")
        if not ATTEMPT_ID.match(body["playback_attempt_id"]):
            errors.append("playback_attempt_id does not match the bounded identifier pattern")
        if body["protocol_version"] != 3:
            errors.append("protocol_version must be 3")
        for key in set(body["diagnostics"]) - DIAGNOSTICS:
            errors.append(f"diagnostics.{key} is not on the server's allowlist")
        if body["event"] == "terminal" and "session_id" not in body and {"plan_id", "plan_attempt_id", "plan_attempt_key"} & set(body):
            errors.append("a terminal start is reported without plan identity")
    return errors


def client_problems(body):
    """Plan sections 5 and 6.1 and decision D-1."""
    errors = []
    context = body["client_playback_context"]
    caps = body["client_capabilities"]
    output = context["output"]
    for feature in set(body.get("client_features", [])) & NEVER_FEATURES:
        errors.append(f"client_features must not carry {feature} (signed-URL media mode, D-1)")
    if "metered" in body:
        errors.append("metered is deprecated and never sent")
    if "audio_passthrough" in caps or "audio_passthrough" in output:
        errors.append("audio_passthrough is never sent; probe results stay in local diagnostics")
    if caps["audio_evidence"] != "platform_attested":
        errors.append("audio_evidence is platform_attested: Roku cannot enumerate sink layouts")
    if set(context["deliveries"]) != DELIVERIES:
        errors.append(f"deliveries must be exactly {sorted(DELIVERIES)}")
    dv8_output = 8 in output.get("hdr_details", {}).get("dolby_vision_profiles", [])
    audio_lists = [("client_capabilities.codecs_audio", caps["codecs_audio"])]
    for name, delivery in context["deliveries"].items():
        where = f"deliveries.{name}"
        audio_lists.append((f"{where}.audio_decode_codecs", delivery["audio_decode_codecs"]))
        if delivery["audio_passthrough_codecs"]:
            errors.append(f"{where}.audio_passthrough_codecs must be empty")
        if "failure_reason" in delivery and delivery["enabled"] and delivery["supported_on_device"]:
            errors.append(f"{where}.failure_reason is only for a disabled class")
        if "hdr_details" in delivery and name not in ("original_http", "hls"):
            errors.append(f"{where}.hdr_details is sent only on original_http and hls")
        if name == "hls":
            # Omission inherits native output DV on the server. Keep the
            # explicit restriction across serialization without losing HDR.
            native_hdr = output.get("hdr_details", {})
            expected_hdr = {key: native_hdr.get(key, False) for key in ("hdr10", "hdr10_plus", "hlg")}
            expected_hdr["dolby_vision_profiles"] = []
            if delivery.get("hdr_details") != expected_hdr:
                errors.append(f"{where}.hdr_details must preserve output HDR with an explicit empty Dolby Vision profile list")
        if delivery.get("max_channels", 2) != 2:
            errors.append(f"{where}.max_channels is only the interim two-channel ceiling")
        if delivery["transformations"]:
            errors.append(f"{where} must not offer client transformations")
        for claim in delivery["validated_claims"]:
            if claim != DV8_CLAIM or name != "original_http":
                errors.append(f"{where}.validated_claims must not carry {claim}")
            elif dv8_output:
                errors.append(f"{DV8_CLAIM} is sent only when the output has no Dolby Vision profile 8")
        # An absent or empty list admits every standard base-layer ID.
        claimed = DV8_CLAIM in delivery["validated_claims"]
        if claimed and not delivery.get("dv8_base_layer_compatibility_ids"):
            errors.append(f"{DV8_CLAIM} is sent only with the base-layer IDs it covers")
        if "dv8_base_layer_compatibility_ids" in delivery and not claimed:
            errors.append(f"{where}.dv8_base_layer_compatibility_ids is sent only with {DV8_CLAIM}")
    for where, codecs in audio_lists:
        for codec in codecs:
            if NEVER_AUDIO.match(codec):
                errors.append(f"{where} must never claim {codec}")
    return errors


def problems(body, kind):
    errors = []
    walk({"$ref": f"#/components/schemas/{GOLDEN[kind]}"}, body, kind, errors)
    if errors or kind not in PLAYBACK:
        return errors
    if kind not in ("start", "replan"):
        return [f"server: {e}" for e in session_problems(body, kind)]
    return [f"server: {e}" for e in server_problems(body, kind)] + [f"client: {e}" for e in client_problems(body)]


def self_test(sample):
    """Each mutation of a valid start body must be rejected."""
    def mutate(change):
        body = copy.deepcopy(sample)
        change(body)
        return body

    cases = {
        "an unknown member": lambda b: b.update(bogus=True),
        "a missing required member": lambda b: b.pop("client_features"),
        "a string where an integer is required": lambda b: b.update(protocol_version="3"),
        "a float where an integer is required": lambda b: b["client_capabilities"]["video_decode"][0].update(max_width=1920.0),
        "an integer where a Boolean is required": lambda b: b["client_capabilities"].update(hdr=0),
        "an unknown nested member": lambda b: b["client_playback_context"]["output"].update(audio_passthrough_codecs=[]),
        "an empty file_id": lambda b: b.update(file_id=""),
        "an uppercase installation_id": lambda b: b.update(installation_id=b["installation_id"].upper()),
        "a bad playback_attempt_id": lambda b: b.update(playback_attempt_id="short"),
        "header-authenticated media": lambda b: b["client_features"].append("header_authenticated_media_v1"),
        "a passthrough codec": lambda b: b["client_playback_context"]["deliveries"]["hls"]["audio_passthrough_codecs"].append("eac3"),
        "truehd": lambda b: b["client_capabilities"]["codecs_audio"].append("truehd"),
        "a contradictory display record": lambda b: b["client_playback_context"]["output"].update(display={"hdr_evidence": "exact", "hdr_types": {"hdr10": False, "hdr10_plus": False, "hlg": False, "dolby_vision_profiles": []}}, hdr_details={"hdr10": True, "hdr10_plus": False, "hlg": False, "dolby_vision_profiles": []}),
        "metered": lambda b: b.update(metered=False),
        "a track index that disagrees with its ID": lambda b: b.update(audio_track_id=f"file:{b['file_id']}:audio:1", audio_track_index=2),
        "base-layer IDs without the claim": lambda b: b["client_playback_context"]["deliveries"]["hls"].update(dv8_base_layer_compatibility_ids=[1]),
        "a base-layer ID above 15": lambda b: b["client_playback_context"]["deliveries"]["original_http"].update(dv8_base_layer_compatibility_ids=[16]),
        "omitted HLS HDR restriction": lambda b: b["client_playback_context"]["deliveries"]["hls"].pop("hdr_details"),
        "HLS Dolby Vision claim": lambda b: b["client_playback_context"]["deliveries"]["hls"]["hdr_details"].update(dolby_vision_profiles=[8]),
        "HLS Dolby Vision level claim": lambda b: b["client_playback_context"]["deliveries"]["hls"]["hdr_details"].update(dolby_vision_profile_levels=[{"profile": 8, "max_level": 9}]),
        "changed HLS HDR10 support": lambda b: b["client_playback_context"]["deliveries"]["hls"]["hdr_details"].update(hdr10=not b["client_playback_context"]["output"]["hdr_details"]["hdr10"]),
        "changed HLS HLG support": lambda b: b["client_playback_context"]["deliveries"]["hls"]["hdr_details"].update(hlg=not b["client_playback_context"]["output"]["hdr_details"]["hlg"]),
    }
    failed = [name for name, change in cases.items() if not problems(mutate(change), "start")]
    session_cases = {
        "a stop sequence without a position": ("stop", {"installation_id": sample["installation_id"], "stop_id": "44444444-4444-4444-8444-444444444444", "sequence": 3}),
        "an uppercase stop_id": ("stop", {"installation_id": sample["installation_id"], "stop_id": "44444444-4444-4444-8444-44444444444A"}),
        "a progress sequence of 0": ("progress", {"installation_id": sample["installation_id"], "sequence": 0, "position": 1, "is_paused": False}),
        "an unlisted diagnostics key": ("route-event", {"installation_id": sample["installation_id"], "event_id": "55555555-5555-4555-8555-555555555555", "protocol_version": 3, "playback_attempt_id": "attempt-0123456789", "event": "first_frame", "diagnostics": {"bogus": "1"}}),
    }
    failed += [name for name, (kind, body) in session_cases.items() if not problems(body, kind)]
    replan_errors = []
    walk({"$ref": "#/components/schemas/PlaybackReplanBody"}, {"operation": "rewind"}, "replan", replan_errors)
    if not any("not one of" in e for e in replan_errors):
        failed.append("an unknown replan operation")
    return failed


def main():
    failures = 0
    goldens = []
    for kind in GOLDEN:
        for path in sorted((FIXTURES / "golden" / kind).glob("*.json")):
            body = json.loads(path.read_text())
            goldens.append((path, kind, body))
    if not goldens:
        print("validate-contract: no goldens under tests/fixtures/golden/", file=sys.stderr)
        return 1
    for path, kind, body in goldens:
        errors = problems(body, kind)
        name = path.relative_to(ROOT)
        if errors:
            failures += 1
            print(f"FAIL {name}", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
        else:
            print(f"ok   {name} ({GOLDEN[kind]})")

    for entry in json.loads((FIXTURES / "v2" / "index.json").read_text())["fixtures"]:
        schema = REQUESTS.get(entry["operation_id"])
        if schema is None or "body" not in entry["request"]:
            continue
        errors = []
        walk({"$ref": f"#/components/schemas/{schema}"}, json.loads(entry["request"]["body"]), schema, errors)
        if errors:
            failures += 1
            print(f"FAIL server fixture {entry['name']}: {errors}", file=sys.stderr)

    start = next(body for _, kind, body in goldens if kind == "start")
    missed = self_test(start)
    if missed:
        failures += 1
        print(f"FAIL self-test: accepted {', '.join(missed)}", file=sys.stderr)

    if failures:
        return 1
    print(f"validate-contract: {len(goldens)} goldens and the server's request fixtures match the contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
