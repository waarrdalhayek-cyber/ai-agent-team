"""Local persistent state for commerce runs; no external service required."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any


class CommerceStateStore:
    def __init__(self, path: str='outputs/commerce/commerce.db'):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as con:
            con.execute('CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, stage TEXT, status TEXT, payload TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')

    def record(self, stage: str, status: str, payload: dict[str,Any]) -> int:
        with sqlite3.connect(self.path) as con:
            cur=con.execute('INSERT INTO runs(stage,status,payload) VALUES(?,?,?)',(stage,status,json.dumps(payload,ensure_ascii=False)))
            return int(cur.lastrowid)

    def latest(self, limit: int=20) -> list[dict[str,Any]]:
        with sqlite3.connect(self.path) as con:
            rows=con.execute('SELECT id,stage,status,payload,created_at FROM runs ORDER BY id DESC LIMIT ?',(limit,)).fetchall()
        return [{'id':r[0],'stage':r[1],'status':r[2],'payload':json.loads(r[3]),'created_at':r[4]} for r in rows]
