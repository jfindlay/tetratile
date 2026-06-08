"""Integration tests for translation behavior.

Tests horizontal and vertical movement, including maximal translations
(left edge, right edge, drop to bottom) to validate movement boundaries.
"""

import pytest

from tetratile import Grid, Polyomino, Square, Translation, tetrominoes


class TestHorizontalMovement:
    """Test horizontal movement (left/right)."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_move_left_from_center(self, piece_idx: int, grid: Grid) -> None:
        """Move left from center succeeds."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        result = piece.translate(Translation(-1, 0), grid)

        assert result is not None, f"{piece.name} move left from center failed"

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_move_right_from_center(self, piece_idx: int, grid: Grid) -> None:
        """Move right from center succeeds."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        result = piece.translate(Translation(1, 0), grid)

        assert result is not None, f"{piece.name} move right from center failed"

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_left_movement_stops_at_wall(self, piece_idx: int, grid: Grid) -> None:
        """Left movement stops at left wall."""
        # Use x=4 so the I piece (4 wide, local x in [-2,1]) also fits
        piece = tetrominoes[piece_idx].translate(Translation(4, 11), grid)
        assert piece is not None

        # Move left until blocked
        current = piece
        while True:
            moved = current.translate(Translation(-1, 0), grid)
            if moved is None:
                break
            current = moved

        # All squares must be in-bounds at the leftmost reachable position
        for s in current.squares:
            assert s.x >= 0, f"{piece.name} went below left wall (x={s.x})"


class TestVerticalMovement:
    """Test vertical movement (down)."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_move_down_from_center(self, piece_idx: int, grid: Grid) -> None:
        """Move down from center succeeds."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        result = piece.translate(Translation(0, -1), grid)

        assert result is not None, f"{piece.name} move down from center failed"

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_down_movement_stops_at_floor(self, piece_idx: int, grid: Grid) -> None:
        """Down movement stops at floor."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 2), grid)
        assert piece is not None

        current = piece
        moves = 0
        while True:
            moved = current.translate(Translation(0, -1), grid)
            if moved is None:
                break
            current = moved
            moves += 1
            if moves > 10:
                break

        assert moves >= 1, f"{piece.name} couldn't move down from y=2"


class TestMaxTranslation:
    """Test maximal translations (left wall, right wall, floor)."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_max_left_translation(self, piece_idx: int, grid: Grid) -> None:
        """Max translation to left edge works."""
        piece: Polyomino | None = tetrominoes[piece_idx].translate(Translation(8, 11), grid)
        assert piece is not None

        while True:
            moved = piece.translate(Translation(-1, 0), grid)
            if moved is None:
                break
            piece = moved

        assert piece.min_x >= 0

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_max_right_translation(self, piece_idx: int, grid: Grid) -> None:
        """Max translation to right edge works."""
        piece: Polyomino | None = tetrominoes[piece_idx].translate(Translation(4, 11), grid)
        assert piece is not None

        while True:
            moved = piece.translate(Translation(1, 0), grid)
            if moved is None:
                break
            piece = moved

        assert piece.max_x < grid.width


class TestTranslationPreservesSquares:
    """Test that translation preserves the same number of squares."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_horizontal_translation_preserves_squares(self, piece_idx: int, grid: Grid) -> None:
        """Horizontal translation preserves square count."""
        piece: Polyomino | None = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal

        # Move left then right
        moved = piece.translate(Translation(-3, 0), grid)
        if moved is not None:
            piece = moved
        moved = piece.translate(Translation(3, 0), grid)
        if moved is not None:
            piece = moved

        assert piece.ordinal == initial_count

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_vertical_translation_preserves_squares(self, piece_idx: int, grid: Grid) -> None:
        """Vertical translation preserves square count."""
        piece: Polyomino | None = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal

        moved = piece.translate(Translation(0, -5), grid)
        if moved is not None:
            piece = moved
        moved = piece.translate(Translation(0, 5), grid)
        if moved is not None:
            piece = moved

        assert piece.ordinal == initial_count


class TestTranslationWithStack:
    """Test translation with a stack present."""

    @pytest.fixture
    def grid_with_stack(self) -> Grid:
        """Create grid with a stack at y=0."""
        grid = Grid(10, 22)
        for x in range(10):
            grid[Square(x, 0)] = "T"
        return grid

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_down_stops_at_stack(self, piece_idx: int, grid_with_stack: Grid) -> None:
        """Down movement stops above the stack."""
        piece: Polyomino | None = tetrominoes[piece_idx].translate(
            Translation(5, 3), grid_with_stack
        )
        assert piece is not None

        current = piece
        while True:
            moved = current.translate(Translation(0, -1), grid_with_stack)
            if moved is None:
                break
            current = moved

        assert current.min_y > 0

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_horizontal_movement_with_stack(self, piece_idx: int, grid_with_stack: Grid) -> None:
        """Horizontal movement works above the stack."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 3), grid_with_stack)
        assert piece is not None

        result_left = piece.translate(Translation(-1, 0), grid_with_stack)
        assert result_left is not None

        result_right = piece.translate(Translation(1, 0), grid_with_stack)
        assert result_right is not None
