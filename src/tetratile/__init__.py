# !/usr/bin/env python3
"""Tetromino tessellation game on the integer lattice :math:`\\mathbb{Z}^2`.

The game operates on a finite rectangular sublattice
:math:`\\mathcal{B} \\subset \\mathbb{Z}^2` (the board) using
y-up Cartesian orientation.  Valid piece moves form the semidirect product
:math:`G = \\mathbb{Z}^2 \rtimes C_4`, where :math:`\\mathbb{Z}^2` is the
integer translation group and :math:`C_4 \\cong \\mathbb{Z}/4\\mathbb{Z}` is
the cyclic group of quarter-turn rotations.

See ``docs/mathematics.rst`` for the full mathematical treatment.

:attr _VERSION: The version of the installed package.
:attr tetrominoes: Tuple of all seven one-sided tetromino :class:`Polyomino`
    instances, one per :class:`TetrominoType` member.
"""

import datetime as dt
import enum
import importlib
import importlib.metadata
import math
import random
import tkinter as tk
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal as D
from typing import NamedTuple

from ._versor import rotate_point
from .config import BoardConfig, GameConfig
from .event_log import EventLogger, EventType
from .input_handler import InputHandler
from .output import OutputHandler

_VERSION: str = importlib.metadata.version("tetratile")

__all__ = [
    "Board",
    "Colors",
    "EigenTransformation",
    "GameEvent",
    "GameObservation",
    "GameState",
    "Grid",
    "Polyomino",
    "Rotation",
    "Square",
    "TetraTile",
    "TetrominoData",
    "TetrominoType",
    "Translation",
    "mix_with_black",
    "tetrominoes",
    "used_keys",
]


# ---------------------------------------------------------------------------
# Primitive lattice types
# ---------------------------------------------------------------------------


class Square(NamedTuple):
    """A unit cell of the :math:`\\mathbb{Z}^2` lattice, identified by its lower-left corner.

    Mathematically, the cell at :math:`(x, y)` is the open unit square
    :math:`(x, x+1) \\times (y, y+1) \\subset \\mathbb{R}^2`.  The integer
    point :math:`(x, y) \\in \\mathbb{Z}^2` is its lower-left corner and
    serves as the canonical identifier.

    Using a ``NamedTuple`` gives value semantics, hashability, and immutability
    at zero overhead — consistent with the lattice-cell interpretation.

    :attr x: Column index (0 = leftmost column).
    :attr y: Row index (0 = bottom row, y-up orientation).
    """

    x: int
    y: int


class Translation(NamedTuple):
    """An element of the translation group :math:`\\mathbb{Z}^2`.

    In the discrete PGA framework (:math:`Cl(2,0,1)`) a translation is
    realised as a **null-bivector translator** :math:`T = 1 + \\tfrac12 t`,
    where :math:`t = dx\\,e_{01} + dy\\,e_{02}` encodes the integer
    displacement vector.  The type retains the direct ``(dx, dy)``
    representation as the concrete bridge to :math:`\\mathbb{Z}^2`.

    ``dx > 0`` is rightward; ``dy > 0`` is upward (y-up Cartesian
    convention throughout).  Gravity is ``Translation(0, -1)`` — an
    explicit negative :math:`y` displacement.

    :attr dx: Horizontal displacement; positive = right.
    :attr dy: Vertical displacement; positive = up.
    """

    dx: int
    dy: int


class Rotation(NamedTuple):
    """An element of the cyclic rotation group :math:`C_4 \\cong \\mathbb{Z}/4\\mathbb{Z}`.

    In the discrete PGA framework (:math:`Cl(2,0,1)`) a quarter-turn is
    realised by the **integer rotor** :math:`U = 1 + e_{12}` (or its
    reverse :math:`\\tilde{U} = 1 - e_{12}` for CCW) via the versor
    sandwich :math:`R(\\mathbf{v}) = U\\,\\mathbf{v}\\,\\tilde{U} / |U|^2`.
    See :func:`._versor.rotate_point` and :ref:`discrete-rotor` in
    ``docs/mathematics.rst`` for the lattice-exactness proof.

    ``steps=+1`` is one CW quarter-turn; ``steps=-1`` is one CCW
    quarter-turn.  The term *steps* is chosen to match the group-theoretic
    notion of a generator applied ``steps`` times.

    :attr steps: Number of CW quarter-turns; ``+1`` CW, ``-1`` CCW.
    """

    steps: int


# Atomic generators of G = Z^N ⋊ B_N^+: lattice-stabilising discrete versors
# of Cl(N,0,1).  Translation = null-bivector translator; Rotation = integer
# rotor in a chosen Euclidean bivector plane.  See docs/mathematics.rst.
type EigenTransformation = Translation | Rotation


class Colors(NamedTuple):
    """Rendering colors for a :class:`Polyomino`.

    Three color variants (normal face, lighter bevel, darker bevel) give
    each piece a distinct 3-D appearance.  Using a ``NamedTuple`` makes
    :class:`Colors` immutable and hashable, consistent with its role as
    pure rendering metadata that is never mutated.

    :attr normal: Primary face color (hex string, e.g. ``"#CC6666"``).
    :attr light: Lighter bevel color for the highlight edge.
    :attr dark: Darker bevel color for the shadow edge.
    """

    normal: str = ""
    light: str = ""
    dark: str = ""


# ---------------------------------------------------------------------------
# Game state types
# ---------------------------------------------------------------------------


class GameState(enum.StrEnum):
    """Game states.

    :attr running: Game is actively running.
    :attr paused: Game is paused.
    :attr over: Game is over.
    """

    running = ""
    paused = "paused"
    over = "game over"


class GameEvent(enum.IntEnum):
    """Available asynchronous game events.

    :attr iterate: Event to iterate the game loop.
    :attr remove: Event to remove full rows.
    """

    iterate = enum.auto()
    remove = enum.auto()


@dataclass(frozen=True)
class GameObservation:
    r"""Read-only snapshot of the game state for agents and human observers.

    Passed to every registered :class:`.OutputHandler` after each gravity
    tick via :meth:`.TetraTile._notify_observers`.  Also returned directly
    by :meth:`.TetraTile.get_observation` for agent polling.

    The board is encoded in **row-major** order — ``board[y][x]`` — with
    ``y=0`` at the bottom row, matching the standard convention for numpy
    arrays and machine-learning agent consumption.  Note the transposition
    relative to Tkinter canvas coordinates (which are y-down).

    The ``current_piece_coords`` set uses :class:`Square` values whose
    ``(x, y)`` coordinates are Cartesian (x=0 left, y=0 bottom).

    :attr board: Row-major board; ``board[y][x]`` is ``None`` (empty) or
        the tetromino name string (occupied).
    :attr current_piece: Single-letter name of the currently falling piece,
        or ``None`` between pieces.
    :attr current_piece_coords: Frozen set of :class:`Square` coordinates for
        the current piece's cells.
    :attr current_piece_rotation: :math:`C_4` rotation index in
        :math:`\\{0, 1, 2, 3\\}` where 0 is the spawn orientation and each
        increment represents one additional CW quarter-turn.  ``-1`` when no
        piece is active.
    :attr next_piece: Name of the next piece to spawn, or ``None``.
    :attr stats: Dictionary of game statistics (pieces placed, rows cleared, etc.).
    :attr state: Current :class:`GameState`.
    :attr elapsed: Elapsed game time.
    """

    board: tuple[tuple[str | None, ...], ...]
    current_piece: str | None
    current_piece_coords: frozenset[Square]
    current_piece_rotation: int
    next_piece: str | None
    stats: dict[str, typing.Any]
    state: GameState
    elapsed: dt.timedelta


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------


def _build_rotation_table() -> dict[str, list[frozenset[Square]]]:
    """Build the module-level rotation lookup table for :func:`_rotation_state`.

    For each tetromino type, generates the four rotation states in canonical
    (spawn-origin) frame and stores them as a list indexed by rotation index.
    Built once at module load; used by :func:`_rotation_state` for O(4)
    worst-case lookup instead of O(28) linear search.

    The local-frame squares at each state are computed by translating the
    spawn squares to origin ``(0, 0)`` — that is, subtracting the canonical
    origin from every square.  Because both the piece's current origin and the
    canonical origin share the same fractional part (they differ only by an
    integer vector), the difference ``piece.origin - canonical_origin`` is
    always an exact integer, making the translation lossless.

    :returns: Dict mapping piece name → list of four ``frozenset[Square]``
        (one per C₄ rotation state, index 0 = spawn orientation).
    """
    table: dict[str, list[frozenset[Square]]] = {}
    for t in TetrominoType:
        cx, cy = t.value.origin
        squares: frozenset[Square] = t.value.squares
        states: list[frozenset[Square]] = []
        for _ in range(4):
            # Translate to local frame: subtract canonical origin (exact integer result)
            local = frozenset(Square(s.x - int(cx), s.y - int(cy)) for s in squares)
            states.append(local)
            # Apply one CW quarter-turn about the canonical origin
            squares = frozenset(Square(int(s.y - cy + cx), int(-(s.x - cx) + cy)) for s in squares)
        table[t.value.name] = states
    return table


