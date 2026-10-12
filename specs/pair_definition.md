# Invariant pair definition v1

Status: frozen baseline for the first PACS grouped-review pilot.

## Required semantic agreement

A proposed PACS invariant pair is eligible only when both images visibly preserve all three fields:

1. **Object class**: dog, elephant, giraffe, guitar, horse, house, or person.
2. **Target-subject count**: the number of visible instances of the target class agrees. Use a bounded or unknown count when cropping, overlap, or occlusion prevents a reliable exact count; unknown counts do not pass automatically.
3. **Coarse activity, pose, or state**: the task-relevant visible state agrees under the vocabularies below.

The proposer must inspect the original pixels together before accepting a pair. Matching descriptions, labels, embeddings, or domains are retrieval evidence and never replace this visual check.

## Coarse state vocabularies

For dog, elephant, giraffe, horse, and person:

- standing or stationary;
- walking;
- running;
- sitting;
- lying;
- jumping;
- riding or being ridden, when applicable;
- head or portrait only;
- unclear.

Exact limb angles, left-versus-right orientation, and modest viewpoint changes need not match when the coarse state remains clear. A state change, uncertain subject count, or whole-subject versus head-only mismatch is semantic.

For guitar:

- isolated or displayed;
- held;
- actively played;
- whole object;
- detail only;
- unclear.

For house:

- whole exterior;
- partial exterior or architectural detail;
- interior;
- unclear.

Class-specific vocabularies may be revised only in a new versioned spec. A revision never changes the interpretation of an earlier run.

## Initial spurious axes

After semantic validity passes, prefer pairs with clear differences along one or more of:

- background;
- palette;
- lighting;
- texture;
- viewpoint;
- crop;
- composition.

Rendering medium or visual style may be described as evidence for texture, palette, and composition differences. Context must be recorded separately because it can overlap with semantic activity. It is not an initial target spurious axis.

More difference is useful only after semantic agreement. A large stylistic or contextual difference never compensates for a mismatch in class, count, or activity/pose/state.

## Abstention and uncertainty

Abstain when any required semantic field is materially uncertain, including severe crop, occlusion, abstraction, unreadable scale, or disagreement between the description and the visible pixels. Store the uncertainty and evidence rather than forcing a pair.

## Human acceptance

One lab reviewer is sufficient for the first pilot. Pair validity and group coverage are separate judgments. The strict GRIT subset contains accepted pairs with `validation_scope=individual`. The broad experimental subset additionally permits accepted `group_scan` pairs. `sample_inference`, rejected, unsure, and unreviewed pairs are excluded.
