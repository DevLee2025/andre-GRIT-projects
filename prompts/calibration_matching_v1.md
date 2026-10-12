# Real-data calibration matching v1

This is a feedback-exposed, metadata-visible development calibration, not an observation in the controlled fixed/adaptive study. Use the current pair_definition.md rubric. Pending criteria are reviewer concerns, not new hard requirements.

Choose cross-domain training-image pairs with the same visible class, count, and coarse activity/pose/state. For a coherent guitar group, require one whole isolated/displayed instrument per image. Semantic agreement is required before considering background, palette, lighting, texture, viewpoint, crop, or composition variation. Do not infer validity from domain/class labels or descriptions alone.

After independent image descriptions have been saved, inspect both originals together. Reject materially uncertain category, count, whole/detail extent, or use state. Save each final pair's concise semantic evidence, visible spurious differences, uncertainty, and uncalibrated confidence; preserve rejected candidates and why they were not used. No repeated image within the final group. Exact duplicate bytes are excluded; report near-duplicate risks.

Produce ten pairs only if ten survive the visual checks. Assign representative roles by a documented calculation or seeded draw; omit unimplemented roles. Conceal rationale, confidence, and evaluative role names during initial human review. Keep initial and revised image identities, order, and highlighted membership identical. Store explanations before human review. Do not auto-accept proposals or create human judgments.
