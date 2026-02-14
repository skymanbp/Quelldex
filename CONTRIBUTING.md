# Contributing to Quelldex

Thanks for your interest in contributing!

## Getting Started

```bash
git clone https://github.com/YOUR_USERNAME/quelldex.git
cd quelldex
pip install PySide6
python main.py
```

## Development Guidelines

- **Single dependency**: Only PySide6. Do not add matplotlib, numpy, or other heavy packages.
- **Charts**: Use QPainter for all rendering. No external plotting libraries.
- **Style**: Follow existing code style. Use `_label()`, `_btn()` helpers for UI creation.
- **Themes**: Any new QSS must work across all 3 themes (dark/light/midnight). Test all.
- **Performance**: Tree views must handle 10K+ files without freezing. Use processEvents batching.

## Pull Request Process

1. Fork the repo and create a feature branch
2. Make your changes
3. Test with a project containing 1K+ files
4. Ensure all 3 themes render correctly
5. Submit PR with a clear description

## Reporting Issues

Please include:
- OS and Python version
- Steps to reproduce
- Screenshot if it's a visual bug
- Console output if there's an error

## Code of Conduct

Be respectful. Keep discussions constructive. We're all here to build something useful.
