"""
Pure-Python statevector quantum simulator.

Implements an n-qubit simulator using dense complex statevectors. This is the
numerical foundation used by the algorithm implementations in
:mod:`quantumhub.algorithms`.

The simulator tracks a state vector of size ``2**n`` and applies gates as dense
matrix multiplications. Memory grows exponentially, so the practical limit is
roughly 20-24 qubits before the state vector dominates RAM.

Built by Sandesh Dhital.
"""

from __future__ import annotations

import cmath
import math
from collections.abc import Sequence

import numpy as np

# Numerical tolerance used for comparisons against exact values.
ATOL = 1e-9


class QuantumError(Exception):
    """Base exception for simulator errors."""


class InsufficientQubitsError(QuantumError):
    """Raised when a register is too small for the requested operation."""


class GateError(QuantumError):
    """Raised when a gate cannot be applied to the given register."""


class Qubit:
    """A single qubit addressed by its index inside a register."""

    __slots__ = ("index",)

    def __init__(self, index: int) -> None:
        if index < 0:
            raise ValueError("Qubit index must be non-negative")
        self.index = index

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Qubit({self.index})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Qubit) and other.index == self.index

    def __hash__(self) -> int:
        return hash(("Qubit", self.index))


class QuantumRegister:
    """An ordered collection of qubits forming a quantum register."""

    def __init__(self, n: int, name: str = "q") -> None:
        if n <= 0:
            raise ValueError("Register must contain at least one qubit")
        if n > 24:
            raise GateError(
                f"Refusing to allocate a {n}-qubit state vector "
                "(dense simulation is limited to 24 qubits)"
            )
        self.name = name
        self.size = n
        self.qubits = [Qubit(i) for i in range(n)]

    def __len__(self) -> int:
        return self.size

    def __iter__(self):
        return iter(self.qubits)

    def __getitem__(self, index: int) -> Qubit:
        return self.qubits[index]

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"QuantumRegister({self.name}, {self.size})"


# --------------------------------------------------------------------------
# Single-qubit gate matrices (little-endian indexing convention)
# --------------------------------------------------------------------------

I2 = np.eye(2, dtype=complex)

H = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)

X = np.array([[0, 1], [1, 0]], dtype=complex)

Y = np.array([[0, -1j], [1j, 0]], dtype=complex)

Z = np.array([[1, 0], [0, -1]], dtype=complex)

S = np.array([[1, 0], [0, 1j]], dtype=complex)

SDG = np.array([[1, 0], [0, -1j]], dtype=complex)

T = np.array([[1, 0], [0, cmath.exp(1j * math.pi / 4)]], dtype=complex)

TDG = np.array([[1, 0], [0, cmath.exp(-1j * math.pi / 4)]], dtype=complex)


def rx(theta: float) -> np.ndarray:
    """Rotation about the X axis by ``theta`` radians."""
    cos = math.cos(theta / 2)
    sin = math.sin(theta / 2)
    return np.array([[cos, -1j * sin], [-1j * sin, cos]], dtype=complex)


def ry(theta: float) -> np.ndarray:
    """Rotation about the Y axis by ``theta`` radians."""
    cos = math.cos(theta / 2)
    sin = math.sin(theta / 2)
    return np.array([[cos, -sin], [sin, cos]], dtype=complex)


def rz(theta: float) -> np.ndarray:
    """Rotation about the Z axis by ``theta`` radians."""
    return np.array(
        [
            [cmath.exp(-1j * theta / 2), 0],
            [0, cmath.exp(1j * theta / 2)],
        ],
        dtype=complex,
    )


def phase(theta: float) -> np.ndarray:
    """Apply a relative phase ``exp(i * theta)`` to the ``|1>`` component."""
    return np.array([[1, 0], [0, cmath.exp(1j * theta)]], dtype=complex)


def u3(theta: float, phi: float, lam: float) -> np.ndarray:
    """Generic single-qubit U3 gate (IBM decomposition)."""
    return np.array(
        [
            [math.cos(theta / 2), -cmath.exp(1j * lam) * math.sin(theta / 2)],
            [
                cmath.exp(1j * phi) * math.sin(theta / 2),
                cmath.exp(1j * (phi + lam)) * math.cos(theta / 2),
            ],
        ],
        dtype=complex,
    )


