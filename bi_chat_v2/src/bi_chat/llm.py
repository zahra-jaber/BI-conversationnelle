from __future__ import annotations

from typing import Any

from bi_chat.config import Settings


def build_chat_model(settings: Settings) -> Any:
    try:
        from langchain_ollama import ChatOllama
    except Exception:
        from langchain_community.chat_models import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_chat_model,
        temperature=0,
    )


def build_embeddings(settings: Settings) -> Any:
    try:
        from langchain_ollama import OllamaEmbeddings
    except Exception:
        from langchain_community.embeddings import OllamaEmbeddings

    return OllamaEmbeddings(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embed_model,
    )
