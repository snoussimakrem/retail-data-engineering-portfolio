import argparse
from migration.pipeline import duckdb_aggregate, spark_aggregate, write_results

def main():
    p = argparse.ArgumentParser(description='Run equivalent retail sales aggregations')
    p.add_argument('--input', required=True)
    p.add_argument('--output', default='output/aggregate.csv')
    p.add_argument('--engine', choices=['duckdb', 'spark', 'compare'], default='compare')
    a = p.parse_args()
    if a.engine == 'compare':
        duck = duckdb_aggregate(a.input)
        spark = spark_aggregate(a.input)
        if duck != spark:
            raise SystemExit('ERROR: engine results differ; no output written')
        rows = duck
        print(f'PASS: {len(rows)} aggregated rows match exactly')
    else:
        rows = (duckdb_aggregate if a.engine == 'duckdb' else spark_aggregate)(a.input)
    write_results(a.output, rows)
    print(f'Wrote {len(rows)} rows to {a.output}')

if __name__ == '__main__': main()
