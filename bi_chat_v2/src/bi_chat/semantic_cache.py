from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from bi_chat.config import Settings
from bi_chat.llm import build_embeddings


@dataclass(frozen=True)
class CacheHit:
    question: str
    sql: str
    answer: str
    score: float


class SemanticCache:
    def __init__(self, settings: Settings, path: str = "data/cache.sqlite") -> None:
        self.settings = settings
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question TEXT NOT NULL,
              embedding_json TEXT,
              sql TEXT,
              answer TEXT,
              created_at INTEGER NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created_at ON cache_entries(created_at)")
        self._conn.commit()
        self._emb = None

    def _ensure_embedder(self) -> Optional[Any]:
        if self._emb is not None:
            return self._emb
        try:
            self._emb = build_embeddings(self.settings)
        except Exception:
            self._emb = None
        return self._emb

    def _embed(self, text: str) -> Optional[np.ndarray]:
        emb = self._ensure_embedder()
        if emb is None:
            return None
        try:
            vec = emb.embed_query(text)
            return np.array(vec, dtype=np.float32)
        except Exception:
            return None

    def lookup(self, question: str, threshold: float, max_age_seconds: int = 60 * 60 * 24 * 30) -> Optional[CacheHit]:
        now = int(time.time())
        cutoff = now - int(max_age_seconds)

        qvec = self._embed(question)
        if qvec is None:
            row = self._conn.execute(
                "SELECT question, sql, answer FROM cache_entries WHERE question = ? AND created_at >= ? ORDER BY id DESC LIMIT 1",
                (question, cutoff),
            ).fetchone()
            if row:
                return CacheHit(question=row[0], sql=row[1] or "", answer=row[2] or "", score=1.0)
            return None

        rows = self._conn.execute(
            "SELECT question, embedding_json, sql, answer FROM cache_entries WHERE embedding_json IS NOT NULL AND created_at >= ?",
            (cutoff,),
        ).fetchall()
        if not rows:
            return None

        best: Optional[CacheHit] = None
        qn = float(np.linalg.norm(qvec)) + 1e-9
        for question_text, emb_json, sql, answer in rows:
            try:
                e = np.array(json.loads(emb_json), dtype=np.float32)
                score = float(np.dot(qvec, e) / (qn * (float(np.linalg.norm(e)) + 1e-9)))
            except Exception:
                continue
            if best is None or score > best.score:
                best = CacheHit(question=str(question_text), sql=str(sql or ""), answer=str(answer or ""), score=score)

        if best and best.score >= float(threshold):
            return best
        return None

    def store(self, question: str, sql: str, answer: str) -> None:
        now = int(time.time())
        qvec = self._embed(question)
        emb_json = json.dumps(qvec.tolist()) if qvec is not None else None
        self._conn.execute(
            "INSERT INTO cache_entries(question, embedding_json, sql, answer, created_at) VALUES(?, ?, ?, ?, ?)",
            (question, emb_json, sql, answer, now),
        )
        self._conn.commit()
