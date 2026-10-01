"""Tests for the dense statevector simulator."""

import cmath
import itertools
import math

import numpy as np
import pytest

from quantumhub.statevector import (
    GateError,
    QuantumRegister,
    QuantumState,
    crz,
)

# --------------------------------------------------------------------------
# Register construction
# --------------------------------------------------------------------------


def test_register_rejects_empty():
    with pytest.raises(ValueError):
        QuantumRegister(0)


def test_register_rejects_oversized():
    with pytest.raises(GateError):
        QuantumRegister(25)


def test_register_length_and_indexing():
    reg = QuantumRegister(3, "q")
    assert len(reg) == 3
    assert reg[0].index == 0
    assert [q.index for q in reg] == [0, 1, 2]


# --------------------------------------------------------------------------
# Initial state
# --------------------------------------------------------------------------


def test_initial_state_is_zero_basis():
    st = QuantumState(QuantumRegister(3, "q"))
    assert np.allclose(st.state, [1, 0, 0, 0, 0, 0, 0, 0])
    assert math.isclose(float(np.linalg.norm(st.state)), 1.0)


def test_set_state_rejects_wrong_dimension():
    st = QuantumState(QuantumRegister(2, "q"))
    with pytest.raises(GateError):
        st.set_state(np.array([1, 0, 0], dtype=complex))


def test_set_state_rejects_unnormalised():
    st = QuantumState(QuantumRegister(1, "q"))
    with pytest.raises(GateError):
        st.set_state(np.array([1, 1], dtype=complex))


def test_reset_restores_zero_state():
    st = QuantumState(QuantumRegister(2, "q"))
    st.h(0)
    st.cnot(0, 1)
    st.reset()
    assert np.allclose(st.state, [1, 0, 0, 0])


# --------------------------------------------------------------------------
# Single-qubit gates, against the gate matrices
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["h", "x", "y", "z", "s", "sdg", "t", "tdg"])
def test_single_qubit_gates_against_matrices(name):
    from quantumhub import statevector as sv

    matrices = {
        "h": sv.H,
        "x": sv.X,
        "y": sv.Y,
        "z": sv.Z,
        "s": sv.S,
        "sdg": sv.SDG,
        "t": sv.T,
        "tdg": sv.TDG,
    }
    matrix = matrices[name]
    st = QuantumState(QuantumRegister(4, "q"))
    st.apply_single(matrix, 2)
    expected = np.kron(np.kron(np.eye(2), matrix), np.eye(4))
    assert np.allclose(st.state, expected[:, 0], atol=1e-12)


def test_hadamard_creates_superposition():
    st = QuantumState(QuantumRegister(1, "q"))
    st.h(0)
    assert np.allclose(st.state, [1 / math.sqrt(2), 1 / math.sqrt(2)], atol=1e-12)


def test_x_flips_basis_state():
    st = QuantumState(QuantumRegister(3, "q"))
    st.x(1)
    assert abs(st.probability(0b010) - 1.0) < 1e-12


def test_z_signs_the_odd_component():
    st = QuantumState(QuantumRegister(1, "q"))
    st.set_state(np.array([1, 0], dtype=complex))
    st.z(0)
    assert np.allclose(st.state, [1, 0])


def test_squares_are_identity():
    """H, S and T satisfy H*H = I, S*S = Z and T*T = S."""
    st = QuantumState(QuantumRegister(1, "q"))
    st.h(0)
    st.h(0)
    assert np.allclose(st.state, [1, 0], atol=1e-12)

    st = QuantumState(QuantumRegister(1, "q"))
    st.s(0)
    st.s(0)
    assert np.allclose(st.state, [1, 0], atol=1e-12)

    st = QuantumState(QuantumRegister(1, "q"))
    st.t(0)
    st.t(0)
    assert np.allclose(st.state, [1, 0], atol=1e-12)


