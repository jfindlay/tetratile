# Agent Guidelines for Tetratile Project

## Project Overview

Tetratile is a tetromino tessellation game built with Python and tkinter.

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
- **Dev**: pytest, ruff, mypy, pyupgrade

## Build & Test Commands

```bash
# Install in development mode
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/

# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/

# Build package
uv pip install build
python -m build
```

## Project Structure

```
tetratile/
├── src/tetratile/
│   ├── __init__.py      # Main game logic, TetraTile class
│   ├── __main__.py      # CLI entry point
│   ├── config.py        # Configuration with Pydantic models
│   └── py.typed         # PEP 561 marker for type checkers
├── tests/
│   └── unit/
│       └── test_pysirtet.py  # Unit tests
├── pyproject.toml        # Project configuration
└── README.md            # User documentation
```

## Key Classes

- **TetraTile**: Main game window and event loop
- **Board**: Canvas-based display for tetrominoes
- **Grid**: Game state data structure
- **Polyomino**: Base class for tetromino geometry
- **TetrominoType**: Enum with all tetromino definitions
- **TetrominoData**: Frozen dataclass with tetromino attributes

## Tetromino Enumeration

Tetrominos are defined as:
1. ``TetrominoData`` - frozen dataclass with immutable tetromino data
2. ``TetrominoType`` - enum with all 7 tetromino instances
3. ``tetrominoes`` - tuple of instantiated Tetromino objects

## Configuration

- Pydantic models validate config at runtime
- TOML file format for persistent config
- CLI arguments override config file
- Defaults in Pydantic Field definitions

## Version Management

- Version derived from git tags via hatch-vcs
- Runtime version via ``importlib.metadata.version()``
- Fallback version: "0.0" (only if git unavailable)
