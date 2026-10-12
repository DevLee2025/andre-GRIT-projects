# Potential review criteria — running list

Status: proposals for later human review, **not active matching requirements**.

Created: 2026-10-09. Keep this list cumulative: add evidence and dated decisions rather than deleting earlier concerns. A future approved criterion needs an operational definition and a new rubric version before governing proposals. Existing groups keep their original rubric.

## Human direction

> Save them as recorded concerns for reviewer judgement, but also create a running list (could just be a .txt or .md file) of potential new criteria to add. I will review the potential new criteria later.

For now, retain the concerns in the review record. They may inform the human's judgment but do not become universal matching constraints, automatic rejections, or an instruction to alter a fixed-condition prompt.

## Candidates

Entries C-001 through C-006 originate from the human's initial review of `SMOKE-20260930-10` on 2026-10-09. These are reviewer-reported observations, not a fresh independent visual assessment. That source group is a layout fixture, not a model-generated scientific proposal set. Later calibration feedback is recorded separately below.

| ID | Potential criterion | Motivating observation | Questions before adoption | Status |
| --- | --- | --- | --- | --- |
| C-001 | Architectural form or house subtype | SMOKE-004: the houses are not the same style. | Which visible structural differences matter: silhouette, roof form, floors, or building subtype? Distinguish depicted architecture from artistic rendering style, which is intended to vary. | Proposed; reviewer judgment only |
| C-002 | Held-object identity and subject–object interaction | SMOKE-005: fan versus book; holding objects alone did not establish equivalent meaning for the reviewer. | Must object categories match, or only the activity/interaction? When is an accessory incidental, and when does it define the depicted activity? | Proposed; reviewer judgment only |
| C-003 | Clothing and headwear with apparent role significance | SMOKE-005: hatless subject versus subject with a military cap. | Should headwear presence, clothing form, or visible role cues be preserved? Do not infer occupation or personal identity solely from appearance. | Proposed; reviewer judgment only |
| C-004 | Apparent life stage and subject presentation | SMOKE-005/006: the reviewer distinguishes the depicted people, including a middle-aged man and a woman with a baby. | Does apparent age/presentation matter independently of count and activity? What can be reliably observed in a stylized image? Separate this question from the already-required subject-count check. | Proposed; reviewer judgment only |
| C-005 | Dog subtype or visible morphology | SMOKE-008: the reviewer describes "two different species of dog." | Should matching preserve visible shape, ears, muzzle, coat form, or a defensible subtype? Preserve the original wording as feedback; do not treat species or breed as verified labels. Distinguish anatomy from drawing-style changes. | Proposed; reviewer judgment only |
| C-006 | Hair and facial-hair configuration | SMOKE-009: fully bald subject versus hair and a goatee. | Is hair presence/shape part of essential meaning or task-irrelevant appearance for this experiment? Is shape more relevant than color? Would a mandatory match unnecessarily exclude useful variation? | Proposed; reviewer judgment only |

## Guitar calibration feedback — 2026-10-10

Source: initial human review of `CAL-20261010-001`, condition `calibration_visible`. The reviewer accepts pair 02 and rejects the other nine. Coverage is incomplete: only guitars and insufficient domain variety. These statements record human judgments; they do not retroactively change the frozen descriptions, proposer rationales, metadata or rubric. The original wording is retained in the linked response.

| ID | Potential criterion | Motivating observation | Questions before adoption | Status |
| --- | --- | --- | --- | --- |
| C-007 | Guitar body contour and cutaway structure | CAL-001-01: a fully rounded body versus a single cutaway, despite a preserved pick guard. The reviewer identifies body-shape differences as a common rejection reason without assigning that reason to every other pair. | How should full/partial cutaways and body contour be represented across drawing styles and views? Separate structural contour from proportion and simple image-plane rotation. | Proposed; reviewer judgment only |
| C-008 | Pick guard presence and configuration | CAL-001-03: presence versus absence; CAL-001-05: different pick guards. | Must presence, placement and shape match? How should stylized omission or genuinely hidden/occluded details be recorded? Do not equate color or surface pattern with structural configuration. | Proposed; reviewer judgment only |
| C-009 | Headstock structure | CAL-001-05: discernably different headstocks. | Which visible structural distinctions matter, and what evidence separates a shape change from viewpoint, proportions or artistic simplification? | Proposed; reviewer judgment only |
| C-010 | F-hole presence and related body construction | CAL-001-05: presence versus absence of f holes. | Should f-hole presence be mandatory when observable? How should absence, occlusion and unresolvable stylization be distinguished without inventing construction details? | Proposed; reviewer judgment only |

### Features the reviewer did not use as semantic differences