def _rotation_state(piece: "Polyomino") -> int:
    """Derive the :math:`C_4` rotation index of a piece from its current squares.

    Translates the piece's board-frame squares to canonical local frame
    (by subtracting the canonical origin) and looks up the result in the
    pre-built :data:`_ROTATION_TABLE`.  The lookup is O(4) worst case.

    The translation ``piece.origin - canonical_origin`` is an exact integer
    vector because both origins share the same :class:`~decimal.Decimal`
    fractional part (0 for integer-centre pieces, ``-0.5`` for half-integer
    ones) and differ only by the integer spawn displacement.

    :param piece: The :class:`Polyomino` to inspect.
    :returns: Rotation index in :math:`\\{0, 1, 2, 3\\}`, or ``-1`` if the
        piece name is not a recognised :class:`TetrominoType`.
    """
    states = _ROTATION_TABLE.get(piece.name)
    if states is None:
        return -1

    # Find the canonical origin for this piece type
    canonical_origin: tuple[D, D] | None = None
    for t in TetrominoType:
        if t.value.name == piece.name:
            canonical_origin = t.value.origin
            break
    if canonical_origin is None:
        return -1

    # Translate piece squares to canonical local frame.
    # piece.origin - canonical_origin is an exact integer vector.
    cx, cy = canonical_origin
    ox, oy = piece.origin
    dx = int(ox - cx)
    dy = int(oy - cy)
    local = frozenset(Square(s.x - dx, s.y - dy) for s in piece.squares)

    for state, state_squares in enumerate(states):
        if local == state_squares:
            return state
    return -1


def mix_with_black(color: str, factor: float = 0.5) -> str:
    """Blend a hex color with black.

    :param color: Hex color string (e.g., "#RRGGBB").
    :param factor: Blend factor from 0.0 (original) to 1.0 (black).
    :returns: New hex color string.
    """
    if not color or len(color) != 7:
        return color
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
    except ValueError:
        return color
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Grid: pure occupancy map
# ---------------------------------------------------------------------------


class Grid:
    """Finite rectangular sublattice :math:`\\mathcal{B} \\subset \\mathbb{Z}^2` with occupancy.

    Models the region :math:`\\{0,\\ldots,w-1\\} \\times \\{0,\\ldots,h-1\\}` of
    the integer lattice.  Each cell :math:`(x, y)` is the unit open square
    :math:`(x, x+1) \\times (y, y+1)`; the integer point :math:`(x, y)` is
    its lower-left corner.  ``Grid[Square(0, 0)]`` is the bottom-left cell.

    The internal state is a **partial function**
    :math:`\\mathcal{G}: \\mathcal{B} \\rightharpoonup \\text{PieceName}`,
    encoded as ``dict[Square, str]``.  Presence of a key = occupied by a
    locked piece; absence = empty.  The active piece is **never** written here.

    The placement validity predicate :meth:`check` tests whether a set of
    candidate :class:`Square`s is entirely within :math:`\\mathcal{B}` and
    overlaps no currently occupied cell:

    .. math::

        \\text{valid}(\\mathcal{G}, S)
        \\iff
        \\forall s \\in S:\\; s \\in \\mathcal{B}
        \\;\\wedge\\; s \\notin \\operatorname{dom}(\\mathcal{G}).

    :attr width: Number of columns in the grid.
    :attr height: Number of rows in the grid.
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize the game grid with all cells empty.

        :param width: Number of columns.
        :param height: Number of rows.
        """
        self._occupancy: dict[Square, str] = {}
        self.width = width
        self.height = height

    def _in_bounds(self, s: Square) -> bool:
        """Test whether a square is within the board domain.

        :param s: The square to test.
        :returns: ``True`` if :math:`0 \\le s.x < w` and :math:`0 \\le s.y < h`.
        """
        return 0 <= s.x < self.width and 0 <= s.y < self.height

    def __getitem__(self, s: Square) -> str | None:
        """Return the piece name occupying square ``s``, or ``None`` if empty.

        :param s: The square to query.
        :returns: Piece name string, or ``None`` if the cell is empty.
        :raises IndexError: If ``s`` is outside the board domain.
        """
        if not self._in_bounds(s):
            raise IndexError(f"grid coordinates out of bounds: {s}")
        return self._occupancy.get(s)

    def __setitem__(self, s: Square, name: str | None) -> None:
        """Set or clear the piece occupying square ``s``.

        :param s: The square to update.
        :param name: Piece name to place, or ``None`` to clear.
        :raises IndexError: If ``s`` is outside the board domain.
        """
        if not self._in_bounds(s):
            raise IndexError(f"grid coordinates out of bounds: {s}")
        if name is None:
            self._occupancy.pop(s, None)
        else:
            self._occupancy[s] = name

    def __iter__(self) -> Iterator[Square]:
        """Iterate over all squares in the board domain (column-major order).

        :yields: Each :class:`Square` in the board domain.
        """
        for x in range(self.width):
            for y in range(self.height):
                yield Square(x, y)

    def check(self, squares: frozenset[Square] | set[Square]) -> bool:
        """Test the placement validity predicate for a set of candidate squares.

        A set :math:`S` is *valid* when every element lies within the board
        domain :math:`\\mathcal{B}` and does not overlap an already-occupied
        locked cell:

        .. math::

            \\text{valid}(\\mathcal{G}, S)
            \\iff
            \\forall s \\in S:\\; s \\in \\mathcal{B}
            \\;\\wedge\\; s \\notin \\operatorname{dom}(\\mathcal{G}).

        :param squares: Candidate squares to test.
        :returns: ``True`` if every square is in-bounds and unoccupied.
        """
        for s in squares:
            if not self._in_bounds(s):
                return False
            if s in self._occupancy:
                return False
        return True

    def occupied(self) -> dict[Square, str]:
        """Return a shallow copy of the occupancy map.

        :returns: ``dict[Square, str]`` mapping occupied squares to piece names.
        """
        return dict(self._occupancy)

    def print(self) -> None:
        """Display grid state to stdout for debugging.

        Rows are printed top-to-bottom (``y = height-1`` first) with a
        screen-row counter on the left.  Each occupied cell shows the
        first character of its piece name; empty cells show a dot.
        """
        digits = len(str(self.height))
        row_fmt = f"{{:0{digits}}}"
        print(digits * " " + "+" + self.width * "-" + "+")
        for y in reversed(range(self.height)):
            row = "".join((self._occupancy.get(Square(x, y), ".")[:1] or ".") for x in range(self.width))
            print(row_fmt.format(self.height - y - 1) + "|" + row + "|")
        print(digits * " " + "+" + self.width * "-" + "+")


