"""Unit tests for tetratile."""

import random
from collections.abc import Generator
from contextlib import contextmanager

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


@contextmanager
def not_raises(exception: type[Exception]) -> Generator[None, None, None]:
    """Context manager to verify an exception is NOT raised.

    :param exception: The exception type that should not be raised.
    :yields: Nothing.
    """
    try:
        yield
    except exception:
        raise pytest.fail(f"DID RAISE {exception}") from None


class TestPolyomino:
    """Tests for Polyomino class."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_ordinal(self) -> None:
        """Test Polyomino.ordinal equals number of squares."""
        for t in tetrominoes:
            assert t.ordinal == 4

    def test_min_x(self) -> None:
        """Test Polyomino.min_x returns correct minimum x coordinate."""
        squares = frozenset({Square(1, 2), Square(3, 4), Square(2, 1)})
        import decimal

        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.min_x == 1

    def test_max_x(self) -> None:
        """Test Polyomino.max_x returns correct maximum x coordinate."""
        squares = frozenset({Square(1, 2), Square(3, 4), Square(2, 1)})
        import decimal

        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.max_x == 3

    def test_min_y(self) -> None:
        """Test Polyomino.min_y returns correct minimum y coordinate."""
        squares = frozenset({Square(1, 2), Square(3, 4), Square(2, 1)})
        import decimal

        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.min_y == 1

    def test_max_y(self) -> None:
        """Test Polyomino.max_y returns correct maximum y coordinate."""
        squares = frozenset({Square(1, 2), Square(3, 4), Square(2, 1)})
        import decimal

        p = Polyomino(
            squares=squares,
            origin=(decimal.Decimal(2), decimal.Decimal(2)),
            colors=Colors(),
            name="T",
        )
        assert p.max_y == 4

    def test_rotate_value_semantics(self) -> None:
        """Polyomino.rotate returns a new Polyomino, not mutating the original."""
        for piece_type in tetrominoes:
            if piece_type.name == "o":
                continue
            moved = piece_type.translate(
                Translation(self.grid.width // 2, self.grid.height // 2), self.grid
            )
            assert moved is not None
            original_squares = moved.squares
            rotated = moved.rotate(Rotation(1), self.grid)
            assert rotated is not None
            # Original is unchanged
            assert moved.squares == original_squares
            # Result is a different object
            assert rotated is not moved

    def test_translate_value_semantics(self) -> None:
        """Polyomino.translate returns a new Polyomino, not mutating the original."""
        for piece_type in tetrominoes:
            moved = piece_type.translate(
                Translation(self.grid.width // 2, self.grid.height // 2), self.grid
            )
            assert moved is not None
            original_squares = moved.squares
            translated = moved.translate(Translation(1, 0), self.grid)
            assert translated is not None
            assert moved.squares == original_squares
            assert translated is not moved

    def test_translate_blocked_returns_none(self) -> None:
        """Polyomino.translate returns None when blocked."""
        piece = tetrominoes[0]  # Z piece
        moved = piece.translate(Translation(self.grid.width // 2, 0), self.grid)
        assert moved is not None
        result = moved.translate(Translation(0, -1), self.grid)
        assert result is None

    def test_four_cw_rotations_return_to_original(self) -> None:
        """Four CW rotations return piece to original square set."""
        for piece_type in tetrominoes:
            moved = piece_type.translate(
                Translation(self.grid.width // 2, self.grid.height // 2), self.grid
            )
            assert moved is not None
            original_squares = moved.squares
            current = moved
            for _ in range(4):
                rotated = current.rotate(Rotation(1), self.grid)
                if rotated is None:
                    break
                current = rotated
            assert current.squares == original_squares, (
                f"{piece_type.name} did not return after 4 CW rotations"
            )


class TestGrid:
    """Tests for Grid class."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_get_empty_returns_none(self) -> None:
        """Grid.__getitem__ returns None for empty cells."""
        for s in self.grid:
            with not_raises(IndexError):
                assert self.grid[s] is None

    def test_get_out_of_bounds_raises(self) -> None:
        """Grid.__getitem__ raises IndexError for out-of-bounds squares."""
        with pytest.raises(IndexError):
            _ = self.grid[Square(-1, 0)]
        with pytest.raises(IndexError):
            _ = self.grid[Square(0, -1)]
        with pytest.raises(IndexError):
            _ = self.grid[Square(self.grid.width, 0)]
        with pytest.raises(IndexError):
            _ = self.grid[Square(0, self.grid.height)]

    def test_set_and_get(self) -> None:
        """Grid.__setitem__ and __getitem__ round-trip correctly."""
        for i in range(self.grid.width):
            for j in range(self.grid.height):
                with not_raises(IndexError):
                    name = random.choice(list(tetrominoes)).name
                    self.grid[Square(i, j)] = name
                    assert self.grid[Square(i, j)] == name

    def test_set_none_clears(self) -> None:
        """Setting a cell to None clears it."""
        s = Square(0, 0)
        self.grid[s] = "T"
        assert self.grid[s] == "T"
        self.grid[s] = None
        assert self.grid[s] is None

    def test_set_out_of_bounds_raises(self) -> None:
        """Grid.__setitem__ raises IndexError for out-of-bounds squares."""
        with pytest.raises(IndexError):
            self.grid[Square(-1, 0)] = "T"
        with pytest.raises(IndexError):
            self.grid[Square(0, -1)] = "T"
        with pytest.raises(IndexError):
            self.grid[Square(self.grid.width, 0)] = "T"
        with pytest.raises(IndexError):
            self.grid[Square(0, self.grid.height)] = "T"

    def test_check_empty_grid(self) -> None:
        """Grid.check validates all squares on an empty grid."""
        all_squares = frozenset(self.grid)
        for s in all_squares:
            assert self.grid.check(frozenset({s}))

    def test_check_occupied_cell_fails(self) -> None:
        """Grid.check fails for occupied squares."""
        s = Square(0, 0)
        self.grid[s] = "T"
        assert not self.grid.check(frozenset({s}))

    def test_check_out_of_bounds_fails(self) -> None:
        """Grid.check fails for out-of-bounds squares."""
        assert not self.grid.check(frozenset({Square(-1, 0)}))
        assert not self.grid.check(frozenset({Square(0, -1)}))
        assert not self.grid.check(frozenset({Square(self.grid.width, 0)}))
        assert not self.grid.check(frozenset({Square(0, self.grid.height)}))

    def test_iter_yields_all_squares(self) -> None:
        """Grid.__iter__ yields all width*height squares."""
        squares = list(self.grid)
        assert len(squares) == self.grid.width * self.grid.height

    def test_occupied_reflects_set_items(self) -> None:
        """Grid.occupied() returns all squares set to non-None."""
        self.grid[Square(0, 0)] = "T"
        self.grid[Square(1, 1)] = "S"
        occ = self.grid.occupied()
        assert occ[Square(0, 0)] == "T"
        assert occ[Square(1, 1)] == "S"
        assert len(occ) == 2


