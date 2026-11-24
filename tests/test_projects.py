import csv
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from generate_data import generate
from quality.run import run
from migration.pipeline import duckdb_aggregate, spark_aggregate

HAS_DUCKDB = importlib.util.find_spec('duckdb') is not None
HAS_SPARK = importlib.util.find_spec('pyspark') is not None

class RetailTests(unittest.TestCase):
    def test_generation_is_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/'a.csv', Path(d)/'b.csv'
            generate(a, 100); generate(b, 100)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_quality_quarantines_and_persists(self):
        with tempfile.TemporaryDirectory() as d:
            source, out, db = Path(d)/'sales.csv', Path(d)/'out', Path(d)/'history.db'
            generate(source, 100, dirty=True)
            result = run(source, out, db)
            self.assertEqual(result['total'], 100)
            self.assertGreater(result['rejected'], 0)
            self.assertIn('sale_date_invalid', result['issues'])
            with (out/'clean.csv').open() as f: self.assertEqual(len(list(csv.DictReader(f))), result['valid'])
            with (out/'quarantine.csv').open() as f: self.assertEqual(len(list(csv.DictReader(f))), result['rejected'])
            with sqlite3.connect(db) as con: self.assertEqual(con.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 1)

    @unittest.skipUnless(HAS_DUCKDB, 'duckdb not installed')
    def test_duckdb_known_result(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'sales.csv'
            p.write_text('sale_id,sale_date,store_id,product_id,quantity,unit_price_cents\n1,2024-01-01,1,2,3,100\n2,2024-01-01,1,3,1,250\n')
            self.assertEqual(duckdb_aggregate(p), [('2024-01-01', 1, 2, 4, 550)])

    @unittest.skipUnless(HAS_DUCKDB and HAS_SPARK, 'duckdb and pyspark are required')
    def test_spark_and_duckdb_equivalence(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'sales.csv'; generate(p, 200)
            self.assertEqual(duckdb_aggregate(p), spark_aggregate(p))

if __name__ == '__main__': unittest.main()
