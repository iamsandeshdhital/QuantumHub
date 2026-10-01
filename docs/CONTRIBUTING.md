# Contributing

## Setup

```bash
git clone https://github.com/iamsandeshdhital/QuantumHub.git
cd QuantumHub
python -m pip install -r requirements-dev.txt
python verify_requirements.py
```

## Before you open a pull request

```bash
make check
```

That runs the environment check, the algorithm verification and the full test
suite with coverage. All three must pass. `make lint` must also be clean.

## Adding a paper

1. Append a record to `data/papers.json` with the next free `id`. See
   [the data model](docs/DATA_MODEL.md) for every field and the validation
   rules.
2. Fill in the bibliographic fields from the published record. Do not guess.
3. Run `python verify_requirements.py` and
   `python -m pytest tests/test_repository.py -q`.

The dataset must keep all three organisation types represented, and the loader
rejects an author entry that still looks like an unfilled placeholder.

## Adding a project

1. Append a record to `data/projects.json` with the next free `id`.
2. If the code is in this repository, set `implemented` to true, name the
   `module`, name an `entry_point` that actually exists, and point
   `test_module` at a file that exists. Describe the difficulty concretely in
   `why_hard`, and state in `correctness_evidence` what the code is checked
   against.
3. Run `python -m pytest tests/test_repository.py -q`.

A test imports every implemented project's module and asserts its entry point
exists. The catalogue cannot claim something the code does not provide.

## Adding an algorithm

1. Put the implementation in `quantumhub/algorithms.py`.
2. Check it against something computed independently. A recorded expected value
   is not good enough: use the DFT matrix, brute-force enumeration, an analytic
   bound, or direct diagonalisation.
3. Return a dataclass or dict carrying the quantities needed to judge the
   result.
4. Add tests in `tests/test_algorithms.py`.
5. Add an entry to `CHECKS` in `verify_quantum.py` so it runs in the standalone
   script too.
6. Add a record to `data/projects.json` describing it.

## Style

- Docstrings on every public function, class and module, with `Args`,
  `Returns` and `Raises` where relevant.
- Type hints on public interfaces.
- `ruff check .` and `ruff format .` must be clean.
- Comments should explain **why**, not restate the code.

## Commit messages

Describe the change and the reasoning, for example:

```
Fix the SWAP gate for non-adjacent qubits

apply_two_qubit only varied the qubits below the pair, so
swap(1, 2) and swap(1, 3) silently did nothing at four qubits.
Enumerating basis indices with both pair bits clear fixes it and
removes the stride assumption.
```

## Reporting bugs

Open an issue with what you ran, what you expected and what happened. If the
bug is in a quantum algorithm, include the failing ground truth so it can be
reproduced.
