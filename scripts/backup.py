#!/usr/bin/env python3
"""Back up all portfolio databases using SQLite's online backup API.

Safe to run while the server is live (WAL mode). Each DB gets a
timestamped copy in backups/. Keeps the 30 most recent per portfolio.

Usage:
    uv run python scripts/backup.py
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
PORTFOLIOS_FILE = ROOT / "portfolios.json"
BACKUP_DIR = ROOT / "backups"
KEEP = 30


def _load_portfolios() -> list[dict]:
    if not PORTFOLIOS_FILE.exists():
        return []
    with open(PORTFOLIOS_FILE) as f:
        cfg = json.load(f)
    return cfg.get("portfolios", [])


def _backup_db(src: Path, dest: Path) -> None:
    with sqlite3.connect(src) as src_conn:
        with sqlite3.connect(dest) as dst_conn:
            src_conn.backup(dst_conn)


def _prune(backup_dir: Path, stem: str) -> None:
    """Delete oldest backups beyond KEEP for a given portfolio stem."""
    pattern = re.compile(rf"^\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}_{re.escape(stem)}\.db$")
    existing = sorted(
        [f for f in backup_dir.iterdir() if pattern.match(f.name)],
        key=lambda f: f.name,
    )
    for old in existing[:-KEEP]:
        old.unlink(missing_ok=True)


def main() -> None:
    portfolios = _load_portfolios()
    if not portfolios:
        print("backup: no portfolios found — nothing to back up")
        return

    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    errors = []

    for entry in portfolios:
        rel = entry.get("path", "")
        src = Path(rel) if Path(rel).is_absolute() else ROOT / rel
        if not src.exists():
            print(f"backup: skip {src.name} (not found)")
            continue

        stem = src.stem
        dest = BACKUP_DIR / f"{timestamp}_{stem}.db"
        try:
            _backup_db(src, dest)
            print(f"backup: {src.name} → backups/{dest.name}")
            _prune(BACKUP_DIR, stem)
        except Exception as exc:
            msg = f"backup: ERROR backing up {src.name}: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
