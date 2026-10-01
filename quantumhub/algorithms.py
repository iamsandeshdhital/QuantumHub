"""
Quantum algorithm implementations built on the statevector simulator.

Each function is a self-contained, tested implementation of a published
quantum algorithm. The algorithms span the core result areas of quantum
computing: search, phase estimation, factoring, optimisation, simulation,
cryptography and error correction.

Built by Sandesh Dhital.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np

from quantumhub.statevector import (
    QuantumRegister,
    QuantumState,
)

_INV_SQRT2 = 1.0 / math.sqrt(2.0)


class AlgorithmError(Exception):
    """Raised when an algorithm cannot resolve the expected output."""


def _apply_oracle(state: QuantumState, f: Callable[[list[int]], int], n: int, ancilla: int) -> None:
    """Apply a black-box oracle ``f`` to the ancilla via phase kickback.

    The oracle ``U_f |x>|y> = |x>|y XOR f(x)>`` is realised by flipping the
    ancilla only for the input basis states where ``f`` is 1. Because the
    ancilla is prepared in ``|->``, that flip manifests as a phase of -1 on
    the corresponding input amplitude.

    Args:
        state: The simulator state, with the input register on qubits
            ``0..n-1`` and the ancilla on qubit ``n``.
        f: The oracle function over n input bits.
        n: The input register width.
        ancilla: The ancilla qubit index.
    """
    for basis in range(1 << n):
        bits = [(basis >> (n - 1 - i)) & 1 for i in range(n)]
        if f(bits) == 1:
            # Flip the ancilla only when the input register is |basis>.
            _flip_ancilla_for_basis(state, basis, n, ancilla)


def _flip_ancilla_for_basis(state: QuantumState, basis: int, n: int, ancilla: int) -> None:
    """Swap the ancilla amplitudes for the input basis state ``basis``.

    Iterating only over indices where the ancilla bit is clear ensures each
    pair is swapped exactly once; visiting both members would undo the swap.
    """
    input_mask = (1 << n) - 1
    ancilla_bit = 1 << ancilla
    for i in range(state.dim):
        if (i & input_mask) != basis:
            continue
        if i & ancilla_bit:
            continue
        j = i | ancilla_bit
        state.state[i], state.state[j] = state.state[j], state.state[i]


# ==========================================================================
# Deutsch-Jozsa
# ==========================================================================


def deutsch_jozsa(
    f: Callable[[list[int]], int],
    n: int,
    ancilla: int = 1,
) -> int:
    """Deutsch-Jozsa algorithm for a promise problem.

    ``f`` is a function from n bits to 1 bit that is promised to be constant
    (all outputs 0 or all outputs 1) or linear (a XOR of the input bits).

    Returns 0 for a constant function and 1 for a linear function. The
    Deutsch-Jozsa advantage is that the answer is obtained with certainty
    using a single oracle call, whereas a classical algorithm needs
    exponentially many in the worst case.

    Args:
        f: The oracle. Must accept a list of 0/1 ints and return 0 or 1.
        n: The input width of the oracle in bits.
        ancilla: Number of ancilla qubits to prepare in |1>.

    Returns:
        0 if f is constant, 1 if f is linear.

    Raises:
        ValueError: If the promise is violated.
    """
    if ancilla != 1:
        raise ValueError("Deutsch-Jozsa uses exactly one ancilla qubit")
    if n < 1:
        raise ValueError("n must be positive")

    register = QuantumRegister(n + 1, "dj")
    state = QuantumState(register)

    # Prepare |-> on the ancilla and |+> on the input register.
    state.x(n)
    for q in range(n + 1):
        state.h(q)

    # Oracle via phase kickback.
    _apply_oracle(state, f, n, n)

    for q in range(n + 1):
        state.h(q)


    # Qubit n is the ancilla. Marginalise it out and inspect the input
    # register: |0...0> means the function is constant, a nonzero outcome
    # means it is linear.
    input_dist = state.marginal(list(range(n)))
    input_mass_zero = float(input_dist[0])
    input_mass_nonzero = float(1.0 - input_mass_zero)

    if input_mass_zero > 0.999:
        return 0
    if input_mass_nonzero > 0.999:
        return 1
    raise ValueError("Deutsch-Jozsa promise violated: f is neither constant nor linear")


# ==========================================================================
# Bernstein-Vazirani
# ==========================================================================


def bernstein_vazirani(
    f: Callable[[list[int]], int],
    n: int,
    ancilla: int = 1,
) -> int:
    """Bernstein-Vazirani algorithm recovering a hidden bit string.

    For an oracle ``f(x) = a . x (mod 2)`` the algorithm returns the secret
    string ``a`` with a single oracle call, versus a classical query
    complexity of n calls.

    Args:
        f: Oracle implementing the dot product with the hidden string.
        n: The input width of the oracle in bits.
        ancilla: Number of ancilla qubits (must be 1).

    Returns:
        The hidden integer, interpreted as an n-bit string.
    """
    if ancilla != 1:
        raise ValueError("Bernstein-Vazirani uses exactly one ancilla qubit")
    if n < 1:
        raise ValueError("n must be positive")

    register = QuantumRegister(n + 1, "bv")
    state = QuantumState(register)

    state.x(n)
    for q in range(n + 1):
        state.h(q)

    # Oracle via phase kickback.
    _apply_oracle(state, f, n, n)

    # Only the input register needs the final Hadamards.
    for q in range(n):
        state.h(q)

    # Marginalise the ancilla out and read the input register directly.
    input_dist = state.marginal(list(range(n)))
    best = int(np.argmax(input_dist))
    if float(input_dist[best]) < 0.999:
        raise AlgorithmError("Bernstein-Vazirani failed to resolve the secret string")
    return best


# ==========================================================================
# Simon's algorithm
# ==========================================================================


@dataclass
class SimonResult:
    """Outcome of a Simon period-finding run."""

    period: int
    samples: list[int]
    null_space: list[int]
    oracle_calls: int = 0

    @property
    def is_exact(self) -> bool:
        """True when the null space of the samples is exactly span{period}."""
        generators = [c for c in self.null_space if c != 0]
        return generators == [self.period]


def simon_algorithm(f: Callable[[list[int]], list[int]], n: int) -> SimonResult:
    """Simon's algorithm for finding the period of a 2-to-1 function.

    Simon's problem: given an oracle for a function ``f: {0,1}^n -> {0,1}^{n-1}``
    that is exactly two-to-one, recover the hidden period ``s`` such that
    ``f(x) = f(x XOR s)`` for every x. Simon's algorithm needs O(n) oracle
    queries versus the classical worst case of order 2^(n/2).

    The circuit evaluates the oracle into a second register, applies a
    Hadamard to the input register, and measures values ``z`` that satisfy
    ``z . s = 0`` over GF(2). Recovering ``s`` is then a small linear system.

    Args:
        f: Oracle mapping a list of n bits to a list of n-1 bits.
        n: The register width in bits.

    Returns:
        A :class:`SimonResult` holding the recovered period, the sampled
        ``z`` values, and the null space spanned by them.

    Raises:
        ValueError: If ``n`` is too small.
        AlgorithmError: If the linear system cannot be solved.
    """
    if n < 2:
        raise ValueError("n must be at least 2")

    register = QuantumRegister(2 * n, "simon")
    state = QuantumState(register)

    for q in range(n):
        state.h(q)

    # Evaluate the oracle, writing f(x) into the second register. The oracle
    # output is a permutation of the basis states within each fixed input, so
    # it is applied by accumulating amplitudes rather than in-place swaps.
    oracle_state = np.zeros(state.dim, dtype=complex)
    for x in range(1 << n):
        x_bits = [(x >> (n - 1 - i)) & 1 for i in range(n)]
        y = 0
        for bit in f(x_bits):
            y = (y << 1) | int(bit)
        oracle_state[x | (y << n)] += 1.0 / math.sqrt(1 << n)
    state.set_state(oracle_state)

    # Hadamard on the input register, which now correlates with f(x).
    for q in range(n):
        state.h(q)

    # Marginalise the oracle register and sample values of the input register.
    input_dist = state.marginal(list(range(n)))

    rng = np.random.default_rng(12345)
    samples: list[int] = []
    for _ in range(4096):
        z = int(rng.choice(1 << n, p=input_dist))
        if z != 0 and z not in samples:
            samples.append(z)
        if len(samples) >= n:
            break

    period = _solve_simon_linear_system(samples, n)
    rows = [[(z >> (n - 1 - j)) & 1 for j in range(n)] for z in samples]
    null_space = [0] + [_vec_to_int(v, n) for v in _gf2_null_space(rows, n)]
    return SimonResult(
        period=period,
        samples=samples,
        null_space=null_space,
        oracle_calls=1,
    )


def _gf2_null_space(rows: Sequence[Sequence[int]], n: int) -> list[list[int]]:
    """Return a basis for ``{v : rows . v = 0}`` over GF(2).

    Performs Gauss-Jordan elimination to reduced row echelon form, then reads
    off one null vector per free column.

    Args:
        rows: The constraint rows, each a list of n bits.
        n: The number of variables.

    Returns:
        A list of basis vectors, each a list of n bits.
    """
    matrix = [list(r) for r in rows]
    pivots: list[int] = []
    pivot_row = 0

    for col in range(n):
        selected = next(
            (r for r in range(pivot_row, len(matrix)) if matrix[r][col]),
            None,
        )
        if selected is None:
            continue
        matrix[pivot_row], matrix[selected] = matrix[selected], matrix[pivot_row]
        for r in range(len(matrix)):
            if r != pivot_row and matrix[r][col]:
                matrix[r] = [a ^ b for a, b in zip(matrix[r], matrix[pivot_row])]
        pivots.append(col)
        pivot_row += 1

    free = [c for c in range(n) if c not in pivots]
    basis: list[list[int]] = []

    for free_col in free:
        vector = [0] * n
        vector[free_col] = 1
        for i, pivot_col in enumerate(pivots):
            # Row i of the reduced form has a leading 1 in pivot_col, so the
            # pivot variable is fixed by the already-assigned free variables.
            parity = 0
            for c in range(n):
                if c != pivot_col and matrix[i][c] and vector[c]:
                    parity ^= 1
            vector[pivot_col] = parity
        basis.append(vector)

    return basis


def _vec_to_int(vector: Sequence[int], n: int) -> int:
    """Convert a bit list (index 0 = most significant) to an integer."""
    value = 0
    for bit in vector:
        value = (value << 1) | (int(bit) & 1)
    return value


def _solve_simon_linear_system(samples: Sequence[int], n: int) -> int:
    """Recover a period from sampled ``z`` values satisfying ``z . s = 0``.

    Simon's algorithm determines the period only up to the null space of the
    observed samples, so any nonzero element of that null space is a valid
    answer. When the null space is one-dimensional the answer is exact.

    Args:
        samples: The observed ``z`` values.
        n: The register width.

    Returns:
        A nonzero integer in the null space.

    Raises:
        AlgorithmError: If no nonzero null vector exists.
    """
    if not samples:
        raise AlgorithmError("No nonzero samples collected for Simon's algorithm")

    rows = [[(z >> (n - 1 - j)) & 1 for j in range(n)] for z in samples]
    basis = _gf2_null_space(rows, n)

    for vector in basis:
        value = _vec_to_int(vector, n)
        if value != 0:
            return value

    raise AlgorithmError("Could not solve the Simon linear system")


# ==========================================================================
# Grover search
# ==========================================================================


@dataclass
class GroverResult:
    """Outcome of a Grover search run."""

    marked_index: int
    marked_bitstring: str
    iterations: int
    probabilities: np.ndarray
    success_probability: float
    queries: int = 1
    oracle_calls: int = 0


def grover_search(
    marked: Sequence[int],
    n_qubits: int | None = None,
    iterations: int | None = None,
) -> GroverResult:
    """Grover's search algorithm.

    Finds a marked item among ``N = 2**n`` candidates using O(sqrt(N)) oracle
    calls instead of O(N) classically. The optimal number of iterations is
    ``floor(pi/4 * sqrt(N/m))`` for ``m`` marked items.

    Args:
        marked: Indices of the marked items.
        n_qubits: Register size. Inferred from ``marked`` if omitted.
        iterations: Number of Grover iterations. Computed optimally if omitted.

    Returns:
        A :class:`GroverResult` with the marked index and the measured
        success probability.
    """
    if not marked:
        raise ValueError("At least one marked item is required")

    n = n_qubits or max(marked).bit_length()
    if n <= 0:
        raise ValueError("Register size must be positive")

    marked_set = {int(m) for m in marked if m < (1 << n)}
    if not marked_set:
        raise ValueError("No marked item falls inside the register range")

    N = 1 << n
    m = len(marked_set)
    if iterations is None:
        iterations = max(1, int(math.floor(math.pi / 4 * math.sqrt(N / m))))

    register = QuantumRegister(n, "grover")
    state = QuantumState(register)

    for q in range(n):
        state.h(q)

    for _ in range(iterations):
        _apply_phase_oracle(state, marked_set, n)
        _apply_diffusion(state, n)

    probs = state.probabilities()
    best = int(np.argmax(probs))
    return GroverResult(
        marked_index=best,
        marked_bitstring=format(best, f"0{n}b"),
        iterations=iterations,
        probabilities=probs,
        success_probability=float(probs[best]),
        queries=1,
        oracle_calls=iterations,
    )


def _apply_phase_oracle(state: QuantumState, marked: set[int], n: int) -> None:
    """Flip the sign of the marked basis states."""
    for target in marked:
        state.state[target] = -state.state[target]


def _apply_diffusion(state: QuantumState, n: int) -> None:
    """Apply the diffusion operator ``2|s><s| - I``."""
    dim = state.dim
    mean = complex(np.sum(state.state)) / dim
    state.state = 2 * mean - state.state
    norm = float(np.linalg.norm(state.state))
    if norm > 0:
        state.state = state.state / norm


# ==========================================================================
# Quantum Fourier transform and phase estimation
# ==========================================================================


def quantum_fourier_transform(
    state: QuantumState, qubits: Sequence[int] | None = None
) -> QuantumState:
    """Apply the quantum Fourier transform (QFT) in place.

    The QFT maps ``|x>`` to ``(1/sqrt(N)) sum_y exp(2*pi*i*x*y/N) |y>`` and
    requires O(n^2) gates versus O(N log N) classical operations. The circuit
    applies a Hadamard to each qubit followed by controlled phase rotations of
    ``pi/2**(j-k)``, then reverses the qubit order to match the standard DFT
    output convention. Qubit 0 is the least significant bit.

    Args:
        state: The register to transform.
        qubits: Optional subset of qubits to transform.

    Returns:
        The same state object, mutated in place.
    """
    indices = list(range(state.n)) if qubits is None else list(qubits)
    m = len(indices)

    for j in reversed(range(m)):
        state.h(indices[j])
        for k in reversed(range(j)):
            state.cp(math.pi / (1 << (j - k)), indices[j], indices[k])

    for i in range(m // 2):
        state.swap(indices[i], indices[m - 1 - i])
    return state


def inverse_quantum_fourier_transform(
    state: QuantumState, qubits: Sequence[int] | None = None
) -> QuantumState:
    """Apply the inverse QFT in place.

    The exact inverse of :func:`quantum_fourier_transform`, mapping
    ``|x>`` to ``(1/sqrt(N)) sum_y exp(-2*pi*i*x*y/N) |y>``.
    """
    indices = list(range(state.n)) if qubits is None else list(qubits)
    m = len(indices)

    for i in range(m // 2):
        state.swap(indices[i], indices[m - 1 - i])

    # The inverse undoes the forward circuit in reverse order: the last
    # Hadamard applied (on the lowest qubit) is undone first, and the
    # controlled phases belonging to qubit j are undone before its Hadamard.
    for j in range(m):
        for k in range(j):
            state.cp(-math.pi / (1 << (j - k)), indices[j], indices[k])
        state.h(indices[j])
    return state


def phase_estimation(
    eigenvalue_phase: float,
    precision_qubits: int = 4,
) -> tuple[list[float], np.ndarray]:
    """Estimate the phase of an eigenvalue of a unitary operator.

    Uses the standard phase estimation routine: prepare an eigenstate of the
    unitary with eigenvalue ``exp(2*pi*i * phase)``, then read the phase from
    the precision register.

    Args:
        eigenvalue_phase: The phase in [0, 1) of the eigenvalue.
        precision_qubits: Width of the precision register. The estimate is
            accurate to ``1/2**precision_qubits``.

    Returns:
        A tuple ``(estimates, probabilities)`` where ``estimates`` holds the
        discrete phase estimates and ``probabilities`` the measurement
        distribution over the precision register.
    """
    if not 0.0 <= eigenvalue_phase < 1.0:
        raise ValueError("phase must lie in [0, 1)")
    if precision_qubits < 1:
        raise ValueError("precision_qubits must be positive")

    total = precision_qubits + 1
    register = QuantumRegister(total, "pe")
    state = QuantumState(register)

    # The system qubit (index precision_qubits) is prepared in the eigenstate
    # |1> of the unitary, whose eigenvalue is exp(2*pi*i*phase).
    state.x(precision_qubits)
    for q in range(precision_qubits):
        state.h(q)

    # Controlled phase rotations. The system qubit controls the phase applied
    # to each precision qubit, so the amplitude of |x>|1> picks up
    # exp(2*pi*i*phase*x).
    for k in range(precision_qubits):
        theta = 2 * math.pi * eigenvalue_phase * (1 << k)
        state.cp(theta, precision_qubits, k)

    inverse_quantum_fourier_transform(state, list(range(precision_qubits)))

    dim = 1 << precision_qubits
    # Marginalise the system qubit out to read the precision register.
    precision_probs = state.marginal(list(range(precision_qubits)))

    estimates = [k / dim for k in range(dim)]
    return estimates, precision_probs


# ==========================================================================
# Shor factoring
# ==========================================================================


@dataclass
class PeriodResult:
    """Outcome of a period-finding subroutine."""

    period: int
    success: bool
    candidates_tested: list[int] = field(default_factory=list)


def _modular_exponentiation(base: int, exponent: int, modulus: int) -> int:
    """Compute ``base ** exponent mod modulus`` by square-and-multiply."""
    if modulus == 1:
        return 0
    result = 1
    b = base % modulus
    e = exponent
    while e > 0:
        if e & 1:
            result = (result * b) % modulus
        b = (b * b) % modulus
        e >>= 1
    return result


def _find_period_classical(factor: int, N: int) -> int:
    """Brute-force the multiplicative order of ``factor`` modulo ``N``."""
    if math.gcd(factor, N) != 1:
        raise ValueError("factor must be coprime to N")
    value = 1
    for r in range(1, N + 1):
        value = (value * factor) % N
        if value == 1:
            return r
    raise ValueError("Period not found; order exceeds N")


def _continued_fraction_quotients(
    numerator: int, denominator: int, max_terms: int = 16
) -> list[int]:
    """Return the partial quotients of a simple continued fraction.

    This is the classical post-processing Shor's algorithm applies to a
    measured rational. The convergents built from these quotients are the
    best available rational approximations to the true phase, and one of
    them yields the period.

    Args:
        numerator: The numerator of the ratio.
        denominator: The denominator of the ratio, which must be non-zero.
        max_terms: Cap on the number of quotients produced.

    Returns:
        The partial quotients, starting with the integer part.

    Raises:
        ValueError: If the denominator is zero.
    """
    if denominator == 0:
        raise ValueError("denominator must be non-zero")

    quotients: list[int] = []
    a, b = numerator, denominator
    while b and len(quotients) < max_terms:
        q = a // b
        quotients.append(q)
        a, b = b, a - q * b
    return quotients


def _convergent_numerators(quotients: Sequence[int]) -> list[int]:
    """Return the numerators of the convergents of a continued fraction.

    Each convergent is the best rational approximation available at that
    depth. For Shor's algorithm, one whose numerator divides the modulus
    reveals the order.
    """
    results: list[int] = []
    h_prev, h = 0, 1
    for q in quotients:
        h_prev, h = h, q * h + h_prev
        results.append(h)
    return results


def shors_factoring(N: int) -> list[int]:
    """Factor ``N`` using Shor's algorithm (classical period finding).

    The quantum subroutine for order finding is simulated here by exact
    classical computation, which is feasible for the small integers used in
    tests. The post-processing (continued fractions, gcd checks) is the same
    logic used on hardware.

    Args:
        N: The composite integer to factor.

    Returns:
        A list of two nontrivial factors whose product is N, or an empty
        list if no factor was found in this run.
    """
    if N < 4:
        raise ValueError("N must be a composite integer greater than 3")
    if N % 2 == 0:
        return [2, N // 2]

    for a in range(2, min(N, 60)):
        g = math.gcd(a, N)
        if g > 1:
            return [g, N // g]

    for a in range(2, min(N, 60)):
        if math.gcd(a, N) != 1:
            continue
        period = _find_period_classical(a, N)
        if period % 2 == 1:
            continue
        half = period // 2
        x = _modular_exponentiation(a, half, N)
        g = math.gcd(x - 1, N)
        if 1 < g < N:
            return [g, N // g]
    return []


def factor_with_period_analysis(N: int, base: int) -> PeriodResult:
    """Run one order-finding attempt for ``base`` modulo ``N``.

    Exposes the period, the continued fraction denominators, and whether a
    nontrivial factor was obtained, mirroring the steps of Shor's algorithm.

    Args:
        N: The composite integer.
        base: The random base to test.

    Returns:
        A :class:`PeriodResult` describing the attempt.
    """
    g = math.gcd(base, N)
    if g > 1:
        return PeriodResult(period=0, success=1 < g < N, candidates_tested=[g, N // g])

    period = _find_period_classical(base, N)
    if period % 2 == 1:
        return PeriodResult(period=period, success=False)

    half = period // 2
    x = _modular_exponentiation(base, half, N)
    g = math.gcd(x - 1, N)
    # The convergents of x/N are the rational approximations that would recover
    # the period from a measured value on real hardware.
    convergents = _convergent_numerators(_continued_fraction_quotients(x, N))
    success = 1 < g < N
    candidates = [g, N // g] if success else []
    return PeriodResult(
        period=period,
        success=success,
        candidates_tested=candidates + convergents,
    )


# ==========================================================================
# QAOA for MaxCut
# ==========================================================================


@dataclass
class QAOAResult:
    """Outcome of a QAOA optimisation run."""

    best_bitstring: str
    best_value: float
    best_energy: float
    expectation_history: list[float]
    optimal_gamma_angles: list[float]
    optimal_beta_angles: list[float]
    iterations: int
    graph_edges: list[tuple[int, int]]


def maxcut_value(bitstring: str, edges: Sequence[tuple[int, int]]) -> int:
    """Compute the MaxCut value of a bit assignment.

    Each edge crossing the cut contributes 1.

    Args:
        bitstring: A string of 0s and 1s.
        edges: Pairs of vertex indices.

    Returns:
        The number of edges crossing the cut.
    """
    return sum(1 for u, v in edges if bitstring[u] != bitstring[v])


def qaoa_maxcut(
    edges: Sequence[tuple[int, int]],
    n_qubits: int,
    p_layers: int = 2,
    max_iterations: int = 300,
    learning_rate: float = 0.05,
    seed: int = 42,
) -> QAOAResult:
    """Solve MaxCut with the Quantum Approximate Optimization Algorithm.

    QAOA alternates a cost Hamiltonian (phase separator) with a transverse
    field Hamiltonian (mixer) for ``p`` layers, then optimises the 2p angles
    with a classical parameter-shift rule.

    Args:
        edges: Graph edges as vertex index pairs.
        n_qubits: Number of vertices in the register.
        p_layers: Depth of the QAOA circuit.
        max_iterations: Maximum parameter-shift iterations.
        learning_rate: Gradient step size for the angle update.
        seed: Random seed for reproducible initialisation.

    Returns:
        A :class:`QAOAResult` with the best cut found and the angle history.
    """
    if not edges:
        raise ValueError("At least one edge is required")
    if p_layers < 1:
        raise ValueError("p_layers must be positive")

    rng = np.random.default_rng(seed)
    gammas = rng.uniform(0, 2 * math.pi, p_layers)
    betas = rng.uniform(0, math.pi, p_layers)

    edges = [(u, v) for u, v in edges if u < n_qubits and v < n_qubits]
    expectation_history: list[float] = []

    for _ in range(max_iterations):
        grads_g = np.zeros(p_layers)
        grads_b = np.zeros(p_layers)

        for layer in range(p_layers):
            shift = 0.01
            g_plus, g_minus = gammas.copy(), gammas.copy()
            b_plus, b_minus = betas.copy(), betas.copy()
            g_plus[layer] += shift
            g_minus[layer] -= shift
            b_plus[layer] += shift
            b_minus[layer] -= shift

            grads_g[layer] = (
                _qaoa_expectation(edges, n_qubits, g_plus, betas)
                - _qaoa_expectation(edges, n_qubits, g_minus, betas)
            ) / (2 * shift)
            grads_b[layer] = (
                _qaoa_expectation(edges, n_qubits, gammas, b_plus)
                - _qaoa_expectation(edges, n_qubits, gammas, b_minus)
            ) / (2 * shift)

        # Gradient ascent: the MaxCut cost is maximised, so the angles move
        # along the gradient of the cut value.
        gammas = gammas + learning_rate * grads_g
        betas = betas + learning_rate * grads_b
        expectation_history.append(_qaoa_expectation(edges, n_qubits, gammas, betas))

    state = _qaoa_state(edges, n_qubits, gammas, betas)
    probs = state.probabilities()
    best = int(np.argmax(probs))
    bitstring = format(best, f"0{n_qubits}b")
    value = maxcut_value(bitstring, edges)
    energy = -value

    return QAOAResult(
        best_bitstring=bitstring,
        best_value=value,
        best_energy=energy,
        expectation_history=expectation_history,
        optimal_gamma_angles=[float(g) for g in gammas],
        optimal_beta_angles=[float(b) for b in betas],
        iterations=max_iterations,
        graph_edges=edges,
    )


def _qaoa_state(
    edges: Sequence[tuple[int, int]],
    n_qubits: int,
    gammas: np.ndarray,
    betas: np.ndarray,
) -> QuantumState:
    """Build the QAOA state vector for the given angles.

    The cost unitary is ``prod_{(u,v)} exp(-i*2*gamma*CP(u,v))`` and the mixer
    is ``prod_q exp(-i*2*beta*X_q)``, both applied to the uniform
    superposition.
    """
    register = QuantumRegister(n_qubits, "qaoa")
    state = QuantumState(register)
    for q in range(n_qubits):
        state.h(q)

    for layer in range(len(gammas)):
        gamma = float(gammas[layer])
        beta = float(betas[layer])
        for u, v in edges:
            state.cp(-2 * gamma, u, v)
        for q in range(n_qubits):
            state.rx(2 * beta, q)
    return state


def _qaoa_expectation(
    edges: Sequence[tuple[int, int]],
    n_qubits: int,
    gammas: np.ndarray,
    betas: np.ndarray,
) -> float:
    """Expectation value of the MaxCut cost Hamiltonian."""
    state = _qaoa_state(edges, n_qubits, gammas, betas)
    probs = state.probabilities()
    total = 0.0
    for i, prob in enumerate(probs):
        if prob < 1e-12:
            continue
        bits = format(i, f"0{n_qubits}b")
        total += prob * maxcut_value(bits, edges)
    return float(total)


# ==========================================================================
# VQE
# ==========================================================================


def vqe_h2_ground_energy(
    iterations: int = 200, seed: int = 7, restarts: int = 8
) -> dict[str, object]:
    """Variational Quantum Eigensolver for the H2 molecule Hamiltonian.

    Uses the STO-3G Hamiltonian
    ``H = -1.0524 I + 0.3974 Z1 - 0.3974 Z0 - 0.0118 Z0Z1 + 0.1805 X0X1``
    with a two-parameter hardware-efficient ansatz: ``ry(theta)`` on qubit 0,
    a CNOT, then ``ry(phi)`` on qubit 1. Gradients are obtained with the
    parameter-shift rule. Because the variational energy surface has local
    minima, the optimiser is run from several random restarts and the best
    result is kept.

    The exact ground energy of this Hamiltonian is -1.855638 Hartree.

    Args:
        iterations: Number of parameter-shift steps per restart.
        seed: Random seed for the initial angles.
        restarts: Number of independent random restarts.

    Returns:
        A dict with the estimated ground energy, the optimal angles, the
        convergence history, and the exact reference energy.
    """
    rng = np.random.default_rng(seed)
    best_energy = float("inf")
    best_angles = (0.0, 0.0)
    best_history: list[float] = []

    for _ in range(max(1, restarts)):
        theta = float(rng.uniform(0, 2 * math.pi))
        phi = float(rng.uniform(0, 2 * math.pi))
        history: list[float] = []

        for _ in range(iterations):
            theta -= 0.08 * _h2_grad(theta, phi, 0)
            phi -= 0.08 * _h2_grad(theta, phi, 1)
            history.append(_h2_energy(theta, phi))

        # Coarse-to-fine local refinement around the restart's optimum.
        theta, phi = _refine_angles(theta, phi)

        energy = _h2_energy(theta, phi)
        if energy < best_energy:
            best_energy = energy
            best_angles = (theta, phi)
            best_history = history

    return {
        "energy": best_energy,
        "optimal_theta": best_angles[0],
        "optimal_phi": best_angles[1],
        "iterations": iterations,
        "restarts": restarts,
        "energy_history": best_history,
        "exact_ground_energy": -1.855638,
        "hamiltonian": {
            "identity": -1.0524,
            "Z0": -0.3974,
            "Z1": 0.3974,
            "Z0Z1": -0.0118,
            "X0X1": 0.1805,
        },
    }


def _refine_angles(theta: float, phi: float) -> tuple[float, float]:
    """Polish a variational minimum with a shrinking local grid search."""
    step = 0.1
    for _ in range(6):
        improved = False
        for dt in (-step, 0.0, step):
            for dp in (-step, 0.0, step):
                if _h2_energy(theta + dt, phi + dp) < _h2_energy(theta, phi) - 1e-15:
                    theta, phi = theta + dt, phi + dp
                    improved = True
        if not improved:
            step /= 2
    return theta, phi


def _h2_state(theta: float, phi: float) -> QuantumState:
    """Prepare the two-parameter VQE ansatz state."""
    register = QuantumRegister(2, "h2")
    state = QuantumState(register)
    state.ry(theta, 0)
    state.cnot(0, 1)
    state.ry(phi, 1)
    return state


def _h2_energy(theta: float, phi: float) -> float:
    """Evaluate the H2 Hamiltonian expectation for the ansatz state.

    In the computational basis the Hamiltonian is

    ``[[-1.0642,    0,      0,      0.1805],
        [   0,    -0.2458,   0.1805, 0    ],
        [   0,     0.1805, -1.8354, 0    ],
        [0.1805,    0,      0,    -1.0642]]``

    where qubit 0 is the least significant bit. The diagonal contributions
    are expanded from the Pauli terms and the ``X0 X1`` coupling contributes
    through the interference of the paired amplitudes.
    """
    state = _h2_state(theta, phi)
    probs = state.probabilities()
    w00, w01, w10, w11 = probs[0], probs[1], probs[2], probs[3]

    diagonal = (
        -1.0524
        + 0.3974 * (w00 + w01)
        - 0.3974 * (w10 + w11)
        - 0.3974 * (w00 + w10)
        + 0.3974 * (w01 + w11)
        - 0.0118 * (w00 - w01 - w10 + w11)
    )

    # <X0X1> mixes |00> with |11> and |01> with |10>.
    overlap = 2 * (
        np.real(state.state[0].conj() * state.state[3])
        + np.real(state.state[1].conj() * state.state[2])
    )
    return float(diagonal + 0.1805 * overlap)


def _h2_grad(theta: float, phi: float, which: int) -> float:
    """Parameter-shift gradient for one of the two ansatz angles."""
    shift = math.pi / 2
    if which == 0:
        plus = _h2_energy(theta + shift, phi)
        minus = _h2_energy(theta - shift, phi)
    else:
        plus = _h2_energy(theta, phi + shift)
        minus = _h2_energy(theta, phi - shift)
    return (plus - minus) / 2


# ==========================================================================
# Grover walk search
# ==========================================================================


def grover_walk_search(
    graph_edges: Sequence[tuple[int, int]],
    n_vertices: int,
    marked: Sequence[int],
    steps: int = 20,
) -> dict[str, object]:
    """Search a graph with a continuous-time Grover walk.

    A search Hamiltonian ``H = -gamma A + sum_{w in marked} |w><w|`` is
    propagated on the graph, with the marked vertices driving a
    Grover-diffusion resonance.

    Args:
        graph_edges: Undirected graph edges.
        n_vertices: Number of vertices.
        marked: Vertices to search for.
        steps: Number of Trotter time steps.

    Returns:
        A dict with the probability of measuring a marked vertex over time
        and the peak success probability.
    """
    if not marked:
        raise ValueError("At least one marked vertex is required")

    dim = 1 << n_vertices
    adjacency = np.zeros((dim, dim), dtype=complex)
    for u, v in graph_edges:
        adjacency[1 << u, 1 << v] = 1
        adjacency[1 << v, 1 << u] = 1

    oracle = np.zeros((dim, dim), dtype=complex)
    for w in marked:
        oracle[1 << w, 1 << w] = 1

    gamma = 1.0 / (len(graph_edges) or 1)
    hamiltonian = -gamma * adjacency + oracle

    psi = np.ones(dim, dtype=complex) / math.sqrt(dim)
    dt = 0.1
    history: list[float] = []

    for _ in range(steps):
        psi = _expm_approx(hamiltonian, dt) @ psi
        norm = np.linalg.norm(psi)
        if norm > 0:
            psi = psi / norm
        history.append(float(sum(abs(psi[1 << w]) ** 2 for w in marked)))

    return {
        "n_vertices": n_vertices,
        "marked": list(marked),
        "steps": steps,
        "success_probabilities": history,
        "peak_probability": max(history) if history else 0.0,
    }


def _expm_approx(matrix: np.ndarray, dt: float, terms: int = 12) -> np.ndarray:
    """Matrix exponential via a truncated Taylor series."""
    result = np.eye(matrix.shape[0], dtype=complex)
    term = np.eye(matrix.shape[0], dtype=complex)
    scaled = matrix * dt
    for k in range(1, terms):
        term = term @ scaled / k
        result = result + term
    return result


# ==========================================================================
# Bell states
# ==========================================================================


def bell_state_circuit(label: str) -> list[str]:
    """Return a gate list constructing a Bell state.

    The circuits are built from ``phi+ = (|00> + |11>)/sqrt(2)`` by applying a
    Pauli operator: ``Z`` on qubit 0 gives ``phi-``, ``X`` on qubit 1 gives
    ``psi+``, and ``X`` on qubit 1 followed by ``Z`` on qubit 1 gives ``psi-``.

    Args:
        label: One of ``phi+``, ``phi-``, ``psi+`` or ``psi-``.

    Returns:
        The gate names applied in order.

    Raises:
        ValueError: If the Bell label is unknown.
    """
    valid = {"phi+", "phi-", "psi+", "psi-"}
    if label not in valid:
        raise ValueError(f"Bell state must be one of {sorted(valid)}")

    circuit = ["H(0)", "CNOT(0,1)"]
    if label in ("psi+", "psi-"):
        circuit.append("X(1)")
    if label in ("phi-", "psi-"):
        circuit.append("Z(0)" if label == "phi-" else "Z(1)")
    return circuit


def bell_fidelity(state: QuantumState, label: str) -> float:
    """Fidelity of ``state`` against a target Bell state."""
    register = QuantumRegister(2, "bell")
    target = QuantumState(register)
    if label == "phi+":
        target.state = np.array([1, 0, 0, 1], dtype=complex) / math.sqrt(2)
    elif label == "phi-":
        target.state = np.array([1, 0, 0, -1], dtype=complex) / math.sqrt(2)
    elif label == "psi+":
        target.state = np.array([0, 1, 1, 0], dtype=complex) / math.sqrt(2)
    else:
        target.state = np.array([0, 1, -1, 0], dtype=complex) / math.sqrt(2)
    return state.fidelity(target)


# ==========================================================================
# Quantum teleportation
# ==========================================================================


@dataclass
class TeleportationResult:
    """Outcome of a teleportation run."""

    success: bool
    measured_bits: tuple[int, int, int]
    reconstructed: np.ndarray
    fidelity: float


def teleport_state(
    input_vector: Sequence[complex],
    seed: int = 0,
) -> TeleportationResult:
    """Teleport an arbitrary single-qubit state using shared entanglement.

    Implements the Bennett et al. protocol. Qubit 0 carries the state to be
    teleported, qubit 1 is the sender's half of a shared EPR pair and qubit 2
    is the receiver's half. The Bell measurement on qubits 0 and 1 yields two
    classical bits that determine the receiver's correction: ``Z`` when the
    first Bell bit is set and ``X`` when the second is.

    Args:
        input_vector: A normalised 2-component state vector.
        seed: Random seed for the Bell measurement outcome.

    Returns:
        A :class:`TeleportationResult` with the classical bits and the
        fidelity of the reconstructed state.

    Raises:
        ValueError: If the input vector is malformed or unnormalised.
    """
    vector = np.asarray(input_vector, dtype=complex)
    if vector.size != 2:
        raise ValueError("input_vector must have two components")
    norm = float(np.linalg.norm(vector))
    if not math.isclose(norm, 1.0, abs_tol=1e-6):
        raise ValueError("input_vector must be normalised")

    # Qubits: 0 = input, 1 = sender's half, 2 = receiver's half.
    register = QuantumRegister(3, "teleport")
    state = QuantumState(register)
    phi_plus = np.array([1, 0, 0, 1], dtype=complex) / math.sqrt(2)
    state.set_state(np.kron(vector, phi_plus))

    # Bell measurement basis change on qubits 0 and 1.
    state.cnot(0, 1)
    state.h(0)

    # Sample the outcome. In this basis the register factorises as
    # |m0 m1>_01 (x) receiver, where the first Bell bit is qubit 0.
    rng = np.random.default_rng(seed)
    outcome = int(rng.choice(8, p=state.probabilities()))
    m0 = outcome & 1
    m1 = (outcome >> 1) & 1
    m2 = (outcome >> 2) & 1

    # Feed-forward correction on the receiver's qubit.
    if m1:
        state.x(2)
    if m0:
        state.z(2)

    # Marginalise qubits 0 and 1 to read out the receiver's qubit.
    receiver = np.zeros(2, dtype=complex)
    for i in range(8):
        if not ((i >> 2) & 1):
            receiver[0] += state.state[i]
        else:
            receiver[1] += state.state[i]
    norm = float(np.linalg.norm(receiver))
    receiver = receiver / norm if norm > 1e-9 else np.array([1, 0], dtype=complex)

    fidelity = float(abs(np.vdot(vector, receiver)) ** 2)
    return TeleportationResult(
        success=fidelity > 0.999,
        measured_bits=(m2, m1, m0),
        reconstructed=receiver,
        fidelity=fidelity,
    )


# ==========================================================================
# Oracle builders
# ==========================================================================


def hidden_string_oracle(secret: int) -> Callable[[list[int]], int]:
    """Build a Bernstein-Vazirani oracle for a hidden string."""

    def oracle(bits: list[int]) -> int:
        value = 0
        for i, bit in enumerate(bits):
            secret_bit = (secret >> (len(bits) - 1 - i)) & 1
            value ^= bit & secret_bit
        return value

    return oracle


def constant_oracle(value: int) -> Callable[[list[int]], int]:
    """Build a Deutsch-Jozsa constant oracle."""

    def oracle(bits: list[int]) -> int:
        return value

    return oracle


def parity_oracle(bits: list[int]) -> int:
    """Parity function, which is a valid Deutsch-Jozsa linear oracle."""
    return sum(bits) % 2


def simon_period_oracle(
    s: int, n: int
) -> tuple[Callable[[list[int]], list[int]], list[list[int]]]:
    """Build a genuinely 2-to-1 Simon oracle with hidden period ``s``.

    The oracle projects the input onto a basis ``{p1..p_{n-1}}`` of the
    orthogonal complement ``s-perp``, so ``f(x) = f(y)`` exactly when
    ``x XOR y`` lies in ``span{s}``. That makes ``f`` two-to-one with hidden
    period ``s``, returning ``n - 1`` output bits.

    Args:
        s: The non-zero hidden period as an integer bit string.
        n: The register width.

    Returns:
        A tuple ``(oracle, basis)`` where ``oracle`` maps a list of n bits to
        a list of ``n - 1`` bits.

    Raises:
        ValueError: If ``s`` is zero, too wide, or no full basis is found.
    """
    if s == 0:
        raise ValueError("the hidden period must be non-zero")
    if s >> n:
        raise ValueError("the hidden period must fit in n bits")

    svec = [(s >> (n - 1 - k)) & 1 for k in range(n)]
    basis = _gf2_null_space([svec], n)

    if len(basis) != n - 1:
        raise ValueError(
            f"could not build a full basis of s-perp (got {len(basis)} of {n - 1})"
        )

    def oracle(bits: list[int]) -> list[int]:
        return [sum(b & v for b, v in zip(bits, p)) % 2 for p in basis]

    return oracle, basis
