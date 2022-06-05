#!/usr/bin/env python3

import copy
import datetime
import enum
import importlib
import math
import random
import sys
import tkinter as tk
import typing
from dataclasses import dataclass, field
from decimal import Decimal as D

_VERSION: str = importlib.metadata.version("tetratile")


class Dimension(enum.IntEnum):
    """
    Map cardinal cartesian products to integers.
    """

    D1 = 1
    D2 = 2
    D3 = 3  # For polycubes


class Degree(enum.IntEnum):
    """
    Map polyomino enumerators to cardinal integers.
    """

    monimo = enum.auto()
    domino = enum.auto()
    tromino = enum.auto()
    tetromino = enum.auto()
    pentomino = enum.auto()


class EigenTransformation(enum.IntEnum):
    """
    Base class for allowed eigentransformations of polyominos in the 2D lattice.
    """

    identity = 0
    rotation = 1  # Rotation: ±π/2 (counter)clockwise
    horizontal = 2  # Translation: ±1 left or right
    vertical = 3  # Translation: ±1 up or down


@dataclass
class Transformation:
    """
    Represent a polyomino transformation as an eigentransformation scaled by an integer multiple.
    """

    eigentransformation: EigenTransformation
    multiple: int = 1  # Typically game controls only increment by one unit


class GameState(enum.StrEnum):
    """
    Enumerate game states.
    """

    running = ""
    paused = "paused"
    over = "game over"


class EventType(enum.IntEnum):
    """
    Enumerate available asynchronous events.
    """

    iterate = enum.auto()
    remove = enum.auto()


@dataclass
class Colors:
    """
    Store color information used for displaying polyominos in the game.
    """

    normal: str
    light: str
    dark: str


@dataclass
class Square:
    """
    An elemental unit of the grid.

    colors: Color scheme.
    id: Tkinter item id.
    """

    colors: Colors | None = None
    id: int | None = None
    is_active: bool | None = None


class Grid:
    """
    The rectangular region of squares that comprises the game state.  The squares map to the integer coordinates in the first
    quadrant of the cartesian plane such that each square is represented by the (integral) point at its upper right corner.  The
    origin corresponds to the upper right corner of the lower left square of the grid.
    """

    def __init__(self, width: int, height: int):
        """
        Setup game grid
        """
        # Initialize internal grid
        self._grid = [[Square() for i in range(height)] for j in range(width)]
        self.width = width
        self.height = height

    def __check_nonnegative(self, v: list[int]) -> None:
        """
        Disallow accessing squares by negative coordinates.  Python allows accessing elements of iterables by one modulus below
        the residual representation of the array, but we disallow it for simplicity.
        """
        if 0 > min(v):
            raise IndexError("grid coordinates must be nonnegative")

    def __getitem__(self, v: list[int]) -> Square:
        """
        Retrieve the square at coordinates `v` from the origin.
        """
        self.__check_nonnegative(v)
        return self._grid[v[0]][v[1]]

    def __setitem__(self, v: list[int], square: Square) -> None:
        """
        Update the square at coordinates `v` from the origin.
        """
        self.__check_nonnegative(v)
        self._grid[v[0]][v[1]].update(type, id)

    def __iter__(self) -> typing.Generator[list[int], None, None]:
        """
        Iterate over the grid squares.
        """
        for x in range(self.width):
            for y in range(self.height):
                yield [x, y]

    def check(self, coords: list[list[int]]) -> bool:
        """
        Validate whether the coordinates are all contained in the grid.
        """
        for v in coords:
            # Check that v points to the interior of the grid
            try:
                self[v]
            except IndexError:
                return False
            # Check that v points to an unoccupied square
            if self[v]["type"] is not None:
                return False
        return True

    def print(self) -> None:
        """
        Display grid state.
        """
        # Convert columns to rows
        rows: dict[int, dict[int, str]] = {}
        for v in self:
            square = self[v]
            if v[1] not in rows:
                rows[v[1]] = {}
            rows[v[1]][v[0]] = " " if square["type"] is None else square["type"]

        # Print rows with formatting
        digits = len(str(self.height))
        row_fmt = "{{:0{}}}".format(digits)
        print(digits * " " + "+" + 2 * len(self._grid) * "-" + "+")
        for i in reversed(rows.keys()):
            row_image = "".join([2 * rows[i][j] if len(rows[i][j]) == 1 else rows[i][j][:2] for j in sorted(rows[i].keys())])
            print(row_fmt.format(self.height - i - 1) + "|" + row_image + "|")
        print(digits * " " + "+" + 2 * len(self._grid) * "-" + "+")


