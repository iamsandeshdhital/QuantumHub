"""Tests for the Flask application: HTML pages, JSON API and the lab endpoint."""

import json

import pytest

import config
from app import ALGORITHM_CATALOGUE, create_app


@pytest.fixture(scope="module")
def app():
    settings = config.Config(testing=True, debug=False)
    return create_app(settings)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# --------------------------------------------------------------------------
# HTML pages
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/", "/papers", "/projects", "/lab", "/analytics", "/about", "/api-docs"],
)
def test_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200, path
    assert b"QuantumHub" in response.data


def test_index_shows_headline_numbers(client):
    body = client.get("/").get_data(as_text=True)
    assert "Papers" in body
    assert "Implementations" in body


def test_papers_page_lists_papers(client):
    body = client.get("/papers").get_data(as_text=True)
    assert "Papers" in body
    assert "badge-institution" in body or "badge-company" in body


def test_papers_page_accepts_a_search(client):
    body = client.get("/papers?q=surface+code").get_data(as_text=True)
    assert "matching" in body


def test_papers_page_rejects_an_unknown_filter(client):
    response = client.get("/papers?difficulty=wizard")
    assert response.status_code == 400


def test_paper_detail_renders(client):
    listing = json.loads(client.get("/api/papers?per_page=1").get_data(as_text=True))
    paper_id = listing["papers"][0]["id"]
    response = client.get(f"/papers/{paper_id}")
    assert response.status_code == 200
    assert b"Abstract" in response.data


def test_unknown_paper_detail_is_404(client):
    assert client.get("/papers/nope").status_code == 404


def test_project_detail_renders(client):
    listing = json.loads(client.get("/api/projects?per_page=1").get_data(as_text=True))
    project_id = listing["projects"][0]["id"]
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    assert b"Why it is hard" in response.data


def test_unknown_project_detail_is_404(client):
    assert client.get("/projects/nope").status_code == 404


def test_lab_page_lists_every_algorithm(client):
    """Each catalogue entry must appear on the lab page and in its JS payload."""
    body = client.get("/lab").get_data(as_text=True)
    for entry in ALGORITHM_CATALOGUE:
        assert entry["key"] in body, entry["key"]


def test_lab_page_offers_every_parameter(client):
    """Every parameter in the catalogue must reach the browser as JSON."""
    body = client.get("/lab").get_data(as_text=True)
    for entry in ALGORITHM_CATALOGUE:
        for parameter in entry["parameters"]:
            assert f'"{parameter}"' in body, (entry["key"], parameter)


def test_about_page_states_the_verification_approach(client):
    body = client.get("/about").get_data(as_text=True)
    assert "verification" in body.lower()


# --------------------------------------------------------------------------
# JSON API: health and papers
# --------------------------------------------------------------------------


def test_health(client):
    payload = client.get("/api/health").get_json()
    assert payload["status"] == "ok"
    assert payload["papers"] > 0
    assert payload["projects"] > 0


def test_papers_api_shape(client):
    payload = client.get("/api/papers").get_json()
    assert set(payload) >= {"count", "total", "pagination", "papers"}
    assert isinstance(payload["papers"], list)
    first = payload["papers"][0]
    assert set(first) >= {
        "id",
        "title",
        "authors",
        "organisation",
        "org_type",
        "year",
        "abstract",
        "tags",
        "link",
    }


def test_papers_api_filters_by_org_type(client):
    payload = client.get("/api/papers?org_type=company").get_json()
    assert payload["papers"]
    assert all(p["org_type"] == "company" for p in payload["papers"])


def test_papers_api_rejects_unknown_filter(client):
    response = client.get("/api/papers?org_type=government")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_papers_api_search(client):
    payload = client.get("/api/papers?q=surface+code").get_json()
    assert payload["total"] >= 1
    assert any("surface" in p["title"].lower() for p in payload["papers"])


def test_papers_api_pagination(client):
    first = client.get("/api/papers?per_page=2&page=1").get_json()
    second = client.get("/api/papers?per_page=2&page=2").get_json()
    assert first["count"] <= 2
    assert first["pagination"]["has_next"] is True
    if second["papers"]:
        assert first["papers"][0]["id"] != second["papers"][0]["id"]


