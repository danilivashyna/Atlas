#!/usr/bin/env python3
"""
Idempotent database migration runner.

Scans migrations/ directory, executes .sql files in alphabetical order.
Each migration is idempotent (IF NOT EXISTS patterns).

Usage:
  python scripts/db/migrate.py [--db /path/to/atlas.db]
"""

import os
import sqlite3
import sys
from pathlib import Path


def get_db_path():
    """Get database path from env or default."""
    return os.getenv("ATLAS_DB_PATH", "/tmp/atlas.db")


def migrate(db_path: str):
    """Run all migrations in migrations/ directory."""
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"

    if not migrations_dir.exists():
        print(f"Migrations directory not found: {migrations_dir}")
        return False

    # Get all .sql files sorted alphabetically
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found")
        return True

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for migration_file in migration_files:
            print(f"Running migration: {migration_file.name}")

            with open(migration_file, "r") as f:
                sql = f.read()

            # Execute migration (may contain multiple statements)
            cursor.executescript(sql)
            conn.commit()
            print(f"  ✓ {migration_file.name}")

        conn.close()
        print(f"\nMigrations completed successfully (db: {db_path})")
        return True

    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    db_path = get_db_path()
    if len(sys.argv) > 2 and sys.argv[1] == "--db":
        db_path = sys.argv[2]

    success = migrate(db_path)
    sys.exit(0 if success else 1)
