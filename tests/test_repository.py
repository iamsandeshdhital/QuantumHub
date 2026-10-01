"""Tests for the paper and project repositories and the dataset validation."""

import json

import pytest

from quantumhub import analytics
from quantumhub.papers import (
    DIFFICULTIES,
    ORG_TYPES,
    DatasetError,
    get_repository,
    parse_paper,
)
from quantumhub.projects import (
    ProjectDataError,
    ProjectRepository,
    parse_project,
)


@pytest.fixture(scope="module")
def papers():
    return get_repository(reload=True)


@pytest.fixture(scope="module")
def projects():
    return ProjectRepository.from_path()


# --------------------------------------------------------------------------
# The bundled datasets must load and validate
# --------------------------------------------------------------------------


def test_paper_dataset_loads(papers):
    assert len(papers) > 0


def test_paper_ids_are_unique(papers):
    ids = [p.id for p in papers]
    assert len(set(ids)) == len(ids)


def test_every_org_type_is_represented(papers):
    present = {p.org_type for p in papers}
    assert present == set(ORG_TYPES), f"missing org types: {set(ORG_TYPES) - present}"


def test_every_paper_has_an_external_link(papers):
    for paper in papers:
        assert paper.link.startswith("https://"), paper.id
        assert "doi.org/" in paper.link or "arxiv.org/" in paper.link


def test_years_are_plausible(papers):
    for paper in papers:
        assert 1900 <= paper.year <= 2100


def test_difficulties_are_known(papers):
    for paper in papers:
        assert paper.difficulty in DIFFICULTIES


def test_author_summaries_are_readable(papers):
    long_paper = max(papers, key=lambda p: len(p.authors))
    assert "et al." in long_paper.author_summary
    short = next(p for p in papers if len(p.authors) == 1)
    assert short.author_summary == short.authors[0]


# --------------------------------------------------------------------------
# Validation rejects malformed records
# --------------------------------------------------------------------------


VALID_RECORD = {
    "id": "x001",
    "title": "A Valid Paper",
    "authors": ["A. Person"],
    "organisation": "Some University",
    "org_type": "institution",
    "year": 2020,
    "venue": "Nature",
    "doi": "10.1234/abc",
    "arxiv": None,
    "abstract": "An abstract.",
    "tags": ["tag"],
    "difficulty": "advanced",
    "algorithm_family": "simulation",
    "hardware_platform": "general",
}


def test_valid_record_parses():
    paper = parse_paper(dict(VALID_RECORD))
    assert paper.id == "x001"
    assert paper.link == "https://doi.org/10.1234/abc"


@pytest.mark.parametrize("missing", ["title", "organisation", "org_type", "year", "abstract", "tags"])
def test_missing_required_fields_are_rejected(missing):
    record = dict(VALID_RECORD)
    del record[missing]
    with pytest.raises(DatasetError):
        parse_paper(record)


def test_unknown_org_type_is_rejected():
    record = dict(VALID_RECORD, org_type="government")
    with pytest.raises(DatasetError):
        parse_paper(record)


def test_unknown_difficulty_is_rejected():
    record = dict(VALID_RECORD, difficulty="impossible")
    with pytest.raises(DatasetError):
        parse_paper(record)


def test_malformed_doi_is_rejected():
    record = dict(VALID_RECORD, doi="not-a-doi")
    with pytest.raises(DatasetError):
        parse_paper(record)


def test_malformed_arxiv_is_rejected():
    record = dict(VALID_RECORD, doi=None, arxiv="abcd")
    with pytest.raises(DatasetError):
        parse_paper(record)


def test_record_without_any_link_is_rejected():
    record = dict(VALID_RECORD, doi=None, arxiv=None)
    with pytest.raises(DatasetError):
        parse_paper(record)


def test_placeholder_author_is_rejected():
    """A name made only of initials ending in S is a placeholder, not a person."""
    record = dict(VALID_RECORD, authors=["A. S. S."])
    with pytest.raises(DatasetError) as excinfo:
        parse_paper(record)
    assert "placeholder" in str(excinfo.value)


