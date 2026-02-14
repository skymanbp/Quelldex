"""
Quelldex Project v4 — Cached scanning, smart ignore, efficient metadata
"""

import json
import os
import time
from pathlib import Path
from typing import Optional


# -- File Category Definitions ------------------------------------

CATEGORIES = {
    "Source Code": {
        "icon": ">>", "color": "#6580c8",
        "ext": {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
                ".h", ".hpp", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
                ".scala", ".lua", ".r", ".m", ".cs", ".dart", ".vue", ".svelte"}
    },
    "Data": {
        "icon": "<>", "color": "#7fb86a",
        "ext": {".json", ".xml", ".yaml", ".yml", ".csv", ".tsv", ".sql",
                ".db", ".sqlite", ".parquet", ".hdf5", ".h5", ".npy", ".npz",
                ".feather", ".arrow", ".xls", ".xlsx", ".pickle", ".pkl"}
    },
    "Docs": {
        "icon": "==", "color": "#d0a050",
        "ext": {".md", ".txt", ".pdf", ".doc", ".docx", ".rst", ".tex",
                ".html", ".htm", ".rtf", ".odt", ".epub", ".wiki"}
    },
    "Config": {
        "icon": "()", "color": "#9b82cc",
        "ext": {".ini", ".cfg", ".conf", ".env", ".toml", ".properties",
                ".gitignore", ".editorconfig", ".eslintrc", ".prettierrc",
                ".dockerignore", ".babelrc", "Makefile", "Dockerfile",
                ".flake8", ".pylintrc"}
    },
    "Scripts": {
        "icon": "$>", "color": "#d96070",
        "ext": {".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1", ".fish",
                ".awk", ".sed", ".makefile"}
    },
    "Styles": {
        "icon": "##", "color": "#58aec0",
        "ext": {".css", ".scss", ".sass", ".less", ".styl"}
    },
    "Images": {
        "icon": "[]", "color": "#d0a050",
        "ext": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".webp",
                ".ico", ".tiff", ".psd", ".ai", ".eps"}
    },
    "Output": {
        "icon": "->", "color": "#5cb898",
        "ext": {".log", ".out", ".result", ".report", ".tmp", ".bak",
                ".cache", ".map", ".min.js", ".min.css", ".dist"}
    },
}

# Directories to always skip during scanning
IGNORE_DIRS = {
    ".git", ".svn", ".hg", ".quelldex",
    "node_modules", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".next", ".nuxt", "dist", "build", ".cache",
    ".idea", ".vscode", ".vs",
    "vendor", "bower_components",
    "target",        # Rust/Java
    ".gradle",
    "Pods",          # iOS
}

