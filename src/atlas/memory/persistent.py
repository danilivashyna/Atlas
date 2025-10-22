# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Persistent memory backend for semantic vectors (SQLite by default).

Stores 5D vectors with metadata and supports cosine similarity queries.
Interface matches MappaMemory for transparent backend switching.
"""

import json
import sqlite3
import tempfile
import time
from math import sqrt
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _cosine(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity for 5D vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class PersistentMemory:
    """
    Persistent memory backed by SQLite.

    Stores 5D vectors with metadata in a local database file.
    Cosine similarity is computed on-the-fly (no vector index yet).
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize persistent memory backend.

        Args:
            db_path: Path to SQLite database. If None, uses temp file.
        """
        if db_path is None:
            # Use temp directory for tests and default deployments
            self.db_path = str(Path(tempfile.gettempdir()) / "atlas_memory.db")
        else:
            self.db_path = db_path

        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database connection and schema."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()

        # Create items table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                v1 REAL NOT NULL,
                v2 REAL NOT NULL,
                v3 REAL NOT NULL,
                v4 REAL NOT NULL,
                v5 REAL NOT NULL,
                meta TEXT
            )
        """
        )
        self.conn.commit()

    def write(self, _id: str, vec5: List[float], meta: Optional[Dict[str, Any]] = None) -> None:
        """
        Write a vector to persistent memory.

        Args:
            _id: Unique identifier
            vec5: 5D vector as list of floats
            meta: Optional metadata dict
        """
        if not isinstance(vec5, list) or len(vec5) != 5:
            raise ValueError("vec5 must be a list of exactly 5 floats")

        if self.conn is None:
            self._init_db()

        cursor = self.conn.cursor()
        meta_json = json.dumps(meta) if meta else None

        cursor.execute(
            """
            INSERT OR REPLACE INTO items (id, v1, v2, v3, v4, v5, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (_id, vec5[0], vec5[1], vec5[2], vec5[3], vec5[4], meta_json),
        )
        self.conn.commit()

    def query(self, vec5: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query for similar vectors using cosine similarity.

        Args:
            vec5: 5D query vector
            top_k: Number of top results to return

        Returns:
            List of dicts with id, score, vector, meta
        """
        if not isinstance(vec5, list) or len(vec5) != 5:
            raise ValueError("vec5 must be a list of exactly 5 floats")

        if self.conn is None:
            self._init_db()

        cursor = self.conn.cursor()
        cursor.execute("SELECT id, v1, v2, v3, v4, v5, meta FROM items")
        rows = cursor.fetchall()

        scores = []
        for row in rows:
            _id, v1, v2, v3, v4, v5, meta_json = row
            v = [v1, v2, v3, v4, v5]
            sim = _cosine(vec5, v)
            meta = json.loads(meta_json) if meta_json else None
            scores.append((sim, _id, v, meta))

        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)

        items = []
        for sim, _id, v, meta in scores[:top_k]:
            items.append({"id": _id, "score": float(sim), "vector": v, "meta": meta})

        return items

    def flush(self) -> int:
        """
        Delete all records from memory.

        Returns:
            Number of records deleted
        """
        if self.conn is None:
            self._init_db()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items")
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM items")
        self.conn.commit()

        return count

    def load(self, path: str) -> int:
        """
        Bulk load records from JSONL file.

        Each line must be a JSON object with keys: id, vector (5-element list), meta (optional).

        Args:
            path: Path to .jsonl file

        Returns:
            Number of records loaded
        """
        if self.conn is None:
            self._init_db()

        loaded = 0
        with open(path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    item_id = record.get("id")
                    vector = record.get("vector")
                    meta = record.get("meta")

                    if item_id and isinstance(vector, list) and len(vector) == 5:
                        self.write(item_id, vector, meta)
                        loaded += 1
                except (json.JSONDecodeError, ValueError):
                    # Skip malformed lines
                    continue

        return loaded

    def stats(self) -> Dict[str, Any]:
        """
        Return memory statistics.

        Returns:
            Dict with backend, count, and path info
        """
        if self.conn is None:
            self._init_db()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items")
        count = cursor.fetchone()[0]

        try:
            size_bytes = Path(self.db_path).stat().st_size
        except Exception:
            size_bytes = 0

        return {
            "backend": "sqlite",
            "count": count,
            "path": self.db_path,
            "size_bytes": size_bytes,
        }

    def close(self) -> None:
        """Close database connection."""
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    # ---- Nodes (Router v0.4) Interface ----

    def _init_nodes_table(self) -> None:
        """Create nodes table if it doesn't exist."""
        if self.conn is None:
            self._init_db()

        cursor = self.conn.cursor()

        # Create nodes table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                path TEXT PRIMARY KEY,
                parent TEXT,
                v1 REAL NOT NULL,
                v2 REAL NOT NULL,
                v3 REAL NOT NULL,
                v4 REAL NOT NULL,
                v5 REAL NOT NULL,
                label TEXT,
                weight REAL DEFAULT 0.5,
                meta TEXT
            )
        """
        )

        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(path)")

        self.conn.commit()

    def write_node(
        self,
        path: str,
        parent: Optional[str],
        vec5: List[float],
        label: Optional[str] = None,
        weight: float = 0.5,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write a hierarchical node.

        Args:
            path: Node path (e.g., "dim2/dim2.4")
            parent: Parent node path or None for root
            vec5: 5D vector
            label: Human-readable label
            weight: Priority weight [0..1]
            meta: Optional metadata
        """
        self._init_nodes_table()

        if not isinstance(vec5, list) or len(vec5) != 5:
            raise ValueError("vec5 must be a list of exactly 5 floats")

        cursor = self.conn.cursor()
        meta_json = json.dumps(meta) if meta else None

        cursor.execute(
            """
            INSERT OR REPLACE INTO nodes
            (path, parent, v1, v2, v3, v4, v5, label, weight, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                path,
                parent,
                vec5[0],
                vec5[1],
                vec5[2],
                vec5[3],
                vec5[4],
                label,
                weight,
                meta_json,
            ),
        )
        self.conn.commit()

    def get_children(self, parent_path: str) -> List[Dict[str, Any]]:
        """Get all child nodes of a given parent."""
        self._init_nodes_table()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT path, parent, v1, v2, v3, v4, v5, label, weight, meta
            FROM nodes
            WHERE parent = ?
        """,
            (parent_path,),
        )
        rows = cursor.fetchall()

        result = []
        for row in rows:
            path, parent, v1, v2, v3, v4, v5, label, weight, meta_json = row
            result.append(
                {
                    "path": path,
                    "parent": parent,
                    "vec5": [v1, v2, v3, v4, v5],
                    "label": label,
                    "weight": weight,
                    "meta": json.loads(meta_json) if meta_json else None,
                }
            )
        return result

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes."""
        self._init_nodes_table()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT path, parent, v1, v2, v3, v4, v5, label, weight, meta
            FROM nodes
        """
        )
        rows = cursor.fetchall()

        result = []
        for row in rows:
            path, parent, v1, v2, v3, v4, v5, label, weight, meta_json = row
            result.append(
                {
                    "path": path,
                    "parent": parent,
                    "vec5": [v1, v2, v3, v4, v5],
                    "label": label,
                    "weight": weight,
                    "meta": json.loads(meta_json) if meta_json else None,
                }
            )
        return result

    def knn_nodes(self, vec5: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Query k-nearest nodes by cosine similarity."""
        self._init_nodes_table()

        if not isinstance(vec5, list) or len(vec5) != 5:
            raise ValueError("vec5 must be a list of exactly 5 floats")

        all_nodes = self.get_all_nodes()

        scores = []
        for node in all_nodes:
            node_vec = node["vec5"]
            sim = _cosine(vec5, node_vec)
            scores.append((sim, node))

        scores.sort(key=lambda x: x[0], reverse=True)

        result = []
        for sim, node in scores[:top_k]:
            result.append({**node, "score": float(sim)})

        return result

    def stats_nodes(self) -> Dict[str, Any]:
        """Get statistics for nodes table."""
        self._init_nodes_table()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        count = cursor.fetchone()[0]

        return {
            "backend": "sqlite",
            "count_nodes": count,
            "path": self.db_path,
        }

    def flush_nodes(self) -> int:
        """Delete all nodes. Returns count deleted."""
        self._init_nodes_table()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM nodes")
        self.conn.commit()

        return count

    # ===== RETICULUM: Content Links (v0.5+) =====

    def _init_links_table(self) -> None:
        """Create links table if it doesn't exist. Links associate nodes with content."""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_path TEXT NOT NULL,
                content_id TEXT NOT NULL,
                kind TEXT DEFAULT 'doc',
                score REAL DEFAULT 0.0,
                meta TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Indices
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_links_node ON links(node_path)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_links_content ON links(content_id)
            """
        )

        self.conn.commit()

    def write_link(
        self,
        node_path: str,
        content_id: str,
        kind: str = "doc",
        score: float = 0.0,
        meta: Optional[dict] = None,
    ) -> None:
        """Write or update a link between a node and content."""
        self._init_links_table()
        cursor = self.conn.cursor()
        meta_str = json.dumps(meta) if meta else None
        cursor.execute(
            "INSERT OR REPLACE INTO links (node_path, content_id, kind, score, meta) VALUES (?, ?, ?, ?, ?)",
            (node_path, content_id, kind, score, meta_str),
        )
        self.conn.commit()

    def get_links(self, node_path: str) -> List[Dict[str, Any]]:
        """Get all links for a specific node."""
        self._init_links_table()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, node_path, content_id, kind, score, meta FROM links WHERE node_path = ? ORDER BY score DESC",
            (node_path,),
        )
        results = []
        for row in cursor.fetchall():
            meta = json.loads(row[5]) if row[5] else None
            results.append(
                {
                    "id": row[0],
                    "node_path": row[1],
                    "content_id": row[2],
                    "kind": row[3],
                    "score": row[4],
                    "meta": meta,
                }
            )
        return results

    def query_links(
        self, path_prefix: Optional[str] = None, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Query links, optionally filtered by path prefix for subtree search."""
        self._init_links_table()
        cursor = self.conn.cursor()
        if path_prefix:
            like_pattern = f"{path_prefix}%"
            cursor.execute(
                "SELECT id, node_path, content_id, kind, score, meta FROM links WHERE node_path LIKE ? ORDER BY score DESC LIMIT ?",
                (like_pattern, top_k),
            )
        else:
            cursor.execute(
                "SELECT id, node_path, content_id, kind, score, meta FROM links ORDER BY score DESC LIMIT ?",
                (top_k,),
            )
        results = []
        for row in cursor.fetchall():
            meta = json.loads(row[5]) if row[5] else None
            results.append(
                {
                    "id": row[0],
                    "node_path": row[1],
                    "content_id": row[2],
                    "kind": row[3],
                    "score": row[4],
                    "meta": meta,
                }
            )
        return results

    def delete_link(self, link_id: int) -> bool:
        """Delete a link by ID. Returns True if deleted."""
        self._init_links_table()
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM links WHERE id = ?", (link_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def flush_links(self) -> int:
        """Delete all links. Returns count deleted."""
        self._init_links_table()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM links")
        self.conn.commit()
        return count

    def flush_link_versions(self) -> int:
        """Delete all link_versions. Returns count deleted."""
        self._init_link_versions()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM link_versions")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM link_versions")
        self.conn.commit()
        return count

    def get_node(self, path: str):
        self._init_nodes_table()
        c = self.conn.cursor()
        c.execute(
            """SELECT path, parent, v1, v2, v3, v4, v5, label, weight, meta
                     FROM nodes WHERE path = ?""",
            (path,),
        )
        row = c.fetchone()
        if not row:
            return None
        path, parent, v1, v2, v3, v4, v5, label, weight, meta_json = row
        return {
            "path": path,
            "parent": parent,
            "vec5": [v1, v2, v3, v4, v5],
            "label": label,
            "weight": weight,
            "meta": json.loads(meta_json) if meta_json else None,
        }

    def _init_link_versions(self):
        cur = self.conn.cursor()
        cur.execute(
            """
          CREATE TABLE IF NOT EXISTS link_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_path TEXT NOT NULL,
            content_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            score REAL DEFAULT 0.0,
            kind TEXT DEFAULT 'doc',
            meta TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(node_path, content_id, version)
          )"""
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_lv_node ON link_versions(node_path)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_lv_content ON link_versions(content_id)")
        self.conn.commit()

    def write_link_version(
        self,
        node_path: str,
        content_id: str,
        version: int,
        score: float = 0.0,
        kind: str = "doc",
        meta: dict | None = None,
    ) -> None:
        self._init_link_versions()
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO link_versions
            (node_path, content_id, version, score, kind, meta)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (node_path, content_id, version, score, kind, json.dumps(meta) if meta else None),
        )
        self.conn.commit()

    def get_link_versions(self, content_id: str):
        self._init_link_versions()
        cur = self.conn.cursor()
        cur.execute(
            """SELECT node_path, content_id, version, score, kind, meta, created_at
                       FROM link_versions WHERE content_id = ?
                       ORDER BY version DESC, created_at DESC""",
            (content_id,),
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            meta = json.loads(r[5]) if r[5] else None
            out.append(
                {
                    "node_path": r[0],
                    "content_id": r[1],
                    "version": r[2],
                    "score": r[3],
                    "kind": r[4],
                    "meta": meta,
                    "created_at": r[6],
                }
            )
        return out

    def resolve_latest(self, content_id: str, top_k: int = 5):
        self._init_link_versions()
        cur = self.conn.cursor()
        cur.execute(
            """SELECT node_path, MAX(version) as v
                       FROM link_versions WHERE content_id=?
                       GROUP BY node_path ORDER BY v DESC""",
            (content_id,),
        )
        rows = cur.fetchall()
        # вернём top_k последних по version
        out = [{"path": r[0], "version": int(r[1])} for r in rows[:top_k]]
        return out

    def stats_links(self) -> Dict[str, Any]:
        """Get statistics for links table."""
        self._init_links_table()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT content_id) FROM links")
        unique_content = cursor.fetchone()[0]
        return {"count_links": count, "count_unique_content": unique_content}

    def query_link_versions(
        self, path_prefix: Optional[str] = None, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Query link_versions, optionally filtered by path prefix for subtree search."""
        self._init_link_versions()
        cursor = self.conn.cursor()
        if path_prefix:
            like_pattern = f"{path_prefix}%"
            cursor.execute(
                "SELECT node_path, content_id, version, score, kind, meta, strftime('%s', created_at) FROM link_versions WHERE node_path LIKE ? ORDER BY score DESC LIMIT ?",
                (like_pattern, top_k),
            )
        else:
            cursor.execute(
                "SELECT node_path, content_id, version, score, kind, meta, strftime('%s', created_at) FROM link_versions ORDER BY score DESC LIMIT ?",
                (top_k,),
            )
        results = []
        for row in cursor.fetchall():
            meta = json.loads(row[5]) if row[5] else None
            created_at_ts = float(row[6]) if row[6] else time.time()
            results.append(
                {
                    "node_path": row[0],
                    "content_id": row[1],
                    "version": row[2],
                    "score": row[3],
                    "kind": row[4],
                    "meta": meta,
                    "created_at_ts": created_at_ts,
                }
            )
        return results
