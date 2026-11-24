"""Generate deterministic, synthetic retail sales; monetary values are integer cents."""
import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

def generate(path, rows, seed=42, dirty=False):
    if rows < 1:
        raise ValueError('rows must be positive')
    rng = random.Random(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['sale_id', 'sale_date', 'store_id', 'product_id', 'quantity', 'unit_price_cents'])
        for i in range(rows):
            sale_id = i + 1
            sale_date = (date(2024, 1, 1) + timedelta(days=rng.randrange(365))).isoformat()
            product = rng.randrange(1, 101)
            quantity = rng.randrange(1, 11)
            price = rng.randrange(100, 10001)
            if dirty and i % 20 == 0:
                price = -price
            if dirty and i % 23 == 0:
                product = ''
            if dirty and i > 0 and i % 29 == 0:
                sale_id = i
            if dirty and i % 31 == 0:
                sale_date = 'invalid-date'
            writer.writerow([sale_id, sale_date, rng.randrange(1, 11), product, quantity, price])

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', default='output/sales.csv')
    p.add_argument('--rows', type=int, default=10000)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--dirty', action='store_true')
    a = p.parse_args()
    generate(a.output, a.rows, a.seed, a.dirty)