# --------------------------------------------------------------------------
# Two-qubit gates
# --------------------------------------------------------------------------


def cnot() -> np.ndarray:
    """CNOT gate as a 4x4 matrix with little-endian qubit ordering.

    The control is qubit 0 (the more significant bit) and the target is
    qubit 1.
    """
    return np.array(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 0],
        ],
        dtype=complex,
    )


def cz() -> np.ndarray:
    """Controlled-Z gate as a 4x4 matrix."""
    return np.diag([1, 1, 1, -1]).astype(complex)


def swap() -> np.ndarray:
    """SWAP gate as a 4x4 matrix."""
    return np.array(
        [
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
        ],
        dtype=complex,
    )


def crx(theta: float) -> np.ndarray:
    """Controlled rotation about X."""
    matrix = np.eye(4, dtype=complex)
    matrix[2:4, 2:4] = rx(theta)
    return matrix


def cry(theta: float) -> np.ndarray:
    """Controlled rotation about Y."""
    matrix = np.eye(4, dtype=complex)
    matrix[2:4, 2:4] = ry(theta)
    return matrix


def crz(theta: float) -> np.ndarray:
    """Controlled rotation about Z."""
    matrix = np.eye(4, dtype=complex)
    matrix[2:4, 2:4] = rz(theta)
    return matrix


def toffoli() -> np.ndarray:
    """CCNOT (Toffoli) gate as an 8x8 matrix."""
    matrix = np.eye(8, dtype=complex)
    matrix[6, 6] = 0
    matrix[7, 7] = 0
    matrix[6, 7] = 1
    matrix[7, 6] = 1
    return matrix


# --------------------------------------------------------------------------
# Register
# --------------------------------------------------------------------------


