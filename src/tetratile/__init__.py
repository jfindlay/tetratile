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

import copy
import datetime as dt
import enum
import importlib
import importlib.metadata
import math
import random
import tkinter as tk
import typing
from dataclasses import dataclass, field
from decimal import Decimal as D

from .config import BoardConfig, GameConfig
from .event_log import EventLogger, EventType
from .input_handler import InputHandler
from .output import OutputHandler

_VERSION: str = importlib.metadata.version("tetratile")


class Dimension(enum.IntEnum):
    """Map Cartesian coordinate axes to their index in a coordinate pair.

    Each value equals the 1-based index of the corresponding axis in an
    ``[x, y, ...]`` coordinate pair, so ``coord[Dimension.X - 1]`` yields
    the x component.

    :attr X: The x axis (column); index 0 in ``[x, y]`` pairs.
    :attr Y: The y axis (row); index 1 in ``[x, y]`` pairs.
    :attr Z: The z axis (depth); index 2 in ``[x, y, z]`` triples (polycubes).
    """

    X = 1
    Y = 2
    Z = 3


class EigenTransformation(enum.IntEnum):
    """Atomic generators of the transform group :math:`\\mathbb{Z}^2 \rtimes C_4`.

    Each member names one irreducible move from which all valid piece
    transformations are composed:

    - :attr:`identity` is the group identity element.
    - :attr:`rotation` generates :math:`C_4 \\cong \\mathbb{Z}/4\\mathbb{Z}`;
      ``Transformation(rotation, +1)`` is one CW quarter-turn,
      ``Transformation(rotation, -1)`` is one CCW quarter-turn.
    - :attr:`horizontal` generates the :math:`e_x = (1,0)` direction of
      :math:`\\mathbb{Z}^2`; ``multiple > 0`` is rightward.
    - :attr:`vertical` generates a **downward** unit step by convention
      (``multiple=+1`` maps to ``dy=-1`` in the y-up frame).  Gravity
      therefore uses ``Transformation(vertical, 1)``.  This sign
      convention is a deliberate gravity alignment and will be corrected
      to the standard y-up sign in the planned refactor, where the
      translation type :class:`Translation` ``(dx, dy)`` makes the
      direction explicit with ``dy > 0`` meaning up.

    The values :attr:`min`, :attr:`max`, :attr:`bottom` are **not**
    eigentransformations in the group-theoretic sense; they are *derived*
    operations that compute the supremum of the piece's orbit under a unit
    generator (see :ref:`extremal-translations` in ``docs/mathematics.rst``
    and :meth:`.InputHandler.move_left_max`).  They are retained here
    temporarily for backward compatibility and are scheduled for removal;
    they belong in :class:`.InputHandler`, not in this type.  The integer
    gap at values 4–5 is a legacy artifact from a previous interface
    version.

    :attr identity: The group identity; no transformation applied.
    :attr rotation: Generator of :math:`C_4`; one quarter-turn per multiple.
    :attr horizontal: Generator of the :math:`e_x` direction; one step per multiple.
    :attr vertical: Generator of the gravity direction; ``multiple=+1`` means one step down.
    :attr min: Derived: translate to leftmost reachable position (orbit supremum under :math:`-e_x`).
    :attr max: Derived: translate to rightmost reachable position (orbit supremum under :math:`+e_x`).
    :attr bottom: Derived: translate to lowest reachable position (orbit supremum under :math:`-e_y`).
    """

    identity = 0
    rotation = 1
    horizontal = 2
    vertical = 3
    min = 6
    max = 7
    bottom = 8


@dataclass
class Transformation:
    """An element of the generating set of :math:`G = \\mathbb{Z}^2 \rtimes C_4`.

    A :class:`Transformation` pairs an :class:`EigenTransformation` (an
    atomic generator) with an integral **multiple** that scales it.  The
    term *multiple* rather than *magnitude* is deliberate: the scale factor
    must be an integer because :math:`\\mathbb{Z}^2` admits only integer
    displacements — real-valued scaling is not valid on the lattice.

    Examples::

        Transformation(EigenTransformation.rotation, 1)    # one CW quarter-turn
        Transformation(EigenTransformation.horizontal, -1) # one step left
        Transformation(EigenTransformation.vertical, 1)    # one step down (gravity)

    In the planned refactor this dataclass is replaced by the richer union
    type ``type EigenTransformation = Translation | Rotation`` (named tuple
    types that embed both the direction and the multiple), which eliminates
    the need for a separate wrapper.

    :attr eigentransformation: The atomic generator to apply.
    :attr multiple: Integral scale factor; sign encodes direction for
        ``rotation`` (:math:`+1` = CW) and ``horizontal`` (:math:`+1` = right).
        For ``vertical``, :math:`+1` maps to :math:`dy = -1` (downward) by
        convention.  Ignored for ``min``, ``max``, ``bottom``.
    """

    eigentransformation: EigenTransformation
    multiple: int = 1


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


@dataclass
class GameObservation:
    r"""Read-only snapshot of the game state for agents and human observers.

    Passed to every registered :class:`.OutputHandler` after each gravity
    tick via :meth:`.TetraTile._notify_observers`.  Also returned directly
    by :meth:`.TetraTile.get_observation` for agent polling.

    The board is encoded in **row-major** order — ``board[y][x]`` — with
    ``y=0`` at the bottom row, matching the standard convention for numpy
    arrays and machine-learning agent consumption.  Note the transposition
    relative to Tkinter canvas coordinates (which are y-down).

    The ``current_piece_coords`` list uses Cartesian :math:`(x, y)` pairs
    (not row-major): ``x=0`` is the left column, ``y=0`` is the bottom row.
    These are the same coordinates used throughout the game logic.

    In the planned refactor this dataclass gains ``frozen=True`` to make
    snapshots immutable.

    :attr board: Row-major board; ``board[y][x]`` is ``None`` (empty) or
        the tetromino name string (occupied).
    :attr current_piece: Single-letter name of the currently falling piece,
        or ``None`` between pieces.
    :attr current_piece_coords: List of ``[x, y]`` Cartesian coordinates for
        the current piece's squares.
    :attr current_piece_state: SRS rotation state in :math:`\{0,1,2,3\}`;
        corresponds to the position in :math:`C_4`.
    :attr next_piece: Name of the next piece to spawn, or ``None``.
    :attr stats: Dictionary of game statistics (pieces placed, rows cleared, etc.).
    :attr state: Current :class:`GameState`.
    :attr elapsed: Elapsed game time.
    """

    board: list[list[str | None]]
    current_piece: str | None
    current_piece_coords: list[list[int]]
    current_piece_state: int
    next_piece: str | None
    stats: dict[str, typing.Any]
    state: GameState
    elapsed: dt.timedelta


@dataclass
class Colors:
    """Rendering colors for a :class:`Polyomino`.

    Three color variants (normal face, lighter bevel, darker bevel) give
    each piece a distinct 3-D appearance.  In the planned refactor
    :class:`Colors` becomes a ``NamedTuple`` for immutability and
    hashability.

    :attr normal: Primary face color (hex string, e.g. ``"#CC6666"``).
    :attr light: Lighter bevel color for the highlight edge.
    :attr dark: Darker bevel color for the shadow edge.
    """

    normal: str = ""
    light: str = ""
    dark: str = ""


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


