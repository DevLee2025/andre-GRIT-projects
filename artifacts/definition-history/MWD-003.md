# Model working definition of an invariant pair

Current revision: **MWD-003**. Recorded 2026-10-11. Context: feedback-exposed PACS calibration.

This is the model's stated, inspectable decision policy: criteria, assumptions, uncertainty, and changes attributed to feedback. It is a working research record, not a measurement of model weights or a guarantee that every proposal follows the policy correctly. Image checks and human judgments remain separate evidence.

## Current working interpretation — MWD-003

An invariant pair should preserve the task-relevant subject meaning while differing in observable depiction features that do not change that meaning. For this calibration, subject meaning is assessed through **class, subject structure, state/activity, and relevant interactions**. Count has two competing interpretations to compare, not a newly settled default.

- **Class:** require compatible visible category evidence, not just agreement of dataset labels. Proportions alone do not establish guitar versus ukulele across artistic styles.
- **Structure:** record concrete visible similarities and contradictions. Guitar body contour/cutaways, pick guards, headstocks, and f holes are candidate criteria motivated by human rejection. They remain recorded concerns; they have not all become mandatory matching constraints. Class-specific criteria need an explicit codebook and effective version.
- **State and interactions:** distinguish a displayed guitar, a held guitar, and a guitar being played. Record visible evidence for the relation. Background flowers or drawn musical notes alone do not establish an action by the subject; contextual suggestion and depicted interaction have separate fields.
- **Depiction:** image-plane rotation, left/right orientation, color, rendering style, and moderate viewpoint changes can differ when structure and state remain verifiable. Rotation is not the same as a change in articulated pose. Color/pattern neutrality was explicitly stated for this guitar review; do not turn it into an untested universal rule for every class and task.
- **Visibility:** cropping and occlusion may remove evidence. A hidden or unresolved feature is unknown, not absent and not automatically matching. Preserve the baseline's whole/detail restrictions until a prospective rubric explicitly changes them.
- **Count:** compare (A) equal total visible target-class count with (B) one independently identified primary subject in each image, allowing incidental extras only if they do not alter the primary subject's state or relationships. Record all extra subjects under both rules. Ambiguous or coequal subjects do not justify convenient primary selection.
- **Compatibility heuristic:** ask whether the visible structures could depict the same kind of individual object under depiction changes. This is a screen for contradictions, not evidence that the objects are actually identical. Require positive matching evidence; lack of visible contradiction alone is insufficient. It cannot override a state mismatch or uncertain required field.
- **Spurious variation:** record background, palette, lighting, texture, viewpoint, crop, and composition separately. More variation never compensates for a semantic failure. A different PACS domain is a sampling constraint or an observation, not proof of an invariant pair.
- **Group quality:** pair validity and group coverage are distinct. Count classes, domain relationships, states, nuisance axes, repeated images, and unresolved cases. Acceptance of a representative pair does not imply acceptance of the rest.

Operational judgments use **match / mismatch / unknown**, with visible evidence and a reason code. A required-field unknown leads to abstention, not a forced agreement. The aim is a reproducible lab convention whose reliability and downstream effect can be measured, not a universal proof of image meaning.

## What is active, approved, or still tentative?

| Item | Status and effective boundary |
| --- | --- |
| Frozen class + exact count + coarse activity/pose/state v1 | Still governs CAL-20261010-001; never rewrite that run's interpretation |
| Subject-centered interpretation above | Current calibration working hypothesis; prospective analysis guidance |
| Compare exact count and primary subject on identical next-calibration pairs | Explicitly approved by the human on 2026-10-11 |
| Replace the default count rule with primary subject | Not approved or inferred |
| Mandatory fine structural criteria | Proposed concerns for later human review; see potential_review_criteria.md |
| Definition history and delayed domain-policy disclosure | Explicitly requested on 2026-10-11; applies to future review packets |
| Controlled fixed/adaptive conditions | Keep their own frozen definition/prompt revisions; this shared calibration file is not live input to fixed conditions |

## Visible change history

Entries below are append-only. Corrections add a new entry. Baseline reconstructions are labeled rather than presented as contemporaneous model observations.

### MWD-001 — baseline reconstruction (recorded 2026-10-11)

**Source boundary:** the rubric snapshotted before CAL-20261010-001 was proposed, in `runs/pacs-calibration-20261010-01/spec_snapshot/specs/pair_definition.md`.

