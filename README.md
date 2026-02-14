# ◈ Quelldex

**Source & Data Organization Engine** — A lightweight desktop tool for file organization, version control, data visualization, and project planning.

> *Quelldex = German "Quell" (source) + "dex" (index)*

<p align="center">
  <img src="docs/screenshot-dark.png" alt="Quelldex Dark Theme" width="800">
</p>

---

## Why Quelldex?

Most file managers don't understand your code. Most IDEs don't help you organize data. Quelldex bridges the gap — it automatically classifies your files into 9 categories, provides a built-in version control system (no Git required), lets you visualize CSV/JSON data with zero config, and tracks your project tasks on a Kanban board scoped to branches.

**5,300 lines of Python. Single dependency (`PySide6`). Runs anywhere.**

---

## Features

### Smart File Browser
- **9-category auto-classification** — Source Code · Data · Docs · Config · Scripts · Styles · Images · Output · Other
- **3 view modes** — Category groups · Directory tree · Flat list
- **Real-time search** with debounced filtering
- **Smart Shelf** — Stage batch file operations (move, copy, rename), preview before executing
- **Pinned files & recent files** — Quick access to what matters

### Built-in Version Control
A complete VCS engine with no external dependencies — ideal for projects that don't use Git.

- **Snapshot commits** with SHA-256 content-addressed object store
- **Branching** — Create, switch, merge, delete branches
- **Tagging** — Mark important versions for instant rollback
- **Diff viewer** — Side-by-side line-level comparison with add/delete/change highlighting
- **Change tracking** — Real-time detection of new, modified, and deleted files
- **Merge conflict detection** — Automatic conflict identification during branch merges

### Planner (Kanban Board)
A project task manager built directly into the file organizer — no context switching.

- **3-column Kanban** — To Do → In Progress → Done
- **Branch-scoped tasks** — Tasks can be shared across all branches or bound to a specific branch
- **Scope filtering** — View all tasks, shared-only, or branch-specific
- **Task merging** — Copy tasks from one branch to another (smart deduplication by title)
- **4 priority levels** — Critical (red) · High (gold) · Medium (blue) · Low (gray)
- **Rich task cards** — Title, description, tags, due date, priority indicator
- **Persistent storage** — Tasks saved per-project in `.quelldex/project.json`

### Data Visualization
Zero-config charts for CSV, TSV, and JSON files — powered by QPainter, no matplotlib needed.

- **6 chart types** — Histogram · Line · Bar · Scatter · Correlation matrix · Multi-file overlay
- **Multi-file comparison** — Load multiple data files, plot on the same axes
- **Full statistics** — Mean, median, std dev, variance, skewness, Q1/Q3, top frequencies
- **Cross-file statistics** — Global stats across data sources for the same column

### File Comparison
- **File vs File** — Side-by-side diff of any two files
- **File vs Version** — Compare current working file against any VCS commit
- **Syntax-highlighted diff** — Green (added), red (deleted), amber (changed)

### Multi-Theme System
- **3 built-in themes** — Dark · Light · Midnight
- **Runtime switching** — Change theme without restart, preference persisted
- **Custom arrow indicators** — Branch arrows generated as PNGs per theme color

### IDE & Tool Integration
- **Auto-detection** — VS Code, Cursor, Sublime Text, Vim
- **Smart double-click** — Code files open in IDE, data files open in Data Viz
- **External tool protocol** — Register custom tools via JSON config (MarkVue, H5Lens, etc.)

---

## Quick Start

```bash
# Install dependency
pip install PySide6

# Run
python main.py
```

### Build Standalone Executable (Windows)

```bash
pip install pyinstaller
pyinstaller quelldex.spec
# Output: dist/Quelldex.exe
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open project folder |
| `Ctrl+S` | Quick VCS commit |
| `Ctrl+1` | Files view |
| `Ctrl+2` | Version Control view |
| `Ctrl+3` | Planner view |
| `Ctrl+4` | Data Viz view |
| `Ctrl+5` | Compare view |
| `Ctrl+6` | Settings view |
| `Ctrl+Tab` | Cycle between open projects |
| `F5` | Force refresh (invalidate cache) |

---

## Project Structure

```
quelldex/
├── main.py                    # Entry point (QApplication + theme init)
├── requirements.txt           # PySide6
├── src/
│   ├── core/
│   │   ├── vcs.py             # Version control engine (SHA-256 object store)
│   │   └── project.py         # Project model, file scanning, planner data
│   ├── ui/
│   │   ├── app.py             # Main window, all views, Kanban board
│   │   ├── theme.py           # 3 theme palettes, QSS generator, arrow PNGs
│   │   └── widgets.py         # QPainter charts, icon factory, loading spinner
│   ├── viz/
│   │   └── data_viewer.py     # CSV/TSV/JSON parser, statistics engine
│   └── integrations/
│       └── bridges.py         # IDE detection, external tool protocol
├── build.bat                  # Windows build script
├── quelldex.spec              # PyInstaller config
└── installer.iss              # Inno Setup installer config
```

---

## What Makes It Different

| Feature | Quelldex | VS Code | File Managers |
|---------|----------|---------|---------------|
| Auto file classification | ✅ 9 categories | ❌ | ❌ |
| Built-in VCS (no Git) | ✅ Full branching | ❌ Needs Git | ❌ |
| Branch-scoped task board | ✅ Kanban + merge | ❌ | ❌ |
| Multi-file data viz | ✅ 6 chart types | ❌ Needs extensions | ❌ |
| Smart Shelf (staged ops) | ✅ Preview → execute | ❌ | ❌ |
| Zero-config, single dep | ✅ PySide6 only | ❌ | Varies |

### Unique innovations:
1. **Branch-scoped Planner** — Tasks tied to VCS branches, with cross-branch merge
2. **Smart Shelf** — Batch file operations staged for review before execution
3. **Multi-file overlay charts** — Compare multiple CSV/JSON datasets on one plot
4. **External tool protocol** — Open JSON API for registering any tool
5. **Lightweight VCS** — SHA-256 content-addressed storage, no Git dependency
6. **Theme-aware PNG arrows** — Branch indicators generated at runtime per theme

---

## Tech Stack

- **Python 3.9+**
- **PySide6 / Qt6** — GUI framework
- **QPainter** — Native chart rendering (no matplotlib)
- **SHA-256** — Content-addressed VCS object store
- **SQLite3** — Metadata caching
- **Pure Python PNG generator** — Branch arrow images via `struct` + `zlib`

---

## Screenshots

> Add screenshots here after first build

| Dark Theme | Light Theme | Midnight Theme |
|------------|-------------|----------------|
| ![Dark](docs/dark.png) | ![Light](docs/light.png) | ![Midnight](docs/midnight.png) |

---

## Contributing

Contributions welcome. Please open an issue first to discuss what you'd like to change.

## License

[MIT](LICENSE)

---

<p align="center">
  <sub>Built with care. Organized by design.</sub>
</p>
