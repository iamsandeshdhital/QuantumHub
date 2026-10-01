"""
Project catalogue: the hard implementations in this repository plus external
reference projects.

Built by Sandesh Dhital.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROJECTS_PATH = DATA_DIR / "projects.json"

DIFFICULTIES = ("introductory", "intermediate", "advanced", "research")


class ProjectDataError(ValueError):
    """Raised when the bundled project dataset fails validation."""


@dataclass(frozen=True)
class Project:
    """A single project record."""

    id: str
    title: str
    category: str
    difficulty: str
    implemented: bool
    description: str
    why_hard: str
    correctness_evidence: str | None
    tags: tuple[str, ...]
    module: str | None = None
    test_module: str | None = None
    entry_point: str | None = None
    url: str | None = None
    organisation: str | None = None
    org_type: str | None = None

    @property
    def source(self) -> str:
        """Either the in-repository module path or the external URL."""
        if self.implemented:
            return self.module or "quantumhub"
        return self.url or ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "difficulty": self.difficulty,
            "implemented": self.implemented,
            "description": self.description,
            "why_hard": self.why_hard,
            "correctness_evidence": self.correctness_evidence,
            "tags": list(self.tags),
            "module": self.module,
            "test_module": self.test_module,
            "entry_point": self.entry_point,
            "url": self.url,
            "organisation": self.organisation,
            "org_type": self.org_type,
            "source": self.source,
        }


def _require(record: dict[str, Any], key: str, record_id: str) -> Any:
    if key not in record or record[key] in (None, ""):
        raise ProjectDataError(f"project {record_id}: missing required field {key!r}")
    return record[key]


def parse_project(record: dict[str, Any]) -> Project:
    """Validate and convert a raw dataset record into a :class:`Project`.

    Implemented projects must name a module; external ones must supply a URL.

    Args:
        record: A raw mapping from the JSON dataset.

    Returns:
        The validated :class:`Project`.

    Raises:
        ProjectDataError: If any field is missing, malformed, or inconsistent
            with the ``implemented`` flag.
    """
    record_id = str(record.get("id", "<no id>"))

    for key in ("title", "category", "difficulty", "description", "why_hard"):
        _require(record, key, record_id)

    if record["difficulty"] not in DIFFICULTIES:
        raise ProjectDataError(
            f"project {record_id}: difficulty must be one of {DIFFICULTIES}, "
            f"got {record['difficulty']!r}"
        )

    implemented = record.get("implemented")
    if not isinstance(implemented, bool):
        raise ProjectDataError(f"project {record_id}: 'implemented' must be a boolean")

    tags = record.get("tags")
    if not isinstance(tags, list) or not tags:
        raise ProjectDataError(f"project {record_id}: 'tags' must be a non-empty list")

    if implemented:
        if not record.get("module"):
            raise ProjectDataError(
                f"project {record_id}: an implemented project must name a 'module'"
            )
        if not record.get("correctness_evidence"):
            raise ProjectDataError(
                f"project {record_id}: an implemented project must state "
                "'correctness_evidence'"
            )
    else:
        if not record.get("url") or not str(record["url"]).startswith("http"):
            raise ProjectDataError(
                f"project {record_id}: an external project must supply an http 'url'"
            )

    return Project(
        id=record_id,
        title=str(record["title"]).strip(),
        category=str(record["category"]).strip(),
        difficulty=str(record["difficulty"]),
        implemented=implemented,
        description=str(record["description"]).strip(),
        why_hard=str(record["why_hard"]).strip(),
        correctness_evidence=(
            str(record["correctness_evidence"]).strip()
            if record.get("correctness_evidence")
            else None
        ),
        tags=tuple(str(t).strip().lower() for t in tags),
        module=record.get("module"),
        test_module=record.get("test_module"),
        entry_point=record.get("entry_point"),
        url=record.get("url"),
        organisation=record.get("organisation"),
        org_type=record.get("org_type"),
    )


class ProjectRepository:
    """An in-memory collection of project records."""

    def __init__(self, projects: Sequence[Project]) -> None:
        self._projects: tuple[Project, ...] = tuple(projects)
        self._by_id: dict[str, Project] = {p.id: p for p in self._projects}
        if len(self._by_id) != len(self._projects):
            raise ProjectDataError("duplicate project ids in dataset")

    @classmethod
    def from_path(cls, path: Path | str = PROJECTS_PATH) -> ProjectRepository:
        """Load and validate the project dataset from a JSON file.

        Raises:
            ProjectDataError: If the file is missing, malformed, or invalid.
        """
        path = Path(path)
        if not path.exists():
            raise ProjectDataError(f"dataset not found at {path}")
        try:
            with path.open(encoding="utf-8") as handle:
                document = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ProjectDataError(
                f"dataset at {path} is not valid JSON: {exc}"
            ) from exc

        if "projects" not in document or not isinstance(document["projects"], list):
            raise ProjectDataError(f"dataset at {path} must contain a 'projects' list")

        return cls([parse_project(record) for record in document["projects"]])

    def __len__(self) -> int:
        return len(self._projects)

    def __iter__(self):
        return iter(self._projects)

    def all(self) -> tuple[Project, ...]:
        """Return every project."""
        return self._projects

    def get(self, project_id: str) -> Project | None:
        """Return one project by id, or None."""
        return self._by_id.get(project_id)

    def require(self, project_id: str) -> Project:
        """Return one project by id.

        Raises:
            KeyError: If no project has that id.
        """
        project = self._by_id.get(project_id)
        if project is None:
            raise KeyError(project_id)
        return project

    def implemented(self) -> tuple[Project, ...]:
        """Return only the projects implemented in this repository."""
        return tuple(p for p in self._projects if p.implemented)

    def external(self) -> tuple[Project, ...]:
        """Return only the external reference projects."""
        return tuple(p for p in self._projects if not p.implemented)

    def filter(
        self,
        category: str | None = None,
        difficulty: str | None = None,
        implemented: bool | None = None,
        tag: str | None = None,
        query: str | None = None,
    ) -> tuple[Project, ...]:
        """Return projects matching every supplied criterion.

        Raises:
            ValueError: If ``difficulty`` is not a known level.
        """
        if difficulty is not None and difficulty not in DIFFICULTIES:
            raise ValueError(
                f"difficulty must be one of {DIFFICULTIES}, got {difficulty!r}"
            )

        results = list(self._projects)
        if category is not None:
            needle = category.strip().lower()
            results = [p for p in results if p.category.lower() == needle]
        if difficulty is not None:
            results = [p for p in results if p.difficulty == difficulty]
        if implemented is not None:
            results = [p for p in results if p.implemented is implemented]
        if tag is not None:
            needle = tag.strip().lower()
            results = [p for p in results if needle in p.tags]
        if query:
            needle = query.strip().lower()
            results = [
                p
                for p in results
                if needle in p.title.lower()
                or needle in p.description.lower()
                or needle in " ".join(p.tags)
            ]
        return tuple(results)

    def facets(self) -> dict[str, Any]:
        """Return the distinct values and counts available for filtering."""
        category_counts: dict[str, int] = {}
        difficulty_counts: dict[str, int] = {}
        tag_counts: dict[str, int] = {}

        for project in self._projects:
            category_counts[project.category] = (
                category_counts.get(project.category, 0) + 1
            )
            difficulty_counts[project.difficulty] = (
                difficulty_counts.get(project.difficulty, 0) + 1
            )
            for tag in project.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "category": {"values": sorted(category_counts), "counts": dict(sorted(category_counts.items()))},
            "difficulty": {
                "values": list(DIFFICULTIES),
                "counts": {d: difficulty_counts.get(d, 0) for d in DIFFICULTIES},
            },
            "tags": {"values": sorted(tag_counts), "counts": dict(sorted(tag_counts.items()))},
            "implemented": {
                "implemented": len(self.implemented()),
                "external": len(self.external()),
            },
        }


_DEFAULT_REPOSITORY: ProjectRepository | None = None


def get_repository(reload: bool = False) -> ProjectRepository:
    """Return the process-wide project repository, loading it on first use.

    Args:
        reload: Force a reload from disk, which is used by the tests.

    Returns:
        The shared repository.
    """
    global _DEFAULT_REPOSITORY
    if _DEFAULT_REPOSITORY is None or reload:
        _DEFAULT_REPOSITORY = ProjectRepository.from_path()
    return _DEFAULT_REPOSITORY
