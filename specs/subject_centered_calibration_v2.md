# Subject-centered calibration and count-policy comparison

Version: draft 2, 2026-10-11. The human approved comparing both count rules. The detailed codebook and challenge-bank design below are prospective; no new image group or human labels have been generated under them yet.

## Operational rule

Use the same semantic core for both arms: class, coarse state/activity, and recorded relevant interactions, with fine structural differences coded as concerns unless explicitly adopted as mandatory. Each field has a value, visible evidence, and an observability flag. For a required field, a contradiction fails and insufficient evidence yields `unsure`. Depiction differences cannot compensate for either. This separates an operational lab definition from the unprovable general claim that two images have exactly the same meaning.

| Observation | Operational treatment |
| --- | --- |
| A guitar rotated 45 degrees | Depiction variation if state and construction remain verifiable |
| Sitting versus running animal | State mismatch, not image rotation |
| Flowers behind an otherwise displayed guitar | Record background variation; do not infer playing |
| Drawn music notes with a guitar | Record contextual suggestion separately from depicted activity |
| Person holding/playing a guitar | Record a subject-object interaction; inspect before assigning held/played state |
| Unseen pick guard due to crop or stylization | Unknown presence, not absent; retain uncertainty |
| Clearly incompatible cutaways or f holes | Record specific structural concern and human judgment; no silent hard-rule adoption |
| Color, pattern, proportions | Separate depiction attributes; proportions alone do not relabel an instrument |

Describe each image independently before pairing. Record every visible target instance, a primary-subject candidate (if unique), evidence for that choice, state and interactions, structural observations, incidental extras, and uncertainty. Do not choose a different primary subject after seeing a convenient partner. A central/larger object is evidence of prominence, not an automatic rule; interacting or coequal subjects may make single-subject interpretation inappropriate.

## Compare on identical pairs

- **Exact count:** equal total visible target-class count; unknown count does not pass. Shared core checks still apply.
- **Primary subject:** each image has an unambiguous independently selected primary subject; compare its core attributes. Extra subjects can be incidental only when they do not change its state or relevant relationships. Record extras and the justification. Ambiguous primary status yields `unsure`.
- Both arms use the same images, remaining rubric, structural-concern status, and nuisance axes. Do not compare the old coarse exact-count rubric against a simultaneously expanded fine-structure primary-subject rubric and attribute all differences to count.
- Ask for both initial judgments before revealing rationale or domain-selection policy. Counterbalance which count rule is listed first using a stored seed. Store order, both responses, reason codes, and times. Same-reviewer judgments are paired observations, not independent samples.
- Preserve initial and revised judgments separately for each policy. A downstream export must explicitly choose a policy; never overwrite the other policy's label or silently combine their accepted sets.

Suggested first challenge bank: 20 pairs in two groups of 10, covering equal-count controls, incidental extras with a clear primary subject, coequal/ambiguous multiple subjects, and context/visibility stress cases. Target at least three classes and all three available source-domain pair types where suitable images exist. Record shortfalls rather than manufacturing good matches. Include plausible failures and uncertainties; this tests the rubric rather than maximizing acceptance.

Continue train-only selection with sketch held out. With three source domains there are 3 unordered domain pairs x 7 classes = 21 eligible types, not all 42 PACS types. Do not expand into held-out data to satisfy a coverage target. Image reuse, sampling seed, candidate pool, rule version and selection process are saved before review. This is feedback-exposed calibration, outside controlled fixed/adaptive comparisons and their counters.

## Delayed selection disclosure

Every new group records `domain_selection.policy`: `cross_domain_required`, `unconstrained`, `same_domain_required`, or legacy `unknown`. Pair-level overrides are explicit. `unconstrained` means the domain-equality restriction is absent; it does not mean uniform sampling or absence of other restrictions. Report the actual candidate domains and any quotas/retrieval restrictions separately in the revealed evidence.

The **initial** page omits the rule, its evidence, construction rationale, and proposer confidence from the HTML source. Existing metadata-visible conditions can still show each image's factual class/domain; they do not announce how selection was constrained. A reviewer may infer a pattern from the images, so this is delayed disclosure, not a claim of perfect blinding. Metadata-hidden conditions retain hidden per-image labels.

The **revised** page discloses the rule and, separately, whether each pair actually crosses dataset domains. Never infer the imposed rule just from observed pairs or appearance. Missing historical evidence is `unknown`, not `unconstrained`. The original guitar calibration did enforce different domains, specifically photo and cartoon, in its prompt and publication guard. An explicitly dated addendum can state that fact without rewriting its frozen group or original reveal.

## Definition history and rule reliability

Use [model_working_definition.md](model_working_definition.md) as the evolving calibration notebook. Before a future group, freeze the actual governing definition/prompt version and hash. Record the source review events used by an update. A future adaptive condition gets its own version; a global notebook edit cannot mutate a fixed condition.

Count acceptance/rejection/uncertainty under both policies, reasons for disagreements, per-field agreement, time, and coverage/redundancy. Check repeatability on a small concealed repeat subset if practical. A second lab reviewer can later measure inter-reviewer agreement; a single reviewer's approval is still sufficient under the current acceptance protocol. Do not invent reliability statistics from one pass by one reviewer.

Downstream GRIT comparisons should use matched pair budgets, recorded subset policy, training-only selection, and untouched held-out evaluation. Human agreement tests the chosen annotation convention; robustness requires an actual model experiment. This plan does not establish either outcome in advance.
