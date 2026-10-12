from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable

from chat_review.common import ContractError, canonical_json, read_json, resolve_inside, sha256_bytes, sha256_file


CALIBRATION_MATCHING_PROMPT = "calibration_spec_snapshot/prompts/calibration_matching_v1.md"
CALIBRATION_DESCRIPTION_PROMPT = "calibration_spec_snapshot/prompts/calibration_description_v1.md"
PROVENANCE_COLUMNS = {
    "study_kind": "string",
    "controlled_study_eligible": "bool",
    "counts_toward_adaptive_update": "bool",
    "prompt_sha256": "string",
    "description_prompt_sha256": "string",
    "calibration_metadata_sha256": "string",
}


def _requires_calibration_metadata(run: dict[str, Any], groups: Iterable[dict[str, Any]]) -> bool:
    conditions = [*run.get("conditions", []), *(group.get("condition", "") for group in groups)]
    return run.get("study_kind") == "real_data_calibration" or any(
        str(condition).startswith("calibration_") for condition in conditions
    )


def _run_provenance(
    run: dict[str, Any], groups: list[dict[str, Any]], provenance: dict[str, Any] | None,
) -> dict[str, Any]:
    calibration_required = _requires_calibration_metadata(run, groups)
    if provenance is not None and (calibration_required or provenance.get("study_kind") == "real_data_calibration"):
        if (
            provenance.get("study_kind") != "real_data_calibration"
            or provenance.get("controlled_study_eligible") is not False
            or provenance.get("counts_toward_adaptive_update") is not False
        ):
            raise ContractError("calibration data cannot use controlled-study provenance")
        return provenance
    if calibration_required:
        raise ContractError("calibration metadata must be loaded and verified before building export rows")
    for field in ("controlled_study_eligible", "counts_toward_adaptive_update"):
        if field in run and not isinstance(run[field], bool):
            raise ContractError(f"run.{field} must be an explicit boolean")
    # A frozen prompt or a fixed/adaptive condition does not establish study eligibility.
    explicit_eligibility = run.get("controlled_study_eligible") is True
    study_kind = run.get("study_kind", "controlled_study" if explicit_eligibility else "legacy_unspecified")
    hashes = {item["path"]: item["sha256"] for item in run.get("spec_snapshot", [])}
    declared = {
        "study_kind": study_kind,
        "controlled_study_eligible": explicit_eligibility and study_kind == "controlled_study",
        # There is no group condition at run level; only condition-linked rows can qualify.
        "counts_toward_adaptive_update": False,
        "prompt_sha256": hashes.get("prompts/proposer_fixed_hidden_v1.md", ""),
        "description_prompt_sha256": "",
        "calibration_metadata_sha256": "",
    }
    if provenance is not None and provenance != declared:
        raise ContractError("export provenance disagrees with explicit run eligibility")
    return declared


def _group_provenance(
    run: dict[str, Any], group: dict[str, Any], provenance: dict[str, Any],
) -> dict[str, Any]:
    condition = group.get("condition", "")
    return {
        **provenance,
        "counts_toward_adaptive_update": (
            provenance["controlled_study_eligible"] is True
            and condition in {"adaptive_hidden", "adaptive_visible"}
            and condition in run.get("conditions", [])
            and run.get("counts_toward_adaptive_update", True) is True
        ),
    }


