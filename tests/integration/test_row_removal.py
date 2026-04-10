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
        """Test that pieces above a full row shift down after clearing."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Set up a full row at y=0
        for x in range(grid.width):
            grid[x, 0].type = "T"
        # Piece above the full row — should shift down by 1
        grid[0, 1].type = "Z"

        count = board_obj.remove_full_rows()

        assert count == 1
        # Z shifted down from y=1 to y=0
        assert grid[0, 0].type == "Z"
        # y=1 is now empty
        assert grid[0, 1].type is None

    def test_overburden_shifts_two_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test that overburden shifts down by 2 when two full rows are cleared."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Two full rows at y=0 and y=1, partial rows above
        for x in range(grid.width):
            grid[x, 0].type = "T"
            grid[x, 1].type = "S"
        grid[0, 2].type = "Z"
        grid[0, 3].type = "L"

        count = board_obj.remove_full_rows()

        assert count == 2
        # Z shifts from y=2 to y=0, L shifts from y=3 to y=1
        assert grid[0, 0].type == "Z"
        assert grid[0, 1].type == "L"
        assert grid[0, 2].type is None
        assert grid[0, 3].type is None

    def test_overburden_non_consecutive_full_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test overburden shifts correctly with non-consecutive full rows."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Partial at y=0, full at y=1, partial at y=2, full at y=3, partial at y=4
        grid[0, 0].type = "Z"
        for x in range(grid.width):
            grid[x, 1].type = "T"
        grid[0, 2].type = "S"
        for x in range(grid.width):
            grid[x, 3].type = "J"
        grid[0, 4].type = "L"

        count = board_obj.remove_full_rows()

        assert count == 2
        # y=0 partial (Z): 0 full rows below it -> stays at y=0
        assert grid[0, 0].type == "Z"
        # y=2 partial (S): 1 full row below it (y=1) -> shifts to y=1
        assert grid[0, 1].type == "S"
        # y=4 partial (L): 2 full rows below it (y=1,y=3) -> shifts to y=2
        assert grid[0, 2].type == "L"
        assert grid[0, 3].type is None
        assert grid[0, 4].type is None


class TestMixedRowConditions:
    """Tests for mixed row conditions."""

    @pytest.fixture
    def board(self, config: GameConfig) -> tuple[Board, GameConfig]:
        """Create a board with mocked canvas."""
        mock_parent = MagicMock()
        board = Board(config, mock_parent, config.board.width, config.board.height)
        return board, config

    def test_mixed_full_and_partial_rows(self, board: tuple[Board, GameConfig]) -> None:
        """Test that partial rows above a full row shift down after clearing."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Full row at y=0, partial at y=1
        for x in range(grid.width):
            grid[x, 0].type = "T"
        grid[0, 1].type = "S"

        count = board_obj.remove_full_rows()

        assert count == 1
        # S shifted down from y=1 to y=0
        assert grid[0, 0].type == "S"
        # y=1 is now empty
        assert grid[0, 1].type is None

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
        """Test that stacked pieces shift down correctly after row clear."""
        board_obj, config = board
        grid = board_obj._game_grid

        # Full row at y=0, partial row at y=1, another partial at y=2
        for x in range(grid.width):
            grid[x, 0].type = "T"
        grid[0, 1].type = "S"
        grid[0, 2].type = "L"

        count = board_obj.remove_full_rows()

        assert count == 1
        # S shifted from y=1 to y=0, L shifted from y=2 to y=1
        assert grid[0, 0].type == "S"
        assert grid[0, 1].type == "L"
        assert grid[0, 2].type is None
