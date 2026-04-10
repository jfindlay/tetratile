# !/usr/bin/env python3
"""Tetromino tessellation game.

A tetromino puzzle game where players stack falling tetromino pieces
to form complete rows on the game board.

:attr _VERSION: The version of the installed package.
:attr tetrominoes: Tuple of all instantiated tetromino objects for the game.
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
    """Map cardinal cartesian products to integers.

    :attr D1: One-dimensional.
    :attr D2: Two-dimensional (for polyominoes).
    :attr D3: Three-dimensional (for polycubes).
    """

    D1 = 1
    D2 = 2
    D3 = 3


class EigenTransformation(enum.IntEnum):
    """Allowed eigentransformations of polyominos in the 2D lattice.

    :attr identity: No transformation.
    :attr rotation: Rotation by ±π/2.
    :attr horizontal: Translation left or right.
    :attr vertical: Translation up or down.
    :attr min: Translate to left edge.
    :attr max: Translate to right edge.
    :attr bottom: Translate to bottom.
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
    """A polyomino transformation as an eigentransformation scaled by an integer multiple.

    :attr eigentransformation: The type of transformation to apply.
    :attr multiple: The number of times to apply the transformation.
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
    """Game state observation for AI agents and human observers.

    This dataclass provides a read-only snapshot of the current game state,
    usable by both AI agents for decision-making and by human observers
    (including other frontends) for display purposes.

    :attr board: 2D array of cell types (None for empty, tetromino name for occupied).
    :attr current_piece: Name of current falling piece (Z, S, l, T, o, L, J).
    :attr current_piece_coords: List of [x, y] coordinates for current piece squares.
    :attr current_piece_state: SRS rotation state (0-3).
    :attr next_piece: Name of next piece to spawn.
    :attr stats: Dictionary of game statistics.
    :attr state: Current game state (running, paused, over).
    :attr elapsed: Elapsed game time as timedelta.
    """

    board: list[list[str | None]]
    current_piece: str | None
    current_piece_coords: list[list[int]]
    current_piece_state: int
    next_piece: str | None
    stats: dict
    state: GameState
    elapsed: dt.timedelta


@dataclass
class Colors:
    """Store color information used for displaying polyominos in the game.

    :attr normal: The primary color.
    :attr light: The lighter color variant.
    :attr dark: The darker color variant.
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
    """An elemental unit of the grid.

    :attr colors: Colors for rendering the square.
    :attr id: Tkinter canvas item ID.
    :attr is_active: Whether the square is part of the active piece.
    :attr type: Name of the tetromino occupying this square.
    """

    colors: Colors | None = None
    id: int | None = None
    is_active: bool | None = None
    type: str | None = None


