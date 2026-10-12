# First real PACS chat calibration

Status: **initial and revised reviews confirmed; local export validated**. Group: `CAL-20261010-001`. The human reports reading the explanations and explicitly keeps the judgments unchanged: 02 accepted, nine rejected, coverage incomplete. The [confirmed receipt](records/reviews/2026-10-11-revised-receipt.md) carries forward the displayed inspection scopes (01–08 individual; 09–10 group_scan), without inferring new inspection.

The accepted pair is available in [the versioned Parquet release](exports/revised-20261011-v2/invariant_pairs.parquet); [validation](exports/revised-20261011-v2/validation_report.json) reloads all eight tables and verifies embedded source-image hashes. This public snapshot includes that release. It is calibration data, not controlled-study evidence or a completed GRIT robustness experiment.

The [dated domain-selection addendum](review/CAL-20261010-001/revised-domain-disclosure-20261011.html) makes explicit that different domains were required, using photo/cartoon guitars. The original [initial](review/CAL-20261010-001/initial.html) and [revised](review/CAL-20261010-001/revised.html) pages remain unchanged. Reading the earlier reveal does not establish that the human read this later addendum. Its evidence is in `records/disclosures/2026-10-11-domain-selection.json`, also copied into the release.

The [working-definition history](../../specs/model_working_definition.md) records evolving hypotheses separately from this run's frozen rubric. The next [comparison plan](../../specs/subject_centered_calibration_v2.md) evaluates both exact-count and primary-subject rules on identical pairs. Comparing both was approved; a new default was not chosen. No next image group is published yet.

Open [the initial review page](review/CAL-20261010-001/initial.html) locally after downloading this repository. It is a self-contained folder with 20 copied image assets. No web server, API key, or network image request is required. Keep `initial_assets/` beside `initial.html`. The HTML, member order, asset hashes and image decoding were checked directly; automated rendered-browser layout verification was not completed.

## What was prepared

- Seed `20261010`; current local PACS manifest and all eligible source images fingerprinted.
- Local 80/10/10 split retained. Proposals use **train only** and exclude the whole sketch domain. The eligible source-training pool has 4,850 images. No downstream classifier training or target-domain evaluation occurred.
- Seeded sample of 40 photo and 40 cartoon guitar images, described individually in four separate agent contexts before matching. Opaque filenames and instructions withheld metadata from those description tasks; there was no operating-system isolation.
- Ten final photo-to-cartoon proposals, with twenty distinct images. Matching used saved observations followed by joint pixel checks. All ten have a passing independent model check for their exact final image identities. Model checks are not human acceptance.
- Stored summaries, uncertainties, uncalibrated confidence and actual computed audit roles. Initial HTML contains only neutral audit badges; no persuasive summary, rationale, confidence or evaluative role names.
- Existing project embeddings choose audit highlights only. Their hashes and exact formulas are in the group record; original checkpoint provenance remains unverified. They did not choose the pairs or prove their validity.

This is **feedback-exposed calibration**, not a clean fixed/adaptive experiment. It does not count toward condition updates. Exact model revision, token totals and cost were not exposed by the chat runtime and are not invented. The seed replays sampling and audit selection, not model text generation; saved output files preserve those observations.

## Review flow

1. Human reviews the initial page and states what was actually inspected, pair validity, exceptions, and coverage judgment in chat.
2. Append the exact response and parsed receipt to `records/reviews.jsonl`; ask the human to confirm the receipt.
3. After confirmation, render the revised page from the **same frozen group record**, keeping membership, order and highlights unchanged. Do not reveal stored rationale before initial review.
4. Record and confirm the revised judgment separately. This run's export decision stage is **revised**.
5. Export accepted pairs only after confirmed judgments. Strict requires individual inspection; broad also permits explicit full-sheet group scans. `sample_inference` remains disabled. Use a new versioned export directory; never overwrite previous exports.

At initial delivery, no human review event or acceptance existed. The subsequent initial response and unchanged revised response are now recorded and confirmed in the hash-chain ledger. The versioned release contains one accepted pair in each of strict/broad/all-pairs, all ten proposals and memberships, four review/confirmation events, and all 80 descriptions. Local interchange validation is complete; an end-to-end test against a specific external GRIT loader remains separate work. Use the validated `revised-20261011-v2` directory; the failed empty development attempt is omitted from this public snapshot.

For this calibration, the human requested the reveal in the same message as the initial judgment, before the parsed receipt was shown. The initial receipt was confirmed in the later unchanged-judgment reply. The ledger preserves that sequence rather than claiming the intended confirmation-before-reveal order was followed exactly.

## Evidence files

- `run.json`, `calibration.json`: frozen configuration, source and study eligibility.
- `inputs/description_mapping.jsonl`: alias-to-source mapping and source image hashes.
- `description_packages/batch-*/descriptions.jsonl` and `inspection_log.json`: independent outputs and viewed-original logs.
- `records/image_descriptions.jsonl`, `descriptions_frozen.json`: joined observations and their checksums, saved before matching.
- `records/shortlist*.json`, `group-draft*.json`: pre-review drafts retained with their revisions. These are **not accepted pair data**.
- `records/joint_independent_audit*.json`: first audit and explicit replacement checks. Later files supersede only named draft positions.
- `records/groups/CAL-20261010-001.json`: final frozen proposal, concise explanations, metadata, checks, role formulas and feature hashes.
- `records/proposal_validation.json`: source-only, no-reuse, duplicate, schema, decoding and initial-stage checks.
- `records/reviews.jsonl` and `records/reviews/`: exact initial/revised human responses, confirmed receipts, and rubric feedback.
- `exports/revised-20261011-v2/validation_report.json`: local Parquet/image validation and calibration eligibility.
- `records/disclosures/2026-10-11-domain-selection.json`: dated selection-policy disclosure after the original revised review.

Local session state and tool-debug transition records are omitted; the scientific records above retain their original bytes. See [publication notes](../../PUBLICATION.md) for the explicit public adaptations and retained limitations.

The first draft contained two same-domain pairs because the coordinator inferred domain from appearance. The manifest guard rejected publication; the same four images were re-paired into cross-domain pairs and independently checked again. Prior drafts and that correction are preserved. The coordinator also replaced uncertain crop/category candidates. Nonselected pool images are not automatically invalid.

Do not regenerate the group or descriptions after human review. Corrections require a new version with explicit provenance. The previous smoke group remains unchanged and excluded from scientific exports.
