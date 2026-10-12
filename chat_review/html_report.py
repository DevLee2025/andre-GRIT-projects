from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any

from chat_review.common import DOMAINS, ContractError, atomic_write_bytes, read_json, resolve_inside


SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
DOMAIN_SELECTION_LABELS = {
    "cross_domain_required": "Different domains required",
    "unconstrained": "Domain difference not required",
    "same_domain_required": "Same domain required",
    "unknown": "Domain-selection policy unknown",
}


def _domain_selection(record: dict[str, Any], location: str) -> dict[str, str]:
    # Absence is a legacy unknown, never evidence of a selection constraint.
    if "domain_selection" not in record:
        return {"policy": "unknown"}
    selection = record["domain_selection"]
    if not isinstance(selection, dict):
        raise ContractError(f"{location}.domain_selection must be an object")
    policy = selection.get("policy")
    if not isinstance(policy, str) or policy not in DOMAIN_SELECTION_LABELS:
        raise ContractError(f"{location}.domain_selection.policy is invalid: {policy!r}")
    if selection.keys() - {"policy", "evidence", "source"}:
        raise ContractError(f"{location}.domain_selection has unsupported fields")
    for field in ("evidence", "source"):
        if field in selection and not isinstance(selection[field], str):
            raise ContractError(f"{location}.domain_selection.{field} must be plain text")
    return selection


def _domain_relationship(pair: dict[str, Any]) -> str:
    domains = [(pair.get(role) or {}).get("domain") for role in ("anchor", "candidate")]
    if any(domain not in DOMAINS for domain in domains):
        return "unknown"
    return "same" if domains[0] == domains[1] else "different"


def validate_domain_selection(group: dict[str, Any]) -> None:
    """Validate effective policies against metadata before either stage is published."""
    selection = _domain_selection(group, "group")
    for index, pair in enumerate(group["pairs"], start=1):
        location = f"pair {pair.get('pair_id') or index}"
        effective = _domain_selection(pair, location) if "domain_selection" in pair else selection
        required = {"cross_domain_required": "different", "same_domain_required": "same"}.get(effective["policy"])
        if required is not None and _domain_relationship(pair) != required:
            raise ContractError(
                f"{location}: domain_selection policy {effective['policy']} requires {required} domains; "
                "image domain metadata is missing, invalid, or contradicts the policy"
            )


def _selection_evidence(selection: dict[str, str]) -> str:
    return "".join(
        f"<p><strong>Selection {field}:</strong> {html.escape(selection[field])}</p>"
        for field in ("evidence", "source") if selection.get(field)
    )


def _selection_explanation(selection: dict[str, str], *, missing: bool) -> str:
    if missing:
        return ("No domain-selection policy was recorded for this legacy group. "
                "Observed domain differences do not establish a selection requirement.")
    if selection["policy"] == "unknown":
        return "The selection requirement is unknown; it cannot be inferred from the observed domains."
    if selection["policy"] == "unconstrained":
        return "Either same-domain or different-domain pairs were permitted."
    return "This is a selection requirement, not evidence of semantic validity."


def _pair_domain_disclosure(pair: dict[str, Any], group_selection: dict[str, str]) -> str:
    override = "domain_selection" in pair
    selection = pair["domain_selection"] if override else group_selection
    scope = "pair override" if override else "inherited group policy"
    relationship = {
        "same": "Same domain",
        "different": "Different domains",
        "unknown": "Unknown; valid domain metadata is unavailable",
    }[_domain_relationship(pair)]
    # Actual label names remain governed by _metadata_line and the visibility condition.
    detail = (f"<p>{_selection_explanation(selection, missing=False)}</p>"
              + _selection_evidence(selection)) if override else ""
    return (
        f"<p><strong>Domain selection ({scope}):</strong> {DOMAIN_SELECTION_LABELS[selection['policy']]}</p>"
        f"{detail}<p><strong>Observed domain relationship (metadata):</strong> {relationship}</p>"
    )


def _safe_name(value: str) -> str:
    result = SAFE_ID.sub("_", value).strip("._")
    if not result:
        raise ContractError("pair or image alias cannot produce an empty asset name")
    return result[:120]


def _copy_asset(source: Path, assets_dir: Path, stem: str) -> str:
    if not source.is_file():
        raise FileNotFoundError(f"review image is missing: {source}")
    suffix = source.suffix.lower() or ".jpg"
    destination = assets_dir / f"{_safe_name(stem)}{suffix}"
    shutil.copyfile(source, destination)
    return f"{assets_dir.name}/{destination.name}"


