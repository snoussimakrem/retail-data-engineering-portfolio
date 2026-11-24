"""Cold-process benchmark. Peak RSS includes child processes sampled by psutil."""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import psutil
from generate_data import generate

def measured_run(engine, source, target):
    start = time.perf_counter()
    process = subprocess.Popen([sys.executable, '-m', 'migration.run', '--engine', engine,
        '--input', str(source), '--output', str(target)], stdout=subprocess.DEVNULL)
    peak = 0
    while process.poll() is None:
        try:
            parent = psutil.Process(process.pid)
            family = [parent] + parent.children(recursive=True)
            total = 0
            for p in family:
                try: total += p.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied): pass
            peak = max(peak, total)
        except psutil.NoSuchProcess: pass
        time.sleep(.05)
    seconds = time.perf_counter() - start
    if process.returncode:
        raise RuntimeError(f'{engine} failed with exit code {process.returncode}')
    return round(seconds, 4), peak

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sizes', type=int, nargs='+', default=[1000, 10000, 100000])
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--output', default='output/benchmark')
    a = p.parse_args()
    if a.repeats < 1 or any(n < 1 for n in a.sizes): p.error('sizes and repeats must be positive')
    out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
    records = []
    for size in a.sizes:
        source = out / f'sales-{size}.csv'
        generate(source, size)
        for run in range(1, a.repeats + 1):
            outputs = {}
            # Alternate execution order to reduce systematic order bias.
            engines = ['duckdb', 'spark'] if run % 2 else ['spark', 'duckdb']
            for engine in engines:
                target = out / f'{size}-{run}-{engine}.csv'
                elapsed, peak = measured_run(engine, source, target)
                outputs[engine] = target.read_bytes()
                records.append({'rows': size, 'run': run, 'engine': engine, 'seconds': elapsed, 'peak_rss_bytes': peak})
                print(size, run, engine, elapsed, 'seconds', flush=True)
            if outputs['duckdb'] != outputs['spark']:
                raise RuntimeError(f'Output mismatch for {size} rows, run {run}; benchmark invalid')
    with (out / 'results.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['rows','run','engine','seconds','peak_rss_bytes']); w.writeheader(); w.writerows(records)
    (out / 'metadata.json').write_text(json.dumps({'python': sys.version, 'cpu_count': os.cpu_count(),
        'method': 'cold subprocess; 50ms process-tree RSS samples; alternating engine order; includes startup and CSV output'}, indent=2))
    print('Results saved to', out)

if __name__ == '__main__': main()
