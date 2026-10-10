"""Ordered additive SQLite migrations; never run automatically against the original DB."""
from pathlib import Path
from sqlalchemy import inspect
from .extensions import db


def upgrade():
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("These migrations support SQLite; PostgreSQL needs reviewed dialect migrations")
    folder = Path(__file__).resolve().parents[1] / "migrations"
    with db.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            existing = set(inspect(connection).get_table_names())
            connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY NOT NULL)")
            applied = {row[0] for row in connection.exec_driver_sql("SELECT version FROM schema_migrations")}
            for script in sorted(folder.glob("*.sql")):
                if script.stem in applied:
                    continue
                if script.stem == "0001_existing_schema" and "users" in existing:
                    expected = set(db.metadata.tables) - {"auth_sessions", "credentials", "organizations", "organization_members"}
                    if not expected.issubset(existing):
                        raise RuntimeError("Existing database is incomplete; manual baseline review required")
                else:
                    for statement in script.read_text(encoding="utf-8").split(";"):
                        if statement.strip():
                            connection.exec_driver_sql(statement)
                connection.exec_driver_sql("INSERT INTO schema_migrations(version) VALUES (?)", (script.stem,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
