"""Verify the environment and the bundled datasets before running anything else.

Run this first. It is deliberately dependency-light so that a broken install
produces a clear message rather than a traceback from deep inside the app.

Usage:

    python verify_requirements.py

Exits 0 when everything checks out and 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MIN_PYTHON = (3, 10)
REQUIRED_PACKAGES = (("flask", "3.0"), ("numpy", "1.26"))


def check_python() -> bool:
    """Confirm the interpreter is new enough."""
    version = sys.version_info
    if version[:2] < MIN_PYTHON:
        print(
            f"  FAIL  Python {version.major}.{version.minor} is too old; "
            f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required"
        )
        return False
    print(f"  OK    Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_packages() -> bool:
    """Confirm the runtime dependencies are importable and new enough."""
    from importlib import metadata

    ok = True
    for name, minimum in REQUIRED_PACKAGES:
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            print(f"  FAIL  {name} is not installed")
            ok = False
            continue

        def parse(text):
            parts = []
            for chunk in text.split("."):
                digits = "".join(c for c in chunk if c.isdigit())
                parts.append(int(digits) if digits else 0)
            return tuple(parts)

        if parse(installed) < parse(minimum):
            print(f"  FAIL  {name} {installed} is older than the required {minimum}")
            ok = False
        else:
            print(f"  OK    {name} {installed}")
    return ok


def check_layout() -> bool:
    """Confirm the expected files and directories are present."""
    expected = [
        "app.py",
        "config.py",
        "data/papers.json",
        "data/projects.json",
        "quantumhub/__init__.py",
        "quantumhub/algorithms.py",
        "quantumhub/analytics.py",
        "quantumhub/papers.py",
        "quantumhub/projects.py",
        "quantumhub/statevector.py",
        "templates/base.html",
        "static/style.css",
    ]
    ok = True
    for relative in expected:
        if (BASE_DIR / relative).exists():
            print(f"  OK    {relative}")
        else:
            print(f"  FAIL  {relative} is missing")
            ok = False
    return ok


def check_datasets() -> bool:
    """Load and validate both datasets through their real loaders."""
    sys.path.insert(0, str(BASE_DIR))
    ok = True
    try:
        from quantumhub.papers import PaperRepository
        from quantumhub.projects import ProjectRepository
    except Exception as exc:  # pragma: no cover - import failure path
        print(f"  FAIL  could not import the loaders: {exc}")
        return False

    try:
        papers = PaperRepository.from_path(BASE_DIR / "data" / "papers.json")
        print(
            f"  OK    {len(papers)} papers across "
            f"{len({p.organisation for p in papers})} organisations"
        )
    except Exception as exc:
        print(f"  FAIL  paper dataset: {exc}")
        ok = False

    try:
        projects = ProjectRepository.from_path(BASE_DIR / "data" / "projects.json")
        print(
            f"  OK    {len(projects)} projects "
            f"({len(projects.implemented())} implemented, {len(projects.external())} external)"
        )
    except Exception as exc:
        print(f"  FAIL  project dataset: {exc}")
        ok = False

    return ok


def check_app_imports() -> bool:
    """Confirm the Flask application can be constructed."""
    sys.path.insert(0, str(BASE_DIR))
    try:
        import config
        from app import create_app

        application = create_app(config.Config(testing=True))
        routes = len(list(application.url_map.iter_rules()))
        print(f"  OK    application created with {routes} routes")
        return True
    except Exception as exc:
        print(f"  FAIL  could not build the application: {exc}")
        return False


def main() -> int:
    """Run every check and report a summary."""
    print("QuantumHub environment check")
    print("-" * 60)

    checks = (
        ("Python", check_python),
        ("Packages", check_packages),
        ("Layout", check_layout),
        ("Datasets", check_datasets),
        ("Application", check_app_imports),
    )

    results = []
    for name, check in checks:
        print(f"\n[{name}]")
        results.append((name, check()))

    print("\n" + "-" * 60)
    failed = [name for name, passed in results if not passed]
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        print("Run `pip install -r requirements-dev.txt` and try again.")
        return 1

    print(f"All {len(results)} checks passed.")
    print("Start the app with `python app.py`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