@dataclass
class Square:
    """A unit cell of the :math:`\\mathbb{Z}^2` lattice together with its render state.

    Mathematically, a :class:`Square` at coordinates :math:`(x, y)` is the
    open unit cell :math:`(x, x+1) \times (y, y+1) \\subset \\mathbb{R}^2`,
    identified by its lower-left corner :math:`(x, y) \\in \\mathbb{Z}^2`.

    **Current design note.**  This dataclass currently conflates two distinct
    concerns:

    - *Game state*: ``type`` (which piece occupies the cell) and ``is_active``
      (whether the cell belongs to the currently falling piece).
    - *Render state*: ``colors`` and ``id`` (Tkinter canvas item identifier).

    The planned refactor separates these: :class:`Square` will become a
    ``NamedTuple(x: int, y: int)`` — a pure lattice-cell identifier —
    while :class:`Board` maintains its own ``dict[Square, int]`` (canvas IDs)
    and ``dict[Square, Colors]`` (rendering colors).  The ``is_active`` flag
    will be eliminated once the active piece is never written to the grid.

    :attr colors: Rendering colors; ``None`` for an empty cell.
    :attr id: Tkinter canvas item ID for the drawn square; ``None`` if undrawn.
    :attr is_active: ``True`` if this cell belongs to the currently falling piece.
        Used to exclude active cells from full-row detection and row-shift logic.
    :attr type: Name of the tetromino occupying this cell; ``None`` if empty.
    """

    colors: Colors | None = None
    id: int | None = None
    is_active: bool | None = None
    type: str | None = None


class Grid:
    """Finite rectangular sublattice :math:`\\mathcal{B} \\subset \\mathbb{Z}^2` with occupancy.

    Models the region :math:`\\{0,\\ldots,w-1\\} \times \\{0,\\ldots,h-1\\}` of
    the integer lattice.  Each cell :math:`(x, y)` is the unit open square
    :math:`(x, x+1) \times (y, y+1)`; the integer point :math:`(x, y)` is
    its lower-left corner.  ``Grid[0, 0]`` is the bottom-left cell;
    ``Grid[width-1, height-1]`` is the top-right cell.

    The placement validity predicate :meth:`check` tests whether a set of
    candidate coordinates is entirely within :math:`\\mathcal{B}` and
    overlaps no currently occupied cell:

    .. math::

        \\text{valid}(\\mathcal{G}, S)
        \\iff
        \\forall s \\in S:\\; s \\in \\mathcal{B}
        \\;\\wedge\\; s \\notin \\operatorname{dom}(\\mathcal{G}).

    **Current design note.**  The grid currently stores :class:`Square`
    objects that mix game state (``type``, ``is_active``) with render state
    (``colors``, ``id``).  The planned refactor replaces the internal
    ``_grid`` with a sparse ``dict[Square, str]`` (``Occupancy``) holding
    only locked-piece cells.  The active piece will never be written here.

    :attr width: Number of columns in the grid.
    :attr height: Number of rows in the grid.
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize the game grid with all cells empty.

        :param width: Number of columns.
        :param height: Number of rows.
        """
        self._grid = [[Square() for i in range(height)] for j in range(width)]
        self.width = width
        self.height = height

    def __check_nonnegative(self, v: list[int] | tuple[int, int]) -> None:
        """Validate that coordinates are nonnegative.

        :param v: Coordinates to validate.
        :raises IndexError: If coordinates are negative.
        """
        if min(v) < 0:
            raise IndexError("grid coordinates must be nonnegative")

    def __getitem__(self, v: list[int] | tuple[int, int]) -> Square:
        """Retrieve the square at coordinates ``v`` from the origin.

        :param v: Coordinates of the square.
        :returns: The square at the given coordinates.
        :raises IndexError: If coordinates are out of bounds or negative.
        """
        self.__check_nonnegative(v)
        return self._grid[v[0]][v[1]]

    def __setitem__(self, v: list[int] | tuple[int, int], square: Square) -> None:
        """Update the square at coordinates ``v`` from the origin.

        :param v: Coordinates of the square.
        :param square: The square to place at the coordinates.
        :raises IndexError: If coordinates are out of bounds or negative.
        """
        self.__check_nonnegative(v)
        self._grid[v[0]][v[1]] = square

    def __iter__(self) -> typing.Generator[list[int], None, None]:
        """Iterate over the grid squares.

        :yields: Coordinates of each square.
        """
        for x in range(self.width):
            for y in range(self.height):
                yield [x, y]

    def check(self, coords: list[list[int]]) -> bool:
        """Test the placement validity predicate for a set of candidate coordinates.

        A set of coordinates :math:`S` is *valid* when every element lies
        within the board domain :math:`\\mathcal{B}` and does not overlap an
        already-occupied cell:

        .. math::

            \\text{valid}(\\mathcal{G}, S)
            \\iff
            \\forall s \\in S:\\; s \\in \\mathcal{B}
            \\;\\wedge\\; s \\notin \\operatorname{dom}(\\mathcal{G}).

        :param coords: List of ``[x, y]`` candidate coordinates.
        :returns: ``True`` if every coordinate is in-bounds and unoccupied.
        """
        for v in coords:
            try:
                self[v]
            except IndexError:
                return False
            if self[v].type is not None:
                return False
        return True

    def print(self) -> None:
        """Display grid state to stdout for debugging.

        Rows are printed top-to-bottom (``y = height-1`` first) with a
        screen-row counter on the left.  Each occupied cell shows the first
        two characters of its piece name; empty cells show two spaces.
        """
        rows: dict[int, dict[int, str]] = {}
        for v in self:
            square = self[v]
            if v[1] not in rows:
                rows[v[1]] = {}
            rows[v[1]][v[0]] = " " if square.type is None else square.type

        digits = len(str(self.height))
        row_fmt = f"{{:0{digits}}}"
        print(digits * " " + "+" + 2 * len(self._grid) * "-" + "+")
        for i in reversed(rows.keys()):
            row_image = "".join([2 * rows[i][j] if len(rows[i][j]) == 1 else rows[i][j][:2] for j in sorted(rows[i].keys())])
            print(row_fmt.format(self.height - i - 1) + "|" + row_image + "|")
        print(digits * " " + "+" + 2 * len(self._grid) * "-" + "+")


