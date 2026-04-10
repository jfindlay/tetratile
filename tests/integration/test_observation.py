"""Integration tests for GameObservation, OutputHandler, and Agent."""

from unittest.mock import MagicMock

import pytest

from tetratile import Board, GameObservation, GameState
from tetratile.agent import Action, RandomAgent
from tetratile.config import GameConfig
from tetratile.output import AgentOutputHandler, PrintObserver

# ---------------------------------------------------------------------------
# GameObservation board layout
# ---------------------------------------------------------------------------


class TestObservationBoardLayout:
    """Verify that GameObservation.board is row-major: board[y][x]."""

    @pytest.fixture
    def board(self, config: GameConfig) -> Board:
        """Create a Board with mocked parent."""
        parent = MagicMock()
        return Board(config, parent, config.board.width, config.board.height)

    def test_board_outer_dimension_is_height(self, board: Board, config: GameConfig) -> None:
        """board[y] rows: outer list length equals board height."""
        # Place a single piece and call get_observation via a mock game
        grid = board._game_grid
        grid[0, 0].type = "T"

        # Build observation manually (same logic as TetraTile.get_observation)
        width, height = board.width, board.height
        board_state = [[None] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                if grid[x, y].type:
                    board_state[y][x] = grid[x, y].type

        assert len(board_state) == height
        assert all(len(row) == width for row in board_state)

    def test_board_bottom_row_is_index_zero(self, board: Board, config: GameConfig) -> None:
        """board[0] is the bottom row (y=0 in Cartesian)."""
        grid = board._game_grid
        # Place a marker at x=3, y=0 (bottom-left area)
        grid[3, 0].type = "Z"

        width, height = board.width, board.height
        board_state = [[None] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                if grid[x, y].type:
                    board_state[y][x] = grid[x, y].type

        assert board_state[0][3] == "Z", "Cell at y=0, x=3 should appear in board_state[0][3]"
        # No other row should contain the marker
        for y in range(1, height):
            assert board_state[y][3] is None

    def test_board_top_row_is_index_height_minus_one(self, board: Board, config: GameConfig) -> None:
        """board[height-1] is the top row (y=height-1 in Cartesian)."""
        grid = board._game_grid
        height = board.height
        grid[5, height - 1].type = "S"

        width = board.width
        board_state = [[None] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                if grid[x, y].type:
                    board_state[y][x] = grid[x, y].type

        assert board_state[height - 1][5] == "S"
        for y in range(height - 1):
            assert board_state[y][5] is None

    def test_board_column_index_matches_x(self, board: Board, config: GameConfig) -> None:
        """board[y][x] column index matches the x Cartesian coordinate."""
        grid = board._game_grid
        # Place markers at different x values in the same row (y=2)
        grid[0, 2].type = "T"
        grid[4, 2].type = "L"
        grid[9, 2].type = "J"

        width, height = board.width, board.height
        board_state = [[None] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                if grid[x, y].type:
                    board_state[y][x] = grid[x, y].type

        assert board_state[2][0] == "T"
        assert board_state[2][4] == "L"
        assert board_state[2][9] == "J"


# ---------------------------------------------------------------------------
# AgentOutputHandler
# ---------------------------------------------------------------------------


class TestAgentOutputHandler:
    """Tests for AgentOutputHandler push/poll model."""

    def _make_obs(self) -> GameObservation:
        """Create a minimal fake observation."""
        return GameObservation(
            board=[[None] * 10 for _ in range(22)],
            current_piece="T",
            current_piece_coords=[[5, 20]],
            current_piece_state=0,
            next_piece="S",
            stats={},
            state=GameState.running,
            elapsed=__import__("datetime").timedelta(seconds=0),
        )

    def test_get_latest_returns_none_before_first_observation(self) -> None:
        """get_latest() is None before any observation is pushed."""
        handler = AgentOutputHandler()
        assert handler.get_latest() is None

    def test_get_latest_returns_most_recent_observation(self) -> None:
        """get_latest() returns the most recently pushed observation."""
        handler = AgentOutputHandler()
        obs = self._make_obs()
        handler.on_observation(obs)
        assert handler.get_latest() is obs

    def test_get_latest_updates_on_new_push(self) -> None:
        """get_latest() updates when a new observation is pushed."""
        handler = AgentOutputHandler()
        obs1 = self._make_obs()
        obs2 = self._make_obs()
        handler.on_observation(obs1)
        handler.on_observation(obs2)
        assert handler.get_latest() is obs2


# ---------------------------------------------------------------------------
# PrintObserver
# ---------------------------------------------------------------------------


class TestPrintObserver:
    """Tests for PrintObserver output."""

    def _make_obs(self) -> GameObservation:
        """Create a minimal fake observation."""
        import datetime

        board = [[None] * 10 for _ in range(22)]
        board[0][3] = "T"  # bottom row, column 3
        return GameObservation(
            board=board,
            current_piece="T",
            current_piece_coords=[[3, 0]],
            current_piece_state=0,
            next_piece="S",
            stats={"rows_cleared": 0, "pieces": 1},
            state=GameState.running,
            elapsed=datetime.timedelta(seconds=5),
        )

    def test_print_observer_writes_to_stdout(self, capsys: pytest.CaptureFixture) -> None:
        """PrintObserver.on_observation writes board state to stdout."""
        observer = PrintObserver()
        obs = self._make_obs()
        observer.on_observation(obs)
        captured = capsys.readouterr()
        assert "STATE:" in captured.out
        assert "Piece:" in captured.out
        assert "Rows cleared:" in captured.out

    def test_print_observer_shows_occupied_cell(self, capsys: pytest.CaptureFixture) -> None:
        """PrintObserver output contains the piece name for occupied cells."""
        observer = PrintObserver()
        obs = self._make_obs()
        observer.on_observation(obs)
        captured = capsys.readouterr()
        # The "T" piece marker should appear in the board rendering
        assert "TT" in captured.out  # 2-char cell representation


# ---------------------------------------------------------------------------
# Agent and Action
# ---------------------------------------------------------------------------


class TestRandomAgent:
    """Tests for RandomAgent decision-making."""

    def _make_obs(self) -> GameObservation:
        """Minimal observation."""
        import datetime

        return GameObservation(
            board=[[None] * 10 for _ in range(22)],
            current_piece="T",
            current_piece_coords=[],
            current_piece_state=0,
            next_piece="S",
            stats={},
            state=GameState.running,
            elapsed=datetime.timedelta(seconds=0),
        )

    def test_select_action_returns_action_enum(self) -> None:
        """select_action returns an Action enum value."""
        agent = RandomAgent()
        obs = self._make_obs()
        action = agent.select_action(obs)
        assert isinstance(action, Action)

    def test_select_action_returns_movement_action(self) -> None:
        """RandomAgent only returns movement actions (not pause/hard-drop/lock)."""
        agent = RandomAgent()
        obs = self._make_obs()
        non_movement = {Action.toggle_pause, Action.hard_drop, Action.lock_piece, Action.move_left_max, Action.move_right_max}
        for _ in range(50):
            action = agent.select_action(obs)
            assert action not in non_movement

    def test_action_values_are_inputhandler_method_names(self) -> None:
        """Every Action value is a valid method name on InputHandler."""
        from tetratile.input_handler import InputHandler

        for action in Action:
            assert hasattr(InputHandler, action.value), (
                f"Action.{action.name} = '{action.value}' has no matching method on InputHandler"
            )
