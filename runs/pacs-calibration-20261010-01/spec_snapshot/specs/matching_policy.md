# Matching policy v1

## Candidate construction

Pair proposals use only images allowed by the run's proposal split. The first pilot uses `train`. For a held-out-domain fold, every image from the target domain is excluded from proposal, description, retrieval, grouping, and adaptive-feedback packages even when its manifest split is `train`.

The metadata-hidden condition receives opaque image aliases and pixels only. The metadata-visible condition may receive frozen manifest class and domain fields. Image descriptions are image-only in both conditions; metadata is introduced only to the visible matcher and summarizer. Labels must not be copied into fields presented as visual observations.

## Matching sequence

1. Describe each image independently using `image_description.schema.json`.
2. Retrieve candidates using frozen visual embeddings and structured-description similarity. In metadata-visible conditions, class and domain may restrict retrieval.
3. Enforce visible class, exact or compatible target count, and coarse activity/pose/state agreement.
4. Rank eligible candidates by meaningful difference on the initial spurious axes and by contribution to collection coverage.
5. Reopen both original images and perform a joint pixel check.
6. Select one candidate or abstain. Record rejected candidates and reasons when they reached the joint check.

Semantic validity is lexicographically prior to spurious difference. Scores are diagnostic fields, not human validation.

## Reuse and redundancy

Every proposal records both image IDs, retrieval rank, similarity signals, repeated-image counts, and near-duplicate diagnostics. The first pilot reports image reuse rather than imposing an untested universal cap. A run may set a cap in its frozen configuration; the default is no image more than five accepted proposals within one condition.

## Adaptive condition

The adaptive prompt may update only after a condition has at least five completed initial group reviews and at least 20 individually audited pairs. Updates append a versioned feedback-memory block. Earlier prompts, proposals, and reviews remain unchanged. Fixed conditions never receive human feedback.
