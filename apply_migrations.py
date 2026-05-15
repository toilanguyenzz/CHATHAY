"""Apply database migrations to Supabase using direct SQL."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import config

def get_connection_string():
    """Get PostgreSQL connection string from Supabase URL or env."""
    # Try DATABASE_URL first (common for Supabase local dev)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Alternatively, construct from Supabase connection string
    # Supabase provides the connection string in the settings
    # For Railway deployment, use SUPABASE_CONNECTION_STRING
    db_url = os.getenv("SUPABASE_CONNECTION_STRING")
    if db_url:
        return db_url

    # For local dev, you might have a separate Postgres URL
    # In production (Railway), Supabase is external, so we need the full connection string
    print("ERROR: DATABASE_URL or SUPABASE_CONNECTION_STRING not set")
    print("Please set one of these environment variables with your Postgres connection string")
    print("Format: postgresql://user:password@host:port/database")
    return None

def apply_migration(migration_file: str, conn):
    """Apply a single SQL migration file."""
    migration_path = Path(__file__).parent / "migrations" / migration_file

    if not migration_path.exists():
        print(f"Migration file not found: {migration_path}")
        return False

    sql = migration_path.read_text(encoding="utf-8")

    with conn.cursor() as cur:
        # Split by semicolon to execute multiple statements
        statements = [s.strip() for s in sql.split(';') if s.strip()]

        for i, stmt in enumerate(statements, 1):
            if not stmt:
                continue
            try:
                cur.execute(stmt)
                print(f"  Statement {i}/{len(statements)}: OK")
            except Exception as e:
                # Many statements might fail if already exists (tables, indexes, etc.)
                error_msg = str(e).lower()
                if "already exists" in error_msg or "duplicate" in error_msg:
                    print(f"  Statement {i}: already exists (skipped)")
                else:
                    print(f"  Statement {i}: ERROR - {str(e)[:100]}")

        conn.commit()
        print(f"\n  Migration {migration_file} applied!")
        return True

def main():
    db_url = get_connection_string()
    if not db_url:
        sys.exit(1)

    print(f"Connecting to database...")
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        print("Connected successfully!\n")
    except ImportError:
        print("psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted([
        f.name for f in migrations_dir.glob("*.sql")
    ])

    print(f"Found {len(migration_files)} migrations to apply\n")

    for migration in migration_files:
        print(f"Applying: {migration}")
        apply_migration(migration, conn)
        print()

    conn.close()
    print("All migrations completed!")

if __name__ == "__main__":
    main()