- **Color and surface pattern:** explicitly not treated as semantic detail in this guitar review. Preserve this distinction when considering construction features. This is not a new claim that every color/pattern change in every object class is task-irrelevant.
- **Proportions alone:** explicitly not sufficient for a semantic rejection or definitive guitar-versus-ukulele label. Art style and the framing of an isolated instrument can alter apparent proportions. The reference to a possible ukulele in pair 03 is an example of typing ambiguity, not verified ground truth or permission to relabel PACS.
- **Coverage versus validity:** acceptance of pair 02 does not establish group coverage. The coverage concern is a request for broader class/domain evidence in future groups, not permission to draw proposals from the held-out domain or evaluation splits.

These clarifications remain attached to the review and the prospective criteria list. No entry has been promoted to the active matching rubric; no adaptive update has occurred.

## Existing-rule issues, not new criteria

- **Target-subject count:** the reported adult-with-baby versus single-person contrast in SMOKE-006 already warrants checking the existing count rule. A baby counts as a person when visible. Whether the images actually differ in count still requires the pixel check.
- **Activity/pose/state:** if carrying, reading, holding a fan, or interacting with a baby changes the coarse state, the existing rubric may already explain a rejection. The proposed criteria above concern distinctions beyond that coarse state.
- **Coverage uncertainty:** the reviewer needs a broader PACS view to judge contextual coverage. Record `coverage=unsure`; do not infer a particular missing category or a new pair-validity criterion.

## Decision log

- 2026-10-09 — Human requested that all new details remain recorded reviewer concerns, with candidates accumulated here for later review. No criterion was promoted to the active rubric.
- 2026-10-10 — Recorded C-007–C-010 and the color/pattern/proportion distinctions from the first real calibration review. Initial decisions are 1 accept and 9 reject; derived scope receipt remains open to confirmation/correction. The same-message `next.` authorizes the explanation reveal, not a revised judgment or a new rubric version.

## Adding future entries

### 2026-10-11 additions after explanation reveal

Source: [revised response](../runs/pacs-calibration-20261010-01/records/reviews/2026-10-11-revised-response.md). Human judgments did not change. The human explicitly approved comparing both count policies; no default was selected. The [working-definition history](model_working_definition.md) records the model's prospective interpretation.

| ID | Candidate clarification | Operational question | Status |
| --- | --- | --- | --- |
| C-011 | Image rotation/orientation versus subject pose | Record image-plane rotation separately from articulated pose and coarse state. A rotated displayed guitar remains displayed if observable. Existing baseline already permits left/right orientation and modest viewpoint changes. | Reviewer guidance; clarify prospective coding without rewriting earlier rationales |
| C-012 | Primary-subject semantics versus exact target count | Select a primary subject independently per image before matching; retain total count and interactions. Ambiguous/coequal subjects cannot be discarded to rescue a match. | Approved for comparative calibration only; default count unresolved |
| C-013 | Depicted subject state versus incidental context | Separate background/context cues from direct evidence of holding, playing, or other interaction. Musical notes alone suggest context; they do not prove that an instrument is being played. | Proposed operational clarification |
| C-014 | Same-instance plausibility as a structural screen | Could the visible structures be compatible under depiction changes? Require positive evidence, distinguish unknown from absent, and do not claim actual identity. Class-specific observability differs. | Tentative reviewer heuristic; not an identity requirement |
| C-015 | Crop and observability | Does a crop merely hide a feature, or establish a different required state? Keep unknown evidence separate from mismatch; do not automatically relax existing whole/detail rules. | Proposed; needs calibration |

The response refers to music notes in pair 04; the frozen explanation places notation in 03 and 06. Preserve the original wording, treat the subject/context guidance as general, and do not silently alter pair provenance.

Decision update: 2026-10-11 — initial receipt confirmed and revised judgments explicitly unchanged. One acceptance, nine rejections; inherited scopes remain eight individual and two group_scan. None of these calibration events count toward controlled adaptive updates.

Use a stable criterion ID, a concrete visible feature, the source group/pair IDs and review date, an operational-definition question, and a status (`proposed`, `approved_for_future_version`, or `declined`). On approval, link the new rubric version and effective run boundary. Preserve the original feedback even when a proposed interpretation is declined.

## Evidence

- [Initial human response](../artifacts/chat-review-smoke/reviews/2026-10-09-initial-response.md)
- [Pending review receipt](../artifacts/chat-review-smoke/reviews/2026-10-09-receipt.md)
- [Active pair definition](pair_definition.md)
- [Guitar calibration initial response](../runs/pacs-calibration-20261010-01/records/reviews/2026-10-10-initial-response.md)
- [Guitar calibration review receipt](../runs/pacs-calibration-20261010-01/records/reviews/2026-10-10-initial-receipt.md)