**Working definition:** preserve visible class, exact target count, and coarse activity/pose/state; then seek observable variation on the seven nuisance axes. Unknown critical attributes abstain. Fine object construction is not a mandatory gate. This reconstruction describes the documented policy used, not an independently recorded mental state.

**Scope:** historical baseline for the existing group. The original document and hash remain in the run snapshot.

### MWD-002 — fine structure as a concern (recorded 2026-10-11)

**Evidence:** initial review of CAL-20261010-001, saved 2026-10-10. Only 02 accepted; nine rejected. Earlier smoke feedback also raised architecture, dog type, hair/facial hair, and carried objects.

**Change from MWD-001:** coarse class/count/state can miss construction differences important to this reviewer. Add explicit observation of body contour/cutaway, pick guard, headstock, and f holes. Keep color and surface pattern separate; proportions alone do not establish instrument type. Store these as concerns rather than silently elevating them to universal requirements.

**Why:** the reviewer distinguished structure from depiction in concrete pair-specific examples. A change in acceptance rate alone would not identify which criterion should change.

**Effect:** prospective concerns list only. Existing proposals, confidence values and baseline remain unchanged. This is a retrospective synthesis of saved feedback, not a claim that this file existed before the review.

### MWD-003 — subject focus and competing count rules (recorded 2026-10-11)

**Evidence:** revised response to CAL-20261010-001; explicit answer “Compare both rules (recommended)”; request for a visible definition history and delayed domain disclosure.

**Change from MWD-002:** prioritize the subject's structure/state/relationships over incidental context; distinguish depiction rotation from articulated pose; treat crop as potentially missing evidence; use same-instance plausibility only as a tentative compatibility screen. Keep exact count and primary subject as separate hypotheses for the next calibration. Explicitly separate imposed domain constraints from observed domain differences.

**Why:** the human identified possible over-weighting of background context and unresolved count semantics. The two count policies must be compared on the same pairs under the same remaining rubric to isolate their difference.

**Effect:** current working hypothesis and next comparison plan. Human decisions are unchanged (02 accepted, nine rejected). No revised-review feedback is fed into a controlled adaptive condition, and calibration events do not increment its counters.

## Update procedure

1. After review, append a dated revision with old/new criteria, exact source feedback references, reason, uncertainties, status, affected condition, and first future group/batch to which it applies. Update the current interpretation and revision pointer. Preserve earlier entries. Save the complete revised file as `artifacts/definition-history/<revision>.md` with a companion JSON fingerprint and source references; never overwrite an archived revision. The first archive is MWD-003, and its baseline entries are explicitly retrospective reconstructions.
2. Record “no definition change” when feedback does not warrant a change. Do not invent a change after every judgment.
3. A new run snapshots and hashes this file alongside the governing rubric. The snapshot is a record of knowledge at creation, **not automatic promotion of every hypothesis to an active rule**.
4. For a later authorized adaptive update, freeze a new condition-specific definition/prompt artifact with its parent revision and eligible initial-review event IDs before proposing the next batch. Five completed initial groups AND at least 20 individually audited pairs remain the current update threshold. The update mechanism must be implemented/validated before claiming automated updates.
5. Fixed conditions continue using their original snapshot. Revised-review insights can inform future calibration/study designs but do not enter the within-run initial-feedback adaptive channel. A shared evolving notebook must not contaminate fixed or metadata-blind proposer contexts.
6. Initial reviewer HTML never embeds this evolving interpretation, the domain constraint, or rationale in hidden elements. Reveal the **proposal-time** definition reference and selection rule after initial review. A later addendum is clearly dated; it never replaces the original explanation.

## Source records

- [Frozen baseline](../runs/pacs-calibration-20261010-01/spec_snapshot/specs/pair_definition.md)
- [Initial human response](../runs/pacs-calibration-20261010-01/records/reviews/2026-10-10-initial-response.md)
- [Revised human response](../runs/pacs-calibration-20261010-01/records/reviews/2026-10-11-revised-response.md)
- [Count comparison approval](../runs/pacs-calibration-20261010-01/records/reviews/2026-10-11-count-policy-answer.json)
- [History/disclosure request](../runs/pacs-calibration-20261010-01/records/reviews/2026-10-11-definition-and-disclosure-request.md)
- [Potential criteria](potential_review_criteria.md)
- [Next calibration plan](subject_centered_calibration_v2.md)
