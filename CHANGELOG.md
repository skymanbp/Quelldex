# Changelog

All notable changes to Quelldex are documented here.

## [5.1.0] — 2026-02-14

### Added
- **Planner view** — 3-column Kanban board (To Do / In Progress / Done)
- Branch-scoped tasks — shared or branch-specific with scope filtering
- Task merge across branches with deduplication
- 4 priority levels with color-coded indicators
- Task CRUD with edit dialog (title, description, priority, scope, tags, due date)
- `plan_col` and `task_card` QSS styles for all 3 themes

### Fixed
- Blue selection highlight on tree branch area (QPalette.Highlight → transparent)
- Native Windows connector lines (Fusion style + transparent PNG border-image)
- Branch arrow rendering — runtime PNG generation per theme color
- Keyboard shortcuts updated to Ctrl+1~6 for 6 views

## [5.0.0] — 2026-02-14

### Added
- **Multi-theme system** — Dark, Light, Midnight with runtime switching
- **File comparison view** — File vs File and File vs VCS version
- **Loading spinner** with processEvents batching for large projects
- Theme preference persistence via QSettings

### Changed
- Complete QSS rewrite for 3 theme palettes
- Branch decoration arrows generated as PNG at runtime

## [4.1.0] — 2026-02-14

### Added
- Six-layer performance optimization
  - View caching (build once, refresh data)
  - Batch rendering with processEvents
  - Search debouncing (300ms)
  - Tree item cap (3,000 max)
  - VCS fast scanning (mtime-based skip)
  - File cache validation

## [4.0.0] — 2026-02-14

### Added
- **Multi-project workspace** — Open multiple projects, switch with Ctrl+Tab
- Elegant minimalist UI redesign
- Sidebar navigation with project list
- Project cards with file count and size info

### Changed
- Migrated from tkinter to PySide6/Qt6

## [3.0.0] — 2026-02-14

### Added
- PySide6 GUI framework
- Tokyo Night dark theme
- QPainter native chart rendering

## [2.0.0] — 2026-02-14

### Added
- Version control system with SHA-256 object store
- Branch and tag management
- Smart Shelf for batch file operations
- Data visualization (6 chart types)
- IDE integration and external tool protocol

## [1.0.0] — 2026-02-14

### Added
- Initial release
- 9-category file auto-classification
- File browser with 3 view modes
- Basic tkinter GUI
