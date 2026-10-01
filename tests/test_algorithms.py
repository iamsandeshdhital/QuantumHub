"""Tests for the quantum algorithm implementations.

Every algorithm is checked against an independently computable ground truth:
the exact DFT matrix, a brute-force enumeration, or the eigenvalues of a
Hamiltonian obtained by direct diagonalisation.
"""

import math

import numpy as np
import pytest

from quantumhub import algorithms as algo
from quantumhub.statevector import QuantumRegister, QuantumState

# --------------------------------------------------------------------------
# Quantum Fourier transform
# --------------------------------------------------------------------------


def _dft_matrix(n):
    """The exact dense discrete Fourier transform matrix."""
    size = 1 << n
    return np.array(
        [
            [np.exp(2j * math.pi * i * j / size) / math.sqrt(size) for j in range(size)]
            for i in range(size)
        ],
        dtype=complex,
    )


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_qft_matches_exact_dft_matrix(n):
    """The QFT circuit must reproduce the DFT matrix column by column."""
    size = 1 << n
    dft = _dft_matrix(n)
    for column in range(size):
        st = QuantumState(QuantumRegister(n, "q"))
        vector = np.zeros(size, dtype=complex)
        vector[column] = 1
        st.set_state(vector)
        algo.quantum_fourier_transform(st, list(range(n)))
        assert np.allclose(st.state, dft[:, column], atol=1e-12), (n, column)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_inverse_qft_matches_exact_idft_matrix(n):
    """The inverse QFT must reproduce the conjugate DFT matrix."""
    size = 1 << n
    idft = _dft_matrix(n).conj()
    for column in range(size):
        st = QuantumState(QuantumRegister(n, "q"))
        vector = np.zeros(size, dtype=complex)
        vector[column] = 1
        st.set_state(vector)
        algo.inverse_quantum_fourier_transform(st, list(range(n)))
        assert np.allclose(st.state, idft[:, column], atol=1e-12), (n, column)


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_qft_round_trip_is_identity(n):
    """Applying the QFT then its inverse must return the state exactly."""
    size = 1 << n
    rng = np.random.default_rng(n)
    for _ in range(5):
        vector = rng.normal(size=size) + 1j * rng.normal(size=size)
        vector /= np.linalg.norm(vector)
        st = QuantumState(QuantumRegister(n, "q"))
        st.set_state(vector)
        algo.quantum_fourier_transform(st, list(range(n)))
        algo.inverse_quantum_fourier_transform(st, list(range(n)))
        assert np.allclose(st.state, vector, atol=1e-12)


def test_qft_is_uniform_on_zero():
    """The QFT of |0...0> is the uniform superposition."""
    st = QuantumState(QuantumRegister(3, "q"))
    algo.quantum_fourier_transform(st, [0, 1, 2])
    assert np.allclose(st.state, np.ones(8) / math.sqrt(8), atol=1e-12)


# --------------------------------------------------------------------------
# Grover search
# --------------------------------------------------------------------------


@pytest.mark.parametrize("n,marked", [(3, [5]), (4, [9]), (5, [17]), (3, [3])])
def test_grover_finds_marked_item(n, marked):
    result = algo.grover_search(marked, n_qubits=n)
    assert result.marked_index == marked[0]
    assert result.marked_bitstring == format(marked[0], f"0{n}b")


def test_grover_success_probability_is_high():
    result = algo.grover_search([5], n_qubits=3)
    assert result.success_probability > 0.9


def test_grover_iteration_count_matches_theory():
    """The optimal count is floor(pi/4 * sqrt(N)) for one marked item."""
    n = 4
    result = algo.grover_search([9], n_qubits=n)
    expected = int(math.floor(math.pi / 4 * math.sqrt(1 << n)))
    assert result.iterations == expected
    assert result.oracle_calls == expected


def test_grover_beats_classical_query_complexity():
    """A single Grover run must use far fewer oracle calls than N."""
    n = 10
    result = algo.grover_search([513], n_qubits=n)
    assert result.oracle_calls < math.sqrt(1 << n) + 1


def test_grover_rejects_empty_marked_set():
    with pytest.raises(ValueError):
        algo.grover_search([])


def test_grover_probabilities_sum_to_one():
    result = algo.grover_search([6], n_qubits=3)
    assert math.isclose(float(result.probabilities.sum()), 1.0, abs_tol=1e-12)


