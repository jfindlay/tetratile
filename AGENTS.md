# Agent Guidelines for Tetratile Project

## Project Overview

Tetratile is a tetromino tessellation game built with Python and tkinter.
The implementation is **transparently mathematical by design**: every
significant type and operation maps directly to a named mathematical
concept.  The full mathematical treatment is in ``docs/mathematics.rst``.

## Mathematical Design Principles

These principles govern all design decisions in the codebase.  Code that
deviates from them should be treated as a defect, not a style choice.

### The Transform Group

The game operates on a finite rectangular sublattice
:math:`\mathcal{B} \subset \mathbb{Z}^2` (the board) with y-up Cartesian
orientation (y=0 at the bottom).  Valid piece moves form the **semidirect
product** :math:`G = \mathbb{Z}^2 \rtimes C_4`, where
:math:`\mathbb{Z}^2` is the integer translation group and
:math:`C_4 \cong \mathbb{Z}/4\mathbb{Z}` is the cyclic group of
quarter-turn rotations.  Reflections are excluded — they produce
physically distinct pieces (S ≠ Z, L ≠ J) — so the valid rotation group
is :math:`C_4`, not the full dihedral group :math:`D_4`.  This is why the
game has **7 one-sided** tetrominoes rather than 5 free ones.

### Eigentransformations

An *eigentransformation* is an **atomic generator** of :math:`G` — an
irreducible move from which all compound moves are composed.  The type
alias ``type EigenTransformation = Translation | Rotation`` names this
concept directly.

- ``Translation(dx, dy)``: an element of :math:`\mathbb{Z}^2`.
  ``dx > 0`` is rightward; ``dy > 0`` is upward.  Gravity is
  ``Translation(0, -1)`` — explicitly negative :math:`y`, consistent with
  the y-up convention.
- ``Rotation(steps)``: an element of :math:`C_4`.
  ``steps=+1`` is CW; ``steps=-1`` is CCW.

The operations ``move_left_max``, ``move_right_max``, and ``full_drop``
are **derived** (orbit suprema), not generators.  They belong in
``InputHandler``, not in ``EigenTransformation``.

### The ``multiple`` Field

The scale factor on a generator is always an **integer**.  The term
*multiple* (not *magnitude*) is used precisely to signal this: real-valued
scaling is not valid on the integer lattice :math:`\mathbb{Z}^N`.

### Polyominoes

A polyomino of **ordinal** :math:`n` is a connected finite subset of
:math:`n` unit cells of :math:`\mathbb{Z}^2`.  In code:

- ``Polyomino.squares: frozenset[Square]`` — a ``frozenset`` captures the
  correct set semantics (unordered, no duplicates, immutable).
- ``Square(x, y)`` is a ``NamedTuple`` identifying a unit cell by its
  lower-left corner.
- ``Polyomino.ordinal`` = ``len(squares)``; ``ordinal == 4`` ↔ tetromino.

### The Board as an Occupancy Map

The locked-piece state is a **partial function**
:math:`\mathcal{G}: \mathcal{B} \rightharpoonup \text{PieceName}`,
encoded as ``dict[Square, str]``.  Presence of a key = occupied; absence
= empty.  The **active piece** is tracked separately in
``TetraTile.piece`` and is never written to :math:`\mathcal{G}`.

### Value Semantics

``Polyomino.translate()`` and ``Polyomino.rotate()`` return **new**
``Polyomino`` instances (or ``None`` if blocked).  They do not mutate.
This reflects the group action: applying a group element to a piece yields
a new state.  Value semantics eliminates ``copy.deepcopy``.

### Functional Boundary Kicks

Rotation kicks are **algebraically derived** from the rotated piece's
bounding box versus the grid domain — analogous to a covariant derivative.
No precomputed state-pair tables.  The ``_boundary_kicks`` generator yields
minimal corrective ``Translation`` values in priority order (in-place,
horizontal, vertical, corner), at most four candidates.

### Half-Integer Origins

Pieces whose geometric centre of symmetry is a half-integer point (Z, S,
I, O) store ``origin = (Decimal('-0.5'), Decimal('-0.5'))`` in local
coordinates.  ``Decimal`` arithmetic preserves these values exactly
through all four rotation states, giving exact rotation with no
truncation drift.

### Separation of Concerns

``Grid`` (occupancy map, pure game state) has no Tkinter dependency and is
fully unit-testable.  ``Board`` (Tkinter canvas) is a pure rendering
surface with no game logic.

### Coequal Input Frontends

``HumanInputHandler`` and ``AgentInputHandler`` are structurally identical
subclasses of ``InputHandler``.  All movement methods call
``TetraTile.move_piece()`` with an ``EigenTransformation``; the state
guard (``GameState.running``) lives there.  Neither frontend has
privileged access to the game.

### N-Dimensional Generalization

The design anticipates N-dimensional polyhypercube games.
``Translation`` becomes an N-vector; ``Rotation`` gains a
``plane: tuple[int,int]`` parameter (selecting which of
:math:`\binom{N}{2}` coordinate planes to rotate in).  The rotation
formula is already in the N-dimensional form, hardcoded to plane
``(0, 1)`` for 2D.  ``_boundary_kicks`` extends to all N axes.  The
proper rotation subgroup of the hyperoctahedral group :math:`B_N` is the
target rotation group.

### On Clifford Algebra

Considered and **set aside**.  The discrete lattice constraint
(:math:`\mathbb{Z}^N`, not :math:`\mathbb{R}^N`) and the non-native
encoding of translations in :math:`Cl(N)` make Geometric Algebra less
natural than the direct :math:`\mathbb{Z}^N \rtimes B_N^+` formulation.
GA would be relevant for a continuous-physics extension of the game.

