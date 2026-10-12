# Potential review criteria — running list

Status: proposals for later human review, **not active matching requirements**.

Created: 2026-10-09. Keep this list cumulative: add evidence and dated decisions rather than deleting earlier concerns. A future approved criterion needs an operational definition and a new rubric version before governing proposals. Existing groups keep their original rubric.

## Human direction

> Save them as recorded concerns for reviewer judgement, but also create a running list (could just be a .txt or .md file) of potential new criteria to add. I will review the potential new criteria later.

For now, retain the concerns in the review record. They may inform the human's judgment but do not become universal matching constraints, automatic rejections, or an instruction to alter a fixed-condition prompt.

## Candidates

All entries below originate from the human's initial review of `SMOKE-20260930-10` on 2026-10-09. These are reviewer-reported observations, not a fresh independent visual assessment. The source group is a layout fixture, not a model-generated scientific proposal set.

| ID | Potential criterion | Motivating observation | Questions before adoption | Status |
| --- | --- | --- | --- | --- |
| C-001 | Architectural form or house subtype | SMOKE-004: the houses are not the same style. | Which visible structural differences matter: silhouette, roof form, floors, or building subtype? Distinguish depicted architecture from artistic rendering style, which is intended to vary. | Proposed; reviewer judgment only |
| C-002 | Held-object identity and subject–object interaction | SMOKE-005: fan versus book; holding objects alone did not establish equivalent meaning for the reviewer. | Must object categories match, or only the activity/interaction? When is an accessory incidental, and when does it define the depicted activity? | Proposed; reviewer judgment only |
| C-003 | Clothing and headwear with apparent role significance | SMOKE-005: hatless subject versus subject with a military cap. | Should headwear presence, clothing form, or visible role cues be preserved? Do not infer occupation or personal identity solely from appearance. | Proposed; reviewer judgment only |
| C-004 | Apparent life stage and subject presentation | SMOKE-005/006: the reviewer distinguishes the depicted people, including a middle-aged man and a woman with a baby. | Does apparent age/presentation matter independently of count and activity? What can be reliably observed in a stylized image? Separate this question from the already-required subject-count check. | Proposed; reviewer judgment only |
| C-005 | Dog subtype or visible morphology | SMOKE-008: the reviewer describes "two different species of dog." | Should matching preserve visible shape, ears, muzzle, coat form, or a defensible subtype? Preserve the original wording as feedback; do not treat species or breed as verified labels. Distinguish anatomy from drawing-style changes. | Proposed; reviewer judgment only |
| C-006 | Hair and facial-hair configuration | SMOKE-009: fully bald subject versus hair and a goatee. | Is hair presence/shape part of essential meaning or task-irrelevant appearance for this experiment? Is shape more relevant than color? Would a mandatory match unnecessarily exclude useful variation? | Proposed; reviewer judgment only |

## Existing-rule issues, not new criteria

- **Target-subject count:** the reported adult-with-baby versus single-person contrast in SMOKE-006 already warrants checking the existing count rule. A baby counts as a person when visible. Whether the images actually differ in count still requires the pixel check.
- **Activity/pose/state:** if carrying, reading, holding a fan, or interacting with a baby changes the coarse state, the existing rubric may already explain a rejection. The proposed criteria above concern distinctions beyond that coarse state.
- **Coverage uncertainty:** the reviewer needs a broader PACS view to judge contextual coverage. Record `coverage=unsure`; do not infer a particular missing category or a new pair-validity criterion.

## Decision log

- 2026-10-09 — Human requested that all new details remain recorded reviewer concerns, with candidates accumulated here for later review. No criterion was promoted to the active rubric.

## Adding future entries

Use a stable criterion ID, a concrete visible feature, the source group/pair IDs and review date, an operational-definition question, and a status (`proposed`, `approved_for_future_version`, or `declined`). On approval, link the new rubric version and effective run boundary. Preserve the original feedback even when a proposed interpretation is declined.

## Evidence

- [Initial human response](../artifacts/chat-review-smoke/reviews/2026-10-09-initial-response.md)
- [Pending review receipt](../artifacts/chat-review-smoke/reviews/2026-10-09-receipt.md)
- [Active pair definition](pair_definition.md)