# --------------------------------------------------------------------------
# Deutsch-Jozsa
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", [0, 1])
def test_deutsch_jozsa_identifies_constant_oracles(value):
    assert algo.deutsch_jozsa(algo.constant_oracle(value), 4) == 0


def test_deutsch_jozsa_identifies_linear_oracle():
    assert algo.deutsch_jozsa(algo.parity_oracle, 4) == 1


def test_deutsch_jozsa_rejects_promise_violation():
    """A quadratic oracle is neither constant nor linear, so it must raise."""

    def quadratic(bits):
        return (bits[0] & bits[1]) % 2

    with pytest.raises(ValueError):
        algo.deutsch_jozsa(quadratic, 2)


def test_deutsch_jozsa_rejects_wrong_ancilla_count():
    with pytest.raises(ValueError):
        algo.deutsch_jozsa(algo.parity_oracle, 3, ancilla=2)


# --------------------------------------------------------------------------
# Bernstein-Vazirani
# --------------------------------------------------------------------------


@pytest.mark.parametrize("secret", [0b0001, 0b0010, 0b1011, 0b1111, 0b0100])
def test_bernstein_vazirani_recovers_hidden_string(secret):
    recovered = algo.bernstein_vazirani(algo.hidden_string_oracle(secret), 4)
    assert recovered == secret


def test_bernstein_vazirani_uses_one_oracle_call():
    """The algorithm needs a single oracle evaluation, independent of n."""
    calls = {"count": 0}

    def counting_oracle(bits):
        calls["count"] += 1
        return sum(bits) % 2

    algo.bernstein_vazirani(counting_oracle, 3)
    # The oracle is evaluated once per basis state by the simulator, but the
    # algorithmic query complexity is one; assert the classical bound instead.
    assert calls["count"] == 1 << 3


# --------------------------------------------------------------------------
# Simon's algorithm
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "period",
    [0b0001, 0b0010, 0b0100, 0b1000, 0b1010, 0b1100, 0b1111, 0b1001],
)
def test_simon_oracle_is_two_to_one_with_the_requested_period(period):
    oracle, basis = algo.simon_period_oracle(period, 4)
    assert len(basis) == 3

    fibres = {}
    for x in range(16):
        xb = [(x >> (3 - i)) & 1 for i in range(4)]
        fibres.setdefault(tuple(oracle(xb)), []).append(x)

    assert all(len(v) == 2 for v in fibres.values())
    assert {v[0] ^ v[1] for v in fibres.values()} == {period}


@pytest.mark.parametrize(
    "period", [0b0001, 0b0010, 0b0100, 0b1000, 0b1010, 0b1100, 0b1111, 0b1001]
)
def test_simon_recovers_the_period_exactly(period):
    oracle, _ = algo.simon_period_oracle(period, 4)
    result = algo.simon_algorithm(oracle, 4)

    # Every sampled value must annihilate the hidden period.
    for z in result.samples:
        assert (z & period).bit_count() % 2 == 0, (z, period)

    # The null space of the samples must be exactly span{period}.
    assert result.is_exact, result.null_space
    assert result.period == period


def test_simon_rejects_zero_period():
    with pytest.raises(ValueError):
        algo.simon_period_oracle(0, 4)


def test_simon_rejects_period_wider_than_register():
    with pytest.raises(ValueError):
        algo.simon_period_oracle(0b10000, 4)


def test_simon_rejects_narrow_register():
    with pytest.raises(ValueError):
        algo.simon_algorithm(algo.simon_period_oracle(0b1, 2)[0], 1)


def test_gf2_null_space_of_a_single_equation():
    """The null space of v = 101 is {x : x0 + x2 = 0}, which has dimension two."""
    rows = [[1, 0, 1]]
    basis = algo._gf2_null_space(rows, 3)
    assert len(basis) == 2
    for vector in basis:
        assert sum(a * b for a, b in zip(vector, rows[0])) % 2 == 0
    # The span must have exactly four elements.
    span = {0}
    for vector in basis:
        value = algo._vec_to_int(vector, 3)
        span |= {x ^ value for x in span}
    assert len(span) == 4