class TestMixWithBlack:
    """Tests for mix_with_black() function."""

    def test_mix_with_black_full_black(self) -> None:
        """Test mix_with_black with factor=1.0 returns black."""
        result = mix_with_black("#FF0000", 1.0)
        assert result == "#000000"

    def test_mix_with_black_zero_factor(self) -> None:
        """Test mix_with_black with factor=0.0 returns original color."""
        result = mix_with_black("#FF0000", 0.0)
        assert result == "#ff0000"

    def test_mix_with_black_partial_mix(self) -> None:
        """Test mix_with_black with intermediate factor."""
        result = mix_with_black("#FF0000", 0.5)
        assert result.startswith("#")
        assert int(result[1:3], 16) == 127

    def test_mix_with_black_invalid_color_short(self) -> None:
        """Test mix_with_black handles invalid short color."""
        result = mix_with_black("#FF", 0.5)
        assert result == "#FF"

    def test_mix_with_black_invalid_color_empty(self) -> None:
        """Test mix_with_black handles empty string."""
        result = mix_with_black("", 0.5)
        assert result == ""

    def test_mix_with_black_invalid_color_none(self) -> None:
        """Test mix_with_black handles None-like string."""
        result = mix_with_black("invalid", 0.5)
        assert result == "invalid"

    def test_mix_with_black_green(self) -> None:
        """Test mix_with_black with green color."""
        result = mix_with_black("#00FF00", 0.5)
        assert result.startswith("#")
        assert int(result[3:5], 16) == 127

    def test_mix_with_black_blue(self) -> None:
        """Test mix_with_black with blue color."""
        result = mix_with_black("#0000FF", 0.5)
        assert result.startswith("#")
        assert int(result[5:7], 16) == 127