@dataclass
class Polyomino:
    r"""
    Define a polyomino by coordinates to the upper right corner of each of its squares and provide the valid transformations for
    a polyomino on the $\mathbb Z^{\mathrm dim}$ lattice.
    """

    dim: Dimension
    deg: Degree
    colors: Colors

    # Compute the polyomino proper origin from the given coordinates.  To reduce the distance between the polyomino proper
    # origin and the polyomino center of mass, coordinates can take integral and half-integral values.  Half integer quanta
    # offer enough resolution to enable desired rotational symmetries.
    coords: list[list[int]]
    o: list[D] = field(init=False)

    def __post_init__(self, dim: Dimension, deg: Degree, colors: Colors, coords: list[list[int]]):
        """
        Setup polyomino proper origin relative to its coordinates.
        """
        self.o = [D(sum([v[d] for v in coords]) / self.deg) for d in range(self.dim)]

    def min(self) -> int:
        """
        Return the minimum coordinate of the polyomino in the given dimension.
        """
        return min([c[self.dim] for c in self.coords])

    def max(self) -> int:
        """
        Return the maximum coordinate of the polyomino in the given dimension.
        """
        return max([c[self.dim] for c in self.coords])

    def transform(self, t: Transformation, grid: Grid) -> bool:
        """
        Transform the tetromino in the given grid coordinates.
        """
        match t.eigentransformation:
            case EigenTransformation.identity:
                return True
            case EigenTransformation.rotation:
                return self.rotate(t, grid)
            case EigenTransformation.horizontal | EigenTransformation.vertical:
                return self.translate(t, grid)

    def rotate(self, r: Transformation, grid: Grid) -> bool:
        """
        Rotate polyomino clockwise or counterclockwise in increments of ±π/2 about its proper origin by the factor provided if
        the resulting transformation is contained within the grid and places the polyomino on unoccupied squares.
        """
        # Prepare new coordinates and rotation tensor
        coords = [[0 for d in range(self.dim)] for i in range(self.deg)]
        # TODO: The remainder of this function is 2D
        # Apply rotation "vector" in the angular "direction" as a rotation tensor in the grid coords
        for i in range(self.deg):
            coords[i][0] = int(-r.multiple * (self.coords[i][1] - self.o[1]) + self.o[0])
            coords[i][1] = int(r.multiple * (self.coords[i][0] - self.o[0]) + self.o[1])
        if grid.check(coords):
            self.coords = coords
            return True
        return False

    def translate(self, t: Transformation, grid: Grid) -> bool:
        """
        Translate polyomino by the vector t if the resulting transformation places the polyomino within the grid and on
        unoccupied squares.
        """
        # TODO: Most of this function is 2D
        # Define w as explicit coordinates in the grid reference frame
        w = translation(v) if isinstance(v, Translation) else v
        # Define unit form of w
        magnitude = int(math.sqrt(w[0] ** 2 + w[1] ** 2)) or 1  # Prevent zero division
        # Not really a unit in the dir of w, but a projection onto the grid
        unit = [
            math.ceil(w[0] / magnitude),
            math.ceil(w[1] / magnitude),
        ]

        # Prepare new coordinates and new proper origin in the grid frame
        coords = [[0 for d in range(self.dim)] for i in range(self.deg)]
        o = [0 for d in range(self.dim)]

        # Incrementally translate upto translation magnitude
        success = False
        u = unit
        if u == [0 for d in range(self.dim)]:
            return success
        while True:
            for i in range(self.deg):
                coords[i][0] = self.coords[i][0] + u[0]
                coords[i][1] = self.coords[i][1] + u[1]
                o = [self.o[0] + u[0], self.o[1] + u[1]]
            if grid.check(coords):
                self.coords = [[coord[0], coord[1]] for coord in coords]
                self.o = [o[0], o[1]]
                success = True
                if not incremental:
                    return success
            else:
                return success


@dataclass
class Tetromino(Polyomino):
    """ """

    dim: Dimension = Dimension.D2
    deg: Degree = Degree.tetromino


