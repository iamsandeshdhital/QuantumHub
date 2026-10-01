"""Run the quantum algorithm verification suite and print a report.

This is a standalone script so you can check the implementations without
installing a test framework. It exercises the same code paths as the pytest
suite, and every check compares against an independently computed ground truth.

Usage:

    python verify_quantum.py
"""

from __future__ import annotations

import math
import sys
import traceback
from collections.abc import Callable

import numpy as np

from quantumhub import algorithms as algo
from quantumhub.statevector import QuantumRegister, QuantumState

ATOL = 1e-9


def _dft_matrix(n: int) -> np.ndarray:
    """The exact dense discrete Fourier transform matrix."""
    size = 1 << n
    return np.array(
        [[np.exp(2j * math.pi * i * j / size) / math.sqrt(size) for j in range(size)] for i in range(size)],
        dtype=complex,
    )


# --------------------------------------------------------------------------
# Simulator
# --------------------------------------------------------------------------


def check_bell_state() -> str:
    state = QuantumState(QuantumRegister(2, "bell"))
    state.h(0)
    state.cnot(0, 1)
    probs = state.probabilities()
    assert abs(probs[0] - 0.5) < ATOL and abs(probs[3] - 0.5) < ATOL
    assert probs[1] < ATOL and probs[2] < ATOL
    return f"|00>={probs[0]:.4f} |11>={probs[3]:.4f} entropy={state.entropy():.4f} bits"


def check_toffoli() -> str:
    state = QuantumState(QuantumRegister(3, "ghz"))
    state.x(0)
    state.x(1)
    state.toffoli(0, 1, 2)
    assert state.probability(0b111) > 0.999
    return f"P(|111>)={state.probability(0b111):.4f}"


def check_swap_on_all_basis_states() -> str:
    """SWAP must exchange exactly the addressed qubits for every basis state."""
    n = 4
    for a, b in [(0, 1), (1, 2), (0, 3), (2, 3), (1, 3)]:
        for src in range(1 << n):
            state = QuantumState(QuantumRegister(n, "q"))
            state.set_state(np.eye(1 << n, dtype=complex)[src])
            state.swap(a, b)
            ba, bb = (src >> a) & 1, (src >> b) & 1
            expected = src ^ ((1 << a) | (1 << b)) if ba != bb else src
            assert abs(state.state[expected] - 1) < ATOL, (a, b, src)
    return "5 qubit pairs x 16 basis states"


def check_marginals() -> str:
    """Marginals must agree with a brute-force partial trace."""
    import itertools

    n = 4
    rng = np.random.default_rng(0)
    state = QuantumState(QuantumRegister(n, "q"))
    vector = rng.normal(size=1 << n) + 1j * rng.normal(size=1 << n)
    vector /= np.linalg.norm(vector)
    state.set_state(vector)

    checked = 0
    for size in range(1, n + 1):
        for qubits in itertools.combinations(range(n), size):
            got = state.marginal(list(qubits))
            want = np.zeros(1 << (max(qubits) + 1))
            probs = state.probabilities()
            for i in range(state.dim):
                index = 0
                for q in qubits:
                    index |= ((i >> q) & 1) << q
                want[index] += probs[i]
            assert np.allclose(got, want, atol=1e-12), qubits
            checked += 1
    return f"{checked} qubit subsets match brute force"


# --------------------------------------------------------------------------
# Algorithms
# --------------------------------------------------------------------------


def check_qft_against_dft() -> str:
    for n in (1, 2, 3, 4):
        dft = _dft_matrix(n)
        for column in range(1 << n):
            state = QuantumState(QuantumRegister(n, "qft"))
            vector = np.zeros(1 << n, dtype=complex)
            vector[column] = 1
            state.set_state(vector)
            algo.quantum_fourier_transform(state, list(range(n)))
            assert np.allclose(state.state, dft[:, column], atol=1e-12), (n, column)
    return "n=1..4, every basis state matches the DFT matrix"


def check_qft_round_trip() -> str:
    worst = 0.0
    for n in (1, 2, 3, 4):
        rng = np.random.default_rng(n)
        for _ in range(5):
            vector = rng.normal(size=1 << n) + 1j * rng.normal(size=1 << n)
            vector /= np.linalg.norm(vector)
            state = QuantumState(QuantumRegister(n, "qft"))
            state.set_state(vector)
            algo.quantum_fourier_transform(state, list(range(n)))
            algo.inverse_quantum_fourier_transform(state, list(range(n)))
            worst = max(worst, float(np.abs(state.state - vector).max()))
    assert worst < 1e-12, worst
    return f"worst amplitude error {worst:.2e}"


def check_grover() -> str:
    details = []
    for n, marked in ((3, 5), (4, 9), (5, 17)):
        result = algo.grover_search([marked], n_qubits=n)
        assert result.marked_index == marked
        expected = int(math.floor(math.pi / 4 * math.sqrt(1 << n)))
        assert result.iterations == expected
        details.append(f"n={n} p={result.success_probability:.4f}")
    return ", ".join(details)


def check_deutsch_jozsa() -> str:
    constant0 = algo.deutsch_jozsa(algo.constant_oracle(0), 4)
    constant1 = algo.deutsch_jozsa(algo.constant_oracle(1), 4)
    linear = algo.deutsch_jozsa(algo.parity_oracle, 4)
    assert (constant0, constant1, linear) == (0, 0, 1)
    return f"constant0={constant0} constant1={constant1} parity={linear}"


