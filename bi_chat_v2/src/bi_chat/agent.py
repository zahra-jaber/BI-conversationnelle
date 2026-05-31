from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bi_chat.acl import ACL
from bi_chat.config import Settings
from bi_chat.db import inspect_schema, make_engine, run_query
from bi_chat.llm import build_chat_model
from bi_chat.semantic_cache import SemanticCache
from bi_chat.sql_validation import SQLValidationError, validate_sql
from bi_chat.viz import make_figure


@dataclass(frozen=True)
class AgentResult:
    answer: str
    sql: Optional[str] = None
    figure: Any = None
    rows: Optional[List[Dict[str, Any]]] = None
    from_cache: bool = False


_SQL_RE = re.compile(r"(?is)\bSQL\s*:\s*(.+)$")
_CLARIFY_RE = re.compile(r"(?is)^\s*CLARIFY\s*:\s*(.+)$")


def _check_table_access(sql: str, allowed_tables: List[str]) -> None:
    """Vérifie que le SQL n'utilise que les tables autorisées."""
    if "*" in allowed_tables:
        return

    allowed_lower = [t.lower() for t in allowed_tables]

    # Chercher uniquement les vraies tables après FROM et JOIN
    from_join_pattern = re.compile(
        r'(?:FROM|JOIN)\s+([a-zA-Z_]+\.[a-zA-Z_]+)',
        re.IGNORECASE
    )
    tables_in_sql = from_join_pattern.findall(sql)

    for table in tables_in_sql:
        if table.lower() not in allowed_lower:
            raise SQLValidationError(
                f"Accès refusé : la table '{table}' n'est pas autorisée pour votre rôle."
            )


def _build_prompt(
    question: str,
    schema_prompt: str,
    allowed_tables: List[str],
    chat_history: List[Dict[str, Any]],
) -> str:
    acl_txt = "*" if "*" in allowed_tables else ", ".join(allowed_tables)
    return (
        "Tu es un générateur SQL PostgreSQL. Tu reçois une question et tu réponds UNIQUEMENT avec une requête SQL.\n"
        "RÈGLES ABSOLUES :\n"
        "1. Réponds TOUJOURS avec : SQL: <requête SQL complète>\n"
        "2. Ne donne JAMAIS d'explication, jamais de texte, jamais de commentaire\n"
        "3. Utilise UNIQUEMENT les tables listées dans 'Tables autorisées' ci-dessous\n"
        "4. Ajoute toujours le schéma devant la table ex: ecommerce.olist_orders_dataset\n"
        "5. Si la question nécessite une table NON autorisée réponds : CLARIFY: Cette question dépasse votre périmètre d'accès.\n"
        "6. Si la question est ambiguë réponds : CLARIFY: <question de clarification>\n"
        "7. INTERDIT : INSERT UPDATE DELETE DROP CREATE\n"
        "8. Une seule requête SQL, pas de point-virgule à la fin\n\n"
        f"Tables autorisées (UNIQUEMENT ces tables) : {acl_txt}\n\n"
        "Schéma :\n"
        f"{schema_prompt}\n\n"
        "EXEMPLES :\n"
        "Question : Quel est le chiffre d'affaires total ?\n"
        "SQL: SELECT SUM(payment_value) AS chiffre_affaires_total FROM ecommerce.olist_order_payments_dataset\n\n"
        "Question : Combien de commandes y a-t-il ?\n"
        "SQL: SELECT COUNT(*) AS nombre_commandes FROM ecommerce.olist_orders_dataset\n\n"
        "Question : Quelles sont les 5 catégories les plus vendues ?\n"
        "SQL: SELECT p.product_category_name, COUNT(*) AS nb_ventes FROM ecommerce.olist_order_items_dataset i JOIN ecommerce.olist_products_dataset p ON i.product_id = p.product_id GROUP BY p.product_category_name ORDER BY nb_ventes DESC LIMIT 5\n\n"
        "Question : Quel est le nombre d employés par département ?\n"
        "SQL: SELECT department, COUNT(*) AS nombre_employes FROM rh.employees GROUP BY department ORDER BY nombre_employes DESC\n\n"
        f"Question : {question}\n"
        "SQL:"
    )


