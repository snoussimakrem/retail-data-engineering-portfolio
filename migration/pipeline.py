"""Equivalent daily store aggregation in DuckDB and Spark."""
from pathlib import Path
import csv

FIELDS = ['sale_date', 'store_id', 'order_count', 'units', 'revenue_cents']

def duckdb_aggregate(source):
    import duckdb
    con = duckdb.connect()
    try:
        # Input is trusted synthetic data with the documented schema.
        return con.execute('''SELECT sale_date::VARCHAR, store_id::BIGINT,
            count(*)::BIGINT, sum(quantity)::BIGINT,
            sum(quantity * unit_price_cents)::BIGINT
            FROM read_csv(?, header=true, columns={
                'sale_id':'BIGINT','sale_date':'VARCHAR','store_id':'BIGINT',
                'product_id':'BIGINT','quantity':'BIGINT','unit_price_cents':'BIGINT'})
            GROUP BY sale_date, store_id ORDER BY sale_date, store_id''', [str(source)]).fetchall()
    finally:
        con.close()

def spark_aggregate(source):
    from pyspark.sql import SparkSession, functions as F, types as T
    schema = T.StructType([T.StructField('sale_id', T.LongType()), T.StructField('sale_date', T.StringType()),
        T.StructField('store_id', T.LongType()), T.StructField('product_id', T.LongType()),
        T.StructField('quantity', T.LongType()), T.StructField('unit_price_cents', T.LongType())])
    spark = (SparkSession.builder.master('local[2]').appName('retail-migration')
             .config('spark.ui.enabled', 'false').config('spark.driver.host', '127.0.0.1')
             .config('spark.driver.bindAddress', '127.0.0.1').config('spark.sql.shuffle.partitions', '4').getOrCreate())
    try:
        data = spark.read.csv(str(Path(source).resolve()), header=True, schema=schema)
        result = (data.groupBy('sale_date', 'store_id').agg(F.count('*').alias('order_count'),
            F.sum('quantity').alias('units'), F.sum(F.col('quantity') * F.col('unit_price_cents')).alias('revenue_cents'))
            .orderBy('sale_date', 'store_id').collect())
        return [tuple(row) for row in result]
    finally:
        spark.stop()

def write_results(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)
