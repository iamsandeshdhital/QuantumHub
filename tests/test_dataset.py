"""Tests for the dataset loaders' failure modes and the validator script.

These exercise the error paths that only fire when something is wrong with the
data files, which is exactly when you want a clear failure rather than a stack
trace from deep inside a request handler.
"""

import json

import pytest

from quantumhub.papers import DatasetError, PaperRepository, parse_paper
from quantumhub.projects import ProjectDataError, ProjectRepository, parse_project

VALID_PAPER = {
    "id": "p001",
    "title": "A Paper",
    "authors": ["A. Person"],
    "organisation": "A University",
    "org_type": "institution",
    "year": 2020,
    "venue": "Nature",
    "doi": "10.1000/xyz",
    "arxiv": None,
    "abstract": "An abstract.",
    "tags": ["alpha"],
    "difficulty": "advanced",
    "algorithm_family": "simulation",
    "hardware_platform": "general",
}


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Paper loader failures
# --------------------------------------------------------------------------


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(DatasetError) as excinfo:
        PaperRepository.from_path(tmp_path / "absent.json")
    assert "not found" in str(excinfo.value)


def test_invalid_json_is_reported(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(DatasetError) as excinfo:
        PaperRepository.from_path(path)
    assert "not valid JSON" in str(excinfo.value)


def test_missing_papers_key_is_reported(tmp_path):
    path = _write(tmp_path, "d.json", {"metadata": {}})
    with pytest.raises(DatasetError) as excinfo:
        PaperRepository.from_path(path)
    assert "'papers' list" in str(excinfo.value)


def test_papers_must_be_a_list(tmp_path):
    path = _write(tmp_path, "d.json", {"papers": {"id": "p001"}})
    with pytest.raises(DatasetError):
        PaperRepository.from_path(path)


def test_duplicate_ids_are_rejected(tmp_path):
    path = _write(
        tmp_path,
        "d.json",
        {"papers": [dict(VALID_PAPER, id="p001"), dict(VALID_PAPER, id="p001")]},
    )
    with pytest.raises(DatasetError) as excinfo:
        PaperRepository.from_path(path)
    assert "duplicate" in str(excinfo.value)


def test_author_must_be_a_string(tmp_path):
    path = _write(tmp_path, "d.json", {"papers": [dict(VALID_PAPER, authors=[42])]})
    with pytest.raises(DatasetError):
        PaperRepository.from_path(path)


def test_blank_author_is_rejected(tmp_path):
    path = _write(tmp_path, "d.json", {"papers": [dict(VALID_PAPER, authors=["   "])]})
    with pytest.raises(DatasetError):
        PaperRepository.from_path(path)


def test_tags_must_be_a_non_empty_list(tmp_path):
    path = _write(tmp_path, "d.json", {"papers": [dict(VALID_PAPER, tags=[])]})
    with pytest.raises(DatasetError):
        PaperRepository.from_path(path)


def test_record_without_an_id_is_still_validated(tmp_path):
    """A record with no id is reported using a readable placeholder."""
    record = dict(VALID_PAPER)
    del record["id"]
    del record["title"]
    with pytest.raises(DatasetError) as excinfo:
        parse_paper(record)
    assert "<no id>" in str(excinfo.value)


def test_arxiv_identifier_may_carry_a_version(tmp_path):
    path = _write(tmp_path, "d.json", {"papers": [dict(VALID_PAPER, arxiv="2103.05604v2")]})
    repository = PaperRepository.from_path(path)
    assert repository.all()[0].arxiv == "2103.05604v2"


def test_old_style_arxiv_identifier_is_accepted(tmp_path):
    path = _write(tmp_path, "d.json", {"papers": [dict(VALID_PAPER, arxiv="quant-ph/9508027")]})
    repository = PaperRepository.from_path(path)
    assert repository.all()[0].arxiv == "quant-ph/9508027"


def test_paper_link_prefers_the_doi(tmp_path):
    path = _write(
        tmp_path, "d.json", {"papers": [dict(VALID_PAPER, arxiv="2103.05604")]}
    )
    paper = PaperRepository.from_path(path).all()[0]
    assert paper.link.startswith("https://doi.org/")


def test_paper_link_falls_back_to_arxiv(tmp_path):
    path = _write(tmp_path, "d.json", {"papers": [dict(VALID_PAPER, doi=None, arxiv="2103.05604")]})
    paper = PaperRepository.from_path(path).all()[0]
    assert paper.link == "https://arxiv.org/abs/2103.05604"


def test_author_summary_truncates_long_lists():
    record = dict(VALID_PAPER, authors=[f"Author {i}" for i in range(10)])
    paper = parse_paper(record)
    assert paper.author_summary.startswith("Author 0 et al.")
    assert "10 authors" in paper.author_summary


# --------------------------------------------------------------------------
# Project loader failures
# --------------------------------------------------------------------------


VALID_PROJECT = {
    "id": "j001",
    "title": "A Project",
    "category": "search",
    "difficulty": "advanced",
    "implemented": True,
    "module": "quantumhub.algorithms",
    "description": "Does a thing.",
    "why_hard": "Because it is subtle.",
    "correctness_evidence": "Checked against theory.",
    "tags": ["alpha"],
    "entry_point": "grover_search",
}


def test_missing_project_file_is_reported(tmp_path):
    with pytest.raises(ProjectDataError) as excinfo:
        ProjectRepository.from_path(tmp_path / "absent.json")
    assert "not found" in str(excinfo.value)


def test_invalid_project_json_is_reported(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("nope", encoding="utf-8")
    with pytest.raises(ProjectDataError) as excinfo:
        ProjectRepository.from_path(path)
    assert "not valid JSON" in str(excinfo.value)


def test_missing_projects_key_is_reported(tmp_path):
    path = _write(tmp_path, "d.json", {"metadata": {}})
    with pytest.raises(ProjectDataError) as excinfo:
        ProjectRepository.from_path(path)
    assert "'projects' list" in str(excinfo.value)


def test_duplicate_project_ids_are_rejected(tmp_path):
    path = _write(
        tmp_path, "d.json", {"projects": [dict(VALID_PROJECT), dict(VALID_PROJECT)]}
    )
    with pytest.raises(ProjectDataError) as excinfo:
        ProjectRepository.from_path(path)
    assert "duplicate" in str(excinfo.value)


def test_implemented_flag_must_be_boolean():
    with pytest.raises(ProjectDataError) as excinfo:
        parse_project(dict(VALID_PROJECT, implemented="yes"))
    assert "boolean" in str(excinfo.value)


def test_external_project_without_a_url_is_rejected():
    record = dict(VALID_PROJECT, implemented=False, url=None)
    record.pop("correctness_evidence")
    with pytest.raises(ProjectDataError) as excinfo:
        parse_project(record)
    assert "http 'url'" in str(excinfo.value)


def test_external_project_with_a_non_http_url_is_rejected():
    record = dict(VALID_PROJECT, implemented=False, url="ftp://example.com")
    record.pop("correctness_evidence")
    with pytest.raises(ProjectDataError):
        parse_project(record)


def test_project_tags_must_be_a_non_empty_list():
    with pytest.raises(ProjectDataError):
        parse_project(dict(VALID_PROJECT, tags=[]))


def test_project_source_for_an_external_entry():
    record = dict(VALID_PROJECT, implemented=False, url="https://example.com/repo")
    record.pop("correctness_evidence")
    project = parse_project(record)
    assert project.source == "https://example.com/repo"


def test_project_source_is_the_module_for_an_implemented_entry():
    project = parse_project(dict(VALID_PROJECT))
    assert project.source == "quantumhub.algorithms"