def test_real_names_with_initials_are_accepted():
    record = dict(VALID_RECORD, authors=["Simao Mandra", "J. Mutus", "M. Y. Niu"])
    paper = parse_paper(record)
    assert len(paper.authors) == 3


def test_empty_author_list_is_rejected():
    with pytest.raises(DatasetError):
        parse_paper(dict(VALID_RECORD, authors=[]))


def test_out_of_range_year_is_rejected():
    with pytest.raises(DatasetError):
        parse_paper(dict(VALID_RECORD, year=1234))


def test_to_dict_is_json_serialisable(papers):
    payload = [p.to_dict() for p in papers]
    text = json.dumps(payload)
    assert len(json.loads(text)) == len(papers)


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------


def test_filter_by_org_type(papers):
    for org_type in ORG_TYPES:
        results = papers.filter(org_type=org_type)
        assert results
        assert all(p.org_type == org_type for p in results)


def test_filter_by_difficulty(papers):
    results = papers.filter(difficulty="advanced")
    assert all(p.difficulty == "advanced" for p in results)


def test_filter_rejects_unknown_org_type(papers):
    with pytest.raises(ValueError):
        papers.filter(org_type="nope")


def test_filter_by_year_range(papers):
    span = papers.years()
    low, high = min(span), max(span)
    results = papers.filter(year_min=low, year_max=high)
    assert len(results) == len(papers)
    assert all(low <= p.year <= high for p in results)


def test_filter_by_tag(papers):
    tag = papers.all()[0].tags[0]
    results = papers.filter(tag=tag)
    assert results
    assert all(tag in p.tags for p in results)


def test_filter_by_organisation_is_case_insensitive(papers):
    organisation = papers.all()[0].organisation
    lower = papers.filter(organisation=organisation.lower())
    assert organisation in {p.organisation for p in lower}


def test_combined_filters_are_conjunctive(papers):
    results = papers.filter(org_type="company", difficulty="advanced")
    assert all(p.org_type == "company" and p.difficulty == "advanced" for p in results)


def test_no_filters_returns_everything(papers):
    assert len(papers.filter()) == len(papers)


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------


def test_search_finds_a_known_title(papers):
    target = papers.all()[0]
    token = target.title.split()[0]
    results = papers.search(token)
    assert target.id in {p.id for p in results}


def test_search_ranks_title_matches_first(papers):
    results = papers.search("surface code")
    assert results
    assert "surface" in results[0].title.lower()


def test_search_with_no_match_is_empty(papers):
    assert papers.search("zzzznotarealtoken") == ()


def test_search_respects_limit(papers):
    assert len(papers.search("quantum", limit=3)) <= 3


def test_search_rejects_non_positive_limit(papers):
    with pytest.raises(ValueError):
        papers.search("quantum", limit=0)


def test_search_handles_empty_query(papers):
    assert papers.search("   ") == ()


# --------------------------------------------------------------------------
# Facets
# --------------------------------------------------------------------------


def test_facets_counts_match_the_dataset(papers):
    facets = papers.facets()
    assert sum(facets["org_type"]["counts"].values()) == len(papers)
    assert sum(facets["difficulty"]["counts"].values()) == len(papers)


def test_facets_org_type_counts_are_correct(papers):
    facets = papers.facets()
    for org_type in ORG_TYPES:
        expected = sum(1 for p in papers if p.org_type == org_type)
        assert facets["org_type"]["counts"][org_type] == expected


def test_facets_expose_a_year_range(papers):
    span = papers.facets()["year_range"]
    assert span["min"] <= span["max"]


# --------------------------------------------------------------------------
# Access
# --------------------------------------------------------------------------


def test_get_returns_none_for_unknown_id(papers):
    assert papers.get("does-not-exist") is None


def test_require_raises_for_unknown_id(papers):
    with pytest.raises(KeyError):
        papers.require("does-not-exist")


def test_require_returns_the_paper(papers):
    target = papers.all()[0]
    assert papers.require(target.id) is target


# --------------------------------------------------------------------------
# Project repository
# --------------------------------------------------------------------------


