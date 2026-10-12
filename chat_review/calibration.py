"""Freeze independent observations and publish a reviewed-by-model calibration proposal.

These commands never create human judgments. Pixel inspection and its concise evidence
must be supplied by the coordinator; schema validation cannot establish semantic truth.
"""
from __future__ import annotations

import argparse
import html
import json
import random
from pathlib import Path

import jsonschema
import numpy as np
from PIL import Image

from chat_review.common import (
    ContractError, atomic_write_json, fingerprint, read_json, resolve_inside,
    sha256_bytes, sha256_file, utc_now, write_jsonl,
)
from chat_review.html_report import build_report, validate_domain_selection


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require_hash(path: Path, expected: str) -> None:
    if sha256_file(path) != expected:
        raise ContractError(f"frozen input changed: {path}")


def inputs(run: Path) -> tuple[dict, dict, dict[str, dict]]:
    config = read_json(run / "run.json")
    calibration = read_json(run / "calibration.json")
    if config["conditions"] != ["calibration_visible"] or calibration["controlled_study_eligible"]:
        raise ContractError("this command is only for explicitly labeled calibration runs")
    require_hash(run / "inputs/candidate_pool.jsonl", config["candidate_pool"]["sha256"])
    require_hash(run / "inputs/description_mapping.jsonl", calibration["description_mapping_sha256"])
    for item in config["spec_snapshot"]:
        require_hash(resolve_inside(run / "spec_snapshot", item["path"]), item["sha256"])
    for item in calibration["extra_spec_snapshots"]:
        require_hash(resolve_inside(run, item["path"]), item["sha256"])
    pool = {r["id"]: r for r in rows(run / "inputs/candidate_pool.jsonl")}
    mapping = rows(run / "inputs/description_mapping.jsonl")
    if len({r["image_alias"] for r in mapping}) != len(mapping):
        raise ContractError("duplicate description alias")
    for row in mapping:
        if any(row[k] != pool[row["id"]][k] for k in ("domain", "class", "split", "file", "sha256")):
            raise ContractError("description mapping disagrees with the frozen source pool")
        if row["split"] != "train" or row["domain"] == config["target_domain"]:
            raise ContractError("calibration image leaks evaluation data")
    return config, calibration, {r["image_alias"]: r for r in mapping}


def freeze_descriptions(run: Path) -> dict:
    _, _, mapping = inputs(run)
    target = run / "records/image_descriptions.jsonl"
    frozen = run / "records/descriptions_frozen.json"
    if target.exists() or frozen.exists():
        raise FileExistsError("descriptions are already frozen; do not rewrite observations after matching")
    schema = read_json(run / "spec_snapshot/specs/image_description.schema.json")
    descriptions, sources, seen = [], [], set()
    for batch in sorted({r["batch"] for r in mapping.values()}):
        package = run / f"description_packages/batch-{batch:02d}"
        raw = package / "descriptions.jsonl"
        inspection = package / "inspection_log.json"
        read_json(inspection)  # A required agent inspection log, not an automatic pixel check.
        sources.extend(fingerprint(p, p.relative_to(run).as_posix()) for p in (raw, inspection))
        expected = {alias for alias, value in mapping.items() if value["batch"] == batch}
        records = rows(raw)
        if {r["image_alias"] for r in records} != expected or len(records) != len(expected):
            raise ContractError(f"batch {batch} must describe every assigned image exactly once")
        for record in records:
            alias = record["image_alias"]
            jsonschema.validate(record["description"], schema)
            if alias in seen or record["description"]["image_alias"] != alias:
                raise ContractError("duplicate or inconsistent description alias")
            seen.add(alias)
            image = mapping[alias]
            require_hash(package / f"{alias}.jpg", image["sha256"])
            descriptions.append({**record, "image_id": image["id"], "image_sha256": image["sha256"]})
    descriptions.sort(key=lambda r: r["image_alias"])
    write_jsonl(target, descriptions)
    result = {"frozen_at": utc_now(), "image_count": len(descriptions),
              "descriptions": fingerprint(target, target.relative_to(run).as_posix()), "sources": sources,
              "limitation": "Image-only instructions; no operating-system metadata isolation. Confidence is uncalibrated."}
    atomic_write_json(frozen, result)
    return result