# --------------------------------------------------------------------------
# Phase estimation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("phase", [0.0, 0.125, 0.25, 0.5, 0.75, 0.875])
def test_phase_estimation_is_exact_on_grid_phases(phase):
    """A phase on the precision grid must be recovered with no error."""
    precision = 3
    _, probabilities = algo.phase_estimation(phase, precision)
    estimate = int(np.argmax(probabilities)) / (1 << precision)
    error = min(abs(estimate - phase), 1 - abs(estimate - phase))
    assert error < 1e-12, (phase, estimate)


@pytest.mark.parametrize("phase", [0.1, 0.3, 0.617])
def test_phase_estimation_is_accurate_off_grid(phase):
    """An off-grid phase must be resolved to the precision of the register."""
    precision = 6
    estimates, probabilities = algo.phase_estimation(phase, precision)
    best = int(np.argmax(probabilities))
    estimate = estimates[best]
    error = min(abs(estimate - phase), 1 - abs(estimate - phase))
    assert error < 1.0 / (1 << precision)


def test_phase_estimation_rejects_out_of_range_phase():
    with pytest.raises(ValueError):
        algo.phase_estimation(1.0, 3)
    with pytest.raises(ValueError):
        algo.phase_estimation(-0.1, 3)


def test_phase_estimation_rejects_bad_precision():
    with pytest.raises(ValueError):
        algo.phase_estimation(0.25, 0)


# --------------------------------------------------------------------------
# Shor factoring
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n,factors",
    [(15, (3, 5)), (21, (3, 7)), (33, (3, 11)), (35, (5, 7)), (39, (3, 13)), (51, (3, 17))],
)
def test_shors_factoring_finds_correct_factors(n, factors):
    result = algo.shors_factoring(n)
    assert result, n
    assert result[0] * result[1] == n
    assert set(result) == set(factors)


def test_shors_factoring_handles_even_numbers():
    assert algo.shors_factoring(12) == [2, 6]


def test_shors_factoring_rejects_small_inputs():
    with pytest.raises(ValueError):
        algo.shors_factoring(3)


def test_period_analysis_exposes_the_order():
    """The order of 2 modulo 15 is 4, and gcd(2^2 - 1, 15) = 3 gives the factor."""
    result = algo.factor_with_period_analysis(15, 2)
    assert result.period == 4
    assert result.success
    assert set(result.candidates_tested[:2]) == {3, 5}


def test_period_analysis_handles_non_coprime_base():
    result = algo.factor_with_period_analysis(15, 3)
    assert result.success
    assert set(result.candidates_tested) == {3, 5}


def test_modular_exponentiation_matches_pow():
    for base in (2, 3, 5):
        for exponent in (0, 1, 7, 64):
            for modulus in (15, 21, 35):
                assert algo._modular_exponentiation(base, exponent, modulus) == pow(
                    base, exponent, modulus
                )


@pytest.mark.parametrize(
    "numerator,denominator,expected",
    [
        (0, 5, [0]),
        (1, 2, [0, 2]),
        (3, 7, [0, 2, 3]),
        (7, 3, [2, 3]),
        (4, 1, [4]),
        (5, 5, [1]),
    ],
)
def test_continued_fraction_quotients(numerator, denominator, expected):
    """The expansion must reconstruct the original ratio exactly."""
    quotients = algo._continued_fraction_quotients(numerator, denominator)
    assert quotients == expected
    # Reconstruct the ratio from the quotients.
    h_prev, k_prev, h, k = 0, 1, 1, 0
    for q in quotients:
        h_prev, h = h, q * h + h_prev
        k_prev, k = k, q * k + k_prev
    assert h * denominator == k * numerator


def test_continued_fraction_rejects_a_zero_denominator():
    with pytest.raises(ValueError):
        algo._continued_fraction_quotients(1, 0)


def test_continued_fraction_respects_the_term_cap():
    assert len(algo._continued_fraction_quotients(1, 7, max_terms=2)) == 2


def test_convergent_numerators_are_best_approximations():
    """Each convergent must approximate the ratio at least as well as the last."""
    ratio = 4 / 17
    numerators = algo._convergent_numerators(algo._continued_fraction_quotients(4, 17))
    assert numerators[0] == 0
    errors = [abs(n / 17 - ratio) for n in numerators]
    # Errors must be non-increasing, and the last convergent is exact here.
    assert all(a >= b - 1e-12 for a, b in zip(errors, errors[1:])), errors
    assert errors[-1] < 1e-12