class TestBoundaryKicks:
    """Tests for _boundary_kicks algebraic generator."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        self.grid = Grid(10, 22)

    def test_identity_always_first(self) -> None:
        """_boundary_kicks always yields Translation(0, 0) first."""
        piece = tetrominoes[3].translate(Translation(5, 11), self.grid)
        assert piece is not None
        kicks = list(_boundary_kicks(piece, self.grid))
        assert kicks[0] == Translation(0, 0)

    def test_in_bounds_only_identity(self) -> None:
        """Piece fully in bounds yields only the identity kick."""
        piece = tetrominoes[3].translate(Translation(5, 11), self.grid)
        assert piece is not None
        kicks = list(_boundary_kicks(piece, self.grid))
        assert kicks == [Translation(0, 0)]

    def test_at_most_four_candidates(self) -> None:
        """_boundary_kicks yields at most 4 candidates."""
        for piece_type in tetrominoes:
            piece = piece_type.translate(Translation(5, 11), self.grid)
            assert piece is not None
            kicks = list(_boundary_kicks(piece, self.grid))
            assert len(kicks) <= 4


class TestRotationState:
    """Tests for _rotation_state() — derives C₄ index from piece squares."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up a standard 10×22 grid."""
        self.grid = Grid(10, 22)

    def test_spawn_state_is_zero_for_all_pieces(self) -> None:
        """Every piece at spawn orientation reports rotation state 0."""
        for piece_type in tetrominoes:
            piece = piece_type.translate(Translation(5, 11), self.grid)
            assert piece is not None
            assert _rotation_state(piece) == 0, f"{piece_type.name} spawn state should be 0"

    @pytest.mark.parametrize(
        "piece_idx", [i for i in range(len(tetrominoes)) if tetrominoes[i].name != "o"]
    )
    def test_cw_rotations_cycle_0_1_2_3(self, piece_idx: int) -> None:
        """Four successive CW rotations produce states 1, 2, 3, 0 in order (non-O pieces)."""
        piece_type = tetrominoes[piece_idx]
        piece = piece_type.translate(Translation(5, 11), self.grid)
        assert piece is not None

        current = piece
        for expected in [1, 2, 3, 0]:
            rotated = current.rotate(Rotation(1), self.grid)
            assert rotated is not None, f"{piece_type.name} CW rotation failed at state {expected}"
            current = rotated
            assert _rotation_state(current) == expected, (
                f"{piece_type.name} expected state {expected}, got {_rotation_state(current)}"
            )

    @pytest.mark.parametrize(
        "piece_idx", [i for i in range(len(tetrominoes)) if tetrominoes[i].name != "o"]
    )
    def test_ccw_rotations_cycle_3_2_1_0(self, piece_idx: int) -> None:
        """Four successive CCW rotations produce states 3, 2, 1, 0 in order (non-O pieces)."""
        piece_type = tetrominoes[piece_idx]
        piece = piece_type.translate(Translation(5, 11), self.grid)
        assert piece is not None

        current = piece
        for expected in [3, 2, 1, 0]:
            rotated = current.rotate(Rotation(-1), self.grid)
            assert rotated is not None, f"{piece_type.name} CCW rotation failed at state {expected}"
            current = rotated
            assert _rotation_state(current) == expected, (
                f"{piece_type.name} CCW expected state {expected}, got {_rotation_state(current)}"
            )

    def test_o_piece_rotation_state_always_zero(self) -> None:
        """O piece always reports rotation state 0 (all four states are identical)."""
        o_piece = next(t for t in tetrominoes if t.name == "o")
        piece = o_piece.translate(Translation(5, 11), self.grid)
        assert piece is not None
        # O is rotationally symmetric: rotate() returns the same-squares piece or None
        assert _rotation_state(piece) == 0
        rotated = piece.rotate(Rotation(1), self.grid)
        # Whether or not O returns None, the state is 0
        if rotated is not None:
            assert _rotation_state(rotated) == 0

    def test_unknown_piece_name_returns_minus_one(self) -> None:
        """_rotation_state returns -1 for a piece with an unrecognised name."""
        import decimal

        unknown = Polyomino(
            squares=frozenset({Square(5, 11), Square(6, 11)}),
            origin=(decimal.Decimal(5), decimal.Decimal(11)),
            colors=tetrominoes[0].colors,
            name="X",
        )
        assert _rotation_state(unknown) == -1

    def test_all_four_states_distinct_for_asymmetric_pieces(self) -> None:
        """Asymmetric pieces (T, L, J, Z, S) have four distinct rotation states."""
        asymmetric = [t for t in tetrominoes if t.name in ("T", "L", "J", "Z", "S")]
        for piece_type in asymmetric:
            piece = piece_type.translate(Translation(5, 11), self.grid)
            assert piece is not None
            states = [_rotation_state(piece)]
            current = piece
            for _ in range(3):
                rotated = current.rotate(Rotation(1), self.grid)
                assert rotated is not None, f"{piece_type.name} rotation failed"
                current = rotated
                states.append(_rotation_state(current))
            assert len(set(states)) == 4, (
                f"{piece_type.name} rotation states not all distinct: {states}"
            )