def audit_roles(pairs: list[dict], project: Path, seed: int) -> dict:
    """Use existing features only for reproducible audit selection, never validity."""
    feature_file = project / "pipeline/data/embeddings/embeddings.npy"
    ids_file = feature_file.with_name("ids.json")
    ids = read_json(ids_file)
    if len(set(ids)) != len(ids):
        raise ContractError("embedding IDs are not unique")
    index = {image_id: i for i, image_id in enumerate(ids)}
    features = np.load(feature_file, mmap_mode="r", allow_pickle=False)
    if features.shape[0] != len(ids):
        raise ContractError("embedding matrix and IDs disagree")
    vectors = np.asarray([[features[index[p[role]["id"]]] for role in ("anchor", "candidate")]
                          for p in pairs], dtype=np.float64)
    if not np.isfinite(vectors).all() or (np.linalg.norm(vectors, axis=-1) == 0).any():
        raise ContractError("nonfinite or zero image embedding")
    vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
    centers = vectors.mean(axis=1)
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    distances = np.maximum(0, 1 - centers @ centers.T)
    mean_distance = distances.sum(axis=1) / (len(pairs)-1)
    medoid = int(np.argmin(mean_distance))
    boundary = int(np.argmax(distances[medoid]))
    nearest = distances.copy()
    np.fill_diagonal(nearest, np.inf)
    nearest = nearest.min(axis=1)
    outlier = int(np.argmax(nearest))
    least = min(range(len(pairs)), key=lambda i: (pairs[i]["confidence"], pairs[i]["pair_id"]))
    chosen = random.Random(seed).randrange(len(pairs))
    role_indices = {"embedding_medoid": medoid, "seeded_random": chosen,
                    "lowest_confidence": least, "embedding_boundary": boundary, "embedding_outlier": outlier}
    for i, pair in enumerate(pairs):
        pair["highlighted_roles"] = [role for role, selected in role_indices.items() if selected == i]
    return {
        "algorithm_version": 1, "seed": seed,
        "roles": {role: pairs[i]["pair_id"] for role, i in role_indices.items()},
        "definitions": {
            "embedding_medoid": "Minimum mean cosine distance between normalized mean-of-two image feature vectors.",
            "seeded_random": "Python random.Random(run_seed).randrange(group_size), independent draw; roles may overlap.",
            "lowest_confidence": "Minimum coordinator uncalibrated confidence; pair ID breaks ties.",
            "embedding_boundary": "Maximum cosine distance from the embedding medoid; first position breaks ties.",
            "embedding_outlier": "Maximum nearest-other-pair cosine distance; first position breaks ties.",
        },
        "feature_file": fingerprint(feature_file, feature_file.relative_to(project).as_posix()),
        "ids_file": fingerprint(ids_file, ids_file.relative_to(project).as_posix()),
        "provenance_limit": "Existing project image features. Original checkpoint and generation revision are not independently verified. Numerical audit roles are reproducible from the hashed files; they do not measure pair validity or prove semantic coverage. Only this group's source-training rows are used.",
        "metrics": [{"pair_id": p["pair_id"], "mean_distance": float(mean_distance[i]),
                     "distance_from_medoid": float(distances[medoid, i]),
                     "nearest_other_distance": float(nearest[i]),
                     "within_pair_cosine": float(vectors[i, 0] @ vectors[i, 1])} for i, p in enumerate(pairs)],
    }