@dataclass
class Polyomino:
    r"""A polyomino — a connected finite subset of the integer lattice :math:`\mathbb{Z}^2`.

    A polyomino of **ordinal** :math:`n` (an :math:`n`-omino) is a connected
    finite set of :math:`n` unit cells of :math:`\mathbb{Z}^2`.  This class
    represents one, together with a rotation pivot and rendering metadata.

    **Coordinate convention.**  Each entry in ``coords`` is an ``[x, y]``
    pair identifying a cell by its lower-left corner.  The cell at
    :math:`(x, y)` occupies :math:`(x, x+1) \times (y, y+1)` in the plane.
    Coordinates use y-up orientation: :math:`y = 0` is the bottom row.

    **Rotation pivot** ``o``.  The pivot is stored with
    :class:`~decimal.Decimal` arithmetic so that half-integer centres (used
    by Z, S, I, O) are preserved exactly through all four rotation states.
    For pieces whose geometric centre of symmetry is a half-integer point,
    ``o = [D('-0.5'), D('-0.5')]`` in local frame; for others ``o = [0, 0]``.
    See :ref:`half-integer-origin` in ``docs/mathematics.rst``.

    **Planned refactor.**  ``coords`` becomes ``frozenset[Square]`` (a set,
    since a polyomino has no canonical cell ordering), ``o`` becomes
    ``tuple[Decimal, Decimal]``, ``dim`` is removed (always 2 in this game),
    and ``full``/``full_below_count`` are removed (board-bookkeeping state
    that pollutes the geometry class).

    :attr dim: Number of coordinate dimensions (always :attr:`Dimension.Y` = 2).
    :attr colors: Rendering colors for this piece.
    :attr coords: List of ``[x, y]`` lower-left corners of each cell.
    :attr o: Rotation pivot in the current board frame; uses
        :class:`~decimal.Decimal` for exact half-integer arithmetic.
    :attr name: Single-letter piece identifier (e.g. ``"T"``, ``"Z"``).
    :attr full: Temporary flag set by :meth:`.Board._get_rows`; ``True`` if
        this row-polyomino occupies a completely filled row.  Scheduled for
        removal (board bookkeeping does not belong on the geometry type).
    :attr full_below_count: Temporary count set by :meth:`.Board._get_rows`;
        number of full rows below this row.  Also scheduled for removal.
    """

    dim: Dimension
    colors: Colors
    coords: list[list[int]]

    o: list[D] = field(init=False)
    name: str = ""
    full: bool = field(default=False, init=False)
    full_below_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        """Compute the rotation pivot from the coordinate centroid.

        For integer-centre pieces the centroid is an integer lattice point and
        the ``Decimal`` values are whole numbers.  For half-integer-centre
        pieces (Z, S, I, O) the constructor supplies ``coords`` shifted by
        :math:`(-0.5, -0.5)` so that the centroid is the correct rotation
        pivot; the caller also sets ``o`` via direct assignment after
        construction.
        """
        self.o = [D(sum([v[d] for v in self.coords]) / len(self.coords)) for d in range(self.dim)]

    def min(self, dim: Dimension | None = None) -> int:
        """Return the minimum coordinate of the polyomino along the given axis.

        Equivalent to :math:`\\min_{s \\in \\text{squares}} s_d` where
        :math:`d` is the index of the requested dimension.  In the planned
        refactor this method is replaced by the named properties
        ``min_x`` and ``min_y``.

        :param dim: Axis to query (:attr:`Dimension.X` or :attr:`Dimension.Y`).
            Defaults to ``self.dim``.
        :returns: Minimum coordinate value along that axis.
        """
        d = dim if dim is not None else self.dim
        return min([c[d.value - 1] for c in self.coords])

    def max(self, dim: Dimension | None = None) -> int:
        """Return the maximum coordinate of the polyomino along the given axis.

        Equivalent to :math:`\\max_{s \\in \\text{squares}} s_d`.  In the
        planned refactor replaced by ``max_x`` and ``max_y`` properties.

        :param dim: Axis to query; defaults to ``self.dim``.
        :returns: Maximum coordinate value along that axis.
        """
        d = dim if dim is not None else self.dim
        return max([c[d.value - 1] for c in self.coords])

    def transform(self, t: Transformation, grid: Grid) -> bool:
        """Apply an :class:`EigenTransformation` to the polyomino.

        Dispatches to :meth:`rotate` or :meth:`translate` based on the
        type of generator.  In the planned refactor this method accepts the
        richer union type ``EigenTransformation = Translation | Rotation``
        and uses ``match``/``case`` structural pattern matching.

        :param t: The transformation to apply.
        :param grid: The grid to transform within.
        :returns: ``True`` if the transformation was applied successfully.
        """
        match t.eigentransformation:
            case EigenTransformation.identity:
                return True
            case EigenTransformation.rotation:
                return self.rotate(t, grid)
            case EigenTransformation.horizontal | EigenTransformation.vertical:
                return self.translate(t, grid)
            case EigenTransformation.min | EigenTransformation.max | EigenTransformation.bottom:
                return self.translate(t, grid)
        return False  # unreachable: all EigenTransformation members are covered above

    def rotate(self, r: Transformation, grid: Grid) -> bool:
        """Rotate the polyomino about its proper origin.

        Applies the standard CW quarter-turn in :math:`y`-up Cartesian
        coordinates:

        .. math::

            (dx, dy) \\;\\longmapsto\\; (dy, -dx)
            \\quad\\text{for }\\texttt{multiple}=+1\\text{ (clockwise)},

            (dx, dy) \\;\\longmapsto\\; (-dy, dx)
            \\quad\\text{for }\\texttt{multiple}=-1\\text{ (counterclockwise).}

        About pivot :math:`(o_x, o_y)`, cell :math:`(x_i, y_i)` maps to

        .. math::

            x_i' = r \\cdot (y_i - o_y) + o_x, \\qquad
            y_i' = -r \\cdot (x_i - o_x) + o_y,

        where :math:`r` = ``multiple``.  The :func:`int` truncation is exact
        for integer-centre pieces (T, L, J) and exact for half-integer-centre
        pieces (Z, S, I, O) because :class:`~decimal.Decimal` arithmetic
        preserves ``o`` without rounding.

        This is the base implementation for non-tetromino polyominoes.
        :class:`Tetromino` overrides this to use the SRS kick system.  In the
        planned refactor both implementations are unified in a single
        :meth:`rotate` that uses functional boundary kicks (see
        :ref:`boundary-kicks` in ``docs/mathematics.rst``).

        :param r: Rotation transformation; ``multiple=+1`` is CW, ``multiple=-1`` is CCW.
        :param grid: The grid to validate the rotated position against.
        :returns: ``True`` if the rotated position is valid and the piece was moved.
        """
        coords = [[0 for d in range(self.dim)] for _ in self.coords]
        for i, _ in enumerate(self.coords):
            coords[i][0] = int(r.multiple * (self.coords[i][1] - self.o[1]) + self.o[0])
            coords[i][1] = int(-r.multiple * (self.coords[i][0] - self.o[0]) + self.o[1])
        if grid.check(coords):
            self.coords = coords
            return True
        return False

    def translate(self, t: Transformation | list[int], grid: Grid) -> bool:
        """Translate the polyomino within the grid.

        When ``t`` is a raw ``[dx, dy]`` list, or when the eigentransformation
        is ``horizontal`` or ``vertical``, a **single step** is applied: the
        piece moves by ``(dx, dy)`` if the destination is valid, otherwise the
        piece is unchanged.

        When the eigentransformation is ``min``, ``max``, or ``bottom``
        (scheduled for removal — see :class:`EigenTransformation`), the piece
        is moved *incrementally* one unit at a time until the next step would
        be invalid.  This computes the **supremum of the piece's orbit** under
        the unit generator; see :ref:`extremal-translations` in
        ``docs/mathematics.rst``.

        In the planned refactor this method is replaced by a value-returning
        ``translate(t: Translation, grid: Grid) -> Polyomino | None``.

        :param t: Translation specification — a ``Transformation`` or a raw
            ``[dx, dy]`` list.
        :param grid: The grid to validate positions against.
        :returns: ``True`` if the piece moved (including for the incremental
            case, which always returns ``True`` regardless of how far it moved).
        """
        dx, dy, single_step = self._get_translation(t)
        if dx is None and dy is None:
            return False

        if single_step:
            coords = [[self.coords[i][0] + dx, self.coords[i][1] + dy] for i, _ in enumerate(self.coords)]
            if grid.check(coords):
                self.coords = coords
                self.o = [self.o[0] + dx, self.o[1] + dy]
                return True
        else:
            while True:
                coords = [[self.coords[i][0] + dx, self.coords[i][1] + dy] for i, _ in enumerate(self.coords)]
                if not grid.check(coords):
                    break
                self.coords = coords
                self.o = [self.o[0] + dx, self.o[1] + dy]
            return True
        return False

    def _get_translation(self, t: Transformation | list[int]) -> tuple[int, int, bool]:
        """Decode a translation specification into a unit vector and step mode.

        Returns ``(dx, dy, single_step)`` where ``single_step=True`` means
        apply once, ``single_step=False`` means apply repeatedly until blocked
        (the inductive supremum computation for ``min``/``max``/``bottom``).

        Note the sign convention for ``vertical``: ``multiple=+1`` returns
        ``dy=-1`` (one step *down*), because the ``vertical`` generator
        points in the gravity direction by convention.  This will be
        corrected in the refactor to a consistent y-up sign (where
        ``Translation(0, -1)`` explicitly means downward).

        :param t: A :class:`Transformation` or a raw ``[dx, dy]`` list.
        :returns: ``(dx, dy, single_step)`` tuple.
        """
        if isinstance(t, list):
            return t[0], t[1], True
        match t.eigentransformation:
            case EigenTransformation.horizontal:
                return t.multiple, 0, True
            case EigenTransformation.vertical:
                return 0, -t.multiple, True
            case EigenTransformation.min:
                return -1, 0, False
            case EigenTransformation.max:
                return 1, 0, False
            case EigenTransformation.bottom:
                return 0, -1, False
        return 0, 0, True


