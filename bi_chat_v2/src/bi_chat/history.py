from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class HistoryStore:
    def __init__(self, path: str = "data/history.sqlite") -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at INTEGER NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, id)")
        self._conn.commit()

    def append(self, session_id: str, role: str, content: str) -> None:
        now = int(time.time())
        self._conn.execute(
            "INSERT INTO chat_messages(session_id, role, content, created_at) VALUES(?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        self._conn.commit()

    def get_last(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, int(limit)),
        ).fetchall()
        rows.reverse()
        return [{"role": r[0], "content": r[1]} for r in rows]