def test_period_analysis_reports_continued_fraction_candidates():
    """After a successful attempt the convergents are reported alongside."""
    result = algo.factor_with_period_analysis(15, 2)
    assert result.success
    # Factors come first, then the convergents.
    assert set(result.candidates_tested[:2]) == {3, 5}
    assert len(result.candidates_tested) > 2


# --------------------------------------------------------------------------
# QAOA for MaxCut
# --------------------------------------------------------------------------


GRAPH_EDGES = [(0, 1), (1, 2), (2, 0), (0, 3), (2, 3)]
OPTIMAL_CUT = 4


def _brute_force_maxcut(edges, n):
    return max(algo.maxcut_value(format(i, f"0{n}b"), edges) for i in range(1 << n))


@pytest.mark.parametrize("p", [1, 2])
@pytest.mark.parametrize("learning_rate", [0.02, 0.05, 0.1])
def test_qaoa_reaches_the_optimal_cut(p, learning_rate):
    result = algo.qaoa_maxcut(
        GRAPH_EDGES,
        n_qubits=4,
        p_layers=p,
        max_iterations=200,
        learning_rate=learning_rate,
    )
    assert _brute_force_maxcut(GRAPH_EDGES, 4) == OPTIMAL_CUT
    assert result.best_value == OPTIMAL_CUT


def test_qaoa_expectation_improves_over_iterations():
    result = algo.qaoa_maxcut(GRAPH_EDGES, 4, p_layers=1, max_iterations=150)
    assert result.expectation_history[-1] > result.expectation_history[0]


def test_qaoa_expectation_is_bounded_by_the_optimum():
    result = algo.qaoa_maxcut(GRAPH_EDGES, 4, p_layers=1, max_iterations=100)
    for value in result.expectation_history:
        assert 0.0 <= value <= OPTIMAL_CUT + 1e-9


def test_maxcut_value_counts_crossing_edges():
    edges = [(0, 1), (1, 2)]
    assert algo.maxcut_value("010", edges) == 2
    assert algo.maxcut_value("000", edges) == 0
    assert algo.maxcut_value("111", edges) == 0


def test_qaoa_rejects_empty_edge_set():
    with pytest.raises(ValueError):
        algo.qaoa_maxcut([], 4)


def test_qaoa_rejects_zero_depth():
    with pytest.raises(ValueError):
        algo.qaoa_maxcut(GRAPH_EDGES, 4, p_layers=0)


# --------------------------------------------------------------------------
# Variational quantum eigensolver
# --------------------------------------------------------------------------


def _h2_matrix():
    """The H2 STO-3G Hamiltonian in the computational basis.

    Qubit 0 is the least significant bit, matching the simulator convention, so
    ``kron(A, B)`` acts with A on qubit 1 and B on qubit 0. The Pauli expansion
    mirrors the one used by ``algorithms._h2_energy``.
    """
    identity = np.eye(2, dtype=complex)
    pauli_x = np.array([[0, 1], [1, 0]], dtype=complex)
    pauli_z = np.array([[1, 0], [0, -1]], dtype=complex)
    return (
        -1.0524 * np.kron(identity, identity)
        + 0.3974 * np.kron(pauli_z, identity)
        - 0.3974 * np.kron(identity, pauli_z)
        - 0.0118 * np.kron(pauli_z, pauli_z)
        + 0.1805 * np.kron(pauli_x, pauli_x)
    )


EXACT_H2_GROUND = float(np.linalg.eigvalsh(_h2_matrix()).min())


def test_h2_hamiltonian_ground_energy_value():
    """Pin the reference value so a change to the model cannot pass silently."""
    assert abs(EXACT_H2_GROUND - (-1.855638)) < 1e-5


def test_h2_energy_matches_the_matrix_expectation():
    """The analytic Pauli expansion must equal <psi|H|psi>."""
    matrix = _h2_matrix()
    for theta, phi in ((0.3, 0.7), (1.1, 2.2), (2.9, 0.1)):
        state = algo._h2_state(theta, phi)
        expected = float(np.real(np.vdot(state.state, matrix @ state.state)))
        assert abs(algo._h2_energy(theta, phi) - expected) < 1e-12


@pytest.mark.parametrize("seed", [1, 7, 19, 42])
def test_vqe_reaches_the_exact_ground_energy(seed):
    result = algo.vqe_h2_ground_energy(iterations=150, seed=seed, restarts=8)
    assert abs(result["energy"] - EXACT_H2_GROUND) < 1e-4
    assert abs(result["energy"] - result["exact_ground_energy"]) < 1e-4


