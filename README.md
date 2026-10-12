# Andre's GRIT pair-validation projects

Research tools for collecting and reviewing candidate invariant image pairs for **Geometric Robustness via Invariant Training (GRIT)**. Current work shifts from human selection in a CAPTCHA-style app to **model-proposed groups, human review in chat, and a static HTML image viewer**.

This is an independent development repository. Integration with the Inouye Lab organization is pending permission; this repository does not claim lab endorsement. [GRIT research code](https://github.com/inouye-lab/GRIT) is a separate project.

## Current result — October 12, 2026

- The chat-review pipeline freezes run specifications and data eligibility, renders initial/revised HTML, records human judgments in a hash-chain ledger, and exports accepted pairs with embedded images in Hugging Face-compatible Parquet.
- First real calibration: 80 independently described guitar images, ten photo/cartoon pair proposals, and one lab reviewer. **One pair accepted, nine rejected; judgments unchanged after explanation reveal.** Coverage was judged incomplete. This small, deliberately narrow calibration is not an estimate of PACS-wide acceptance or robustness.
- Pair 02 is the sole accepted pair in the strict and broad exports. Rejections, raw review responses, descriptions, proposal revisions, and uncertainty remain available as research evidence.
- The model's stated working definition has a visible change history. Domain-selection requirements appear in the explanation reveal, separately from the domains the images happen to have.
- Next: compare exact-count and primary-subject interpretations on the same pairs, broaden class/domain coverage, and assess reliability before downstream GRIT evaluation.

No downstream robustness result is claimed. The tools do not yet automatically call a proposer API or implement the complete controlled adaptive-condition scheduler. The current calibration was coordinated through chat and is excluded from controlled fixed/adaptive comparisons.

## Start here

| Resource | Purpose |
| --- | --- |
| [Chat workflow](chat_review/README.md) | Commands and data contracts |
| [Grouped-review plan](CHAT_GROUP_REVIEW_PLAN.md) | Current methodological design |
| [Review protocol](specs/review_protocol.md) | Initial/revised judgments, scope, and confirmation |
| [Working definition and history](specs/model_working_definition.md) | Current interpretation, evidence, and pending decisions |
| [Potential criteria](specs/potential_review_criteria.md) | Suggestions not silently promoted to requirements |
| [Next calibration design](specs/subject_centered_calibration_v2.md) | Paired comparison of the two count rules |
| [Real calibration](runs/pacs-calibration-20261010-01/README.md) | Frozen inputs, complete group, review stages, and export |
| [Publication notes](PUBLICATION.md) | What was retained, omitted, or adapted for this public snapshot |

The [earlier proposer study plan](PROPOSER_STUDY_PLAN.md) is retained for the rationale behind the experimental conditions. Its custom participant-app design was superseded by grouped review in chat. [SPEC.md](SPEC.md) and [MIGRATION.md](MIGRATION.md) document the older CAPTCHA app rather than the current chat workflow.

## Inspect the saved calibration without downloading PACS

Clone or download this repository, then open these files locally with their adjacent asset directories intact:

1. [Initial contact sheet](runs/pacs-calibration-20261010-01/review/CAL-20261010-001/initial.html): no model explanation or confidence.
2. [Original explanation reveal](runs/pacs-calibration-20261010-01/review/CAL-20261010-001/revised.html): frozen model rationales.
3. [Later domain-policy disclosure](runs/pacs-calibration-20261010-01/review/CAL-20261010-001/revised-domain-disclosure-20261011.html): explicitly records that different domains were required. It is a dated addendum, not the page used for the earlier human judgment.
4. [Confirmed review receipt](runs/pacs-calibration-20261010-01/records/reviews/2026-10-11-revised-receipt.md) and [accepted-pair release](runs/pacs-calibration-20261010-01/exports/revised-20261011-v2/README.md).

GitHub displays HTML source; download the folder and open the HTML in a browser to see the contact sheets. No server or API credentials are needed for these saved pages. The full 9,991-image corpus is not duplicated here; the saved description packages, smoke fixture, and review pages contain their referenced image subset.

## Install and test the chat tools

Python 3.11+ is recommended. From the repository root:

```bash
python -m pip install -r chat_review/requirements.txt
python -B -m unittest discover -s chat_review/tests -v
python -B tools/validate_public_snapshot.py
```

Tests use the committed manifest and synthetic image fixtures; they do not require the full PACS download or a model API. The public-snapshot validator additionally checks the actual saved review chain, frozen input hashes, original image assets, and exported tables.

## Data and reproducibility

PACS has four domains and seven classes. The local split is stratified by class/domain with seed `20260623`: **80% training, 10% validation, 10% test**. The real calibration uses source-domain training images only, with the entire sketch domain held out. The original downloaded Hub revision is unknown; exact local image hashes and frozen membership are retained instead of claiming a verified upstream revision.

The run seed reproduces sampling and audit selection, not stochastic model output. Saved descriptions and explanations preserve the observed outputs. Exact runtime model revision, token use, and cost were unavailable. Metadata hiding for description agents was instruction-based, not OS-level isolation. Historical embedding provenance is incomplete; stored roles can be inspected, but exact recomputation needs those original feature files.

The strict GRIT subset requires individually inspected, accepted pairs. The broad subset may also include explicitly scanned group members. Acceptance is distinct from group coverage and from controlled-study eligibility. Calibration records do not increment adaptive-condition counters. The prospective threshold remains five completed initial group reviews and at least twenty individually audited pairs per adaptive condition.

## Earlier CAPTCHA app and supporting tools

- `web/`: React/Vite Play, Review, and PACS Analyzer interfaces.
- `pipeline/`: PACS preparation, seeded splits, feature/probe utilities, and game-to-Parquet export.
- `server/`: optional FastAPI multi-annotator review server; local server data is excluded.
- `vlm_eval/`: earlier model-based simulation and data compatibility tools.

To obtain images for new runs or the web app:

```bash
python -m pip install -r chat_review/requirements.txt
python pipeline/build_real_manifest.py
cd web
npm ci
npm run dev
```

The builder downloads PACS and **replaces** `web/public/manifest.json` with metadata-only records. Preserve the committed manifest if comparing against its frozen hash; it contains historical model scores. Image IDs depend on upstream ordering, so a new download is not automatically an exact reconstruction of the historical corpus. Verify image hashes before replaying scientific exports. New run directories and exports must have new names; do not overwrite frozen runs.

The old app's collection archives and full dataset remain in the [earlier repository](https://github.com/DevLee2025/InvariantPairsCAPTCHAApp/tree/6c84b1f). This snapshot does not copy its commit history, bulky exports, or automatic website deployment workflow.
