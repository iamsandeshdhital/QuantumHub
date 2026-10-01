"""
QuantumHub web application.

Serves an HTML interface and a JSON API over the paper dataset, the project
catalogue, the analytics module, and a live view of the simulator and the
algorithm implementations in this repository.

Run with:

    python app.py

Built by Sandesh Dhital.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from flask import Flask, abort, jsonify, render_template, request

import config
from quantumhub import algorithms as algo
from quantumhub import analytics
from quantumhub.papers import DIFFICULTIES, ORG_TYPES
from quantumhub.papers import get_repository as get_papers
from quantumhub.projects import get_repository as get_projects
from quantumhub.statevector import QuantumRegister, QuantumState


def create_app(settings: config.Config | None = None) -> Flask:
    """Build and configure the Flask application.

    Args:
        settings: Configuration to use. Defaults to the module-level config.

    Returns:
        The configured application.
    """
    settings = settings or config.config

    app = Flask(
        __name__,
        template_folder=settings.templates_folder,
        static_folder=settings.static_folder,
    )
    app.config.update(settings.as_flask_config())
    app.config["QH_SETTINGS"] = settings

    papers_repo = get_papers()
    projects_repo = get_projects()

    register_routes(app, papers_repo, projects_repo, settings)
    return app


def register_routes(
    app: Flask,
    papers_repo,
    projects_repo,
    settings: config.Config,
) -> None:
    """Attach every route to ``app``.

    Split out from :func:`create_app` so the route table is easy to read in one
    place and easy to test in isolation.

    Args:
        app: The application to attach routes to.
        papers_repo: The paper repository.
        projects_repo: The project repository.
        settings: The active configuration.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _paginate(items: list[Any]):
        """Return ``(page_items, pagination_dict)`` for a request."""
        page = request.args.get("page", default=1, type=int)
        per_page = request.args.get("per_page", default=settings.page_size, type=int)
        page = max(1, page)
        per_page = max(1, min(per_page, settings.max_page_size))

        total_items = len(items)
        total_pages = max(1, math.ceil(total_items / per_page))
        page = min(page, total_pages)
        start = (page - 1) * per_page

        return items[start : start + per_page], {
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        }

    def _paper_filters() -> dict[str, str | None]:
        """Extract paper filters from the query string."""
        return {
            "query": request.args.get("q") or None,
            "org_type": request.args.get("org_type") or None,
            "difficulty": request.args.get("difficulty") or None,
            "algorithm_family": request.args.get("algorithm_family") or None,
            "hardware_platform": request.args.get("hardware_platform") or None,
            "tag": request.args.get("tag") or None,
            "organisation": request.args.get("organisation") or None,
            "year_min": request.args.get("year_min", type=int),
            "year_max": request.args.get("year_max", type=int),
        }

    def _sorted_papers(papers):
        """Apply the requested sort order to a list of papers."""
        sort = request.args.get("sort", "year")
        order = request.args.get("order", "desc")
        reverse = order == "desc"
        if sort == "year":
            return sorted(papers, key=lambda p: p.year, reverse=reverse)
        if sort == "title":
            return sorted(papers, key=lambda p: p.title.lower(), reverse=reverse)
        if sort == "organisation":
            return sorted(papers, key=lambda p: p.organisation.lower(), reverse=reverse)
        return sorted(papers, key=lambda p: p.id)

    # ------------------------------------------------------------------
    # HTML pages
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        """Landing page with headline statistics."""
        papers = papers_repo.all()
        summary = analytics.coverage(papers_repo, projects_repo)
        return render_template(
            "index.html",
            summary=summary,
            org_types=ORG_TYPES,
            difficulties=DIFFICULTIES,
            recent_papers=sorted(papers, key=lambda p: p.year, reverse=True)[:6],
            implemented=projects_repo.implemented()[:6],
        )

    @app.route("/papers")
    def papers_page():
        """Filterable, paginated list of papers."""
        filters = _paper_filters()
        try:
            results = list(papers_repo.filter(**filters))
        except ValueError as exc:
            return render_template("error.html", message=str(exc)), 400

        if filters["query"]:
            results = list(papers_repo.search(filters["query"], limit=settings.max_search_results))

        results = _sorted_papers(results)
        page_items, pagination = _paginate(results)

        return render_template(
            "papers.html",
            papers=page_items,
            pagination=pagination,
            facets=papers_repo.facets(),
            filters=filters,
            org_types=ORG_TYPES,
            difficulties=DIFFICULTIES,
            total=len(results),
        )

    @app.route("/papers/<paper_id>")
    def paper_detail(paper_id: str):
        """A single paper with related entries."""
        paper = papers_repo.get(paper_id)
        if paper is None:
            abort(404)

        related = papers_repo.filter(algorithm_family=paper.algorithm_family)
        if len(related) <= 1:
            related = papers_repo.filter(tag=paper.tags[0])
        related = [p for p in related if p.id != paper.id][:6]

        return render_template(
            "paper_detail.html", paper=paper, related=related, facets=papers_repo.facets()
        )

    @app.route("/projects")
    def projects_page():
        """The project catalogue."""
        category = request.args.get("category")
        difficulty = request.args.get("difficulty")
        implemented = request.args.get("implemented")
        show_implemented = None
        if implemented is not None:
            show_implemented = implemented.lower() in {"1", "true", "yes"}

        try:
            results = projects_repo.filter(
                category=category, difficulty=difficulty, implemented=show_implemented
            )
        except ValueError as exc:
            return render_template("error.html", message=str(exc)), 400

        return render_template(
            "projects.html",
            projects=results,
            facets=projects_repo.facets(),
            category=category,
            difficulty=difficulty,
            implemented=show_implemented,
        )

    @app.route("/projects/<project_id>")
    def project_detail(project_id: str):
        """A single project."""
        project = projects_repo.get(project_id)
        if project is None:
            abort(404)
        return render_template("project_detail.html", project=project)

    @app.route("/lab")
    def lab():
        """The interactive simulator page."""
        return render_template(
            "lab.html",
            algorithms=ALGORITHM_CATALOGUE,
            max_qubits=8,
        )

    @app.route("/lab/run", methods=["POST"])
    def lab_run():
        """Execute one lab experiment and return the result as JSON.

        The body must be a JSON object carrying an ``algorithm`` key. A
        malformed body is rejected rather than silently falling back to
        defaults, so a client bug cannot quietly run a different experiment.
        """
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(
                {"error": "request body must be a JSON object with an 'algorithm' key"}
            ), 400

        algorithm = payload.get("algorithm")
        if not isinstance(algorithm, str) or not algorithm.strip():
            return jsonify({"error": "'algorithm' must be a non-empty string"}), 400

        parameters = payload.get("parameters") or {}
        if not isinstance(parameters, dict):
            return jsonify({"error": "'parameters' must be an object"}), 400

        try:
            result = _run_lab_experiment(algorithm.strip(), parameters)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # pragma: no cover - defensive
            return jsonify({"error": f"experiment failed: {exc}"}), 500

        return jsonify(result)

    @app.route("/analytics")
    def analytics_page():
        """Distribution charts rendered as inline SVG-free HTML bars."""
        return render_template(
            "analytics.html",
            summary=analytics.coverage(papers_repo, projects_repo),
        )

    @app.route("/about")
    def about():
        """Project background and scope."""
        return render_template("about.html")

    @app.route("/api-docs")
    def api_docs():
        """Human-readable API reference."""
        return render_template("api_docs.html", endpoints=API_ENDPOINTS)

    # ------------------------------------------------------------------
    # JSON API: papers
    # ------------------------------------------------------------------

    @app.route("/api/health")
    def api_health():
        """Liveness probe."""
        return jsonify(
            {
                "status": "ok",
                "papers": len(papers_repo),
                "projects": len(projects_repo),
            }
        )

    @app.route("/api/papers")
    def api_papers():
        """List papers with filtering, search, sorting and pagination."""
        filters = _paper_filters()
        try:
            if filters["query"]:
                results = list(
                    papers_repo.search(filters["query"], limit=settings.max_search_results)
                )
            else:
                results = list(papers_repo.filter(**filters))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        results = _sorted_papers(results)
        page_items, pagination = _paginate(results)

        return jsonify(
            {
                "count": len(page_items),
                "total": len(results),
                "pagination": pagination,
                "filters": {k: v for k, v in filters.items() if v is not None},
                "papers": [p.to_dict() for p in page_items],
            }
        )

    @app.route("/api/papers/<paper_id>")
    def api_paper(paper_id: str):
        """Fetch one paper."""
        paper = papers_repo.get(paper_id)
        if paper is None:
            return jsonify({"error": f"no paper with id {paper_id!r}"}), 404
        return jsonify(paper.to_dict())

    @app.route("/api/papers/facets")
    def api_paper_facets():
        """Available filter values and their counts."""
        return jsonify(papers_repo.facets())

    # ------------------------------------------------------------------
    # JSON API: projects
    # ------------------------------------------------------------------

    @app.route("/api/projects")
    def api_projects():
        """List projects."""
        implemented = request.args.get("implemented")
        show = None
        if implemented is not None:
            show = implemented.lower() in {"1", "true", "yes"}
        try:
            results = projects_repo.filter(
                category=request.args.get("category"),
                difficulty=request.args.get("difficulty"),
                implemented=show,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"count": len(results), "projects": [p.to_dict() for p in results]})

    @app.route("/api/projects/<project_id>")
    def api_project(project_id: str):
        """Fetch one project."""
        project = projects_repo.get(project_id)
        if project is None:
            return jsonify({"error": f"no project with id {project_id!r}"}), 404
        return jsonify(project.to_dict())

    # ------------------------------------------------------------------
    # JSON API: analytics
    # ------------------------------------------------------------------

    @app.route("/api/analytics")
    def api_analytics():
        """Combined distribution statistics across both datasets."""
        return jsonify(analytics.coverage(papers_repo, projects_repo))

    @app.route("/api/analytics/papers")
    def api_analytics_papers():
        """Distribution of papers only."""
        return jsonify(analytics.paper_distribution(papers_repo.all()))

    @app.route("/api/analytics/projects")
    def api_analytics_projects():
        """Distribution of projects only."""
        return jsonify(analytics.project_distribution(projects_repo.all()))

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------

    @app.errorhandler(404)
    def handle_404(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "not found", "path": request.path}), 404
        return render_template("error.html", message="That page does not exist."), 404

    @app.errorhandler(500)
    def handle_500(error):  # pragma: no cover - defensive
        if request.path.startswith("/api/"):
            return jsonify({"error": "internal server error"}), 500
        return render_template("error.html", message="Something went wrong."), 500