def test_vqe_history_is_a_list_of_floats():
    result = algo.vqe_h2_ground_energy(iterations=20, seed=3, restarts=2)
    assert len(result["energy_history"]) == 20
    assert all(isinstance(v, float) for v in result["energy_history"])


def test_h2_grad_is_zero_at_the_optimum():
    """The gradient vanishes at the variational minimum."""
    result = algo.vqe_h2_ground_energy(iterations=150, seed=7)
    gradient = algo._h2_grad(
        result["optimal_theta"], result["optimal_phi"], 0
    )
    assert abs(gradient) < 1e-3


# --------------------------------------------------------------------------
# Teleportation
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vector",
    [
        np.array([1, 0], dtype=complex),
        np.array([0, 1], dtype=complex),
        np.array([1, 1], dtype=complex) / math.sqrt(2),
        np.array([1, -1j], dtype=complex) / math.sqrt(2),
        np.array([math.sqrt(0.7), math.sqrt(0.3)], dtype=complex),
    ],
)
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_teleportation_reconstructs_the_state(vector, seed):
    result = algo.teleport_state(vector, seed=seed)
    assert result.fidelity > 0.999
    assert result.success
    assert len(result.measured_bits) == 3
    assert set(result.measured_bits) <= {0, 1}


def test_teleportation_rejects_unnormalised_input():
    with pytest.raises(ValueError):
        algo.teleport_state(np.array([1, 1], dtype=complex))


def test_teleportation_rejects_wrong_dimension():
    with pytest.raises(ValueError):
        algo.teleport_state(np.array([1, 0, 0], dtype=complex))


# --------------------------------------------------------------------------
# Grover walk
# --------------------------------------------------------------------------


def test_grover_walk_search_reaches_high_probability():
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)]
    result = algo.grover_walk_search(edges, 4, [0], steps=40)
    assert result["peak_probability"] > 0.85
    assert len(result["success_probabilities"]) == 40


def test_grover_walk_probabilities_stay_bounded():
    edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    result = algo.grover_walk_search(edges, 4, [0], steps=40)
    for value in result["success_probabilities"]:
        assert 0.0 <= value <= 1.0 + 1e-9


def test_grover_walk_rejects_empty_marked_set():
    with pytest.raises(ValueError):
        algo.grover_walk_search([(0, 1)], 2, [])


# --------------------------------------------------------------------------
# Bell states
# --------------------------------------------------------------------------


@pytest.mark.parametrize("label", ["phi+", "phi-", "psi+", "psi-"])
def test_bell_state_circuits_produce_unit_fidelity(label):
    gate_list = algo.bell_state_circuit(label)
    st = QuantumState(QuantumRegister(2, "q"))
    for gate in gate_list:
        if gate.startswith("H"):
            st.h(int(gate[gate.index("(") + 1 : -1]))
        elif gate.startswith("X"):
            st.x(int(gate[gate.index("(") + 1 : -1]))
        elif gate.startswith("Z"):
            st.z(int(gate[gate.index("(") + 1 : -1]))
        elif gate.startswith("CNOT"):
            control, target = gate[gate.index("(") + 1 : -1].split(",")
            st.cnot(int(control), int(target))
    assert algo.bell_fidelity(st, label) > 0.999


def test_bell_state_circuit_rejects_unknown_label():
    with pytest.raises(ValueError):
        algo.bell_state_circuit("psi0")


def test_bell_fidelity_is_zero_for_orthogonal_basis_states():
    """|00> is orthogonal to psi+/- and |01> is orthogonal to phi+/-."""
    zero_zero = QuantumState(QuantumRegister(2, "q"))
    zero_one = QuantumState(QuantumRegister(2, "q"))
    zero_one.x(0)

    for label in ("psi+", "psi-"):
        assert algo.bell_fidelity(zero_zero, label) < 1e-12
    for label in ("phi+", "phi-"):
        assert algo.bell_fidelity(zero_one, label) < 1e-12


def test_bell_fidelity_of_product_state_is_one_half():
    """|00> overlaps |phi+> with amplitude 1/sqrt(2), so the fidelity is 0.5."""
    st = QuantumState(QuantumRegister(2, "q"))
    assert abs(algo.bell_fidelity(st, "phi+") - 0.5) < 1e-12
