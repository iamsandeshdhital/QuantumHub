# Architecture

## Layers

```
                    HTTP
                     |
        +------------+-------------+
        |                          |
   HTML templates              JSON API
        |                          |
        +------------+-------------+
                     |
              app.py (routes)
                     |
     +---------------+----------------+
     |               |                |
 papers.py     projects.py       algorithms.py
     |               |                |
     +-------+-------+          statevector.py
             |                            |
          data/*.json              numpy
```

Dependencies point downward only. `statevector.py` imports nothing from the
rest of the package. `algorithms.py` imports only `statevector`. The data
modules import nothing from the algorithms. The web layer is the only place
that knows about all of them.

## Modules

### `quantumhub/statevector.py`

The numerical core. A dense complex statevector of size `2**n`.

Qubit 0 is the **least significant bit** of the state index, so the index of
`|q_n ... q_1 q_0>` is `q_0 + 2*q_1 + ... + 2^(n-1) * q_n`.

Gates come in three implementations:

1. **Direct index iteration** (`cp`, `apply_controlled_x`, `toffoli`) for gates
   whose semantics are easiest to state positionally. O(2^n), order-independent.
2. **Stride iteration** (`apply_single`) for single-qubit gates. O(2^n).
3. **Block iteration** (`apply_two_qubit`) for 4x4 matrices. Enumerates every
   index with both pair bits clear, then applies the matrix to the four
   amplitudes of that block. When the caller's first argument is the
   lower-indexed qubit, the matrix is relabelled by conjugating with the pair
   swap.

`marginal` traces out a subset of qubits. It transposes the tensor so the kept
axes lead, squares the amplitudes, sums over the traced axes, then scatters the
result into a qubit-number-indexed array. The returned array is always indexed
so that **bit j of the index is qubit j**, which is the same convention as
`probabilities()`. This matters: reading a sub-register with a different
convention silently returns a bit-reversed answer.

### `quantumhub/algorithms.py`

Sixteen algorithm implementations. Each returns a dataclass or dict carrying
the quantities needed to judge the result, not just a pass/fail boolean.

Shared helpers:

- `_apply_oracle` implements a black-box oracle by swapping the ancilla
  amplitudes for each input basis state. It must visit each pair once; visiting
  both members undoes the swap.
- `_gf2_null_space` runs Gauss-Jordan elimination over GF(2) to reduced row
  echelon form and reads off one null vector per free column. Used both for
  Simon's period recovery and to generate two-to-one oracles.
- `_modular_exponentiation` uses square-and-multiply for Shor's order finding.

### `quantumhub/papers.py` and `quantumhub/projects.py`

Frozen dataclasses plus a validating loader. The loader is the integrity gate:
it runs on import and raises `DatasetError` or `ProjectDataError` rather than
letting a malformed record reach a request handler.

Search scoring weights a title match at 10, a tag match at 4, an author match
at 3, an organisation match at 2 and an abstract match at 1. Ties break by
year descending, then by id, so results are stable.

### `quantumhub/analytics.py`

Pure functions over sequences of records. No I/O, no Flask. This keeps the
statistics testable without a request context.

## Conventions

**Little-endian qubits.** Qubit 0 is the least significant bit. This matches
NumPy's reshape semantics and makes `state.index` a direct bit read.

**Global phase is not tracked.** Algorithms that return a fidelity normalise
before comparing, since global phase is unobservable.

**Simulator limits are explicit.** `QuantumRegister` raises above 24 qubits
rather than letting the process run out of memory.

**Every algorithm is checked against an independent ground truth.** Not a
recorded expected value. The DFT matrix, brute-force enumeration, and direct
diagonalisation are all used.

## Testing strategy

| Layer | Approach |
| --- | --- |
| Gates | Compared against independently constructed matrices, and against exhaustive basis-state enumeration |
| Marginal | Compared against a brute-force partial trace over every qubit subset |
| Algorithms | Compared against theory: DFT matrix, analytic Grover bound, brute force, exact diagonalisation |
| Datasets | Table-driven validation tests, one per failure mode |
| Catalogue integrity | Asserts every implemented project's module imports and its entry point exists |
| Web | Endpoint-by-endpoint status, content and shape assertions |

The suite runs 423 tests at 92 percent statement and branch coverage.

## Why the oracle is applied by index iteration

A black-box oracle cannot be applied gate-by-gate, because the input register
is in superposition and the function is arbitrary. The only tractable exact
approach on a statevector simulator is to enumerate basis states and swap the
ancilla amplitudes where the oracle fires. This is what `_apply_oracle` does,
and it is why the promise problem oracles are accepted as Python callables.

## Why Simon needs a real two-to-one oracle

A common mistake is to use `f(x) = x XOR s` or `f(x) = x AND s`. Neither is
two-to-one: the first is a bijection, the second has fibres of size `2^(n-1)`
or larger. The correct construction projects onto a basis of `s` orthogonal
complement, which `simon_period_oracle` builds. A test asserts the two-to-one
property before the algorithm is allowed to run, because an oracle that
violates the promise produces a plausible-looking but meaningless answer.

## Known limitations

- Dense simulation is exponential in qubit count.
- No noise model, so the circuits are ideal.
- Shor's order finding is classical; only the post-processing models hardware.
- The paper dataset is a small teaching sample with human-compiled
  bibliographic fields.
