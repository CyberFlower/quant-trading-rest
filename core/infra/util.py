from pathlib import Path
from typing import Optional


def find_project_root(start: Optional[Path] = None) -> Path:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for path in (current, *current.parents):
        if (path / ".git").exists():
            return path
    raise RuntimeError("Project root not found (.git missing)")


def get_minute_db_dir(start: Optional[Path] = None) -> Path:
    return find_project_root(start) / "prices_min_db"