class Tetrominoes:
    """
    Collection of all Tetromino types.
    """

    class Z(Tetromino):
        def __post_init__(self):
            """
            Instantiate a tetromino from the more generic Polyomino class.
            """
            self.coords = [[-2, 0], [-1, 0], [-1, -1], [0, -1]]
            self.colors = Colors("#CC6666", "#F89FAB", "#803C3B")

    class S(Tetromino):
        def __post_init__(self):
            """
            Instantiate a tetromino from the more generic Polyomino class.
            """
            self.coords = ([[-1, -1], [0, -1], [0, 0], [1, 0]],)
            self.colors = Colors("#66CC66", "#79FC79", "#3B803B")

    class l(Tetromino):
        def __post_init__(self):
            """
            Instantiate a tetromino from the more generic Polyomino class.
            """
            self.coords = ([[-2, 0], [-1, 0], [0, 0], [1, 0]],)
            self.colors = (Colors("#6666CC", "#7979FC", "#3B3B80"),)

    class T(Tetromino):
        def __post_init__(self):
            """
            Instantiate a tetromino from the more generic Polyomino class.
            """
            self.coords = ([[-1, 0], [0, 0], [0, -1], [1, 0]],)
            self.colors = (Colors("#CCCC66", "#FCFC79", "#80803B"),)

    class o(Tetromino):
        def __post_init__(self):
            """
            Instantiate a tetromino from the more generic Polyomino class.
            """
            self.coords = ([[0, 0], [0, 1], [1, 1], [1, 0]],)
            self.colors = (Colors("#CC66CC", "#FC79FC", "#803B80"),)

    class L(Tetromino):
        def __post_init__(self):
            """
            Instantiate a tetromino from the more generic Polyomino class.
            """
            self.coords = ([[-1, 1], [-1, 0], [-1, -1], [0, -1]],)
            self.colors = (Colors("#66CCCC", "#79FCFC", "#3B8080"),)

    class J(Tetromino):
        def __post_init__(self):
            """
            Instantiate a tetromino from the more generic Polyomino class.
            """
            self.coords = ([[0, 1], [0, 0], [0, -1], [-1, -1]],)
            self.colors = (Colors("#DAAA00", "#FCC600", "#806200"),)

    @classmethod
    def __next__(cls) -> Generator[Tetrominoes, None, None]:
        """
        Iterate over tetrominoes.
        """
        yield from (attr for attr in vars(cls).values() if isinstance(attr, type))


class PrecisionVar(tk.StringVar):
    """
    Represent the value at the specified precision while maintaining the actual value at full precision.
    """

    def __init__(self, *args, value: int | float | None = None, precision: int = 2, **kwargs):
        """
        Setup PrecisionVar object.
        """
        self.precision = precision
        self.float_value = self._validate(value if value is not None else 0.0)
        super().__init__(*args, value=self._fmt(), **kwargs)

    def _validate(self, value: float) -> float:
        """
        Validate input value.
        """
        if isinstance(value, (int, float)) and value >= 0:
            return value
        else:
            raise TypeError("value must be a nonnegative number")

    def _fmt(self) -> str:
        """
        Format decimal string representation.
        """
        return "{{:.{}f}}".format(self.precision).format(self.float_value)

    def get(self, raw: bool = False) -> float:
        """
        Get value formatted to specified precision.
        """
        return self.float_value if raw else super().get()

    def set(self, value: float = 0.0) -> None:
        """
        Set value.
        """
        self.float_value = self._validate(value)
        super().set(self._fmt())


class TimerVar(tk.StringVar):
    """
    Timer string widget variable with start/stop capability.
    """

    def __init__(self, *args, value: datetime.timedelta | None = None, **kwargs):
        """
        Setup TimerVar object.
        """
        self.set(value if value is not None else datetime.timedelta())
        super().__init__(*args, value=self._to_str(self.accumulated_elapsed), **kwargs)

    def _to_str(self, value: datetime.timedelta) -> str:
        """
        Convert value timedelta to string without microseconds.
        """
        return str(value)[:7]

    def get(self, as_seconds: bool = False) -> tk.StringVar:
        """
        Get elapsed time as a string or as total seconds.
        """
        computed = datetime.now() - self.active_counting_since + self.accumulated_elapsed
        super().set(
            self._to_str(computed)
        )  # TkInter uses an internal method to get the value into a widget, so we need to update the parent value here
        return computed.total_seconds() if as_seconds else super().get()

    def set(self, value: datetime.timedelta = datetime.timedelta()) -> None:
        """
        Reset the timer with a new value or update the value to the current time.
        """
        self.accumulated_elapsed = value  # Reset active counter
        self.active_counting_since = datetime.timedelta()  # Timestamp of last start/resume

    def start(self) -> None:
        """
        Begin/resume counting.
        """
        if not self.active_counting_since:  # Start action is idempotent
            self.active_counting_since = datetime.now()

    def stop(self) -> None:
        """
        Collect active counting into `accumulated_elapsed` and reset `active_counting_since`.
        """
        if self.active_counting_since:  # Stop action is idempotent
            self.accumulated_elapsed += datetime.now() - self.active_counting_since
            self.active_counting_since = datetime.timedelta()