class QuantumState:
    """A simulator holding the state vector of an n-qubit register."""

    def __init__(self, register: QuantumRegister) -> None:
        self.register = register
        self.n = register.size
        self.dim = 1 << self.n
        self.state = np.zeros(self.dim, dtype=complex)
        self.state[0] = 1.0 + 0j
        #: Snapshot of the state taken by :meth:`snapshot`.
        self._snapshot: np.ndarray | None = None

    # -- lifecycle ---------------------------------------------------------

    def reset(self) -> QuantumState:
        """Reset the register to the all-zero computational basis state."""
        self.state = np.zeros(self.dim, dtype=complex)
        self.state[0] = 1.0 + 0j
        return self

    def set_state(self, vector: Sequence[complex]) -> QuantumState:
        """Overwrite the state vector, validating norm and dimension."""
        array = np.asarray(vector, dtype=complex)
        if array.size != self.dim:
            raise GateError(
                f"Expected a state vector of length {self.dim}, got {array.size}"
            )
        norm = float(np.linalg.norm(array))
        if not math.isclose(norm, 1.0, abs_tol=1e-6):
            raise GateError(f"State vector must be normalised, got norm {norm:.6f}")
        self.state = array
        return self

    def snapshot(self) -> np.ndarray:
        """Record the current state for later comparison."""
        self._snapshot = self.state.copy()
        return self._snapshot

    def is_collapsed(self) -> bool:
        """Return True if the snapshot differs from the current state."""
        if self._snapshot is None:
            return False
        return not np.allclose(self.state, self._snapshot, atol=ATOL)

    # -- gates -------------------------------------------------------------

    def apply_single(self, matrix: np.ndarray, qubit: int) -> QuantumState:
        """Apply a 2x2 matrix to ``qubit``."""
        if not 0 <= qubit < self.n:
            raise GateError(f"Qubit {qubit} is out of range for {self.n} qubits")
        if matrix.shape != (2, 2):
            raise GateError("Single-qubit gate must be a 2x2 matrix")

        # The stride between amplitudes differing only in `qubit`.
        stride = 1 << qubit
        for offset in range(0, self.dim, stride * 2):
            for i in range(stride):
                lo = offset + i
                hi = lo + stride
                a = self.state[lo]
                b = self.state[hi]
                self.state[lo] = matrix[0, 0] * a + matrix[0, 1] * b
                self.state[hi] = matrix[1, 0] * a + matrix[1, 1] * b
        return self

    def apply_two_qubit(self, matrix: np.ndarray, q1: int, q2: int) -> QuantumState:
        """Apply a 4x4 matrix to the qubit pair ``(q1, q2)``.

        ``q1`` is treated as the more significant qubit of the pair.
        """
        if not 0 <= q1 < self.n or not 0 <= q2 < self.n:
            raise GateError(f"Qubits ({q1}, {q2}) are out of range for {self.n} qubits")
        if q1 == q2:
            raise GateError("Two-qubit gate requires two distinct qubits")
        if matrix.shape != (4, 4):
            raise GateError("Two-qubit gate must be a 4x4 matrix")

        # Ensure the high-order qubit of the pair is the higher index so the
        # pair basis is ordered |q1 q2> in the matrix convention.
        if q1 < q2:
            q1, q2 = q2, q1
            matrix = _swap_pair_ordering(matrix)

        stride_hi = 1 << q1
        stride_lo = 1 << q2
        mask = stride_hi | stride_lo

        # Every 4-amplitude block is identified by the basis index with both
        # pair bits cleared. All other qubits (including those below q2) are
        # held fixed and vary between blocks.
        blocks = [i for i in range(0, self.dim, 1) if not (i & mask)]
        for base in blocks:
            indices = (base, base | stride_lo, base | stride_hi, base | mask)
            amplitudes = np.array([self.state[i] for i in indices], dtype=complex)
            updated = matrix @ amplitudes
            for pos, i in enumerate(indices):
                self.state[i] = updated[pos]
        return self

    # -- convenience gates -------------------------------------------------

    def h(self, qubit: int) -> QuantumState:
        """Hadamard gate."""
        return self.apply_single(H, qubit)

    def x(self, qubit: int) -> QuantumState:
        """Pauli-X gate."""
        return self.apply_single(X, qubit)

    def y(self, qubit: int) -> QuantumState:
        """Pauli-Y gate."""
        return self.apply_single(Y, qubit)

    def z(self, qubit: int) -> QuantumState:
        """Pauli-Z gate."""
        return self.apply_single(Z, qubit)

    def s(self, qubit: int) -> QuantumState:
        """S (phase) gate."""
        return self.apply_single(S, qubit)

    def sdg(self, qubit: int) -> QuantumState:
        """S-dagger gate."""
        return self.apply_single(SDG, qubit)

    def t(self, qubit: int) -> QuantumState:
        """T gate."""
        return self.apply_single(T, qubit)

    def tdg(self, qubit: int) -> QuantumState:
        """T-dagger gate."""
        return self.apply_single(TDG, qubit)

    def rx(self, theta: float, qubit: int) -> QuantumState:
        """X-axis rotation."""
        return self.apply_single(rx(theta), qubit)

    def ry(self, theta: float, qubit: int) -> QuantumState:
        """Y-axis rotation."""
        return self.apply_single(ry(theta), qubit)

    def rz(self, theta: float, qubit: int) -> QuantumState:
        """Z-axis rotation."""
        return self.apply_single(rz(theta), qubit)

    def p(self, theta: float, qubit: int) -> QuantumState:
        """Relative phase gate."""
        return self.apply_single(phase(theta), qubit)

    def cnot(self, control: int, target: int) -> QuantumState:
        """CNOT gate."""
        return self.apply_two_qubit(cnot(), control, target)

    def cz(self, q1: int, q2: int) -> QuantumState:
        """Controlled-Z gate."""
        return self.apply_two_qubit(cz(), q1, q2)

    def swap(self, q1: int, q2: int) -> QuantumState:
        """SWAP gate."""
        return self.apply_two_qubit(swap(), q1, q2)

    def crx(self, theta: float, control: int, target: int) -> QuantumState:
        """Controlled X rotation."""
        return self.apply_two_qubit(crx(theta), control, target)

    def cry(self, theta: float, control: int, target: int) -> QuantumState:
        """Controlled Y rotation."""
        return self.apply_two_qubit(cry(theta), control, target)

    def crz(self, theta: float, control: int, target: int) -> QuantumState:
        """Controlled Z rotation."""
        return self.apply_two_qubit(crz(theta), control, target)

    def apply_controlled_x(self, control: int, target: int) -> QuantumState:
        """Apply a CNOT using explicit basis-state iteration.

        This is ordering-independent and used where the control qubit index
        is higher than the target index.
        """
        if not 0 <= control < self.n or not 0 <= target < self.n:
            raise GateError("CNOT qubit index out of range")
        if control == target:
            raise GateError("CNOT requires two distinct qubits")
        for i in range(self.dim):
            if (i >> control) & 1:
                self.state[i], self.state[i ^ (1 << target)] = (
                    self.state[i ^ (1 << target)],
                    self.state[i],
                )
        return self

    def cp(self, theta: float, control: int, target: int) -> QuantumState:
        """Apply a controlled phase gate ``diag(1, 1, 1, e^{i*theta})``.

        Implemented by direct basis-state iteration, so it is independent of
        the qubit-ordering convention used by the 4x4 matrix path.
        """
        if not 0 <= control < self.n or not 0 <= target < self.n:
            raise GateError("Controlled phase qubit index out of range")
        if control == target:
            raise GateError("Controlled phase requires two distinct qubits")
        factor = cmath.exp(1j * theta)
        for i in range(self.dim):
            if ((i >> control) & 1) and ((i >> target) & 1):
                self.state[i] *= factor
        return self

    def toffoli(self, c1: int, c2: int, target: int) -> QuantumState:
        """Toffoli (CCNOT) gate on three qubits.

        Flips ``target`` exactly when both controls are in state 1.
        """
        if len({c1, c2, target}) != 3:
            raise GateError("Toffoli gate requires three distinct qubits")
        if not all(0 <= q < self.n for q in (c1, c2, target)):
            raise GateError("Toffoli gate qubit index out of range")

        control_mask = (1 << c1) | (1 << c2)
        target_bit = 1 << target

        # Swap the amplitudes of |..11 0> and |..11 1> for every assignment of
        # the remaining qubits. The other six basis states are unchanged.
        for i in range(self.dim):
            if (i & control_mask) == control_mask:
                j = i | target_bit
                if j < self.dim:
                    self.state[i], self.state[j] = self.state[j], self.state[i]
        return self

    # -- measurement -------------------------------------------------------

    def measure(self, shots: int = 1, seed: int | None = None) -> list[int]:
        """Measure the register in the computational basis.

        Returns a list of integer outcomes, one per shot.
        """
        if shots <= 0:
            raise ValueError("shots must be a positive integer")
        probabilities = self.probabilities()
        rng = np.random.default_rng(seed)
        return [
            int(rng.choice(self.dim, p=probabilities)) for _ in range(shots)
        ]

    def measure_qubit(self, qubit: int, shots: int = 1, seed: int | None = None) -> list[int]:
        """Measure a single qubit, collapsing the register."""
        if not 0 <= qubit < self.n:
            raise GateError(f"Qubit {qubit} is out of range")
        results = []
        rng = np.random.default_rng(seed)
        for _ in range(shots):
            outcome = int(rng.choice(self.dim, p=self.probabilities()))
            bit = (outcome >> (self.n - 1 - qubit)) & 1
            self._collapse(outcome)
            results.append(bit)
        return results

    def _collapse(self, outcome: int) -> None:
        """Project the register onto ``outcome`` in the computational basis."""
        projected = np.zeros(self.dim, dtype=complex)
        projected[outcome] = 1.0 + 0j
        self.state = projected

    def probabilities(self) -> np.ndarray:
        """Return the measurement probability distribution."""
        probs = np.abs(self.state) ** 2
        total = probs.sum()
        if total > 0:
            probs = probs / total
        return probs

    def probability(self, outcome: int) -> float:
        """Return the probability of a specific basis state."""
        return float(np.abs(self.state[outcome]) ** 2)

    def to_dict(self, top_k: int = 8) -> dict[str, object]:
        """Return the most probable outcomes and basic diagnostics."""
        probs = self.probabilities()
        order = np.argsort(probs)[::-1][:top_k]
        outcomes = [
            {
                "state": format(i, f"0{self.n}b"),
                "probability": round(float(probs[i]), 6),
            }
            for i in order
            if probs[i] > 1e-12
        ]
        return {
            "num_qubits": self.n,
            "dimension": self.dim,
            "entropy": round(self.entropy(), 6),
            "outcomes": outcomes,
        }

    def marginal(self, qubits: Sequence[int]) -> np.ndarray:
        """Return the measurement distribution over a subset of qubits.

        Traces out every qubit not listed and returns the distribution indexed
        by the retained qubits, using the same convention as
        :meth:`probabilities`: bit ``j`` of the returned index holds the
        outcome of qubit ``j``, so qubit 0 is the least significant bit. This
        is the correct way to read a sub-register regardless of where the
        other qubits sit.

        Args:
            qubits: The qubit indices to keep. Order does not matter; the
                returned index is keyed by qubit number.

        Returns:
            An array of length ``2**max(qubits) + 1`` summing to 1, indexed
            so that bit ``j`` is qubit ``j``.

        Raises:
            GateError: If a qubit index is out of range.
        """
        for q in qubits:
            if not 0 <= q < self.n:
                raise GateError(f"Qubit {q} is out of range for {self.n} qubits")

        keep_set = set(qubits)
        if not keep_set:
            raise GateError("marginal requires at least one qubit")
        traced = [q for q in range(self.n) if q not in keep_set]

        # Tensor axis `a` of a length-n reshape corresponds to qubit n-1-a.
        # Order the kept axes from the highest qubit down so that the reshaped
        # row index is the retained basis value with qubit 0 as the LSB.
        keep_desc = sorted(keep_set, reverse=True)
        axes = [self.n - 1 - q for q in keep_desc] + [self.n - 1 - q for q in traced]
        tensor = np.transpose(self.state.reshape([2] * self.n), axes)
        matrix = tensor.reshape(1 << len(keep_desc), 1 << len(traced))

        compact = (np.abs(matrix) ** 2).sum(axis=1)

        # Scatter into a qubit-number-indexed array so bit j of the returned
        # index always refers to qubit j, as documented.
        out = np.zeros(1 << (keep_desc[0] + 1))
        for row, weight in enumerate(compact):
            index = 0
            for position, qubit in enumerate(keep_desc):
                bit = (row >> (len(keep_desc) - 1 - position)) & 1
                index |= bit << qubit
            out[index] = weight

        total = float(out.sum())
        if total > 0:
            out = out / total
        return out

    def entropy(self) -> float:
        """Shannon entropy of the measurement distribution, in bits."""
        probs = self.probabilities()
        nonzero = probs[probs > 1e-12]
        return float(-np.sum(nonzero * np.log2(nonzero)))

    def fidelity(self, other: QuantumState) -> float:
        """Fidelity |<psi|phi>|^2 between this state and ``other``."""
        return float(abs(np.vdot(other.state, self.state)) ** 2)

    def copy(self) -> QuantumState:
        """Return an independent copy of this state."""
        clone = QuantumState(self.register)
        clone.state = self.state.copy()
        return clone