def test_hxh_is_z():
    """H X H equals Z, so H|0> stays |0> and H|1> becomes -|1>."""
    st = QuantumState(QuantumRegister(1, "q"))
    st.h(0)
    st.x(0)
    st.h(0)
    assert np.allclose(st.state, [1, 0], atol=1e-12)


@pytest.mark.parametrize("theta", [0.0, 0.3, 1.0, math.pi])
def test_rx_ry_rz_are_unitary_rotations(theta):
    for gate, method in (("rx", "rx"), ("ry", "ry"), ("rz", "rz")):
        st = QuantumState(QuantumRegister(2, "q"))
        getattr(st, method)(theta, 1)
        assert math.isclose(float(np.linalg.norm(st.state)), 1.0, abs_tol=1e-12)


def test_rx_double_application_is_rx_of_double_angle():
    theta = 0.7
    a = QuantumState(QuantumRegister(1, "q"))
    a.rx(theta, 0)
    a.rx(theta, 0)
    b = QuantumState(QuantumRegister(1, "q"))
    b.rx(2 * theta, 0)
    assert np.allclose(a.state, b.state, atol=1e-12)


# --------------------------------------------------------------------------
# Two-qubit gates
# --------------------------------------------------------------------------


@pytest.mark.parametrize("pair", [(0, 1), (1, 2), (0, 2), (0, 3), (2, 3), (1, 3)])
def test_swap_acts_as_classical_swap(pair):
    """SWAP must exchange exactly the two addressed qubits and nothing else."""
    q1, q2 = pair
    n = 4
    for src in range(1 << n):
        st = QuantumState(QuantumRegister(n, "q"))
        st.set_state(np.eye(1 << n, dtype=complex)[src])
        st.swap(q1, q2)
        b1 = (src >> q1) & 1
        b2 = (src >> q2) & 1
        expected = src ^ ((1 << q1) | (1 << q2)) if b1 != b2 else src
        assert abs(st.state[expected] - 1) < 1e-12, (pair, src)


@pytest.mark.parametrize("control,target", [(0, 1), (1, 0), (1, 2), (2, 1), (0, 3), (3, 0)])
def test_cnot_flips_target_only_when_control_set(control, target):
    n = 4
    for src in range(1 << n):
        st = QuantumState(QuantumRegister(n, "q"))
        st.set_state(np.eye(1 << n, dtype=complex)[src])
        st.cnot(control, target)
        expected = src ^ (1 << target) if (src >> control) & 1 else src
        assert abs(st.state[expected] - 1) < 1e-12, (control, target, src)


@pytest.mark.parametrize("control,target", [(0, 1), (1, 0), (1, 2), (2, 1), (0, 2), (2, 0)])
def test_cz_applies_phase_only_when_both_set(control, target):
    n = 3
    for src in range(1 << n):
        theta = 0.9
        st = QuantumState(QuantumRegister(n, "q"))
        st.set_state(np.eye(1 << n, dtype=complex)[src])
        st.cp(theta, control, target)
        both = bool((src >> control) & 1) and bool((src >> target) & 1)
        expected = cmath.exp(1j * theta) if both else 1.0
        assert abs(st.state[src] - expected) < 1e-12, (control, target, src)


def test_cz_via_h_cnot_h():
    """CZ can be built from H on the target, CNOT, then H again."""
    st = QuantumState(QuantumRegister(2, "q"))
    st.set_state(np.array([0, 0, 0, 1], dtype=complex))
    st.h(1)
    st.cnot(0, 1)
    st.h(1)
    assert abs(st.state[3] + 1) < 1e-12


@pytest.mark.parametrize("q1,q2", [(0, 1), (1, 0), (1, 2), (0, 2), (2, 0), (0, 3)])
def test_two_qubit_matrix_path_matches_direct_path(q1, q2):
    """The 4x4 matrix path and the explicit-gate path must agree."""
    theta = 0.63
    n = 4
    a = QuantumState(QuantumRegister(n, "q"))
    a.apply_two_qubit(crz(theta), q1, q2)
    b = QuantumState(QuantumRegister(n, "q"))
    b.crz(theta, q1, q2)
    assert np.allclose(a.state, b.state, atol=1e-12)