def test_papers_api_clamps_per_page(client):
    payload = client.get("/api/papers?per_page=100000").get_json()
    assert payload["pagination"]["per_page"] <= 100


def test_papers_api_sorting(client):
    ascending = client.get("/api/papers?sort=year&order=asc").get_json()
    years = [p["year"] for p in ascending["papers"]]
    assert years == sorted(years)

    descending = client.get("/api/papers?sort=year&order=desc").get_json()
    years = [p["year"] for p in descending["papers"]]
    assert years == sorted(years, reverse=True)


def test_paper_by_id(client):
    listing = client.get("/api/papers?per_page=1").get_json()
    paper_id = listing["papers"][0]["id"]
    payload = client.get(f"/api/papers/{paper_id}").get_json()
    assert payload["id"] == paper_id


def test_paper_by_unknown_id_is_404_json(client):
    response = client.get("/api/papers/nope")
    assert response.status_code == 404
    assert response.is_json
    assert "error" in response.get_json()


def test_paper_facets(client):
    payload = client.get("/api/papers/facets").get_json()
    assert set(payload) >= {"org_type", "difficulty", "algorithm_family", "tags"}
    assert sum(payload["org_type"]["counts"].values()) == payload["org_type"]["counts"]["institution"] + payload["org_type"]["counts"]["company"] + payload["org_type"]["counts"]["independent"]


# --------------------------------------------------------------------------
# JSON API: projects and analytics
# --------------------------------------------------------------------------


def test_projects_api(client):
    payload = client.get("/api/projects").get_json()
    assert payload["count"] > 0
    assert set(payload["projects"][0]) >= {"id", "title", "implemented", "description"}


def test_projects_api_filters_by_implemented(client):
    payload = client.get("/api/projects?implemented=true").get_json()
    assert all(p["implemented"] for p in payload["projects"])


def test_project_by_id(client):
    listing = client.get("/api/projects?per_page=1").get_json()
    project_id = listing["projects"][0]["id"]
    payload = client.get(f"/api/projects/{project_id}").get_json()
    assert payload["id"] == project_id


def test_unknown_project_is_404_json(client):
    response = client.get("/api/projects/nope")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_analytics_api(client):
    payload = client.get("/api/analytics").get_json()
    assert set(payload) >= {"papers", "projects", "organisations", "tags", "year_span"}


def test_analytics_papers_api(client):
    payload = client.get("/api/analytics/papers").get_json()
    assert payload["total"] > 0
    assert sum(payload["by_org_type"].values()) == payload["total"]


def test_analytics_projects_api(client):
    payload = client.get("/api/analytics/projects").get_json()
    assert payload["implemented"] + payload["external"] == payload["total"]


# --------------------------------------------------------------------------
# Lab experiments
# --------------------------------------------------------------------------


def _run(client, algorithm, **parameters):
    """POST an experiment with a proper JSON content type."""
    return client.post(
        "/lab/run",
        data=json.dumps({"algorithm": algorithm, "parameters": parameters}),
        content_type="application/json",
    )


def test_lab_bell(client):
    payload = _run(client, "bell").get_json()
    assert payload["fidelity_phi_plus"] > 0.999


def test_lab_ghz(client):
    payload = _run(client, "ghz", qubits=4).get_json()
    assert payload["state"]["num_qubits"] == 4
    assert abs(payload["state"]["entropy"] - 1.0) < 1e-6


def test_lab_grover(client):
    payload = _run(client, "grover", qubits=4, marked=5).get_json()
    assert payload["found"] == format(5, "04b")
    assert payload["success_probability"] > 0.5


def test_lab_deutsch_jozsa(client):
    payload = _run(client, "deutsch-jozsa", qubits=3, oracle="parity").get_json()
    assert payload["outcome"] == "linear"

    payload = _run(client, "deutsch-jozsa", qubits=3, oracle="constant0").get_json()
    assert payload["outcome"] == "constant"