def _swap_pair_ordering(matrix: np.ndarray) -> np.ndarray:
    """Relabel a 4x4 two-qubit matrix so the two qubits are exchanged.

    The matrix is given in the basis ``|q1 q0>`` and must be converted to
    ``|q0 q1>``. This is the conjugation by the SWAP operator, which maps
    basis index 1 to 2 and index 2 to 1.
    """
    permuted = matrix.copy()
    permuted[[1, 2]] = permuted[[2, 1]]
    return permuted[:, [0, 2, 1, 3]]


# --------------------------------------------------------------------------
# Measurement operators and expectation helpers
# --------------------------------------------------------------------------


def pauli_expectation(state: QuantumState, qubit: int, axis: str = "Z") -> float:
    """Real expectation value of a single-qubit Pauli operator."""
    gates = {"X": state.x, "Y": state.y, "Z": state.z}
    if axis.upper() not in gates:
        raise ValueError("axis must be one of X, Y, Z")
    temp = state.copy()
    gates[axis.upper()](qubit)
    return float(2 * np.real(np.vdot(state.state, temp.state)))


def global_phase(state: QuantumState) -> float:
    """Estimate the global phase relative to the |0...0> basis state."""
    return float(cmath.phase(state.state[np.argmax(np.abs(state.state))]))
