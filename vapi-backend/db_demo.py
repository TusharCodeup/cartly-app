# Cartly Database Utility & Query Tester
from __future__ import annotations
from sqlalchemy import text
from database import engine, init_db

def run_sql(query: str):
    """Run a raw SQL query on Cartly's shopping database.

    Example:
        rows = run_sql("SELECT * FROM shopping_items")
        print(rows)
    """
    init_db()
    with engine.begin() as conn:
        result = conn.execute(text(query))
        return result.fetchall() if result.returns_rows else result.rowcount

if __name__ == "__main__":
    print("--- Cartly Shopping List DB Status ---")
    rows = run_sql("SELECT id, category, name, quantity, unit, max_price, checked, canceled FROM shopping_items WHERE canceled = 0")
    if not rows:
        print("No active items in shopping list database.")
    else:
        for r in rows:
            print(f"[{r[0]}] {r[1]} -> {r[2]} (qty: {r[3]} {r[4] or ''}) | maxPrice: ${r[5] or 'N/A'}")