def test_lab_bernstein_vazirani(client):
    payload = _run(client, "bernstein-vazirani", qubits=4, secret=11).get_json()
    assert payload["correct"] is True


def test_lab_qft_verifies_against_the_dft(client):
    payload = _run(client, "qft", qubits=3, input=1).get_json()
    assert payload["matches_exact_dft"] is True


def test_lab_phase_estimation(client):
    payload = _run(client, "phase-estimation", phase=0.25, precision=3).get_json()
    assert payload["estimation_error"] < 1e-9


def test_lab_simon(client):
    payload = _run(client, "simon", period=9).get_json()
    assert payload["exact"] is True


def test_lab_teleport(client):
    payload = _run(client, "teleport", seed=0).get_json()
    assert payload["success"] is True
    assert payload["fidelity"] > 0.999


def test_lab_factor(client):
    payload = _run(client, "factor", n=15).get_json()
    assert payload["verified"] is True
    assert payload["factors"][0] * payload["factors"][1] == 15


def test_lab_qaoa(client):
    payload = _run(client, "qaoa", qubits=4, p=1, iterations=40).get_json()
    assert payload["matches_optimal"] is True


def test_lab_vqe(client):
    payload = _run(client, "vqe", seed=7).get_json()
    assert payload["energy_error"] < 1e-4


def test_lab_rejects_unknown_algorithm(client):
    response = _run(client, "teleportation-engine")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_lab_rejects_out_of_range_parameter(client):
    response = _run(client, "ghz", qubits=99)
    assert response.status_code == 400
    assert "between" in response.get_json()["error"]


def test_lab_rejects_non_numeric_parameter(client):
    response = _run(client, "ghz", qubits="many")
    assert response.status_code == 400
    assert "integer" in response.get_json()["error"]


def test_lab_rejects_out_of_range_phase(client):
    response = _run(client, "phase-estimation", phase=1.5)
    assert response.status_code == 400


def test_lab_every_catalogued_algorithm_runs(client):
    """Smoke-test each catalogue entry with its documented defaults."""
    defaults = {
        "bell": {},
        "ghz": {"qubits": 3},
        "grover": {"qubits": 3, "marked": 3},
        "deutsch-jozsa": {"qubits": 3},
        "bernstein-vazirani": {"qubits": 3, "secret": 5},
        "qft": {"qubits": 2, "input": 1},
        "phase-estimation": {"phase": 0.5, "precision": 2},
        "simon": {"period": 3},
        "teleport": {"seed": 0},
        "factor": {"n": 15},
        "qaoa": {"qubits": 3, "p": 1, "iterations": 20},
        "vqe": {"seed": 1},
    }
    assert set(defaults) == {entry["key"] for entry in ALGORITHM_CATALOGUE}

    for key, parameters in defaults.items():
        response = _run(client, key, **parameters)
        assert response.status_code == 200, (key, response.get_data(as_text=True))
        payload = response.get_json()
        assert "error" not in payload, (key, payload)


def test_lab_handles_an_empty_body(client):
    response = client.post("/lab/run", data=json.dumps({}), content_type="application/json")
    assert response.status_code == 400


def test_lab_rejects_a_non_json_body(client):
    """A body sent without the JSON content type must be rejected, not guessed."""
    response = client.post("/lab/run", data="algorithm=grover")
    assert response.status_code == 400
    assert "JSON" in response.get_json()["error"]


def test_lab_rejects_a_missing_algorithm_key(client):
    response = client.post(
        "/lab/run", data=json.dumps({"parameters": {}}), content_type="application/json"
    )
    assert response.status_code == 400


def test_lab_rejects_non_object_parameters(client):
    response = client.post(
        "/lab/run",
        data=json.dumps({"algorithm": "ghz", "parameters": [1, 2]}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "parameters" in response.get_json()["error"]


# --------------------------------------------------------------------------
# Error handling
# --------------------------------------------------------------------------


def test_api_404_is_json(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["error"] == "not found"


def test_html_404_is_html(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert b"does not exist" in response.data
