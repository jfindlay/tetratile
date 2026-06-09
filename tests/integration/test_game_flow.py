"""Integration tests for game flow and piece movement."""

import random

import pytest

from tetratile import (
    Grid,
    Polyomino,
    Rotation,
    Square,
    Translation,
    tetrominoes,
)

# Use a fixed seed so random.choice-based tests are deterministic.
_RNG = random.Random(42)


class TestPieceMovement:
    """Tests for piece movement and completeness."""

    @pytest.mark.parametrize("piece", tetrominoes)
    def test_tetromino_has_four_squares(self, piece: Polyomino) -> None:
        """Each tetromino type has exactly 4 squares."""
        assert piece.ordinal == 4

    def test_movement_preserves_all_squares(self, grid: Grid) -> None:
        """Translation does not lose squares."""
        piece = _RNG.choice(tetrominoes)
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_count = moved.ordinal
        initial_squares = moved.squares

        moved2 = moved.translate(Translation(2, 0), grid)
        assert moved2 is not None
        assert moved2.ordinal == initial_count

        expected = frozenset(Square(s.x + 2, s.y) for s in initial_squares)
        assert moved2.squares == expected

    def test_horizontal_movement_left(self, grid: Grid) -> None:
        """Translating left moves each square one column to the left."""
        piece = _RNG.choice(tetrominoes)
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_squares = moved.squares
        moved2 = moved.translate(Translation(-1, 0), grid)
        assert moved2 is not None

        expected = frozenset(Square(s.x - 1, s.y) for s in initial_squares)
        assert moved2.squares == expected

    def test_horizontal_movement_right(self, grid: Grid) -> None:
        """Translating right moves each square one column to the right."""
        piece = _RNG.choice(tetrominoes)
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_squares = moved.squares
        moved2 = moved.translate(Translation(1, 0), grid)
        assert moved2 is not None

        expected = frozenset(Square(s.x + 1, s.y) for s in initial_squares)
        assert moved2.squares == expected

    def test_vertical_movement_down(self, grid: Grid) -> None:
        """Translating down moves each square one row downward."""
        piece = _RNG.choice(tetrominoes)
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_squares = moved.squares
        moved2 = moved.translate(Translation(0, -1), grid)
        assert moved2 is not None

        expected = frozenset(Square(s.x, s.y - 1) for s in initial_squares)
        assert moved2.squares == expected

    def test_rotation_preserves_all_squares(self, grid: Grid) -> None:
        """Rotation does not change the number of squares."""
        piece = _RNG.choice([t for t in tetrominoes if t.name != "o"])
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_count = moved.ordinal
        current = moved
        for _ in range(4):
            rotated = current.rotate(Rotation(1), grid)
            assert rotated is not None
            assert rotated.ordinal == initial_count
            current = rotated

    def test_piece_at_left_edge_cannot_move_left(self, grid: Grid) -> None:
        """A piece at its leftmost position returns None on further left movement."""
        piece = _RNG.choice(tetrominoes)
        current: Polyomino | None = piece.translate(
            Translation(grid.width // 2, grid.height // 2), grid
        )
        assert current is not None
        while True:
            moved = current.translate(Translation(-1, 0), grid)
            if moved is None:
                break
            current = moved

        result = current.translate(Translation(-1, 0), grid)
        assert result is None

    def test_piece_at_right_edge_cannot_move_right(self, grid: Grid) -> None:
        """A piece at the right edge cannot move further right."""
        piece = tetrominoes[2]  # l piece: 4 wide
        moved = piece.translate(Translation(grid.width - 2, grid.height // 2), grid)
        assert moved is not None

        result = moved.translate(Translation(1, 0), grid)
        assert result is None

    def test_piece_at_bottom_cannot_move_down(self, grid: Grid) -> None:
        """A piece at the bottom row cannot move further down."""
        piece = tetrominoes[0]  # Z piece
        moved = piece.translate(Translation(grid.width // 2, 0), grid)
        assert moved is not None

        result = moved.translate(Translation(0, -1), grid)
        assert result is None

    def test_side_movement_to_left_wall(self, grid: Grid) -> None:
        """Piece reaches left wall (min_x == 0) when moved left until blocked."""
        piece = _RNG.choice(tetrominoes)
        current: Polyomino | None = piece.translate(
            Translation(grid.width // 2, grid.height // 2), grid
        )
        assert current is not None

        while True:
            moved = current.translate(Translation(-1, 0), grid)
            if moved is None:
                break
            current = moved

        assert current.min_x == 0

    def test_side_movement_to_right_wall(self, grid: Grid) -> None:
        """Piece reaches right wall (max_x == width-1) when moved right until blocked."""
        piece = _RNG.choice(tetrominoes)
        current: Polyomino | None = piece.translate(
            Translation(grid.width // 2, grid.height // 2), grid
        )
        assert current is not None

        while True:
            moved = current.translate(Translation(1, 0), grid)
            if moved is None:
                break
            current = moved

        assert current.max_x == grid.width - 1

    def test_bottom_movement(self, grid: Grid) -> None:
        """Piece reaches the floor (min_y == 0) when moved down until blocked."""
        piece = _RNG.choice(tetrominoes)
        current: Polyomino | None = piece.translate(
            Translation(grid.width // 2, grid.height // 2), grid
        )
        assert current is not None

        while True:
            moved = current.translate(Translation(0, -1), grid)
            if moved is None:
                break
            current = moved

        assert current.min_y == 0

    def test_stacking_preserves_both_pieces(self, grid: Grid) -> None:
        """Locking two pieces into the grid preserves all squares of both."""
        piece1 = tetrominoes[3]  # T piece
        moved1 = piece1.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved1 is not None

        piece2 = tetrominoes[0]  # Z piece
        moved2 = piece2.translate(Translation(grid.width // 2, grid.height // 2 + 5), grid)
        assert moved2 is not None

        for s in moved1.squares:
            grid[s] = moved1.name
        for s in moved2.squares:
            grid[s] = moved2.name

        piece1_count = sum(1 for s in grid if grid[s] == moved1.name)
        piece2_count = sum(1 for s in grid if grid[s] == moved2.name)

        assert piece1_count == 4
        assert piece2_count == 4
