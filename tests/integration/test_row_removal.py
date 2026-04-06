"""Integration tests for row removal conditions."""

from unittest.mock import MagicMock

import pytest

from tetratile import Board
from tetratile.config import GameConfig


class TestRowRemovalConditions:
    """Tests for row removal edge cases."""

    @pytest.fixture
    def board(self, config: GameConfig) -> tuple[Board, GameConfig]:
        """Create a board with mocked canvas."""
        mock_parent = MagicMock()
        board = Board(config, mock_parent, config.board.width, config.board.height)
        return board, config

    def test_single_full_row(self, board: tuple[Board, GameConfig]) -> None:
        """Test removing a single full row."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"

        count = board_obj.remove_full_rows()

        assert count == 1
        for x in range(grid.width):
            assert grid[x, 0].type is None

    def test_two_consecutive_full_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test removing two consecutive full rows."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"
            grid[x, 1].type = "S"

        count = board_obj.remove_full_rows()

        assert count == 2
        for x in range(grid.width):
            assert grid[x, 0].type is None
            assert grid[x, 1].type is None

    def test_three_consecutive_full_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test removing three consecutive full rows."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"
            grid[x, 1].type = "S"
            grid[x, 2].type = "L"

        count = board_obj.remove_full_rows()

        assert count == 3

    def test_four_consecutive_full_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test removing four consecutive full rows (tetris)."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"
            grid[x, 1].type = "S"
            grid[x, 2].type = "L"
            grid[x, 3].type = "J"

        count = board_obj.remove_full_rows()

        assert count == 4

    def test_non_consecutive_full_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test that non-consecutive full rows are both detected."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"
            grid[x, 2].type = "S"

        count = board_obj.remove_full_rows()

        assert count == 2

    def test_partial_row_not_removed(self, board: tuple[Board, GameConfig]) -> None:
        """Test that a row with one empty cell is not removed."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width - 1):
            grid[x, 0].type = "T"

        count = board_obj.remove_full_rows()

        assert count == 0
        for x in range(grid.width - 1):
            assert grid[x, 0].type == "T"

    def test_row_with_active_piece_not_removed(self, board: tuple[Board, GameConfig]) -> None:
        """Test that rows with active pieces are not removed."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"

        grid[5, 0].is_active = True

        count = board_obj.remove_full_rows()

        assert count == 0


class TestRowShiftBehavior:
    """Tests for row shifting after removal."""

    @pytest.fixture
    def board(self, config: GameConfig) -> tuple[Board, GameConfig]:
        """Create a board with mocked canvas."""
        mock_parent = MagicMock()
        board = Board(config, mock_parent, config.board.width, config.board.height)
        return board, config

    def test_partial_row_not_affected_without_full_row(self, board: tuple[Board, GameConfig]) -> None:
        """Test that partial rows are not affected when no full rows exist."""
        board_obj, config = board
        grid = board_obj._game_grid

        grid[0, 0].type = "T"
        grid[1, 0].type = "S"
        grid[0, 1].type = "L"

        count = board_obj.remove_full_rows()

        assert count == 0
        assert grid[0, 0].type == "T"
        assert grid[1, 0].type == "S"
        assert grid[0, 1].type == "L"

    def test_multiple_rows_shift_correctly(self, board: tuple[Board, GameConfig]) -> None:
        """Test that pieces above a full row are preserved after clearing."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Set up a full row at y=0
        for x in range(grid.width):
            grid[x, 0].type = "T"
        # Pieces above the full row
        grid[0, 1].type = "Z"

        count = board_obj.remove_full_rows()

        assert count == 1
        assert grid[0, 0].type is None
        assert grid[0, 1].type == "Z"


class TestMixedRowConditions:
    """Tests for mixed row conditions."""

    @pytest.fixture
    def board(self, config: GameConfig) -> tuple[Board, GameConfig]:
        """Create a board with mocked canvas."""
        mock_parent = MagicMock()
        board = Board(config, mock_parent, config.board.width, config.board.height)
        return board, config

    def test_mixed_full_and_partial_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test handling of mixed full and partial rows."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Full row at y=0, partial at y=1
        for x in range(grid.width):
            grid[x, 0].type = "T"
        grid[0, 1].type = "S"

        count = board_obj.remove_full_rows()

        assert count == 1
        # Full row should be cleared
        assert grid[0, 0].type is None
        # Partial row should be preserved
        assert grid[0, 1].type == "S"

    def test_full_row_at_top_preserves_lower_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test that clearing a full row preserves rows below."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Full row at y=0, full row at y=1
        for x in range(grid.width):
            grid[x, 0].type = "T"
            grid[x, 1].type = "S"

        count = board_obj.remove_full_rows()

        assert count == 2
        # Both rows should be cleared
        for x in range(grid.width):
            assert grid[x, 0].type is None
            assert grid[x, 1].type is None

    def test_stack_preservation_after_clear(self, board: tuple[Board, GameConfig]) -> None:
        """Test that stacked pieces are preserved after row clear."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Full row at y=0, partial row at y=1
        for x in range(grid.width):
            grid[x, 0].type = "T"
        grid[0, 1].type = "S"

        count = board_obj.remove_full_rows()

        assert count == 1
        # Full row should be cleared
        assert grid[0, 0].type is None
        # Partial row should be preserved
        assert grid[0, 1].type == "S"