def test_two_qubit_rejects_same_qubit():
    st = QuantumState(QuantumRegister(2, "q"))
    with pytest.raises(GateError):
        st.apply_two_qubit(np.eye(4, dtype=complex), 1, 1)


def test_out_of_range_qubit_rejected():
    st = QuantumState(QuantumRegister(2, "q"))
    with pytest.raises(GateError):
        st.h(2)
    with pytest.raises(GateError):
        st.cnot(0, 5)


# --------------------------------------------------------------------------
# Toffoli
# --------------------------------------------------------------------------


@pytest.mark.parametrize("c1,c2,t", [(0, 1, 2), (2, 1, 0), (0, 2, 1), (1, 2, 0), (0, 1, 3)])
def test_toffoli_flips_target_when_both_controls_set(c1, c2, t):
    n = 4
    for src in range(1 << n):
        st = QuantumState(QuantumRegister(n, "q"))
        st.set_state(np.eye(1 << n, dtype=complex)[src])
        st.toffoli(c1, c2, t)
        fire = bool((src >> c1) & 1) and bool((src >> c2) & 1)
        expected = src ^ (1 << t) if fire else src
        assert abs(st.state[expected] - 1) < 1e-12, (c1, c2, t, src)


def test_toffoli_builds_ghz_from_ones():
    st = QuantumState(QuantumRegister(3, "q"))
    st.x(0)
    st.x(1)
    st.toffoli(0, 1, 2)
    assert abs(st.probability(0b111) - 1.0) < 1e-12


def test_toffoli_rejects_repeated_qubits():
    st = QuantumState(QuantumRegister(3, "q"))
    with pytest.raises(GateError):
        st.toffoli(0, 1, 1)


# --------------------------------------------------------------------------
# Bell states and entanglement
# --------------------------------------------------------------------------


def test_bell_state_is_entangled():
    st = QuantumState(QuantumRegister(2, "q"))
    st.h(0)
    st.cnot(0, 1)
    probs = st.probabilities()
    assert abs(probs[0] - 0.5) < 1e-12
    assert abs(probs[3] - 0.5) < 1e-12
    assert probs[1] < 1e-12 and probs[2] < 1e-12


def test_bell_state_entropy_is_one_bit():
    st = QuantumState(QuantumRegister(2, "q"))
    st.h(0)
    st.cnot(0, 1)
    assert abs(st.entropy() - 1.0) < 1e-12


def test_basis_state_entropy_is_zero():
    st = QuantumState(QuantumRegister(2, "q"))
    st.x(0)
    assert st.entropy() < 1e-12


def test_product_state_entropy_equals_single_qubit_entropy():
    """A product state has the same entropy as its entangled factor."""
    st = QuantumState(QuantumRegister(2, "q"))
    st.h(1)
    assert abs(st.entropy() - 1.0) < 1e-12


def test_three_qubit_ghz_entropy_is_one_bit():
    st = QuantumState(QuantumRegister(3, "q"))
    st.h(0)
    st.cnot(0, 1)
    st.cnot(1, 2)
    assert abs(st.entropy() - 1.0) < 1e-12
    assert abs(st.probability(0b000) - 0.5) < 1e-12
    assert abs(st.probability(0b111) - 0.5) < 1e-12


# --------------------------------------------------------------------------
# Marginals
# --------------------------------------------------------------------------


def _brute_force_marginal(state, qubits):
    """Reference marginal: bit j of the result index is qubit j."""
    out = np.zeros(1 << (max(qubits) + 1))
    probs = state.probabilities()
    for i in range(state.dim):
        index = 0
        for q in qubits:
            index |= ((i >> q) & 1) << q
        out[index] += probs[i]
    return out


