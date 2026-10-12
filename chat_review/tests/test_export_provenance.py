from __future__ import annotations

import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chat_review.common import ContractError, fingerprint, sha256_file
from chat_review.export_hf import (
    CALIBRATION_DESCRIPTION_PROMPT,
    CALIBRATION_MATCHING_PROMPT,
    PROVENANCE_COLUMNS,
    build_pair_rows,
    export_run,
    group_tables,
    load_export_provenance,
    pair_features,
    read_jsonl,
)
from chat_review.review import append_event, confirm_event


ROOT = Path(__file__).resolve().parents[2]
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOc8AAAAASUVORK5CYII="
)


class ExportProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix=".export-provenance-", dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run_dir = self.root / "fixture-run"
        self.groups_dir = self.run_dir / "records" / "groups"
        self.groups_dir.mkdir(parents=True)
        self.pacs_root = self.root / "images"
        self.pacs_root.mkdir()
        self.output_dir = self.root / "export"
        self.run = {
            "run_id": "fixture-run", "conditions": ["calibration_visible"],
            "proposal_split": "train", "target_domain": "sketch", "seed": 7,
            "model": "fixture-model", "reasoning_effort": "test",
            "judgment_stage_for_export": "revised", "manifest": {"sha256": "fixture-manifest"},
            "spec_snapshot": [
                {"path": "specs/pair_definition.md", "sha256": "fixture-pair-spec"},
                {"path": "prompts/proposer_fixed_hidden_v1.md", "sha256": "legacy-proposer-hash"},
            ],
        }
        snapshots = []
        for relative, text in (
            (CALIBRATION_MATCHING_PROMPT, "Frozen fixture matching prompt."),
            (CALIBRATION_DESCRIPTION_PROMPT, "Frozen fixture description prompt."),
            ("calibration_spec_snapshot/specs/potential_review_criteria.md", "Frozen fixture criteria."),
        ):
            path = self.run_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            snapshots.append(fingerprint(path, relative))
        self.calibration = {
            "study_kind": "real_data_calibration", "controlled_study_eligible": False,
            "counts_toward_adaptive_update": False, "seed": 7, "held_out_domain": "sketch",
            "extra_spec_snapshots": snapshots,
        }
        self.group = {"group_id": "G-fixture", "condition": "calibration_visible", "pairs": []}
        for index in range(2):
            images = []
            for side, domain in (("anchor", "photo"), ("candidate", "cartoon")):
                name = f"{index}-{side}"
                (self.pacs_root / f"{name}.png").write_bytes(PNG)
                images.append({"file": f"{name}.png", "id": name, "domain": domain, "class": "dog", "split": "train"})
            self.group["pairs"].append({
                "pair_id": f"P-{index}", "anchor": images[0], "candidate": images[1],
                "highlighted_roles": ["seeded_random"] if index == 0 else [],
                "target_count": 1, "activity_pose_state": "standing", "spurious_axes": ["background"],
                "semantic_rationale": "Fixture evidence", "confidence": 0.8,
            })
        self.review = {
            "event_id": "E-fixture", "group_id": "G-fixture", "reviewer_id": "fixture-reviewer",
            "stage": "revised", "coverage": "adequate",
            "derived_pair_receipt": [
                {"pair_id": "P-0", "verdict": "accept", "validation_scope": "individual"},
                {"pair_id": "P-1", "verdict": "accept", "validation_scope": "group_scan"},
            ],
        }
        self.descriptions = [
            {"image_id": image["id"], "description_version": "fixture-v1", "description": {"class": "dog"}}
            for pair in self.group["pairs"] for image in (pair["anchor"], pair["candidate"])
        ]
        self.save_inputs()

    def save_inputs(self) -> None:
        for path, value in (
            (self.run_dir / "run.json", self.run),
            (self.run_dir / "calibration.json", self.calibration),
            (self.groups_dir / "group.json", self.group),
        ):
            path.write_text(json.dumps(value), encoding="utf-8")

    def provenance(self) -> dict:
        return load_export_provenance(self.run_dir, self.run, [self.group])

    def rows(self, provenance: dict | None = None) -> list[dict]:
        return build_pair_rows(
            run=self.run, groups=[self.group], reviews={"G-fixture": self.review},
            pacs_root=self.pacs_root, provenance=provenance,
        )

    def make_legacy(self) -> None:
        self.run["conditions"] = ["fixed_hidden"]
        self.group["condition"] = "fixed_hidden"
        self.save_inputs()
        (self.run_dir / "calibration.json").unlink()

    def assert_export_rejected(self, message: str) -> None:
        with patch("chat_review.export_hf.write_table") as writer:
            with self.assertRaisesRegex(ContractError, message):
                export_run(self.run_dir, self.groups_dir, self.pacs_root, self.output_dir)
            writer.assert_not_called()
        self.assertFalse(self.output_dir.exists())

    def test_calibration_uses_verified_matching_and_description_hashes(self) -> None:
        provenance = self.provenance()
        rows = self.rows(provenance)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["prompt_sha256"], sha256_file(self.run_dir / CALIBRATION_MATCHING_PROMPT))
            self.assertEqual(row["description_prompt_sha256"], sha256_file(self.run_dir / CALIBRATION_DESCRIPTION_PROMPT))
            self.assertEqual(row["calibration_metadata_sha256"], sha256_file(self.run_dir / "calibration.json"))
            self.assertNotEqual(row["prompt_sha256"], "legacy-proposer-hash")
            self.assertEqual(row["study_kind"], "real_data_calibration")
            self.assertIs(row["controlled_study_eligible"], False)
            self.assertIs(row["counts_toward_adaptive_update"], False)
            self.assertTrue(row["eligible_broad"])
        self.assertEqual([row["eligible_strict"] for row in rows], [True, False])

    def test_normal_and_legacy_rows_keep_original_hash_and_review_scope(self) -> None:
        self.make_legacy()
        for condition in ("fixed_hidden", "fixed_visible", "adaptive_hidden", "adaptive_visible"):
            with self.subTest(condition=condition):
                self.run["conditions"] = [condition]
                self.group["condition"] = condition
                self.assertEqual(self.rows(), self.rows(self.provenance()))
                for row in self.rows():
                    self.assertEqual(row["prompt_sha256"], "legacy-proposer-hash")
                    self.assertEqual(row["description_prompt_sha256"], "")
                    self.assertEqual(row["calibration_metadata_sha256"], "")
                    self.assertEqual(row["study_kind"], "legacy_unspecified")
                    self.assertIs(row["controlled_study_eligible"], False)
                    self.assertIs(row["counts_toward_adaptive_update"], False)
        del self.run["conditions"]
        self.run["spec_snapshot"] = []
        self.assertEqual(self.rows()[0]["prompt_sha256"], "")

    def test_unknown_and_smoke_runs_are_not_scientific(self) -> None:
        self.make_legacy()
        for run_id, fields in (
            ("unknown", {}),
            ("smoke-fixture", {}),
            ("smoke-fixture", {"study_kind": "smoke"}),
            ("smoke-fixture", {"study_kind": "smoke", "controlled_study_eligible": True}),
            ("unknown", {"study_kind": "controlled_study"}),
            ("unknown", {"counts_toward_adaptive_update": True}),
        ):
            with self.subTest(run_id=run_id, fields=fields):
                for key in ("study_kind", "controlled_study_eligible", "counts_toward_adaptive_update"):
                    self.run.pop(key, None)
                self.run.update(run_id=run_id, **fields)
                self.run["conditions"] = ["adaptive_visible"]
                self.group["condition"] = "adaptive_visible"
                provenance = self.provenance()
                self.assertEqual(provenance["study_kind"], fields.get("study_kind", "legacy_unspecified"))
                for row in self.rows(provenance):
                    self.assertIs(row["controlled_study_eligible"], False)
                    self.assertIs(row["counts_toward_adaptive_update"], False)
                with patch("chat_review.export_hf.simple_features", side_effect=dict):
                    tables = group_tables(self.run, [self.group], [self.review], self.descriptions, provenance)
                for rows, _ in tables.values():
                    for row in rows:
                        self.assertIs(row["controlled_study_eligible"], False)
                        self.assertIs(row["counts_toward_adaptive_update"], False)

    def test_explicit_controlled_fixed_groups_never_count_toward_adaptive_updates(self) -> None:
        self.make_legacy()
        self.run.update(study_kind="controlled_study", controlled_study_eligible=True, counts_toward_adaptive_update=True)
        for condition in ("fixed_hidden", "fixed_visible"):
            with self.subTest(condition=condition):
                self.run["conditions"] = [condition]
                self.group["condition"] = condition
                provenance = self.provenance()
                self.assertIs(provenance["counts_toward_adaptive_update"], False)
                self.assertEqual(len(self.rows(provenance)), 2)
                for row in self.rows(provenance):
                    self.assertIs(row["controlled_study_eligible"], True)
                    self.assertIs(row["counts_toward_adaptive_update"], False)
                with patch("chat_review.export_hf.simple_features", side_effect=dict):
                    tables = group_tables(self.run, [self.group], [self.review], self.descriptions, provenance)
                for rows, _ in tables.values():
                    self.assertTrue(all(row["counts_toward_adaptive_update"] is False for row in rows))

    def test_explicit_controlled_mixed_conditions_use_each_groups_condition(self) -> None:
        self.make_legacy()
        original_columns = set(self.rows()[0])
        self.run.update(study_kind="controlled_study", controlled_study_eligible=True)
        self.run["conditions"] = ["fixed_hidden", "adaptive_visible", "fixed_visible", "adaptive_hidden"]
        groups, reviews = [], {}
        for condition in self.run["conditions"]:
            group = copy.deepcopy(self.group)
            group.update(group_id=condition, condition=condition)
            for pair in group["pairs"]:
                pair["pair_id"] = f'{condition}-{pair["pair_id"]}'
            review = copy.deepcopy(self.review)
            review.update(group_id=condition, event_id=f"E-{condition}")
            for receipt in review["derived_pair_receipt"]:
                receipt["pair_id"] = f'{condition}-{receipt["pair_id"]}'
            groups.append(group)
            reviews[condition] = review
        before = copy.deepcopy((self.run, groups, reviews))
        provenance = load_export_provenance(self.run_dir, self.run, groups)
        rows = build_pair_rows(run=self.run, groups=groups, reviews=reviews, pacs_root=self.pacs_root, provenance=provenance)
        self.assertEqual(len(rows), 8)
        self.assertEqual(sum(row["eligible_strict"] for row in rows), 4)
        self.assertEqual(sum(row["counts_toward_adaptive_update"] for row in rows), 4)
        for row in rows:
            self.assertEqual(set(row), original_columns)
            self.assertIs(row["controlled_study_eligible"], True)
            self.assertEqual(row["counts_toward_adaptive_update"], row["condition"].startswith("adaptive_"))
        with patch("chat_review.export_hf.simple_features", side_effect=dict):
            tables = group_tables(self.run, groups, list(reviews.values()), self.descriptions, provenance)
        for table_rows, _ in tables.values():
            for row in table_rows:
                self.assertIs(row["controlled_study_eligible"], True)
                self.assertEqual(row["counts_toward_adaptive_update"], row.get("group_id", "").startswith("adaptive_"))
        self.assertEqual((self.run, groups, reviews), before)

    def test_adaptive_eligibility_requires_explicit_valid_metadata_and_known_condition(self) -> None:
        self.make_legacy()
        self.run["controlled_study_eligible"] = True
        self.run["conditions"] = ["adaptive_visible"]
        self.group["condition"] = "adaptive_visible"
        self.assertEqual(self.provenance()["study_kind"], "controlled_study")
        self.assertTrue(all(row["counts_toward_adaptive_update"] for row in self.rows(self.provenance())))
        for fields, condition in (
            ({"counts_toward_adaptive_update": False}, "adaptive_visible"),
            ({"controlled_study_eligible": False}, "adaptive_visible"),
            ({}, "adaptive_hidden"),  # Not declared in this run.
            ({}, "adaptive_future"),
            ({}, ""),
        ):
            with self.subTest(fields=fields, condition=condition):
                run = {**self.run, **fields}
                group = {**self.group, "condition": condition}
                provenance = load_export_provenance(self.run_dir, run, [group])
                rows = build_pair_rows(run=run, groups=[group], reviews={"G-fixture": self.review}, pacs_root=self.pacs_root, provenance=provenance)
                self.assertTrue(all(row["counts_toward_adaptive_update"] is False for row in rows))
        for field in ("controlled_study_eligible", "counts_toward_adaptive_update"):
            for value in ("true", 1, None):
                with self.subTest(field=field, value=value):
                    run = {**self.run, field: value}
                    with self.assertRaisesRegex(ContractError, "explicit boolean"):
                        load_export_provenance(self.run_dir, run, [self.group])
        self.run.pop("controlled_study_eligible")
        forged = {**self.provenance(), "study_kind": "controlled_study", "controlled_study_eligible": True}
        with self.assertRaisesRegex(ContractError, "explicit run eligibility"):
            self.rows(forged)

    def test_calibration_row_builders_require_loaded_provenance(self) -> None:
        with self.assertRaisesRegex(ContractError, "loaded and verified"):
            self.rows()
        with self.assertRaisesRegex(ContractError, "loaded and verified"):
            group_tables(self.run, [self.group], [], self.descriptions)
        invalid = {**self.provenance(), "controlled_study_eligible": True}
        with self.assertRaisesRegex(ContractError, "controlled-study provenance"):
            self.rows(invalid)

    def test_all_normalized_tables_carry_calibration_provenance(self) -> None:
        provenance = self.provenance()
        # Feature declarations can be inspected without importing datasets.
        with patch("chat_review.export_hf.simple_features", side_effect=dict):
            tables = group_tables(self.run, [self.group], [self.review], self.descriptions, provenance)
        self.assertEqual(set(tables), {"groups", "group_members", "proposal_ledger", "judgments", "image_descriptions"})
        for name, (rows, features) in tables.items():
            with self.subTest(table=name):
                self.assertTrue(rows)
                self.assertTrue(PROVENANCE_COLUMNS.items() <= features.items())
                for row in rows:
                    self.assertEqual({key: row[key] for key in PROVENANCE_COLUMNS}, provenance)

    def test_missing_metadata_fails_for_run_or_group_calibration(self) -> None:
        for run_condition, group_condition in (
            ("calibration_visible", "calibration_visible"),
            ("fixed_hidden", "calibration_visible"),
            ("calibration_visible", "fixed_hidden"),
        ):
            with self.subTest(run_condition=run_condition, group_condition=group_condition):
                self.run["conditions"] = [run_condition]
                self.group["condition"] = group_condition
                self.save_inputs()
                (self.run_dir / "calibration.json").unlink()
                self.assert_export_rejected("requires calibration.json")

    def test_metadata_presence_prevents_a_controlled_classification(self) -> None:
        self.run["conditions"] = ["fixed_hidden"]
        self.group["condition"] = "fixed_hidden"
        self.assertIs(self.rows(self.provenance())[0]["controlled_study_eligible"], False)

    def test_modified_or_missing_frozen_prompts_fail_before_output(self) -> None:
        for relative in (CALIBRATION_MATCHING_PROMPT, CALIBRATION_DESCRIPTION_PROMPT):
            path = self.run_dir / relative
            original = path.read_bytes()
            with self.subTest(prompt=relative, problem="modified"):
                path.write_bytes(b"X" * len(original))  # Same size: checksum must be checked.
                self.assert_export_rejected("modified frozen calibration snapshot")
            with self.subTest(prompt=relative, problem="missing"):
                path.unlink()
                self.assert_export_rejected("missing or modified frozen calibration snapshot")
            path.write_bytes(original)

    def test_missing_duplicate_and_escaping_fingerprints_are_rejected(self) -> None:
        original = copy.deepcopy(self.calibration["extra_spec_snapshots"])
        for relative in (CALIBRATION_MATCHING_PROMPT, CALIBRATION_DESCRIPTION_PROMPT):
            with self.subTest(missing=relative):
                self.calibration["extra_spec_snapshots"] = [item for item in original if item["path"] != relative]
                self.save_inputs()
                self.assert_export_rejected("missing frozen calibration prompt fingerprint")
        self.calibration["extra_spec_snapshots"] = [*original, original[0]]
        self.save_inputs()
        self.assert_export_rejected("duplicate calibration snapshot")
        self.calibration["extra_spec_snapshots"] = [{**original[0], "path": "../outside.md"}]
        self.save_inputs()
        self.assert_export_rejected("path escapes allowed root")

    def test_invalid_metadata_and_eligibility_flags_are_rejected(self) -> None:
        original = copy.deepcopy(self.calibration)
        for key, invalid in (
            ("study_kind", "controlled_study"), ("controlled_study_eligible", True),
            ("counts_toward_adaptive_update", True), ("controlled_study_eligible", "false"),
            ("counts_toward_adaptive_update", 0), ("extra_spec_snapshots", None),
            ("seed", 8), ("held_out_domain", "photo"), ("run_id", "wrong-run"),
        ):
            with self.subTest(key=key, value=invalid):
                self.calibration = {**original, key: invalid}
                self.save_inputs()
                self.assert_export_rejected("calibration.json")
        for content in ("[]", "{broken", "null"):
            with self.subTest(content=content):
                (self.run_dir / "calibration.json").write_text(content, encoding="utf-8")
                self.assert_export_rejected("calibration.json")

    def test_provenance_does_not_change_acceptance_or_mutate_inputs(self) -> None:
        before = copy.deepcopy((self.run, self.group, self.review, self.descriptions))
        files = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.run_dir.rglob("*") if path.is_file()}
        provenance = self.provenance()
        self.rows(provenance)
        self.assertEqual((self.run, self.group, self.review, self.descriptions), before)
        for path, expected in files.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), expected)
        self.assertEqual({path for path in self.run_dir.rglob("*") if path.is_file()}, set(files))
        for verdict, scope in (("reject", "individual"), ("unsure", "individual"), ("accept", "unreviewed")):
            with self.subTest(verdict=verdict, scope=scope):
                for receipt in self.review["derived_pair_receipt"]:
                    receipt.update(verdict=verdict, validation_scope=scope)
                self.assertEqual(self.rows(provenance), [])
        self.assert_export_rejected("no confirmed accepted")

    def test_fixture_parquet_export_preserves_provenance_and_separate_counts(self) -> None:
        try:
            import pyarrow.parquet as parquet
            pair_features()
        except ImportError:
            self.skipTest("datasets unavailable; pure provenance tests cover this environment")
        schemas = {}
        for mode in ("calibration", "legacy", "controlled_mixed"):
            with self.subTest(mode=mode):
                if mode == "legacy":
                    self.make_legacy()
                if mode == "controlled_mixed":
                    self.run.update(study_kind="controlled_study", controlled_study_eligible=True)
                    self.run["conditions"] = ["fixed_hidden", "adaptive_visible"]
                    (self.run_dir / "run.json").write_text(json.dumps(self.run), encoding="utf-8")
                    adaptive_group = copy.deepcopy(self.group)
                    adaptive_group.update(group_id="G-adaptive", condition="adaptive_visible")
                    for pair in adaptive_group["pairs"]:
                        pair["pair_id"] = f'adaptive-{pair["pair_id"]}'
                    (self.groups_dir / "adaptive.json").write_text(json.dumps(adaptive_group), encoding="utf-8")
                ledger = self.run_dir / "records" / "reviews.jsonl"
                if not ledger.exists() or mode == "controlled_mixed":
                    event_id = "E-adaptive" if mode == "controlled_mixed" else "E-fixture"
                    append_event(ledger, adaptive_group if mode == "controlled_mixed" else self.group, {
                        "event_id": event_id, "reviewer_id": "fixture-reviewer", "stage": "revised",
                        "inspection": {"mode": "highlighted_and_full_contact_sheet", "pair_ids": []},
                        "pair_validity": "accept", "coverage": "adequate", "exceptions": [], "pair_comments": [],
                        "raw_response": "Synthetic fixture review only.",
                    })
                    confirm_event(ledger, event_id, "fixture-reviewer", "Fixture confirmation only.")
                description_path = self.run_dir / "records" / "image_descriptions.jsonl"
                description_path.write_text("".join(json.dumps(row) + "\n" for row in self.descriptions), encoding="utf-8")
                before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.run_dir.rglob("*") if path.is_file()}
                output = self.root / f"{mode}-export"
                report = export_run(self.run_dir, self.groups_dir, self.pacs_root, output)
                self.assertEqual(report["status"], "passed")
                self.assertIn("datasets_reload", report["checks"])
                self.assertEqual(report["pair_counts"], {
                    "total": 4 if mode == "controlled_mixed" else 2,
                    "calibration": 2 if mode == "calibration" else 0,
                    "controlled_study_eligible": 4 if mode == "controlled_mixed" else 0,
                    "adaptive_update_eligible": 2 if mode == "controlled_mixed" else 0,
                })
                self.assertEqual(report["provenance"], self.provenance())
                self.assertEqual(json.loads((output / "validation_report.json").read_text()), report)
                self.assertEqual(report["files"]["grit_strict.parquet"]["rows"], 2 if mode == "controlled_mixed" else 1)
                for filename in report["files"]:
                    # Export validation already reloaded with datasets; inspect Arrow values
                    # directly to avoid a second cache with overly long Windows lock paths.
                    table = parquet.read_table(output / filename)
                    self.assertTrue(set(PROVENANCE_COLUMNS).issubset(table.column_names))
                    if filename in schemas:
                        self.assertTrue(table.schema.equals(schemas[filename], check_metadata=False))
                    schemas[filename] = table.schema
                    for row in table.to_pylist():
                        expected = {**self.provenance(), "counts_toward_adaptive_update": mode == "controlled_mixed" and row.get("group_id") == "G-adaptive"}
                        self.assertEqual({key: row[key] for key in PROVENANCE_COLUMNS}, expected)
                for row in read_jsonl(output / "invariant_pairs_metadata.jsonl"):
                    expected = {**self.provenance(), "counts_toward_adaptive_update": mode == "controlled_mixed" and row.get("group_id") == "G-adaptive"}
                    self.assertEqual({key: row[key] for key in PROVENANCE_COLUMNS}, expected)
                self.assertIn("not adaptive-update progress", (output / "README.md").read_text())
                self.assertEqual({path for path in self.run_dir.rglob("*") if path.is_file()}, set(before))
                for path, expected in before.items():
                    self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), expected)


if __name__ == "__main__":
    unittest.main()
