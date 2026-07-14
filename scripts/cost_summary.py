"""Extract cost figures from catalog.db for the proof writeup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "catalog.db"


def main() -> None:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    total = cur.execute(
        "SELECT COALESCE(SUM(cost), 0) FROM runs WHERE model NOT LIKE '%mock%'"
    ).fetchone()[0]
    n_runs = cur.execute(
        "SELECT COUNT(*) FROM runs WHERE model NOT LIKE '%mock%'"
    ).fetchone()[0]
    published = cur.execute(
        "SELECT COUNT(*) FROM products WHERE status = 'published'"
    ).fetchone()[0]
    with_pid = cur.execute(
        "SELECT COALESCE(SUM(cost), 0), COUNT(DISTINCT product_id) "
        "FROM runs WHERE model NOT LIKE '%mock%' AND product_id IS NOT NULL"
    ).fetchone()

    by_node = cur.execute(
        "SELECT node, model, COUNT(*), ROUND(SUM(cost), 6) "
        "FROM runs WHERE model = 'gpt-5.3-chat' GROUP BY node, model"
    ).fetchall()

    print(f"total_azure_cost_usd={total}")
    print(f"azure_run_rows={n_runs}")
    print(f"published_products={published}")
    print(f"cost_linked_to_products_usd={with_pid[0]}")
    print(f"distinct_products_with_cost={with_pid[1]}")
    if published and total:
        print(f"avg_cost_per_published_usd={float(total) / published:.6f}")
    if with_pid[1]:
        print(f"avg_cost_per_costed_product_usd={float(with_pid[0]) / with_pid[1]:.6f}")
    print("gpt53_by_node=")
    for row in by_node:
        print(f"  {row}")


if __name__ == "__main__":
    main()
