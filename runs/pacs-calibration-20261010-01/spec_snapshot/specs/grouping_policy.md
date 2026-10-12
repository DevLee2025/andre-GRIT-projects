# Grouping policy v1

## Group keys

Group proposals narrowly enough that one coverage claim is meaningful. A group key includes:

- visible object class;
- target-subject count;
- coarse activity, pose, or state;
- metadata condition;
- domain-pair direction when available in that condition;
- one or more observed spurious-change axes.

Do not use a broad class-only group such as “dog pairs.” Split a group when its semantic state or intended variation cannot be summarized faithfully.

## Size assignment

The calibration sizes are 10, 20, and 40 pairs. The run seed determines size assignment and all seeded representative choices. Group size, seed, and assignment algorithm version are stored.

## Required members and diagnostics

Every pair appears in the contact sheet. Highlight deterministic roles when enough distinct pairs exist:

- embedding medoid or most typical pair;
- seeded-random pair;
- lowest-confidence proposal;
- farthest or boundary pair;
- strongest outlier or most novel spurious change.

One pair may fill multiple roles, and each role must be recorded. The group record also stores per-axis coverage, repeated images, near duplicates, confidence distribution, known uncertainties, and missing variation.

## Summary contract

The revealed summary separates:

1. the shared semantic claim;
2. observed variation on each spurious axis;
3. redundancy and coverage gaps;
4. representative and boundary examples;
5. known uncertainties;
6. reasons the group may fail.

The initial review artifact omits proposer confidence and persuasive rationale. The revised artifact reveals the stored summary without changing group membership.