@dataclass(frozen=True)
class TetrominoData:
    """Immutable spawn-state geometry and colors for a single tetromino type.

    ``coords`` stores the four cell positions in the piece's local (origin-
    centred) coordinate frame using :class:`~decimal.Decimal` values.  For
    pieces whose geometric centre of symmetry is a half-integer point (Z, S,
    I, O), the coordinates encode the half-integer shift needed to locate the
    pivot exactly — the :class:`Tetromino` constructor extracts the integer
    cell positions and sets ``o = [D('-0.5'), D('-0.5')]`` accordingly.

    :attr name: Single-letter piece identifier.
    :attr coords: Local-frame cell positions as ``(x, y)`` :class:`~decimal.Decimal` pairs.
    :attr normal: Primary face color (hex string).
    :attr light: Lighter bevel color (hex string).
    :attr dark: Darker bevel color (hex string).
    """

    name: str
    coords: tuple[tuple[D, D], ...]
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

    :attr Z: Z-tetromino; half-integer centre, spawns in two-row zigzag.
    :attr S: S-tetromino; half-integer centre, mirror of Z.
    :attr l: I-tetromino (four in a row); half-integer centre.
    :attr T: T-tetromino; integer centre, T-shape.
    :attr o: O-tetromino (2×2 square); half-integer centre.
    :attr L: L-tetromino; integer centre, L-shape.
    :attr J: J-tetromino; integer centre, J-shape (mirror of L).
    """

    Z = TetrominoData(
        name="Z",
        coords=((D("-1"), D("1")), (D("0"), D("1")), (D("0"), D("0")), (D("1"), D("0"))),
        normal="#CC6666",
        light="#F89FAB",
        dark="#803C3B",
    )
    S = TetrominoData(
        name="S",
        coords=((D("-1"), D("0")), (D("0"), D("0")), (D("0"), D("1")), (D("1"), D("1"))),
        normal="#66CC66",
        light="#79FC79",
        dark="#3B803B",
    )
    l = TetrominoData(  # noqa: E741
        name="l",
        coords=((D("-2"), D("0")), (D("-1"), D("0")), (D("0"), D("0")), (D("1"), D("0"))),
        normal="#6666CC",
        light="#7979FC",
        dark="#3B3B80",
    )
    T = TetrominoData(
        name="T",
        coords=((D("-1"), D("0")), (D("0"), D("0")), (D("1"), D("0")), (D("0"), D("1"))),
        normal="#CCCC66",
        light="#FCFC79",
        dark="#80803B",
    )
    o = TetrominoData(
        name="o",
        coords=((D("-1"), D("0")), (D("-1"), D("-1")), (D("0"), D("0")), (D("0"), D("-1"))),
        normal="#CC66CC",
        light="#FC79FC",
        dark="#803B80",
    )  # noqa: E741
    L = TetrominoData(
        name="L",
        coords=((D("-1"), D("0")), (D("0"), D("0")), (D("1"), D("0")), (D("1"), D("1"))),
        normal="#66CCCC",
        light="#79FCFC",
        dark="#3B8080",
    )
    J = TetrominoData(
        name="J",
        coords=((D("-1"), D("0")), (D("0"), D("0")), (D("1"), D("0")), (D("-1"), D("1"))),
        normal="#DAAA00",
        light="#FCC600",
        dark="#806200",
    )

    @property
    def tetromino(self) -> "Tetromino":
        """Create a Tetromino instance from this type.

        :returns: A new Tetromino instance with this type's data.
        """
        return Tetromino(self.value)


# SRS_KICK_JLSTZ: precomputed wall-kick offsets for J, L, S, T, Z pieces.
#
# Each key ``(state_before, state_after)`` identifies a rotation transition in
# C_4 = {0, 1, 2, 3} where 0 = spawn, 1 = CW-90°, 2 = 180°, 3 = CW-270°.
# Each value is a list of (dx, dy) offsets in the y-up coordinate system
# (y-values are negated from the Tetris Wiki, which uses y-down).  The offsets
# are tried in order; the first placement accepted by Grid.check wins.
#
# Planned removal: the refactor replaces these tables with the _boundary_kicks
# algebraic generator derived from the rotated piece's bounding box.
# See docs/mathematics.rst §Boundary Kicks.
SRS_KICK_JLSTZ: dict[tuple[int, int], list[tuple[int, int]]] = {
    (0, 0): [],
    (0, 1): [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)],
    (0, 3): [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)],
    (1, 0): [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)],
    (1, 1): [],
    (1, 2): [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)],
    (2, 1): [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)],
    (2, 2): [],
    (2, 3): [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)],
    (3, 0): [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)],
    (3, 2): [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)],
    (3, 3): [],
}

# SRS_KICK_I: precomputed wall-kick offsets for the I (l) piece.
# Same key/value structure as SRS_KICK_JLSTZ but with I-piece-specific offsets
# that account for its 4×1 bounding box and half-integer rotation centre.
# Planned removal: replaced by _boundary_kicks in the refactor.
SRS_KICK_I: dict[tuple[int, int], list[tuple[int, int]]] = {
    (0, 0): [],
    (0, 1): [(0, 0), (-2, 0), (+1, 0), (-2, +1), (+1, -2)],
    (0, 3): [(0, 0), (-1, 0), (+2, 0), (-1, -2), (+2, +1)],
    (1, 0): [(0, 0), (+2, 0), (-1, 0), (+2, -1), (-1, +2)],
    (1, 1): [],
    (1, 2): [(0, 0), (-1, 0), (+2, 0), (-1, -2), (+2, +1)],
    (2, 1): [(0, 0), (+1, 0), (-2, 0), (+1, +2), (-2, -1)],
    (2, 2): [],
    (2, 3): [(0, 0), (+2, 0), (-1, 0), (+2, -1), (-1, +2)],
    (3, 0): [(0, 0), (+1, 0), (-2, 0), (+1, +2), (-2, -1)],
    (3, 2): [(0, 0), (-2, 0), (+1, 0), (-2, +1), (+1, -2)],
    (3, 3): [],
}

# SRS_KICK_O: precomputed wall-kick offsets for the O (o) piece.
# All offsets are (0, 0): the O piece is rotationally symmetric about its
# 2×2 bounding box centre, so no corrective translation is ever needed.
# Planned removal: replaced by _boundary_kicks in the refactor (which will
# simply yield (0,0) only for the O piece, since it never violates boundaries).
SRS_KICK_O: dict[tuple[int, int], list[tuple[int, int]]] = {
    (0, 0): [],
    (0, 1): [],
    (0, 3): [],
    (1, 0): [],
    (1, 1): [],
    (1, 2): [],
    (1, 3): [],
    (2, 0): [],
    (2, 1): [],
    (2, 2): [],
    (2, 3): [],
    (3, 0): [],
    (3, 1): [],
    (3, 2): [],
    (3, 3): [],
}

# SRS_CENTERS: rotation pivot lookup by piece name.
#
# All entries are (D(0), D(0)) — a vestigial structure from a previous
# implementation where the I piece used a different centre.  The original
# half-integer pivot approach (origin = D('-0.5'), D('-0.5') for Z/S/I/O)
# was removed by agent-assisted edits; this dict records integer pivots for
# all pieces instead.  Scheduled for removal in the planned refactor, which
# restores half-integer origins for Z, S, I, O and eliminates this lookup.
SRS_CENTERS: dict[str, tuple[D, D]] = {
    "Z": (D(0), D(0)),
    "S": (D(0), D(0)),
    "l": (D(0), D(0)),
    "T": (D(0), D(0)),
    "o": (D(0), D(0)),
    "L": (D(0), D(0)),
    "J": (D(0), D(0)),
}


def used_keys() -> list[str]:
    """Return list of keys for the used dictionary.

    :returns: ["total", "Z", "S", "l", "T", "o", "L", "J"].
    """
    return ["total"] + [t.value.name for t in TetrominoType]


class Tetromino(Polyomino):
    """A :class:`Polyomino` of ordinal 4, with SRS rotation-state tracking.

    Subclasses :class:`Polyomino` to add ``rotation_state``, which tracks
    the piece's current position in :math:`C_4 = \\{0, 1, 2, 3\\}` for SRS
    kick-table lookup.  State ``0`` is the spawn orientation, ``1`` is
    CW-90°, ``2`` is 180°, ``3`` is CW-270°.

    **Planned removal.**  The planned refactor removes this subclass entirely:

    * All pieces become plain :class:`Polyomino` instances.
    * ``rotation_state`` is unnecessary once the SRS kick tables are replaced
      by the ``_boundary_kicks`` algebraic generator.
    * A piece *knows* it is a tetromino through the ``ordinal`` property
      (``piece.ordinal == 4``), not via subclass identity.

    :attr dim: Always :attr:`Dimension.Y` (= 2) for tetrominoes.
    :attr name: Single-letter piece identifier.
    :attr rotation_state: Current :math:`C_4` index; used to look up SRS kicks.
    """

    dim: Dimension = Dimension.Y
    name: str = ""
    rotation_state: int = 0

    def __init__(self, data: TetrominoData | None = None) -> None:
        """Initialize a tetromino from :class:`TetrominoData`.

        :param data: Spawn-state geometry and colors.  If ``None``, creates
            an empty tetromino with no cells or colors.
        """
        self.coords: list[list[int]] = []
        self.colors: Colors = Colors("", "", "")
        self.rotation_state = 0
        if data is not None:
            self.name = data.name
            self.colors = Colors(data.normal, data.light, data.dark)
            self.coords = [[int(v[0]), int(v[1])] for v in data.coords]
            self.o = [SRS_CENTERS.get(data.name, (D(0), D(0)))[0], SRS_CENTERS.get(data.name, (D(0), D(0)))[1]]
        self.dim = Dimension.Y

    def _get_kick_table(self) -> dict[tuple[int, int], list[tuple[int, int]]]:
        """Return the SRS kick table appropriate for this piece.

        Routes to :data:`SRS_KICK_O` (O piece), :data:`SRS_KICK_I` (I piece),
        or :data:`SRS_KICK_JLSTZ` (all others).

        :returns: Kick-offset table keyed by ``(state_before, state_after)``.
        """
        if self.name == "o":
            return SRS_KICK_O
        elif self.name == "l":
            return SRS_KICK_I
        return SRS_KICK_JLSTZ

    def _rotate_coords(self, direction: int) -> list[list[int]]:
        """Compute freely-rotated coordinates (no grid validity check).

        Applies the standard CW quarter-turn formula in :math:`y`-up
        Cartesian coordinates:

        .. math::

            x_i' = d \\cdot (y_i - o_y) + o_x, \\qquad
            y_i' = -d \\cdot (x_i - o_x) + o_y,

        where :math:`d` = ``direction``.  ``direction=+1`` gives
        :math:`(dx,dy) \\mapsto (dy,-dx)` (CW); ``direction=-1`` gives
        :math:`(dx,dy) \\mapsto (-dy,dx)` (CCW).

        This method is extracted from :meth:`srs_rotate` so that the SRS
        algorithm can compute the rotated coordinates before checking each
        kick offset.  In the planned refactor this logic is inlined into a
        unified :meth:`Polyomino.rotate` method.

        :param direction: ``+1`` for CW, ``-1`` for CCW (y-up convention).
        :returns: New ``[x, y]`` coordinates for each cell after rotation.
        """
        coords = [[0 for _ in range(self.dim)] for _ in self.coords]
        for i, _ in enumerate(self.coords):
            coords[i][0] = int(direction * (self.coords[i][1] - self.o[1]) + self.o[0])
            coords[i][1] = int(-direction * (self.coords[i][0] - self.o[0]) + self.o[1])
        return coords

    def srs_rotate(self, direction: int, grid: Grid) -> bool:
        """Rotate using the Super Rotation System (SRS) with kick tables.

        Implements the Tetris Guideline SRS algorithm:

        1. Compute the rotation state transition
           :math:`k_{\\text{new}} = (k_{\\text{old}} + d) \\bmod 4` where
           :math:`d` = ``direction`` (:math:`+1` CW, :math:`-1` CCW).
        2. Look up the kick-offset list from the appropriate table
           (:data:`SRS_KICK_JLSTZ`, :data:`SRS_KICK_I`, or
           :data:`SRS_KICK_O`) for the state pair
           ``(state_old, state_new)``.
        3. For each offset :math:`(\\delta x, \\delta y)` in the list:
           compute the freely-rotated coordinates via
           :meth:`_rotate_coords`, translate by the offset, and test
           with :meth:`Grid.check`.
        4. Accept the first valid placement; update ``coords``, ``o``, and
           ``rotation_state``.  Return ``False`` if all offsets fail.

        This is the precomputed-table equivalent of the ``_boundary_kicks``
        algebraic generator that will replace it in the planned refactor.
        Both implement the *covariant rotation* concept: free rotation
        corrected by a compensating translation for the bounded domain.

        :param direction: ``+1`` for CW, ``-1`` for CCW (y-up convention).
        :param grid: The grid to validate each candidate placement against.
        :returns: ``True`` if a valid placement was found and the piece was moved.
        """
        old_state = self.rotation_state
        new_state = (old_state + direction) % 4
        kick_table = self._get_kick_table()
        kicks = kick_table.get((old_state, new_state), [(0, 0)])

        for kick_x, kick_y in kicks:
            coords = self._rotate_coords(direction)
            translated = [[c[0] + kick_x, c[1] + kick_y] for c in coords]
            if grid.check(translated):
                self.coords = translated
                self.o = [self.o[0] + D(kick_x), self.o[1] + D(kick_y)]
                self.rotation_state = new_state
                return True
        return False

    def rotate(self, r: Transformation, grid: Grid) -> bool:
        """Rotate using SRS with full kick tables.

        :param r: Rotation transformation with multiple indicating direction.
        :param grid: The grid to rotate within.
        :returns: True if rotation was successful.
        """
        return self.srs_rotate(r.multiple, grid)


tetrominoes: tuple[Tetromino, ...] = tuple(t.tetromino for t in TetrominoType)


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


class Board(tk.Canvas):
    """Tkinter canvas that renders the game board.

    Each :class:`Board` instance owns one :class:`Grid` (``_game_grid``)
    and acts as both the occupancy-map store and the rendering surface.

    **Coordinate systems.**  The game uses Cartesian :math:`y`-up coordinates
    (``y=0`` at the bottom).  Tkinter uses screen coordinates with ``y=0`` at
    the top.  The transform :math:`(x, y) \\mapsto (x, h-1-y)` — implemented in
    :meth:`_transform_coord` — converts between them.

    **Planned architectural change.**  The planned refactor separates state from
    rendering:

    * :class:`Grid` becomes a pure occupancy map (``dict[Square, str]``),
      owned directly by :class:`TetraTile`.
    * :class:`Board` becomes a pure rendering surface: it owns render maps
      (``dict[Square, int]`` for canvas IDs, ``dict[Square, Colors]``) but
      holds no game-state grid.

    :attr width: Grid width in squares (delegates to ``_game_grid.width``).
    :attr height: Grid height in squares (delegates to ``_game_grid.height``).
    """

    @property
    def width(self) -> int:
        """Grid width in squares."""
        return self._game_grid.width

    @property
    def height(self) -> int:
        """Grid height in squares."""
        return self._game_grid.height

    def __init__(self, config: GameConfig, parent: tk.Misc, width: int, height: int, is_projection: bool = False) -> None:
        """Initialize the board.

        :param config: Game configuration.
        :param parent: Parent widget.
        :param width: Grid width in squares.
        :param height: Grid height in squares.
        :param is_projection: Whether this is a projection (shadow) board.
        """
        self._config = config
        self.is_projection = is_projection
        self.border_width = config.board.scale // 16
        self.aspect_proportion = 3 if self.is_projection else 1
        self.full_row_colors = Colors("#DDDDDD", "#FFFFFF", "#BBBBBB")
        self.pause_cover_id = 0

        self._game_grid = Grid(width, height)

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

    def _transform_coord(self, v: list[int]) -> list[int]:
        """Convert Cartesian :math:`y`-up coordinates to Tkinter screen coordinates.

        The game uses :math:`y`-up orientation (:math:`y=0` at the bottom);
        Tkinter places the origin at the top-left with :math:`y` increasing
        downward.  The bijection is

        .. math::

            (x, y) \\;\\longmapsto\\; (x,\\; h - 1 - y),

        where :math:`h` is the board height.  This is an involution (its own
        inverse), so it converts in both directions.

        :param v: Cartesian ``[x, y]`` coordinates.
        :returns: Tkinter ``[x, screen_y]`` coordinates.
        """
        return [v[0], self.height - 1 - v[1]]

    def _draw_square(self, v: list[int], colors: Colors) -> int:
        """Draw a polyomino square on the board at ``v``.

        :param v: Coordinates of the square.
        :param colors: Colors to use for rendering.
        :returns: Tkinter canvas item ID.
        """
        u = self._transform_coord(v)
        scale = self._config.board.scale
        u = [scale * u[0], scale * u[1]]
        return self.create_rectangle(
            u[0] + self.border_width,
            u[1] + self.border_width,
            u[0] + scale,
            u[1] + scale // self.aspect_proportion,
            fill=colors.normal,
            outline=colors.dark,
            width=self.border_width,
        )

    def update(self, piece: Polyomino, clear: bool = False, is_active: bool = False, transparency: float = 0.0) -> None:
        """Place or clear a piece on the board.

        :param piece: The piece to place or clear.
        :param clear: If True, remove the piece. Otherwise place it.
        :param is_active: Whether the piece is active (falling).
        :param transparency: Transparency factor (0.0-1.0) to mix with black.
        """
        for v in piece.coords:
            u = [v[0], 0] if self.is_projection else v
            square = self._game_grid[u]
            if clear:
                if square.id is not None:
                    self.delete(square.id)
                square.type = None
                square.id = None
                square.colors = None
                square.is_active = None
            else:
                if not square.id:
                    colors = piece.colors
                    if transparency > 0:
                        colors = Colors(
                            mix_with_black(colors.normal, transparency),
                            mix_with_black(colors.light, transparency),
                            mix_with_black(colors.dark, transparency),
                        )
                    square.type = piece.name
                    square.id = self._draw_square(u, colors)
                    square.colors = colors
                    square.is_active = is_active

    def select_full_rows(self) -> bool:
        """Highlight full rows with a distinct color to signal impending removal.

        A row at height :math:`y` is *full* when every cell in
        :math:`\\{0, \\ldots, w-1\\} \\times \\{y\\}` is occupied by a locked piece
        (``is_active`` is false).  Full rows are redrawn in
        ``full_row_colors`` to provide a visual cue before the scheduled
        :meth:`remove_full_rows` call.

        :returns: ``True`` if at least one full row was found.
        """
        has_full_rows = False
        for y in range(self.height):
            row_coords = [
                [x, y] for x in range(self.width) if self._game_grid[x, y].type and not self._game_grid[x, y].is_active
            ]
            if len(row_coords) == self.width:
                has_full_rows = True
                row = Polyomino(
                    dim=Dimension.Y,
                    colors=self.full_row_colors,
                    coords=row_coords,
                    name="row",
                )
                row.full = True
                self.update(row, clear=True)
                self.update(row)
        return has_full_rows

    def _get_rows(self) -> tuple[int, list[Polyomino]]:
        """Collect all non-empty rows as temporary row-polyominoes.

        Each row is modelled as a degenerate :class:`Polyomino` (a
        :math:`1 \\times w` strip) carrying a ``full`` flag and a
        ``full_below_count`` (the number of full rows below it, used to
        compute the shift distance during row removal).

        This is a transitional representation: in the planned refactor the
        row-bookkeeping fields ``Polyomino.full`` and
        ``Polyomino.full_below_count`` are removed, and row operations work
        directly on the occupancy dict.

        :returns: ``(full_count, rows)`` — the number of full rows and a list
            of non-empty row polyominoes from bottom to top.
        """
        rows: list[Polyomino] = []
        full_count = 0
        for y in range(self.height):
            row_coords = [
                [x, y] for x in range(self.width) if self._game_grid[x, y].type and not self._game_grid[x, y].is_active
            ]
            if len(row_coords):
                row = Polyomino(
                    dim=Dimension.Y,
                    colors=Colors(),
                    coords=row_coords,
                    name="row",
                )
                rows.append(row)
                row.full = False
                row.full_below_count = full_count
            if len(row_coords) == self.width:
                full_count += 1
                row.full = True
                row.colors = self.full_row_colors
                self.update(row, clear=True)
                self.update(row)
        return full_count, rows

    def remove_full_rows(self) -> int:
        """Remove all full rows and shift the overburden down.

        Full rows are those where every cell is occupied by a locked piece.
        After removing them, each remaining locked cell at height :math:`y`
        is shifted down by the count of full rows strictly below it:

        .. math::

            y' = y - |\\{y_f < y : y_f \\text{ is a full row}\\}|.

        Cells are processed bottom-to-top to avoid overwriting unprocessed
        cells during the shift.  Both the occupancy data and the canvas
        rendering are updated atomically: each shifted cell is erased from
        its old position and redrawn at its new position.

        :returns: Number of rows removed.
        """
        full_count, rows = self._get_rows()

        # Identify full row indices (excluding active pieces)
        full_row_indices = [
            y
            for y in range(self.height)
            if all(self._game_grid[x, y].type and not self._game_grid[x, y].is_active for x in range(self.width))
        ]

        if not full_row_indices:
            return 0

        # Clear full rows
        for y in full_row_indices:
            for x in range(self.width):
                square = self._game_grid[x, y]
                if square.id is not None:
                    self.delete(square.id)
                square.type = None
                square.id = None
                square.colors = None
                square.is_active = None

        # Shift remaining cells down; iterate bottom-to-top to avoid overwriting
        for y in range(self.height):
            for x in range(self.width):
                if self._game_grid[x, y].type and not self._game_grid[x, y].is_active:
                    rows_below = sum(1 for fy in full_row_indices if fy < y)
                    if rows_below > 0:
                        new_y = y - rows_below
                        dest_square = self._game_grid[x, new_y]
                        src_square = self._game_grid[x, y]
                        dest_square.type = src_square.type
                        dest_square.colors = src_square.colors
                        dest_square.is_active = src_square.is_active
                        if src_square.colors:
                            dest_square.id = self._draw_square([x, new_y], src_square.colors)
                        if src_square.id is not None:
                            self.delete(src_square.id)
                        src_square.type = None
                        src_square.id = None
                        src_square.colors = None
                        src_square.is_active = None

        return len(full_row_indices)

    def clear(self) -> None:
        """Remove all occupied squares from the board."""
        _, rows = self._get_rows()
        for row in rows:
            self.update(row, clear=True)

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


class TetraTile(tk.Frame):
    """Game controller: owns the occupancy state, active piece, and rendering surfaces.

    :class:`TetraTile` is the central coordinator.  It owns:

    * ``board`` — the main :class:`Board` (canvas + :class:`Grid`).  In the
      planned refactor the :class:`Grid` will be lifted out into
      ``self._grid`` so that :class:`Board` becomes a pure renderer.
    * ``piece`` — the active :class:`Polyomino` (never written to
      ``board._game_grid`` while falling; only written at lock-time).
    * The input and output handler registries.

    All player and agent input enters through :meth:`move_piece`, which is
    the **single canonical state guard**: it returns ``False`` immediately
    unless the game is :attr:`GameState.running`.

    :meth:`iterate` is the **gravity clock**: one call applies the generator
    :math:`-e_y` (``Translation(0, -1)``), locking the piece and spawning
    the next one if it cannot descend.

    :attr board: Main rendering canvas with embedded game grid.
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
        self.next_piece: Tetromino | None = None
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
        self._shadow_coords: list[list[int]] = []
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

    def _update_piece_on_board(self, clear: bool = False, is_active: bool = True) -> None:
        """Place or clear the current piece and its projection on the board.

        :param clear: If True, remove the piece. Otherwise place it.
        :param is_active: Whether the piece is active (falling).
        """
        if self.piece is None:
            return

        stack_transparency = 0.15 if self._config.stack_transparency and not is_active else 0.0
        self.board.update(self.piece, clear=clear, is_active=is_active, transparency=stack_transparency)

        match self._config.shadow:
            case "projection":
                if self.projection_board is not None:
                    self.projection_board.update(self.piece, clear=clear, is_active=is_active)
            case "shadow":
                self._update_shadow()

    def _update_shadow(self) -> None:
        """Update the shadow piece on the main board showing where the piece will land."""
        if self.piece is None or self.state != GameState.running:
            return

        if self._shadow_id is not None:
            self.board.delete(self._shadow_id)
            self._shadow_id = None

        for coord in self._shadow_coords:
            self.board.delete(f"shadow_{coord[0]}_{coord[1]}")
        self._shadow_coords = []

        piece_copy = copy.deepcopy(self.piece)
        drop_distance = 0
        while piece_copy.translate([0, -1], self.board._game_grid):
            drop_distance -= 1

        if drop_distance == 0:
            return

        self._shadow_coords = [[c[0], c[1] + drop_distance] for c in self.piece.coords]
        for coord in self._shadow_coords:
            u = self.board._transform_coord(coord)
            scale = self._config.board.scale
            x1 = scale * u[0] + self.board.border_width
            y1 = scale * u[1] + self.board.border_width
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
                tags=(f"shadow_{coord[0]}_{coord[1]}",),
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
        is active.  This is the single canonical lock implementation used
        by both :class:`HumanInputHandler` and :class:`AgentInputHandler`.
        """
        if self.state != GameState.running or self.piece is None:
            return
        piece_type = self.piece.name
        self._update_piece_on_board(clear=True)
        self._update_piece_on_board(is_active=False)
        match self._config.shadow:
            case "shadow":
                if hasattr(self, "_shadow_coords"):
                    for coord in getattr(self, "_shadow_coords", []):
                        self.board.delete(f"shadow_{coord[0]}_{coord[1]}")
                    self._shadow_coords = []
        self._sync_logger_time()
        self.event_logger.log(EventType.piece_lock, piece_type=piece_type)
        if self.board.select_full_rows():
            self._schedule(GameEvent.remove)
        self.add_piece()

    def get_observation(self) -> "GameObservation":
        """Get current game state for observation (AI agent or human observer).

        :returns: GameObservation with current board state, pieces, and stats.
        """
        # Build row-major board: board_state[y][x], y=0 is bottom row
        width, height = self.board.width, self.board.height
        board_state: list[list[str | None]] = [[None] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                if self.board._game_grid[x, y].type:
                    board_state[y][x] = self.board._game_grid[x, y].type

        elapsed_secs = float(self.time_elapsed.get(as_seconds=True) or 0.0)
        current_piece: Tetromino | None = self.piece if isinstance(self.piece, Tetromino) else None
        return GameObservation(
            board=board_state,
            current_piece=current_piece.name if current_piece else None,
            current_piece_coords=current_piece.coords if current_piece else [],
            current_piece_state=current_piece.rotation_state if current_piece else 0,
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
        self.board.clear()
        if self.projection_board is not None:
            self.projection_board.clear()
        if hasattr(self, "_shadow_coords"):
            for coord in getattr(self, "_shadow_coords", []):
                self.board.delete(f"shadow_{coord[0]}_{coord[1]}")
            self._shadow_coords = []
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

        Applies the generator :math:`-e_y` (one step downward) to the active
        piece.  If the piece cannot descend (it is blocked by the floor or the
        stack), it is **locked** (written to the occupancy grid) and the next
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
        if not self.move_piece(Transformation(EigenTransformation.vertical, 1)):
            self._update_piece_on_board(clear=True)
            self._update_piece_on_board(is_active=False)
            if self.board.select_full_rows():
                self._schedule(GameEvent.remove)
            self.add_piece()
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
        the game transitions to :attr:`GameState.over`.  In the planned
        refactor this uses :meth:`Polyomino.at` (a no-check translate) instead
        of :meth:`Polyomino.translate` with a grid check.

        The piece is **not** written to the occupancy grid at spawn; it lives
        only in ``self.piece`` until :meth:`lock_piece` commits it.
        """

        def get_next_piece() -> None:
            """Select and preview a new random piece."""
            self.preview_board.clear()
            self.next_piece = copy.deepcopy(random.choice(tetrominoes))
            self.next_piece.translate(
                [
                    self.preview_board.width // 2,
                    self.preview_board.height // 2,
                ],
                self.preview_board._game_grid,
            )
            self.preview_board.update(self.next_piece)

        if not self.next_piece:
            get_next_piece()
        piece = copy.deepcopy(self.next_piece)
        assert piece is not None
        self.used[piece.name].set(self.used[piece.name].get() + 1)
        self.used["total"].set(self.used["total"].get() + 1)
        get_next_piece()

        if piece.translate(
            [
                self.board.width // 2 - self.preview_board.width // 2,
                self.board.height - 1 - piece.max(Dimension.Y),
            ],
            self.board._game_grid,
        ):
            match self._config.shadow:
                case "projection":
                    if self.projection_board is not None:
                        self.projection_board.clear()
                case "shadow":
                    if hasattr(self, "_shadow_coords"):
                        for coord in getattr(self, "_shadow_coords", []):
                            self.board.delete(f"shadow_{coord[0]}_{coord[1]}")
                        self._shadow_coords = []
            self.piece = piece
            self._sync_logger_time()
            self.event_logger.log(EventType.piece_spawn, piece_type=piece.name)
            self._update_piece_on_board()
        else:
            self.piece = piece
            self._sync_logger_time()
            self.event_logger.log(EventType.game_over, reason="cannot spawn")
            self.event_logger.stop(self._get_stats())
            self.event_logger.save()
            self.set_state(GameState.over)

    def move_piece(self, transformation: Transformation) -> bool:
        """Apply a transformation to the active piece.

        This is the **single canonical entry point for all input actions**
        (human or agent).  It enforces the state guard:

        * Returns ``False`` immediately if the game is not
          :attr:`GameState.running` or no piece is active.

        On a successful move the active piece is erased from the board,
        the transformation applied, and the piece redrawn at its new
        position.  Events are logged for rotation, horizontal, and vertical
        moves.

        Rotation is routed through :meth:`Tetromino.srs_rotate` (which
        uses the SRS kick tables); all other transformations are routed
        through :meth:`Polyomino.transform`.  In the planned refactor both
        paths are unified in :meth:`Polyomino.rotate` using functional
        boundary kicks.

        :param transformation: The :class:`EigenTransformation` to apply,
            wrapped in a :class:`Transformation`.
        :returns: ``True`` if the piece moved successfully.
        """
        if self.state != GameState.running or self.piece is None:
            return False
        self._update_piece_on_board(clear=True)

        if transformation.eigentransformation == EigenTransformation.rotation:
            piece = self.piece
            assert isinstance(piece, Tetromino)
            result = piece.srs_rotate(transformation.multiple, self.board._game_grid)
        else:
            result = self.piece.transform(transformation, self.board._game_grid)

        self._update_piece_on_board()
        if result and self.piece is not None:
            self._sync_logger_time()
            match transformation.eigentransformation:
                case EigenTransformation.rotation:
                    direction_str = "CW" if transformation.multiple > 0 else "CCW"
                    self.event_logger.log(EventType.piece_rotate, piece_type=self.piece.name, direction=direction_str)
                case EigenTransformation.horizontal:
                    dir_str = "right" if transformation.multiple > 0 else "left"
                    self.event_logger.log(EventType.piece_move, piece_type=self.piece.name, direction=dir_str)
                case EigenTransformation.vertical:
                    self.event_logger.log(EventType.piece_move, piece_type=self.piece.name, direction="down")
        return result

    def remove_full_rows(self) -> None:
        """Remove full rows, shift overburden, and update statistics.

        Delegates to :meth:`Board.remove_full_rows` for the grid operation,
        then updates the removed-rows counters and logs a
        :attr:`~.EventType.row_clear` event.
        """
        full_count = self.board.remove_full_rows()
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


class Preferences(tk.Frame):
    """Dialog for editing game preferences."""

    def __init__(self) -> None:
        """Initialize the preferences dialog.

        :raises NotImplementedError: Preferences dialog is not yet implemented.
        """
        raise NotImplementedError("Cannot create preferences dialog")
