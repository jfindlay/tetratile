"""Integration tests for Board class."""

import copy
from unittest.mock import MagicMock

import pytest

from tetratile import Board, tetrominoes
from tetratile.config import GameConfig


class TestBoardUpdate:
    """Tests for Board.update() functionality."""

    @pytest.fixture
    def board(self, config: GameConfig) -> tuple[Board, GameConfig]:
        """Create a board with mocked canvas.

        Returns the board's internal grid as the board object itself.
        """
        mock_parent = MagicMock()
        board = Board(config, mock_parent, config.board.width, config.board.height)
        return board, config

    def test_update_places_all_tetromino_squares(self, board: tuple[Board, GameConfig]) -> None:
        """Test that Board.update places all 4 squares of a tetromino."""
        board_obj, config = board
        grid = board_obj._game_grid

        tetromino = copy.deepcopy(tetrominoes[3])  # T piece
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        board_obj.update(tetromino)

        for coord in tetromino.coords:
            square = grid[coord]
            assert square.type == tetromino.name
            assert square.id is not None
            assert square.colors is not None

    def test_update_clears_all_tetromino_squares(self, board: tuple[Board, GameConfig]) -> None:
        """Test that Board.update with clear=True removes all squares."""
        board_obj, config = board
        grid = board_obj._game_grid

        tetromino = copy.deepcopy(tetrominoes[3])  # T piece
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        board_obj.update(tetromino)
        board_obj.update(tetromino, clear=True)

        for coord in tetromino.coords:
            square = grid[coord]
            assert square.type is None
            assert square.id is None
            assert square.colors is None

    def test_update_is_active_flag(self, board: tuple[Board, GameConfig]) -> None:
        """Test that is_active flag is set correctly."""
        board_obj, config = board
        grid = board_obj._game_grid

        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        board_obj.update(tetromino, is_active=True)
        for coord in tetromino.coords:
            assert grid[coord].is_active is True

        board_obj.update(tetromino, clear=True)
        board_obj.update(tetromino, is_active=False)
        for coord in tetromino.coords:
            assert grid[coord].is_active is False

    def test_update_all_tetromino_types(self, board: tuple[Board, GameConfig]) -> None:
        """Test that all tetromino types are placed correctly."""
        board_obj, config = board
        grid = board_obj._game_grid

        for tetromino_type in tetrominoes:
            tetromino = copy.deepcopy(tetromino_type)
            tetromino.translate([grid.width // 2, grid.height // 2], grid)

            board_obj.update(tetromino)

            for coord in tetromino.coords:
                assert grid[coord].type == tetromino.name
                assert grid[coord].id is not None

            board_obj.update(tetromino, clear=True)

    def test_clear_removes_all_squares(self, board: tuple[Board, GameConfig]) -> None:
        """Test that clear() removes all squares from board."""
        board_obj, config = board
        grid = board_obj._game_grid

        for tetromino_type in tetrominoes:
            tetromino = copy.deepcopy(tetromino_type)
            tetromino.translate([grid.width // 2, grid.height // 2], grid)
            board_obj.update(tetromino)
            board_obj.update(tetromino, clear=True)

        board_obj.clear()

        for v in grid:
            square = grid[v]
            assert square.type is None
            assert square.id is None


class TestBoardFullRows:
    """Tests for full row detection."""

    @pytest.fixture
    def board(self, config: GameConfig) -> tuple[Board, GameConfig]:
        """Create a board with mocked canvas."""
        mock_parent = MagicMock()
        board = Board(config, mock_parent, config.board.width, config.board.height)
        return board, config

    def test_select_full_row_detects_complete_row(self, board: tuple[Board, GameConfig]) -> None:
        """Test that select_full_rows detects a complete row."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"

        result = board_obj.select_full_rows()

        assert result is True

    def test_select_full_row_ignores_partial_row(self, board: tuple[Board, GameConfig]) -> None:
        """Test that select_full_rows ignores incomplete rows."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width - 1):
            grid[x, 0].type = "T"

        result = board_obj.select_full_rows()

        assert result is False

    def test_select_full_rows_finds_multiple(self, board: tuple[Board, GameConfig]) -> None:
        """Test detecting multiple full rows."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"
            grid[x, 1].type = "T"

        result = board_obj.select_full_rows()

        assert result is True

    def test_remove_full_rows_clears_only_full(self, board: tuple[Board, GameConfig]) -> None:
        """Test that remove_full_rows clears only full rows."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 0].type = "T"

        grid[0, 1].type = "Z"

        board_obj.remove_full_rows()

        for x in range(grid.width):
            assert grid[x, 0].type is None

        assert grid[0, 1].type == "Z"

    def test_remove_full_rows_shifts_upper_rows_down(self, board: tuple[Board, GameConfig]) -> None:
        """Test that rows above cleared rows shift down."""
        board_obj, config = board
        grid = board_obj._game_grid

        for x in range(grid.width):
            grid[x, 1].type = "T"

        board_obj.remove_full_rows()

        for x in range(grid.width):
            assert grid[x, 1].type is None
            assert grid[x, 0].type is None