def _metadata_line(image: dict[str, Any], visible: bool) -> str:
    if not visible:
        return ""
    fields = []
    for key in ("id", "class", "domain"):
        if image.get(key) is not None:
            fields.append(f"{html.escape(key)}: {html.escape(str(image[key]))}")
    return " · ".join(fields)


def build_report(
    *,
    group: dict[str, Any],
    output_path: Path,
    pacs_root: Path,
    stage: str,
) -> Path:
    if stage not in {"initial", "revised"}:
        raise ContractError("stage must be initial or revised")
    pairs = group.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ContractError("group.pairs must be a non-empty array")
    validate_domain_selection(group)
    group_selection = _domain_selection(group, "group")
    condition = str(group.get("condition", ""))
    metadata_visible = condition.endswith("_visible")
    assets_dir = output_path.parent / f"{output_path.stem}_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    cards: list[str] = []
    for index, pair in enumerate(pairs, start=1):
        pair_id = str(pair.get("pair_id") or f"pair-{index:03d}")
        anchor = pair.get("anchor") or {}
        candidate = pair.get("candidate") or {}
        anchor_source = resolve_inside(pacs_root, str(anchor.get("file", "")))
        candidate_source = resolve_inside(pacs_root, str(candidate.get("file", "")))
        anchor_url = _copy_asset(anchor_source, assets_dir, f"{pair_id}-anchor")
        candidate_url = _copy_asset(candidate_source, assets_dir, f"{pair_id}-candidate")
        roles = [str(value) for value in pair.get("highlighted_roles", [])]
        focused = bool(roles)
        # Keep audit membership visible without revealing selection reasons or their count.
        badge_labels = roles if stage == "revised" else (["Audit example"] if focused else [])
        badges = "".join(f'<span class="badge">{html.escape(label)}</span>' for label in badge_labels)
        explanation = ""
        if stage == "revised":
            explanation = f"""
              <div class="explanation">
                {_pair_domain_disclosure(pair, group_selection)}
                <p><strong>Semantic rationale:</strong> {html.escape(str(pair.get('semantic_rationale', 'Not supplied.')))}</p>
                <p><strong>Spurious difference:</strong> {html.escape(str(pair.get('spurious_rationale', 'Not supplied.')))}</p>
                <p><strong>Uncertainty:</strong> {html.escape(str(pair.get('uncertainty', 'None recorded.')))}</p>
                <p><strong>Proposer confidence:</strong> {html.escape(str(pair.get('confidence', 'Not supplied')))}</p>
              </div>
            """
        cards.append(
            f"""
            <article class="pair-card{' focused' if focused else ''}" id="{html.escape(pair_id)}">
              <header><span class="pair-position">{index}</span><code>{html.escape(pair_id)}</code><span class="badges">{badges}</span></header>
              <div class="images">
                <figure><img src="{html.escape(anchor_url)}" alt="Anchor image for {html.escape(pair_id)}"><figcaption>Anchor<br>{_metadata_line(anchor, metadata_visible)}<br><a href="{html.escape(anchor_url)}" target="_blank" rel="noopener noreferrer">Open original image</a></figcaption></figure>
                <figure><img src="{html.escape(candidate_url)}" alt="Paired image for {html.escape(pair_id)}"><figcaption>Candidate<br>{_metadata_line(candidate, metadata_visible)}<br><a href="{html.escape(candidate_url)}" target="_blank" rel="noopener noreferrer">Open original image</a></figcaption></figure>
              </div>
              {explanation}
            </article>
            """
        )

    calibration_notice = ""
    if group.get("calibration_notice"):
        calibration_notice = f'<p class="notice calibration-notice">{html.escape(str(group["calibration_notice"]))}</p>'

    summary = ""
    if stage == "revised":
        coverage = group.get("coverage_summary", {})
        coverage_rows = "".join(
            f"<li><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</li>"
            for key, value in sorted(coverage.items())
        ) or "<li>No coverage summary supplied.</li>"
        reasons = group.get("reasons_group_may_fail", [])
        reason_rows = "".join(f"<li>{html.escape(str(reason))}</li>" for reason in reasons) or "<li>None recorded.</li>"
        summary = f"""
        <section class="summary">
          <h2>Revealed model summary</h2>
          <h3>Group domain-selection policy</h3>
          <p><strong>{DOMAIN_SELECTION_LABELS[group_selection['policy']]}</strong></p>
          <p>Applies to all pairs except those with an explicit pair override below.</p>
          <p>{_selection_explanation(group_selection, missing='domain_selection' not in group)}</p>
          {_selection_evidence(group_selection)}
          <p class="role-legend">Highlighted roles indicate why a pair was selected for inspection, not whether it is valid.</p>
          <p><strong>Shared semantic claim:</strong> {html.escape(str(group.get('semantic_claim', 'Not supplied.')))}</p>
          <h3>Claimed coverage</h3><ul>{coverage_rows}</ul>
          <h3>Reasons this group may fail</h3><ul>{reason_rows}</ul>
        </section>
        """

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(str(group.get('group_id', 'Group review')))} · {stage}</title>
  <style>
    :root {{ color-scheme: light; --ink:#172033; --muted:#647087; --paper:#f6f7fa; --card:#fff; --focus:#8b1e3f; --line:#d9deea; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif; }}
    main {{ max-width:1440px; margin:auto; padding:28px; }}
    .top {{ display:flex; gap:18px; justify-content:space-between; align-items:flex-start; margin-bottom:22px; }}
    h1,h2,h3,p {{ margin-top:0; }}
    .stage {{ border:1px solid var(--line); border-radius:999px; background:#fff; padding:7px 12px; white-space:nowrap; }}
    .notice {{ background:#fff7df; border:1px solid #ead38c; border-radius:10px; padding:12px 14px; margin:0 0 20px; }}
    .summary {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; margin-bottom:20px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:16px; }}
    .pair-card {{ min-width:0; background:var(--card); border:2px solid transparent; border-radius:12px; box-shadow:0 2px 10px #18233a12; overflow:hidden; break-inside:avoid; }}
    .pair-card.focused {{ border-color:var(--focus); }}
    .pair-card header {{ min-height:46px; display:flex; align-items:center; gap:9px; padding:9px 12px; border-bottom:1px solid var(--line); }}
    .pair-position {{ display:grid; place-items:center; width:26px; height:26px; border-radius:50%; background:var(--ink); color:#fff; font-weight:700; }}
    .badges {{ margin-left:auto; display:flex; flex-wrap:wrap; gap:5px; justify-content:flex-end; }}
    .badge {{ color:var(--focus); background:#f8e8ee; border-radius:999px; padding:3px 7px; font-size:11px; }}
    .images {{ display:grid; grid-template-columns:1fr 1fr; gap:1px; background:var(--line); }}
    figure {{ min-width:0; margin:0; background:#fff; }}
    img {{ display:block; width:100%; aspect-ratio:1; object-fit:contain; background:#eef0f4; }}
    figcaption {{ min-height:43px; padding:7px 9px; color:var(--muted); font-size:12px; overflow-wrap:anywhere; }}
    .explanation {{ padding:12px; border-top:1px solid var(--line); }}
    .explanation p:last-child {{ margin-bottom:0; }}
    footer {{ margin-top:24px; color:var(--muted); }}
    @media (max-width:620px) {{ main {{ padding:14px; }} .grid {{ grid-template-columns:1fr; }} .top {{ display:block; }} .stage {{ display:inline-block; }} }}
    @media print {{ body {{ background:#fff; }} main {{ max-width:none; padding:0; }} .pair-card {{ box-shadow:none; }} }}
  </style>
</head>
<body>
<main>
  <div class="top"><div><h1>{html.escape(str(group.get('group_id', 'Unnamed group')))}</h1><p>{len(pairs)} pairs · condition {html.escape(condition or 'unspecified')}</p></div><span class="stage">{html.escape(stage.title())} review</span></div>
  <p class="notice">All pairs are shown below. Being present does not mean a pair was inspected. In chat, state whether you inspected highlighted pairs, the full contact sheet, or explicit pair IDs.</p>
  {calibration_notice}
  {summary}
  <section class="grid" aria-label="Complete pair contact sheet">{''.join(cards)}</section>
  <footer>Static artifact. It contains no form, network request, analytics, or automatic review claim.</footer>
</main>
</body>
</html>
"""
    atomic_write_bytes(output_path, document.encode("utf-8"))
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a static initial or revised group-review HTML artifact.")
    parser.add_argument("--group", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pacs-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("initial", "revised"), required=True)
    args = parser.parse_args()
    result = build_report(group=read_json(args.group), output_path=args.output, pacs_root=args.pacs_root, stage=args.stage)
    print(json.dumps({"html": str(result), "assets": str(result.parent / f'{result.stem}_assets')}, indent=2))


if __name__ == "__main__":
    main()
