"""
Cross-dataset analytics: distribution of papers by organisation type, year,
difficulty, algorithm family and hardware platform, plus links between papers
and the implementations in this repository.

Built by Sandesh Dhital.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quantumhub.papers import Paper, PaperRepository
from quantumhub.projects import Project, ProjectRepository

DIFFICULTY_ORDER = ("introductory", "intermediate", "advanced", "research")


def _tally(values: Sequence[str]) -> dict[str, int]:
    """Count occurrences of each value, sorted by descending count then name."""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return {
        key: counts[key]
        for key in sorted(counts, key=lambda k: (-counts[k], k))
    }


def paper_distribution(papers: Sequence[Paper]) -> dict[str, Any]:
    """Return the distribution of papers across every facet.

    Args:
        papers: The papers to summarise.

    Returns:
        A dict of facet name to a value-ordered count mapping, plus per-year
        and per-organisation-type totals.
    """
    by_year = _tally([str(p.year) for p in papers])

    return {
        "total": len(papers),
        "by_org_type": _tally([p.org_type for p in papers]),
        "by_difficulty": {
            level: sum(1 for p in papers if p.difficulty == level)
            for level in DIFFICULTY_ORDER
        },
        "by_algorithm_family": _tally([p.algorithm_family for p in papers]),
        "by_hardware_platform": _tally([p.hardware_platform for p in papers]),
        "by_venue": _tally([p.venue for p in papers]),
        "by_year": {year: by_year[year] for year in sorted(by_year)},
        "by_organisation": _tally([p.organisation for p in papers]),
    }


def project_distribution(projects: Sequence[Project]) -> dict[str, Any]:
    """Return the distribution of projects across every facet.

    Args:
        projects: The projects to summarise.

    Returns:
        A dict of facet name to a value-ordered count mapping.
    """
    return {
        "total": len(projects),
        "implemented": sum(1 for p in projects if p.implemented),
        "external": sum(1 for p in projects if not p.implemented),
        "by_category": _tally([p.category for p in projects]),
        "by_difficulty": {
            level: sum(1 for p in projects if p.difficulty == level)
            for level in DIFFICULTY_ORDER
        },
    }


def organisation_leaderboard(
    papers: Sequence[Paper], limit: int = 10
) -> list[dict[str, Any]]:
    """Return the organisations with the most papers.

    Args:
        papers: The papers to summarise.
        limit: Maximum number of entries.

    Returns:
        A list of ``{organisation, org_type, papers}`` dicts, largest first.

    Raises:
        ValueError: If ``limit`` is not positive.
    """
    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    tally: dict[str, dict[str, Any]] = {}
    for paper in papers:
        entry = tally.setdefault(
            paper.organisation,
            {"organisation": paper.organisation, "org_type": paper.org_type, "papers": 0},
        )
        entry["papers"] += 1

    ordered = sorted(
        tally.values(), key=lambda e: (-e["papers"], e["organisation"])
    )
    return ordered[:limit]


def tag_leaderboard(papers: Sequence[Paper], limit: int = 15) -> list[dict[str, Any]]:
    """Return the most frequently used tags.

    Args:
        papers: The papers to summarise.
        limit: Maximum number of entries.

    Returns:
        A list of ``{tag, count}`` dicts, most frequent first.

    Raises:
        ValueError: If ``limit`` is not positive.
    """
    if limit <= 0:
        raise ValueError("limit must be a positive integer")

    counts: dict[str, int] = {}
    for paper in papers:
        for tag in paper.tags:
            counts[tag] = counts.get(tag, 0) + 1

    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"tag": tag, "count": count} for tag, count in ordered[:limit]]


def year_span(papers: Sequence[Paper]) -> dict[str, int]:
    """Return the earliest and latest publication year present.

    Raises:
        ValueError: If no papers are supplied.
    """
    if not papers:
        raise ValueError("cannot compute a year span for an empty paper set")
    years = [p.year for p in papers]
    return {"min": min(years), "max": max(years), "count": len(set(years))}


def coverage(
    papers_repo: PaperRepository, projects_repo: ProjectRepository
) -> dict[str, Any]:
    """Summarise what the repository covers across both datasets.

    Args:
        papers_repo: The paper repository.
        projects_repo: The project repository.

    Returns:
        A combined summary dict.
    """
    papers = papers_repo.all()
    projects = projects_repo.all()
    return {
        "papers": paper_distribution(papers),
        "projects": project_distribution(projects),
        "organisations": organisation_leaderboard(papers, limit=25),
        "tags": tag_leaderboard(papers, limit=25),
        "year_span": year_span(papers),
        "paper_org_types": sorted({p.org_type for p in papers}),
        "project_org_types": sorted(
            {p.org_type for p in projects if p.org_type}
        ),
    }
