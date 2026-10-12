from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from chat_review.common import ContractError, atomic_write_bytes, canonical_json, read_json, sha256_bytes, utc_now


INSPECTION_MODES = {
    "highlighted_only",
    "highlighted_and_full_contact_sheet",
    "full_contact_sheet_no_focused_inspection",
    "explicit_pair_ids",
}
VERDICTS = {"accept", "reject", "unsure"}
GROUP_VERDICTS = {"accept", "reject", "unsure", "accept_with_exclusions"}
COVERAGE_VERDICTS = {"adequate", "redundant", "incomplete", "unsure"}


def derive_pair_receipt(group: dict[str, Any], event: dict[str, Any]) -> list[dict[str, str]]:
    pairs = group.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ContractError("group.pairs must be a non-empty array")
    pair_ids = [pair.get("pair_id") for pair in pairs]
    if any(not isinstance(pair_id, str) for pair_id in pair_ids) or len(set(pair_ids)) != len(pair_ids):
        raise ContractError("group pair IDs must be non-empty and unique")

    inspection = event.get("inspection", {})
    mode = inspection.get("mode")
    if mode not in INSPECTION_MODES:
        raise ContractError(f"inspection.mode must be one of {sorted(INSPECTION_MODES)}")
    explicit_ids = set(inspection.get("pair_ids", []))
    highlighted = {
        pair["pair_id"]
        for pair in pairs
        if pair.get("highlighted_roles")
    }
    focused: set[str] = set()
    full_scan = mode in {"highlighted_and_full_contact_sheet", "full_contact_sheet_no_focused_inspection"}
    if mode in {"highlighted_only", "highlighted_and_full_contact_sheet"}:
        focused.update(highlighted)
    if mode == "explicit_pair_ids":
        focused.update(explicit_ids)

    overrides: dict[str, dict[str, Any]] = {}
    for key in ("exceptions", "pair_comments"):
        for item in event.get(key, []):
            pair_id = item.get("pair_id")
            if pair_id not in pair_ids:
                raise ContractError(f"review references unknown pair ID: {pair_id!r}")
            if key == "exceptions" or item.get("establishes_individual_review") is True:
                focused.add(pair_id)
            overrides.setdefault(pair_id, {}).update(item)
    unknown_focused = focused.difference(pair_ids)
    if unknown_focused:
        raise ContractError(f"inspection references unknown pair IDs: {sorted(unknown_focused)}")

    group_verdict = event.get("pair_validity")
    if group_verdict not in GROUP_VERDICTS:
        raise ContractError(f"pair_validity must be one of {sorted(GROUP_VERDICTS)}")
    default_verdict = "accept" if group_verdict in {"accept", "accept_with_exclusions"} else group_verdict

    receipt: list[dict[str, str]] = []
    for pair_id in pair_ids:
        override = overrides.get(pair_id, {})
        verdict = override.get("verdict", default_verdict)
        if verdict not in VERDICTS:
            raise ContractError(f"pair override verdict must be one of {sorted(VERDICTS)}")
        if pair_id in focused:
            scope = "individual"
        elif full_scan:
            scope = "group_scan"
        else:
            scope = "unreviewed"
        receipt.append(
            {
                "pair_id": pair_id,
                "verdict": verdict,
                "validation_scope": scope,
                "comment": str(override.get("comment", "")),
            }
        )
    return receipt


def normalize_event(group: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    required = ("event_id", "reviewer_id", "stage", "pair_validity", "coverage", "raw_response")
    missing = [key for key in required if not event.get(key)]
    if missing:
        raise ContractError(f"review event missing required fields: {', '.join(missing)}")
    if event["stage"] not in {"initial", "revised"}:
        raise ContractError("stage must be initial or revised")
    if event["coverage"] not in COVERAGE_VERDICTS:
        raise ContractError(f"coverage must be one of {sorted(COVERAGE_VERDICTS)}")

    normalized = dict(event)
    normalized["schema_version"] = 1
    normalized["group_id"] = group.get("group_id")
    normalized.setdefault("recorded_at", utc_now())
    normalized["derived_pair_receipt"] = derive_pair_receipt(group, normalized)
    return normalized


def append_event(ledger_path: Path, group: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_event(group, event)
    existing: list[dict[str, Any]] = []
    if ledger_path.exists():
        with ledger_path.open("r", encoding="utf-8") as handle:
            existing = [json.loads(line) for line in handle if line.strip()]
    if any(row.get("event_id") == normalized["event_id"] for row in existing):
        raise ContractError(f"duplicate review event ID: {normalized['event_id']}")
    previous_hash = existing[-1]["record_hash"] if existing else None
    normalized["previous_record_hash"] = previous_hash
    normalized["record_hash"] = sha256_bytes(canonical_json(normalized))
    payload = b"".join(canonical_json(row) + b"\n" for row in [*existing, normalized])
    atomic_write_bytes(ledger_path, payload)
    return normalized


def confirm_event(ledger_path: Path, target_event_id: str, reviewer_id: str, raw_response: str) -> dict[str, Any]:
    if not ledger_path.exists():
        raise ContractError("cannot confirm an event before the review ledger exists")
    with ledger_path.open("r", encoding="utf-8") as handle:
        existing = [json.loads(line) for line in handle if line.strip()]
    targets = [row for row in existing if row.get("event_id") == target_event_id and row.get("record_type", "review") == "review"]
    if len(targets) != 1:
        raise ContractError(f"review event to confirm was not found exactly once: {target_event_id}")
    if any(row.get("record_type") == "confirmation" and row.get("confirms_event_id") == target_event_id for row in existing):
        raise ContractError(f"review event is already confirmed: {target_event_id}")
    confirmation = {
        "schema_version": 1,
        "record_type": "confirmation",
        "event_id": f"confirm:{target_event_id}",
        "confirms_event_id": target_event_id,
        "reviewer_id": reviewer_id,
        "raw_response": raw_response,
        "recorded_at": utc_now(),
        "previous_record_hash": existing[-1]["record_hash"],
    }
    confirmation["record_hash"] = sha256_bytes(canonical_json(confirmation))
    payload = b"".join(canonical_json(row) + b"\n" for row in [*existing, confirmation])
    atomic_write_bytes(ledger_path, payload)
    return confirmation


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and append a chat review event.")
    parser.add_argument("--group", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--event", type=Path)
    action.add_argument("--confirm-event-id")
    parser.add_argument("--reviewer-id")
    parser.add_argument("--confirmation-response", default="confirm")
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    if args.event:
        event = read_json(args.event)
        event.setdefault("record_type", "review")
        result = append_event(args.ledger, read_json(args.group), event)
        print(json.dumps({"event_id": result["event_id"], "status": "pending_confirmation", "receipt": result["derived_pair_receipt"]}, indent=2))
    else:
        if not args.reviewer_id:
            parser.error("--reviewer-id is required with --confirm-event-id")
        result = confirm_event(args.ledger, args.confirm_event_id, args.reviewer_id, args.confirmation_response)
        print(json.dumps({"event_id": result["event_id"], "status": "confirmed", "confirms": result["confirms_event_id"]}, indent=2))


if __name__ == "__main__":
    main()