def load_export_provenance(
    run_dir: Path, run: dict[str, Any], groups: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify frozen calibration inputs without modifying the run or its records."""
    metadata_path = run_dir / "calibration.json"
    if not metadata_path.is_file():
        if _requires_calibration_metadata(run, groups):
            raise ContractError("calibration data requires calibration.json")
        return _run_provenance(run, groups, None)
    content = metadata_path.read_bytes()
    try:
        calibration = json.loads(content)
    except (ValueError, UnicodeError) as exc:
        raise ContractError("invalid calibration.json") from exc
    if not isinstance(calibration, dict) or (
        calibration.get("study_kind") != "real_data_calibration"
        or calibration.get("controlled_study_eligible") is not False
        or calibration.get("counts_toward_adaptive_update") is not False
    ):
        raise ContractError("calibration.json must exclude calibration from controlled study and adaptive counters")
    for key, expected in (("run_id", run["run_id"]), ("seed", run["seed"]), ("held_out_domain", run.get("target_domain"))):
        if key in calibration and calibration[key] != expected:
            raise ContractError(f"calibration.json {key} disagrees with run.json")
    snapshots = calibration.get("extra_spec_snapshots")
    if not isinstance(snapshots, list):
        raise ContractError("calibration.json requires extra_spec_snapshots")
    hashes: dict[str, str] = {}
    for item in snapshots:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item.get("sha256"):
            raise ContractError("invalid calibration snapshot fingerprint")
        relative = item["path"]
        if relative in hashes:
            raise ContractError(f"duplicate calibration snapshot: {relative}")
        snapshot = resolve_inside(run_dir, relative)
        if not snapshot.is_file() or sha256_file(snapshot) != item["sha256"]:
            raise ContractError(f"missing or modified frozen calibration snapshot: {relative}")
        if "bytes" in item and snapshot.stat().st_size != item["bytes"]:
            raise ContractError(f"frozen calibration snapshot size mismatch: {relative}")
        hashes[relative] = item["sha256"]
    for required in (CALIBRATION_MATCHING_PROMPT, CALIBRATION_DESCRIPTION_PROMPT):
        if required not in hashes:
            raise ContractError(f"missing frozen calibration prompt fingerprint: {required}")
    return {
        "study_kind": "real_data_calibration",
        "controlled_study_eligible": False,
        "counts_toward_adaptive_update": False,
        "prompt_sha256": hashes[CALIBRATION_MATCHING_PROMPT],
        "description_prompt_sha256": hashes[CALIBRATION_DESCRIPTION_PROMPT],
        "calibration_metadata_sha256": sha256_bytes(content),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_hash_chain(records: list[dict[str, Any]]) -> None:
    previous: str | None = None
    for index, row in enumerate(records, start=1):
        if row.get("previous_record_hash") != previous:
            raise ContractError(f"review ledger chain is broken at row {index}")
        stored = row.get("record_hash")
        unhashed = dict(row)
        unhashed.pop("record_hash", None)
        calculated = sha256_bytes(canonical_json(unhashed))
        if stored != calculated:
            raise ContractError(f"review ledger hash mismatch at row {index}")
        previous = stored


def confirmed_reviews(records: list[dict[str, Any]], stage: str) -> dict[str, dict[str, Any]]:
    validate_hash_chain(records)
    confirmed_ids = {
        row["confirms_event_id"]
        for row in records
        if row.get("record_type") == "confirmation" and row.get("confirms_event_id")
    }
    candidates = [
        row for row in records
        if row.get("record_type", "review") == "review"
        and row.get("event_id") in confirmed_ids
        and row.get("stage") == stage
    ]
    superseded = {row.get("supersedes_event_id") for row in candidates if row.get("supersedes_event_id")}
    active = [row for row in candidates if row.get("event_id") not in superseded]
    by_group: dict[str, dict[str, Any]] = {}
    for row in active:
        group_id = row.get("group_id")
        if group_id in by_group:
            raise ContractError(f"multiple active confirmed {stage} reviews for group {group_id}; use supersedes_event_id")
        by_group[group_id] = row
    return by_group


def image_payload(pacs_root: Path, image: dict[str, Any]) -> tuple[dict[str, Any], str]:
    path = resolve_inside(pacs_root, str(image.get("file", "")))
    if not path.is_file():
        raise FileNotFoundError(f"pair image is missing: {path}")
    content = path.read_bytes()
    return {"bytes": content, "path": path.name}, sha256_bytes(content)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def build_pair_rows(
    *,
    run: dict[str, Any],
    groups: list[dict[str, Any]],
    reviews: dict[str, dict[str, Any]],
    pacs_root: Path,
    provenance: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    provenance = _run_provenance(run, groups, provenance)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    spec_hashes = {item["path"]: item["sha256"] for item in run.get("spec_snapshot", [])}
    pair_spec_hash = spec_hashes.get("specs/pair_definition.md", "")
    expected_split = run["proposal_split"]
    target_domain = run.get("target_domain")

    for group in groups:
        group_provenance = _group_provenance(run, group, provenance)
        group_id = group.get("group_id")
        review = reviews.get(group_id)
        if review is None:
            continue
        receipt = {row["pair_id"]: row for row in review.get("derived_pair_receipt", [])}
        for pair in group.get("pairs", []):
            pair_id = pair.get("pair_id")
            decision = receipt.get(pair_id)
            if decision is None or decision.get("verdict") != "accept":
                continue
            scope = decision.get("validation_scope")
            if scope not in {"individual", "group_scan"}:
                continue
            if pair_id in seen:
                raise ContractError(f"pair ID appears more than once in export: {pair_id}")
            seen.add(pair_id)
            anchor = pair.get("anchor", {})
            candidate = pair.get("candidate", {})
            for role, image in (("anchor", anchor), ("candidate", candidate)):
                if image.get("split", expected_split) != expected_split:
                    raise ContractError(f"{pair_id} {role} is outside proposal split {expected_split}")
                if target_domain and image.get("domain") == target_domain:
                    raise ContractError(f"{pair_id} {role} leaks held-out target domain {target_domain}")
            if anchor.get("class") != candidate.get("class"):
                raise ContractError(f"{pair_id} has inconsistent manifest classes")
            if not isinstance(pair.get("target_count"), int) or pair["target_count"] < 1:
                raise ContractError(f"{pair_id} is missing a positive, visually verified target_count")
            if not str(pair.get("activity_pose_state", "")).strip():
                raise ContractError(f"{pair_id} is missing activity_pose_state")
            if not pair.get("spurious_axes"):
                raise ContractError(f"{pair_id} has no recorded spurious axis")
            anchor_image, anchor_hash = image_payload(pacs_root, anchor)
            paired_image, paired_hash = image_payload(pacs_root, candidate)
            rows.append(
                {
                    **group_provenance,
                    "pair_id": pair_id,
                    "run_id": run["run_id"],
                    "group_id": group_id,
                    "condition": group.get("condition", ""),
                    "judgment_stage": review["stage"],
                    "validation_scope": scope,
                    "eligible_strict": scope == "individual",
                    "eligible_broad": True,
                    "reviewer_id": review["reviewer_id"],
                    "review_event_id": review["event_id"],
                    "group_coverage_verdict": review.get("coverage", ""),
                    "review_comment": _text(review.get("comment")),
                    "pair_review_comment": _text(decision.get("comment")),
                    "anchor_id": anchor.get("id", ""),
                    "paired_id": candidate.get("id", ""),
                    "object_class": anchor.get("class", ""),
                    "anchor_domain": anchor.get("domain", ""),
                    "paired_domain": candidate.get("domain", ""),
                    "proposal_split": expected_split,
                    "target_count": int(pair["target_count"]),
                    "activity_pose_state": _text(pair.get("activity_pose_state")),
                    "semantic_rationale": _text(pair.get("semantic_rationale")),
                    "spurious_axes": [str(value) for value in pair.get("spurious_axes", [])],
                    "spurious_rationale": _text(pair.get("spurious_rationale")),
                    "uncertainty": _text(pair.get("uncertainty")),
                    "proposer_confidence": float(pair.get("confidence")) if pair.get("confidence") is not None else -1.0,
                    "proposal_model": run["model"],
                    "reasoning_effort": run["reasoning_effort"],
                    "seed": int(run["seed"]),
                    "manifest_sha256": run["manifest"]["sha256"],
                    "pair_spec_sha256": pair_spec_hash,
                    "anchor_sha256": anchor_hash,
                    "paired_sha256": paired_hash,
                    "anchor_image": anchor_image,
                    "paired_image": paired_image,
                }
            )
    return rows


def pair_features():
    from datasets import Features, Image, Sequence, Value

    return Features(
        {
            **{name: Value(kind) for name, kind in PROVENANCE_COLUMNS.items()},
            "pair_id": Value("string"), "run_id": Value("string"), "group_id": Value("string"),
            "condition": Value("string"), "judgment_stage": Value("string"), "validation_scope": Value("string"),
            "eligible_strict": Value("bool"), "eligible_broad": Value("bool"), "reviewer_id": Value("string"),
            "review_event_id": Value("string"), "group_coverage_verdict": Value("string"),
            "review_comment": Value("string"), "pair_review_comment": Value("string"),
            "anchor_id": Value("string"), "paired_id": Value("string"), "object_class": Value("string"),
            "anchor_domain": Value("string"), "paired_domain": Value("string"), "proposal_split": Value("string"),
            "target_count": Value("int32"), "activity_pose_state": Value("string"),
            "semantic_rationale": Value("string"), "spurious_axes": Sequence(Value("string")),
            "spurious_rationale": Value("string"), "uncertainty": Value("string"),
            "proposer_confidence": Value("float64"), "proposal_model": Value("string"),
            "reasoning_effort": Value("string"), "seed": Value("int64"),
            "manifest_sha256": Value("string"), "pair_spec_sha256": Value("string"),
            "anchor_sha256": Value("string"), "paired_sha256": Value("string"),
            "anchor_image": Image(decode=False), "paired_image": Image(decode=False),
        }
    )


def simple_features(columns: dict[str, str]):
    from datasets import Features, Value

    return Features({name: Value(kind) for name, kind in columns.items()})


def write_table(rows: list[dict[str, Any]], features: Any, path: Path) -> None:
    from datasets import Dataset

    if rows:
        dataset = Dataset.from_list(rows, features=features)
    else:
        dataset = Dataset.from_dict({name: [] for name in features}, features=features)
    dataset.to_parquet(str(path))


def group_tables(
    run: dict[str, Any],
    groups: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
    descriptions: list[dict[str, Any]],
    provenance: dict[str, Any] | None = None,
) -> dict[str, tuple[list[dict[str, Any]], Any]]:
    provenance = _run_provenance(run, groups, provenance)
    provenance_by_group = {
        group["group_id"]: _group_provenance(run, group, provenance)
        for group in groups if group.get("group_id")
    }
    group_rows = []
    member_rows = []
    proposal_rows = []
    for group in groups:
        pairs = group.get("pairs", [])
        group_rows.append(
            {
                "group_id": group.get("group_id", ""), "run_id": run["run_id"],
                "condition": group.get("condition", ""), "pair_count": len(pairs),
                "semantic_claim": _text(group.get("semantic_claim")),
                "coverage_summary_json": json.dumps(group.get("coverage_summary", {}), sort_keys=True),
                "reasons_group_may_fail_json": json.dumps(group.get("reasons_group_may_fail", [])),
                "raw_group_json": json.dumps(group, sort_keys=True),
            }
        )
        for position, pair in enumerate(pairs, start=1):
            member_rows.append(
                {"group_id": group.get("group_id", ""), "pair_id": pair.get("pair_id", ""),
                 "position": int(pair.get("position", position)),
                 "highlighted_roles_json": json.dumps(pair.get("highlighted_roles", []))}
            )
            proposal_rows.append(
                {"pair_id": pair.get("pair_id", ""), "group_id": group.get("group_id", ""),
                 "condition": group.get("condition", ""), "decision": "select",
                 "confidence": float(pair.get("confidence")) if pair.get("confidence") is not None else -1.0,
                 "semantic_rationale": _text(pair.get("semantic_rationale")),
                 "spurious_rationale": _text(pair.get("spurious_rationale")),
                 "uncertainty": _text(pair.get("uncertainty")), "raw_pair_json": json.dumps(pair, sort_keys=True)}
            )
    confirmed = {row.get("confirms_event_id") for row in ledger if row.get("record_type") == "confirmation"}
    judgment_rows = [
        {
            "record_type": row.get("record_type", "review"), "event_id": row.get("event_id", ""),
            "group_id": row.get("group_id", ""), "reviewer_id": row.get("reviewer_id", ""),
            "stage": row.get("stage", ""), "pair_validity": row.get("pair_validity", ""),
            "coverage": row.get("coverage", ""), "recorded_at": row.get("recorded_at", ""),
            "confirmed": row.get("event_id") in confirmed or row.get("record_type") == "confirmation",
            "raw_response": row.get("raw_response", ""), "parsed_json": json.dumps(row, sort_keys=True),
            "record_hash": row.get("record_hash", ""), "previous_record_hash": row.get("previous_record_hash") or "",
        }
        for row in ledger
    ]
    description_rows = [
        {
            "image_id": row.get("image_id", ""),
            "image_alias": row.get("image_alias", ""),
            "description_version": row.get("description_version", ""),
            "structured_json": json.dumps(row.get("description", row.get("structured", {})), sort_keys=True),
            "raw_output_ref": row.get("raw_output_ref", ""),
        }
        for row in descriptions
    ]
    tables = {
        "groups": (group_rows, simple_features({"group_id":"string", "run_id":"string", "condition":"string", "pair_count":"int32", "semantic_claim":"string", "coverage_summary_json":"string", "reasons_group_may_fail_json":"string", "raw_group_json":"string"})),
        "group_members": (member_rows, simple_features({"group_id":"string", "pair_id":"string", "position":"int32", "highlighted_roles_json":"string"})),
        "proposal_ledger": (proposal_rows, simple_features({"pair_id":"string", "group_id":"string", "condition":"string", "decision":"string", "confidence":"float64", "semantic_rationale":"string", "spurious_rationale":"string", "uncertainty":"string", "raw_pair_json":"string"})),
        "judgments": (judgment_rows, simple_features({"record_type":"string", "event_id":"string", "group_id":"string", "reviewer_id":"string", "stage":"string", "pair_validity":"string", "coverage":"string", "recorded_at":"string", "confirmed":"bool", "raw_response":"string", "parsed_json":"string", "record_hash":"string", "previous_record_hash":"string"})),
        "image_descriptions": (description_rows, simple_features({"image_id":"string", "image_alias":"string", "description_version":"string", "structured_json":"string", "raw_output_ref":"string"})),
    }
    for name, (table_rows, features) in tables.items():
        features.update(simple_features(PROVENANCE_COLUMNS))
        tables[name] = ([{**row, **provenance_by_group.get(row.get("group_id"), provenance)} for row in table_rows], features)
    return tables


def dataset_card() -> str:
    return """---
configs:
- config_name: pairs
  data_files:
  - split: train
    path: invariant_pairs.parquet
- config_name: grit_strict
  data_files:
  - split: train
    path: grit_strict.parquet
- config_name: grit_broad
  data_files:
  - split: train
    path: grit_broad.parquet
- config_name: groups
  data_files:
  - split: train
    path: groups.parquet
- config_name: group_members
  data_files:
  - split: train
    path: group_members.parquet
- config_name: judgments
  data_files:
  - split: train
    path: judgments.parquet
- config_name: proposal_ledger
  data_files:
  - split: train
    path: proposal_ledger.parquet
- config_name: image_descriptions
  data_files:
  - split: train
    path: image_descriptions.parquet
---

# PACS grouped invariant pairs

One row per accepted pair. `anchor_image` and `paired_image` are embedded for the Hugging Face viewer. The strict GRIT table contains individually reviewed pairs. The broad experimental table additionally contains pairs explicitly covered by a full-contact-sheet group scan. Group, proposal, judgment, and description provenance are normalized into separate configs. JSON-valued provenance uses strings to avoid empty-struct Parquet failures.

Study eligibility is separate from review scope: `eligible_strict` and `eligible_broad` describe inspection only. Filter on `controlled_study_eligible` for controlled-study data and on `counts_toward_adaptive_update` before computing adaptive counters. Real-data calibration has `study_kind=real_data_calibration` and both flags false, even after human acceptance. `prompt_sha256` identifies the matching prompt; `description_prompt_sha256` identifies the independent description prompt when available (blank for legacy runs). See `validation_report.json` for this export's provenance and separate calibration/controlled pair counts. These counts are export totals, not adaptive-update progress.

Runs without an explicit eligibility declaration default to `study_kind=legacy_unspecified` and `controlled_study_eligible=false`; a prompt snapshot, condition name, or accepted smoke fixture does not establish scientific eligibility. An explicit boolean `controlled_study_eligible=true` establishes eligibility only for `study_kind=controlled_study` (the kind inferred when that explicit flag is supplied alone). Adaptive eligibility is computed per group: only declared `adaptive_hidden`/`adaptive_visible` groups in an eligible controlled run can qualify, and an explicit run-level `counts_toward_adaptive_update=false` vetoes it. Fixed, calibration, legacy-unknown, and rows without a group condition never qualify for adaptive counters. The run-level provenance summary has no group condition and therefore keeps its adaptive flag false; use row flags and the separate pair totals.
"""


def export_run(run_dir: Path, groups_dir: Path, pacs_root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"versioned export directory already exists: {output_dir}")
    run = read_json(run_dir / "run.json")
    ledger = read_jsonl(run_dir / "records" / "reviews.jsonl")
    descriptions = read_jsonl(run_dir / "records" / "image_descriptions.jsonl")
    groups = [read_json(path) for path in sorted(groups_dir.glob("*.json"))]
    provenance = load_export_provenance(run_dir, run, groups)
    if not groups:
        raise ContractError(f"no group JSON files found in {groups_dir}")
    stage = run["judgment_stage_for_export"]
    reviews = confirmed_reviews(ledger, stage)
    rows = build_pair_rows(run=run, groups=groups, reviews=reviews, pacs_root=pacs_root, provenance=provenance)
    if not rows:
        raise ContractError(f"no confirmed accepted {stage} pairs qualify for broad export")

    described_ids = {row.get("image_id") for row in descriptions}
    required_ids = {row["anchor_id"] for row in rows} | {row["paired_id"] for row in rows}
    missing_descriptions = sorted(required_ids.difference(described_ids))
    if missing_descriptions:
        preview = ", ".join(missing_descriptions[:5])
        raise ContractError(f"accepted pair images are missing frozen descriptions ({len(missing_descriptions)}): {preview}")

    output_dir.mkdir(parents=True)
    all_features = pair_features()
    write_table(rows, all_features, output_dir / "invariant_pairs.parquet")
    write_table([row for row in rows if row["eligible_strict"]], all_features, output_dir / "grit_strict.parquet")
    write_table(rows, all_features, output_dir / "grit_broad.parquet")
    for name, (table_rows, features) in group_tables(run, groups, ledger, descriptions, provenance).items():
        write_table(table_rows, features, output_dir / f"{name}.parquet")
    (output_dir / "README.md").write_text(dataset_card(), encoding="utf-8")
    with (output_dir / "invariant_pairs_metadata.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            metadata = {key: value for key, value in row.items() if key not in {"anchor_image", "paired_image"}}
            handle.write(json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n")
    report = validate_export(output_dir, len(rows), sum(row["eligible_strict"] for row in rows))
    report["provenance"] = provenance
    report["pair_counts"] = {
        "total": len(rows),
        "calibration": sum(row["study_kind"] == "real_data_calibration" for row in rows),
        "controlled_study_eligible": sum(row["controlled_study_eligible"] for row in rows),
        "adaptive_update_eligible": sum(row["counts_toward_adaptive_update"] for row in rows),
    }
    (output_dir / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def validate_export(output_dir: Path, broad_count: int, strict_count: int) -> dict[str, Any]:
    from datasets import Dataset

    expected = {"invariant_pairs.parquet": broad_count, "grit_broad.parquet": broad_count, "grit_strict.parquet": strict_count}
    results = {}
    with tempfile.TemporaryDirectory(prefix="hfv-") as temp:
        validation_root = Path(temp)
        cache = validation_root / "cache"
        for name, count in expected.items():
            local_copy = validation_root / name
            shutil.copyfile(output_dir / name, local_copy)
            dataset = Dataset.from_parquet(str(local_copy), cache_dir=str(cache))
            if len(dataset) != count:
                raise ContractError(f"reload row count mismatch for {name}: expected {count}, got {len(dataset)}")
            if count and not {"anchor_image", "paired_image", "anchor_id", "paired_id"}.issubset(dataset.column_names):
                raise ContractError(f"required pair columns missing after reload: {name}")
            results[name] = {"rows": len(dataset), "columns": len(dataset.column_names), "sha256": sha256_file(output_dir / name)}
        for name in ("groups", "group_members", "judgments", "proposal_ledger", "image_descriptions"):
            local_copy = validation_root / f"{name}.parquet"
            shutil.copyfile(output_dir / f"{name}.parquet", local_copy)
            dataset = Dataset.from_parquet(str(local_copy), cache_dir=str(cache))
            results[f"{name}.parquet"] = {"rows": len(dataset), "columns": len(dataset.column_names), "sha256": sha256_file(output_dir / f"{name}.parquet")}
    return {"status": "passed", "checks": ["datasets_reload", "row_counts", "required_pair_columns", "nonempty_explicit_features"], "files": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a confirmed grouped-review run to versioned Hugging Face Parquet files.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--groups-dir", type=Path)
    parser.add_argument("--pacs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    groups_dir = args.groups_dir or args.run_dir / "records" / "groups"
    report = export_run(args.run_dir, groups_dir, args.pacs_root, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
