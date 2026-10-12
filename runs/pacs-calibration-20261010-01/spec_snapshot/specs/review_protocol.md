# Lab chat review protocol v1

Status: draft for the first chat-only grouped-review pilot.

## Principle

The reviewer does **not** manually assign `individual`, `group_scan`, `sample_inference`, or `unreviewed` to every pair. The reviewer states what they inspected and gives a judgment in ordinary language or the compact template below. Codex derives validation scope using fixed rules, appends the raw response and parsed record, and shows a receipt for confirmation or correction.

Codex can know which images it presented, but it cannot know where the reviewer looked. Presentation alone never establishes review scope. The reviewer must explicitly say whether they inspected only named/highlighted pairs or scanned the complete contact sheet.

## Recommended response format

```text
GROUP: <group id>
STAGE: initial | revised
INSPECTED: highlighted only | highlighted + full contact sheet | full contact sheet (no focused inspection) | <pair ids>
PAIR VALIDITY: accept | reject | unsure | accept with exclusions
COVERAGE: adequate | redundant | incomplete | unsure
EXCEPTIONS: <pair ids or none>
MISSING COVERAGE: <plain English or none>
COMMENT: <plain English>
```

Natural-language replies are allowed. For example:

> I scanned the full contact sheet. The group is mostly valid, but exclude P-014-07 because the dog is running and P-014-12 because I cannot verify the count. Coverage is incomplete because there are no indoor backgrounds.

Codex parses this as `accept with exclusions`, marks named/explicitly discussed pairs as individually reviewed, applies `group_scan` to the remaining scanned members, records the coverage gap, and returns a receipt. The reviewer can reply `confirm`, `next`, or provide a correction. `next` confirms the displayed receipt before moving on.

## Scope derivation

- **`individual`**: the reviewer says they inspected the highlighted audit set, explicitly lists the pair as inspected, opens it for focused inspection and confirms doing so, or makes a pair-specific visual judgment. A pair-specific comment may trigger this proposed label, but Codex must show it in the receipt before finalization.
- **`group_scan`**: the reviewer explicitly states that they scanned the complete contact sheet. Non-excepted group members not marked `individual` receive this scope. Merely being present in HTML is insufficient.
- **`unreviewed`**: the pair was neither individually inspected nor covered by an explicit full-contact-sheet scan.
- **`sample_inference`**: assigned by the pipeline, never manually by the reviewer, when an unreviewed pair belongs to a group that passes a prespecified probability-sampling rule. This scope is disabled for the first pilot's GRIT exports.

Pair-specific overrides always supersede the group verdict. `reject` and `unsure` never enter either GRIT subset.

## GRIT subsets

- **Strict:** accepted pairs with `validation_scope=individual`.
- **Broad experimental:** accepted pairs with `validation_scope in {individual, group_scan}`, excluding pair-specific rejections/unsure decisions.
- **Inferred research-only:** `sample_inference` pairs, if that mechanism is enabled in a later run. It is never merged silently into strict or broad.

One lab reviewer approval is sufficient for acceptance in the first pilot. Reviewer ID, initial and revised verdicts, exact response, parsed fields, timestamp, group/spec/model versions, and any correction events are retained.

## What `sample_inference` would mean

Example for a later experiment: a group contains 40 pairs. Before review, the run seed selects 20 uniformly at random without replacement for individual audit. The acceptance rule is frozen as:

- zero critical semantic failures among the 20 audited pairs; and
- the exact one-sided 95% hypergeometric upper bound on the whole-group defect rate is at most 10%.

With zero failures in 20 of 40, the largest whole-group defect count not rejected at the 5% level is 4, an upper defect-rate bound of 10%. The 20 audited pairs are `individual`; the other 20 may be labeled `sample_inference`. This does **not** mean a human saw them, and they remain outside the first pilot's strict and broad exports.

If the group size, sample size, random-selection rule, failure definition, confidence level, or threshold was not fixed before viewing outcomes, no `sample_inference` label may be assigned.

## Initial and revised stages

The metadata condition (`hidden` or `visible`) is independent of the judgment stage. The recommended first experiment retains both metadata conditions and also keeps the earlier two-stage judgment:

1. Initial HTML: contact sheet, condition-appropriate factual fields, and deterministic highlighted members; no proposer confidence or persuasive group rationale.
2. Revised HTML: reveal the model's explanation, uncertainty, coverage claim, and construction rationale.

Record both responses separately. A run selects which stage controls GRIT inclusion.

## First-pilot locked choices

- Variable group-size pilot: 10, 20, and 40 pairs, assigned and recorded by run seed.
- One lab reviewer approval required.
- `group_scan` qualifies only for the broad experimental subset.
- `sample_inference` is recorded in the schema but disabled for strict and broad export.
- Initial spurious-coverage axes: background, palette, lighting, texture, viewpoint, crop, and composition.
- Context is stored descriptively and flagged as a possible semantic factor; it is not initially counted as a targeted spurious axis.
- Adaptive update occurs after at least five completed initial group reviews **and** at least 20 individually audited pairs in that condition.