# --------------------------------------------------------------------------
# Lab experiments
# --------------------------------------------------------------------------


ALGORITHM_CATALOGUE: tuple[dict[str, Any], ...] = (
    {
        "key": "bell",
        "name": "Bell state",
        "description": "Prepare a maximally entangled pair and report the outcome distribution.",
        "parameters": {},
    },
    {
        "key": "ghz",
        "name": "GHZ state",
        "description": "Prepare an n-qubit GHZ state and report the entropy and distribution.",
        "parameters": {"qubits": {"type": "int", "default": 4, "min": 2, "max": 10}},
    },
    {
        "key": "grover",
        "name": "Grover search",
        "description": "Search an unstructured space for a marked item using amplitude amplification.",
        "parameters": {
            "qubits": {"type": "int", "default": 4, "min": 2, "max": 8},
            "marked": {"type": "int", "default": 5, "min": 0, "max": 255},
        },
    },
    {
        "key": "deutsch-jozsa",
        "name": "Deutsch-Jozsa",
        "description": "Distinguish a constant oracle from a linear one with one query.",
        "parameters": {
            "qubits": {"type": "int", "default": 3, "min": 1, "max": 8},
            "oracle": {"type": "choice", "default": "parity", "options": ["parity", "constant0", "constant1"]},
        },
    },
    {
        "key": "bernstein-vazirani",
        "name": "Bernstein-Vazirani",
        "description": "Recover a hidden bit string with a single oracle query.",
        "parameters": {
            "qubits": {"type": "int", "default": 4, "min": 1, "max": 8},
            "secret": {"type": "int", "default": 11, "min": 0, "max": 255},
        },
    },
    {
        "key": "qft",
        "name": "Quantum Fourier transform",
        "description": "Apply the QFT to a basis state and compare against the exact DFT.",
        "parameters": {
            "qubits": {"type": "int", "default": 3, "min": 1, "max": 6},
            "input": {"type": "int", "default": 1, "min": 0, "max": 63},
        },
    },
    {
        "key": "phase-estimation",
        "name": "Phase estimation",
        "description": "Estimate the phase of an eigenvalue using a precision register.",
        "parameters": {
            "phase": {"type": "float", "default": 0.25, "min": 0.0, "max": 1.0},
            "precision": {"type": "int", "default": 3, "min": 1, "max": 5},
        },
    },
    {
        "key": "simon",
        "name": "Simon's algorithm",
        "description": "Find the period of a two-to-one oracle via a GF(2) null space.",
        "parameters": {
            "period": {"type": "int", "default": 9, "min": 1, "max": 15},
        },
    },
    {
        "key": "teleport",
        "name": "Teleportation",
        "description": "Teleport an arbitrary qubit state and measure the reconstruction fidelity.",
        "parameters": {"seed": {"type": "int", "default": 0, "min": 0, "max": 1000}},
    },
    {
        "key": "factor",
        "name": "Integer factoring",
        "description": "Factor a composite integer by order finding, as in Shor's algorithm.",
        "parameters": {
            "n": {"type": "int", "default": 15, "min": 4, "max": 9999},
        },
    },
    {
        "key": "qaoa",
        "name": "QAOA MaxCut",
        "description": "Optimise a graph cut value with the quantum approximate optimization algorithm.",
        "parameters": {
            "qubits": {"type": "int", "default": 4, "min": 2, "max": 6},
            "p": {"type": "int", "default": 1, "min": 1, "max": 3},
            "iterations": {"type": "int", "default": 60, "min": 5, "max": 300},
        },
    },
    {
        "key": "vqe",
        "name": "VQE for H2",
        "description": "Estimate the H2 ground energy with a variational eigensolver.",
        "parameters": {"seed": {"type": "int", "default": 7, "min": 0, "max": 1000}},
    },
)


