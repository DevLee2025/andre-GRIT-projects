---
configs:
- config_name: pairs
  data_files:
  - split: train
    path: invariant_pairs.parquet
- config_name: grit_strict
  data_files:
  - split: train
    path: grit_strict.parquet
- config_name: grit_broad
  data_files:
  - split: train
    path: grit_broad.parquet
- config_name: groups
  data_files:
  - split: train
    path: groups.parquet
- config_name: group_members
  data_files:
  - split: train
    path: group_members.parquet
- config_name: judgments
  data_files:
  - split: train
    path: judgments.parquet
- config_name: proposal_ledger
  data_files:
  - split: train
    path: proposal_ledger.parquet
- config_name: image_descriptions
  data_files:
  - split: train
    path: image_descriptions.parquet
---

# PACS grouped invariant pairs

This release is `pacs-calibration-20261010-01 / revised-20261011-v2`: one confirmed accepted pair (CAL-001-02), nine rejected proposals retained in the proposal table, and unchanged initial/revised human decisions. It is feedback-exposed calibration, with no controlled-study or adaptive-update eligibility. Local Parquet/image readback passed; downstream GRIT training has not been run.

`domain_selection_addendum.json` records a later disclosure: the original matching process required different domains and was restricted to photo/cartoon guitars. The frozen proposal rows remain the originals; the addendum is not a new human judgment or a retrospectively edited proposal. Local HTML paths in the addendum identify original workspace artifacts, not hosted web URLs.

One row per accepted pair. `anchor_image` and `paired_image` are embedded for the Hugging Face viewer. The strict GRIT table contains individually reviewed pairs. The broad experimental table additionally contains pairs explicitly covered by a full-contact-sheet group scan. Group, proposal, judgment, and description provenance are normalized into separate configs. JSON-valued provenance uses strings to avoid empty-struct Parquet failures.

Study eligibility is separate from review scope: `eligible_strict` and `eligible_broad` describe inspection only. Filter on `controlled_study_eligible` for controlled-study data and on `counts_toward_adaptive_update` before computing adaptive counters. Real-data calibration has `study_kind=real_data_calibration` and both flags false, even after human acceptance. `prompt_sha256` identifies the matching prompt; `description_prompt_sha256` identifies the independent description prompt when available (blank for legacy runs). See `validation_report.json` for this export's provenance and separate calibration/controlled pair counts. These counts are export totals, not adaptive-update progress.

Runs without an explicit eligibility declaration default to `study_kind=legacy_unspecified` and `controlled_study_eligible=false`; a prompt snapshot, condition name, or accepted smoke fixture does not establish scientific eligibility. An explicit boolean `controlled_study_eligible=true` establishes eligibility only for `study_kind=controlled_study` (the kind inferred when that explicit flag is supplied alone). Adaptive eligibility is computed per group: only declared `adaptive_hidden`/`adaptive_visible` groups in an eligible controlled run can qualify, and an explicit run-level `counts_toward_adaptive_update=false` vetoes it. Fixed, calibration, legacy-unknown, and rows without a group condition never qualify for adaptive counters. The run-level provenance summary has no group condition and therefore keeps its adaptive flag false; use row flags and the separate pair totals.
