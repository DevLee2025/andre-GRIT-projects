"""Validate published bytes and the included calibration evidence without network access."""
from __future__ import annotations

import io
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image
import pyarrow.parquet as pq

from chat_review.common import read_json, resolve_inside, sha256_bytes, sha256_file
from chat_review.export_hf import confirmed_reviews, read_jsonl, validate_hash_chain


def check(condition, message):
    if not condition:
        raise ValueError(message)


def check_fingerprint(base, record):
    path = resolve_inside(base, record['path'])
    check(sha256_file(path) == record['sha256'], f'Hash mismatch: {record["path"]}')


class Images(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.paths = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        if tag == 'img':
            self.paths.append(dict(attributes)['src'])


def main():
    publication = read_json(ROOT / 'PUBLICATION_MANIFEST.json')
    for record in publication['files']:
        check_fingerprint(ROOT, record)
    run = ROOT / 'runs/pacs-calibration-20261010-01'
    config = read_json(run / 'run.json')
    calibration = read_json(run / 'calibration.json')
    check_fingerprint(ROOT, config['manifest'])
    for record in config['spec_snapshot']:
        check_fingerprint(run / 'spec_snapshot', record)
    for record in calibration['extra_spec_snapshots']:
        check_fingerprint(run, record)
    frozen = read_json(run / 'records/descriptions_frozen.json')
    check_fingerprint(run, frozen['descriptions'])
    for record in frozen['sources']:
        check_fingerprint(run, record)
    pool = read_jsonl(run / 'inputs/candidate_pool.jsonl')
    check(sha256_file(run / config['candidate_pool']['index_file']) == config['candidate_pool']['sha256'], 'Candidate-pool hash')
    check(len(pool) == 4850 and all(i['split'] == 'train' and i['domain'] != 'sketch' for i in pool), 'Source-training eligibility')
    mapping_path = run / 'inputs/description_mapping.jsonl'
    check(sha256_file(mapping_path) == calibration['description_mapping_sha256'], 'Description mapping hash')
    mapping = read_jsonl(mapping_path)
    check(len(mapping) == 80, 'Description sample size')
    for image in mapping:
        path = run / f'description_packages/batch-{image["batch"]:02d}/{image["image_alias"]}.jpg'
        check(sha256_file(path) == image['sha256'], f'Description image hash: {image["image_alias"]}')
        with Image.open(path) as pixels:
            pixels.load()
    validation = read_json(run / 'records/proposal_validation.json')
    check_fingerprint(run, validation['group'])
    check_fingerprint(run, validation['initial_html'])
    for record in validation['review_assets']:
        check_fingerprint(run, record)
    group = read_json(run / validation['group']['path'])
    expected_images = [pair[role]['sha256'] for pair in group['pairs'] for role in ('anchor', 'candidate')]
    for page in (run / 'review/CAL-20261010-001').glob('*.html'):
        images = Images(page.read_text(encoding='utf-8')).paths
        check(len(images) == 20, f'Image count: {page.name}')
        check([sha256_file(resolve_inside(page.parent, p)) for p in images] == expected_images, f'Image identity/order: {page.name}')
    for ledger in [run / 'records/reviews.jsonl', ROOT / 'artifacts/chat-review-smoke/reviews/reviews.jsonl']:
        validate_hash_chain(read_jsonl(ledger))
    reviews = read_jsonl(run / 'records/reviews.jsonl')
    check(len(reviews) == 4, 'Review/confirmation event count')
    check(bool(confirmed_reviews(reviews, 'initial')) and bool(confirmed_reviews(reviews, 'revised')), 'Both stages confirmed')
    initial = next(r for r in reviews if r.get('stage') == 'initial')
    revised = next(r for r in reviews if r.get('stage') == 'revised')
    check(initial['derived_pair_receipt'] == revised['derived_pair_receipt'], 'Explicit unchanged decisions')
    check([r['pair_id'] for r in revised['derived_pair_receipt'] if r['verdict'] == 'accept'] == ['CAL-001-02'], 'Sole accepted pair')
    export = run / 'exports/revised-20261011-v2'
    report = read_json(export / 'validation_report.json')
    expected_counts = {'invariant_pairs': 1, 'grit_strict': 1, 'grit_broad': 1, 'groups': 1,
                       'group_members': 10, 'proposal_ledger': 10, 'judgments': 4, 'image_descriptions': 80}
    accepted = next(p for p in group['pairs'] if p['pair_id'] == 'CAL-001-02')
    for name, count in expected_counts.items():
        path = export / f'{name}.parquet'
        check(sha256_file(path) == report['files'][path.name]['sha256'], f'Export hash: {name}')
        table = pq.read_table(path)
        check(table.num_rows == count, f'Export rows: {name}')
        if name in {'invariant_pairs', 'grit_strict', 'grit_broad'}:
            row = table.to_pylist()[0]
            check(row['pair_id'] == 'CAL-001-02', f'Exported pair: {name}')
            check(not row['controlled_study_eligible'] and not row['counts_toward_adaptive_update'], 'Calibration eligibility')
            for field, role in [('anchor_image', 'anchor'), ('paired_image', 'candidate')]:
                data = row[field]['bytes']
                check(sha256_bytes(data) == accepted[role]['sha256'], f'Embedded image hash: {field}')
                with Image.open(io.BytesIO(data)) as image:
                    image.load()
    archive = read_json(ROOT / 'artifacts/definition-history/MWD-003.json')
    check_fingerprint(ROOT, archive['snapshot'])
    print(json.dumps({'status': 'passed', 'published_files': len(publication['files']),
                      'described_images': len(mapping), 'proposed_pairs': 10, 'accepted_pairs': 1,
                      'checks': ['publication_hashes', 'frozen_specs', 'train_only_pool', 'description_images',
                                 'review_ledgers', 'unchanged_judgments', 'HTML_image_identity_and_order',
                                 'Parquet_rows_hashes_and_image_decode', 'calibration_eligibility', 'definition_archive']}, indent=2))


if __name__ == '__main__':
    main()
