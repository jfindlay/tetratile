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


class TestBoardRenderDelta:
    """Tests for the targeted (delta) rendering behaviour of Board.render().

    Verifies that:
    - Active-piece squares are painted and erased correctly without touching
      locked squares that did not change.
    - Locked squares are only repainted when ``locked_dirty=True``.
    - Moving the active piece only modifies the vacated and newly-occupied squares.
    """

    @pytest.fixture
    def board(self, config: GameConfig) -> Board:
        """Create a Board with a mocked parent widget."""
        mock_parent = MagicMock()
        return Board(config, mock_parent, config.board.width, config.board.height)

    @pytest.fixture
    def grid(self, config: GameConfig) -> Grid:
        """Create a fresh Grid."""
        return Grid(config.board.width, config.board.height)

    def test_locked_squares_not_painted_without_locked_dirty(
        self, board: Board, grid: Grid
    ) -> None:
        """Locked squares in grid are NOT painted when locked_dirty is False (default)."""
        grid[Square(0, 0)] = "T"
        grid[Square(1, 0)] = "T"

        board.render(grid, None)  # locked_dirty=False by default

        assert Square(0, 0) not in board._canvas_ids
        assert Square(1, 0) not in board._canvas_ids

    def test_locked_squares_painted_with_locked_dirty(self, board: Board, grid: Grid) -> None:
        """Locked squares in grid ARE painted when locked_dirty=True."""
        grid[Square(0, 0)] = "T"
        grid[Square(1, 0)] = "T"

        board.render(grid, None, locked_dirty=True)

        assert Square(0, 0) in board._canvas_ids
        assert Square(1, 0) in board._canvas_ids

    def test_moving_piece_erases_vacated_squares(self, board: Board, grid: Grid) -> None:
        """After the piece moves right, the vacated left squares are erased."""
        piece = tetrominoes[3]  # T piece
        pos1 = piece.translate(Translation(4, 11), grid)
        assert pos1 is not None

        board.render(grid, pos1)
        squares_before = set(pos1.squares)

        pos2 = pos1.translate(Translation(1, 0), grid)
        assert pos2 is not None
        board.render(grid, pos2)

        vacated = squares_before - pos2.squares
        still_active = squares_before & pos2.squares

        # Vacated squares must be erased (not in canvas_ids)
        for s in vacated:
            assert s not in board._canvas_ids, f"Vacated square {s} still on canvas"

        # Squares still under the piece must remain painted
        for s in still_active:
            assert s in board._canvas_ids, f"Persistent square {s} was erased"

    def test_active_piece_tracking_updated_after_render(self, board: Board, grid: Grid) -> None:
        """_active_squares is updated to the new piece position after render."""
        piece = tetrominoes[3]
        pos1 = piece.translate(Translation(4, 11), grid)
        assert pos1 is not None

        board.render(grid, pos1)
        assert board._active_squares == pos1.squares

        pos2 = pos1.translate(Translation(1, 0), grid)
        assert pos2 is not None
        board.render(grid, pos2)
        assert board._active_squares == pos2.squares

    def test_clear_resets_active_squares(self, board: Board, grid: Grid) -> None:
        """board.clear() resets _active_squares to the empty frozenset."""
        piece = tetrominoes[3]
        moved = piece.translate(Translation(4, 11), grid)
        assert moved is not None

        board.render(grid, moved)
        assert len(board._active_squares) > 0

        board.clear()
        assert board._active_squares == frozenset()

    def test_locked_dirty_erases_stale_locked_squares(self, board: Board, grid: Grid) -> None:
        """When locked_dirty=True, squares removed from the grid are erased."""
        # Paint two squares as locked
        grid[Square(0, 0)] = "T"
        grid[Square(1, 0)] = "T"
        board.render(grid, None, locked_dirty=True)
        assert Square(0, 0) in board._canvas_ids
        assert Square(1, 0) in board._canvas_ids

        # Remove one square from grid, re-render with locked_dirty
        grid[Square(0, 0)] = None
        board.render(grid, None, locked_dirty=True)

        assert Square(0, 0) not in board._canvas_ids
        assert Square(1, 0) in board._canvas_ids
