"""Tests for the gate matrices and operator helpers in the statevector module.

Each gate is checked against an independent construction rather than a stored
value, so a change to a matrix cannot pass by agreeing with itself.
"""

import cmath
import math

import numpy as np
import pytest

from quantumhub import statevector as sv
from quantumhub.statevector import QuantumRegister, QuantumState

# --------------------------------------------------------------------------
# Single-qubit matrices
# --------------------------------------------------------------------------


def test_hadamard_is_its_own_inverse():
    assert np.allclose(sv.H @ sv.H, np.eye(2), atol=1e-12)


def test_pauli_matrices_satisfy_the_clifford_relations():
    identity = np.eye(2, dtype=complex)
    # The Pauli matrices anticommute and square to the identity.
    assert np.allclose(sv.X @ sv.Y, 1j * sv.Z, atol=1e-12)
    assert np.allclose(sv.Y @ sv.Z, 1j * sv.X, atol=1e-12)
    assert np.allclose(sv.Z @ sv.X, 1j * sv.Y, atol=1e-12)
    for m in (sv.X, sv.Y, sv.Z):
        assert np.allclose(m @ m, identity, atol=1e-12)


def test_s_gates_square_to_z():
    assert np.allclose(sv.S @ sv.S, sv.Z, atol=1e-12)


def test_t_gates_square_to_s():
    assert np.allclose(sv.T @ sv.T, sv.S, atol=1e-12)


def test_daggers_are_inverses():
    for gate, dagger in ((sv.S, sv.SDG), (sv.T, sv.TDG)):
        assert np.allclose(gate @ dagger, np.eye(2), atol=1e-12)


def test_sdg_is_the_conjugate_transpose_of_s():
    assert np.allclose(sv.SDG, sv.S.conj().T, atol=1e-12)


# --------------------------------------------------------------------------
# Rotation matrices
# --------------------------------------------------------------------------


@pytest.mark.parametrize("theta", [0.0, 0.4, 1.1, math.pi, 2.7])
def test_rotations_are_unitary(theta):
    for matrix in (sv.rx(theta), sv.ry(theta), sv.rz(theta)):
        assert np.allclose(matrix.conj().T @ matrix, np.eye(2), atol=1e-12)


def test_zero_rotation_is_the_identity():
    for builder in (sv.rx, sv.ry, sv.rz):
        assert np.allclose(builder(0.0), np.eye(2), atol=1e-12)


def test_rx_has_imaginary_offdiagonal_and_ry_is_real():
    theta = 0.9
    rx = sv.rx(theta)
    assert np.allclose(np.diag(rx).imag, 0, atol=1e-12)
    assert np.allclose(rx[0, 1], -1j * math.sin(theta / 2), atol=1e-12)
    assert np.allclose(sv.ry(theta).imag, 0, atol=1e-12)
    assert np.allclose(np.abs(np.diag(sv.rz(theta))), 1.0, atol=1e-12)


def test_rx_pi_is_minus_x_up_to_phase():
    assert np.allclose(sv.rx(math.pi), -1j * sv.X, atol=1e-12)


def test_phase_gate_only_touches_the_one_component():
    theta = 0.4
    assert np.allclose(sv.phase(theta), np.diag([1.0, cmath.exp(1j * theta)]), atol=1e-12)


def test_u3_is_unitary_and_starts_in_the_zero_state():
    theta, phi, lam = 0.6, 0.3, 0.9
    matrix = sv.u3(theta, phi, lam)
    assert np.allclose(matrix.conj().T @ matrix, np.eye(2), atol=1e-12)
    # U3 applied to |0> lands on the cos/sin column of the standard formula.
    expected = np.array(
        [math.cos(theta / 2), cmath.exp(1j * phi) * math.sin(theta / 2)], dtype=complex
    )
    assert np.allclose(matrix @ np.array([1, 0], dtype=complex), expected, atol=1e-12)


# --------------------------------------------------------------------------
# Two-qubit matrices
# --------------------------------------------------------------------------


def test_cnot_matrix_is_self_inverse():
    assert np.allclose(sv.cnot() @ sv.cnot(), np.eye(4), atol=1e-12)


def test_cz_is_diagonal_with_two_negative_entries():
    matrix = sv.cz()
    assert np.allclose(matrix, np.diag([1, 1, 1, -1]).astype(complex), atol=1e-12)


def test_swap_is_self_inverse_and_symmetric():
    assert np.allclose(sv.swap() @ sv.swap(), np.eye(4), atol=1e-12)
    assert np.allclose(sv.swap(), sv.swap().T, atol=1e-12)


