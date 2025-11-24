#!/usr/bin/env python3
"""
Initialize Northwind Analytics synthetic database.

This script creates a SQLite database and populates it with synthetic
SaaS metrics data for the Northwind Analytics example.
"""

import sqlite3
import sys
from pathlib import Path


def init_database(db_path: str = "northwind_analytics.db") -> None:
    """Initialize database with schema and seed data.

    Args:
        db_path: Path to SQLite database file
    """
    db_file = Path(db_path)
    sql_dir = Path(__file__).parent

    # Create database connection
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    try:
        # Execute schema
        schema_file = sql_dir / "01_schema.sql"
        with open(schema_file) as f:
            cursor.executescript(f.read())

        # Load seed data
        seed_file = sql_dir / "02_seed_data.sql"
        with open(seed_file) as f:
            cursor.executescript(f.read())

        # Load revenue data
        revenue_file = sql_dir / "03_revenue_data.sql"
        with open(revenue_file) as f:
            cursor.executescript(f.read())

        # Commit changes
        conn.commit()

        # Verify data
        tables = [
            ("regions", "Regions"),
            ("customers", "Customers"),
            ("subscriptions", "Subscriptions"),
            ("revenue", "Revenue records"),
        ]

        for table, _label in tables:
            # Table names from trusted list, but use identifier for safety
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            cursor.fetchone()[0]

        # Show Q3 revenue summary
        cursor.execute("""
            SELECT
                r.region_name as region,
                SUM(CASE WHEN rev.year_month = '2024-07' THEN rev.mrr ELSE 0 END) as jul_mrr,
                SUM(CASE WHEN rev.year_month = '2024-08' THEN rev.mrr ELSE 0 END) as aug_mrr,
                SUM(CASE WHEN rev.year_month = '2024-09' THEN rev.mrr ELSE 0 END) as sep_mrr,
                SUM(CASE WHEN rev.year_month IN ('2024-07', '2024-08', '2024-09')
                    THEN rev.contraction_mrr ELSE 0 END) as total_contraction,
                SUM(CASE WHEN rev.year_month IN ('2024-07', '2024-08', '2024-09')
                    THEN rev.churned_mrr ELSE 0 END) as total_churn
            FROM revenue rev
            JOIN regions r ON rev.region_id = r.region_id
            WHERE rev.year_month IN ('2024-07', '2024-08', '2024-09')
            GROUP BY r.region_name
            ORDER BY r.region_name
        """)

        for row in cursor.fetchall():
            _region, _jul, _aug, _sep, _contraction, _churn = row

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    # Default to current directory, or accept path as argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else "northwind_analytics.db"
    init_database(db_path)
