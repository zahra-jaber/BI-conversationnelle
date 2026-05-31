from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import sqlglot
from sqlglot import exp


class SQLValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidationResult:
    sql: str
    referenced_tables: List[str]


_FORBIDDEN_ROOTS = tuple(
    cls
    for cls in [
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Create,
        exp.Drop,
        exp.Alter,
        getattr(exp, "Truncate", None),
        getattr(exp, "TruncateTable", None),
        exp.Grant,
        exp.Revoke,
        getattr(exp, "Command", None),
    ]
    if cls is not None
)


def _normalize_table_name(table: exp.Table, default_schema: str) -> str:
    if table.catalog:
        # catalog.schema.table; ignore catalog for ACL checks
        schema = table.db or default_schema
        return f"{schema}.{table.name}"
    if table.db:
        return f"{table.db}.{table.name}"
    return f"{default_schema}.{table.name}"


def validate_sql(
    sql: str,
    *,
    allowed_tables: List[str],
    default_schema: str,
    enforce_limit: Optional[int] = None,
) -> ValidationResult:
    if not sql or not sql.strip():
        raise SQLValidationError("SQL vide")

    if ";" in sql.strip().rstrip(";"):
        raise SQLValidationError("Multi-statement interdit")

    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except Exception as e:
        raise SQLValidationError(f"SQL invalide: {e}") from e

    if isinstance(parsed, _FORBIDDEN_ROOTS):
        raise SQLValidationError("Seul SELECT est autorisé")

    if not isinstance(parsed, (exp.Select, exp.Union, exp.With)):
        raise SQLValidationError("Seul SELECT est autorisé")

    # Forbid comments / dangerous tokens (simple heuristic)
    lowered = sql.lower()
    if "--" in lowered or "/*" in lowered or "*/" in lowered:
        raise SQLValidationError("Commentaires SQL interdits")
    if " copy " in lowered or lowered.strip().startswith("copy "):
        raise SQLValidationError("COPY interdit")

    referenced: List[str] = []
    for t in parsed.find_all(exp.Table):
        referenced.append(_normalize_table_name(t, default_schema))

    allow_all = "*" in allowed_tables
    if not allow_all:
        unauthorized = sorted(set([t for t in referenced if t not in allowed_tables]))
        if unauthorized:
            raise SQLValidationError(
                "Accès interdit aux tables: " + ", ".join(unauthorized)
            )

    if enforce_limit and enforce_limit > 0:
        parsed = _ensure_limit(parsed, enforce_limit)

    normalized = parsed.sql(dialect="postgres")
    return ValidationResult(sql=normalized, referenced_tables=sorted(set(referenced)))


def _ensure_limit(node: exp.Expression, limit: int) -> exp.Expression:
    # Add LIMIT if missing. If existing LIMIT > limit, cap it.
    if isinstance(node, exp.With):
        node.set("this", _ensure_limit(node.this, limit))
        return node

    if isinstance(node, exp.Union):
        node.set("this", _ensure_limit(node.this, limit))
        node.set("expression", _ensure_limit(node.expression, limit))
        if not node.args.get("limit"):
            node.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
        return node

    if isinstance(node, exp.Select):
        lim = node.args.get("limit")
        if lim is None:
            node.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
        else:
            try:
                expr = getattr(lim, "expression", None) or lim.args.get("expression")
                current = int(getattr(expr, "name", ""))
                if current > limit:
                    node.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
            except Exception:
                node.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
        return node

    return node
