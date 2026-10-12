from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from chat_review.common import ContractError, sha256_file
from chat_review.create_run import create_run, load_candidate_pool
from chat_review.export_hf import export_run
from chat_review.html_report import build_report
from chat_review.make_smoke_group import make_smoke_group
from chat_review.review import append_event, confirm_event, derive_pair_receipt


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "web" / "public" / "manifest.json"


def sample_group(root: Path) -> dict:
    for index in range(4):
        (root / f"image-{index}.jpg").write_bytes(b"fake-image")
    return {
        "group_id": "G-001",
        "condition": "fixed_hidden",
        "semantic_claim": "one standing dog",
        "coverage_summary": {"background": "varied"},
        "reasons_group_may_fail": ["one crop is tight"],
        "pairs": [
            {
                "pair_id": "P-001",
                "anchor": {"file": "image-0.jpg", "domain": "photo", "class": "dog"},
                "candidate": {"file": "image-1.jpg", "domain": "sketch", "class": "dog"},
                "highlighted_roles": ["seeded_random"],
                "semantic_rationale": "same visible class, count, and pose",
                "spurious_rationale": "background and texture differ",
                "uncertainty": "none",
                "confidence": 0.9,
            },
            {
                "pair_id": "P-002",
                "anchor": {"file": "image-2.jpg", "domain": "photo", "class": "dog"},
                "candidate": {"file": "image-3.jpg", "domain": "cartoon", "class": "dog"},
                "highlighted_roles": [],
                "semantic_rationale": "same visible class, count, and pose",
                "spurious_rationale": "palette differs",
                "uncertainty": "minor crop",
                "confidence": 0.7,
            },
        ],
    }


