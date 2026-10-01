# QuantumHub

A quantum computing research index paired with a working, tested
implementation you can read and run.

The index covers papers from academic institutions, commercial companies and
independent groups. The implementation is a pure-Python statevector simulator
plus sixteen algorithm checks, each verified against an independently computed
ground truth rather than a recorded expected output.

- Author: Sandesh Dhital
- Repository: <https://github.com/iamsandeshdhital/QuantumHub>
- Licence: MIT

---

## Quick start

```bash
git clone https://github.com/iamsandeshdhital/QuantumHub.git
cd QuantumHub

python -m pip install -r requirements.txt

# 1. Check the environment, layout and datasets
python verify_requirements.py

# 2. Verify the algorithms
python verify_quantum.py

# 3. Start the web application
python app.py
```

Then open <http://127.0.0.1:5000>.

For development, install the extra tooling and run the full suite:

```bash
python -m pip install -r requirements-dev.txt
make check     # verify + verify-quantum + tests
```

---

## What is actually verified

Every check compares against something computed independently, so a change to
an implementation cannot pass by agreeing with itself.

| Check | Ground truth |
| --- | --- |
| Quantum Fourier transform | The dense DFT matrix, element by element, for every basis state up to 4 qubits |
| QFT inverse and round trip | Amplitude error below 1e-12 on random states |
| Sub-register marginals | A brute-force partial trace over every qubit subset of a 4-qubit register |
| SWAP and controlled-phase | All 16 basis states at 4 qubits, for several qubit pairs |
| Toffoli | All 16 basis states at 4 qubits, for several control/target choices |
| Grover search | The marked index recovered exactly, and the iteration count compared with `floor(pi/4 * sqrt(N))` |
| Deutsch-Jozsa | Constant and linear oracles classified correctly; a quadratic oracle is rejected |
| Bernstein-Vazirani | All four 4-bit secret strings recovered exactly |
| Simon's algorithm | The generated oracle is first proved two-to-one with the intended period, then the null space is shown to be exactly `span{period}` |
| Phase estimation | Phases on the precision grid recovered with zero error |
| Shor factoring | Factors multiplied back and checked equal to the input for six composites |
| VQE for H2 | Compared with the eigenvalues of the Hamiltonian from direct diagonalisation; agrees to about 1e-7 Hartree |
| QAOA MaxCut | Compared with brute-force enumeration of all assignments |
| Teleportation | Fidelity above 0.999 across 32 runs on four different input states |
| Grover walk | Probability trace bounded and peak above 0.85 |

---

## Layout

```
QuantumHub/
├── app.py                     Flask application: HTML pages, JSON API, lab endpoint
├── config.py                  Environment-driven configuration
├── quantumhub/
│   ├── statevector.py         Dense simulator, gate algebra, marginals, measurement
│   ├── algorithms.py          Sixteen algorithm implementations
│   ├── papers.py              Paper dataset, validation, filtering, search, facets
│   ├── projects.py            Project catalogue with integrity checks
│   └── analytics.py           Distribution statistics across both datasets
├── data/
│   ├── papers.json            25 papers from institutions, companies, independent groups
│   └── projects.json          10 implementations here, 5 external references
├── templates/                 Jinja2 templates
├── static/                    CSS and a small progressive-enhancement script
├── tests/                     423 tests
├── docs/                      Architecture, API reference, data model
├── verify_requirements.py     Environment, layout and dataset check
├── verify_quantum.py          Standalone algorithm verification
├── pyproject.toml             Packaging, pytest, coverage and ruff configuration
├── Makefile                   Common tasks
├── Dockerfile                 Container image
└── .github/workflows/ci.yml   Tests on Python 3.10, 3.11 and 3.12
```

---

## The web application

| Page | What it does |
| --- | --- |
| `/` | Headline statistics and distribution charts |
| `/papers` | Filterable, searchable, sortable, paginated paper list |
| `/papers/<id>` | Full record with DOI or arXiv link and related papers |
| `/projects` | Project catalogue, filterable by category, difficulty and origin |
| `/projects/<id>` | What a project is, why it is hard, how it is verified |
| `/lab` | Interactive simulator, calling the same code the tests exercise |
| `/analytics` | Distribution across every facet |
| `/api-docs` | API reference with copy-pasteable examples |
| `/about` | Verification approach, data provenance, scope limits |