class Grid:
    """The rectangular region of squares that comprises the game state.

    The squares map to integer coordinates in the first quadrant of the
    Cartesian plane. Each square is represented by the point at its upper
    right corner, with the origin at the upper right corner of the
    lower left square.

    :attr width: Number of columns in the grid.
    :attr height: Number of rows in the grid.
    """

    def __init__(self, width: int, height: int) -> None:
        """Initialize the game grid.

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
        """Validate whether the coordinates are all contained in the grid.

        :param coords: List of coordinates to validate.
        :returns: True if all coordinates are valid and squares are unoccupied.
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
        """Display grid state to stdout."""
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
    r"""Define a polyomino by coordinates to each of its squares.

    Provides valid transformations for a polyomino on the
    :math:`\mathbb Z^{\mathrm dim}` lattice.

    :attr dim: Dimensionality of the polyomino.
    :attr deg: Degree (number of squares).
    :attr colors: Colors for rendering.
    :attr coords: Coordinates to the upper right corner of each square.
    :attr o: Proper origin, computed from coordinates.
    :attr name: Name identifier.
    :attr full: Whether the piece represents a full row.
    :attr full_below_count: Number of full rows below this piece.
    """

    dim: Dimension
    colors: Colors
    coords: list[list[int]]

    o: list[D] = field(init=False)
    name: str = ""
    full: bool = field(default=False, init=False)
    full_below_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        """Compute proper origin from coordinates."""
        self.o = [D(sum([v[d] for v in self.coords]) / len(self.coords)) for d in range(self.dim)]

    def min(self, dim: Dimension | None = None) -> int:
        """Return the minimum coordinate of the polyomino in the given dimension.

        :param dim: The dimension to check. Defaults to self.dim.
        :returns: Minimum coordinate value.
        """
        d = dim if dim is not None else self.dim
        return min([c[d.value - 1] for c in self.coords])

    def max(self, dim: Dimension | None = None) -> int:
        """Return the maximum coordinate of the polyomino in the given dimension.

        :param dim: The dimension to check. Defaults to self.dim.
        :returns: Maximum coordinate value.
        """
        d = dim if dim is not None else self.dim
        return max([c[d.value - 1] for c in self.coords])

    def transform(self, t: Transformation, grid: Grid) -> bool:
        """Transform the polyomino in the given grid coordinates.

        :param t: The transformation to apply.
        :param grid: The grid to transform within.
        :returns: True if transformation was successful.
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

    def rotate(self, r: Transformation, grid: Grid) -> bool:
        """Rotate the polyomino about its proper origin.

        :param r: Rotation transformation with multiple indicating direction.
        :param grid: The grid to rotate within.
        :returns: True if rotation was successful and polyomino fits in grid.
        """
        coords = [[0 for d in range(self.dim)] for _ in self.coords]
        for i, _ in enumerate(self.coords):
            coords[i][0] = int(-r.multiple * (self.coords[i][1] - self.o[1]) + self.o[0])
            coords[i][1] = int(r.multiple * (self.coords[i][0] - self.o[0]) + self.o[1])
        if grid.check(coords):
            self.coords = coords
            return True
        return False

    def translate(self, t: Transformation | list[int], grid: Grid) -> bool:
        """Translate the polyomino within the grid.

        :param t: The translation vector or transformation.
        :param grid: The grid to translate within.
        :returns: True if translation was successful.
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
        """Get translation vector (dx, dy) and whether to use single step or iterate.

        :param t: The translation specification.
        :returns: (dx, dy, single_step) where single_step indicates whether to
            move once or iterate until blocked.
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
    """Immutable data for a tetromino type.

    :attr name: Single-letter identifier.
    :attr coords: Coordinates to each square.
    :attr normal: Primary color hex code.
    :attr light: Light color hex code.
    :attr dark: Dark color hex code.
    """

    name: str
    coords: tuple[tuple[D, D], ...]
    normal: str
    light: str
    dark: str


class TetrominoType(enum.Enum):
    """Enumeration of all tetromino types.

    :attr Z: Z-shaped tetromino.
    :attr S: S-shaped tetromino.
    :attr l: l-shaped tetromino.
    :attr T: T-shaped tetromino.
    :attr o: o-shaped tetromino.
    :attr L: L-shaped tetromino.
    :attr J: J-shaped tetromino.
    """

    Z = TetrominoData(
        name="Z",
        coords=((D("-1"), D("0")), (D("0"), D("0")), (D("0"), D("-1")), (D("1"), D("-1"))),
        normal="#CC6666",
        light="#F89FAB",
        dark="#803C3B",
    )
    S = TetrominoData(
        name="S",
        coords=((D("0"), D("0")), (D("1"), D("0")), (D("0"), D("-1")), (D("-1"), D("-1"))),
        normal="#66CC66",
        light="#79FC79",
        dark="#3B803B",
    )
    l = TetrominoData(
        name="l",
        coords=((D("-2"), D("0")), (D("-1"), D("0")), (D("0"), D("0")), (D("1"), D("0"))),
        normal="#6666CC",
        light="#7979FC",
        dark="#3B3B80",
    )  # noqa: E741
    T = TetrominoData(
        name="T",
        coords=((D("0"), D("0")), (D("-1"), D("1")), (D("0"), D("1")), (D("1"), D("1"))),
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
        coords=((D("-1"), D("1")), (D("-1"), D("0")), (D("-1"), D("-1")), (D("0"), D("-1"))),
        normal="#66CCCC",
        light="#79FCFC",
        dark="#3B8080",
    )
    J = TetrominoData(
        name="J",
        coords=((D("0"), D("1")), (D("0"), D("0")), (D("0"), D("-1")), (D("-1"), D("-1"))),
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

SRS_CENTERS: dict[str, tuple[D, D]] = {
    "Z": (D(0), D(0)),
    "S": (D(0), D(0)),
    "l": (D("0.5"), D(0)),
    "T": (D(0), D(0)),
    "o": (D(0), D(0)),
    "L": (D("-0.5"), D(0)),
    "J": (D("-0.5"), D(0)),
}


def used_keys() -> list[str]:
    """Return list of keys for the used dictionary.

    :returns: ["total", "Z", "S", "l", "T", "o", "L", "J"].
    """
    return ["total"] + [t.value.name for t in TetrominoType]


class Tetromino(Polyomino):
    """Base class for tetrominoes.

    :attr dim: Always Dimension.D2 for tetrominoes.
    :attr name: Single-letter identifier.
    :attr rotation_state: SRS rotation state (0-3).
    """

    dim: Dimension = Dimension.D2
    name: str = ""
    rotation_state: int = 0

    def __init__(self, data: TetrominoData | None = None) -> None:
        """Initialize a tetromino.

        :param data: Data to initialize from. If None, creates empty tetromino.
        """
        self.coords: list[list[int]] = []
        self.colors: Colors = Colors("", "", "")
        self.rotation_state = 0
        if data is not None:
            self.name = data.name
            self.colors = Colors(data.normal, data.light, data.dark)
            self.coords = [[int(v[0]), int(v[1])] for v in data.coords]
            self.o = [SRS_CENTERS.get(data.name, (D(0), D(0)))[0], SRS_CENTERS.get(data.name, (D(0), D(0)))[1]]
        self.dim = Dimension.D2

    def _get_kick_table(self) -> dict[tuple[int, int], list[tuple[int, int]]]:
        """Get the SRS kick table for this tetromino.

        :returns: Kick table for JLSTZ, I, or O piece.
        """
        if self.name == "o":
            return SRS_KICK_O
        elif self.name == "l":
            return SRS_KICK_I
        return SRS_KICK_JLSTZ

    def _rotate_coords(self, direction: int) -> list[list[int]]:
        """Calculate rotated coordinates about the origin.

        :param direction: Rotation direction (+1=CW, -1=CCW in screen coords).
        :returns: New coordinates after rotation.
        """
        coords = [[0 for _ in range(self.dim)] for _ in self.coords]
        for i, _ in enumerate(self.coords):
            coords[i][0] = int(direction * (self.coords[i][1] - self.o[1]) + self.o[0])
            coords[i][1] = int(-direction * (self.coords[i][0] - self.o[0]) + self.o[1])
        return coords

    def srs_rotate(self, direction: int, grid: Grid) -> bool:
        """Rotate using SRS with full kick tables.

        :param direction: Rotation direction (+1=CW, -1=CCW in screen coords).
        :param grid: The grid to rotate within.
        :returns: True if rotation was successful.
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
    """Display polyomino block grid on a Tkinter canvas.

    :attr width: Grid width in squares.
    :attr height: Grid height in squares.
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
        """Transform tetratile coordinates to Tkinter coordinates.

        Tetratile uses a Cartesian plane with origin at lower left,
        while Tkinter uses origin at upper left.

        :param v: Tetratile coordinates.
        :returns: Tkinter coordinates.
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
        """Mark full rows with full row colors prior to removing them.

        :returns: True if any full rows were found.
        """
        has_full_rows = False
        for y in range(self.height):
            row_coords = [
                [x, y] for x in range(self.width) if self._game_grid[x, y].type and not self._game_grid[x, y].is_active
            ]
            if len(row_coords) == self.width:
                has_full_rows = True
                row = Polyomino(
                    dim=Dimension.D2,
                    colors=self.full_row_colors,
                    coords=row_coords,
                    name="row",
                )
                row.full = True
                self.update(row, clear=True)
                self.update(row)
        return has_full_rows

    def _get_rows(self) -> tuple[int, list[Polyomino]]:
        """Gather all full and partial rows.

        :returns: (full_count, rows) where full_count is the number of full rows
            and rows is a list of row polyominoes.
        """
        rows: list[Polyomino] = []
        full_count = 0
        for y in range(self.height):
            row_coords = [
                [x, y] for x in range(self.width) if self._game_grid[x, y].type and not self._game_grid[x, y].is_active
            ]
            if len(row_coords):
                row = Polyomino(
                    dim=Dimension.D2,
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
        """Remove full rows.

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

        # Shift remaining cells down (bottom to top to avoid overwriting)
        for y in range(self.height - 1, -1, -1):
            for x in range(self.width):
                if self._game_grid[x, y].type and not self._game_grid[x, y].is_active:
                    rows_below = sum(1 for fy in full_row_indices if fy > y)
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
    """Main game window.

    :attr board: The main game board.
    :attr preview_board: The preview board showing next piece.
    :attr projection_board: The projection/shadow board.
    :attr state: Current game state.
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
        self._verbose_output: bool = False

        self.add_piece()
        self.iterate_id = self._schedule(GameEvent.iterate)

    def _schedule(self, game_event: GameEvent) -> str:
        """Schedule an asynchronous event.

        :param game_event: The type of event to schedule.
        :returns: Tkinter after callback ID.
        """
        if game_event == GameEvent.iterate:
            action = self.iterate
            rate = self.rate.get(raw=True)
        elif game_event == GameEvent.remove:
            action = self.remove_full_rows
            rate = self.rate.get(raw=True) * self._config.remove_freq

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

    # Internal action methods - called by both human and agent handlers
    def _do_move_left(self) -> bool:
        """Internal implementation for move left.

        :returns: True if move was successful.
        """
        return self.move_piece(Transformation(EigenTransformation.horizontal, -1))

    def _do_move_right(self) -> bool:
        """Internal implementation for move right.

        :returns: True if move was successful.
        """
        return self.move_piece(Transformation(EigenTransformation.horizontal, 1))

    def _do_rotate_cw(self) -> bool:
        """Internal implementation for clockwise rotation.

        :returns: True if rotation was successful.
        """
        return self.move_piece(Transformation(EigenTransformation.rotation, 1))

    def _do_rotate_ccw(self) -> bool:
        """Internal implementation for counter-clockwise rotation.

        :returns: True if rotation was successful.
        """
        return self.move_piece(Transformation(EigenTransformation.rotation, -1))

    def _do_soft_drop(self) -> bool:
        """Internal implementation for soft drop (one step down).

        :returns: True if move was successful.
        """
        return self.move_piece(Transformation(EigenTransformation.vertical, 1))

    def _do_hard_drop(self) -> None:
        """Internal implementation for hard drop."""
        while self.move_piece(Transformation(EigenTransformation.vertical, 1)):
            pass

    def _do_move_left_max(self) -> None:
        """Internal implementation for move to left edge."""
        while self.move_piece(Transformation(EigenTransformation.horizontal, -1)):
            pass

    def _do_move_right_max(self) -> None:
        """Internal implementation for move to right edge."""
        while self.move_piece(Transformation(EigenTransformation.horizontal, 1)):
            pass

    def _do_toggle_pause(self) -> None:
        """Internal implementation for toggle pause."""
        self.toggle_pause(None)

    def _do_lock_piece(self) -> None:
        """Internal implementation for lock piece without dropping."""
        if self.piece is not None:
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

    # Input handler management
    def set_input_handler(self, handler: "InputHandler") -> None:
        """Set the input handler for game control.

        :param handler: InputHandler instance (HumanInputHandler or AgentInputHandler).
        """
        self._input_handler = handler

    def get_input_handler(self) -> "InputHandler":
        """Get the current input handler.

        :returns: Current InputHandler instance.
        """
        return self._input_handler

    # Convenience methods for direct control (REPL mode)
    def move_left(self) -> bool:
        """Move the current piece one step left.

        :returns: True if move was successful.
        """
        return self._do_move_left()

    def move_right(self) -> bool:
        """Move the current piece one step right.

        :returns: True if move was successful.
        """
        return self._do_move_right()

    def rotate_cw(self) -> bool:
        """Rotate the current piece clockwise.

        :returns: True if rotation was successful.
        """
        return self._do_rotate_cw()

    def rotate_ccw(self) -> bool:
        """Rotate the current piece counter-clockwise.

        :returns: True if rotation was successful.
        """
        return self._do_rotate_ccw()

    def soft_drop(self) -> bool:
        """Move the current piece one step down (soft drop).

        :returns: True if move was successful.
        """
        return self._do_soft_drop()

    def hard_drop(self) -> None:
        """Drop the current piece to the bottom immediately."""
        self._do_hard_drop()

    def move_left_max(self) -> None:
        """Move the current piece to the left edge (max translation)."""
        self._do_move_left_max()

    def move_right_max(self) -> None:
        """Move the current piece to the right edge (max translation)."""
        self._do_move_right_max()

    def lock_piece(self) -> None:
        """Lock the current piece in place without dropping."""
        self._do_lock_piece()

    def print_board(self) -> None:
        """Print current board state to stdout."""
        self.board._game_grid.print()

    def get_stats(self) -> dict:
        """Get current game statistics.

        :returns: Dictionary with pieces, rows_cleared, rows_by_count, pieces_by_type.
        """
        return self._get_stats()

    def set_verbose_output(self, enabled: bool) -> None:
        """Enable or disable verbose terminal output.

        :param enabled: True to enable verbose output, False to disable.
        """
        self._verbose_output = enabled

    def _print_game_state(self) -> None:
        """Print current game state to stdout (for verbose/agent mode)."""
        stats = self._get_stats()
        elapsed_seconds = self.time_elapsed.get(as_seconds=True) or 0.0

        print("=" * 40)
        print(f"STATE: {self.state}")
        print(f"Piece: {self.piece.name if self.piece else 'None'} (state={self.piece.rotation_state if self.piece else 0})")
        print(f"Next: {self.next_piece.name if self.next_piece else 'None'}")
        print(f"Rows cleared: {self.removed_total.get()}")
        print(f"Pieces: {stats.get('pieces', 0)}")
        print(f"Time: {elapsed_seconds:.1f}s")
        print()
        self.board._game_grid.print()
        print("=" * 40)
        print()

    def get_observation(self) -> "GameObservation":
        """Get current game state for observation (AI agent or human observer).

        :returns: GameObservation with current board state, pieces, and stats.
        """
        # Build board state as 2D array
        board_state: list[list[str | None]] = [[None for _ in range(self.board.height)] for _ in range(self.board.width)]
        for y in range(self.board.height):
            for x in range(self.board.width):
                if self.board._game_grid[x, y].type:
                    board_state[x][y] = self.board._game_grid[x, y].type

        return GameObservation(
            board=board_state,
            current_piece=self.piece.name if self.piece else None,
            current_piece_coords=self.piece.coords if self.piece else [],
            current_piece_state=self.piece.rotation_state if self.piece else 0,
            next_piece=self.next_piece.name if self.next_piece else None,
            stats=self._get_stats(),
            state=self.state,
            elapsed=self.time_elapsed.get() or dt.timedelta(),
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

    def setup_events(self) -> None:
        """Respond to inputs and other game conditions.

        Binds keyboard events to their handler methods.
        """
        for name, key in self._config.keys.model_dump().items():
            self.master.bind(key, getattr(self, name))

    def pause(self, event: tk.Event) -> None:
        """Toggle pause state.

        :param event: Tkinter event (unused).
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

    def left(self, event: tk.Event) -> None:
        """Translate the current piece one step left.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            self.move_piece(Transformation(EigenTransformation.horizontal, -1))

    def right(self, event: tk.Event) -> None:
        """Translate the current piece one step right.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            self.move_piece(Transformation(EigenTransformation.horizontal, 1))

    def down(self, event: tk.Event) -> None:
        """Translate the current piece one step down.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            self.move_piece(Transformation(EigenTransformation.vertical, 1))

    def left_side(self, event: tk.Event) -> None:
        """Translate the current piece to the left edge.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            while self.move_piece(Transformation(EigenTransformation.horizontal, -1)):
                pass

    def right_side(self, event: tk.Event) -> None:
        """Translate the current piece to the right edge.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            while self.move_piece(Transformation(EigenTransformation.horizontal, 1)):
                pass

    def rotate_left(self, event: tk.Event) -> None:
        """Rotate the current piece counterclockwise.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            self.move_piece(Transformation(EigenTransformation.rotation, -1))

    def rotate_right(self, event: tk.Event) -> None:
        """Rotate the current piece clockwise.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            self.move_piece(Transformation(EigenTransformation.rotation, 1))

    def drop(self, event: tk.Event) -> None:
        """Drop the current piece to the bottom.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running:
            while self.move_piece(Transformation(EigenTransformation.vertical, 1)):
                pass

    def lock(self, event: tk.Event) -> None:
        """Lock the current piece in place without dropping.

        :param event: Tkinter event (unused).
        """
        if self.state == GameState.running and self.piece is not None:
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
        """Process one game cycle.

        Moves the active piece down one row if possible,
        handles row removal, and schedules the next iteration.
        """
        if self.state == GameState.paused:
            return
        if not self.move_piece(Transformation(EigenTransformation.vertical, 1)):
            self._update_piece_on_board(clear=True)
            self._update_piece_on_board(is_active=False)
            if self.board.select_full_rows():
                self._schedule(GameEvent.remove)
            self.add_piece()
        if self._verbose_output:
            self._print_game_state()
        if self.state == GameState.running:
            self._update_rates()
            self.iterate_id = self._schedule(GameEvent.iterate)
        elif self.state == GameState.over:
            self.restart_button = tk.Button(self.marquee, text="restart", command=self.restart)
            self.restart_button.pack(side="top")

    def add_piece(self) -> None:
        """Add a tetromino to the top center of the board."""

        def get_next_piece() -> None:
            """Get a new piece for preview."""
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
                self.board.height - 1 - piece.max(Dimension.D2),
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
        """Move current piece according to the transformation requested.

        :param transformation: The transformation to apply.
        :returns: True if the move was successful.
        """
        assert self.piece is not None
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
        """Remove full rows and move partial rows down into the vacancies."""
        full_count = self.board.remove_full_rows()
        self._update_removed(full_count)
        if full_count > 0:
            self._sync_logger_time()
            self.event_logger.log(EventType.row_clear, count=full_count)

    def _get_stats(self) -> dict[str, int | list[int] | dict[str, int]]:
        """Get current game statistics.

        :returns: Dictionary of game statistics.
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
