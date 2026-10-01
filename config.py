"""
Configuration management for QuantumHub.

Settings are read from the environment with conservative defaults so the project
runs with no setup. A ``.env`` file is honoured if present.

Built by Sandesh Dhital.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> dict[str, str]:
    """Minimal ``.env`` reader. Missing files are ignored."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("\"'")
    return values


_ENV_FILE_VALUES = _load_dotenv(BASE_DIR / ".env")


def get_setting(key: str, default: Any = None) -> Any:
    """Return an environment setting, falling back to ``.env`` then ``default``."""
    if key in os.environ:
        return os.environ[key]
    return _ENV_FILE_VALUES.get(key, default)


def get_int(key: str, default: int) -> int:
    """Return an integer setting, ignoring unparseable values."""
    raw = get_setting(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def get_bool(key: str, default: bool = False) -> bool:
    """Return a boolean setting, accepting common truthy strings."""
    raw = get_setting(key)
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    """Runtime configuration for the application."""

    secret_key: str = field(
        default_factory=lambda: get_setting("SECRET_KEY", "quantumhub-dev-secret")
    )
    host: str = field(default_factory=lambda: get_setting("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: get_int("PORT", 5000))
    debug: bool = field(default_factory=lambda: get_bool("DEBUG", False))
    testing: bool = field(default_factory=lambda: get_bool("TESTING", False))
    json_sort_keys: bool = field(
        default_factory=lambda: get_bool("JSON_SORT_KEYS", False)
    )
    page_size: int = field(default_factory=lambda: get_int("PAGE_SIZE", 10))
    max_page_size: int = field(default_factory=lambda: get_int("MAX_PAGE_SIZE", 100))
    max_search_results: int = field(
        default_factory=lambda: get_int("MAX_SEARCH_RESULTS", 50)
    )
    papers_path: Path = field(
        default_factory=lambda: Path(
            get_setting("PAPERS_PATH", str(BASE_DIR / "data" / "papers.json"))
        )
    )
    projects_path: Path = field(
        default_factory=lambda: Path(
            get_setting("PROJECTS_PATH", str(BASE_DIR / "data" / "projects.json"))
        )
    )
    templates_folder: str = field(default_factory=lambda: "templates")
    static_folder: str = field(default_factory=lambda: "static")

    def as_flask_config(self) -> dict[str, Any]:
        """Return the subset of settings Flask expects in ``app.config``."""
        return {
            "SECRET_KEY": self.secret_key,
            "DEBUG": self.debug,
            "TESTING": self.testing,
            "JSON_SORT_KEYS": self.json_sort_keys,
            "PAGE_SIZE": self.page_size,
            "MAX_PAGE_SIZE": self.max_page_size,
            "MAX_SEARCH_RESULTS": self.max_search_results,
        }


#: The configuration used when the app is created without an explicit one.
config = Config()