# ---------------------------------------------------------------------------
# Polyomino: immutable value type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Polyomino:
    r"""A polyomino — a connected finite subset of the integer lattice :math:`\mathbb{Z}^2`.

    A polyomino of **ordinal** :math:`n` (an :math:`n`-omino) is a connected
    finite set of :math:`n` unit cells of :math:`\mathbb{Z}^2`.  This class
    represents one polyomino, together with a rotation pivot and rendering
    metadata.

    **Value semantics.**  :class:`Polyomino` is a frozen dataclass: all
    fields are immutable, and the transform methods :meth:`translate` and
    :meth:`rotate` return **new** :class:`Polyomino` instances (or ``None``
    if blocked).  This reflects the group action: applying a group element
    to a piece yields a new algebraic state without mutating the old one.

    **Coordinate convention.**  Each :class:`Square` in ``squares`` has
    :math:`(x, y)` coordinates identifying its lower-left corner.  The cell
    at :math:`(x, y)` occupies :math:`(x, x+1) \\times (y, y+1)` in the plane.
    Coordinates use y-up orientation: :math:`y = 0` is the bottom row.

    **Rotation pivot** ``origin``.  The pivot is stored with
    :class:`~decimal.Decimal` arithmetic so that half-integer centres (used
    by Z, S, I, O) are preserved exactly through all four rotation states.
    For pieces whose geometric centre of symmetry is a half-integer point,
    ``origin = (D('-0.5'), D('-0.5'))`` in local frame; for integer-centre
    pieces ``origin = (D(0), D(0))``.
    See :ref:`half-integer-origin` in ``docs/mathematics.rst``.

    :attr squares: Frozen set of :class:`Square`s comprising the polyomino.
    :attr origin: Rotation pivot in board-frame :class:`~decimal.Decimal`
        coordinates; updated by :meth:`translate` to remain centred on the piece.
    :attr colors: Rendering colors.
    :attr name: Single-letter piece identifier (e.g. ``"T"``, ``"Z"``).
    """

    squares: frozenset[Square]
    origin: tuple[D, D]
    colors: Colors
    name: str = ""

    @property
    def ordinal(self) -> int:
        """Number of cells in the polyomino (:math:`n` in :math:`n`-omino).

        :returns: ``len(self.squares)``.
        """
        return len(self.squares)

    @property
    def min_x(self) -> int:
        """Minimum x coordinate over all cells.

        :returns: :math:`\\min_{s \\in \\text{squares}} s.x`.
        """
        return min(s.x for s in self.squares)

    @property
    def max_x(self) -> int:
        """Maximum x coordinate over all cells.

        :returns: :math:`\\max_{s \\in \\text{squares}} s.x`.
        """
        return max(s.x for s in self.squares)

    @property
    def min_y(self) -> int:
        """Minimum y coordinate over all cells.

        :returns: :math:`\\min_{s \\in \\text{squares}} s.y`.
        """
        return min(s.y for s in self.squares)

    @property
    def max_y(self) -> int:
        """Maximum y coordinate over all cells.

        :returns: :math:`\\max_{s \\in \\text{squares}} s.y`.
        """
        return max(s.y for s in self.squares)

    def translate(self, t: Translation, grid: Grid) -> "Polyomino | None":
        """Translate the polyomino by ``t`` if valid.

        Applies the integer displacement :math:`(dx, dy)` to every cell.
        Returns a **new** :class:`Polyomino` at the translated position, or
        ``None`` if the translated position is blocked or out of bounds.

        This implements the group action of :math:`\\mathbb{Z}^2` on the
        polyomino: the result is a new algebraic state, not a mutation.

        :param t: :class:`Translation` to apply.
        :param grid: :class:`Grid` to validate the result against.
        :returns: Translated :class:`Polyomino`, or ``None`` if blocked.
        """
        new_squares = frozenset(Square(s.x + t.dx, s.y + t.dy) for s in self.squares)
        if not grid.check(new_squares):
            return None
        new_origin = (self.origin[0] + t.dx, self.origin[1] + t.dy)
        return Polyomino(squares=new_squares, origin=new_origin, colors=self.colors, name=self.name)

    def rotate(self, r: Rotation, grid: Grid, kick: bool = True) -> "Polyomino | None":
        """Rotate the polyomino about its origin, with optional boundary kicks.

        Implements the CW quarter-turn via the **integer rotor** from discrete
        plane-based geometric algebra (:mod:`._versor`).  For the unnormalised
        rotor :math:`U = 1 + e_{12}` the versor sandwich gives

        .. math::

            R(\\mathbf{v}) = U\\,\\mathbf{v}\\,\\tilde{U} / |U|^2
            = (y,\\,-x)
            \\quad\\text{(CW, steps = +1)},

        which is lattice-exact: integer inputs yield integers, and
        half-integer :class:`~decimal.Decimal` inputs yield half-integers,
        with no floating-point rounding.  See :ref:`discrete-rotor` in
        ``docs/mathematics.rst`` for the :math:`\\sqrt{2}`-cancellation proof.

        Each cell :math:`(x_i, y_i)` is rotated by translating to the pivot
        frame (subtract origin), applying the rotor sandwich ``steps`` times,
        then translating back (add origin).

        When ``kick=True`` (the default), :func:`_boundary_kicks` generates
        corrective :class:`Translation`s derived from bounding-box violations
        against the grid domain (see :ref:`boundary-kicks` in
        ``docs/mathematics.rst``).  The first valid kick is accepted.

        When ``kick=False``, only the in-place rotation (zero kick) is
        attempted; this is the semantics for games or tests where wall-kick
        correction is disabled.

        Returns a **new** :class:`Polyomino` at the rotated (and possibly
        kicked) position, or ``None`` if no valid position exists.

        :param r: :class:`Rotation`; ``steps=+1`` CW, ``steps=-1`` CCW.
        :param grid: :class:`Grid` to validate each candidate placement against.
        :param kick: If ``True``, apply boundary kicks; if ``False``, only try in-place.
        :returns: Rotated (and possibly kicked) :class:`Polyomino`, or ``None``.
        """
        ox, oy = self.origin

        def _rotate_square(s: Square) -> Square:
            rx, ry = rotate_point(s.x - ox, s.y - oy, r.steps)
            return Square(int(rx + ox), int(ry + oy))

        new_squares = frozenset(_rotate_square(s) for s in self.squares)
        rotated = Polyomino(squares=new_squares, origin=self.origin, colors=self.colors, name=self.name)
        kicks = _boundary_kicks(rotated, grid) if kick else iter((Translation(0, 0),))
        for k in kicks:
            candidate = frozenset(Square(s.x + k.dx, s.y + k.dy) for s in new_squares)
            if grid.check(candidate):
                new_origin = (self.origin[0] + k.dx, self.origin[1] + k.dy)
                return Polyomino(squares=candidate, origin=new_origin, colors=self.colors, name=self.name)
        return None


def _boundary_kicks(piece: Polyomino, grid: Grid) -> Iterator[Translation]:
    """Generate corrective translations for a rotationally displaced polyomino.

    Given a polyomino that may violate the board boundary after rotation,
    yields :class:`Translation` candidates in priority order derived
    algebraically from the piece's bounding-box violations against the grid
    domain :math:`[0, w) \\times [0, h)`.  This is the *covariant rotation*
    principle: free rotation composed with the minimal compensating translation
    that restores domain membership.

    Priority order (at most four candidates):

    1. ``Translation(0, 0)`` — in-place (always tried first).
    2. ``Translation(δx, 0)`` — horizontal correction only.
    3. ``Translation(0, δy)`` — vertical correction only.
    4. ``Translation(δx, δy)`` — combined correction.

    where :math:`\\delta x = \\text{clamp}(x,\\, \\text{min\\_x},\\, \\text{max\\_x})`
    and similarly for :math:`\\delta y`.

    No precomputed state-pair tables are used; candidates are derived
    entirely from the rotated piece's geometry and the grid dimensions.

    :param piece: The piece in its proposed (rotated) position.
    :param grid: The grid whose domain defines the valid range.
    :yields: :class:`Translation` candidates in priority order.
    """
    yield Translation(0, 0)

    # Compute bounding-box violations
    dx = 0
    dy = 0
    if piece.min_x < 0:
        dx = -piece.min_x
    elif piece.max_x >= grid.width:
        dx = grid.width - 1 - piece.max_x
    if piece.min_y < 0:
        dy = -piece.min_y
    elif piece.max_y >= grid.height:
        dy = grid.height - 1 - piece.max_y

    if dx != 0:
        yield Translation(dx, 0)
    if dy != 0:
        yield Translation(0, dy)
    if dx != 0 and dy != 0:
        yield Translation(dx, dy)


# ---------------------------------------------------------------------------
# TetrominoData and TetrominoType
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TetrominoData:
    """Immutable spawn-state geometry and colors for a single tetromino type.

    ``squares`` stores the four cell positions in the piece's local
    (origin-centred) coordinate frame as a ``frozenset[Square]``.  For
    pieces whose geometric centre of symmetry is a half-integer point (Z, S,
    I, O), the coordinates encode the half-integer shift needed to locate the
    pivot exactly — the :attr:`origin` field stores the corresponding
    ``(Decimal, Decimal)`` pivot.

    :attr name: Single-letter piece identifier.
    :attr squares: Local-frame cell positions as a :class:`~frozenset` of :class:`Square`.
    :attr origin: Rotation pivot in local coordinates; half-integer for Z/S/I/O.
    :attr normal: Primary face color (hex string).
    :attr light: Lighter bevel color (hex string).
    :attr dark: Darker bevel color (hex string).
    """

    name: str
    squares: frozenset[Square]
    origin: tuple[D, D]
    normal: str
    light: str
    dark: str


