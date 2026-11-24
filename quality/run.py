"""Validate retail records, quarantine invalid rows, and record run history."""
import argparse
import csv
import json
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone, date
from pathlib import Path

FIELDS = ['sale_id', 'sale_date', 'store_id', 'product_id', 'quantity', 'unit_price_cents']

def check_row(row, seen):
    problems = []
    sale_id = row.get('sale_id', '')
    for name in ('sale_id', 'store_id', 'product_id', 'quantity', 'unit_price_cents'):
        try:
            value = int(row.get(name, ''))
            if value <= 0: problems.append(f'{name}_nonpositive')
        except (TypeError, ValueError):
            problems.append(f'{name}_invalid')
    try: date.fromisoformat(row.get('sale_date', ''))
    except (ValueError, TypeError): problems.append('sale_date_invalid')
    if sale_id and sale_id in seen: problems.append('sale_id_duplicate')
    if sale_id: seen.add(sale_id)
    return problems

def run(input_path, output_dir, db_path):
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    started = datetime.now(timezone.utc).isoformat()
    valid, rejected, counts, seen = [], [], Counter(), set()
    with open(input_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError(f'Expected exact CSV header: {FIELDS}')
        for row in reader:
            issues = check_row(row, seen)
            if issues:
                counts.update(issues)
                rejected.append({**row, 'errors': ';'.join(issues)})
            else: valid.append(row)
    for name, rows, fields in [('clean.csv', valid, FIELDS), ('quarantine.csv', rejected, FIELDS + ['errors'])]:
        with (output_dir / name).open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    summary = {'run_id': run_id, 'started_at_utc': started, 'input': str(input_path),
               'total': len(valid) + len(rejected), 'valid': len(valid), 'rejected': len(rejected), 'issues': dict(counts)}
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, started_at_utc TEXT, input_path TEXT, total INTEGER, valid INTEGER, rejected INTEGER, issues TEXT)')
        db.execute('INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)', (run_id, started, str(input_path), summary['total'], len(valid), len(rejected), json.dumps(dict(counts))))
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True); p.add_argument('--output', default='output/quality')
    p.add_argument('--db', default='output/quality/history.db')
    p.add_argument('--fail-on-rejected', action='store_true', help='Exit 2 if any rows are quarantined')
    a = p.parse_args(); result = run(a.input, a.output, a.db)
    print(json.dumps(result, indent=2))
    if a.fail_on_rejected and result['rejected']: raise SystemExit(2)

if __name__ == '__main__': main()
