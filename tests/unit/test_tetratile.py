"""Unit tests for tetratile."""

import decimal

import pytest

from tetratile import (
    Colors,
    Grid,
    Polyomino,
    Rotation,
    Square,
    Translation,
    _boundary_kicks,
    _rotation_state,
    mix_with_black,
    tetrominoes,
)
from tetratile.config import GameConfig

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_DEFAULT_GRID_WIDTH = GameConfig().board.width
_DEFAULT_GRID_HEIGHT = GameConfig().board.height


@pytest.fixture
def grid() -> Grid:
    """Create a default 10×22 grid for unit tests."""
    return Grid(_DEFAULT_GRID_WIDTH, _DEFAULT_GRID_HEIGHT)


@pytest.fixture
def small_grid() -> Grid:
    """Create a standard 10×22 grid for boundary-kick tests."""
    return Grid(10, 22)


# ---------------------------------------------------------------------------
# TestPolyomino
# ---------------------------------------------------------------------------


class TestPolyomino:
    """Tests for Polyomino class."""

    @pytest.mark.parametrize("piece", tetrominoes)
    def test_ordinal(self, piece: Polyomino) -> None:
        """Polyomino.ordinal equals four for every tetromino."""
        assert piece.ordinal == 4

    @pytest.mark.parametrize(
        "squares,expected",
        [
            (frozenset({Square(1, 2), Square(3, 4), Square(2, 1)}), 1),
        ],
    )
    def test_min_x(self, squares: frozenset[Square], expected: int) -> None:
        """Polyomino.min_x returns the correct minimum x coordinate."""
        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.min_x == expected

    @pytest.mark.parametrize(
        "squares,expected",
        [
            (frozenset({Square(1, 2), Square(3, 4), Square(2, 1)}), 3),
        ],
    )
    def test_max_x(self, squares: frozenset[Square], expected: int) -> None:
        """Polyomino.max_x returns the correct maximum x coordinate."""
        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.max_x == expected

    @pytest.mark.parametrize(
        "squares,expected",
        [
            (frozenset({Square(1, 2), Square(3, 4), Square(2, 1)}), 1),
        ],
    )
    def test_min_y(self, squares: frozenset[Square], expected: int) -> None:
        """Polyomino.min_y returns the correct minimum y coordinate."""
        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.min_y == expected

    @pytest.mark.parametrize(
        "squares,expected",
        [
            (frozenset({Square(1, 2), Square(3, 4), Square(2, 1)}), 4),
        ],
    )
    def test_max_y(self, squares: frozenset[Square], expected: int) -> None:
        """Polyomino.max_y returns the correct maximum y coordinate."""
        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.max_y == expected

    @pytest.mark.parametrize("piece", [p for p in tetrominoes if p.name != "o"])
    def test_rotate_value_semantics(self, piece: Polyomino, grid: Grid) -> None:
        """Polyomino.rotate returns a new Polyomino without mutating the original."""
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None
        original_squares = moved.squares
        rotated = moved.rotate(Rotation(1), grid)
        assert rotated is not None
        assert moved.squares == original_squares
        assert rotated is not moved

    @pytest.mark.parametrize("piece", tetrominoes)
    def test_translate_value_semantics(self, piece: Polyomino, grid: Grid) -> None:
        """Polyomino.translate returns a new Polyomino without mutating the original."""
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None
        original_squares = moved.squares
        translated = moved.translate(Translation(1, 0), grid)
        assert translated is not None
        assert moved.squares == original_squares
        assert translated is not moved

    def test_translate_blocked_returns_none(self, grid: Grid) -> None:
        """Polyomino.translate returns None when blocked."""
        piece = tetrominoes[0]  # Z piece
        moved = piece.translate(Translation(grid.width // 2, 0), grid)
        assert moved is not None
        result = moved.translate(Translation(0, -1), grid)
        assert result is None

    @pytest.mark.parametrize("piece", tetrominoes)
    def test_four_cw_rotations_return_to_original(self, piece: Polyomino, grid: Grid) -> None:
        """Four CW rotations return every piece to its original square set."""
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None
        original_squares = moved.squares
        current = moved
        for _ in range(4):
            rotated = current.rotate(Rotation(1), grid)
            if rotated is None:
                break
            current = rotated
        assert current.squares == original_squares, (
            f"{piece.name} did not return after 4 CW rotations"
        )


# ---------------------------------------------------------------------------
# TestGrid
# ---------------------------------------------------------------------------


class TestGrid:
    """Tests for Grid class."""

    def test_get_empty_returns_none(self, grid: Grid) -> None:
        """Grid.__getitem__ returns None for every cell in a fresh grid."""
        for s in grid:
            assert grid[s] is None

    @pytest.mark.parametrize(
        "square",
        [
            Square(-1, 0),
            Square(0, -1),
        ],
    )
    def test_get_out_of_bounds_negative_raises(self, grid: Grid, square: Square) -> None:
        """Grid.__getitem__ raises IndexError for negative out-of-bounds squares."""
        with pytest.raises(IndexError):
            _ = grid[square]

    def test_get_out_of_bounds_positive_raises(self, grid: Grid) -> None:
        """Grid.__getitem__ raises IndexError for positive out-of-bounds squares."""
        with pytest.raises(IndexError):
            _ = grid[Square(grid.width, 0)]
        with pytest.raises(IndexError):
            _ = grid[Square(0, grid.height)]

    def test_set_and_get_roundtrip(self, grid: Grid) -> None:
        """Grid.__setitem__ and __getitem__ round-trip for a single known cell."""
        grid[Square(0, 0)] = "T"
        assert grid[Square(0, 0)] == "T"

    def test_set_none_clears(self, grid: Grid) -> None:
        """Setting a cell to None clears it."""
        s = Square(0, 0)
        grid[s] = "T"
        assert grid[s] == "T"
        grid[s] = None
        assert grid[s] is None

    def test_set_out_of_bounds_raises(self, grid: Grid) -> None:
        """Grid.__setitem__ raises IndexError for out-of-bounds squares."""
        with pytest.raises(IndexError):
            grid[Square(-1, 0)] = "T"
        with pytest.raises(IndexError):
            grid[Square(0, -1)] = "T"
        with pytest.raises(IndexError):
            grid[Square(grid.width, 0)] = "T"
        with pytest.raises(IndexError):
            grid[Square(0, grid.height)] = "T"

    def test_check_all_squares_valid_on_empty_grid(self, grid: Grid) -> None:
        """Grid.check validates every individual square on an empty grid."""
        for s in grid:
            assert grid.check(frozenset({s}))

    def test_check_occupied_cell_fails(self, grid: Grid) -> None:
        """Grid.check fails for an occupied square."""
        s = Square(0, 0)
        grid[s] = "T"
        assert not grid.check(frozenset({s}))

    def test_check_out_of_bounds_fails(self, grid: Grid) -> None:
        """Grid.check fails for out-of-bounds squares."""
        assert not grid.check(frozenset({Square(-1, 0)}))
        assert not grid.check(frozenset({Square(0, -1)}))
        assert not grid.check(frozenset({Square(grid.width, 0)}))
        assert not grid.check(frozenset({Square(0, grid.height)}))

    def test_iter_yields_all_squares(self, grid: Grid) -> None:
        """Grid.__iter__ yields exactly width×height squares."""
        squares = list(grid)
        assert len(squares) == grid.width * grid.height

    def test_occupied_reflects_set_items(self, grid: Grid) -> None:
        """Grid.occupied() returns all squares set to non-None."""
        grid[Square(0, 0)] = "T"
        grid[Square(1, 1)] = "S"
        occ = grid.occupied()
        assert occ[Square(0, 0)] == "T"
        assert occ[Square(1, 1)] == "S"
        assert len(occ) == 2


# ---------------------------------------------------------------------------
# TestMixWithBlack
# ---------------------------------------------------------------------------


class TestMixWithBlack:
    """Tests for mix_with_black() function."""

    def test_mix_with_black_full_black(self) -> None:
        """mix_with_black with factor=1.0 returns black."""
        result = mix_with_black("#FF0000", 1.0)
        assert result == "#000000"

    def test_mix_with_black_zero_factor(self) -> None:
        """mix_with_black with factor=0.0 returns the original color."""
        result = mix_with_black("#FF0000", 0.0)
        assert result == "#ff0000"

    def test_mix_with_black_partial_mix(self) -> None:
        """mix_with_black with factor=0.5 halves each channel."""
        result = mix_with_black("#FF0000", 0.5)
        assert result.startswith("#")
        assert int(result[1:3], 16) == 127

    def test_mix_with_black_invalid_color_short(self) -> None:
        """mix_with_black handles a short (invalid) hex string unchanged."""
        result = mix_with_black("#FF", 0.5)
        assert result == "#FF"

    def test_mix_with_black_invalid_color_empty(self) -> None:
        """mix_with_black handles an empty string unchanged."""
        result = mix_with_black("", 0.5)
        assert result == ""

    def test_mix_with_black_invalid_color_none(self) -> None:
        """mix_with_black handles a non-hex string unchanged."""
        result = mix_with_black("invalid", 0.5)
        assert result == "invalid"

    def test_mix_with_black_green(self) -> None:
        """mix_with_black with factor=0.5 halves the green channel."""
        result = mix_with_black("#00FF00", 0.5)
        assert result.startswith("#")
        assert int(result[3:5], 16) == 127

    def test_mix_with_black_blue(self) -> None:
        """mix_with_black with factor=0.5 halves the blue channel."""
        result = mix_with_black("#0000FF", 0.5)
        assert result.startswith("#")
        assert int(result[5:7], 16) == 127


# ---------------------------------------------------------------------------
# TestBoundaryKicks
# ---------------------------------------------------------------------------


class TestBoundaryKicks:
    """Tests for _boundary_kicks algebraic generator."""

    def test_identity_always_first(self, small_grid: Grid) -> None:
        """_boundary_kicks always yields Translation(0, 0) first."""
        piece = tetrominoes[3].translate(Translation(5, 11), small_grid)
        assert piece is not None
        kicks = list(_boundary_kicks(piece, small_grid))
        assert kicks[0] == Translation(0, 0)

    def test_in_bounds_only_identity(self, small_grid: Grid) -> None:
        """A piece fully in bounds yields only the identity kick."""
        piece = tetrominoes[3].translate(Translation(5, 11), small_grid)
        assert piece is not None
        kicks = list(_boundary_kicks(piece, small_grid))
        assert kicks == [Translation(0, 0)]

    @pytest.mark.parametrize("piece", tetrominoes)
    def test_at_most_four_candidates(self, piece: Polyomino, small_grid: Grid) -> None:
        """_boundary_kicks yields at most 4 candidates for any piece."""
        moved = piece.translate(Translation(5, 11), small_grid)
        assert moved is not None
        kicks = list(_boundary_kicks(moved, small_grid))
        assert len(kicks) <= 4


# ---------------------------------------------------------------------------
# TestRotationState
# ---------------------------------------------------------------------------


class TestRotationState:
    """Tests for _rotation_state() — derives C₄ index from piece squares."""

    @pytest.mark.parametrize("piece", tetrominoes)
    def test_spawn_state_is_zero_for_all_pieces(self, piece: Polyomino, small_grid: Grid) -> None:
        """Every piece at spawn orientation reports rotation state 0."""
        moved = piece.translate(Translation(5, 11), small_grid)
        assert moved is not None
        assert _rotation_state(moved) == 0, f"{piece.name} spawn state should be 0"

    @pytest.mark.parametrize(
        "piece_idx", [i for i in range(len(tetrominoes)) if tetrominoes[i].name != "o"]
    )
    def test_cw_rotations_cycle_0_1_2_3(self, piece_idx: int, small_grid: Grid) -> None:
        """Four successive CW rotations produce states 1, 2, 3, 0 in order (non-O pieces)."""
        piece_type = tetrominoes[piece_idx]
        piece = piece_type.translate(Translation(5, 11), small_grid)
        assert piece is not None

        current = piece
        for expected in [1, 2, 3, 0]:
            rotated = current.rotate(Rotation(1), small_grid)
            assert rotated is not None, f"{piece_type.name} CW rotation failed at state {expected}"
            current = rotated
            assert _rotation_state(current) == expected, (
                f"{piece_type.name} expected state {expected}, got {_rotation_state(current)}"
            )

    @pytest.mark.parametrize(
        "piece_idx", [i for i in range(len(tetrominoes)) if tetrominoes[i].name != "o"]
    )
    def test_ccw_rotations_cycle_3_2_1_0(self, piece_idx: int, small_grid: Grid) -> None:
        """Four successive CCW rotations produce states 3, 2, 1, 0 in order (non-O pieces)."""
        piece_type = tetrominoes[piece_idx]
        piece = piece_type.translate(Translation(5, 11), small_grid)
        assert piece is not None

        current = piece
        for expected in [3, 2, 1, 0]:
            rotated = current.rotate(Rotation(-1), small_grid)
            assert rotated is not None, f"{piece_type.name} CCW rotation failed at state {expected}"
            current = rotated
            assert _rotation_state(current) == expected, (
                f"{piece_type.name} CCW expected state {expected}, got {_rotation_state(current)}"
            )

    def test_o_piece_rotation_state_always_zero(self, small_grid: Grid) -> None:
        """O piece always reports rotation state 0 (all four states are identical)."""
        o_piece = next(t for t in tetrominoes if t.name == "o")
        piece = o_piece.translate(Translation(5, 11), small_grid)
        assert piece is not None
        assert _rotation_state(piece) == 0
        rotated = piece.rotate(Rotation(1), small_grid)
        if rotated is not None:
            assert _rotation_state(rotated) == 0

    def test_unknown_piece_name_returns_minus_one(self, small_grid: Grid) -> None:
        """_rotation_state returns -1 for a piece with an unrecognised name."""
        unknown = Polyomino(
            squares=frozenset({Square(5, 11), Square(6, 11)}),
            origin=(decimal.Decimal(5), decimal.Decimal(11)),
            colors=tetrominoes[0].colors,
            name="X",
        )
        assert _rotation_state(unknown) == -1

    @pytest.mark.parametrize(
        "piece", [t for t in tetrominoes if t.name in ("T", "L", "J", "Z", "S")]
    )
    def test_all_four_states_distinct_for_asymmetric_pieces(
        self, piece: Polyomino, small_grid: Grid
    ) -> None:
        """Asymmetric pieces (T, L, J, Z, S) have four distinct rotation states."""
        moved = piece.translate(Translation(5, 11), small_grid)
        assert moved is not None
        states = [_rotation_state(moved)]
        current = moved
        for _ in range(3):
            rotated = current.rotate(Rotation(1), small_grid)
            assert rotated is not None, f"{piece.name} rotation failed"
            current = rotated
            states.append(_rotation_state(current))
        assert len(set(states)) == 4, f"{piece.name} rotation states not all distinct: {states}"
