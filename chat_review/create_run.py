from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from chat_review.common import (
    CLASSES,
    CONDITIONS,
    DOMAINS,
    SPURIOUS_AXES,
    ContractError,
    atomic_write_json,
    fingerprint,
    read_json,
    sha256_file,
    utc_now,
    validate_run_id,
    write_jsonl,
)


SPEC_FILES = (
    "specs/pacs_source.json",
    "specs/pair_definition.md",
    "specs/model_working_definition.md",
    "specs/image_description.schema.json",
    "specs/matching_policy.md",
    "specs/grouping_policy.md",
    "specs/group.schema.json",
    "specs/review_protocol.md",
    "specs/review_event.schema.json",
    "specs/export_schema.json",
    "specs/run_config.schema.json",
    "prompts/proposer_fixed_hidden_v1.md",
)


def load_candidate_pool(manifest_path: Path, proposal_split: str, target_domain: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = read_json(manifest_path)
    images = manifest.get("images")
    if not isinstance(images, list) or not images:
        raise ContractError("manifest.images must be a non-empty array")

    seen: set[str] = set()
    pool: list[dict[str, Any]] = []
    for image in images:
        image_id = image.get("id")
        if not isinstance(image_id, str) or image_id in seen:
            raise ContractError(f"manifest contains a missing or duplicate image id: {image_id!r}")
        seen.add(image_id)
        if image.get("split") != proposal_split:
            continue
        if target_domain is not None and image.get("domain") == target_domain:
            continue
        if image.get("domain") not in DOMAINS or image.get("class") not in CLASSES:
            raise ContractError(f"unsupported PACS metadata for {image_id}")
        pool.append(
            {
                "id": image_id,
                "domain": image["domain"],
                "class": image["class"],
                "split": image["split"],
                "file": image["file"],
            }
        )

    pool.sort(key=lambda row: row["id"])
    if not pool:
        raise ContractError("proposal candidate pool is empty")
    if any(row["split"] != proposal_split for row in pool):
        raise ContractError("candidate pool contains split leakage")
    if target_domain and any(row["domain"] == target_domain for row in pool):
        raise ContractError("candidate pool contains held-out-domain leakage")
    return manifest, pool


def create_run(
    *,
    project_root: Path,
    output_root: Path,
    manifest_path: Path,
    run_id: str,
    seed: int,
    model: str,
    reasoning_effort: str,
    proposal_split: str,
    target_domain: str | None,
    judgment_stage: str,
    group_sizes: list[int],
    conditions: list[str],
    pacs_root: Path,
    hash_images: bool,
) -> Path:
    validate_run_id(run_id)
    if not 0 <= seed <= 0xFFFFFFFF:
        raise ContractError("seed must be an unsigned 32-bit integer")
    if proposal_split not in {"train", "val", "test"}:
        raise ContractError("proposal_split must be train, val, or test")
    if target_domain not in {*DOMAINS, None}:
        raise ContractError(f"target_domain must be one of {DOMAINS} or omitted")
    if judgment_stage not in {"initial", "revised"}:
        raise ContractError("judgment_stage must be initial or revised")
    if not conditions or any(value not in CONDITIONS for value in conditions):
        raise ContractError(f"conditions must be drawn from {CONDITIONS}")
    if not group_sizes or any(value not in {10, 20, 40} for value in group_sizes):
        raise ContractError("group_sizes must be selected from 10, 20, and 40")

    _, pool = load_candidate_pool(manifest_path, proposal_split, target_domain)
    required_sources = [project_root / relative for relative in SPEC_FILES]
    missing_sources = [path for path in required_sources if not path.is_file()]
    if missing_sources:
        raise FileNotFoundError(f"required frozen input is missing: {missing_sources[0]}")
    if hash_images:
        for row in pool:
            image_path = pacs_root / row["file"]
            if not image_path.is_file():
                raise FileNotFoundError(f"candidate image is missing: {image_path}")
            row["sha256"] = sha256_file(image_path)

    run_dir = output_root / run_id
    if run_dir.exists():
        raise FileExistsError(f"immutable run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    (run_dir / "inputs").mkdir()
    (run_dir / "records").mkdir()
    (run_dir / "review").mkdir()
    (run_dir / "exports").mkdir()
    snapshot_dir = run_dir / "spec_snapshot"
    snapshot_dir.mkdir()

    snapshot: list[dict[str, Any]] = []
    for relative in SPEC_FILES:
        source = project_root / relative
        destination = snapshot_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        snapshot.append(fingerprint(destination, relative))

    pool_path = run_dir / "inputs" / "candidate_pool.jsonl"
    pool_hash = write_jsonl(pool_path, pool)
    split_counts = Counter(row["split"] for row in pool)
    pool_domains = sorted({row["domain"] for row in pool})
    pool_classes = sorted({row["class"] for row in pool})

    rng = random.Random(seed)
    condition_order = conditions.copy()
    rng.shuffle(condition_order)

    try:
        manifest_label = manifest_path.relative_to(project_root).as_posix()
    except ValueError:
        manifest_label = manifest_path.as_posix()
    config = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": utc_now(),
        "seed": seed,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "conditions": conditions,
        "condition_order": condition_order,
        "proposal_split": proposal_split,
        "evaluation_protocol": "pacs_held_out_domain",
        "target_domain": target_domain,
        "judgment_stage_for_export": judgment_stage,
        "group_sizes": sorted(set(group_sizes)),
        "adaptive_update": {"completed_initial_groups": 5, "individually_audited_pairs": 20},
        "spurious_axes": list(SPURIOUS_AXES),
        "manifest": fingerprint(manifest_path, manifest_label),
        "candidate_pool": {
            "image_count": len(pool),
            "classes": pool_classes,
            "domains": pool_domains,
            "split_counts": dict(sorted(split_counts.items())),
            "index_file": "inputs/candidate_pool.jsonl",
            "sha256": pool_hash,
            "images_hashed": hash_images,
            "image_hash_algorithm": "sha256" if hash_images else "not_computed",
        },
        "spec_snapshot": snapshot,
    }
    atomic_write_json(run_dir / "run.json", config)
    atomic_write_json(
        run_dir / "inputs" / "split_guard.json",
        {
            "proposal_split": proposal_split,
            "target_domain": target_domain,
            "eligible_image_count": len(pool),
            "manifest_sha256": sha256_file(manifest_path),
            "candidate_pool_sha256": pool_hash,
            "checks": {"single_split_only": True, "held_out_domain_absent": True},
        },
    )
    return run_dir


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Create an immutable chat-review run scaffold.")
    result.add_argument("--run-id", required=True)
    result.add_argument("--seed", type=int, required=True)
    result.add_argument("--model", default="gpt-6-astra")
    result.add_argument("--reasoning-effort", default="ultra")
    result.add_argument("--proposal-split", default="train", choices=("train", "val", "test"))
    result.add_argument("--target-domain", choices=DOMAINS)
    result.add_argument("--judgment-stage", default="revised", choices=("initial", "revised"))
    result.add_argument("--group-sizes", type=int, nargs="+", default=[10, 20, 40])
    result.add_argument("--conditions", nargs="+", default=[value for value in CONDITIONS if not value.startswith("calibration_")])
    result.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    result.add_argument("--manifest", type=Path)
    result.add_argument("--pacs-root", type=Path)
    result.add_argument("--skip-image-hashes", action="store_true", help="Development only; scientific runs should retain the default image hashing.")
    result.add_argument("--output-root", type=Path)
    return result


def main() -> None:
    args = parser().parse_args()
    project_root = args.project_root.resolve()
    manifest = (args.manifest or project_root / "web" / "public" / "manifest.json").resolve()
    output_root = (args.output_root or project_root / "runs").resolve()
    pacs_root = (args.pacs_root or project_root / "web" / "public" / "pacs").resolve()
    run_dir = create_run(
        project_root=project_root,
        output_root=output_root,
        manifest_path=manifest,
        run_id=args.run_id,
        seed=args.seed,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        proposal_split=args.proposal_split,
        target_domain=args.target_domain,
        judgment_stage=args.judgment_stage,
        group_sizes=args.group_sizes,
        conditions=args.conditions,
        pacs_root=pacs_root,
        hash_images=not args.skip_image_hashes,
    )
    print(json.dumps({"run_directory": str(run_dir), "run_config": str(run_dir / "run.json")}, indent=2))


if __name__ == "__main__":
    main()
