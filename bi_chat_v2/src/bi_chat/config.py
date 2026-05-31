from __future__ import annotations

from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass
class Settings:
    # PostgreSQL
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "bi_chat"
    pg_user: str = "bi_user"
    pg_password: str = "bi_password"

    # Keycloak
    keycloak_url: str = "http://localhost:8180"
    keycloak_realm: str = "bi-chat"
    keycloak_client_id: str = "bi-chat-app"
    keycloak_client_secret: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3"
    ollama_embed_model: str = "nomic-embed-text"

    # Application
    app_max_rows: int = 500
    app_cache_similarity_threshold: float = 0.92
    app_sql_timeout_seconds: int = 20

    def __post_init__(self) -> None:
        load_dotenv(override=False)

        self.pg_host = os.getenv("PG_HOST", self.pg_host)
        self.pg_port = int(os.getenv("PG_PORT", str(self.pg_port)))
        self.pg_database = os.getenv("PG_DATABASE", self.pg_database)
        self.pg_user = os.getenv("PG_USER", self.pg_user)
        self.pg_password = os.getenv("PG_PASSWORD", self.pg_password)

        self.keycloak_url = os.getenv("KEYCLOAK_URL", self.keycloak_url)
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", self.keycloak_realm)
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", self.keycloak_client_id)
        self.keycloak_client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", self.keycloak_client_secret)

        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", self.ollama_base_url)
        self.ollama_chat_model = os.getenv("OLLAMA_CHAT_MODEL", self.ollama_chat_model)
        self.ollama_embed_model = os.getenv("OLLAMA_EMBED_MODEL", self.ollama_embed_model)

        self.app_max_rows = int(os.getenv("APP_MAX_ROWS", str(self.app_max_rows)))
        self.app_cache_similarity_threshold = float(
            os.getenv("APP_CACHE_SIMILARITY_THRESHOLD", str(self.app_cache_similarity_threshold))
        )
        self.app_sql_timeout_seconds = int(
            os.getenv("APP_SQL_TIMEOUT_SECONDS", str(self.app_sql_timeout_seconds))
        )
