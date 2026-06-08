"""Integration tests for row removal conditions.

Row removal operates on the :class:`.Grid` occupancy map.  These tests
build grid state directly, apply the row-removal algorithm, and verify
the resulting occupancy.  The algorithm is extracted from
:meth:`.TetraTile.remove_full_rows` for unit-testability.
"""

import pytest

from tetratile import Grid, Square
from tetratile.config import GameConfig


def _remove_full_rows(grid: Grid) -> int:
    """Apply the row-removal algorithm to ``grid`` in place.

    Mirrors the logic in :meth:`.TetraTile.remove_full_rows` but operates
    directly on a :class:`Grid` without requiring a running game or Tkinter.

    :param grid: The :class:`Grid` to modify.
    :returns: Number of full rows removed.
    """
    width, height = grid.width, grid.height

    full_rows = [
        y for y in range(height) if all(Square(x, y) in grid._occupancy for x in range(width))
    ]

    if not full_rows:
        return 0

    full_set = set(full_rows)
    new_occupancy: dict[Square, str] = {}
    for s, name in grid.occupied().items():
        if s.y in full_set:
            continue
        rows_below = sum(1 for fy in full_rows if fy < s.y)
        new_s = Square(s.x, s.y - rows_below)
        new_occupancy[new_s] = name

    grid._occupancy = new_occupancy
    return len(full_rows)


class TestRowRemovalConditions:
    """Tests for row removal edge cases."""

    @pytest.fixture
    def grid(self, config: GameConfig) -> Grid:
        """Create a test grid."""
        return Grid(config.board.width, config.board.height)

    def test_single_full_row(self, grid: Grid) -> None:
        """Test removing a single full row."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"

        count = _remove_full_rows(grid)

        assert count == 1
        for x in range(grid.width):
            assert grid[Square(x, 0)] is None

    def test_two_consecutive_full_rows(self, grid: Grid) -> None:
        """Test removing two consecutive full rows."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
            grid[Square(x, 1)] = "S"

        count = _remove_full_rows(grid)

        assert count == 2
        for x in range(grid.width):
            assert grid[Square(x, 0)] is None
            assert grid[Square(x, 1)] is None

    def test_three_consecutive_full_rows(self, grid: Grid) -> None:
        """Test removing three consecutive full rows."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
            grid[Square(x, 1)] = "S"
            grid[Square(x, 2)] = "L"

        count = _remove_full_rows(grid)

        assert count == 3

    def test_four_consecutive_full_rows(self, grid: Grid) -> None:
        """Test removing four consecutive full rows (tetris)."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
            grid[Square(x, 1)] = "S"
            grid[Square(x, 2)] = "L"
            grid[Square(x, 3)] = "J"

        count = _remove_full_rows(grid)

        assert count == 4

    def test_non_consecutive_full_rows(self, grid: Grid) -> None:
        """Test that non-consecutive full rows are both detected."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
            grid[Square(x, 2)] = "S"

        count = _remove_full_rows(grid)

        assert count == 2

    def test_partial_row_not_removed(self, grid: Grid) -> None:
        """Test that a row with one empty cell is not removed."""
        for x in range(grid.width - 1):
            grid[Square(x, 0)] = "T"

        count = _remove_full_rows(grid)

        assert count == 0
        for x in range(grid.width - 1):
            assert grid[Square(x, 0)] == "T"

    def test_empty_grid_returns_zero(self, grid: Grid) -> None:
        """Test that removing rows from an empty grid returns 0."""
        count = _remove_full_rows(grid)
        assert count == 0


class TestRowShiftBehavior:
    """Tests for row shifting after removal."""

    @pytest.fixture
    def grid(self, config: GameConfig) -> Grid:
        """Create a test grid."""
        return Grid(config.board.width, config.board.height)

    def test_partial_row_not_affected_without_full_row(self, grid: Grid) -> None:
        """Partial rows are not affected when no full rows exist."""
        grid[Square(0, 0)] = "T"
        grid[Square(1, 0)] = "S"
        grid[Square(0, 1)] = "L"

        count = _remove_full_rows(grid)

        assert count == 0
        assert grid[Square(0, 0)] == "T"
        assert grid[Square(1, 0)] == "S"
        assert grid[Square(0, 1)] == "L"

    def test_multiple_rows_shift_correctly(self, grid: Grid) -> None:
        """Piece above a full row shifts down after clearing."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
        grid[Square(0, 1)] = "Z"

        count = _remove_full_rows(grid)

        assert count == 1
        assert grid[Square(0, 0)] == "Z"
        assert grid[Square(0, 1)] is None

    def test_overburden_shifts_two_rows(self, grid: Grid) -> None:
        """Overburden shifts down by 2 when two full rows are cleared."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
            grid[Square(x, 1)] = "S"
        grid[Square(0, 2)] = "Z"
        grid[Square(0, 3)] = "L"

        count = _remove_full_rows(grid)

        assert count == 2
        assert grid[Square(0, 0)] == "Z"
        assert grid[Square(0, 1)] == "L"
        assert grid[Square(0, 2)] is None
        assert grid[Square(0, 3)] is None

    def test_overburden_non_consecutive_full_rows(self, grid: Grid) -> None:
        """Overburden shifts correctly with non-consecutive full rows."""
        grid[Square(0, 0)] = "Z"
        for x in range(grid.width):
            grid[Square(x, 1)] = "T"
        grid[Square(0, 2)] = "S"
        for x in range(grid.width):
            grid[Square(x, 3)] = "J"
        grid[Square(0, 4)] = "L"

        count = _remove_full_rows(grid)

        assert count == 2
        assert grid[Square(0, 0)] == "Z"
        assert grid[Square(0, 1)] == "S"
        assert grid[Square(0, 2)] == "L"
        assert grid[Square(0, 3)] is None
        assert grid[Square(0, 4)] is None


class TestMixedRowConditions:
    """Tests for mixed row conditions."""

    @pytest.fixture
    def grid(self, config: GameConfig) -> Grid:
        """Create a test grid."""
        return Grid(config.board.width, config.board.height)

    def test_mixed_full_and_partial_rows(self, grid: Grid) -> None:
        """Partial rows above a full row shift down after clearing."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
        grid[Square(0, 1)] = "S"

        count = _remove_full_rows(grid)

        assert count == 1
        assert grid[Square(0, 0)] == "S"
        assert grid[Square(0, 1)] is None

    def test_full_row_at_top_both_cleared(self, grid: Grid) -> None:
        """Two full rows are both cleared."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
            grid[Square(x, 1)] = "S"

        count = _remove_full_rows(grid)

        assert count == 2
        for x in range(grid.width):
            assert grid[Square(x, 0)] is None
            assert grid[Square(x, 1)] is None

    def test_stack_preservation_after_clear(self, grid: Grid) -> None:
        """Stacked pieces shift down correctly after row clear."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
        grid[Square(0, 1)] = "S"
        grid[Square(0, 2)] = "L"

        count = _remove_full_rows(grid)

        assert count == 1
        assert grid[Square(0, 0)] == "S"
        assert grid[Square(0, 1)] == "L"
        assert grid[Square(0, 2)] is None
