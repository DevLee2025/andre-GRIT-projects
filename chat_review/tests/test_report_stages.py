from __future__ import annotations

import copy
import html
import json
import struct
import tempfile
import unittest
import zlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from unittest.mock import patch

import jsonschema

from chat_review.common import ContractError, atomic_write_json, fingerprint, read_json, sha256_file, write_jsonl
from chat_review.html_report import build_report


ROOT = Path(__file__).resolve().parents[2]


class ReportParser(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__()
        self.cards: list[dict[str, Any]] = []
        self.tags: list[str] = []
        self._card: dict[str, Any] | None = None
        self._span: str | None = None
        self.feed(source)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        attributes = dict(attrs)
        if tag == "article":
            self._card = {**attributes, "images": [], "links": [], "badges": [], "position": "", "text": ""}
            self.cards.append(self._card)
        if self._card is None:
            return
        if tag == "img":
            self._card["images"].append(attributes)
        elif tag == "a":
            self._card["links"].append(attributes)
        elif tag == "span":
            self._span = attributes.get("class")
            if self._span == "badge":
                self._card["badges"].append("")

    def handle_data(self, data: str) -> None:
        if self._card is not None:
            self._card["text"] += data
            if self._span == "badge":
                self._card["badges"][-1] += data
            elif self._span == "pair-position":
                self._card["position"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._span = None
        elif tag == "article":
            self._card = None


def image_bytes(index: int) -> bytes:
    """Small, distinct, non-square PNG originals without an imaging dependency."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    width, height = index + 3, 2
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = (b"\x00" + bytes((index * 30, 80, 160)) * width) * height
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


class ReportStageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix=".report-stages-", dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inputs = self.root / "inputs"
        self.pacs_root = self.inputs / "pacs"
        self.pacs_root.mkdir(parents=True)
        pairs = []
        # Deliberately unsorted IDs and a multi-role member catch sorting/filtering leaks.
        for index, (pair_id, roles) in enumerate([
            ("P-012", ["medoid", "seeded_random"]),
            ("P-003", []),
            ("P-008", ["boundary"]),
            ("P-001", ["lowest_confidence"]),
        ]):
            images = []
            for offset in range(2):
                image_index = 2 * index + offset
                filename = f"image-{image_index}.png"
                (self.pacs_root / filename).write_bytes(image_bytes(image_index))
                images.append({"file": filename, "id": f"I-{image_index}", "class": "dog", "domain": "photo", "split": "train"})
            pairs.append({
                "pair_id": pair_id,
                "position": index + 1,
                "anchor": images[0],
                "candidate": images[1],
                "target_count": 1,
                "activity_pose_state": "standing",
                "spurious_axes": ["background"],
                "highlighted_roles": roles,
                "semantic_rationale": f"PRIVATE semantic rationale {index} <agrees>",
                "spurious_rationale": f"PRIVATE spurious rationale {index}",
                "uncertainty": f"PRIVATE uncertainty {index}",
                "confidence": 0.812341 + index / 100,
                "selection_score": 0.623451 + index / 100,
                "selection_scores": {"distance": f"PRIVATE selection score {index}"},
            })
        self.group = {
            "schema_version": 1,
            "run_id": "test-calibration",
            "group_id": "G-calibration",
            "condition": "calibration_visible",
            "calibration_notice": "Real-data calibration; these are not controlled experimental results.",
            "semantic_claim": "PRIVATE persuasive group claim",
            "coverage_summary": {"PRIVATE coverage axis": "PRIVATE coverage claim"},
            "reasons_group_may_fail": ["PRIVATE group failure reason"],
            "pairs": pairs,
        }
        (self.inputs / "group.json").write_text(json.dumps(self.group), encoding="utf-8")

    def render(self, stage: str) -> tuple[Path, str, ReportParser]:
        output = self.root / "reports" / f"{stage}.html"
        result = build_report(group=self.group, output_path=output, pacs_root=self.pacs_root, stage=stage)
        self.assertEqual(result, output)
        source = output.read_text(encoding="utf-8")
        return output, source, ReportParser(source)

    def test_initial_hides_evaluations_in_entire_html_including_attributes(self) -> None:
        forbidden = [
            "PRIVATE", "semantic_claim", "semantic rationale", "shared semantic claim",
            "spurious rationale", "spurious difference", "confidence", "uncertainty",
            "selection_score", "selection score", "claimed coverage", "reasons this group may fail",
        ]
        for pair in self.group["pairs"]:
            forbidden.extend([str(pair["confidence"]), str(pair["selection_score"])])
            for role in pair["highlighted_roles"]:
                forbidden.extend([role, role.replace("_", " ")])
        for condition in ("calibration_visible", "fixed_visible", "adaptive_visible", "fixed_hidden", "adaptive_hidden"):
            with self.subTest(condition=condition):
                self.group["condition"] = condition
                _, source, parsed = self.render("initial")
                # Inspect source, not just visible text: attributes, comments and scripts count.
                for token in forbidden:
                    self.assertNotIn(token.lower(), html.unescape(source).lower())
                self.assertEqual([card["badges"] for card in parsed.cards], [
                    ["Audit example"], [], ["Audit example"], ["Audit example"],
                ])
                self.assertNotIn("script", parsed.tags)
                self.assertNotIn("form", parsed.tags)
                self.assertEqual("domain: photo" in source, condition.endswith("_visible"))

    def test_stages_preserve_complete_membership_order_and_highlighting(self) -> None:
        expected_ids = [pair["pair_id"] for pair in self.group["pairs"]]
        expected_focus = [bool(pair["highlighted_roles"]) for pair in self.group["pairs"]]
        memberships = []
        for stage in ("initial", "revised"):
            with self.subTest(stage=stage):
                output, _, parsed = self.render(stage)
                self.assertEqual([card["id"] for card in parsed.cards], expected_ids)
                self.assertEqual([card["position"] for card in parsed.cards], ["1", "2", "3", "4"])
                self.assertEqual(["focused" in card["class"].split() for card in parsed.cards], expected_focus)
                membership = []
                for card, pair in zip(parsed.cards, self.group["pairs"]):
                    self.assertEqual(len(card["images"]), 2)
                    contents = [(output.parent / image["src"]).read_bytes() for image in card["images"]]
                    self.assertEqual(contents, [(self.pacs_root / pair[side]["file"]).read_bytes() for side in ("anchor", "candidate")])
                    membership.append((card["id"], contents))
                memberships.append(membership)
        self.assertEqual(memberships[0], memberships[1])

    def test_revised_reveals_actual_roles_legend_and_escaped_explanations(self) -> None:
        _, source, parsed = self.render("revised")
        self.assertEqual([card["badges"] for card in parsed.cards], [pair["highlighted_roles"] for pair in self.group["pairs"]])
        self.assertIn("Highlighted roles indicate why a pair was selected for inspection, not whether it is valid.", source)
        self.assertIn(html.escape(self.group["semantic_claim"]), source)
        for pair in self.group["pairs"]:
            for key in ("semantic_rationale", "spurious_rationale", "uncertainty", "confidence"):
                self.assertIn(html.escape(str(pair[key])), source)
        self.assertIn("PRIVATE coverage claim", source)
        self.assertIn("PRIVATE group failure reason", source)
        self.assertNotIn("agrees", parsed.tags)
        self.assertNotIn("Audit example", source)

    def test_calibration_notice_is_plain_text_in_both_stages(self) -> None:
        notice = 'Real-data calibration <script>alert("x")</script> & <b>not controlled results</b>.'
        self.group["calibration_notice"] = notice
        for stage in ("initial", "revised"):
            with self.subTest(stage=stage):
                _, source, parsed = self.render(stage)
                self.assertIn(f'<p class="notice calibration-notice">{html.escape(notice)}</p>', source)
                self.assertNotIn("script", parsed.tags)
                self.assertNotIn("b", parsed.tags)

    def test_calibration_notice_is_optional(self) -> None:
        del self.group["calibration_notice"]
        for stage in ("initial", "revised"):
            with self.subTest(stage=stage):
                _, source, _ = self.render(stage)
                self.assertNotIn("calibration-notice", source)

    def test_original_links_open_unchanged_images_in_new_tabs(self) -> None:
        for stage in ("initial", "revised"):
            with self.subTest(stage=stage):
                output, source, parsed = self.render(stage)
                for card, pair in zip(parsed.cards, self.group["pairs"]):
                    self.assertEqual(len(card["links"]), 2)
                    for link, image, side in zip(card["links"], card["images"], ("anchor", "candidate")):
                        self.assertEqual(link["href"], image["src"])
                        self.assertEqual(link["target"], "_blank")
                        self.assertTrue({"noopener", "noreferrer"}.issubset(link["rel"].split()))
                        self.assertEqual((output.parent / link["href"]).read_bytes(), (self.pacs_root / pair[side]["file"]).read_bytes())
                self.assertIn("aspect-ratio:1", source)
                self.assertIn("object-fit:contain", source)
                self.assertIn("@media (max-width:620px)", source)

    def test_rendering_does_not_mutate_inputs_or_the_initial_artifact(self) -> None:
        self.group["domain_selection"] = {"policy": "unconstrained", "evidence": "Immutable evidence"}
        self.group["pairs"][0]["domain_selection"] = {"policy": "same_domain_required", "source": "Immutable source"}
        original_group = copy.deepcopy(self.group)
        originals = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.inputs.rglob("*") if path.is_file()}
        initial, _, _ = self.render("initial")
        initial_artifacts = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in initial.parent.rglob("*") if path.is_file()}
        self.render("revised")
        self.assertEqual(self.group, original_group)
        for path, (content, modified) in {**originals, **initial_artifacts}.items():
            with self.subTest(path=path.relative_to(self.root)):
                self.assertEqual(path.read_bytes(), content)
                self.assertEqual(path.stat().st_mtime_ns, modified)
        self.assertEqual({path for path in self.inputs.rglob("*") if path.is_file()}, set(originals))

    def test_initial_source_is_independent_of_policy_and_evidence(self) -> None:
        forbidden = [
            "domain_selection", "domain-selection", "domain selection", "selection evidence", "selection source",
            "cross_domain_required", "same_domain_required", "unconstrained", "policy unknown",
            "Different domains required", "Domain difference not required", "Same domain required",
            "Observed domain relationship", "legacy group", "pair override", "PRIVATE domain evidence",
            "PRIVATE domain source", "selection requirement",
        ]
        for condition in ("calibration_visible", "fixed_visible", "adaptive_visible", "fixed_hidden", "adaptive_hidden"):
            for candidate_domain in ("photo", "cartoon"):
                self.group["condition"] = condition
                self.group.pop("domain_selection", None)
                for pair in self.group["pairs"]:
                    pair.pop("domain_selection", None)
                    pair["candidate"]["domain"] = candidate_domain
                _, baseline, _ = self.render("initial")
                policies = ["unknown", "unconstrained", "same_domain_required" if candidate_domain == "photo" else "cross_domain_required"]
                for policy in policies:
                    with self.subTest(condition=condition, candidate_domain=candidate_domain, policy=policy):
                        self.group["domain_selection"] = {
                            "policy": policy, "evidence": 'PRIVATE domain evidence <script>"&"</script>',
                            "source": "PRIVATE domain source group",
                        }
                        self.group["pairs"][0]["domain_selection"] = {
                            "policy": "unknown", "evidence": "PRIVATE domain evidence override",
                            "source": "PRIVATE domain source override",
                        }
                        _, source, parsed = self.render("initial")
                        self.assertEqual(source, baseline)
                        for token in forbidden:
                            self.assertNotIn(token.lower(), html.unescape(source).lower())
                        self.assertNotIn("script", parsed.tags)
                        self.assertEqual("domain: photo" in source, condition.endswith("_visible"))

    def test_revised_distinguishes_requirement_from_observed_relationship(self) -> None:
        cases = [
            ("cross_domain_required", "cartoon", "Different domains required", "Different domains"),
            ("unconstrained", "cartoon", "Domain difference not required", "Different domains"),
            ("unconstrained", "photo", "Domain difference not required", "Same domain"),
            ("same_domain_required", "photo", "Same domain required", "Same domain"),
            ("unknown", "cartoon", "Domain-selection policy unknown", "Different domains"),
            (None, "cartoon", "Domain-selection policy unknown", "Different domains"),
        ]
        for policy, domain, label, relationship in cases:
            with self.subTest(policy=policy, domain=domain):
                self.group.pop("domain_selection", None)
                if policy is not None:
                    self.group["domain_selection"] = {"policy": policy}
                for pair in self.group["pairs"]:
                    pair["candidate"]["domain"] = domain
                _, source, parsed = self.render("revised")
                self.assertIn("Group domain-selection policy", source)
                self.assertIn(f"<strong>{label}</strong>", source)
                for card in parsed.cards:
                    self.assertIn(f"Domain selection (inherited group policy): {label}", card["text"])
                    self.assertIn(f"Observed domain relationship (metadata): {relationship}", card["text"])
                if policy in ("unknown", None):
                    self.assertNotIn("Different domains required", source)
                    self.assertNotIn("Domain difference not required", source)
                if policy is None:
                    self.assertIn("No domain-selection policy was recorded for this legacy group.", source)
                    self.assertIn("Observed domain differences do not establish a selection requirement.", source)
                if policy == "unconstrained":
                    self.assertIn("Either same-domain or different-domain pairs were permitted.", source)
                    self.assertNotIn("Different domains required", source)

    def test_revised_hidden_metadata_discloses_relationship_without_domain_labels(self) -> None:
        self.group["domain_selection"] = {"policy": "unconstrained"}
        self.group["pairs"][0]["candidate"]["domain"] = "cartoon"
        for condition in ("fixed_hidden", "adaptive_hidden", "fixed_visible"):
            with self.subTest(condition=condition):
                self.group["condition"] = condition
                _, source, parsed = self.render("revised")
                self.assertIn("Observed domain relationship (metadata): Different domains", parsed.cards[0]["text"])
                self.assertIn("Observed domain relationship (metadata): Same domain", parsed.cards[1]["text"])
                for label in ("photo", "cartoon"):
                    self.assertEqual(label in source, condition.endswith("_visible"))
        del self.group["pairs"][0]["candidate"]["domain"]
        _, _, parsed = self.render("revised")
        self.assertIn("Observed domain relationship (metadata): Unknown; valid domain metadata is unavailable", parsed.cards[0]["text"])

    def test_mixed_policies_scope_overrides_and_evidence_to_their_pairs(self) -> None:
        self.group["domain_selection"] = {
            "policy": "cross_domain_required", "evidence": "GROUP EVIDENCE", "source": "GROUP SOURCE",
        }
        for pair in self.group["pairs"]:
            pair["candidate"]["domain"] = "cartoon"
        overrides = [
            ("unconstrained", "photo", "Domain difference not required"),
            ("same_domain_required", "photo", "Same domain required"),
            ("unknown", "cartoon", "Domain-selection policy unknown"),
        ]
        for index, (policy, domain, _) in enumerate(overrides):
            self.group["pairs"][index]["candidate"]["domain"] = domain
            self.group["pairs"][index]["domain_selection"] = {
                "policy": policy, "evidence": f"PAIR EVIDENCE {index}", "source": f"PAIR SOURCE {index}",
            }
        self.render("initial")  # Overrides govern validation at both stages.
        _, source, parsed = self.render("revised")
        self.assertIn("Applies to all pairs except those with an explicit pair override below.", source)
        self.assertEqual(source.count("GROUP EVIDENCE"), 1)
        self.assertEqual(source.count("GROUP SOURCE"), 1)
        for index, (_, _, label) in enumerate(overrides):
            self.assertIn(f"Domain selection (pair override): {label}", parsed.cards[index]["text"])
            self.assertIn(f"PAIR EVIDENCE {index}", parsed.cards[index]["text"])
            self.assertIn(f"PAIR SOURCE {index}", parsed.cards[index]["text"])
            for other_index, card in enumerate(parsed.cards):
                if other_index != index:
                    self.assertNotIn(f"PAIR EVIDENCE {index}", card["text"])
        self.assertIn("Domain selection (inherited group policy): Different domains required", parsed.cards[3]["text"])
        self.assertNotIn("pair override", parsed.cards[3]["text"])

    def test_policy_objects_validate_in_schema_and_before_any_asset_copy(self) -> None:
        schema = read_json(ROOT / "specs/group.schema.json")
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        validator.validate(self.group)  # Legacy omission remains valid.
        invalid = [
            None, "cross_domain_required", [], {}, {"policy": "forced"}, {"policy": None},
            {"policy": []}, {"policy": True}, {"policy": "unknown", "evidence": {}},
            {"policy": "unconstrained", "source": ["prompt"]}, {"policy": "unknown", "typo": "x"},
        ]
        for scope in (self.group, self.group["pairs"][-1]):
            for selection in invalid:
                for stage in ("initial", "revised"):
                    with self.subTest(scope="group" if scope is self.group else "pair", selection=selection, stage=stage):
                        scope["domain_selection"] = selection
                        with self.assertRaises(jsonschema.ValidationError):
                            validator.validate(self.group)
                        with self.assertRaisesRegex(ContractError, "domain_selection"):
                            self.render(stage)
                        self.assertFalse((self.root / "reports").exists())
            for policy in ("cross_domain_required", "same_domain_required", "unconstrained", "unknown"):
                scope["domain_selection"] = {"policy": policy, "evidence": "Text", "source": "Text"}
                validator.validate(self.group)
            del scope["domain_selection"]

    def test_required_relationships_reject_contradictions_and_missing_metadata_before_publication(self) -> None:
        for scope in (self.group, self.group["pairs"][-1]):
            for policy, bad_domains in (
                ("cross_domain_required", ("photo", None, "", "invalid", [])),
                ("same_domain_required", ("cartoon", None, "", "invalid", [])),
            ):
                for bad_domain in bad_domains:
                    for pair in self.group["pairs"]:
                        pair["candidate"]["domain"] = "cartoon" if policy == "cross_domain_required" else "photo"
                    # A late failure must still leave no earlier images or HTML behind.
                    self.group["pairs"][-1]["candidate"]["domain"] = bad_domain
                    scope["domain_selection"] = {"policy": policy}
                    for stage in ("initial", "revised"):
                        with self.subTest(policy=policy, bad_domain=bad_domain, stage=stage):
                            with self.assertRaisesRegex(ContractError, f"pair P-001: domain_selection policy {policy}"):
                                self.render(stage)
                            self.assertFalse((self.root / "reports").exists())
            del scope["domain_selection"]

    def test_domain_evidence_and_source_are_escaped_plain_text(self) -> None:
        selection = {
            "policy": "unconstrained",
            "evidence": '<script>alert("group")</script> & <em>evidence</em>',
            "source": '<a href="https://example.test/">Group prompt</a>',
        }
        override = {
            "policy": "same_domain_required",
            "evidence": '<img src="x" onerror="alert(1)"> Pair evidence',
            "source": '<iframe src="x"></iframe> Pair prompt',
        }
        self.group["domain_selection"] = selection
        self.group["pairs"][0]["domain_selection"] = override
        _, source, parsed = self.render("revised")
        for record in (selection, override):
            for field in ("evidence", "source"):
                self.assertIn(html.escape(record[field]), source)
                self.assertNotIn(record[field], source)
        for tag in ("script", "em", "iframe"):
            self.assertNotIn(tag, parsed.tags)
        self.assertEqual(parsed.tags.count("img"), 2 * len(self.group["pairs"]))
        self.assertEqual(parsed.tags.count("a"), 2 * len(self.group["pairs"]))

    def test_pair_override_does_not_imply_a_known_policy_for_legacy_group(self) -> None:
        self.group["pairs"][0]["candidate"]["domain"] = "cartoon"
        self.group["pairs"][0]["domain_selection"] = {"policy": "cross_domain_required"}
        _, source, parsed = self.render("revised")
        self.assertIn("No domain-selection policy was recorded for this legacy group.", source)
        self.assertIn("Domain selection (pair override): Different domains required", parsed.cards[0]["text"])
        self.assertIn("Domain selection (inherited group policy): Domain-selection policy unknown", parsed.cards[1]["text"])

    def calibration_fixture(self) -> tuple[Path, Path, Path, dict, dict, dict]:
        """Real temporary freeze/publication files; only pool loading and embeddings are mocked."""
        run = self.root / "calibration-run"
        project = self.root / "project"
        pacs = project / "web/public/pacs"
        pacs.mkdir(parents=True)
        draft = copy.deepcopy(self.group)
        mapping, descriptions, audit = {}, [], []
        for position, pair in enumerate(draft["pairs"], 1):
            aliases = []
            for role in ("anchor", "candidate"):
                image = pair.pop(role)
                image["domain"] = "photo" if role == "anchor" else "cartoon"
                image["sha256"] = sha256_file(self.pacs_root / image["file"])
                (pacs / image["file"]).write_bytes((self.pacs_root / image["file"]).read_bytes())
                alias = f"{position}-{role}"
                mapping[alias] = image
                pair[f"{role}_alias"] = alias
                aliases.append(alias)
                descriptions.append({"image_alias": alias, "description": {
                    "target_count": {"status": "observed", "minimum": 1, "maximum": 1},
                    "visible_category": {"status": "observed"},
                    "activity_pose_state": {"status": "observed"},
                }})
            pair["joint_pixel_check"] = {"outcome": "pass", "reviewer_type": "model", "evidence": "Fixture joint check"}
            audit.append({"pair_number": position, "aliases": aliases, "status": "pass"})
        draft_path = self.root / "draft.json"
        atomic_write_json(draft_path, draft)
        descriptions_path = run / "records/image_descriptions.jsonl"
        write_jsonl(descriptions_path, descriptions)
        atomic_write_json(run / "records/descriptions_frozen.json", {
            "descriptions": fingerprint(descriptions_path, "records/image_descriptions.jsonl"), "sources": [],
        })
        for suffix in ("", "_v2", "_v3", "_v4"):
            atomic_write_json(run / f"records/joint_independent_audit{suffix}.json", audit if not suffix else [])
        atomic_write_json(run / "spec_snapshot/specs/group.schema.json", read_json(ROOT / "specs/group.schema.json"))
        prompt_path = run / "calibration_spec_snapshot/prompts/calibration_matching_v1.md"
        prompt_path.parent.mkdir(parents=True)
        prompt_path.write_bytes((ROOT / "prompts/calibration_matching_v1.md").read_bytes())
        config = {
            "run_id": draft["run_id"], "seed": 5, "target_domain": "sketch", "judgment_stage_for_export": "revised",
            "candidate_pool": {"image_count": len(mapping)},
        }
        calibration = {
            "target_group_size": len(draft["pairs"]),
            "extra_spec_snapshots": [fingerprint(prompt_path, prompt_path.relative_to(run).as_posix())],
        }
        return run, project, draft_path, config, calibration, mapping

    def test_calibration_freezes_enforced_policy_provenance_without_initial_disclosure(self) -> None:
        from chat_review.calibration import finalize

        run, project, draft_path, config, calibration, mapping = self.calibration_fixture()
        draft = read_json(draft_path)
        draft["domain_selection"] = {"policy": "unknown"}
        draft["pairs"][0]["domain_selection"] = {"policy": "unknown"}
        atomic_write_json(draft_path, draft)
        draft_bytes = draft_path.read_bytes()
        with patch("chat_review.calibration.inputs", return_value=(config, calibration, mapping)), \
                patch("chat_review.calibration.audit_roles", return_value={"definitions": {}}):
            result = finalize(run, project, draft_path)
            self.assertEqual(result["status"], "ready_for_initial_human_review")
            group_path = run / f"records/groups/{draft['group_id']}.json"
            frozen_group = read_json(group_path)
            selection = frozen_group["domain_selection"]
            self.assertEqual(selection["policy"], "cross_domain_required")
            self.assertIn("prompt requires cross-domain pairs", selection["evidence"])
            self.assertIn("finalize rejects every same-domain pair", selection["evidence"])
            prompt = calibration["extra_spec_snapshots"][0]
            self.assertIn(prompt["path"], selection["source"])
            self.assertIn(prompt["sha256"], selection["source"])
            self.assertIn("chat_review.calibration.finalize", selection["source"])
            self.assertEqual(frozen_group["proposal_prompt_sha256"], prompt["sha256"])
            self.assertEqual(frozen_group["pairs"][0]["domain_selection"], selection)
            report = run / f"review/{draft['group_id']}/initial.html"
            for value in selection.values():
                self.assertNotIn(value, report.read_text(encoding="utf-8"))
                self.assertNotIn(html.escape(value), report.read_text(encoding="utf-8"))
            validation = read_json(run / "records/proposal_validation.json")
            self.assertEqual(validation["group"]["sha256"], sha256_file(group_path))
            published = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in run.rglob("*") if path.is_file()}
            with self.assertRaisesRegex(FileExistsError, "already been published"):
                finalize(run, project, draft_path)
            for path, (content, modified) in published.items():
                self.assertEqual(path.read_bytes(), content)
                self.assertEqual(path.stat().st_mtime_ns, modified)
        self.assertEqual(draft_path.read_bytes(), draft_bytes)

    def test_calibration_rejects_untrue_or_invalid_policies_before_freeze(self) -> None:
        from chat_review.calibration import finalize

        run, project, draft_path, config, calibration, mapping = self.calibration_fixture()
        original = read_json(draft_path)
        with patch("chat_review.calibration.inputs", return_value=(config, calibration, mapping)), \
                patch("chat_review.calibration.audit_roles") as audit_roles:
            for scope in ("group", "pair"):
                for policy in ("unconstrained", "same_domain_required", "made_up"):
                    with self.subTest(scope=scope, policy=policy):
                        draft = copy.deepcopy(original)
                        record = draft if scope == "group" else draft["pairs"][-1]
                        record["domain_selection"] = {"policy": policy}
                        atomic_write_json(draft_path, draft)
                        with self.assertRaisesRegex(ContractError, "domain_selection"):
                            finalize(run, project, draft_path)
                        self.assertFalse((run / "records/groups").exists())
                        self.assertFalse((run / "review").exists())
            audit_roles.assert_not_called()

    def test_calibration_mandatory_cross_domain_check_precedes_provenance(self) -> None:
        from chat_review.calibration import finalize

        run, project, draft_path, config, calibration, mapping = self.calibration_fixture()
        mapping["4-candidate"]["domain"] = mapping["4-anchor"]["domain"]
        with patch("chat_review.calibration.inputs", return_value=(config, calibration, mapping)), \
                patch("chat_review.calibration.audit_roles") as audit_roles:
            with self.assertRaisesRegex(ContractError, "pair must cross domains"):
                finalize(run, project, draft_path)
            audit_roles.assert_not_called()
        self.assertFalse((run / "records/groups").exists())
        self.assertFalse((run / "review").exists())


if __name__ == "__main__":
    unittest.main()
