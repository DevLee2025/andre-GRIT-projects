# Chat-only grouped invariant-pair review plan

Status: design draft, 2026-09-30. This document supersedes the custom participant-app and database portions of `PROPOSER_STUDY_PLAN.md`. Its pair rubric, run configuration, PACS split safeguards, provenance requirements, downstream evaluation, and Parquet compatibility requirements still apply.

## Decision summary

Humans interact only through a Codex Work conversation. Agents read and edit versioned specification and data files, generate a static HTML review artifact, present it to the human, and convert the human's chat response into append-only structured review records. There is no participant web application, live server, or database in the first lab pilot.

The review unit is a **group of related pairs**, because pair validity and collection coverage are different properties. A group review records both:

1. **Pair validity:** whether the constituent pairs preserve visible class, target-subject count, and coarse activity/pose/state.
2. **Group coverage:** whether the group contains useful, nonredundant variation in the intended spurious attributes.

A group can contain individually valid but redundant pairs, or diverse pairs contaminated by semantic mismatches. The two judgments must never be collapsed into one score.

## Files and reproducibility

Editable specifications live under `specs/`:

- `pair_definition.md`: invariant-pair rubric and class-specific edge cases.
- `image_description.schema.json`: structured visual description contract.
- `matching_policy.md`: hard constraints, ranking, abstention, and final pixel recheck.
- `grouping_policy.md`: group keys, size limits, representative selection, and coverage axes.
- `review_protocol.md`: blind/revealed stages and accepted chat-response format.
- `export_schema.json`: proposal, review, Hugging Face, and GRIT columns.

Each run copies those files into an immutable `runs/<run_id>/spec_snapshot/` and records their SHA-256 hashes. Human feedback may change future runs: after a run, an agent proposes a readable spec diff, the human accepts or revises it in chat, and the approved revision receives a new version. It never retroactively changes the meaning of pairs generated under an earlier version.

Each run stores the model/reasoning setting, prompts, condition, PACS manifest and image hashes, 80/10/10 split map, any held-out target domain, seeds, candidate pools, image descriptions, pair proposals, grouping assignments, complete model outputs, generated HTML, exact human responses, parsed decisions, timestamps, costs, and final exports. The raw chat response is retained alongside the structured interpretation so another researcher can audit the conversion.

## Pipeline

1. **Freeze the run.** Select one proposer model for all conditions in a controlled run, the initial/revised export rule, adaptive cadence, proposal split, optional target domain, budgets, and spec versions.
2. **Build a condition-safe image package.** Pair collection uses the existing `train` split. In a held-out-domain fold, exclude the complete target domain. Metadata-hidden proposer tasks receive opaque filenames and no mapping, labels, domains, paths, or scores. Because a single Codex task can read its workspace, meaningful technical blinding requires a separate task/directory containing only the opaque package; an instruction not to open the mapping is weaker evidence.
3. **Describe images independently.** Process images in bounded batches and store structured, visible observations plus a concise free-text description. Do not show prospective matches while producing descriptions, which reduces pressure to make two descriptions agree.
4. **Retrieve possible matches.** Use hard metadata eligibility on the research side when the condition permits it, then compare structured descriptions and frozen visual embeddings. Description similarity is a retrieval signal, not proof of invariance.
5. **Reopen both original images.** Before proposing a pair, the model must inspect the pixels together and reconfirm category, target count, activity/pose/state, crop, and uncertainty. It may abstain. This prevents an omitted or hallucinated description field from silently deciding the match.
6. **Group proposed pairs.** Group narrowly by visible semantic configuration and intended spurious-change signature, then compute coverage and redundancy diagnostics.
7. **Generate static HTML.** Build a self-contained or relative-asset report with a coverage table, deterministic highlighted examples, and a compact contact sheet of every pair in the group. No network server is required.
8. **Review through chat.** The human opens the HTML, replies in the task, and the agent appends the exact response and parsed labels to the run. The agent regenerates HTML when the human requests a split, exception, or closer view.
9. **Export.** Apply the run's frozen judgment and validation-basis policy, then generate versioned Hugging Face/GRIT Parquet files and run the compatibility gate from `PROPOSER_STUDY_PLAN.md`.

## Structured image descriptions

“Maximum detail” should mean **broad structured coverage**, not unlimited prose. Unlimited descriptions cost more, are hard to compare, and can still omit the decisive feature. Store these fields:

- visible object category and alternatives;
- target-subject count, including lower/upper bounds when occluded;
- activity/pose/state using the versioned class-specific vocabulary;
- body/object configuration, salient shape/anatomy, and orientation;
- viewpoint, scale, crop, and occlusion;
- interactions among target subjects and with other objects;
- background/scene and spatial context;
- apparent rendering medium, texture, palette, lighting, and line/shading style;
- readable text or symbols;
- ambiguity flags, confidence per critical field, and evidence visible in the image;
- a concise free-text description that does not replace the fields above.

The description schema needs explicit `unknown` and `not_applicable` values. A model must not fill missing visual evidence from PACS labels. Keep the raw model output even when schema repair is needed.

## Matching and grouping

Matching is hierarchical:

1. Enforce same visible category, target count, and activity/pose/state.
2. Reject material uncertainty or crop/state mismatches under the current rubric.
3. Rank the remaining candidates for meaningful spurious change and low redundancy.
4. Confirm the selected pair from pixels, not descriptions alone.