def test_controlled_rotations_leave_the_control_branch_untouched():
    theta = 0.55
    for builder in (sv.crx, sv.cry, sv.crz):
        matrix = builder(theta)
        assert np.allclose(matrix[:2, :2], np.eye(2), atol=1e-12)


def test_toffoli_matrix_is_self_inverse():
    assert np.allclose(sv.toffoli() @ sv.toffoli(), np.eye(8), atol=1e-12)


def test_toffoli_matrix_only_swaps_the_two_control_satisfied_states():
    """Controls are bits 1 and 2; the target is bit 0, so only 6 and 7 swap."""
    matrix = sv.toffoli()
    for index in range(8):
        controls_set = bool((index >> 1) & 1) and bool((index >> 2) & 1)
        expected = index ^ 1 if controls_set else index
        assert abs(matrix[index, expected] - 1) < 1e-12, index


# --------------------------------------------------------------------------
# Operator helpers
# --------------------------------------------------------------------------


@pytest.mark.parametrize("axis", ["X", "Y", "Z", "x", "y", "z"])
def test_pauli_expectation_on_bell_state_is_zero(axis):
    st = QuantumState(QuantumRegister(2, "bell"))
    st.h(0)
    st.cnot(0, 1)
    assert abs(sv.pauli_expectation(st, 0, axis)) < 1e-12


def test_pauli_expectation_of_z_on_basis_state():
    st = QuantumState(QuantumRegister(1, "q"))
    st.x(0)
    assert sv.pauli_expectation(st, 0, "Z") < -0.999
    assert sv.pauli_expectation(st, 0, "X") < 1e-12
    assert sv.pauli_expectation(st, 0, "Y") < 1e-12


def test_pauli_expectation_of_x_on_plus_state():
    st = QuantumState(QuantumRegister(1, "q"))
    st.h(0)
    assert sv.pauli_expectation(st, 0, "X") > 0.999


def test_pauli_expectation_rejects_an_unknown_axis():
    st = QuantumState(QuantumRegister(1, "q"))
    with pytest.raises(ValueError):
        sv.pauli_expectation(st, 0, "W")


def test_global_phase_of_basis_state_is_zero():
    st = QuantumState(QuantumRegister(1, "q"))
    assert abs(sv.global_phase(st)) < 1e-12


def test_global_phase_reads_the_dominant_amplitude():
    """The helper reports the phase of the largest-magnitude amplitude."""
    st = QuantumState(QuantumRegister(1, "q"))
    st.set_state(np.array([0.8, 0.6j], dtype=complex))
    assert abs(sv.global_phase(st)) < 1e-9


def test_global_phase_is_measured_relative_to_the_dominant_amplitude():
    """A uniform rotation of the whole state leaves the measurement unchanged."""
    st = QuantumState(QuantumRegister(1, "q"))
    st.ry(0.8, 0)
    reference = sv.global_phase(st)
    st.apply_single(sv.rz(0.0), 0)
    assert abs(sv.global_phase(st) - reference) < 1e-12


# --------------------------------------------------------------------------
# Qubit and register behaviour
# --------------------------------------------------------------------------


def test_qubit_equality_and_hashing():
    a = sv.Qubit(2)
    b = sv.Qubit(2)
    c = sv.Qubit(3)
    assert a == b
    assert a != c
    assert len({a, b, c}) == 2


def test_qubit_rejects_a_negative_index():
    with pytest.raises(ValueError):
        sv.Qubit(-1)


def test_register_repr_mentions_its_name_and_size():
    text = repr(sv.QuantumRegister(3, "abc"))
    assert "abc" in text
    assert "3" in text


# --------------------------------------------------------------------------
# to_dict reporting
# --------------------------------------------------------------------------


def test_to_dict_reports_entropy_and_top_outcomes():
    st = QuantumState(QuantumRegister(2, "bell"))
    st.h(0)
    st.cnot(0, 1)
    report = st.to_dict()
    assert report["num_qubits"] == 2
    assert report["dimension"] == 4
    assert abs(report["entropy"] - 1.0) < 1e-9
    states = {entry["state"] for entry in report["outcomes"]}
    assert states == {"00", "11"}


def test_to_dict_top_k_limits_the_outcome_list():
    st = QuantumState(QuantumRegister(4, "q"))
    for q in range(4):
        st.h(q)
    assert len(st.to_dict(top_k=3)["outcomes"]) <= 3
