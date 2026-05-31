import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bi_chat.acl import load_acl
from bi_chat.agent import answer_question
from bi_chat.auth import connecter_keycloak
from bi_chat.config import Settings
from bi_chat.history import HistoryStore

st.set_page_config(page_title="BI Chat", page_icon="💬", layout="wide")

ROLE_LABELS = {
    "finance": "💰 Finance",
    "rh": "👥 Ressources Humaines",
    "marketing": "📣 Marketing",
    "admin": "🔧 Administrateur",
}
ROLE_COLORS = {
    "finance": "#FAEEDA",
    "rh": "#E1F5EE",
    "marketing": "#EEEDFE",
    "admin": "#FCEBEB",
}


def _init_state() -> None:
    if "user" not in st.session_state:
        st.session_state.user = None
    if "settings" not in st.session_state:
        st.session_state.settings = Settings()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = HistoryStore()
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())


_init_state()
acl = load_acl("acl.yaml")
settings: Settings = st.session_state.settings


# ══════════════════════════════════════════════════════════════
# PAGE DE CONNEXION
# ══════════════════════════════════════════════════════════════
def page_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 💬 BI Chat")
        st.markdown("Connectez-vous pour accéder à vos données")
        st.divider()

        login = st.text_input("Login", placeholder="ex: sara.finance")
        password = st.text_input("Mot de passe", type="password", placeholder="••••••••")

        if st.button("Se connecter", use_container_width=True):
            if not login or not password:
                st.error("Veuillez renseigner votre login et mot de passe.")
            else:
                with st.spinner("Vérification en cours..."):
                    user, erreur = connecter_keycloak(login, password, settings)
                if erreur:
                    st.error(f"❌ {erreur}")
                else:
                    st.session_state.user = user
                    st.rerun()

        st.divider()
        st.caption(
            "🔒 L'authentification est gérée par Keycloak. "
            "Votre rôle est assigné automatiquement par l'administrateur."
        )


# ══════════════════════════════════════════════════════════════
# PAGE PRINCIPALE — CHAT
# ══════════════════════════════════════════════════════════════
def page_chat():
    user = st.session_state.user
    role = user["role"]
    label = ROLE_LABELS.get(role, role)
    color = ROLE_COLORS.get(role, "#F1EFE8")

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {user['nom']}")
        st.markdown(
            f"<span style='background:{color}; padding:4px 12px; border-radius:20px; "
            f"font-size:13px; font-weight:500;'>{label}</span>",
            unsafe_allow_html=True,
        )
        st.divider()

        tables = acl.allowed_tables_for_role(role)
        st.markdown("**Tables accessibles :**")
        if "*" in tables:
            st.markdown("_Toutes les tables_")
        else:
            for t in tables:
                st.markdown(f"- `{t}`")

        st.divider()
        show_sql = st.toggle("Afficher le SQL généré", value=False)
        if st.button("🗑️ Réinitialiser la conversation"):
            st.session_state.messages = []
            st.rerun()
        if st.button("🔓 Se déconnecter"):
            st.session_state.user = None
            st.session_state.messages = []
            st.rerun()

    # En-tête
    st.title(f"💬 BI Chat — {label}")
    st.caption("Posez vos questions en français. Je les traduis en SQL et vous réponds.")
    st.divider()

    # Afficher l'historique des messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if show_sql and msg.get("sql"):
                with st.expander("🔍 Voir le SQL généré"):
                    st.code(msg["sql"], language="sql")
            if msg.get("figure") is not None:
                st.plotly_chart(msg["figure"], use_container_width=True)
            if msg.get("rows"):
                st.dataframe(msg["rows"], use_container_width=True)

    # Zone de saisie
    user_question = st.chat_input("Posez votre question…")
    if user_question:
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Je réfléchis…"):
                result = answer_question(
                    question=user_question,
                    settings=settings,
                    acl=acl,
                    role=role,
                    chat_history=st.session_state.messages,
                    history_store=st.session_state.history,
                    session_id=st.session_state.session_id,
                )
            st.markdown(result.answer)
            if show_sql and result.sql:
                with st.expander("🔍 Voir le SQL généré"):
                    st.code(result.sql, language="sql")
            if result.figure is not None:
                st.plotly_chart(result.figure, use_container_width=True)
            if result.rows:
                st.dataframe(result.rows, use_container_width=True)

        st.session_state.messages.append({
            "role": "assistant",
            "content": result.answer,
            "sql": result.sql,
            "figure": result.figure,
            "rows": result.rows,
        })


# ══════════════════════════════════════════════════════════════
# ROUTAGE
# ══════════════════════════════════════════════════════════════
if st.session_state.user is None:
    page_login()
else:
    page_chat()
