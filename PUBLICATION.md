# Public snapshot — October 12, 2026

This repository is a curated snapshot of Andre's GRIT pair-validation work. The working directory and previous repository history were not rewritten. Publication to this personal repository was authorized; transfer or integration into the Inouye Lab organization is pending separate permission.

## Retained as research evidence

- Current implementation, schemas, prompts, methodological plans, semantic criteria, and definition history.
- Initial and revised human reviews, exact responses, confirmation events, scope receipts, timestamps, and review-ledger hashes. Short confirmation language is retained because it establishes consent to the recorded judgment; no general-purpose chat transcript is included.
- Frozen run specifications, candidate membership/splits, image mappings, individual descriptions, model checks, proposals, draft corrections, confidence limitations, and original initial/revised HTML assets.
- The successful versioned Parquet release: accepted pairs with embedded images plus separate proposal, judgment, membership, group, and description tables. Calibration is explicitly excluded from controlled-study comparisons.
- The earlier smoke-test review, marked as a workflow fixture rather than scientific pair-generation evidence.

## Omitted from the public copy

- Local session resume state, tool/browser troubleshooting records, one-off transition and rendering scripts, failed empty exports, and redundant diagnostic contact sheets. The preserved ledgers/receipts contain the actual review stages.
- Agent runtime identifiers and nicknames. The methodological description-task instructions remain, with portable paths.
- Local caches, credentials/settings directories, dependency installations, server participant storage, administrative documents, and temporary outputs.
- The full PACS corpus, old CAPTCHA collection archives/duplicate PDF and Arrow exports, and the previous repository's Git history. These are not deleted locally. Earlier primary collection data remains in the linked legacy repository; download tools and the calibration image subset are included here.
- The old automatic GitHub Pages deployment workflow. Saving a research snapshot does not deploy a site.

## Explicit public adaptations

`PROPOSER_STUDY_PLAN.md` replaces a machine-specific local manuscript link with a public GRIT-project reference and notes that the manuscript is not bundled. The scientific argument is retained.

`records/description_assignments.json` retains each methodological assignment but replaces the machine-specific root with relative paths and removes tool-session identifiers. Each entry stores a hash of its original message and identifies itself as a public projection. These assignment messages were not the frozen prompt or review hash-chain input; those remain unchanged.

Root onboarding documentation and the calibration README were updated to explain the public layout and avoid links to omitted local debug files. `chat_review/requirements.txt` includes `jsonschema`, which the implementation and tests use.

The legacy VLM README replaces machine-specific output links with portable local paths and distinguishes label agreement from semantic validity. The export test now generates its own test-only images so it can run in a fresh clone without downloading PACS; no research pixels or judgments were altered.

Frozen group/specification files, descriptions, review ledgers, review responses, initial/revised HTML and assets, the definition archive, and Parquet tables retain their original bytes. Historical validation files are dated observations, not claims that every recorded local path is available in this repository. The definition archive's internal links use the original `specs/` base, as documented in its README.

`PUBLICATION_MANIFEST.json` enumerates published files and their hashes. `tools/validate_public_snapshot.py` checks that manifest and the scientific relationships it can verify locally. It does not establish semantic correctness, upstream license rights, model-output replay, or downstream robustness.

## Attribution and limits

PACS source: [flwrlabs/pacs](https://huggingface.co/datasets/flwrlabs/pacs); local source/split notes are in `specs/pacs_source.json`. Dataset images and other third-party materials retain their existing terms; this snapshot does not relicense them. The GRIT manuscript is not bundled, and exact compatibility with the lab's current training loader remains to be tested.

The scientific result currently consists of one small, feedback-exposed guitar calibration. One accepted pair and no changed post-reveal decisions do not establish collection quality, explanation effectiveness, or GRIT robustness across PACS.
