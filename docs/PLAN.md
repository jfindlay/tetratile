# PLAN: Discrete-PGA code refactor

Handoff for `@build`. The mathematics doc (`docs/mathematics.rst`) and the
agent summary (`AGENTS.md`) have been revised so that **discrete plane-based
geometric algebra** (`Cl(N,0,1)`, lattice-stabilising versors) is the primary
formulation, with `Z^N ⋊ B_N^+` and the rotation matrices retained as bridges.
This plan reshapes the *code* to match, so the implementation expresses the
chosen foundation rather than only the bridge.

The refactor is **behaviour-preserving**. Every rotation and translation must
produce byte-identical results to the current implementation. The existing test
suite is the conformance oracle (see "Conformance" below).

## Why (the load-bearing rationale)

- The doc now leads with motors/versors; the code still leads with the
  semidirect-product split (`Translation`, `Rotation`, a coordinate rotation
  formula). The code should make the versor structure visible, the same way
  `Square` / `frozenset[Square]` / `Translation` already make their concepts
  visible (design principle 1, "transparent mathematical types").
- The single most valuable code change is the **integer rotor**: rotation can be
  computed by the sandwich of the unnormalised rotor `U = 1 + e_12` with a final
  integer division by `|U|^2 = 2`. This is lattice-exact with no floating point
  and no `Decimal` for the rotation step — see `docs/mathematics.rst`
  `.. _discrete-rotor:` for the `√2`-cancellation proof.

## Key arithmetic fact (already verified)

For a planar vector `v = x·e1 + y·e2`:

    U v Ũ = (1 + e12)(x e1 + y e2)(1 − e12) = 2·(y e1 − x e2)

so `R v R̃ = (U v Ũ) / |U|² = (y, −x)` — identical to the current CW quarter-turn
`(x, y) ↦ (y, −x)`. Half-integers map to half-integers exactly by the same
cancellation. The `Decimal`-origin design and the integer-rotor design are
arithmetically equivalent; neither rounds.

## Scope decision still open for the implementer

Two viable end-states; pick one and note it in the commit. **Recommended: Option
A** (smaller, lower-risk, preserves the type-honest split the game's behaviour
depends on).

- **Option A — versor interpretation layer, types unchanged.** Keep
  `Translation` / `Rotation` / `EigenTransformation` exactly as they are. Add an
  internal `Motor`/`Versor` representation used *inside* `Polyomino.rotate` (and
  optionally a `_versor` module) to compute the sandwich. Public types and the
  `match`/`case` dispatch in `move_piece` are untouched. The GA structure becomes
  visible in the rotation implementation and in a new `_versor` module, without
  disturbing the input layer.

- **Option B — Motor as a first-class type.** Introduce `Motor`/`Versor` as a
  public type and express `EigenTransformation` generators as motors. Larger
  blast radius: touches `move_piece` dispatch, `input_handler`, `agent` Action
  mapping, and `_rotation_state`. Only take this if the unification is judged
  worth the churn. **Caution:** the doc deliberately keeps the
  `Translation | Rotation` split because the game treats the two generator
  families differently (translation succeeds-or-blocks; rotation may kick). A
  `Motor` type that erases that distinction would regress design principle 1 and
  the kick-handling clarity. If Option B is taken, the split must be preserved at
  the input/dispatch layer even if motors back it.

## Tasks (Option A staging)

1. **Add a `_versor` module (or section) with the integer rotor.**
   - Represent the even-subalgebra elements needed: scalar + `e12` (Euclidean
     rotor) and the null bivectors `e01`, `e02` (translators) if Option B; for
     Option A only the rotor sandwich on a coordinate pair is required.
   - Provide an integer-exact `rotate_point(x, y, steps, plane=(0,1)) -> (x', y')`
     implementing `U v Ũ` with the divide-by-2 normalisation. Keep it `int`-only
     for integer inputs; accept the half-integer pivot via the existing
     pivot-frame translation (subtract origin, rotate, add origin) — the pivot
     subtraction already yields integer or half-integer coordinates.
   - Docstring: rST, cross-reference `docs/mathematics.rst` `.. _discrete-rotor:`
     for the proof (inline doc stays thin per `STYLE-DOC.md` §1).

2. **Rewire `Polyomino.rotate` to call the rotor sandwich.**
   - Replace the coordinate formula
     `int(d·(y−oy)+ox), int(−d·(x−ox)+oy)` with the `_versor` call.
   - Preserve the `kick: bool` parameter and `_boundary_kicks` flow unchanged.
   - The `Decimal` origin stays for now (it still carries the pivot); the rotor
     does not require removing it. Removing `Decimal` is a *separate, optional*
     follow-up once the rotor path is proven — do not bundle it.

3. **Generalise the `plane` selection (optional, N-d readiness).**
   - Thread a `plane: tuple[int, int]` through `rotate_point` defaulting to
     `(0, 1)` so the 2D path is unchanged but the N-d hook from the doc exists in
     code. Do not change `Rotation`'s public shape unless doing Option B.

4. **Docstrings and comments.**
   - Update `Polyomino.rotate`, `Translation`, `Rotation` docstrings to name the
     versor interpretation and point to the doc. Keep the bridge language
     (`Z^2 ⋊ C_4`, `C_4`) — it is still accurate and is the type's contract.

## Conformance (how to verify — do not skip)

The whole refactor lives or dies on exactness. Verify in this order:

- `uv run pytest tests/integration/test_rotation_free.py tests/integration/test_rotation_edge.py tests/integration/test_srs_rotation.py`
  — these exercise rotation and boundary kicks; they are the primary oracle.
- `uv run pytest tests/` — full suite must stay green.
- `uv run mypy src/` — the `int`-only rotor must type-check without `Any`.
- `uv run ruff check src/ tests/` and `uv run ruff format src/ tests/ --check`.

If any rotation test changes output, the rotor implementation is wrong — the
math proof guarantees identical results. Treat a diff as a bug in the refactor,
not a test to update.

## Explicitly out of scope

- Removing `Decimal` (separate follow-up, only after rotor path proven).
- Any change to gameplay, gravity, row removal, rendering, or the input/agent
  protocol.
- Conformal GA. Not used; not relevant unless a continuous-physics extension is
  added later.

## Exit

Rolling-context lifecycle (`STYLE-DOC.md` §3): this PLAN's content exits by
landing in code (the refactor) and by the durable rationale already living in
`docs/mathematics.rst`. Delete this file at merge once the refactor lands.