class TetrominoType(enum.Enum):
    """Enumeration of the seven one-sided tetrominoes.

    There are exactly **seven** one-sided tetrominoes (treating each piece
    as distinct from its mirror image) but only five *free* tetrominoes
    (where mirror images are identified).  This game uses the seven one-sided
    forms because reflections are not valid moves — a player cannot flip a
    physical piece over — so S :math:`\\neq` Z and L :math:`\\neq` J.

    Each member holds a :class:`TetrominoData` value encoding the spawn-
    state geometry and colors.  The ``l`` member uses a lowercase name to
    avoid confusion with the integer ``1``; similarly ``o`` avoids confusion
    with the integer ``0``.

    Half-integer pivot pieces (Z, S, I, O) store
    ``origin = (D('-0.5'), D('-0.5'))`` so that rotation is exact through
    all four states without truncation drift (see :ref:`half-integer-origin`).

    :attr Z: Z-tetromino; half-integer centre, spawns in two-row zigzag.
    :attr S: S-tetromino; half-integer centre, mirror of Z.
    :attr l: I-tetromino (four in a row); half-integer centre.
    :attr T: T-tetromino; integer centre, T-shape (stem pointing down at spawn).
    :attr o: O-tetromino (2×2 square); half-integer centre.
    :attr L: L-tetromino; integer centre, L-shape (vertical at spawn).
    :attr J: J-tetromino; integer centre, J-shape (vertical at spawn, mirror of L).
    """

    # Spawn orientations restored to original mathematical forms:
    # - Z/S: two-row zigzag
    # - I: horizontal bar
    # - T: stem pointing down (flat edge at top)
    # - O: 2×2 square
    # - L/J: vertical bar with foot
    Z = TetrominoData(
        name="Z",
        squares=frozenset({Square(-1, 1), Square(0, 1), Square(0, 0), Square(1, 0)}),
        origin=(D("-0.5"), D("-0.5")),
        normal="#CC6666",
        light="#F89FAB",
        dark="#803C3B",
    )
    S = TetrominoData(
        name="S",
        squares=frozenset({Square(-1, 0), Square(0, 0), Square(0, 1), Square(1, 1)}),
        origin=(D("-0.5"), D("-0.5")),
        normal="#66CC66",
        light="#79FC79",
        dark="#3B803B",
    )
    l = TetrominoData(  # noqa: E741
        name="l",
        squares=frozenset({Square(-2, 0), Square(-1, 0), Square(0, 0), Square(1, 0)}),
        origin=(D("-0.5"), D("-0.5")),
        normal="#6666CC",
        light="#7979FC",
        dark="#3B3B80",
    )
    T = TetrominoData(
        name="T",
        squares=frozenset({Square(-1, 0), Square(0, 0), Square(1, 0), Square(0, -1)}),
        origin=(D(0), D(0)),
        normal="#CCCC66",
        light="#FCFC79",
        dark="#80803B",
    )
    o = TetrominoData(  # noqa: E741
        name="o",
        squares=frozenset({Square(-1, 0), Square(-1, -1), Square(0, 0), Square(0, -1)}),
        origin=(D("-0.5"), D("-0.5")),
        normal="#CC66CC",
        light="#FC79FC",
        dark="#803B80",
    )
    L = TetrominoData(
        name="L",
        squares=frozenset({Square(0, 1), Square(0, 0), Square(0, -1), Square(1, -1)}),
        origin=(D(0), D(0)),
        normal="#66CCCC",
        light="#79FCFC",
        dark="#3B8080",
    )
    J = TetrominoData(
        name="J",
        squares=frozenset({Square(0, 1), Square(0, 0), Square(0, -1), Square(-1, -1)}),
        origin=(D(0), D(0)),
        normal="#DAAA00",
        light="#FCC600",
        dark="#806200",
    )

    @property
    def polyomino(self) -> "Polyomino":
        """Create a :class:`Polyomino` instance from this type's spawn geometry.

        :returns: A new :class:`Polyomino` with spawn-state squares and origin.
        """
        d = self.value
        return Polyomino(
            squares=d.squares,
            origin=d.origin,
            colors=Colors(d.normal, d.light, d.dark),
            name=d.name,
        )


def used_keys() -> list[str]:
    """Return list of keys for the used dictionary.

    :returns: ``["total", "Z", "S", "l", "T", "o", "L", "J"]``.
    """
    return ["total"] + [t.value.name for t in TetrominoType]


tetrominoes: tuple[Polyomino, ...] = tuple(t.polyomino for t in TetrominoType)

# Initialise module-level lookup tables that depend on TetrominoType.
_ROTATION_TABLE = _build_rotation_table()


# ---------------------------------------------------------------------------
# UI helper classes (Tkinter wrappers — no game logic)
# ---------------------------------------------------------------------------


class PrecisionVar:
    """Represent a value at specified precision while maintaining full precision internally.

    :attr variable: The StringVar containing the formatted display value.
    """

    def __init__(self, *, value: int | float | None = None, precision: int = 2) -> None:
        """Initialize the precision variable.

        :param value: Initial value. Defaults to 0.0.
        :param precision: Number of decimal places for display. Defaults to 2.
        """
        self._precision = precision
        self._float_value = self._validate(value if value is not None else 0.0)
        self._var = tk.StringVar(value=self._fmt())

    def _validate(self, value: float) -> float:
        """Validate the value is a nonnegative number.

        :param value: Value to validate.
        :returns: The validated value as float.
        :raises TypeError: If value is not a nonnegative number.
        """
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
        raise TypeError("value must be a nonnegative number")

    def _fmt(self) -> str:
        """Format the value for display.

        :returns: Formatted string.
        """
        return f"{{:.{self._precision}f}}".format(self._float_value)

    def get(self, raw: bool = False) -> float | str:
        """Get the current value.

        :param raw: If True, return the raw float value. Otherwise return formatted string.
        :returns: The value.
        """
        return self._float_value if raw else self._var.get()

    def set(self, value: float) -> None:
        """Set the value.

        :param value: The new value.
        """
        self._float_value = self._validate(value)
        self._var.set(self._fmt())

    @property
    def variable(self) -> tk.StringVar:
        """The StringVar containing the formatted display value.

        :returns: The StringVar.
        """
        return self._var


class TimerVar:
    """Timer widget variable with start/stop capability.

    :attr variable: The StringVar containing the formatted time.
    """

    def __init__(self, *, value: dt.timedelta | None = None) -> None:
        """Initialize the timer.

        :param value: Initial elapsed time. Defaults to zero.
        """
        self._accumulated_elapsed = value if value is not None else dt.timedelta()
        self._active_counting_since: dt.datetime | dt.timedelta = dt.timedelta()
        self._var = tk.StringVar(value=self._to_str(self._accumulated_elapsed))

    def _to_str(self, value: dt.timedelta) -> str:
        """Format timedelta for display.

        :param value: Time to format.
        :returns: Formatted string (first 7 characters).
        """
        return str(value)[:7]

    def get(self, as_seconds: bool = False) -> str | float:
        """Get the current elapsed time.

        :param as_seconds: If True, return total seconds. Otherwise return formatted string.
        :returns: The elapsed time.
        """
        computed: dt.timedelta
        if isinstance(self._active_counting_since, dt.datetime):
            computed = dt.datetime.now() - self._active_counting_since + self._accumulated_elapsed
        else:
            computed = self._accumulated_elapsed
        self._var.set(self._to_str(computed))
        return computed.total_seconds() if as_seconds else self._var.get()

    def set(self, value: dt.timedelta | None = None) -> None:
        """Reset the timer.

        :param value: New elapsed time. Defaults to zero.
        """
        self._accumulated_elapsed = value if value is not None else dt.timedelta()
        self._active_counting_since = dt.timedelta()

    def start(self) -> None:
        """Start the timer."""
        if not self._active_counting_since:
            self._active_counting_since = dt.datetime.now()

    def stop(self) -> None:
        """Stop the timer and accumulate elapsed time."""
        if isinstance(self._active_counting_since, dt.datetime):
            self._accumulated_elapsed += dt.datetime.now() - self._active_counting_since
        self._active_counting_since = dt.timedelta()

    @property
    def variable(self) -> tk.StringVar:
        """The StringVar containing the formatted time.

        :returns: The StringVar.
        """
        return self._var


# ---------------------------------------------------------------------------
# Board: pure rendering surface
# ---------------------------------------------------------------------------


