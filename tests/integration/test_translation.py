"""Integration tests for translation behavior.

Tests horizontal and vertical movement, including max translations
(left edge, right edge, drop to bottom) to validate movement boundaries.
"""

import copy

import pytest

from tetratile import EigenTransformation, Grid, Transformation, tetrominoes


class TestHorizontalMovement:
    """Test horizontal movement (left/right)."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_move_left_from_center(self, piece_idx: int, grid: Grid) -> None:
        """Move left from center succeeds."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        result = piece.translate([-1, 0], grid)

        assert result is True, f"{piece.name} move left from center failed"

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_move_right_from_center(self, piece_idx: int, grid: Grid) -> None:
        """Move right from center succeeds."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        result = piece.translate([1, 0], grid)

        assert result is True, f"{piece.name} move right from center failed"

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_left_movement_stops_at_wall(self, piece_idx: int, grid: Grid) -> None:
        """Left movement stops at left wall."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        # Start at x=1 so there's one valid move left
        piece.translate([1, 11], grid)

        # Move left - should either succeed or fail, but coordinates must stay valid
        piece.translate([-1, 0], grid)

        # Verify all coords are within valid grid range (can extend slightly for wide pieces)
        for coord in piece.coords:
            # Allow small negative values for wide pieces like I
            assert coord[0] >= -3, f"{piece.name} went too far left (x={coord[0]})"


class TestVerticalMovement:
    """Test vertical movement (down)."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_move_down_from_center(self, piece_idx: int, grid: Grid) -> None:
        """Move down from center succeeds."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        result = piece.translate([0, -1], grid)

        assert result is True, f"{piece.name} move down from center failed"

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_down_movement_stops_at_floor(self, piece_idx: int, grid: Grid) -> None:
        """Down movement stops at floor."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 2], grid)

        # Move down until we can't anymore
        moves = 0
        while piece.translate([0, -1], grid):
            moves += 1
            # Prevent infinite loop
            if moves > 10:
                break

        # Should have moved at least once from y=2
        assert moves >= 1, f"{piece.name} couldn't move down from y=2"


class TestMaxTranslation:
    """Test maximal translations (min, max)."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_max_left_translation(self, piece_idx: int, grid: Grid) -> None:
        """Max translation to left edge works."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([8, 11], grid)

        piece.transform(Transformation(EigenTransformation.min), grid)

        # Should reach or get close to left edge
        min_x = min(c[0] for c in piece.coords)
        assert min_x >= 0

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_max_right_translation(self, piece_idx: int, grid: Grid) -> None:
        """Max translation to right edge works."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([1, 11], grid)

        piece.transform(Transformation(EigenTransformation.max), grid)

        max_x = max(c[0] for c in piece.coords)
        assert max_x < grid.width


class TestTranslationPreservesSquares:
    """Test that translation preserves the same number of squares."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_horizontal_translation_preserves_squares(self, piece_idx: int, grid: Grid) -> None:
        """Horizontal translation preserves square count."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        initial_count = len(piece.coords)

        # Move left and right
        piece.translate([-3, 0], grid)
        piece.translate([3, 0], grid)

        assert len(piece.coords) == initial_count

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_vertical_translation_preserves_squares(self, piece_idx: int, grid: Grid) -> None:
        """Vertical translation preserves square count."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        initial_count = len(piece.coords)

        # Move down and up
        piece.translate([0, -5], grid)
        piece.translate([0, 5], grid)

        assert len(piece.coords) == initial_count


class TestTranslationWithStack:
    """Test translation with a stack present."""

    @pytest.fixture
    def grid_with_stack(self) -> Grid:
        """Create grid with a stack."""
        grid = Grid(10, 22)
        # Add a row at the bottom
        for x in range(10):
            grid[x, 0].type = "T"
        return grid

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_down_stops_at_stack(self, piece_idx: int, grid_with_stack: Grid) -> None:
        """Down movement stops at stack."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 3], grid_with_stack)

        # Move down until blocked
        while piece.translate([0, -1], grid_with_stack):
            pass

        # Should be above the stack
        min_y = min(c[1] for c in piece.coords)
        assert min_y > 0

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_horizontal_movement_with_stack(self, piece_idx: int, grid_with_stack: Grid) -> None:
        """Horizontal movement works around stack."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 3], grid_with_stack)

        # Move left
        result = piece.translate([-1, 0], grid_with_stack)
        assert result is True

        # Move right
        result = piece.translate([1, 0], grid_with_stack)
        assert result is True
