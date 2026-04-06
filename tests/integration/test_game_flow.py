"""Integration tests for game flow and piece movement."""

import copy
import random

from tetratile import (
    EigenTransformation,
    Grid,
    Transformation,
    tetrominoes,
)


class TestPieceMovement:
    """Tests for piece movement and completeness."""

    def test_tetromino_has_four_squares(self) -> None:
        """Test that each tetromino type has exactly 4 squares."""
        for t in tetrominoes:
            assert len(t.coords) == 4

    def test_movement_preserves_all_squares(self, grid: Grid) -> None:
        """Test that movement doesn't lose squares."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        initial_count = len(tetromino.coords)
        initial_coords = [c[:] for c in tetromino.coords]

        tetromino.translate([2, 0], grid)
        assert len(tetromino.coords) == initial_count

        for i, expected in enumerate(initial_coords):
            assert tetromino.coords[i] == [expected[0] + 2, expected[1]]

    def test_horizontal_movement_left(self, grid: Grid) -> None:
        """Test moving piece left."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        initial_coords = [c[:] for c in tetromino.coords]

        tetromino.translate([-1, 0], grid)

        for i, expected in enumerate(initial_coords):
            assert tetromino.coords[i] == [expected[0] - 1, expected[1]]

    def test_horizontal_movement_right(self, grid: Grid) -> None:
        """Test moving piece right."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        initial_coords = [c[:] for c in tetromino.coords]

        tetromino.translate([1, 0], grid)

        for i, expected in enumerate(initial_coords):
            assert tetromino.coords[i] == [expected[0] + 1, expected[1]]

    def test_vertical_movement_down(self, grid: Grid) -> None:
        """Test moving piece down."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        initial_coords = [c[:] for c in tetromino.coords]

        tetromino.translate([0, -1], grid)

        for i, expected in enumerate(initial_coords):
            assert tetromino.coords[i] == [expected[0], expected[1] - 1]

    def test_rotation_preserves_all_squares(self, grid: Grid) -> None:
        """Test that rotation doesn't lose squares."""
        tetromino = copy.deepcopy(random.choice([t for t in tetrominoes if t.name != "o"]))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        initial_count = len(tetromino.coords)

        for _ in range(4):
            result = tetromino.srs_rotate(1, grid)
            assert result is True
            assert len(tetromino.coords) == initial_count

    def test_piece_at_left_edge_cannot_move_left(self, grid: Grid) -> None:
        """Test that piece at left edge cannot move further left."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([1, grid.height // 2], grid)

        result = tetromino.translate([-1, 0], grid)
        assert result is False

    def test_piece_at_right_edge_cannot_move_right(self, grid: Grid) -> None:
        """Test that piece at right edge cannot move further right."""
        tetromino = copy.deepcopy(tetrominoes[2])  # l piece: x=[-2, -1, 0, 1]
        tetromino.translate([grid.width - 2, grid.height // 2], grid)

        result = tetromino.translate([1, 0], grid)
        assert result is False

    def test_piece_at_bottom_cannot_move_down(self, grid: Grid) -> None:
        """Test that piece at bottom cannot move further down."""
        tetromino = copy.deepcopy(tetrominoes[0])  # Z piece: y=[0, 0, -1, -1]
        tetromino.translate([grid.width // 2, 1], grid)

        result = tetromino.translate([0, -1], grid)
        assert result is False

    def test_side_movement_to_left_wall(self, grid: Grid) -> None:
        """Test moving piece to left wall."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        t = Transformation(EigenTransformation.min)
        result = tetromino.translate(t, grid)

        assert result is True
        min_x = min(c[0] for c in tetromino.coords)
        assert min_x == 0

    def test_side_movement_to_right_wall(self, grid: Grid) -> None:
        """Test moving piece to right wall."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        t = Transformation(EigenTransformation.max)
        result = tetromino.translate(t, grid)

        assert result is True
        max_x = max(c[0] for c in tetromino.coords)
        assert max_x == grid.width - 1

    def test_bottom_movement(self, grid: Grid) -> None:
        """Test moving piece to bottom."""
        tetromino = copy.deepcopy(random.choice(tetrominoes))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        t = Transformation(EigenTransformation.bottom)
        result = tetromino.translate(t, grid)

        assert result is True
        assert tetromino.min(tetromino.dim) == 0

    def test_stacking_preserves_both_pieces(self, grid: Grid) -> None:
        """Test that stacking pieces preserves both."""
        piece1 = copy.deepcopy(tetrominoes[3])  # T piece
        piece1.translate([grid.width // 2, grid.height // 2], grid)

        piece2 = copy.deepcopy(tetrominoes[0])  # Z piece - won't overlap with T
        piece2.translate([grid.width // 2, grid.height // 2 + 5], grid)

        for coord in piece1.coords:
            grid[coord].type = piece1.name

        for coord in piece2.coords:
            grid[coord].type = piece2.name

        piece1_count = sum(1 for v in grid if grid[v].type == piece1.name)
        piece2_count = sum(1 for v in grid if grid[v].type == piece2.name)

        assert piece1_count == 4
        assert piece2_count == 4