### API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Liveness probe with dataset sizes |
| GET | `/api/papers` | List papers. Filters: `q`, `org_type`, `difficulty`, `algorithm_family`, `hardware_platform`, `tag`, `organisation`, `year_min`, `year_max`. Sort: `sort`, `order`. Pagination: `page`, `per_page` |
| GET | `/api/papers/<id>` | One paper |
| GET | `/api/papers/facets` | Filter values and counts |
| GET | `/api/projects` | List projects. Filters: `category`, `difficulty`, `implemented` |
| GET | `/api/projects/<id>` | One project |
| GET | `/api/analytics` | Combined distribution |
| GET | `/api/analytics/papers` | Paper distribution |
| GET | `/api/analytics/projects` | Project distribution |
| POST | `/lab/run` | Run one experiment |

```bash
curl "http://127.0.0.1:5000/api/papers?org_type=company&per_page=2"

curl -X POST http://127.0.0.1:5000/lab/run \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"grover","parameters":{"qubits":4,"marked":5}}'
```

---

## Algorithms implemented

| Function | Algorithm |
| --- | --- |
| `quantum_fourier_transform` | QFT as a gate sequence matching the DFT matrix |
| `inverse_quantum_fourier_transform` | Inverse QFT |
| `phase_estimation` | Phase estimation by kickback plus inverse QFT |
| `grover_search` | Grover search with amplitude amplification |
| `grover_walk_search` | Continuous-time quantum walk search |
| `deutsch_jozsa` | Deutsch-Jozsa against a real black-box oracle |
| `bernstein_vazirani` | Bernstein-Vazirani hidden string recovery |
| `simon_algorithm` | Simon's period finding with a GF(2) null-space solver |
| `shors_factoring` | Factoring by order finding and gcd post-processing |
| `factor_with_period_analysis` | One order-finding attempt, exposing the period and continued fractions |
| `qaoa_maxcut` | QAOA for MaxCut with parameter-shift gradients |
| `vqe_h2_ground_energy` | VQE for the H2 Hamiltonian with restarts |
| `teleport_state` | Quantum teleportation with feed-forward correction |
| `bell_state_circuit` | Bell state construction |
| `bell_fidelity` | Fidelity against a Bell target |
| `simon_period_oracle` | Builds a two-to-one oracle for any chosen period |

---

## Honest scope notes

- **The dataset is a teaching sample, not a bibliography.** Bibliographic
  fields were compiled from the published record. Check the linked DOI or arXiv
  identifier before citing anything here.
- **Citation counts are omitted** because they change over time and reporting
  them accurately needs a live bibliographic source.
- **`difficulty` and `hardware_platform` are editorial classifications**, not
  claims made by the papers.
- **Dense simulation is memory-bound.** The simulator refuses to allocate more
  than 24 qubits. That is a limit of this code, not a statement about hardware.
- **Shor's order finding runs classically here.** Exact simulation makes the
  quantum step unnecessary at these sizes. The post-processing that runs on
  hardware is implemented and tested.
- **The project is unaffiliated** with any organisation it references.

---

## Data integrity

The loader validates the dataset at startup and refuses to start on:

- a malformed record, a missing required field, or a duplicate id
- an unknown organisation type or difficulty level
- a malformed DOI or arXiv identifier, or a record with neither
- an author entry that still looks like an unfilled placeholder

A test also asserts that every implemented project names a module that imports
and an entry point that exists, and a test file that is present. This is what
stops the catalogue from drifting away from the code.

---

## Development

```bash
make help        # list tasks
make dev         # install development dependencies
make test        # test suite with coverage
make coverage    # HTML coverage report
make lint        # ruff
make verify      # environment, layout and dataset check
make verify-quantum
```

Current state: 423 tests, 92 percent statement and branch coverage.

---

## Licence

MIT. See [LICENSE](LICENSE).

The indexed papers are the work of their authors. This project is not affiliated
with any of the organisations it references.