## Docstring Standards

All docstrings follow this format:

```python
"""Succinct one-line summary.

Optional paragraph with more details. Can span multiple lines.

:param param: Description of parameter.
:param param: Description of another parameter.
:returns: Description of return value.
:raises ExceptionType: Description of when this exception is raised.
:attr attr: Description of attribute.
:yields: Description of yielded value.
"""

"""

**Rules:**
1. Succinct summary string as first line (ends with period)
2. Optional detailed paragraph or bullet points
3. Every named code block (package, module, class, function) requires a docstring
4. Public classes/functions: document attributes, parameters, returns, and raises
5. Omit typing in docstrings - code is fully type annotated
6. Use sphinx rST shorthand markup:
   - `:param name:` - function/method parameters
   - `:returns:` - return value
   - `:raises ExceptionType:` - exceptions
   - `:attr name:` - class attributes
   - `:yields:` - generator yield value
   - Cross-references: ``:class:`ClassName` ``, ``:meth:`method` ``
   - Code literals: ```code``` for code/names
   - Parameters with backticks: ```param```
   - Math (rST latex): ``$\mathbb Z^{\mathrm dim}$``

## Type Annotations

- No ``typing.Any`` - use specific types
- Use composition over inheritance for tkinter classes (e.g., StringVar wrappers)
- Use TypedDict for dict structures with known keys
- Use dataclass for data containers

## Code Style

- Line length: 128 characters
- Target Python version: 3.12+
- Use dataclasses where appropriate
- Avoid `isinstance()` checks for enum members - use `match/case`

## Dependencies

- **Runtime**: pydantic>=2.0
- **Build**: hatchling, hatch-vcs
- **Dev**: pytest, pytest-cov, pytest-mock, pyfakefs, ruff, mypy, pyupgrade, tox, tox-uv

## Build & Test Commands

```bash
# Install in development mode
uv pip install -e ".[dev]"

# Run all tests
uv run pytest tests/

# Run unit tests with coverage
uv run pytest tests/unit/ --cov=src/tetratile --cov-report=term-missing

# Run integration tests
uv run pytest tests/integration/

# Run linting
uv run ruff check src/ tests/

# Run formatting check
uv run ruff format src/ tests/ --check

# Run type checking
uv run mypy src/

# Run pyupgrade
uv run pyupgrade --py312-plus src/ tests/

# Run tox (parallel)
tox -p auto

# Run specific tox environment
tox -e lint
tox -e unit

# Build package wheel
uv build --wheel
```

## Project Structure

```
tetratile/
├── docs/
│   └── mathematics.rst  # Mathematical treatise
├── src/tetratile/
│   ├── __init__.py      # Core types, Polyomino, Grid, Board, TetraTile
│   ├── __main__.py      # CLI entry point
│   ├── agent.py         # Agent ABC, Action enum, RandomAgent
│   ├── agent_runner.py  # AgentRunner: wires Agent to TetraTile
│   ├── config.py        # Configuration with Pydantic models
│   ├── config_ui.py     # Preferences dialog
│   ├── event_log.py     # Event logging
│   ├── input_agent.py   # AgentInputHandler (coequal agent frontend)
│   ├── input_handler.py # InputHandler base class with concrete defaults
│   ├── input_human.py   # HumanInputHandler (coequal human frontend)
│   ├── log_viewer.py    # Log viewer widget
│   ├── output.py        # OutputHandler, PrintObserver, AgentOutputHandler
│   └── py.typed         # PEP 561 marker for type checkers
├── tests/
│   ├── unit/
│   │   └── test_tetratile.py  # Unit tests
│   └── integration/
│       ├── conftest.py
│       ├── test_board.py
│       ├── test_config.py
│       ├── test_event_logging.py
│       ├── test_game_flow.py
│       ├── test_observation.py
│       ├── test_rotation_edge.py
│       ├── test_rotation_free.py
│       ├── test_row_removal.py
│       ├── test_srs_rotation.py
│       └── test_translation.py
├── pyproject.toml        # Project configuration
├── tox.ini              # Tox configuration
├── .pre-commit-config.yaml  # Pre-commit hooks
└── README.md            # User documentation
```

## Key Classes

- **TetraTile**: Main game window, event loop, and game controller
- **Board**: Tkinter canvas — pure rendering surface (no game state)
- **Grid**: Locked-piece occupancy map — pure game state (no rendering)
- **Polyomino**: Immutable set of ``Square``s with a rotation pivot
- **TetrominoType**: Enum of the 7 one-sided tetromino definitions
- **TetrominoData**: Frozen dataclass with tetromino spawn geometry
- **InputHandler**: Coequal base class for human and agent input
- **Agent**: Pure decision function ``GameObservation → Action``
- **OutputHandler**: Push-notification observer interface

## Tetromino Enumeration

Tetrominoes are defined as:

1. ``TetrominoData`` — frozen dataclass with immutable spawn-state geometry
2. ``TetrominoType`` — enum of all 7 one-sided tetromino types
3. ``tetrominoes`` — tuple of instantiated ``Polyomino`` objects

## Configuration

- Pydantic models validate config at runtime
- JSON file format for persistent config
- CLI arguments override config file
- Defaults in Pydantic Field definitions

## Version Management

- Version derived from git tags via hatch-vcs
- Runtime version via ``importlib.metadata.version()``
- Fallback version: "0.0" (only if git unavailable)