def _require_int(parameters: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    """Read a bounded integer parameter."""
    raw = parameters.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"parameter {key!r} must be an integer, got {raw!r}") from exc
    if not low <= value <= high:
        raise ValueError(f"parameter {key!r} must be between {low} and {high}, got {value}")
    return value


def _require_float(parameters: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    """Read a bounded float parameter."""
    raw = parameters.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"parameter {key!r} must be a number, got {raw!r}") from exc
    if not low <= value <= high:
        raise ValueError(f"parameter {key!r} must be between {low} and {high}, got {value}")
    return value


def _ring_graph(n: int) -> list[tuple[int, int]]:
    """A connected cycle-plus-chords graph on n vertices, used by the QAOA lab."""
    edges = [(i, (i + 1) % n) for i in range(n)]
    if n >= 4:
        edges.append((0, n // 2))
    return edges


def _run_lab_experiment(algorithm: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Execute one lab experiment.

    Args:
        algorithm: One of the keys in :data:`ALGORITHM_CATALOGUE`.
        parameters: The experiment parameters.

    Returns:
        A JSON-serialisable result dict.

    Raises:
        ValueError: If the algorithm is unknown or a parameter is invalid.
    """
    if algorithm == "bell":
        state = QuantumState(QuantumRegister(2, "bell"))
        state.h(0)
        state.cnot(0, 1)
        return {
            "algorithm": algorithm,
            "state": state.to_dict(),
            "fidelity_phi_plus": algo.bell_fidelity(state, "phi+"),
        }

    if algorithm == "ghz":
        n = _require_int(parameters, "qubits", 4, 2, 10)
        state = QuantumState(QuantumRegister(n, "ghz"))
        state.h(0)
        for q in range(n - 1):
            state.cnot(q, q + 1)
        return {"algorithm": algorithm, "state": state.to_dict()}

    if algorithm == "grover":
        n = _require_int(parameters, "qubits", 4, 2, 8)
        marked = _require_int(parameters, "marked", 5, 0, (1 << n) - 1)
        result = algo.grover_search([marked], n_qubits=n)
        return {
            "algorithm": algorithm,
            "found": result.marked_bitstring,
            "target": format(marked, f"0{n}b"),
            "success_probability": round(result.success_probability, 6),
            "iterations": result.iterations,
            "oracle_calls": result.oracle_calls,
            "classical_query_bound": 1 << n,
        }

    if algorithm == "deutsch-jozsa":
        n = _require_int(parameters, "qubits", 3, 1, 8)
        choice = parameters.get("oracle", "parity")
        oracles = {
            "parity": algo.parity_oracle,
            "constant0": algo.constant_oracle(0),
            "constant1": algo.constant_oracle(1),
        }
        if choice not in oracles:
            raise ValueError(f"unknown oracle {choice!r}")
        outcome = algo.deutsch_jozsa(oracles[choice], n)
        return {
            "algorithm": algorithm,
            "oracle": choice,
            "outcome": "constant" if outcome == 0 else "linear",
            "oracle_queries": 1,
        }

    if algorithm == "bernstein-vazirani":
        n = _require_int(parameters, "qubits", 4, 1, 8)
        secret = _require_int(parameters, "secret", 11, 0, (1 << n) - 1)
        recovered = algo.bernstein_vazirani(algo.hidden_string_oracle(secret), n)
        return {
            "algorithm": algorithm,
            "secret": format(secret, f"0{n}b"),
            "recovered": format(recovered, f"0{n}b"),
            "correct": recovered == secret,
            "oracle_queries": 1,
            "classical_query_bound": n,
        }

    if algorithm == "qft":
        n = _require_int(parameters, "qubits", 3, 1, 6)
        basis = _require_int(parameters, "input", 1, 0, (1 << n) - 1)
        state = QuantumState(QuantumRegister(n, "qft"))
        vector = np.zeros(1 << n, dtype=complex)
        vector[basis] = 1
        state.set_state(vector)
        algo.quantum_fourier_transform(state, list(range(n)))

        size = 1 << n
        exact = np.array(
            [
                [np.exp(2j * math.pi * i * j / size) / math.sqrt(size) for j in range(size)]
                for i in range(size)
            ],
            dtype=complex,
        )
        return {
            "algorithm": algorithm,
            "input": format(basis, f"0{n}b"),
            "state": state.to_dict(),
            "matches_exact_dft": bool(np.allclose(state.state, exact[:, basis], atol=1e-10)),
        }

    if algorithm == "phase-estimation":
        phase = _require_float(parameters, "phase", 0.25, 0.0, 0.999999)
        precision = _require_int(parameters, "precision", 3, 1, 5)
        estimates, probabilities = algo.phase_estimation(phase, precision)
        best = int(np.argmax(probabilities))
        return {
            "algorithm": algorithm,
            "true_phase": phase,
            "estimate": round(float(estimates[best]), 6),
            "estimation_error": round(
                min(abs(estimates[best] - phase), 1 - abs(estimates[best] - phase)), 6
            ),
            "precision": precision,
            "probabilities": [round(float(p), 6) for p in probabilities],
        }

    if algorithm == "simon":
        period = _require_int(parameters, "period", 9, 1, 15)
        oracle, _ = algo.simon_period_oracle(period, 4)
        result = algo.simon_algorithm(oracle, 4)
        return {
            "algorithm": algorithm,
            "hidden_period": format(period, "04b"),
            "recovered": format(result.period, "04b"),
            "exact": result.period == period,
            "samples": [format(z, "04b") for z in result.samples],
            "oracle_queries": 1,
        }

    if algorithm == "teleport":
        seed = _require_int(parameters, "seed", 0, 0, 1000)
        vector = np.array([1, 1j], dtype=complex) / math.sqrt(2)
        result = algo.teleport_state(vector, seed=seed)
        return {
            "algorithm": algorithm,
            "fidelity": round(result.fidelity, 9),
            "success": result.success,
            "measured_bits": list(result.measured_bits),
        }

    if algorithm == "factor":
        n = _require_int(parameters, "n", 15, 4, 9999)
        factors = algo.shors_factoring(n)
        return {
            "algorithm": algorithm,
            "n": n,
            "factors": factors,
            "verified": bool(factors) and factors[0] * factors[1] == n,
        }

    if algorithm == "qaoa":
        n = _require_int(parameters, "qubits", 4, 2, 6)
        p = _require_int(parameters, "p", 1, 1, 3)
        iterations = _require_int(parameters, "iterations", 60, 5, 300)
        edges = _ring_graph(n)
        result = algo.qaoa_maxcut(edges, n, p_layers=p, max_iterations=iterations)
        optimal = max(
            algo.maxcut_value(format(i, f"0{n}b"), edges) for i in range(1 << n)
        )
        return {
            "algorithm": algorithm,
            "best_bitstring": result.best_bitstring,
            "cut_value": result.best_value,
            "optimal_cut": optimal,
            "matches_optimal": result.best_value == optimal,
            "p_layers": p,
            "iterations": iterations,
        }

    if algorithm == "vqe":
        seed = _require_int(parameters, "seed", 7, 0, 1000)
        result = algo.vqe_h2_ground_energy(iterations=150, seed=seed, restarts=8)
        return {
            "algorithm": algorithm,
            "energy": round(result["energy"], 8),
            "exact_ground_energy": result["exact_ground_energy"],
            "energy_error": round(
                abs(result["energy"] - result["exact_ground_energy"]), 8
            ),
        }

    raise ValueError(f"unknown algorithm {algorithm!r}")


API_ENDPOINTS: tuple[dict[str, str], ...] = (
    {"method": "GET", "path": "/api/health", "description": "Liveness probe with dataset sizes."},
    {"method": "GET", "path": "/api/papers", "description": "List papers. Filters: q, org_type, difficulty, algorithm_family, hardware_platform, tag, organisation, year_min, year_max. Sort: sort, order. Pagination: page, per_page."},
    {"method": "GET", "path": "/api/papers/<id>", "description": "Fetch one paper by id."},
    {"method": "GET", "path": "/api/papers/facets", "description": "Filter values and counts."},
    {"method": "GET", "path": "/api/projects", "description": "List projects. Filters: category, difficulty, implemented."},
    {"method": "GET", "path": "/api/projects/<id>", "description": "Fetch one project by id."},
    {"method": "GET", "path": "/api/analytics", "description": "Combined distribution across both datasets."},
    {"method": "GET", "path": "/api/analytics/papers", "description": "Paper distribution only."},
    {"method": "GET", "path": "/api/analytics/projects", "description": "Project distribution only."},
    {"method": "POST", "path": "/lab/run", "description": "Run one simulator experiment. Body: {\"algorithm\": ..., \"parameters\": {...}}."},
)


app = create_app()


if __name__ == "__main__":
    settings = config.config
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