VALID_PROJECT = {
    "id": "x001",
    "title": "A Valid Project",
    "category": "search",
    "difficulty": "advanced",
    "implemented": True,
    "module": "quantumhub.algorithms",
    "test_module": "tests/test_algorithms.py",
    "description": "Does a thing.",
    "why_hard": "Because it is subtle.",
    "correctness_evidence": "Checked against the DFT matrix.",
    "tags": ["tag"],
    "entry_point": "some_function",
}


def test_valid_project_parses():
    project = parse_project(dict(VALID_PROJECT))
    assert project.id == "x001"
    assert project.source == "quantumhub.algorithms"


def test_implemented_project_requires_correctness_evidence():
    record = dict(VALID_PROJECT)
    del record["correctness_evidence"]
    with pytest.raises(ProjectDataError):
        parse_project(record)


def test_implemented_project_requires_a_module():
    record = dict(VALID_PROJECT)
    record["module"] = None
    with pytest.raises(ProjectDataError):
        parse_project(record)


def test_external_project_requires_a_url():
    record = dict(VALID_PROJECT, implemented=False, url=None, module=None)
    record.pop("correctness_evidence")
    with pytest.raises(ProjectDataError):
        parse_project(record)


def test_unknown_project_difficulty_is_rejected():
    with pytest.raises(ProjectDataError):
        parse_project(dict(VALID_PROJECT, difficulty="wizard"))


def test_project_dataset_loads(projects):
    assert len(projects) > 0


def test_project_dataset_has_implemented_and_external(projects):
    assert projects.implemented()
    assert projects.external()


def test_every_implemented_project_names_an_existing_module(projects):
    import importlib

    for project in projects.implemented():
        module = importlib.import_module(project.module)
        assert module is not None
        if project.entry_point:
            assert hasattr(module, project.entry_point), (
                f"{project.id}: {project.module} has no {project.entry_point}"
            )


def test_every_implemented_project_names_an_existing_test_file(projects):
    from pathlib import Path

    for project in projects.implemented():
        if project.test_module:
            path = Path(project.test_module)
            assert path.exists(), f"{project.id}: missing {path}"


def test_project_ids_are_unique(projects):
    ids = [p.id for p in projects]
    assert len(set(ids)) == len(ids)


def test_project_filter_by_implemented(projects):
    assert all(p.implemented for p in projects.filter(implemented=True))
    assert all(not p.implemented for p in projects.filter(implemented=False))


def test_project_filter_rejects_bad_difficulty(projects):
    with pytest.raises(ValueError):
        projects.filter(difficulty="wizard")


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------


def test_paper_distribution_totals(papers):
    distribution = analytics.paper_distribution(papers.all())
    assert distribution["total"] == len(papers)
    assert sum(distribution["by_org_type"].values()) == len(papers)
    assert sum(distribution["by_difficulty"].values()) == len(papers)


def test_paper_distribution_years_are_sorted(papers):
    distribution = analytics.paper_distribution(papers.all())
    years = list(distribution["by_year"])
    assert years == sorted(years)


def test_organisation_leaderboard_is_ordered(papers):
    board = analytics.organisation_leaderboard(papers.all(), limit=5)
    counts = [entry["papers"] for entry in board]
    assert counts == sorted(counts, reverse=True)
    assert len(board) <= 5


def test_organisation_leaderboard_rejects_bad_limit(papers):
    with pytest.raises(ValueError):
        analytics.organisation_leaderboard(papers.all(), limit=0)


def test_tag_leaderboard_is_ordered(papers):
    board = analytics.tag_leaderboard(papers.all(), limit=5)
    counts = [entry["count"] for entry in board]
    assert counts == sorted(counts, reverse=True)


def test_year_span(papers):
    span = analytics.year_span(papers.all())
    assert span["min"] <= span["max"]
    assert span["count"] >= 1


def test_year_span_rejects_empty_input():
    with pytest.raises(ValueError):
        analytics.year_span([])


def test_coverage_combines_both_datasets(papers, projects):
    summary = analytics.coverage(papers, projects)
    assert summary["papers"]["total"] == len(papers)
    assert summary["projects"]["total"] == len(projects)
    assert set(summary["paper_org_types"]) == set(ORG_TYPES)