class Board(tk.Canvas):
    """Tkinter canvas — a pure rendering surface for the game board.

    :class:`Board` owns no game state.  It holds two render maps:

    * ``_canvas_ids: dict[Square, int]`` — Tkinter canvas item IDs.
    * ``_colors: dict[Square, Colors]`` — colors per drawn square.

    **Coordinate systems.**  The game uses Cartesian :math:`y`-up coordinates
    (``y=0`` at the bottom).  Tkinter uses screen coordinates with ``y=0`` at
    the top.  The transform :math:`(x, y) \\mapsto (x, h-1-y)` — implemented in
    :meth:`_transform_coord` — converts between them.

    The public interface is :meth:`render`, which accepts the current
    :class:`Grid` (locked pieces) and the active :class:`Polyomino` (falling
    piece) and redraws the canvas to reflect the full game state.

    :attr width: Grid width in squares (set at construction).
    :attr height: Grid height in squares (set at construction).
    """

    def __init__(self, config: GameConfig, parent: tk.Misc, width: int, height: int, is_projection: bool = False) -> None:
        """Initialize the board.

        :param config: Game configuration.
        :param parent: Parent widget.
        :param width: Grid width in squares.
        :param height: Grid height in squares.
        :param is_projection: Whether this is a projection (shadow) board.
        """
        self._config = config
        self.width = width
        self.height = height
        self.is_projection = is_projection
        self.border_width = config.board.scale // 16
        self.aspect_proportion = 3 if self.is_projection else 1
        self.full_row_colors = Colors("#DDDDDD", "#FFFFFF", "#BBBBBB")
        self.pause_cover_id = 0

        self._canvas_ids: dict[Square, int] = {}
        self._colors: dict[Square, Colors] = {}
        self._active_squares: frozenset[Square] = frozenset()

        super().__init__(
            parent,
            width=config.board.scale * width,
            height=config.board.scale * height // self.aspect_proportion,
        )
        self.create_rectangle(
            0,
            0,
            config.board.scale * width,
            config.board.scale * height,
            fill="black",
            outline="black",
            width=self.border_width,
        )

    def _transform_coord(self, s: Square) -> tuple[int, int]:
        """Convert Cartesian :math:`y`-up coordinates to Tkinter screen coordinates.

        The game uses :math:`y`-up orientation (:math:`y=0` at the bottom);
        Tkinter places the origin at the top-left with :math:`y` increasing
        downward.  The bijection is

        .. math::

            (x, y) \\;\\longmapsto\\; (x,\\; h - 1 - y),

        where :math:`h` is the board height.  This is an involution (its own
        inverse), so it converts in both directions.

        :param s: Cartesian :class:`Square` coordinates.
        :returns: Tkinter ``(x, screen_y)`` coordinate pair.
        """
        return s.x, self.height - 1 - s.y

    def _draw_square(self, s: Square, colors: Colors) -> int:
        """Draw a square on the board canvas.

        :param s: Coordinates of the square (Cartesian y-up).
        :param colors: Colors to use for rendering.
        :returns: Tkinter canvas item ID.
        """
        tx, ty = self._transform_coord(s)
        scale = self._config.board.scale
        px = scale * tx
        py = scale * ty
        return self.create_rectangle(
            px + self.border_width,
            py + self.border_width,
            px + scale,
            py + scale // self.aspect_proportion,
            fill=colors.normal,
            outline=colors.dark,
            width=self.border_width,
        )

    def _erase_square(self, s: Square) -> None:
        """Erase the canvas item at square ``s``.

        :param s: The square to erase.
        """
        item_id = self._canvas_ids.pop(s, None)
        if item_id is not None:
            self.delete(item_id)
        self._colors.pop(s, None)

    def _paint_square(self, s: Square, colors: Colors) -> None:
        """Paint a square at ``s`` with ``colors`` (erasing any existing item first).

        :param s: The square to paint.
        :param colors: Colors to use.
        """
        self._erase_square(s)
        self._canvas_ids[s] = self._draw_square(s, colors)
        self._colors[s] = colors

    def render(self, grid: Grid, active: "Polyomino | None", transparency: float = 0.0, locked_dirty: bool = False) -> None:
        """Redraw the board, updating only changed squares.

        This is the **single rendering entry point**.  It takes a targeted
        approach to minimise Tkinter canvas operations:

        * **Active piece delta**: Only the squares that changed between the
          previous active piece and the new one are erased or repainted.
          This is O(piece.ordinal) per normal tick instead of O(board area).
        * **Locked pieces**: Painted only when ``locked_dirty=True`` (e.g.
          after a row removal that shifts the entire stack).  Otherwise the
          locked canvas items are left untouched — they were painted when
          the piece was locked and do not change until the next row removal.

        :param grid: The locked-piece occupancy map.
        :param active: The currently falling :class:`Polyomino`, or ``None``.
        :param transparency: Blend factor toward black for locked pieces (0.0 = full color).
        :param locked_dirty: If ``True``, repaint all locked squares from ``grid``
            (used after row removal or board clear).
        """
        # --- Active piece delta ---
        if active is not None:
            new_active: frozenset[Square] = (
                frozenset(Square(s.x, 0) for s in active.squares) if self.is_projection else active.squares
            )
            active_colors = active.colors

            # Erase squares the piece vacated (only if not now a locked square)
            for s in self._active_squares - new_active:
                if s not in grid._occupancy:
                    self._erase_square(s)

            # Paint squares the piece moved into
            for s in new_active - self._active_squares:
                self._paint_square(s, active_colors)

            # Repaint squares that stayed but whose color changed (e.g. transparency)
            for s in new_active & self._active_squares:
                if self._colors.get(s) != active_colors:
                    self._paint_square(s, active_colors)

            self._active_squares = new_active
        else:
            # No active piece: erase any previously drawn active squares
            for s in self._active_squares:
                if s not in grid._occupancy:
                    self._erase_square(s)
            self._active_squares = frozenset()

        # --- Locked pieces (only when dirty) ---
        if locked_dirty:
            # Determine full desired locked state
            desired_locked: dict[Square, Colors] = {}
            for s, name in grid.occupied().items():
                piece_colors = _PIECE_COLORS.get(name, Colors())
                if transparency > 0:
                    piece_colors = Colors(
                        mix_with_black(piece_colors.normal, transparency),
                        mix_with_black(piece_colors.light, transparency),
                        mix_with_black(piece_colors.dark, transparency),
                    )
                desired_locked[s] = piece_colors

            # Erase locked squares no longer in grid
            for s in list(self._canvas_ids.keys()):
                if s not in self._active_squares and s not in desired_locked:
                    self._erase_square(s)

            # Paint/update locked squares
            for s, colors in desired_locked.items():
                if self._colors.get(s) != colors:
                    self._paint_square(s, colors)

    def highlight_full_rows(self, grid: Grid) -> list[int]:
        """Highlight completed rows and return their y-indices.

        A row at height :math:`y` is *full* when every cell in
        :math:`\\{0, \\ldots, w-1\\} \\times \\{y\\}` is in ``grid``.

        :param grid: The locked-piece occupancy map.
        :returns: Sorted list of full row y-indices (ascending).
        """
        full_rows = []
        for y in range(self.height):
            if all(Square(x, y) in grid._occupancy for x in range(self.width)):
                full_rows.append(y)
                for x in range(self.width):
                    self._paint_square(Square(x, y), self.full_row_colors)
        return full_rows

    def clear(self) -> None:
        """Erase all drawn squares from the canvas and reset active-piece tracking."""
        for s in list(self._canvas_ids.keys()):
            self._erase_square(s)
        self._active_squares = frozenset()

    def add_pause_cover(self) -> None:
        """Cover the board when game is paused."""
        if not self.pause_cover_id:
            scale = self._config.board.scale
            self.pause_cover_id = self.create_rectangle(
                0,
                0,
                scale * (self.width + 1),
                scale * (self.height + 1),
                fill="black",
                outline="black",
                width=0,
            )

    def remove_pause_cover(self) -> None:
        """Uncover the board when game is resumed."""
        if self.pause_cover_id > 0:
            self.delete(self.pause_cover_id)
            self.pause_cover_id = 0


# Lookup table: piece name -> Colors, built from TetrominoType for O(1) render.
_PIECE_COLORS: dict[str, Colors] = {t.value.name: Colors(t.value.normal, t.value.light, t.value.dark) for t in TetrominoType}


# ---------------------------------------------------------------------------
# TetraTile: game controller
# ---------------------------------------------------------------------------