def finalize(run: Path, project: Path, draft_path: Path) -> dict:
    config, calibration, mapping = inputs(run)
    frozen = read_json(run / "records/descriptions_frozen.json")
    for item in [frozen["descriptions"], *frozen["sources"]]:
        require_hash(resolve_inside(run, item["path"]), item["sha256"])
    descriptions = {r["image_alias"]: r for r in rows(run / frozen["descriptions"]["path"])}
    group = read_json(draft_path)
    group_id = group["group_id"]
    group_path = resolve_inside(run / "records/groups", f"{group_id}.json")
    review_dir = resolve_inside(run / "review", group_id)
    if group_path.exists() or review_dir.exists():
        raise FileExistsError("this group has already been published; create a versioned correction")
    if group["run_id"] != config["run_id"] or group["condition"] != "calibration_visible":
        raise ContractError("draft belongs to a different run or condition")
    if len(group["pairs"]) != calibration["target_group_size"]:
        raise ContractError("draft does not match this calibration's requested group size")
    # Later independent checks replace only their explicitly named draft positions.
    audits, audit_sources = {}, []
    for name in ("joint_independent_audit.json", "joint_independent_audit_v2.json", "joint_independent_audit_v3.json", "joint_independent_audit_v4.json"):
        path = run / "records" / name
        for check in read_json(path):
            audits[check["pair_number"]] = {**check, "source": f"records/{name}"}
        audit_sources.append(fingerprint(path, path.relative_to(run).as_posix()))
    unique_ids, byte_hashes, pixel_hashes = set(), set(), set()
    pair_ids = [p["pair_id"] for p in group["pairs"]]
    if len(set(pair_ids)) != len(pair_ids):
        raise ContractError("duplicate pair ID")
    checks = []
    for position, pair in enumerate(group["pairs"], 1):
        if pair["position"] != position:
            raise ContractError("pair positions must be contiguous and match stored order")
        check = pair.get("joint_pixel_check", {})
        if check.get("outcome") != "pass" or check.get("reviewer_type") != "model" or not check.get("evidence"):
            raise ContractError("each proposal requires explicit coordinator joint pixel-check evidence")
        independent = audits.get(position, {})
        expected_aliases = [pair["anchor_alias"], pair["candidate_alias"]]
        if independent.get("status") != "pass" or independent.get("aliases") != expected_aliases:
            raise ContractError(f"pair {position} has no passing independent check for its exact images")
        pair["independent_pixel_check"] = independent
        for role in ("anchor", "candidate"):
            alias = pair.pop(f"{role}_alias")
            image = mapping[alias]
            description = descriptions[alias]["description"]
            count = description["target_count"]
            if count["status"] != "observed" or count["minimum"] != 1 or count["maximum"] != 1:
                raise ContractError(f"{alias} has uncertain or non-single subject count")
            if description["visible_category"]["status"] != "observed" or description["activity_pose_state"]["status"] != "observed":
                raise ContractError(f"{alias} has a materially unknown required semantic field")
            source = resolve_inside(project / "web/public/pacs", image["file"])
            require_hash(source, image["sha256"])
            with Image.open(source) as original:
                original.load()
                rgb = original.convert("RGB")
                pixels = sha256_bytes(str(rgb.size).encode() + rgb.tobytes())
            if image["id"] in unique_ids or image["sha256"] in byte_hashes or pixels in pixel_hashes:
                raise ContractError("image reuse or exact duplicate pixels in final group")
            unique_ids.add(image["id"])
            byte_hashes.add(image["sha256"])
            pixel_hashes.add(pixels)
            pair[role] = {k: image[k] for k in ("id", "class", "domain", "split", "file", "sha256")}
            pair[role]["description_alias"] = alias
        if pair["anchor"]["domain"] == pair["candidate"]["domain"]:
            raise ContractError("pair must cross domains")
        if pair["anchor"]["class"] != pair["candidate"]["class"] or pair["target_count"] != 1:
            raise ContractError("pair class/count disagrees with the calibration")
        checks.append({"pair_id": pair["pair_id"], **check})
    # Validate supplied metadata even with older permissive frozen schemas. The
    # provenance below comes from the mandatory check above and the frozen prompt,
    # not from merely observing that the selected images happen to differ.
    validate_domain_selection(group)
    for record in [group, *group["pairs"]]:
        selection = record.get("domain_selection")
        if selection is not None and selection["policy"] not in {"cross_domain_required", "unknown"}:
            raise ContractError("calibration requires cross_domain_required domain_selection for every pair")
    prompt = next(i for i in calibration["extra_spec_snapshots"] if i["path"].endswith("calibration_matching_v1.md"))
    group["domain_selection"] = {
        "policy": "cross_domain_required",
        "evidence": "The calibration matching prompt requires cross-domain pairs; finalize rejects every same-domain pair using frozen source metadata.",
        "source": f"chat_review.calibration.finalize mandatory domain check; frozen prompt {prompt['path']} (sha256: {prompt['sha256']})",
    }
    for pair in group["pairs"]:
        if pair.get("domain_selection", {}).get("policy") == "unknown":
            pair["domain_selection"] = dict(group["domain_selection"])
    validate_domain_selection(group)
    group["highlight_selection"] = audit_roles(group["pairs"], project, config["seed"])
    group["description_freeze_sha256"] = sha256_file(run / "records/descriptions_frozen.json")
    group["independent_audit_sources"] = audit_sources
    group["proposal_prompt_sha256"] = prompt["sha256"]
    group["created_at"] = utc_now()
    group["controlled_study_eligible"] = False
    group["human_review_status"] = "pending_initial"
    jsonschema.validate(group, read_json(run / "spec_snapshot/specs/group.schema.json"))
    # All checks run before publication. Both stages use this same frozen record.
    atomic_write_json(group_path, group)
    write_jsonl(run / "records/joint_pixel_checks.jsonl", checks)
    report = build_report(group=group, output_path=review_dir / "initial.html",
                          pacs_root=project / "web/public/pacs", stage="initial")
    source = report.read_text(encoding="utf-8")
    forbidden = [group["semantic_claim"], *group["highlight_selection"]["definitions"]]
    forbidden += [p[field] for p in group["pairs"] for field in ("semantic_rationale", "spurious_rationale", "uncertainty") if p[field]]
    forbidden += ["domain_selection", "domain-selection policy", "Domain selection (", "Different domains required"]
    forbidden += [value for record in [group, *group["pairs"]]
                  for value in record.get("domain_selection", {}).values() if value]
    if any(value in source or html.escape(value) in source for value in forbidden):
        raise ContractError("initial report leaks stored explanations, domain selection, or evaluative role names")
    result = {
        "status": "ready_for_initial_human_review", "created_at": utc_now(),
        "group_id": group_id, "pairs": len(group["pairs"]), "unique_images": len(unique_ids),
        "described_images": len(descriptions), "eligible_source_training_images": config["candidate_pool"]["image_count"],
        "held_out_domain": config["target_domain"], "human_judgments_created": 0,
        "checks": {"schema": True, "frozen_inputs": True, "train_only": True, "held_out_domain_absent": True,
                   "exact_duplicates_absent": True, "image_reuse_absent": True, "all_images_decode": True,
                   "descriptions_saved_before_matching": True, "initial_rationale_absent": True},
        "group": fingerprint(group_path, group_path.relative_to(run).as_posix()),
        "initial_html": fingerprint(report, report.relative_to(run).as_posix()),
        "review_assets": [fingerprint(p, p.relative_to(run).as_posix()) for p in sorted((report.parent / "initial_assets").iterdir())],
        "limitations": ["A model pixel check is proposal evidence, not human validation.",
                        "One class and two domains; not an estimate of PACS-wide coverage.",
                        "The coordinator has seen previous human feedback; exclude from controlled-condition comparisons.",
                        "Seed fixes sampling and audit selection, not stochastic model text regeneration.",
                        "No downstream training, robustness measurement, or accepted-pair export has been performed."],
    }
    atomic_write_json(run / "records/proposal_validation.json", result)
    atomic_write_json(run / "records/current_state.json", {
        "status": "initial_review_pending", "group_id": group_id,
        "group_file": group_path.relative_to(run).as_posix(), "initial_html": report.relative_to(run).as_posix(),
        "next_action": "Wait for human initial judgment, show derived receipt, obtain confirmation, then render revised HTML from the frozen group.",
        "review_ledger": "records/reviews.jsonl", "judgment_stage_for_export": config["judgment_stage_for_export"],
        "counts_toward_adaptive_update": False,
    })
    return {k: result[k] for k in ("status", "group_id", "pairs", "unique_images", "described_images")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("freeze-descriptions", "finalize"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--draft", type=Path)
    args = parser.parse_args()
    if args.stage == "freeze-descriptions":
        result = freeze_descriptions(args.run.resolve())
        print(json.dumps({"frozen": True, "image_count": result["image_count"]}))
    else:
        if args.draft is None:
            parser.error("finalize requires --draft")
        print(json.dumps(finalize(args.run.resolve(), Path(__file__).resolve().parents[1], args.draft)))


if __name__ == "__main__":
    main()
