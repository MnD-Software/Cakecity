"""Apply append-only Cake City SQL migrations.

Render runs this as a pre-deploy command. Each migration is committed together with
its checksum so an edited migration fails instead of silently drifting production.
"""
import asyncio
import hashlib
import os
from pathlib import Path
import asyncpg


def source_migrations_for(script_path: Path) -> Path:
    """Find repository migrations without assuming a minimum path depth."""
    resolved = script_path.resolve()
    for parent in resolved.parents:
        candidate = parent / "database" / "migrations"
        if candidate.is_dir():
            return candidate
    return resolved.parent / "database" / "migrations"


SOURCE_MIGRATIONS = source_migrations_for(Path(__file__))
PACKAGED_MIGRATIONS = Path(__file__).with_name("migrations")
MIGRATIONS = SOURCE_MIGRATIONS if SOURCE_MIGRATIONS.is_dir() else PACKAGED_MIGRATIONS


async def migrate() -> None:
    migration_files = sorted(MIGRATIONS.glob("*.sql"))
    if not migration_files:
        raise RuntimeError(f"No migrations found in {MIGRATIONS}")
    database_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(database_url)
    try:
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version varchar(180) PRIMARY KEY,
              checksum varchar(64) NOT NULL,
              applied_at timestamptz NOT NULL DEFAULT now()
            )
        """)
        for path in migration_files:
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            existing = await connection.fetchval(
                "SELECT checksum FROM schema_migrations WHERE version = $1", path.name
            )
            if existing:
                if existing != checksum:
                    raise RuntimeError(f"Applied migration was modified: {path.name}")
                continue
            async with connection.transaction():
                await connection.execute(sql)
                await connection.execute(
                    "INSERT INTO schema_migrations(version, checksum) VALUES($1, $2)",
                    path.name, checksum,
                )
            print(f"Applied {path.name}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(migrate())
