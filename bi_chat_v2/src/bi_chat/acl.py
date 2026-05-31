from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


def _load_yaml(path: str) -> dict:
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class ACL:
    roles_to_tables: Dict[str, List[str]]

    def list_roles(self) -> List[str]:
        return sorted(self.roles_to_tables.keys())

    def allowed_tables_for_role(self, role: str) -> List[str]:
        return self.roles_to_tables.get(role, [])

    def schema_for_role(self, role: str) -> str:
        """Retourne le schéma principal associé au rôle."""
        if role == "rh":
            return "rh"
        return "ecommerce"


def load_acl(path: str) -> ACL:
    if not Path(path).exists():
        return ACL(roles_to_tables={"admin": ["*"]})
    raw = _load_yaml(path)
    roles = raw.get("roles", {})
    roles_to_tables: Dict[str, List[str]] = {}
    for role, spec in roles.items():
        roles_to_tables[str(role)] = list((spec or {}).get("allowed_tables", []) or [])
    if "admin" not in roles_to_tables:
        roles_to_tables["admin"] = ["*"]
    return ACL(roles_to_tables=roles_to_tables)
