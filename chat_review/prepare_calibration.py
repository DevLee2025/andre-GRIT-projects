"""Prepare frozen source-only image packages for a real chat calibration."""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from chat_review.common import atomic_write_json, fingerprint, read_json, sha256_file, write_jsonl
from chat_review.create_run import create_run


def prepare(project: Path) -> Path:
    seed = 20261010
    run = create_run(
        project_root=project, output_root=project / "runs",
        manifest_path=project / "web/public/manifest.json",
        run_id="pacs-calibration-20261010-01", seed=seed,
        model="inherited Codex session; exact model revision not surfaced",
        reasoning_effort="inherited; exact setting not surfaced",
        proposal_split="train", target_domain="sketch", judgment_stage="revised",
        group_sizes=[10], conditions=["calibration_visible"],
        pacs_root=project / "web/public/pacs", hash_images=True,
    )
    extra_snapshots = []
    for source_name in ("prompts/calibration_description_v1.md", "prompts/calibration_matching_v1.md", "specs/potential_review_criteria.md"):
        dest = run / "calibration_spec_snapshot" / source_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / source_name, dest)
        extra_snapshots.append(fingerprint(dest, dest.relative_to(run).as_posix()))
    pool = [json.loads(line) for line in (run / "inputs/candidate_pool.jsonl").read_text().splitlines()]
    rng = random.Random(seed)
    selected = []
    for domain in ("photo", "cartoon"):
        available = sorted((r for r in pool if r['class'] == 'guitar' and r['domain'] == domain), key=lambda r:r['id'])
        selected.extend(rng.sample(available, 40))
    rng.shuffle(selected)
    mapping = []
    packages = run / "description_packages"
    for index, row in enumerate(selected):
        alias = f"I{index+1:03d}"
        batch = index // 20 + 1
        folder = packages / f"batch-{batch:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / "web/public/pacs" / row['file'], folder / f"{alias}.jpg")
        mapping.append({**row, "image_alias": alias, "batch": batch})
    write_jsonl(run / "inputs/description_mapping.jsonl", mapping)
    for batch in range(1,5):
        folder = packages / f"batch-{batch:02d}"
        rows = [r for r in mapping if r['batch'] == batch]
        # Overview retains original pixels at 227px without editing image content.
        sheet = Image.new('RGB', (4*247,5*260), 'white')
        draw = ImageDraw.Draw(sheet)
        for i,row in enumerate(rows):
            x,y = (i%4)*247,(i//4)*260
            with Image.open(folder / f"{row['image_alias']}.jpg") as im:
                sheet.paste(im.convert('RGB'), (x+10,y+22))
            draw.text((x+10,y+5),row['image_alias'],fill='black')
        sheet.save(folder / 'overview.png')
        shutil.copyfile(project / 'specs/image_description.schema.json', folder / 'description.schema.json')
        shutil.copyfile(project / 'prompts/calibration_description_v1.md', folder / 'INSTRUCTIONS.md')
    atomic_write_json(run / 'calibration.json', {
        'study_kind':'real_data_calibration', 'controlled_study_eligible':False,
        'feedback_exposed_coordinator':True, 'description_metadata_policy':'image-only by instruction; no OS-level isolation claimed',
        'proposal_metadata_policy':'visible', 'review_metadata_policy':'visible',
        'seed':seed, 'screened_class':'guitar', 'screened_domains':['photo','cartoon'],
        'sample_size_per_domain':40, 'target_group_size':10,
        'sampling_algorithm':'Python random.Random(seed); sample from sorted IDs by domain, then shuffle combined sample',
        'held_out_domain':'sketch', 'image_reuse_limit':1,
        'scientific_export_requires_human_review':True, 'counts_toward_adaptive_update':False,
        'extra_spec_snapshots':extra_snapshots,
        'description_mapping_sha256':sha256_file(run/'inputs/description_mapping.jsonl'),
        'api_tokens_and_cost':'not exposed by the chat/subagent tool; do not impute zero',
    })
    print(json.dumps({'run':str(run),'images':len(mapping),'eligible_train_images':len(pool)}))
    return run


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[1])
