"""Integration tests for Board class."""

from unittest.mock import MagicMock

import pytest

from tetratile import Board, Grid, Square, Translation, tetrominoes
from tetratile.config import GameConfig


class TestBoardRender:
    """Tests for Board.render() functionality."""

    @pytest.fixture
    def board(self, config: GameConfig) -> Board:
        """Create a Board with a mocked parent widget."""
        mock_parent = MagicMock()
        return Board(config, mock_parent, config.board.width, config.board.height)

    @pytest.fixture
    def grid(self, config: GameConfig) -> Grid:
        """Create a fresh Grid matching the board dimensions."""
        return Grid(config.board.width, config.board.height)

    def test_render_active_piece_paints_squares(self, board: Board, grid: Grid) -> None:
        """Rendering an active piece paints its squares onto the canvas."""
        piece = tetrominoes[3]  # T piece
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        board.render(grid, moved)

        for s in moved.squares:
            assert s in board._canvas_ids

    def test_render_clear_removes_active_squares(self, board: Board, grid: Grid) -> None:
        """Rendering with no active piece removes previously painted squares."""
        piece = tetrominoes[3]
        moved = piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        board.render(grid, moved)
        board.render(grid, None)  # clear active piece

        for s in moved.squares:
            assert s not in board._canvas_ids

    def test_render_locked_piece_from_grid(self, board: Board, grid: Grid) -> None:
        """Squares committed to the grid are rendered as locked pieces when locked_dirty=True."""
        for s in grid:
            if s.x < 2 and s.y < 2:
                grid[s] = "T"

        board.render(grid, None, locked_dirty=True)

        for s in grid._occupancy:
            assert s in board._canvas_ids

    def test_render_all_tetromino_types(self, board: Board, grid: Grid) -> None:
        """All tetromino types render without error."""
        for piece_type in tetrominoes:
            moved = piece_type.translate(Translation(grid.width // 2, grid.height // 2), grid)
            assert moved is not None
            board.render(grid, moved)
            board.render(grid, None)

    def test_clear_removes_all_canvas_items(self, board: Board, grid: Grid) -> None:
        """board.clear() removes all drawn canvas items."""
        for piece_type in tetrominoes:
            moved = piece_type.translate(Translation(grid.width // 2, grid.height // 2), grid)
            if moved is not None:
                board.render(grid, moved)

        board.clear()

        assert len(board._canvas_ids) == 0


class TestBoardHighlightFullRows:
    """Tests for full row detection via Board.highlight_full_rows()."""

    @pytest.fixture
    def board(self, config: GameConfig) -> Board:
        """Create a board with mocked canvas."""
        mock_parent = MagicMock()
        return Board(config, mock_parent, config.board.width, config.board.height)

    @pytest.fixture
    def grid(self, config: GameConfig) -> Grid:
        """Create a fresh Grid."""
        return Grid(config.board.width, config.board.height)

    def test_detects_complete_row(self, board: Board, grid: Grid) -> None:
        """highlight_full_rows returns [0] for a full bottom row."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"

        full_rows = board.highlight_full_rows(grid)

        assert full_rows == [0]

    def test_ignores_partial_row(self, board: Board, grid: Grid) -> None:
        """highlight_full_rows returns [] for a partial row."""
        for x in range(grid.width - 1):
            grid[Square(x, 0)] = "T"

        full_rows = board.highlight_full_rows(grid)

        assert full_rows == []

    def test_detects_multiple_full_rows(self, board: Board, grid: Grid) -> None:
        """highlight_full_rows detects two full rows."""
        for x in range(grid.width):
            grid[Square(x, 0)] = "T"
            grid[Square(x, 1)] = "T"

        full_rows = board.highlight_full_rows(grid)

        assert sorted(full_rows) == [0, 1]