def classify_file(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    name = Path(filepath).name.lower()
    for cat, info in CATEGORIES.items():
        if ext in info["ext"] or name in info["ext"]:
            return cat
    return "Other"


def get_category_info(category: str) -> dict:
    return CATEGORIES.get(category, {"icon": "--", "color": "#555a68", "ext": set()})


def is_data_file(filepath: str) -> bool:
    ext = Path(filepath).suffix.lower()
    return ext in {".csv", ".tsv", ".json", ".xlsx", ".xls"}


def is_code_file(filepath: str) -> bool:
    ext = Path(filepath).suffix.lower()
    return ext in CATEGORIES["Source Code"]["ext"]


# -- Cached File Scanner ------------------------------------------

class _FileCache:
    """Fast file metadata cache with TTL-based invalidation."""

    def __init__(self, ttl: float = 5.0):
        self.ttl = ttl
        self._files: list = []
        self._summary: dict = {}
        self._scan_time: float = 0.0
        self._scan_count: int = 0

    @property
    def is_valid(self) -> bool:
        return self._files and (time.time() - self._scan_time) < self.ttl

    def invalidate(self):
        self._scan_time = 0.0

    def get_files(self) -> list:
        return self._files

    def get_summary(self) -> dict:
        return self._summary

    def update(self, files: list):
        self._files = files
        self._scan_time = time.time()
        self._scan_count += 1
        # Compute summary in same pass
        cats = {}
        total_size = 0
        n_data = 0
        n_code = 0
        for f in files:
            cats[f["category"]] = cats.get(f["category"], 0) + 1
            total_size += f["size"]
            if f["is_data"]:
                n_data += 1
            if f["is_code"]:
                n_code += 1
        self._summary = {
            "total_files": len(files),
            "total_size": total_size,
            "categories": cats,
            "data_files": n_data,
            "code_files": n_code,
        }


def scan_directory(root: Path) -> list:
    """Fast directory scan using os.scandir (3-5x faster than rglob).
    Skips ignored directories and oversized files.
    Returns sorted list of file metadata dicts.
    """
    files = []
    root_str = str(root)
    root_len = len(root_str) + 1  # +1 for separator

    def _scan(dirpath: str):
        try:
            entries = os.scandir(dirpath)
        except PermissionError:
            return
        with entries:
            for entry in entries:
                if entry.name.startswith(".") and entry.name in IGNORE_DIRS:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in IGNORE_DIRS:
                        continue
                    _scan(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    rel = entry.path[root_len:].replace("\\", "/")
                    cat = classify_file(rel)
                    files.append({
                        "path": rel,
                        "name": entry.name,
                        "category": cat,
                        "size": st.st_size,
                        "mtime": st.st_mtime,
                        "is_data": is_data_file(rel),
                        "is_code": is_code_file(rel),
                    })

    _scan(root_str)
    files.sort(key=lambda x: (x["category"], x["path"]))
    return files


# -- Project Manager ----------------------------------------------

class Project:
    """Manages project metadata, categories, shelf, and templates."""

    def __init__(self, project_path: str):
        self.path = Path(project_path)
        self.config_path = self.path / ".quelldex" / "project.json"
        self.data = self._load()
        self._cache = _FileCache(ttl=5.0)

    def _load(self) -> dict:
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {
            "name": self.path.name,
            "created_at": time.time(),
            "custom_categories": {},
            "shelf": [],
            "templates": [],
            "ide_path": "",
            "integrations": {},
            "pinned_files": [],
            "recent_files": [],
            "planner": {"tasks": []},
        }

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    @property
    def name(self) -> str:
        return self.data.get("name", self.path.name)

    @name.setter
    def name(self, v):
        self.data["name"] = v

    # -- File Listing (cached) ------------------------------------

    def get_all_files(self) -> list:
        """Get all files categorized. Uses cache if still valid."""
        if not self._cache.is_valid:
            files = scan_directory(self.path)
            self._cache.update(files)
        return self._cache.get_files()

    def get_all_files_nocache(self) -> list:
        """Force a fresh scan (used by background thread)."""
        files = scan_directory(self.path)
        self._cache.update(files)
        return files

    def invalidate_cache(self):
        """Force next get_all_files to rescan."""
        self._cache.invalidate()

    def get_files_by_category(self) -> dict:
        groups = {}
        for f in self.get_all_files():
            groups.setdefault(f["category"], []).append(f)
        return groups

    def get_data_files(self) -> list:
        return [f for f in self.get_all_files() if f["is_data"]]

    # -- Summary (cached) -----------------------------------------

    def get_summary(self) -> dict:
        """Summary reuses cache - no extra scan."""
        if not self._cache.is_valid:
            self.get_all_files()  # populate cache
        return self._cache.get_summary()

    # -- Smart Shelf ----------------------------------------------

    def add_to_shelf(self, action: str, source: str, dest: str = ""):
        self.data["shelf"].append({
            "action": action, "source": source,
            "dest": dest, "added_at": time.time()
        })

    def clear_shelf(self):
        self.data["shelf"] = []

    def execute_shelf(self) -> list:
        import shutil
        results = []
        for op in self.data["shelf"]:
            try:
                src = self.path / op["source"]
                if op["action"] == "delete":
                    src.unlink()
                    results.append(("ok", f"Deleted: {op['source']}"))
                elif op["action"] == "move" and op["dest"]:
                    dst = self.path / op["dest"]
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                    results.append(("ok", f"Moved: {op['source']} -> {op['dest']}"))
                elif op["action"] == "copy" and op["dest"]:
                    dst = self.path / op["dest"]
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dst))
                    results.append(("ok", f"Copied: {op['source']} -> {op['dest']}"))
            except Exception as e:
                results.append(("error", f"Failed: {op['source']} - {e}"))
        self.data["shelf"] = []
        self._cache.invalidate()  # files changed
        return results

    # -- Recent & Pinned ------------------------------------------

    def add_recent(self, filepath: str):
        r = self.data.get("recent_files", [])
        if filepath in r:
            r.remove(filepath)
        r.insert(0, filepath)
        self.data["recent_files"] = r[:20]

    def toggle_pin(self, filepath: str):
        p = self.data.get("pinned_files", [])
        if filepath in p:
            p.remove(filepath)
        else:
            p.append(filepath)
        self.data["pinned_files"] = p

    # -- IDE Config -----------------------------------------------

    def set_ide_path(self, path: str):
        self.data["ide_path"] = path

    def get_ide_path(self) -> str:
        return self.data.get("ide_path", "")

    # -- Integration Config ---------------------------------------

    def set_integration(self, name: str, config: dict):
        if "integrations" not in self.data:
            self.data["integrations"] = {}
        self.data["integrations"][name] = config

    def get_integration(self, name: str) -> dict:
        return self.data.get("integrations", {}).get(name, {})

    # -- Planner --------------------------------------------------

    def _ensure_planner(self):
        if "planner" not in self.data:
            self.data["planner"] = {"tasks": []}

    def get_tasks(self, scope: str = None, status: str = None) -> list:
        """Get tasks filtered by scope and/or status.
        scope='*' = shared, scope='branchname' = branch-specific,
        scope=None = return all."""
        self._ensure_planner()
        tasks = self.data["planner"]["tasks"]
        if scope is not None:
            tasks = [t for t in tasks if t.get("scope") in (scope, "*")]
        if status is not None:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    def add_task(self, title: str, scope: str = "*", priority: str = "medium",
                 description: str = "", tags: list = None, due_date: str = "") -> dict:
        self._ensure_planner()
        import uuid
        task = {
            "id": uuid.uuid4().hex[:12],
            "title": title,
            "description": description,
            "status": "todo",
            "priority": priority,
            "scope": scope,
            "tags": tags or [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "due_date": due_date,
        }
        self.data["planner"]["tasks"].append(task)
        self.save()
        return task

    def update_task(self, task_id: str, **kwargs):
        self._ensure_planner()
        for t in self.data["planner"]["tasks"]:
            if t["id"] == task_id:
                for k, v in kwargs.items():
                    if k in t:
                        t[k] = v
                t["updated_at"] = time.time()
                self.save()
                return t
        return None

    def delete_task(self, task_id: str):
        self._ensure_planner()
        self.data["planner"]["tasks"] = [
            t for t in self.data["planner"]["tasks"] if t["id"] != task_id
        ]
        self.save()

    def merge_tasks_from_branch(self, source_branch: str, target_branch: str):
        """Copy branch-specific tasks from source to target (skip duplicates by title)."""
        self._ensure_planner()
        source_tasks = [t for t in self.data["planner"]["tasks"]
                        if t.get("scope") == source_branch]
        target_titles = {t["title"] for t in self.data["planner"]["tasks"]
                         if t.get("scope") in (target_branch, "*")}
        import uuid
        merged = 0
        for st in source_tasks:
            if st["title"] not in target_titles:
                new_task = dict(st)
                new_task["id"] = uuid.uuid4().hex[:12]
                new_task["scope"] = target_branch
                new_task["updated_at"] = time.time()
                self.data["planner"]["tasks"].append(new_task)
                merged += 1
        self.save()
        return merged
