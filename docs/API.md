# API reference

Base URL: `http://127.0.0.1:5000`

All endpoints return JSON. Errors return `{"error": "..."}` with a 4xx or 5xx
status.

---

## GET /api/health

Liveness probe.

```json
{
  "status": "ok",
  "papers": 25,
  "projects": 15
}
```

---

## GET /api/papers

List papers with filtering, search, sorting and pagination.

### Query parameters

| Parameter | Type | Notes |
| --- | --- | --- |
| `q` | string | Free text over title, abstract, authors, tags, organisation, venue |
| `org_type` | string | `institution`, `company` or `independent` |
| `difficulty` | string | `introductory`, `intermediate`, `advanced`, `research` |
| `algorithm_family` | string | Case-insensitive exact match |
| `hardware_platform` | string | Case-insensitive exact match |
| `tag` | string | Case-insensitive tag match |
| `organisation` | string | Case-insensitive substring match |
| `year_min` | int | Inclusive |
| `year_max` | int | Inclusive |
| `sort` | string | `year` (default), `title`, `organisation`, `id` |
| `order` | string | `desc` (default) or `asc` |
| `page` | int | 1-based, default 1 |
| `per_page` | int | Default 10, clamped to 100 |

An unknown `org_type` or `difficulty` returns 400.

Supplying `q` switches to ranked search and applies `MAX_SEARCH_RESULTS`.

### Response

```json
{
  "count": 2,
  "total": 8,
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_items": 8,
    "total_pages": 1,
    "has_prev": false,
    "has_next": false
  },
  "filters": {"org_type": "company"},
  "papers": [
    {
      "id": "p004",
      "title": "Quantum Supremacy Using a Programmable Superconducting Processor",
      "authors": ["Frank Arute", "Kunal Arya"],
      "author_summary": "Frank Arute, Kunal Arya",
      "authors_truncated": false,
      "organisation": "Google Quantum AI",
      "org_type": "company",
      "year": 2019,
      "venue": "Nature",
      "doi": "10.1038/s41586-019-1666-5",
      "arxiv": "1910.11333",
      "abstract": "...",
      "tags": ["quantum-supremacy", "superconducting"],
      "difficulty": "research",
      "algorithm_family": "benchmarking",
      "hardware_platform": "superconducting",
      "link": "https://doi.org/10.1038/s41586-019-1666-5"
    }
  ]
}
```

Search ranking weights: title 10, tag 4, author 3, organisation 2, abstract 1.

---

## GET /api/papers/&lt;id&gt;

One paper. Returns 404 with `{"error": "no paper with id '...'"}` if unknown.

---

## GET /api/papers/facets

Filter values and their counts, for populating a filter UI.

```json
{
  "org_type": {"values": ["institution", "company", "independent"], "counts": {"...": 0}},
  "difficulty": {"values": ["..."], "counts": {"...": 0}},
  "algorithm_family": {"values": ["..."], "counts": {"...": 0}},
  "hardware_platform": {"values": ["..."], "counts": {"...": 0}},
  "tags": {"values": ["..."], "counts": {"...": 0}},
  "organisations": {"values": ["..."], "counts": {"...": 0}},
  "organisations_by_type": {"institution": ["..."]},
  "year_range": {"min": 1994, "max": 2021}
}
```

---

## GET /api/projects

| Parameter | Type | Notes |
| --- | --- | --- |
| `category` | string | Case-insensitive exact match |
| `difficulty` | string | One of the four levels |
| `implemented` | string | `true` or `false` |

Each record carries `module`, `test_module` and `entry_point` when implemented,
and `url` when external, plus a `source` field that picks the right one.

---

## GET /api/projects/&lt;id&gt;

One project. Returns 404 with an error object if unknown.

---

## GET /api/analytics

Combined distribution across both datasets: totals, counts per facet, the
organisation leaderboard, the tag leaderboard and the year span.

## GET /api/analytics/papers

Paper distribution only.

## GET /api/analytics/projects

Project distribution only, including `implemented` and `external` counts.

---

## POST /lab/run

Run one simulator experiment.

The body **must** be a JSON object with a non-empty `algorithm` string and an
optional `parameters` object. A malformed body is rejected with 400 rather than
silently falling back to defaults, so a client bug cannot quietly run a
different experiment.

### Parameters by algorithm

| `algorithm` | Parameters | Result keys |
| --- | --- | --- |
| `bell` | none | `state`, `fidelity_phi_plus` |
| `ghz` | `qubits` 2-10 | `state` |
| `grover` | `qubits` 2-8, `marked` | `found`, `target`, `success_probability`, `iterations`, `oracle_calls`, `classical_query_bound` |
| `deutsch-jozsa` | `qubits` 1-8, `oracle` in `parity`, `constant0`, `constant1` | `outcome`, `oracle_queries` |
| `bernstein-vazirani` | `qubits` 1-8, `secret` | `secret`, `recovered`, `correct`, `oracle_queries`, `classical_query_bound` |
| `qft` | `qubits` 1-6, `input` | `input`, `state`, `matches_exact_dft` |
| `phase-estimation` | `phase` 0-1, `precision` 1-5 | `true_phase`, `estimate`, `estimation_error`, `probabilities` |
| `simon` | `period` 1-15 | `hidden_period`, `recovered`, `exact`, `samples` |
| `teleport` | `seed` | `fidelity`, `success`, `measured_bits` |
| `factor` | `n` 4-9999 | `n`, `factors`, `verified` |
| `qaoa` | `qubits` 2-6, `p` 1-3, `iterations` | `best_bitstring`, `cut_value`, `optimal_cut`, `matches_optimal` |
| `vqe` | `seed` | `energy`, `exact_ground_energy`, `energy_error` |

Out-of-range or non-numeric parameters return 400 with an explanatory message.

### Examples

```bash
curl -X POST http://127.0.0.1:5000/lab/run \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"grover","parameters":{"qubits":4,"marked":5}}'
```

```json
{
  "algorithm": "grover",
  "found": "0101",
  "target": "0101",
  "success_probability": 0.961289,
  "iterations": 7,
  "oracle_calls": 7,
  "classical_query_bound": 16
}
```

```bash
curl -X POST http://127.0.0.1:5000/lab/run \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"vqe"}'
```

```json
{
  "algorithm": "vqe",
  "energy": -1.85563755,
  "exact_ground_energy": -1.855638,
  "energy_error": 4.5e-7
}
```
