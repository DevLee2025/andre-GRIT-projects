# Chat-only grouped review tools

This package implements the reproducibility layer for the grouped PACS invariant-pair workflow. It does not call a proposer model yet. The first implementation slice freezes run inputs, protects the proposal split and held-out domain, creates static review packets, and converts chat reviews into an append-only scope receipt.

Run commands from the repository root.

## Create an immutable run

```powershell
python -m chat_review.create_run `
  --run-id pilot-001 `
  --seed 20260930 `
  --model gpt-6-astra `
  --reasoning-effort ultra `
  --proposal-split train `
  --target-domain sketch `
  --judgment-stage revised
```

The tool writes `runs/pilot-001/`, snapshots and hashes all governing specs, hashes every eligible image, and produces a candidate pool containing only source-domain training images. Existing run directories are never overwritten. `--skip-image-hashes` exists only for local development fixtures.

New runs also snapshot `specs/model_working_definition.md`, the evolving calibration definition with a visible change history. Its proposed criteria remain distinct from the governing rubric. Fixed conditions retain their snapshots; future adaptive changes require separate condition-specific versions at authorized update boundaries.

## Build a local smoke-test review artifact

The smoke group checks layout and file handling. Its pairs are selected by class/domain metadata and are **not** scientific proposals.

```powershell
python -m chat_review.make_smoke_group `
  --manifest web/public/manifest.json `
  --output runs/pilot-001/records/smoke-group.json `
  --seed 20260930 `
  --size 10

python -m chat_review.html_report `
  --group runs/pilot-001/records/smoke-group.json `
  --output runs/pilot-001/review/smoke-initial.html `
  --pacs-root web/public/pacs `
  --stage initial
```

The HTML copies only the referenced images into an adjacent asset directory, has no forms or network requests, and shows every pair. `--stage revised` reveals stored explanations and coverage claims.

New groups should record `domain_selection` with a `policy` of `cross_domain_required`, `unconstrained`, or `same_domain_required`, plus evidence for how selection was constrained. Pair-level overrides are allowed. The revised page reveals this selection rule separately from the observed domain relationship; the initial page omits it completely. Legacy records with no rule show `unknown` on reveal. Do not infer a forced rule from the final images. Existing frozen artifacts are preserved; later disclosures are versioned addenda.

## Append a chat review

Create a JSON event from the human's chat response and run:

```powershell
python -m chat_review.review `
  --group runs/pilot-001/records/group-001.json `
  --event review-event.json `
  --ledger runs/pilot-001/records/reviews.jsonl
```

An event declares what the reviewer inspected. The tool derives `individual`, `group_scan`, or `unreviewed` for every member and returns the receipt that should be shown in chat. The review remains pending until the reviewer confirms the receipt:

```powershell
python -m chat_review.review `
  --group runs/pilot-001/records/group-001.json `
  --confirm-event-id reviewer-a-group-001-initial-1 `
  --reviewer-id reviewer-a `
  --ledger runs/pilot-001/records/reviews.jsonl
```

Reviews and confirmations are stored in a tamper-evident hash chain. `sample_inference` is intentionally unavailable in this pilot.

Minimal event shape:

```json
{
  "event_id": "reviewer-a-group-001-initial-1",
  "reviewer_id": "reviewer-a",
  "stage": "initial",
  "inspection": {
    "mode": "highlighted_and_full_contact_sheet",
    "pair_ids": []
  },
  "pair_validity": "accept_with_exclusions",
  "coverage": "incomplete",
  "exceptions": [
    {"pair_id": "P-001-07", "verdict": "reject", "comment": "Activity differs."}
  ],
  "pair_comments": [
    {"pair_id": "P-001-03", "comment": "I checked this pair closely; both dogs are sitting.", "establishes_individual_review": true}
  ],
  "missing_coverage": "No indoor backgrounds.",
  "comment": "The remaining pairs preserve the stated coarse pose.",
  "raw_response": "I scanned the full contact sheet..."
}
```

Inspection modes are `highlighted_only`, `highlighted_and_full_contact_sheet`, `full_contact_sheet_no_focused_inspection`, and `explicit_pair_ids`.

## Export confirmed reviews

```powershell
python -m chat_review.export_hf `
  --run-dir runs/pilot-001 `
  --pacs-root web/public/pacs `
  --output runs/pilot-001/exports/v1
```

The versioned output directory must not exist. The exporter creates viewer-ready `invariant_pairs.parquet`, `grit_strict.parquet`, and `grit_broad.parquet`, along with normalized group, membership, proposal, judgment, and description tables. It reloads every Parquet through `datasets` and writes `validation_report.json`. This verifies the local interchange contract; an end-to-end smoke test against the PI's exact GRIT loader still requires that loader or its repository.
