"""
Quelldex VCS — Lightweight version control system
Hash-addressed storage · Branches · Commits · Diffs · Merge · Tags
"""

import os
import hashlib
import json
import time
import difflib
import sqlite3
from pathlib import Path
from typing import Optional


class VCS:
    """Lightweight git-like version control for Quelldex projects."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.vcs_dir = self.project_path / ".quelldex"
        self.objects_dir = self.vcs_dir / "objects"
        self.db_path = self.vcs_dir / "meta.db"
        self._db: Optional[sqlite3.Connection] = None

    # ── Initialization ──────────────────────────────────────────

    def init(self):
        """Initialize VCS repository."""
        self.vcs_dir.mkdir(parents=True, exist_ok=True)
        self.objects_dir.mkdir(exist_ok=True)
        self._init_db()
        if not self.get_branches():
            self._create_branch("main")
            self._set_current_branch("main")

    def _init_db(self):
        db = self._get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS commits (
                id TEXT PRIMARY KEY,
                branch TEXT NOT NULL,
                parent_id TEXT,
                timestamp REAL NOT NULL,
                message TEXT NOT NULL,
                author TEXT DEFAULT 'user',
                snapshot TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS branches (
                name TEXT PRIMARY KEY,
                head_commit TEXT,
                created_at REAL NOT NULL,
                description TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS current_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tags (
                name TEXT PRIMARY KEY,
                commit_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                description TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commit_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_commits_branch ON commits(branch);
            CREATE INDEX IF NOT EXISTS idx_commits_ts ON commits(timestamp);
        """)
        db.commit()

    def _get_db(self) -> sqlite3.Connection:
        if self._db is None:
            self._db = sqlite3.connect(str(self.db_path))
            self._db.row_factory = sqlite3.Row
        return self._db

    def close(self):
        if self._db:
            self._db.close()
            self._db = None

    # ── Object Storage ──────────────────────────────────────────

    def _hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]

    def _store_object(self, content: bytes) -> str:
        h = self._hash_content(content)
        p = self.objects_dir / h[:2] / h[2:]
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'wb') as f:
                f.write(content)
        return h

    def _read_object(self, h: str) -> Optional[bytes]:
        p = self.objects_dir / h[:2] / h[2:]
        if p.exists():
            with open(p, 'rb') as f:
                return f.read()
        return None

    # -- Snapshots (optimized) ------------------------------------

    # Directories to skip (shared with project scanner)
    _IGNORE_DIRS = {
        ".git", ".svn", ".hg", ".quelldex",
        "node_modules", "__pycache__", ".venv", "venv", "env",
        ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
        ".next", ".nuxt", "dist", "build", ".cache",
        ".idea", ".vscode", ".vs",
        "vendor", "bower_components", "target", ".gradle", "Pods",
    }

    def _get_tracked_files(self) -> list:
        """Fast file listing using os.scandir, skips ignored dirs."""
        files = []
        root = str(self.project_path)

        def _scan(dirpath):
            try:
                entries = os.scandir(dirpath)
            except PermissionError:
                return
            with entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in self._IGNORE_DIRS:
                            _scan(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(Path(entry.path))

        _scan(root)
        files.sort()
        return files

    def _file_index(self) -> dict:
        """Build lightweight index: {rel_path: (mtime, size)} without reading content.
        Used for fast change detection."""
        root_str = str(self.project_path)
        root_len = len(root_str) + 1
        index = {}

        def _scan(dirpath):
            try:
                entries = os.scandir(dirpath)
            except PermissionError:
                return
            with entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in self._IGNORE_DIRS:
                            _scan(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            st = entry.stat(follow_symlinks=False)
                            rel = entry.path[root_len:].replace("\\", "/")
                            index[rel] = (st.st_mtime, st.st_size)
                        except OSError:
                            continue

        _scan(root_str)
        return index

    def _take_snapshot(self) -> dict:
        """Take full snapshot — reads and stores file content."""
        snapshot = {}
        for fp in self._get_tracked_files():
            rel = str(fp.relative_to(self.project_path)).replace("\\", "/")
            try:
                content = fp.read_bytes()
                snapshot[rel] = {
                    "hash": self._store_object(content),
                    "size": len(content),
                    "mtime": fp.stat().st_mtime
                }
            except (OSError, PermissionError):
                continue
        return snapshot

    def get_working_changes(self) -> dict:
        """Fast change detection using mtime+size comparison.
        Only hashes files that actually changed."""
        branch = self.get_current_branch()
        head = self._get_branch_head(branch) if branch else None
        last_snap = self.get_commit_snapshot(head) if head else {}

        current_index = self._file_index()
        added = {}
        modified = {}
        removed = {}

        # Check for added and modified files
        for rel, (mtime, size) in current_index.items():
            if rel not in last_snap:
                added[rel] = {"size": size, "mtime": mtime}
            else:
                old = last_snap[rel]
                # Fast path: if mtime and size match, skip (unchanged)
                if abs(old.get("mtime", 0) - mtime) < 0.001 and old.get("size", -1) == size:
                    continue
                # mtime or size differ — mark as modified (without hashing)
                modified[rel] = {"old": old, "new": {"size": size, "mtime": mtime}}

        # Check for removed files
        for rel in last_snap:
            if rel not in current_index:
                removed[rel] = last_snap[rel]

        return {"added": added, "removed": removed, "modified": modified}

    def _restore_snapshot(self, snapshot: dict):
        for fp in self._get_tracked_files():
            rel = str(fp.relative_to(self.project_path))
            if rel not in snapshot:
                fp.unlink()
                try:
                    fp.parent.rmdir()
                except OSError:
                    pass
        for rel, info in snapshot.items():
            fp = self.project_path / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            content = self._read_object(info["hash"])
            if content is not None:
                fp.write_bytes(content)

    # ── Commits ─────────────────────────────────────────────────

    def commit(self, message: str, author: str = "user") -> Optional[str]:
        branch = self.get_current_branch()
        if not branch:
            return None
        snapshot = self._take_snapshot()
        if not snapshot:
            return None
        snap_json = json.dumps(snapshot, sort_keys=True)
        snap_hash = self._store_object(snap_json.encode())
        parent = self._get_branch_head(branch)
        ts = time.time()
        cid = self._hash_content(f"{branch}:{ts}:{message}:{snap_hash}".encode())
        db = self._get_db()
        db.execute(
            "INSERT INTO commits (id, branch, parent_id, timestamp, message, author, snapshot) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, branch, parent, ts, message, author, snap_hash)
        )
        db.execute("UPDATE branches SET head_commit = ? WHERE name = ?", (cid, branch))
        db.commit()
        return cid

    def get_commit(self, cid: str) -> Optional[dict]:
        row = self._get_db().execute("SELECT * FROM commits WHERE id = ?", (cid,)).fetchone()
        return dict(row) if row else None

    def get_commit_snapshot(self, cid: str) -> Optional[dict]:
        c = self.get_commit(cid)
        if not c:
            return None
        data = self._read_object(c["snapshot"])
        return json.loads(data.decode()) if data else None

    def get_history(self, branch: str = None, limit: int = 200) -> list:
        db = self._get_db()
        if branch:
            rows = db.execute(
                "SELECT * FROM commits WHERE branch = ? ORDER BY timestamp DESC LIMIT ?",
                (branch, limit)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM commits ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Branches ────────────────────────────────────────────────

    def _create_branch(self, name, from_commit=None, desc=""):
        db = self._get_db()
        db.execute(
            "INSERT OR IGNORE INTO branches (name, head_commit, created_at, description) "
            "VALUES (?, ?, ?, ?)",
            (name, from_commit, time.time(), desc)
        )
        db.commit()

    def create_branch(self, name: str, description: str = "") -> bool:
        if name in [b["name"] for b in self.get_branches()]:
            return False
        head = self._get_branch_head(self.get_current_branch())
        self._create_branch(name, head, description)
        return True

    def get_branches(self) -> list:
        rows = self._get_db().execute("SELECT * FROM branches ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    def get_current_branch(self) -> Optional[str]:
        row = self._get_db().execute(
            "SELECT value FROM current_state WHERE key = 'current_branch'"
        ).fetchone()
        return row["value"] if row else None

    def _set_current_branch(self, name):
        db = self._get_db()
        db.execute(
            "INSERT OR REPLACE INTO current_state (key, value) VALUES ('current_branch', ?)",
            (name,)
        )
        db.commit()

    def _get_branch_head(self, branch) -> Optional[str]:
        row = self._get_db().execute(
            "SELECT head_commit FROM branches WHERE name = ?", (branch,)
        ).fetchone()
        return row["head_commit"] if row else None

    def switch_branch(self, name: str) -> bool:
        if name not in [b["name"] for b in self.get_branches()]:
            return False
        head = self._get_branch_head(name)
        if head:
            snap = self.get_commit_snapshot(head)
            if snap:
                self._restore_snapshot(snap)
        self._set_current_branch(name)
        return True

    def delete_branch(self, name: str) -> bool:
        if name == self.get_current_branch():
            return False
        self._get_db().execute("DELETE FROM branches WHERE name = ?", (name,))
        self._get_db().commit()
        return True

    def merge_branch(self, source: str, message: str = None) -> dict:
        target = self.get_current_branch()
        if not target or source == target:
            return {"success": False, "error": "Invalid merge target"}
        source_head = self._get_branch_head(source)
        target_head = self._get_branch_head(target)
        if not source_head:
            return {"success": False, "error": "Source branch has no commits"}
        src_snap = self.get_commit_snapshot(source_head) or {}
        tgt_snap = self.get_commit_snapshot(target_head) if target_head else {}
        merged = dict(tgt_snap)
        conflicts = []
        for fp, info in src_snap.items():
            if fp not in tgt_snap:
                merged[fp] = info
            elif tgt_snap[fp]["hash"] != info["hash"]:
                conflicts.append(fp)
                merged[fp] = info
        self._restore_snapshot(merged)
        if not message:
            message = f"合并 '{source}' → '{target}'"
        cid = self.commit(message)
        return {"success": True, "commit_id": cid, "conflicts": conflicts, "files_merged": len(src_snap)}

    # ── Diff ────────────────────────────────────────────────────

    def diff_commits(self, cid_a: str, cid_b: str) -> dict:
        sa = self.get_commit_snapshot(cid_a) or {}
        sb = self.get_commit_snapshot(cid_b) or {}
        return {
            "added": {k: v for k, v in sb.items() if k not in sa},
            "removed": {k: v for k, v in sa.items() if k not in sb},
            "modified": {k: {"old": sa[k], "new": sb[k]}
                         for k in sa if k in sb and sa[k]["hash"] != sb[k]["hash"]}
        }

    def diff_file_content(self, ha: str, hb: str) -> list:
        ca, cb = self._read_object(ha), self._read_object(hb)
        if ca is None or cb is None:
            return []
        try:
            la = ca.decode('utf-8', errors='replace').splitlines(keepends=True)
            lb = cb.decode('utf-8', errors='replace').splitlines(keepends=True)
            return list(difflib.unified_diff(la, lb, lineterm=''))
        except Exception:
            return ["[Binary files differ]"]

    # -- Tags ----------------------------------------------------

    def create_tag(self, name, commit_id=None, description="") -> bool:
        if commit_id is None:
            commit_id = self._get_branch_head(self.get_current_branch())
        if not commit_id:
            return False
        try:
            self._get_db().execute(
                "INSERT INTO tags (name, commit_id, created_at, description) VALUES (?, ?, ?, ?)",
                (name, commit_id, time.time(), description)
            )
            self._get_db().commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_tags(self) -> list:
        return [dict(r) for r in self._get_db().execute(
            "SELECT * FROM tags ORDER BY created_at DESC").fetchall()]

    def goto_tag(self, name: str) -> bool:
        row = self._get_db().execute(
            "SELECT commit_id FROM tags WHERE name = ?", (name,)
        ).fetchone()
        if row:
            snap = self.get_commit_snapshot(row["commit_id"])
            if snap:
                self._restore_snapshot(snap)
                return True
        return False

    # ── Annotations ─────────────────────────────────────────────

    def add_annotation(self, commit_id, file_path, content, line_number=None):
        db = self._get_db()
        db.execute(
            "INSERT INTO annotations (commit_id, file_path, line_number, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (commit_id, file_path, line_number, content, time.time())
        )
        db.commit()

    def get_annotations(self, commit_id=None, file_path=None) -> list:
        q, p = "SELECT * FROM annotations WHERE 1=1", []
        if commit_id:
            q += " AND commit_id = ?"; p.append(commit_id)
        if file_path:
            q += " AND file_path = ?"; p.append(file_path)
        return [dict(r) for r in self._get_db().execute(q + " ORDER BY created_at DESC", p).fetchall()]

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> dict:
        db = self._get_db()
        # Fast storage size without rglob
        total = 0
        obj_dir = str(self.objects_dir)
        if os.path.isdir(obj_dir):
            for dirpath, _, filenames in os.walk(obj_dir):
                for fn in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, fn))
                    except OSError:
                        pass
        return {
            "commits": db.execute("SELECT COUNT(*) as c FROM commits").fetchone()["c"],
            "branches": db.execute("SELECT COUNT(*) as c FROM branches").fetchone()["c"],
            "tags": db.execute("SELECT COUNT(*) as c FROM tags").fetchone()["c"],
            "storage_bytes": total,
        }