Group keys should include class, target count, coarse activity/pose/state, domain-pair direction when that metadata condition permits it, and one or more spurious-change tags. A useful group might be “one sitting dog; photograph-like to line drawing; background and texture changed.” A broad “dog pairs” group is too heterogeneous to summarize honestly.

For the lab pilot, randomize among **10-, 20-, and 40-pair groups** under a recorded seed. Every pair appears in the contact sheet. Highlight at least:

- the embedding medoid or most typical pair;
- one seeded-random pair;
- the lowest-confidence valid proposal;
- the farthest/boundary pair;
- the strongest apparent outlier or most novel spurious change.

These selections are deterministic from stored scores/seeds. The summarizer may explain why they were selected but cannot replace them with more persuasive examples. The group summary reports counts, coverage axes, repeated images, near duplicates, uncertainty, known exceptions, and missing variation. It must include a “reasons this group may fail” section.

## Human review protocol

Use two stages when measuring explanation effects:

1. **Blind group review:** show the contact sheet and objective counts without the model's persuasive summary or confidence. Record pair-validity concerns, exceptions, and coverage judgment.
2. **Revealed review:** show the model's group explanation, highlighted examples, uncertainty, and claimed gaps. Record any revised judgment separately.

The human may answer naturally, but the agent maps the response into this explicit structure and shows the parsed result in chat:

```text
GROUP <id>
pair validity: accept | reject | unsure
coverage: adequate | redundant | incomplete | unsure
exceptions: <pair ids or none>
missing coverage: <free text>
comment: <free text>
```

Group labels and pair labels remain separate. Each pair stores a `validation_basis`:

- `individual`: explicitly inspected and decided;
- `group_scan`: included in a group the human says they scanned, subject to listed exceptions;
- `sample_inference`: uninspected member covered only by a prespecified random-audit rule;
- `unreviewed`: no human validity claim.

The GRIT exporter filters by the run's chosen validation basis. A summary plus one or two representative pairs alone yields a group-level coverage opinion, not pair-level validation for every member. If the study wants to infer validity from a random sample, it must prespecify sample size, failure threshold, and confidence interval; otherwise only individually reviewed or explicitly group-scanned pairs qualify.

The operational format and derivation rules are frozen in [`specs/review_protocol.md`](specs/review_protocol.md). For the first pilot, strict GRIT uses accepted `individual` pairs; broad experimental GRIT adds accepted `group_scan` pairs; `sample_inference` is excluded from both. One lab reviewer approval is sufficient. The initial spurious axes are background, palette, lighting, texture, viewpoint, crop, and composition; context is recorded as a possible semantic factor rather than targeted as spurious.

## Experimental comparisons

The first study should compare the grouped workflow with the previous one-pair-at-a-time protocol using the **same frozen proposal pool** and a matched human-time or pair-view budget. Measure:

- valid-pair precision from an independent detailed audit;
- class/domain and within-class semantic-state coverage;
- spurious-change coverage and difference-vector diversity;
- redundancy, repeated-image use, and near-duplicate rate;
- accepted usable pairs and new coverage cells per human minute;
- initial-to-revised judgment changes;
- review fatigue and missed invalid-pair rate by group position/size;
- model calls, image tokens, latency, and cost;
- downstream GRIT robustness at matched pair count and coverage.

Run a calibration across the three group sizes before choosing a later default. The HTML viewer should record no behavioral telemetry in the lab pilot; the human reports completion in chat and the agent timestamps the exchange. External-participant measurement and consent belong to a later deployment protocol.

## First model recommendation

Use **GPT-6 Astra** for the first small proposer/grouping calibration because this phase emphasizes difficult visual judgment, sustained reasoning, artifact creation, and careful handling of uncertainty. Keep one exact model/reasoning setting across all experimental conditions. For scale, benchmark GPT-6.1 Sol on the same frozen calibration set; it may offer a better cost/quality tradeoff for repeated runs. Claude Opus 5 and a current Gemini model are useful later comparison arms, not simultaneous substitutions inside the initial four-condition experiment.

Model choice remains an empirical question. Before scaling, run a blinded calibration set and measure semantic mismatch rate, count/pose errors, description fidelity, abstention, group-summary faithfulness, cost, and latency. Select on those prespecified metrics rather than general benchmark reputation.

## Questions to lock before the first controlled run

1. Which of the variable 10-, 20-, and 40-pair group sizes best balances throughput and missed errors after calibration?
2. Should a later experiment enable `sample_inference`, and if so, what confidence bound and maximum defect rate should govern it? It is disabled from first-pilot GRIT exports.
3. Is the image describer metadata-hidden in every condition, with only the matcher/summarizer receiving condition-specific metadata, or does metadata visibility apply to every model stage?
4. Feedback may update both future specification versions and, in adaptive conditions, the current run's versioned feedback memory. These are separate recorded mechanisms and never alter earlier proposals or judgments retroactively. The first pilot updates after five completed initial group reviews and at least 20 individually audited pairs in that condition; record both exposures.
5. The initial spurious axes are background, palette, lighting, texture, viewpoint, crop, and composition. Context is descriptive and potentially semantic rather than an initial target axis. What evidence would justify promoting a contextual field to a spurious axis later?
6. What limits apply to repeated images and near-duplicate pairs?
7. Who adjudicates rejected, unsure, or internally inconsistent groups?
8. One lab reviewer approval is sufficient in the first pilot. A later reliability study should decide how many duplicate reviews are needed to estimate inter-reviewer agreement.