class Board(tk.Canvas):
    """
    Used to display polyomino block grid.
    """

    @property
    def width(self) -> int:
        return self.grid.width

    @property
    def height(self) -> int:
        return self.grid.height

    def __init__(self, opts: dict[str, typing.Any], parent: tk.Frame, width: int, height: int, is_projection: bool = False):
        """
        Setup board.
        """
        # Setup options
        self.opts = opts
        self.is_projection = is_projection
        self.border_width = self.opts["scale"] // 16
        self.aspect_proportion = 3 if self.is_projection else 1
        self.full_row_colors = Colors("#DDDDDD", "#FFFFFF", "#BBBBBB")
        self.pause_cover_id = 0

        # Setup internal grid
        self.grid = Grid(self.opts, width, height)

        # Setup TK
        super().__init__(
            parent,
            width=self.opts["scale"] * width,
            height=self.opts["scale"] * height // self.aspect_proportion,
        )
        # Setup board widget
        self.create_rectangle(
            0,
            0,
            self.opts["scale"] * width,
            self.opts["scale"] * height,
            fill="black",
            outline="black",
            width=self.border_width,
        )

        if self.opts["debug"]:
            for v in self.grid:
                u = self._transform_coord(v)
                self.create_text(
                    (self.opts["scale"] * u[0], self.opts["scale"] * u[1]),
                    text="{},{}".format(*u),
                    fill="white",
                    font=("Monospace", 5),
                    anchor=tk.NW,
                )

    def _transform_coord(self, v: list[int]) -> list[int]:
        """
        Tetratile treats the game board as the first quadrant of the Cartesian plane with the origin at the lower left corner,
        whereas Tkinter, conventionally, places the origin in the upper left corner, with positive x and y directions pointing
        right and down, respectively.

        This function transforms tetratile coordinates into Tkinter coordinates.
        """
        return [v[0], self.height - 1 - v[1]]

    def _draw_square(self, v: list[int], colors: Colors) -> int:
        """
        Draw or clear a polyomino square on the board at `v`.
        """
        u = self._transform_coord(v)
        u = [self.opts["scale"] * u[0], self.opts["scale"] * u[1]]
        return self.create_rectangle(
            u[0] + self.border_width,
            u[1] + self.border_width,
            u[0] + self.opts["scale"],
            u[1] + self.opts["scale"] // self.aspect_proportion,
            fill=colors["normal"],
            outline=colors["dark"],
            width=self.border_width,
        )

    def update(self, piece: Polyomino, clear: bool = False, is_active: bool = False) -> None:
        """
        Place or clear piece on the board.
        """
        for v in piece.coords:
            u = [v[0], 0] if self.is_projection else v
            square = self.grid[u]
            if clear:
                square.update(
                    {
                        "type": None,
                        "id": self.delete(square["id"]),
                        "colors": {},
                        "is_active": None,
                    }
                )
            else:
                if not square["id"]:
                    colors = piece.colors[v[0]] if piece.name == "row" and not piece.full else piece.colors
                    square.update(
                        {
                            "type": piece.name,
                            "id": self._draw_square(u, colors),
                            "colors": colors,
                            "is_active": is_active,
                        }
                    )

    def select_full_rows(self) -> bool:
        """
        Mark full rows with full row colors prior to removing them.

        Note: There is a low probability race condition that between the time of marking and the time of removal, new rows could
        become filled by the introduction of a new piece, such that they are removed and not marked as the board does not
        persist calculated data, such as which rows are full, by design: this incidental data is stateless and must be
        recalculated whenever it is needed.  The severity of the race condition is asymptotically constant as the rates of each
        independent game thread: marking and removing, adding new pieces, scale proportionally.
        """
        has_full_rows = False
        for y in range(self.height):
            row_coords = [[x, y] for x in range(self.width) if self.grid[x, y]["type"] and not self.grid[x, y]["is_active"]]
            if len(row_coords) == self.width:
                has_full_rows = True
                row = Polyomino(
                    "row",
                    {v[0]: self.grid[v]["colors"] for v in row_coords},
                    row_coords,
                )
                row.full = True
                row.colors = self.full_row_colors
                self.update(row, clear=True)
                self.update(row)
        return has_full_rows

    def _get_rows(self) -> tuple[int, list[Polyomino]]:
        """
        Gather all full and partial rows.
        """
        rows: list[Polyomino] = []
        full_count = 0
        for y in range(self.height):
            row_coords = [[x, y] for x in range(self.width) if self.grid[x, y]["type"] and not self.grid[x, y]["is_active"]]
            if len(row_coords):
                row = Polyomino(
                    "row",
                    {v[0]: self.grid[v]["colors"] for v in row_coords},
                    row_coords,
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
        """
        Remove full rows and move partial rows down into the vacancies; return number of removed rows.
        """
        full_count, rows = self._get_rows()
        for row in rows:
            if row.full:
                self.update(row, clear=True)
            elif row.full_below_count:
                self.update(row, clear=True)
                row.translate([0, -row.full_below_count], self.grid)
                self.update(row)
        return full_count

    def clear(self) -> None:
        """
        Remove all occupied squares from the board.
        """
        full_count, rows = self._get_rows()
        for row in rows:
            self.update(row, clear=True)

    def add_pause_cover(self) -> None:
        """
        Cover the board when game is paused.
        """
        if not self.pause_cover_id:
            self.pause_cover_id = self.create_rectangle(
                0,
                0,
                self.opts["scale"] * (self.width + 1),
                self.opts["scale"] * (self.height + 1),
                fill="black",
                outline="black",
                width=0,
            )

    def remove_pause_cover(self) -> None:
        """
        Uncover the board when game is paused.
        """
        if self.pause_cover_id > 0:
            self.delete(self.pause_cover_id)
            self.pause_cover_id = 0


class TetraTile(tk.Frame):
    """
    Main game window.
    """

    def __init__(self, config: dict[str, typing.Any], master=None):
        """
        Setup game.
        """
        # Setup options
        self.pdeg = 4  # Polyomino degree (hardcoded to tetromino)
        self.opts = config.opts

        # Setup game data and state
        self.removed = {r + 1: tk.IntVar() for r in range(self.pdeg)}
        self.removed["total"] = tk.IntVar()

        self.used = {t.name: tk.IntVar() for t in tetrominoes}
        self.used["total"] = tk.IntVar()
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

        # Setup TK
        super().__init__(master)
        self.master = master
        self.pack()
        self.create_widgets()
        self.setup_events()
        self.add_piece()
        self.iterate_id = self._schedule(EventType.iterate)  # Start the game cycle

    def _schedule(self, event_type: EventType) -> str:
        """
        Schedule an asynchronous event.
        """
        if event_type == EventType.iterate:
            action = self.iterate
            rate = self.rate.get(raw=True)
        elif event_type == EventType.remove:
            action = self.remove_full_rows
            rate = self.rate.get(raw=True) * self.opts["remove_freq"]

        # Convert seconds to milliseconds.  Physical machines will not wait
        # eternally, so limit the callback lifetime by a factor of 1/ε.
        return self.master.after(int(1e3 / (rate + self.opts["epsilon"])), action)

    def _update_removed(self, rows_removed: int) -> None:
        """
        Update the count of rows removed.
        """
        self.removed[rows_removed].set(self.removed[rows_removed].get() + 1)
        self.removed["total"].set(self.removed["total"].get() + rows_removed)

    def _update_rates(self) -> None:
        """
        Update computed rates.
        """
        new_rate = self.opts["initial_rate"] * (
            1 if self.opts["constant"] else math.log(self.removed["total"].get() / 2**4 + 2, 2)
        )
        self.rate.set(max(new_rate, self.opts["min_rate"]))
        self.piece_rate.set(self.used["total"].get() / (self.time_elapsed.get(as_seconds=True) or 1))
        self.row_rate.set(self.removed["total"].get() / (self.time_elapsed.get(as_seconds=True) or 1))

    def _update_piece_on_board(self, clear: bool = False, is_active: bool = True) -> None:
        """
        Place or clear piece and its projection or shadow on the board.
        """
        self.board.update(self.piece, clear=clear, is_active=is_active)
        if self.opts["shadow"] == "projection":
            self.projection_board.update(self.piece, clear=clear, is_active=is_active)

    def create_widgets(self) -> None:
        """
        Pack in game widgets.
        """
        # Game frame
        self.game = tk.Frame(self)
        self.game.pack(side="left")

        self.board = Board(
            self.opts,
            self.game,
            self.opts["board"]["width"],
            self.opts["board"]["height"],
        )
        self.board.pack(side="top")

        if self.opts["shadow"] == "projection":
            self.projection_board = Board(self.opts, self.game, self.opts["board"]["width"], 1, is_projection=True)
            self.projection_board.pack(side="top")

        # Marquee frame
        self.marquee = tk.Frame(self)
        self.marquee.pack(side="right", padx=self.opts["scale"], pady=self.opts["scale"])

        self.preview_frame = tk.LabelFrame(self.marquee, text="preview")
        self.preview_frame.pack(side="top")
        self.preview_board = Board(self.opts, self.preview_frame, self.pdeg, self.pdeg)
        self.preview_board.pack(side="top")

        self.rate_frame = tk.LabelFrame(self.marquee, text="fall rate")
        self.rate_frame.pack(side="top")
        self.rate_display = tk.Label(self.rate_frame, textvariable=self.rate)
        self.rate_display.pack(side="left")
        self.rate_unit = tk.Label(self.rate_frame, text="blocks/sec")
        self.rate_unit.pack(side="left")

        self.piece_rate_frame = tk.LabelFrame(self.marquee, text="piece rate")
        self.piece_rate_frame.pack(side="top")
        self.piece_rate_display = tk.Label(self.piece_rate_frame, textvariable=self.piece_rate)
        self.piece_rate_display.pack(side="left")
        self.piece_rate_unit = tk.Label(self.piece_rate_frame, text="pieces/sec")
        self.piece_rate_unit.pack(side="left")

        self.row_rate_frame = tk.LabelFrame(self.marquee, text="row rate")
        self.row_rate_frame.pack(side="top")
        self.row_rate_display = tk.Label(self.row_rate_frame, textvariable=self.row_rate)
        self.row_rate_display.pack(side="left")
        self.row_rate_unit = tk.Label(self.row_rate_frame, text="rows/sec")
        self.row_rate_unit.pack(side="left")

        self.used_frame = tk.LabelFrame(self.marquee, text="pieces used")
        self.used_frame.pack(side="top")

        class Total:
            name = "total"

        for t in tetrominoes + (Total(),):
            stack: dict[str, tk.Widget] = {}
            stack["frame"] = tk.Frame(self.used_frame, width=12)
            stack["frame"].pack(side="top")
            stack["quantity"] = tk.Label(stack["frame"], textvariable=self.used[t.name])
            stack["quantity"].pack(side="left")
            stack["unit"] = tk.Label(
                stack["frame"],
                text="{}{}".format("" if t.name == "total" else "x", t.name),
            )
            stack["unit"].pack(side="left")

        self.removed_frame = tk.LabelFrame(self.marquee, text="rows removed")
        self.removed_frame.pack(side="top")
        for r in list(range(1, self.pdeg + 1)) + ["total"]:
            stack: dict[str, tk.Widget] = {}
            stack["frame"] = tk.Frame(self.removed_frame, width=12)
            stack["frame"].pack(side="top")
            stack["quantity"] = tk.Label(stack["frame"], textvariable=self.removed[r])
            stack["quantity"].pack(side="left")
            stack["unit"] = tk.Label(stack["frame"], text="{}{}".format("" if r == "total" else "x", r))
            stack["unit"].pack(side="left")

        self.time_elapsed_frame = tk.LabelFrame(self.marquee, text="elapsed time")
        self.time_elapsed_frame.pack(side="top")
        self.time_elapsed_display = tk.Label(self.time_elapsed_frame, textvariable=self.time_elapsed, width=12)
        self.time_elapsed_display.pack(side="top")

        self.state_display = tk.Label(self.marquee, textvariable=self.state_name)
        self.state_display.pack(side="top")

    def set_state(self, state: GameState) -> None:
        """
        Set the game state.
        """
        self.state = state
        self.state_name.set(state)

    def setup_events(self) -> None:
        """
        Respond to inputs and other game conditions: mainly key input.
        """
        for name, key in self.opts["keys"].items():
            self.master.bind(key, getattr(self, name))

    def pause(self, event: tk.Event) -> None:
        """
        (Un)pause the game.  This function is bound by `setup_events` to the key the user configures for pausing.
        """
        if self.state == GameState.running:
            self.after_cancel(self.iterate_id)
            self.time_elapsed.stop()
            for board in (self.board, self.preview_board, self.projection_board):
                board.add_pause_cover()
            self.set_state(GameState.paused)
        elif self.state == GameState.paused:
            self.iterate_id = self._schedule(EventType.iterate)
            self.time_elapsed.start()
            for board in (self.board, self.preview_board, self.projection_board):
                board.remove_pause_cover()
            self.set_state(GameState.running)

    def transform(self, event: tk.Event) -> None:
        """
        Transform the current piece.
        """
        if self.state == GameState.running:
            self.move_piece(transformation)

    def restart(self) -> None:
        """
        Restart the game.
        """
        # Setup game state
        self.board.clear()
        self.projection_board.clear()
        self.piece: Polyomino = None

        for removed_counter in self.removed.values():
            removed_counter.set(0)
        for piece_counter in self.used.values():
            piece_counter.set(0)

        self.time_elapsed.set()
        self.time_elapsed.start()

        self._update_rates()
        self.set_state(GameState.running)

        # Setup TK
        self.restart_button.destroy()
        self.add_piece()
        self.iterate_id = self._schedule(EventType.iterate)

    def iterate(self) -> None:
        """
        Process one game cycle by updating everything needing monotonic modification per cycle, such as moving the active piece
        one row down if possible.
        """
        if self.state == GameState.paused:
            return
        if not self.move_piece(Translation.down):
            self._update_piece_on_board(clear=True)  # Remove active
            self._update_piece_on_board(is_active=False)  # Now inactive
            if self.board.select_full_rows():
                self._schedule(EventType.remove)
            self.add_piece()
        if self.opts["debug"]:
            self.board.grid.print()
        if self.state == GameState.running:
            self._update_rates()
            self.iterate_id = self._schedule(EventType.iterate)
        elif self.state == GameState.over:
            self.restart_button = tk.Button(self.marquee, text="restart", command=self.restart)
            self.restart_button.pack(side="top")

    def add_piece(self) -> None:
        """
        Add a tetromino to the top center of the board.
        """

        def get_next_piece() -> None:
            """
            Get a new piece.
            """
            self.preview_board.clear()
            self.next_piece = random.choice(Tetrominoes)()
            self.next_piece.translate(
                [
                    self.preview_board.width // 2,
                    self.preview_board.height // 2,
                ],
                self.preview_board.grid,
            )
            self.preview_board.update(self.next_piece)

        if not self.next_piece:
            get_next_piece()
        self.piece = copy.deepcopy(self.next_piece)
        self.used[self.next_piece.name].set(self.used[self.next_piece.name].get() + 1)
        self.used["total"].set(self.used["total"].get() + 1)
        get_next_piece()

        if self.piece.translate(
            [
                self.board.width // 2 - self.preview_board.width // 2,
                self.board.height - 1 - self.piece.max(Dimension.y),
            ],
            self.board.grid,
        ):
            if self.opts["shadow"] == "projection":
                self.projection_board.clear()
            self._update_piece_on_board()
        else:
            self.set_state(GameState.over)

    def move_piece(self, transformation: Transformation) -> bool:
        """
        Move current piece according to the movement requested.
        """
        # Erase piece from board before testing if transformation is available
        self._update_piece_on_board(clear=True)
        # Apply the transformation on the current piece if possible
        result = self.piece.transform(transformation, self.board.grid)
        # (Re)place
        self._update_piece_on_board()
        return result

    def remove_full_rows(self) -> None:
        """
        Remove full rows and move partial rows down into the vacancies.
        """
        full_count = self.board.remove_full_rows()
        self._update_removed(full_count)


class Preferences(tk.Frame):
    """
    Dialog for editing game preferences.
    """

    def __init__(self):
        """
        Setup preferences dialog.
        """
        raise NotImplementedError("Cannot create preferences dialog")