class CandidatePoolTests(unittest.TestCase):
    def test_train_pool_excludes_entire_target_domain(self) -> None:
        _, pool = load_candidate_pool(MANIFEST, "train", "sketch")
        self.assertTrue(pool)
        self.assertTrue(all(row["split"] == "train" for row in pool))
        self.assertTrue(all(row["domain"] != "sketch" for row in pool))
        self.assertEqual(len(pool), len({row["id"] for row in pool}))

    def test_immutable_run_snapshots_specs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            run = create_run(
                project_root=ROOT,
                output_root=output,
                manifest_path=MANIFEST,
                run_id="unit-run",
                seed=7,
                model="test-model",
                reasoning_effort="test",
                proposal_split="train",
                target_domain="photo",
                judgment_stage="initial",
                group_sizes=[10, 20],
                conditions=["fixed_hidden", "fixed_visible"],
                pacs_root=ROOT / "web" / "public" / "pacs",
                hash_images=False,
            )
            config = json.loads((run / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(config["candidate_pool"]["domains"], ["art_painting", "cartoon", "sketch"])
            self.assertGreater(len(config["spec_snapshot"]), 5)
            definition = run / "spec_snapshot/specs/model_working_definition.md"
            definition_record = next(item for item in config["spec_snapshot"] if item["path"] == "specs/model_working_definition.md")
            self.assertEqual(definition.read_bytes(), (ROOT / "specs/model_working_definition.md").read_bytes())
            self.assertEqual(sha256_file(definition), definition_record["sha256"])
            with self.assertRaises(FileExistsError):
                create_run(
                    project_root=ROOT,
                    output_root=output,
                    manifest_path=MANIFEST,
                    run_id="unit-run",
                    seed=7,
                    model="test-model",
                    reasoning_effort="test",
                    proposal_split="train",
                    target_domain="photo",
                    judgment_stage="initial",
                    group_sizes=[10],
                    conditions=["fixed_hidden"],
                    pacs_root=ROOT / "web" / "public" / "pacs",
                    hash_images=False,
                )


class ReviewScopeTests(unittest.TestCase):
    def test_full_scan_makes_unfocused_members_group_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            group = sample_group(Path(temp))
            event = {
                "inspection": {"mode": "highlighted_and_full_contact_sheet", "pair_ids": []},
                "pair_validity": "accept_with_exclusions",
                "exceptions": [{"pair_id": "P-002", "verdict": "reject", "comment": "pose differs"}],
                "pair_comments": [],
            }
            receipt = derive_pair_receipt(group, event)
            self.assertEqual(receipt[0]["validation_scope"], "individual")
            self.assertEqual(receipt[1]["validation_scope"], "individual")
            self.assertEqual(receipt[1]["verdict"], "reject")

    def test_highlighted_only_leaves_other_members_unreviewed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            group = sample_group(Path(temp))
            event = {
                "inspection": {"mode": "highlighted_only", "pair_ids": []},
                "pair_validity": "accept",
                "exceptions": [],
                "pair_comments": [],
            }
            receipt = derive_pair_receipt(group, event)
            self.assertEqual([row["validation_scope"] for row in receipt], ["individual", "unreviewed"])

    def test_ledger_is_append_only_and_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            group = sample_group(root)
            ledger = root / "reviews.jsonl"
            event = {
                "event_id": "E-001",
                "reviewer_id": "R-001",
                "stage": "initial",
                "inspection": {"mode": "highlighted_only", "pair_ids": []},
                "pair_validity": "accept",
                "coverage": "adequate",
                "exceptions": [],
                "pair_comments": [],
                "raw_response": "I inspected the highlighted pair and accept it.",
            }
            result = append_event(ledger, group, event)
            self.assertEqual(result["previous_record_hash"], None)
            confirmation = confirm_event(ledger, "E-001", "R-001", "next")
            self.assertEqual(confirmation["confirms_event_id"], "E-001")
            with self.assertRaises(ContractError):
                append_event(ledger, group, event)
            with self.assertRaises(ContractError):
                confirm_event(ledger, "E-001", "R-001", "next")


class HtmlTests(unittest.TestCase):
    def test_initial_report_contains_all_pairs_and_no_form(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            group = sample_group(root)
            output = root / "review" / "initial.html"
            build_report(group=group, output_path=output, pacs_root=root, stage="initial")
            source = output.read_text(encoding="utf-8")
            self.assertIn("P-001", source)
            self.assertIn("P-002", source)
            self.assertNotIn("<form", source.lower())
            self.assertNotIn("Semantic rationale:", source)
            self.assertNotIn("domain: photo", source)
            self.assertEqual(len(list((root / "review" / "initial_assets").iterdir())), 4)

    def test_revised_visible_report_reveals_metadata_and_reasoning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            group = sample_group(root)
            group["condition"] = "fixed_visible"
            output = root / "revised.html"
            build_report(group=group, output_path=output, pacs_root=root, stage="revised")
            source = output.read_text(encoding="utf-8")
            self.assertIn("Semantic rationale:", source)
            self.assertIn("domain: photo", source)
            self.assertIn("Reasons this group may fail", source)


class SchemaTests(unittest.TestCase):
    def test_all_json_specs_parse(self) -> None:
        for path in (ROOT / "specs").glob("*.json"):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))


class ExportTests(unittest.TestCase):
    def test_export_is_row_oriented_reloadable_and_scope_filtered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = create_run(
                project_root=ROOT,
                output_root=root,
                manifest_path=MANIFEST,
                run_id="export-run",
                seed=11,
                model="test-model",
                reasoning_effort="test",
                proposal_split="train",
                target_domain=None,
                judgment_stage="initial",
                group_sizes=[10],
                conditions=["fixed_hidden"],
                pacs_root=ROOT / "web" / "public" / "pacs",
                hash_images=False,
            )
            groups = run / "records" / "groups"
            groups.mkdir()
            group_path = groups / "group.json"
            make_smoke_group(MANIFEST, group_path, seed=11, size=2, condition="fixed_hidden")
            group = json.loads(group_path.read_text(encoding="utf-8"))
            # Exercise export plumbing without requiring the downloaded PACS corpus.
            # The manifest provides stable metadata; test-only pixels live in Temp.
            from PIL import Image
            fixture_images = root / "fixture-images"
            for pair in group["pairs"]:
                for image in (pair["anchor"], pair["candidate"]):
                    destination = fixture_images / image["file"]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    Image.new("RGB", (8, 8), color=(30, 60, 90)).save(destination)
            for pair in group["pairs"]:
                pair["target_count"] = 1
                pair["activity_pose_state"] = "standing"
                pair["spurious_axes"] = ["background"]
                pair["confidence"] = 0.5
            group_path.write_text(json.dumps(group, indent=2), encoding="utf-8")
            described_ids = {
                image["id"]
                for pair in group["pairs"]
                for image in (pair["anchor"], pair["candidate"])
            }
            with (run / "records" / "image_descriptions.jsonl").open("w", encoding="utf-8") as handle:
                for image_id in sorted(described_ids):
                    handle.write(json.dumps({
                        "image_id": image_id,
                        "image_alias": f"opaque-{len(image_id)}",
                        "description_version": "smoke-v1",
                        "description": {"concise_description": "Smoke-test description."},
                        "raw_output_ref": "smoke-only"
                    }) + "\n")
            event = {
                "event_id": "E-EXPORT",
                "reviewer_id": "R-001",
                "stage": "initial",
                "inspection": {"mode": "highlighted_and_full_contact_sheet", "pair_ids": []},
                "pair_validity": "accept",
                "coverage": "adequate",
                "exceptions": [],
                "pair_comments": [],
                "raw_response": "I inspected the highlighted pair and scanned the full contact sheet.",
            }
            ledger = run / "records" / "reviews.jsonl"
            append_event(ledger, group, event)
            confirm_event(ledger, "E-EXPORT", "R-001", "next")
            report = export_run(run, groups, fixture_images, run / "exports" / "v1")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["files"]["invariant_pairs.parquet"]["rows"], 2)
            self.assertEqual(report["files"]["grit_strict.parquet"]["rows"], 2)


if __name__ == "__main__":
    unittest.main()