def _extract_sql_or_clarify(text: str) -> Dict[str, str]:
    text = text.strip()

    # Chercher CLARIFY
    m = _CLARIFY_RE.match(text)
    if m:
        return {"clarify": m.group(1).strip()}

    # Chercher SQL:
    m2 = _SQL_RE.search(text)
    if m2:
        sql = m2.group(1).strip()
        sql = sql.split(";")[0].strip()
        return {"sql": sql}

    # Si commence directement par SELECT
    if text.upper().startswith("SELECT"):
        sql = text.split(";")[0].strip()
        return {"sql": sql}

    return {"clarify": "Peux-tu reformuler ta question ?"}


def answer_question(
    *,
    question: str,
    settings: Settings,
    acl: ACL,
    role: str,
    chat_history: List[Dict[str, Any]],
    history_store: Any,
    session_id: str,
) -> AgentResult:
    allowed_tables = acl.allowed_tables_for_role(role)
    cache = SemanticCache(settings)

    # Vérifier le cache sémantique
    hit = cache.lookup(question, threshold=settings.app_cache_similarity_threshold)
    if hit:
        return AgentResult(
            answer=hit.answer + f"\n\n_(réponse depuis le cache sémantique, similarité={hit.score:.2f})_",
            sql=hit.sql,
            from_cache=True,
        )

    # Connexion à la base
    try:
        engine = make_engine(settings)
        schemas = ["ecommerce", "rh"] if role == "admin" else [acl.schema_for_role(role)]
        dbschema = inspect_schema(engine, schemas)
    except Exception as e:
        return AgentResult(answer=f"❌ Impossible de se connecter à PostgreSQL : {e}")

    schema_prompt = dbschema.to_prompt(allowed_tables)
    llm = build_chat_model(settings)

    # Générer le SQL
    prompt = _build_prompt(question, schema_prompt, allowed_tables, chat_history)
    try:
        raw = llm.invoke(prompt)
        llm_text = getattr(raw, "content", None) or str(raw)
    except Exception as e:
        return AgentResult(answer=f"❌ Erreur LLM : {e}")

    parsed = _extract_sql_or_clarify(llm_text)
    if "clarify" in parsed:
        return AgentResult(answer=f"🤔 {parsed['clarify']}")

    sql = parsed.get("sql", "")

    # Valider le SQL
    try:
        vr = validate_sql(
            sql,
            allowed_tables=allowed_tables,
            default_schema=acl.schema_for_role(role),
            enforce_limit=settings.app_max_rows,
        )
    except SQLValidationError as e:
        return AgentResult(answer=f"❌ SQL refusé par validation : {e}")

    # Vérifier l'accès aux tables
    try:
        _check_table_access(vr.sql, allowed_tables)
    except SQLValidationError as e:
        return AgentResult(answer=f"🔒 {e}")

    # Exécuter la requête
    try:
        rows = run_query(
            engine,
            vr.sql,
            max_rows=settings.app_max_rows,
            timeout_seconds=settings.app_sql_timeout_seconds,
        )
    except Exception as e:
        return AgentResult(answer=f"❌ Erreur lors de l'exécution SQL : {e}", sql=vr.sql)

    # Générer la réponse
    if not rows:
        answer = "Aucun résultat trouvé pour cette question."
        fig = None
    else:
        answer = f"✅ {len(rows)} résultat(s) trouvé(s)."
        fig = make_figure(rows, question=question)

    # Stocker dans le cache
    cache.store(question, vr.sql, answer)

    # Sauvegarder dans l'historique
    try:
        history_store.append(session_id, "user", question)
        history_store.append(session_id, "assistant", answer)
    except Exception:
        pass

    return AgentResult(answer=answer, sql=vr.sql, figure=fig, rows=rows)