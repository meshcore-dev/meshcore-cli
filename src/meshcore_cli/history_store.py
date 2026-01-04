
# -*- coding: utf-8 -*-
"""
HistoryStore: jednoduché perzistentní úložiště zpráv pro meshcore-cli
- ukládá do ~/.config/meshcore/history/<device_name>/messages.jsonl
- poskytuje metody append(record) a tail(n)
"""
import json
import os
from datetime import datetime, timezone
from typing import List, Dict


class HistoryStore:
    def __init__(self, node_name: str, base_dir: str = None, rotate_daily: bool = False):
        self.node_name = node_name or "unknown"
        self.base_dir = base_dir or os.path.expanduser(f"~/.config/meshcore/history/{self.node_name}")
        self.rotate_daily = rotate_daily
        os.makedirs(self.base_dir, exist_ok=True)

    def _file_path(self) -> str:
        if self.rotate_daily:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return os.path.join(self.base_dir, f"messages-{day}.jsonl")
        return os.path.join(self.base_dir, "messages.jsonl")

    def append(self, record: Dict) -> None:
        """
        Přidá záznam do historie; automaticky doplní timestamp (UTC) a node_name.
        """
        rec = dict(record)
        rec.setdefault("ts", datetime.now(timezone.utc).isoformat())
        rec.setdefault("node_name", self.node_name)
        fp = self._file_path()
        with open(fp, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def tail(self, n: int = 50) -> List[Dict]:
        """
        Vrátí posledních n záznamů z historie.
        """
        fp = self._file_path()
        if not os.path.exists(fp):
            return []
        # jednoduchý "tail": čte bloky od konce; pro běžné velikosti souboru dostačující
        with open(fp, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 2048
            data = b""
            lines = []
            while len(lines) <= n and size > 0:
                size = max(0, size - block)
                f.seek(size)
                data = f.read(block) + data
                lines = data.splitlines()
            tail = lines[-n:] if len(lines) >= n else lines
            out = []
            for l in tail:
                if not l.strip():
                    continue
                try:
                    out.append(json.loads(l.decode("utf-8")))
                except Exception:
                    # poškozená řádka – přeskočit
                    pass
            return out