@pytest.mark.parametrize("size", [1, 2, 3])
def test_marginal_matches_brute_force(size):
    n = 4
    rng = np.random.default_rng(size)
    st = QuantumState(QuantumRegister(n, "q"))
    vec = rng.normal(size=1 << n) + 1j * rng.normal(size=1 << n)
    vec /= np.linalg.norm(vec)
    st.set_state(vec)
    for count in range(1, n + 1):
        for qubits in itertools.combinations(range(n), count):
            got = st.marginal(list(qubits))
            want = _brute_force_marginal(st, list(qubits))
            assert np.allclose(got, want, atol=1e-12), qubits


def test_marginal_of_bell_first_qubit_is_uniform():
    st = QuantumState(QuantumRegister(2, "q"))
    st.h(0)
    st.cnot(0, 1)
    dist = st.marginal([0])
    assert np.allclose(dist, [0.5, 0.5], atol=1e-12)


def test_marginal_rejects_bad_index():
    st = QuantumState(QuantumRegister(2, "q"))
    with pytest.raises(GateError):
        st.marginal([5])


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------


def test_measure_is_deterministic_for_basis_state():
    st = QuantumState(QuantumRegister(2, "q"))
    st.x(1)
    outcomes = st.measure(shots=20, seed=0)
    assert set(outcomes) == {0b10}


def test_measure_rejects_non_positive_shots():
    st = QuantumState(QuantumRegister(1, "q"))
    with pytest.raises(ValueError):
        st.measure(shots=0)


def test_measure_frequency_approximates_probability():
    st = QuantumState(QuantumRegister(1, "q"))
    st.ry(2 * math.asin(math.sqrt(0.3)), 0)
    outcomes = st.measure(shots=4000, seed=12345)
    frequency = outcomes.count(1) / len(outcomes)
    assert abs(frequency - 0.3) < 0.05


def test_measure_qubit_collapses_register():
    st = QuantumState(QuantumRegister(2, "q"))
    st.h(0)
    st.cnot(0, 1)
    bits = st.measure_qubit(0, shots=30, seed=7)
    assert set(bits) <= {0, 1}
    # After collapse the register is a computational basis state.
    probs = st.probabilities()
    assert probs.max() > 1 - 1e-9


# --------------------------------------------------------------------------
# Fidelity, snapshots and copying
# --------------------------------------------------------------------------


def test_fidelity_of_identical_states_is_one():
    a = QuantumState(QuantumRegister(2, "q"))
    a.h(0)
    a.cnot(0, 1)
    b = a.copy()
    assert abs(a.fidelity(b) - 1.0) < 1e-12


def test_fidelity_of_orthogonal_states_is_zero():
    a = QuantumState(QuantumRegister(1, "q"))
    b = QuantumState(QuantumRegister(1, "q"))
    b.x(0)
    assert a.fidelity(b) < 1e-12


def test_copy_is_independent():
    a = QuantumState(QuantumRegister(1, "q"))
    b = a.copy()
    b.x(0)
    assert abs(a.probability(0) - 1.0) < 1e-12


def test_snapshot_detects_collapse():
    st = QuantumState(QuantumRegister(1, "q"))
    st.snapshot()
    assert st.is_collapsed() is False
    st.h(0)
    assert st.is_collapsed() is True


# --------------------------------------------------------------------------
# Normalisation is preserved by every gate
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "gates",
    [
        [("h", 0)],
        [("t", 0), ("tdg", 0)],
        [("s", 0), ("sdg", 0)],
        [("rx", 0, 0.4), ("ry", 0, 0.9), ("rz", 0, 1.3)],
        [("h", 0), ("cnot", 0, 1), ("toffoli", 0, 1, 2)],
        [("h", 2), ("cz", 0, 2), ("swap", 0, 2)],
    ],
)
def test_state_stays_normalised(gates):
    st = QuantumState(QuantumRegister(3, "q"))
    for gate in gates:
        name = gate[0]
        if name in ("rx", "ry", "rz"):
            getattr(st, name)(gate[2], gate[1])
        else:
            getattr(st, name)(*gate[1:])
        assert math.isclose(float(np.linalg.norm(st.state)), 1.0, abs_tol=1e-12)