class TetraTile(tk.Frame):
    """Game controller: owns the occupancy state, active piece, and rendering surfaces.

    :class:`TetraTile` is the central coordinator.  It owns:

    * ``_grid`` — the locked-piece :class:`Grid` (pure game state, no rendering).
    * ``board`` — the main :class:`Board` (pure rendering surface).
    * ``piece`` — the active :class:`Polyomino` (never in ``_grid`` while falling).
    * The input and output handler registries.

    All player and agent input enters through :meth:`move_piece`, which is
    the **single canonical state guard**: it returns ``False`` immediately
    unless the game is :attr:`GameState.running`.

    :meth:`iterate` is the **gravity clock**: one call applies the generator
    ``Translation(0, -1)``, locking the piece and spawning the next one if
    it cannot descend.

    :attr board: Main rendering canvas.
    :attr preview_board: Small canvas showing the next piece.
    :attr projection_board: Optional 1-row canvas for the ghost shadow.
    :attr piece: Currently falling :class:`Polyomino`, or ``None``.
    :attr next_piece: Next piece to spawn.
    :attr state: Current :class:`GameState`.
    :attr event_logger: Records game events for replay/analysis.
    """

    def __init__(self, config: GameConfig, master: tk.Tk | None = None) -> None:
        """Initialize the game.

        :param config: Game configuration.
        :param master: Tkinter root window.

        :raises TypeError: If master is None.
        """
        self.pdeg = 4
        self._config = config

        self.removed_by_count: list[tk.IntVar] = [tk.IntVar() for _ in range(self.pdeg)]
        self.removed_total: tk.IntVar = tk.IntVar()
        self.used: dict[str, tk.IntVar] = {name: tk.IntVar() for name in used_keys()}
        self.next_piece: Polyomino | None = None
        self.piece: Polyomino | None = None

        self.time_elapsed = TimerVar()
        self.time_elapsed.start()

        self.rate = PrecisionVar()
        self.piece_rate = PrecisionVar()
        self.row_rate = PrecisionVar()
        self._update_rates()
        self.state_name = tk.StringVar()
        self.set_state(GameState.running)

        self.event_logger = EventLogger()
        self.event_logger.start(config)

        def _sync_logger_time() -> None:
            """Synchronise the event logger's timestamp with the game timer.

            Converts the current :attr:`time_elapsed` value to milliseconds
            and forwards it to :meth:`.EventLogger.update_time`.  Called
            before every event log entry to ensure accurate timestamps.
            """
            elapsed_seconds = self.time_elapsed.get(as_seconds=True)
            elapsed_ms = int((elapsed_seconds or 0) * 1000)
            self.event_logger.update_time(elapsed_ms, 0)

        self._sync_logger_time = _sync_logger_time

        super().__init__(master)
        if master is None:
            raise TypeError("master cannot be None")
        self.master: tk.Tk = master
        self.projection_board: Board | None = None
        self._shadow_id: int | None = None
        self._shadow_squares: frozenset[Square] = frozenset()
        self._create_menubar()
        self.pack()
        self.create_widgets()
        self.setup_events()

        # Initialize default human input handler
        from .input_human import HumanInputHandler

        self._input_handler: InputHandler = HumanInputHandler(self)
        self._output_handlers: list[OutputHandler] = []
        self._manual_drive: bool = False

        self.add_piece()
        self.iterate_id = self._schedule(GameEvent.iterate)

    def _schedule(self, game_event: GameEvent) -> str:
        """Schedule an asynchronous event.

        When :attr:`_manual_drive` is ``True``, ``GameEvent.iterate`` is not
        scheduled — the caller drives :meth:`iterate` directly — so this
        returns a sentinel string and is otherwise a no-op for that event.
        ``GameEvent.remove`` is always scheduled regardless of manual drive.

        :param game_event: The type of event to schedule.
        :returns: Tkinter after callback ID (or ``"manual"`` sentinel).
        """
        if game_event == GameEvent.iterate:
            if self._manual_drive:
                return "manual"
            action = self.iterate
            rate = self.rate.get(raw=True)
        elif game_event == GameEvent.remove:
            action = self.remove_full_rows
            rate = self.rate.get(raw=True) * self._config.remove_freq
        else:
            return "manual"

        return self.master.after(int(1e3 / (float(rate) + self._config.epsilon)), action)

    def _update_removed(self, rows_removed: int) -> None:
        """Update the count of rows removed.

        :param rows_removed: Number of rows removed in the last operation.
        """
        if 1 <= rows_removed <= self.pdeg:
            idx = rows_removed - 1
            self.removed_by_count[idx].set(self.removed_by_count[idx].get() + 1)
        self.removed_total.set(self.removed_total.get() + rows_removed)

    def _update_rates(self) -> None:
        """Update computed rates."""
        initial = float(self._config.initial_rate)
        constant = bool(self._config.constant)
        min_rate = float(self._config.min_rate)
        new_rate = initial * (1 if constant else math.log(self.removed_total.get() / 2**4 + 2, 2))
        self.rate.set(max(new_rate, min_rate))
        elapsed = float(self.time_elapsed.get(as_seconds=True) or 1)
        self.piece_rate.set(self.used["total"].get() / elapsed)
        self.row_rate.set(self.removed_total.get() / elapsed)

    def _render(self, locked_dirty: bool = False) -> None:
        """Re-render the board and projection/shadow from current game state.

        :param locked_dirty: Pass ``True`` when the locked-piece grid has
            changed (after a lock or row removal) so the board repaints all
            locked squares.  ``False`` (the default) only updates the active
            piece delta, which is O(piece ordinal) instead of O(board area).
        """
        transparency = 0.15 if self._config.stack_transparency else 0.0
        self.board.render(self._grid, self.piece, transparency=transparency, locked_dirty=locked_dirty)

        match self._config.shadow:
            case "projection":
                if self.projection_board is not None:
                    self.projection_board.render(Grid(self.board.width, 1), self.piece)
            case "shadow":
                self._update_shadow()

    def _update_shadow(self) -> None:
        """Update the shadow piece on the main board showing where the piece will land."""
        if self.piece is None or self.state != GameState.running:
            return

        # Erase old shadow tags
        for s in self._shadow_squares:
            self.board.delete(f"shadow_{s.x}_{s.y}")
        self._shadow_squares = frozenset()

        # Simulate a full drop to find landing position
        sim = self.piece
        while True:
            moved = sim.translate(Translation(0, -1), self._grid)
            if moved is None:
                break
            sim = moved

        if sim is self.piece:
            return

        self._shadow_squares = sim.squares
        for s in self._shadow_squares:
            tx, ty = self.board._transform_coord(s)
            scale = self._config.board.scale
            x1 = scale * tx + self.board.border_width
            y1 = scale * ty + self.board.border_width
            x2 = x1 + scale
            y2 = y1 + scale // self.board.aspect_proportion
            self.board.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=mix_with_black(self.piece.colors.normal, 0.5),
                outline=mix_with_black(self.piece.colors.dark, 0.5),
                width=self.board.border_width,
                tags=(f"shadow_{s.x}_{s.y}",),
            )

    def create_widgets(self) -> None:
        """Pack in game widgets."""
        self.game = tk.Frame(self)
        self.game.pack(side="left")

        if self._config.screen_scale:
            screen_w = self.master.winfo_screenwidth()
            screen_h = self.master.winfo_screenheight()
            margin = 0.8
            max_scale_w = int((screen_w * margin) / self._config.board.width)
            max_scale_h = int((screen_h * margin) / (self._config.board.height + 1))
            computed_scale = min(max_scale_w, max_scale_h)
        else:
            computed_scale = self._config.board.scale

        board_config = BoardConfig(
            scale=computed_scale,
            width=self._config.board.width,
            height=self._config.board.height,
        )
        scaled_config = GameConfig(
            board=board_config,
            epsilon=self._config.epsilon,
            min_rate=self._config.min_rate,
            initial_rate=self._config.initial_rate,
            remove_freq=self._config.remove_freq,
            constant=self._config.constant,
            shadow=self._config.shadow,
            kick=self._config.kick,
            stack_transparency=self._config.stack_transparency,
            screen_scale=self._config.screen_scale,
            keys=self._config.keys,
        )

        self._grid = Grid(scaled_config.board.width, scaled_config.board.height)

        self.board = Board(
            scaled_config,
            self.game,
            scaled_config.board.width,
            scaled_config.board.height,
        )
        self.board.pack(side="top")

        if self._config.shadow == "projection":
            self.projection_board = Board(scaled_config, self.game, scaled_config.board.width, 1, is_projection=True)
            self.projection_board.pack(side="top")
        else:
            self.projection_board = None

        self.marquee = tk.Frame(self)
        self.marquee.pack(side="right", padx=computed_scale, pady=computed_scale)

        self.preview_frame = tk.LabelFrame(self.marquee, text="preview")
        self.preview_frame.pack(side="top")
        self._preview_grid = Grid(self.pdeg, self.pdeg)
        self.preview_board = Board(scaled_config, self.preview_frame, self.pdeg, self.pdeg)
        self.preview_board.pack(side="top")

        self.rate_frame = tk.LabelFrame(self.marquee, text="fall rate")
        self.rate_frame.pack(side="top")
        self.rate_display = tk.Label(self.rate_frame, textvariable=self.rate.variable)
        self.rate_display.pack(side="left")
        self.rate_unit = tk.Label(self.rate_frame, text="blocks/sec")
        self.rate_unit.pack(side="left")

        self.piece_rate_frame = tk.LabelFrame(self.marquee, text="piece rate")
        self.piece_rate_frame.pack(side="top")
        self.piece_rate_display = tk.Label(self.piece_rate_frame, textvariable=self.piece_rate.variable)
        self.piece_rate_display.pack(side="left")
        self.piece_rate_unit = tk.Label(self.piece_rate_frame, text="pieces/sec")
        self.piece_rate_unit.pack(side="left")

        self.row_rate_frame = tk.LabelFrame(self.marquee, text="row rate")
        self.row_rate_frame.pack(side="top")
        self.row_rate_display = tk.Label(self.row_rate_frame, textvariable=self.row_rate.variable)
        self.row_rate_display.pack(side="left")
        self.row_rate_unit = tk.Label(self.row_rate_frame, text="rows/sec")
        self.row_rate_unit.pack(side="left")

        self.used_frame = tk.LabelFrame(self.marquee, text="pieces used")
        self.used_frame.pack(side="top")

        total_obj = type("Total", (), {"name": "total"})()
        for t in (*tetrominoes, total_obj):
            used_widget: dict[str, tk.Widget] = {}
            used_widget["frame"] = tk.Frame(self.used_frame, width=12)
            used_widget["frame"].pack(side="top")
            used_widget["quantity"] = tk.Label(used_widget["frame"], textvariable=self.used[t.name])
            used_widget["quantity"].pack(side="left")
            used_widget["unit"] = tk.Label(
                used_widget["frame"],
                text="{}{}".format("" if t.name == "total" else "x", t.name),
            )
            used_widget["unit"].pack(side="left")

        self.removed_frame = tk.LabelFrame(self.marquee, text="rows removed")
        self.removed_frame.pack(side="top")
        for idx, var in enumerate(self.removed_by_count):
            r = idx + 1
            removed_widget: dict[str, tk.Widget] = {}
            removed_widget["frame"] = tk.Frame(self.removed_frame, width=12)
            removed_widget["frame"].pack(side="top")
            removed_widget["quantity"] = tk.Label(removed_widget["frame"], textvariable=var)
            removed_widget["quantity"].pack(side="left")
            removed_widget["unit"] = tk.Label(removed_widget["frame"], text=f"x{r}")
            removed_widget["unit"].pack(side="left")
        removed_widget["frame"] = tk.Frame(self.removed_frame, width=12)
        removed_widget["frame"].pack(side="top")
        removed_widget["quantity"] = tk.Label(removed_widget["frame"], textvariable=self.removed_total)
        removed_widget["quantity"].pack(side="left")
        removed_widget["unit"] = tk.Label(removed_widget["frame"], text="total")
        removed_widget["unit"].pack(side="left")

        self.time_elapsed_frame = tk.LabelFrame(self.marquee, text="elapsed time")
        self.time_elapsed_frame.pack(side="top")
        self.time_elapsed_display = tk.Label(self.time_elapsed_frame, textvariable=self.time_elapsed.variable, width=12)
        self.time_elapsed_display.pack(side="top")

        self.state_display = tk.Label(self.marquee, textvariable=self.state_name)
        self.state_display.pack(side="top")

    def set_state(self, state: GameState) -> None:
        """Set the game state.

        :param state: The new game state.
        """
        self.state = state
        self.state_name.set(state)

    # ------------------------------------------------------------------ #
    # Input / output handler management                                    #
    # ------------------------------------------------------------------ #

    def set_input_handler(self, handler: "InputHandler") -> None:
        """Replace the active input handler.

        :param handler: New :class:`InputHandler` (human or agent).
        """
        self._input_handler = handler

    def get_input_handler(self) -> "InputHandler":
        """Return the active input handler.

        :returns: Current :class:`InputHandler` instance.
        """
        return self._input_handler

    def set_manual_drive(self, enabled: bool) -> None:
        """Enable or disable manual drive mode.

        When ``True``, ``_schedule(GameEvent.iterate)`` becomes a no-op so
        the caller (e.g. :class:`AgentRunner`) drives :meth:`iterate` directly
        without a competing Tk timer.

        :param enabled: ``True`` to suppress automatic scheduling.
        """
        self._manual_drive = enabled

    def add_output_handler(self, handler: "OutputHandler") -> None:
        """Register an output observer.

        Registered handlers receive :class:`GameObservation` snapshots via
        :meth:`OutputHandler.on_observation` after every :meth:`iterate` tick.

        :param handler: :class:`OutputHandler` to register.
        """
        self._output_handlers.append(handler)

    def remove_output_handler(self, handler: "OutputHandler") -> None:
        """Unregister an output observer.

        :param handler: :class:`OutputHandler` to remove.
        """
        self._output_handlers.remove(handler)

    def _notify_observers(self) -> None:
        """Push the current observation to all registered output handlers."""
        if not self._output_handlers:
            return
        obs = self.get_observation()
        for h in self._output_handlers:
            h.on_observation(obs)

    # ------------------------------------------------------------------ #
    # Canonical piece actions (called by InputHandler and iterate())       #
    # ------------------------------------------------------------------ #

    def lock_piece(self) -> None:
        """Lock the current piece in place without dropping.

        No-op when the game is not :attr:`GameState.running` or no piece
        is active.  Commits the active piece's squares to ``_grid`` and
        triggers row removal.
        """
        if self.state != GameState.running or self.piece is None:
            return
        piece = self.piece
        # Commit active piece squares to the occupancy grid
        for s in piece.squares:
            self._grid[s] = piece.name
        self.piece = None
        # Clear shadow before render so it doesn't linger on the next frame
        for s in self._shadow_squares:
            self.board.delete(f"shadow_{s.x}_{s.y}")
        self._shadow_squares = frozenset()
        # Render the locked piece in piece colors, then immediately highlight
        # any full rows over the top.  Both calls are synchronous within the
        # same Tk frame so only the highlight color is ever displayed.
        self._render(locked_dirty=True)
        self._sync_logger_time()
        self.event_logger.log(EventType.piece_lock, piece_type=piece.name)
        if self.board.highlight_full_rows(self._grid):
            self._schedule(GameEvent.remove)
        self.add_piece()

    def get_observation(self) -> "GameObservation":
        """Get current game state for observation (AI agent or human observer).

        :returns: :class:`GameObservation` with current board state, pieces, and stats.
        """
        width, height = self.board.width, self.board.height
        board_state: list[list[str | None]] = [[None] * width for _ in range(height)]
        for s, name in self._grid.occupied().items():
            board_state[s.y][s.x] = name

        elapsed_secs = float(self.time_elapsed.get(as_seconds=True) or 0.0)
        return GameObservation(
            board=tuple(tuple(row) for row in board_state),
            current_piece=self.piece.name if self.piece else None,
            current_piece_coords=self.piece.squares if self.piece else frozenset(),
            current_piece_rotation=_rotation_state(self.piece) if self.piece else -1,
            next_piece=self.next_piece.name if self.next_piece else None,
            stats=self._get_stats(),
            state=self.state,
            elapsed=dt.timedelta(seconds=elapsed_secs),
        )

    def _create_menubar(self) -> None:
        """Create the application menubar."""
        from .config_ui import ConfigUI

        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Preferences...", command=lambda: ConfigUI(self.master, self._config))
        file_menu.add_separator()
        file_menu.add_command(label="View Event Log", command=self._show_log_viewer)
        file_menu.add_command(label="Save Event Log", command=self._save_log)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)

    def _show_log_viewer(self) -> None:
        """Show the event log viewer window."""
        from .log_viewer import LogViewer

        LogViewer(self.master, self.event_logger)

    def _save_log(self) -> None:
        """Save the event log to a file."""
        from tkinter import messagebox

        path = self.event_logger.save()
        messagebox.showinfo("Log Saved", f"Event log saved to:\n{path}")

    # Maps KeysConfig field names to InputHandler method names.
    _KEY_MAP: typing.ClassVar[dict[str, str]] = {
        "pause": "toggle_pause",
        "left": "move_left",
        "right": "move_right",
        "left_side": "move_left_max",
        "right_side": "move_right_max",
        "rotate_left": "rotate_ccw",
        "rotate_right": "rotate_cw",
        "down": "soft_drop",
        "drop": "full_drop",
        "lock": "lock_piece",
    }

    def setup_events(self) -> None:
        """Bind keyboard keys to input handler methods via :attr:`_KEY_MAP`.

        Every key binding routes through the *active* ``_input_handler``, so
        swapping the handler (e.g. from :class:`HumanInputHandler` to
        :class:`AgentInputHandler`) transparently changes who controls the
        game without re-binding keys.  The mapping is::

            KeysConfig field  →  InputHandler method
            ─────────────────────────────────────────
            pause             →  toggle_pause
            left              →  move_left
            right             →  move_right
            left_side         →  move_left_max
            right_side        →  move_right_max
            rotate_left       →  rotate_ccw
            rotate_right      →  rotate_cw
            down              →  soft_drop
            drop              →  full_drop
            lock              →  lock_piece
        """

        def _make_cb(method_name: str) -> typing.Callable[[tk.Event], None]:
            """Return a Tkinter event callback that calls ``method_name`` on the active handler.

            The closure captures ``method_name`` (not the handler itself) so
            that handler swaps take effect without rebinding.
            """

            def callback(event: tk.Event) -> None:  # noqa: ARG001
                """Dispatch the bound key event to the active input handler."""
                getattr(self._input_handler, method_name)()

            return callback

        for cfg_name, handler_method in self._KEY_MAP.items():
            key = getattr(self._config.keys, cfg_name)
            self.master.bind(key, _make_cb(handler_method))

    def pause(self, event: tk.Event | None = None) -> None:
        """Toggle pause state.

        :param event: Tkinter event (unused). May be None when called programmatically.
        """
        if self.state == GameState.running:
            self.after_cancel(self.iterate_id)
            self.time_elapsed.stop()
            self.board.add_pause_cover()
            self.preview_board.add_pause_cover()
            if self.projection_board is not None:
                self.projection_board.add_pause_cover()
            self._sync_logger_time()
            self.event_logger.log(EventType.game_pause)
            self.set_state(GameState.paused)
        elif self.state == GameState.paused:
            self.iterate_id = self._schedule(GameEvent.iterate)
            self.time_elapsed.start()
            self.board.remove_pause_cover()
            self.preview_board.remove_pause_cover()
            if self.projection_board is not None:
                self.projection_board.remove_pause_cover()
            self._sync_logger_time()
            self.event_logger.log(EventType.game_resume)
            self.set_state(GameState.running)

    def restart(self) -> None:
        """Restart the game."""
        self._grid = Grid(self.board.width, self.board.height)
        self.board.clear()
        if self.projection_board is not None:
            self.projection_board.clear()
        for s in self._shadow_squares:
            self.board.delete(f"shadow_{s.x}_{s.y}")
        self._shadow_squares = frozenset()
        self.piece = None

        for var in self.removed_by_count:
            var.set(0)
        self.removed_total.set(0)
        for var in self.used.values():
            var.set(0)

        self.time_elapsed.set()
        self.time_elapsed.start()

        self._update_rates()
        self.set_state(GameState.running)

        self.restart_button.destroy()
        self.add_piece()
        self.iterate_id = self._schedule(GameEvent.iterate)

    def iterate(self) -> None:
        """Process one gravity tick.

        Applies the generator ``Translation(0, -1)`` (one step downward) to
        the active piece.  If the piece cannot descend (blocked by the floor
        or the stack), it is **locked** (committed to ``_grid``) and the next
        piece is spawned.  Full-row removal is scheduled asynchronously.

        After each tick all registered :class:`.OutputHandler`s receive a
        fresh :class:`GameObservation` snapshot via :meth:`_notify_observers`.

        In automatic mode this method reschedules itself via :meth:`_schedule`
        at the current fall rate.  When :attr:`_manual_drive` is ``True``
        (e.g. in :class:`.AgentRunner`) the caller drives this method directly
        and no Tk timer is created.
        """
        if self.state == GameState.paused:
            return
        if not self.move_piece(Translation(0, -1)):
            self.lock_piece()
        self._notify_observers()
        if self.state == GameState.running:
            self._update_rates()
            self.iterate_id = self._schedule(GameEvent.iterate)
        elif self.state == GameState.over:
            self.restart_button = tk.Button(self.marquee, text="restart", command=self.restart)
            self.restart_button.pack(side="top")

    def add_piece(self) -> None:
        """Spawn the next tetromino at the top-centre of the board.

        The piece's local-frame coordinates are translated to board-frame by
        the vector ``(board.width//2 - pdeg//2, board.height - 1 - piece.max_y)``,
        placing its top edge flush with the top of the board.

        If the spawn position is already occupied by locked pieces,
        the game transitions to :attr:`GameState.over`.

        The piece is **not** written to the occupancy grid at spawn; it lives
        only in ``self.piece`` until :meth:`lock_piece` commits it.
        """

        def get_next_piece() -> None:
            """Select and preview a new random piece."""
            self.preview_board.clear()
            self.next_piece = random.choice(tetrominoes)
            # Centre piece in preview board
            cx = self.preview_board.width // 2
            cy = self.preview_board.height // 2
            t = Translation(cx - int(self.next_piece.origin[0]), cy - int(self.next_piece.origin[1]))
            preview_grid = Grid(self.preview_board.width, self.preview_board.height)
            moved = self.next_piece.translate(t, preview_grid)
            if moved is not None:
                self.next_piece = moved
            self.preview_board.render(preview_grid, self.next_piece)

        if not self.next_piece:
            get_next_piece()
        piece = self.next_piece
        assert piece is not None
        self.used[piece.name].set(self.used[piece.name].get() + 1)
        self.used["total"].set(self.used["total"].get() + 1)
        get_next_piece()

        # Translate to spawn position: top-centre of the board
        spawn_x = self.board.width // 2 - self.pdeg // 2
        spawn_y = self.board.height - 1 - piece.max_y
        spawn_t = Translation(spawn_x - int(piece.origin[0]), spawn_y - int(piece.origin[1]))
        spawned = piece.translate(spawn_t, self._grid)

        if spawned is not None:
            match self._config.shadow:
                case "projection":
                    if self.projection_board is not None:
                        self.projection_board.clear()
                case "shadow":
                    for s in self._shadow_squares:
                        self.board.delete(f"shadow_{s.x}_{s.y}")
                    self._shadow_squares = frozenset()
            self.piece = spawned
            self._sync_logger_time()
            self.event_logger.log(EventType.piece_spawn, piece_type=piece.name)
            self._render()
        else:
            self.piece = piece
            self._sync_logger_time()
            self.event_logger.log(EventType.game_over, reason="cannot spawn")
            self.event_logger.stop(self._get_stats())
            self.event_logger.save()
            self.set_state(GameState.over)

    def move_piece(self, t: EigenTransformation) -> bool:
        """Apply a transformation to the active piece.

        This is the **single canonical entry point for all input actions**
        (human or agent).  It enforces the state guard:

        * Returns ``False`` immediately if the game is not
          :attr:`GameState.running` or no piece is active.

        Dispatches via ``match``/``case`` on the :class:`EigenTransformation`
        union type:

        * :class:`Translation` — calls :meth:`Polyomino.translate`.
        * :class:`Rotation` — calls :meth:`Polyomino.rotate` (with functional
          boundary kicks; see :ref:`boundary-kicks` in ``docs/mathematics.rst``).

        Both paths use value semantics: the method returns a new
        :class:`Polyomino` or ``None``; the game state is updated only on
        success.

        :param t: The :class:`EigenTransformation` to apply.
        :returns: ``True`` if the piece moved successfully.
        """
        if self.state != GameState.running or self.piece is None:
            return False

        result: Polyomino | None = None
        match t:
            case Translation():
                result = self.piece.translate(t, self._grid)
            case Rotation():
                result = self.piece.rotate(t, self._grid, kick=self._config.kick)

        if result is None:
            return False

        old_piece = self.piece
        self.piece = result
        self._render()

        self._sync_logger_time()
        match t:
            case Rotation():
                direction_str = "CW" if t.steps > 0 else "CCW"
                self.event_logger.log(EventType.piece_rotate, piece_type=old_piece.name, direction=direction_str)
            case Translation(dx=dx) if dx != 0:
                dir_str = "right" if dx > 0 else "left"
                self.event_logger.log(EventType.piece_move, piece_type=old_piece.name, direction=dir_str)
            case Translation(dy=dy) if dy < 0:
                self.event_logger.log(EventType.piece_move, piece_type=old_piece.name, direction="down")
        return True

    def remove_full_rows(self) -> None:
        """Remove full rows, shift overburden, and update statistics.

        A row at height :math:`y` is *full* when every cell in
        :math:`\\{0,\\ldots,w-1\\} \\times \\{y\\}` is in ``_grid``.
        Full rows are removed and the overburden shifted down:

        .. math::

            y' = y - |\\{y_f < y : y_f \\text{ is a full row}\\}|.

        Both the occupancy map and the rendering are updated.
        """
        width, height = self.board.width, self.board.height

        full_rows = [y for y in range(height) if all(Square(x, y) in self._grid._occupancy for x in range(width))]

        if not full_rows:
            return

        full_count = len(full_rows)
        full_set = set(full_rows)

        # Build new occupancy: remove full rows, shift overburden down
        new_occupancy: dict[Square, str] = {}
        for s, name in self._grid.occupied().items():
            if s.y in full_set:
                continue
            rows_below = sum(1 for fy in full_rows if fy < s.y)
            new_s = Square(s.x, s.y - rows_below)
            new_occupancy[new_s] = name

        self._grid._occupancy = new_occupancy

        # Re-render board from scratch after row removal (locked state changed)
        self.board.clear()
        self._render(locked_dirty=True)

        self._update_removed(full_count)
        if full_count > 0:
            self._sync_logger_time()
            self.event_logger.log(EventType.row_clear, count=full_count)

    def _get_stats(self) -> dict[str, typing.Any]:
        """Collect current game statistics into a plain dictionary.

        :returns: Dictionary with keys ``pieces``, ``rows_cleared``,
            ``rows_by_count`` (list indexed by simultaneous-clear count − 1),
            and ``pieces_by_type`` (dict mapping piece name to usage count).
        """
        return {
            "pieces": self.used["total"].get(),
            "rows_cleared": self.removed_total.get(),
            "rows_by_count": [var.get() for var in self.removed_by_count],
            "pieces_by_type": {name: var.get() for name, var in self.used.items() if name != "total"},
        }
