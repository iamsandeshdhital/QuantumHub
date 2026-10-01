"""
Paper repository: loading, validation, filtering and faceted search.

This module owns the paper dataset. It validates the data on load so that a
malformed record fails loudly at import time rather than surfacing as a confusing
error deep inside a request handler.

Built by Sandesh Dhital.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PAPERS_PATH = DATA_DIR / "papers.json"

ORG_TYPES = ("institution", "company", "independent")
DIFFICULTIES = ("introductory", "intermediate", "advanced", "research")

#: Matches a name made only of single-letter initials ending in "S.", which is
#: the signature of a placeholder that was never replaced with a real name.
_PLACEHOLDER_AUTHOR = re.compile(r"^(?:[A-Z]\.\s*)+(?:S\.\s*)+$")

#: A DOI is "10." followed by a registrant and a suffix.
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")

#: An arXiv identifier, with or without a version suffix.
_ARXIV_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$|^[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?$")


class DatasetError(ValueError):
    """Raised when the bundled dataset fails validation."""


@dataclass(frozen=True)
class Paper:
    """A single bibliographic record."""

    id: str
    title: str
    authors: tuple[str, ...]
    organisation: str
    org_type: str
    year: int
    venue: str
    doi: str | None
    arxiv: str | None
    abstract: str
    tags: tuple[str, ...]
    difficulty: str
    algorithm_family: str
    hardware_platform: str
    authors_truncated: bool = False

    @property
    def link(self) -> str:
        """Canonical external link, preferring the DOI."""
        if self.doi:
            return f"https://doi.org/{self.doi}"
        if self.arxiv:
            return f"https://arxiv.org/abs/{self.arxiv}"
        return ""

    @property
    def author_summary(self) -> str:
        """Authors joined for display, truncated sensibly for long lists."""
        if len(self.authors) <= 4:
            return ", ".join(self.authors)
        return f"{self.authors[0]} et al. ({len(self.authors)} authors)"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "id": self.id,
            "title": self.title,
            "authors": list(self.authors),
            "author_summary": self.author_summary,
            "authors_truncated": self.authors_truncated,
            "organisation": self.organisation,
            "org_type": self.org_type,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "arxiv": self.arxiv,
            "abstract": self.abstract,
            "tags": list(self.tags),
            "difficulty": self.difficulty,
            "algorithm_family": self.algorithm_family,
            "hardware_platform": self.hardware_platform,
            "link": self.link,
        }


def _require(record: dict[str, Any], key: str, record_id: str) -> Any:
    if key not in record or record[key] in (None, ""):
        raise DatasetError(f"paper {record_id}: missing required field {key!r}")
    return record[key]


def parse_paper(record: dict[str, Any]) -> Paper:
    """Validate and convert a raw dataset record into a :class:`Paper`.

    Args:
        record: A raw mapping from the JSON dataset.

    Returns:
        The validated :class:`Paper`.

    Raises:
        DatasetError: If any field is missing or malformed.
    """
    record_id = str(record.get("id", "<no id>"))

    for key in ("title", "organisation", "org_type", "venue", "abstract",
                "difficulty", "algorithm_family", "hardware_platform"):
        _require(record, key, record_id)

    authors = record.get("authors")
    if not isinstance(authors, list) or not authors:
        raise DatasetError(f"paper {record_id}: 'authors' must be a non-empty list")
    for name in authors:
        if not isinstance(name, str) or not name.strip():
            raise DatasetError(f"paper {record_id}: author names must be non-empty strings")
        if _PLACEHOLDER_AUTHOR.match(name.strip()):
            raise DatasetError(
                f"paper {record_id}: author {name!r} looks like an unfilled placeholder"
            )

    tags = record.get("tags")
    if not isinstance(tags, list) or not tags:
        raise DatasetError(f"paper {record_id}: 'tags' must be a non-empty list")

    year = record.get("year")
    if not isinstance(year, int) or not 1900 <= year <= 2100:
        raise DatasetError(f"paper {record_id}: 'year' must be an integer in [1900, 2100]")

    if record["org_type"] not in ORG_TYPES:
        raise DatasetError(
            f"paper {record_id}: org_type must be one of {ORG_TYPES}, got {record['org_type']!r}"
        )
    if record["difficulty"] not in DIFFICULTIES:
        raise DatasetError(
            f"paper {record_id}: difficulty must be one of {DIFFICULTIES}, "
            f"got {record['difficulty']!r}"
        )

    doi = record.get("doi")
    if doi is not None and not _DOI_RE.match(str(doi)):
        raise DatasetError(f"paper {record_id}: malformed DOI {doi!r}")

    arxiv = record.get("arxiv")
    if arxiv is not None and not _ARXIV_RE.match(str(arxiv)):
        raise DatasetError(f"paper {record_id}: malformed arXiv id {arxiv!r}")

    if doi is None and arxiv is None:
        raise DatasetError(
            f"paper {record_id}: at least one of 'doi' or 'arxiv' must be present"
        )

    return Paper(
        id=record_id,
        title=str(record["title"]).strip(),
        authors=tuple(str(a).strip() for a in authors),
        organisation=str(record["organisation"]).strip(),
        org_type=str(record["org_type"]),
        year=year,
        venue=str(record["venue"]).strip(),
        doi=str(doi) if doi else None,
        arxiv=str(arxiv) if arxiv else None,
        abstract=str(record["abstract"]).strip(),
        tags=tuple(str(t).strip().lower() for t in tags),
        difficulty=str(record["difficulty"]),
        algorithm_family=str(record["algorithm_family"]).strip(),
        hardware_platform=str(record["hardware_platform"]).strip(),
        authors_truncated=bool(record.get("authors_truncated", False)),
    )


class PaperRepository:
    """An in-memory collection of papers with filtering and faceting."""

    def __init__(self, papers: Sequence[Paper]) -> None:
        self._papers: tuple[Paper, ...] = tuple(papers)
        self._by_id: dict[str, Paper] = {p.id: p for p in self._papers}
        if len(self._by_id) != len(self._papers):
            raise DatasetError("duplicate paper ids in dataset")

    # -- construction ------------------------------------------------------

    @classmethod
    def from_path(cls, path: Path | str = PAPERS_PATH) -> PaperRepository:
        """Load and validate the dataset from a JSON file.

        Args:
            path: Path to the dataset file.

        Returns:
            A validated repository.

        Raises:
            DatasetError: If the file is missing, malformed, or fails validation.
        """
        path = Path(path)
        if not path.exists():
            raise DatasetError(f"dataset not found at {path}")
        try:
            with path.open(encoding="utf-8") as handle:
                document = json.load(handle)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"dataset at {path} is not valid JSON: {exc}") from exc

        if "papers" not in document or not isinstance(document["papers"], list):
            raise DatasetError(f"dataset at {path} must contain a 'papers' list")

        return cls([parse_paper(record) for record in document["papers"]])

    # -- access ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._papers)

    def __iter__(self):
        return iter(self._papers)

    def all(self) -> tuple[Paper, ...]:
        """Return every paper."""
        return self._papers

    def get(self, paper_id: str) -> Paper | None:
        """Return one paper by id, or None."""
        return self._by_id.get(paper_id)

    def require(self, paper_id: str) -> Paper:
        """Return one paper by id.

        Raises:
            KeyError: If no paper has that id.
        """
        paper = self._by_id.get(paper_id)
        if paper is None:
            raise KeyError(paper_id)
        return paper

    # -- filtering ---------------------------------------------------------

    def filter(
        self,
        query: str | None = None,
        org_type: str | None = None,
        difficulty: str | None = None,
        algorithm_family: str | None = None,
        hardware_platform: str | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        tag: str | None = None,
        organisation: str | None = None,
    ) -> tuple[Paper, ...]:
        """Return papers matching every supplied criterion.

        All criteria are optional; supplying none returns the full collection.
        Text matching is case-insensitive substring matching.

        Args:
            query: Free-text query over title, abstract, authors and tags.
            org_type: Restrict to ``institution``, ``company`` or ``independent``.
            difficulty: Restrict to a single difficulty level.
            algorithm_family: Restrict to a single algorithm family.
            hardware_platform: Restrict to a single hardware platform.
            year_min: Inclusive lower bound on publication year.
            year_max: Inclusive upper bound on publication year.
            tag: Restrict to papers carrying this tag.
            organisation: Case-insensitive substring match on the organisation.

        Returns:
            The matching papers, in dataset order.

        Raises:
            ValueError: If a categorical filter has an unknown value.
        """
        if org_type is not None and org_type not in ORG_TYPES:
            raise ValueError(f"org_type must be one of {ORG_TYPES}, got {org_type!r}")
        if difficulty is not None and difficulty not in DIFFICULTIES:
            raise ValueError(
                f"difficulty must be one of {DIFFICULTIES}, got {difficulty!r}"
            )

        results = list(self._papers)

        if org_type is not None:
            results = [p for p in results if p.org_type == org_type]
        if difficulty is not None:
            results = [p for p in results if p.difficulty == difficulty]
        if algorithm_family is not None:
            needle = algorithm_family.strip().lower()
            results = [p for p in results if p.algorithm_family.lower() == needle]
        if hardware_platform is not None:
            needle = hardware_platform.strip().lower()
            results = [p for p in results if p.hardware_platform.lower() == needle]
        if year_min is not None:
            results = [p for p in results if p.year >= year_min]
        if year_max is not None:
            results = [p for p in results if p.year <= year_max]
        if tag is not None:
            needle = tag.strip().lower()
            results = [p for p in results if needle in p.tags]
        if organisation is not None:
            needle = organisation.strip().lower()
            results = [p for p in results if needle in p.organisation.lower()]
        if query:
            results = [p for p in results if _matches_query(p, query)]

        return tuple(results)

    def search(self, query: str, limit: int | None = None) -> tuple[Paper, ...]:
        """Rank papers against a free-text query.

        Scoring is a simple weighted sum over the fields: a title match counts
        more than an abstract match, which counts more than a tag or author
        match. Ties are broken by year, newest first, then by id for stability.

        Args:
            query: The query string.
            limit: Maximum number of results to return.

        Returns:
            Ranked results.

        Raises:
            ValueError: If ``limit`` is not positive.
        """
        if limit is not None and limit <= 0:
            raise ValueError("limit must be a positive integer")

        terms = [t for t in _tokenise(query) if t]
        if not terms:
            return ()

        scored: list[tuple[float, int, str, Paper]] = []
        for paper in self._papers:
            score = _score_paper(paper, terms)
            if score > 0:
                scored.append((score, -paper.year, paper.id, paper))

        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        results = [item[3] for item in scored]
        return tuple(results[:limit]) if limit else tuple(results)

    # -- facets ------------------------------------------------------------

    def facets(self) -> dict[str, Any]:
        """Return the distinct values and counts available for filtering."""
        org_counts: dict[str, int] = {}
        difficulty_counts: dict[str, int] = {}
        family_counts: dict[str, int] = {}
        platform_counts: dict[str, int] = {}
        tag_counts: dict[str, int] = {}
        org_by_type: dict[str, set[str]] = {t: set() for t in ORG_TYPES}
        year_min: int | None = None
        year_max: int | None = None

        for paper in self._papers:
            org_counts[paper.organisation] = org_counts.get(paper.organisation, 0) + 1
            difficulty_counts[paper.difficulty] = (
                difficulty_counts.get(paper.difficulty, 0) + 1
            )
            family_counts[paper.algorithm_family] = (
                family_counts.get(paper.algorithm_family, 0) + 1
            )
            platform_counts[paper.hardware_platform] = (
                platform_counts.get(paper.hardware_platform, 0) + 1
            )
            org_by_type[paper.org_type].add(paper.organisation)
            for tag in paper.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            year_min = paper.year if year_min is None else min(year_min, paper.year)
            year_max = paper.year if year_max is None else max(year_max, paper.year)

        return {
            "org_type": {
                "values": list(ORG_TYPES),
                "counts": {t: sum(1 for p in self._papers if p.org_type == t) for t in ORG_TYPES},
            },
            "difficulty": {
                "values": list(DIFFICULTIES),
                "counts": {
                    d: sum(1 for p in self._papers if p.difficulty == d) for d in DIFFICULTIES
                },
            },
            "algorithm_family": {
                "values": sorted(family_counts),
                "counts": dict(sorted(family_counts.items())),
            },
            "hardware_platform": {
                "values": sorted(platform_counts),
                "counts": dict(sorted(platform_counts.items())),
            },
            "tags": {
                "values": sorted(tag_counts),
                "counts": dict(sorted(tag_counts.items())),
            },
            "organisations": {
                "values": sorted(org_counts),
                "counts": dict(sorted(org_counts.items())),
            },
            "organisations_by_type": {
                t: sorted(v) for t, v in org_by_type.items()
            },
            "year_range": {"min": year_min, "max": year_max},
        }

    def years(self) -> tuple[int, ...]:
        """Return the distinct publication years, ascending."""
        return tuple(sorted({p.year for p in self._papers}))


# --------------------------------------------------------------------------
# Text matching helpers
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenise(text: str) -> list[str]:
    """Lowercase and split text into alphanumeric tokens."""
    return _TOKEN_RE.findall(text.lower())


def _matches_query(paper: Paper, query: str) -> bool:
    """Return True if any query token appears in the paper's text."""
    haystack = " ".join(
        [
            paper.title,
            paper.abstract,
            paper.organisation,
            paper.venue,
            " ".join(paper.authors),
            " ".join(paper.tags),
        ]
    ).lower()
    return any(token in haystack for token in _tokenise(query))


def _score_paper(paper: Paper, terms: Sequence[str]) -> float:
    """Score a paper against pre-tokenised query terms."""
    title = paper.title.lower()
    abstract = paper.abstract.lower()
    authors = " ".join(paper.authors).lower()
    tags = " ".join(paper.tags)
    org = paper.organisation.lower()

    score = 0.0
    for term in terms:
        if term in title:
            score += 10.0
        if term in tags:
            score += 4.0
        if term in authors:
            score += 3.0
        if term in org:
            score += 2.0
        if term in abstract:
            score += 1.0
    return score


_DEFAULT_REPOSITORY: PaperRepository | None = None


def get_repository(reload: bool = False) -> PaperRepository:
    """Return the process-wide paper repository, loading it on first use.

    Args:
        reload: Force a reload from disk, which is used by the tests.

    Returns:
        The shared repository.
    """
    global _DEFAULT_REPOSITORY
    if _DEFAULT_REPOSITORY is None or reload:
        _DEFAULT_REPOSITORY = PaperRepository.from_path()
    return _DEFAULT_REPOSITORY
