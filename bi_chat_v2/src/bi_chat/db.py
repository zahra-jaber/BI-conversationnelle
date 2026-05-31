from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from bi_chat.config import Settings


def make_engine(settings: Settings) -> Engine:
    url = (
        "postgresql+psycopg://{user}:{password}@{host}:{port}/{db}".format(
            user=settings.pg_user,
            password=settings.pg_password,
            host=settings.pg_host,
            port=settings.pg_port,
            db=settings.pg_database,
        )
    )
    return create_engine(url, pool_pre_ping=True)


@dataclass(frozen=True)
class DBSchema:
    tables: Dict[str, List[Tuple[str, str]]]

    def to_prompt(self, allowed_tables: List[str]) -> str:
        lines: List[str] = []
        allow_all = "*" in allowed_tables
        for table, cols in sorted(self.tables.items()):
            if not allow_all and table not in allowed_tables:
                continue
            col_str = ", ".join([f"{c} ({t})" for c, t in cols])
            lines.append(f"- {table}: {col_str}")
        return "\n".join(lines) if lines else "(aucune table autorisée)"


def inspect_schema(engine: Engine, schemas: List[str]) -> DBSchema:
    """Inspecte plusieurs schémas PostgreSQL."""
    sql = text(
        """
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ANY(:schemas)
        ORDER BY table_schema, table_name, ordinal_position
        """
    )
    tables: Dict[str, List[Tuple[str, str]]] = {}
    with engine.connect() as conn:
        rows = conn.execute(sql, {"schemas": schemas}).fetchall()
    for schema, table_name, column_name, data_type in rows:
        fq = f"{schema}.{table_name}"
        tables.setdefault(fq, []).append((str(column_name), str(data_type)))
    return DBSchema(tables=tables)


def run_query(engine: Engine, sql: str, max_rows: int, timeout_seconds: int) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        # Annuler toute transaction précédente bloquée
        try:
            conn.execute(text("ROLLBACK"))
        except Exception:
            pass

        try:
            if timeout_seconds > 0:
                conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_seconds) * 1000}"))
        except Exception:
            pass

        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchmany(size=max_rows)
        conn.commit()

    return [{columns[i]: r[i] for i in range(len(columns))} for r in rows]