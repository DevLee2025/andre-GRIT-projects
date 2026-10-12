# Independent visual description for calibration v1

Inspect each image independently. Do not propose pairs or compare images while describing them. Use the pixels, not filename, class label, domain label, or previous human feedback as visual evidence.

Write one JSONL record per image conforming to image_description.schema.json. Use its opaque alias. Record visible category, exact count or explicit uncertainty, activity/pose/state, orientation, viewpoint, scale, crop, occlusion, interactions, background, rendering, palette, lighting, texture, composition, text, and uncertainty. Unknown/not-applicable is preferable to invented detail. Confidence is uncalibrated.

For guitars, distinguish whole versus cropped/detail-only; isolated/displayed versus held/actively played. A second partly visible guitar still matters to count. Distinguish a separate object from a cast shadow or reflection and note ambiguity. Do not claim a stringed instrument is definitely a guitar if the pixels do not support that category.

Descriptions must be produced before any paired image is shown. Preserve each model-produced description unchanged; later corrections are separate records. Return concise observable evidence, not private reasoning.