def check_bernstein_vazirani() -> str:
    for secret in (0b0001, 0b0010, 0b1011, 0b1111):
        assert algo.bernstein_vazirani(algo.hidden_string_oracle(secret), 4) == secret
    return "4 secret strings recovered exactly"


def check_simon() -> str:
    periods = []
    for period in (0b0001, 0b0010, 0b0100, 0b1000, 0b1010, 0b1100, 0b1111, 0b1001):
        oracle, _ = algo.simon_period_oracle(period, 4)

        fibres = {}
        for x in range(16):
            xb = [(x >> (3 - i)) & 1 for i in range(4)]
            fibres.setdefault(tuple(oracle(xb)), []).append(x)
        assert all(len(v) == 2 for v in fibres.values()), period
        assert {v[0] ^ v[1] for v in fibres.values()} == {period}, period

        result = algo.simon_algorithm(oracle, 4)
        assert result.is_exact, (period, result.null_space)
        assert result.period == period, (period, result.period)
        periods.append(format(period, "04b"))
    return f"{len(periods)} periods, oracles 2-to-1, null space exact"


def check_phase_estimation() -> str:
    for phase in (0.0, 0.125, 0.25, 0.5, 0.75, 0.875):
        estimates, probabilities = algo.phase_estimation(phase, 3)
        estimate = estimates[int(np.argmax(probabilities))]
        error = min(abs(estimate - phase), 1 - abs(estimate - phase))
        assert error < ATOL, (phase, estimate)
    return "6 phases resolved exactly"


def check_shors_factoring() -> str:
    results = []
    for n in (15, 21, 33, 35, 39, 51):
        factors = algo.shors_factoring(n)
        assert factors and factors[0] * factors[1] == n, (n, factors)
        results.append(f"{n}={factors[0]}x{factors[1]}")
    return ", ".join(results)


def check_vqe() -> str:
    identity = np.eye(2, dtype=complex)
    px = np.array([[0, 1], [1, 0]], dtype=complex)
    pz = np.array([[1, 0], [0, -1]], dtype=complex)
    matrix = (
        -1.0524 * np.kron(identity, identity)
        + 0.3974 * np.kron(pz, identity)
        - 0.3974 * np.kron(identity, pz)
        - 0.0118 * np.kron(pz, pz)
        + 0.1805 * np.kron(px, px)
    )
    exact = float(np.linalg.eigvalsh(matrix).min())

    result = algo.vqe_h2_ground_energy(iterations=150, seed=7, restarts=8)
    error = abs(result["energy"] - exact)
    assert error < 1e-4, (result["energy"], exact)
    return f"E={result['energy']:.6f} exact={exact:.6f} error={error:.2e}"


def check_qaoa() -> str:
    edges = [(0, 1), (1, 2), (2, 0), (0, 3), (2, 3)]
    optimal = max(algo.maxcut_value(format(i, "04b"), edges) for i in range(16))
    details = []
    for p in (1, 2):
        result = algo.qaoa_maxcut(edges, 4, p_layers=p, max_iterations=200)
        assert result.best_value == optimal, (p, result.best_value, optimal)
        details.append(f"p={p} cut={result.best_value}")
    return f"optimal={optimal}, " + ", ".join(details)


def check_teleportation() -> str:
    worst = 1.0
    for vector in (
        np.array([1, 0], dtype=complex),
        np.array([0, 1], dtype=complex),
        np.array([1, 1], dtype=complex) / math.sqrt(2),
        np.array([1, -1j], dtype=complex) / math.sqrt(2),
    ):
        for seed in range(8):
            result = algo.teleport_state(vector, seed=seed)
            assert result.fidelity > 0.999, (vector, seed, result.fidelity)
            worst = min(worst, result.fidelity)
    return f"32 runs, worst fidelity {worst:.6f}"


def check_grover_walk() -> str:
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)]
    result = algo.grover_walk_search(edges, 4, [0], steps=40)
    assert result["peak_probability"] > 0.85
    return f"peak={result['peak_probability']:.4f}"


CHECKS: list[tuple[str, Callable[[], str]]] = [
    ("Bell state", check_bell_state),
    ("Toffoli", check_toffoli),
    ("SWAP on all basis states", check_swap_on_all_basis_states),
    ("Sub-register marginals", check_marginals),
    ("QFT against the DFT", check_qft_against_dft),
    ("QFT round trip", check_qft_round_trip),
    ("Grover search", check_grover),
    ("Deutsch-Jozsa", check_deutsch_jozsa),
    ("Bernstein-Vazirani", check_bernstein_vazirani),
    ("Simon's algorithm", check_simon),
    ("Phase estimation", check_phase_estimation),
    ("Shor factoring", check_shors_factoring),
    ("VQE for H2", check_vqe),
    ("QAOA MaxCut", check_qaoa),
    ("Teleportation", check_teleportation),
    ("Grover walk", check_grover_walk),
]


def main() -> int:
    """Run every check and print a report."""
    print("QuantumHub algorithm verification")
    print("=" * 72)

    failures = 0
    for name, check in CHECKS:
        try:
            detail = check()
            print(f"PASS  {name:<28} {detail}")
        except Exception as exc:
            failures += 1
            print(f"FAIL  {name:<28} {type(exc).__name__}: {exc}")
            if "-v" in sys.argv:
                traceback.print_exc()

    print("=" * 72)
    print(f"{len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
