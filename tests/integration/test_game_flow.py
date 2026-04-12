"""Integration tests for game flow and piece movement."""

import random

from tetratile import (
    Grid,
    Polyomino,
    Rotation,
    Square,
    Translation,
    tetrominoes,
)


class TestPieceMovement:
    """Tests for piece movement and completeness."""

    def test_tetromino_has_four_squares(self) -> None:
        """Test that each tetromino type has exactly 4 squares."""
        for t in tetrominoes:
            assert t.ordinal == 4

    def test_movement_preserves_all_squares(self, grid: Grid) -> None:
        """Test that movement doesn't lose squares."""
        piece = random.choice(tetrominoes)
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
        """Test moving piece left."""
        piece = random.choice(tetrominoes)
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_squares = moved.squares
        moved2 = moved.translate(Translation(-1, 0), grid)
        assert moved2 is not None

        expected = frozenset(Square(s.x - 1, s.y) for s in initial_squares)
        assert moved2.squares == expected

    def test_horizontal_movement_right(self, grid: Grid) -> None:
        """Test moving piece right."""
        piece = random.choice(tetrominoes)
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_squares = moved.squares
        moved2 = moved.translate(Translation(1, 0), grid)
        assert moved2 is not None

        expected = frozenset(Square(s.x + 1, s.y) for s in initial_squares)
        assert moved2.squares == expected

    def test_vertical_movement_down(self, grid: Grid) -> None:
        """Test moving piece down."""
        piece = random.choice(tetrominoes)
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        initial_squares = moved.squares
        moved2 = moved.translate(Translation(0, -1), grid)
        assert moved2 is not None

        expected = frozenset(Square(s.x, s.y - 1) for s in initial_squares)
        assert moved2.squares == expected

    def test_rotation_preserves_all_squares(self, grid: Grid) -> None:
        """Test that rotation doesn't lose squares."""
        piece = random.choice([t for t in tetrominoes if t.name != "o"])
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
        """Test that a piece already at its leftmost position cannot move further left."""
        piece = random.choice(tetrominoes)
        # Move piece to absolute left wall
        current: Polyomino | None = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert current is not None
        while True:
            moved = current.translate(Translation(-1, 0), grid)
            if moved is None:
                break
            current = moved

        # Now at leftmost: one more step left must fail
        result = current.translate(Translation(-1, 0), grid)
        assert result is None

    def test_piece_at_right_edge_cannot_move_right(self, grid: Grid) -> None:
        """Test that piece at right edge cannot move further right."""
        piece = tetrominoes[2]  # l piece: 4 wide
        moved = piece.translate(Translation(grid.width - 2, grid.height // 2), grid)
        assert moved is not None

        result = moved.translate(Translation(1, 0), grid)
        assert result is None

    def test_piece_at_bottom_cannot_move_down(self, grid: Grid) -> None:
        """Test that piece at bottom cannot move further down."""
        piece = tetrominoes[0]  # Z piece
        moved = piece.translate(Translation(grid.width // 2, 0), grid)
        assert moved is not None

        result = moved.translate(Translation(0, -1), grid)
        assert result is None

    def test_side_movement_to_left_wall(self, grid: Grid) -> None:
        """Test moving piece to left wall (orbit supremum)."""
        piece = random.choice(tetrominoes)
        current: Polyomino | None = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert current is not None

        while True:
            moved = current.translate(Translation(-1, 0), grid)
            if moved is None:
                break
            current = moved

        assert current.min_x == 0

    def test_side_movement_to_right_wall(self, grid: Grid) -> None:
        """Test moving piece to right wall (orbit supremum)."""
        piece = random.choice(tetrominoes)
        current: Polyomino | None = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert current is not None

        while True:
            moved = current.translate(Translation(1, 0), grid)
            if moved is None:
                break
            current = moved

        assert current.max_x == grid.width - 1

    def test_bottom_movement(self, grid: Grid) -> None:
        """Test moving piece to bottom (orbit supremum)."""
        piece = random.choice(tetrominoes)
        current: Polyomino | None = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert current is not None

        while True:
            moved = current.translate(Translation(0, -1), grid)
            if moved is None:
                break
            current = moved

        assert current.min_y == 0

    def test_stacking_preserves_both_pieces(self, grid: Grid) -> None:
        """Test that stacking pieces preserves both in the grid."""
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
