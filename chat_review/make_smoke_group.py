from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from chat_review.common import ContractError, atomic_write_json, read_json


def make_smoke_group(manifest_path: Path, output_path: Path, seed: int, size: int, condition: str) -> Path:
    if size < 1:
        raise ContractError("size must be positive")
    manifest = read_json(manifest_path)
    train = [row for row in manifest.get("images", []) if row.get("split") == "train"]
    by_class_domain: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in train:
        by_class_domain[(row["class"], row["domain"])].append(row)
    keys = sorted(by_class_domain)
    rng = random.Random(seed)
    pairs: list[dict[str, Any]] = []
    used: set[str] = set()
    attempts = 0
    while len(pairs) < size and attempts < size * 100:
        attempts += 1
        class_name, anchor_domain = rng.choice(keys)
        other_domains = sorted(
            domain for candidate_class, domain in keys if candidate_class == class_name and domain != anchor_domain
        )
        if not other_domains:
            continue
        candidate_domain = rng.choice(other_domains)
        anchor = rng.choice(by_class_domain[(class_name, anchor_domain)])
        candidate = rng.choice(by_class_domain[(class_name, candidate_domain)])
        if anchor["id"] in used or candidate["id"] in used:
            continue
        used.update((anchor["id"], candidate["id"]))
        position = len(pairs) + 1
        roles = []
        if position == 1:
            roles.append("typical_placeholder")
        if position == 2:
            roles.append("seeded_random")
        if position == size:
            roles.append("boundary_placeholder")
        pairs.append(
            {
                "pair_id": f"SMOKE-{position:03d}",
                "position": position,
                "anchor": {key: anchor[key] for key in ("id", "class", "domain", "split", "file")},
                "candidate": {key: candidate[key] for key in ("id", "class", "domain", "split", "file")},
                "highlighted_roles": roles,
                "semantic_rationale": "Unverified smoke-test pair selected only by manifest class.",
                "spurious_rationale": "Different manifest domains; visual differences have not been model-checked.",
                "uncertainty": "This is a layout and plumbing fixture, not a scientific proposal.",
                "confidence": None,
            }
        )
    if len(pairs) != size:
        raise ContractError(f"could create only {len(pairs)} non-reusing smoke pairs")

    group = {
        "schema_version": 1,
        "group_id": f"SMOKE-{seed}-{size}",
        "run_id": "smoke-test-only",
        "condition": condition,
        "semantic_claim": "Not evaluated. This artifact tests static HTML and review plumbing only.",
        "coverage_summary": {axis: "not evaluated" for axis in ("background", "palette", "lighting", "texture", "viewpoint", "crop", "composition")},
        "reasons_group_may_fail": ["Pairs have not been visually described or jointly checked by a proposer."],
        "pairs": pairs,
    }
    atomic_write_json(output_path, group)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a clearly labeled non-scientific PACS smoke-test group.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260930)
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--condition", choices=("fixed_hidden", "fixed_visible", "adaptive_hidden", "adaptive_visible"), default="fixed_hidden")
    args = parser.parse_args()
    result = make_smoke_group(args.manifest, args.output, args.seed, args.size, args.condition)
    print(json.dumps({"group": str(result)}, indent=2))


if __name__ == "__main__":
    main()
