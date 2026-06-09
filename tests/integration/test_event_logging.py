"""Integration tests for event logging."""

import datetime as dt
from pathlib import Path

from pyfakefs.fake_filesystem import FakeFilesystem

from tetratile.config import GameConfig
from tetratile.event_log import EventLogger, EventType, GameLog


class TestEventLogging:
    """Tests for event logging functionality."""

    def test_logger_starts_with_game_start_event(self) -> None:
        """Test that starting a log records initial state."""
        logger = EventLogger()
        config = GameConfig()

        logger.start(config)

        log = logger.get_log()
        assert log.game_id is not None
        assert log.timestamp_start is not None
        assert log.seed is not None

    def test_log_spawn_event(self) -> None:
        """Test logging a piece spawn event."""
        logger = EventLogger()
        logger.start(GameConfig())

        logger.log(EventType.piece_spawn, piece_type="T")

        log = logger.get_log()
        assert log.events is not None
        assert len(log.events) == 1
        assert log.events[0].type == EventType.piece_spawn
        assert log.events[0].piece_type == "T"

    def test_log_move_event(self) -> None:
        """Test logging a piece move event."""
        logger = EventLogger()
        logger.start(GameConfig())

        logger.log(EventType.piece_move, piece_type="T", direction="left")

        log = logger.get_log()
        assert log.events is not None
        assert len(log.events) == 1
        assert log.events[0].type == EventType.piece_move
        assert log.events[0].piece_type == "T"
        assert log.events[0].direction == "left"

    def test_log_rotate_event(self) -> None:
        """Test logging a piece rotation event."""
        logger = EventLogger()
        logger.start(GameConfig())

        logger.log(EventType.piece_rotate, piece_type="T", direction="CW")

        log = logger.get_log()
        assert log.events is not None
        assert len(log.events) == 1
        assert log.events[0].type == EventType.piece_rotate
        assert log.events[0].direction == "CW"

    def test_log_lock_event(self) -> None:
        """Test logging a piece lock event."""
        logger = EventLogger()
        logger.start(GameConfig())

        logger.log(EventType.piece_lock, piece_type="T")

        log = logger.get_log()
        assert log.events is not None
        assert len(log.events) == 1
        assert log.events[0].type == EventType.piece_lock
        assert log.events[0].piece_type == "T"

    def test_log_row_clear_event(self) -> None:
        """Test logging a row clear event."""
        logger = EventLogger()
        logger.start(GameConfig())

        logger.log(EventType.row_clear, count=2)

        log = logger.get_log()
        assert log.events is not None
        assert len(log.events) == 1
        assert log.events[0].type == EventType.row_clear
        assert log.events[0].count == 2

    def test_multiple_events_in_order(self) -> None:
        """Test that multiple events are logged in order."""
        logger = EventLogger()
        logger.start(GameConfig())

        logger.log(EventType.piece_spawn, piece_type="T")
        logger.log(EventType.piece_move, piece_type="T", direction="left")
        logger.log(EventType.piece_rotate, piece_type="T", direction="CW")
        logger.log(EventType.piece_lock, piece_type="T")

        log = logger.get_log()
        assert log.events is not None
        assert len(log.events) == 4
        assert log.events[0].type == EventType.piece_spawn
        assert log.events[1].type == EventType.piece_move
        assert log.events[2].type == EventType.piece_rotate
        assert log.events[3].type == EventType.piece_lock

    def test_elapsed_time_increments(self) -> None:
        """Test that elapsed time is recorded."""
        logger = EventLogger()
        logger.start(GameConfig())

        logger._elapsed_ms = 100
        logger.log(EventType.piece_spawn, piece_type="T")
        logger._elapsed_ms = 200
        logger.log(EventType.piece_lock, piece_type="T")

        log = logger.get_log()
        assert log.events is not None
        assert log.events[0].elapsed == dt.timedelta(milliseconds=100)
        assert log.events[1].elapsed == dt.timedelta(milliseconds=200)

    def test_stop_records_stats(self) -> None:
        """Test that stopping records final stats."""
        from tetratile import GameStats

        logger = EventLogger()
        logger.start(GameConfig())

        stats = GameStats(pieces=10, rows_cleared=5, rows_by_count=[], pieces_by_type={})
        logger.stop(stats)

        log = logger.get_log()
        assert log.stats is not None
        assert log.stats["pieces"] == 10
        assert log.stats["rows_cleared"] == 5
        assert log.timestamp_end is not None

    def test_json_serialization_roundtrip(self) -> None:
        """Test JSON serialization and deserialization."""
        logger = EventLogger()
        logger.start(GameConfig())
        logger.log(EventType.piece_spawn, piece_type="T")
        logger.log(EventType.piece_move, piece_type="T", direction="left")
        logger.log(EventType.row_clear, count=1)
        from tetratile import GameStats

        logger.stop(GameStats(pieces=1, rows_cleared=1, rows_by_count=[], pieces_by_type={}))

        json_str = logger.to_json()
        restored = GameLog.from_json(json_str)

        assert restored.game_id == logger.get_log().game_id
        assert restored.events is not None
        assert len(restored.events) == 3
        assert restored.events[0].type == EventType.piece_spawn
        assert restored.events[1].type == EventType.piece_move
        assert restored.events[2].type == EventType.row_clear
        assert restored.stats is not None
        assert restored.stats["pieces"] == 1
        assert restored.stats["rows_cleared"] == 1

    def test_save_to_file(self, fs: FakeFilesystem) -> None:
        """Test saving event log to filesystem."""
        from tetratile import GameStats

        log_dir = Path("/fake/logs")
        logger = EventLogger(log_dir=log_dir)
        logger.start(GameConfig())
        logger.log(EventType.piece_spawn, piece_type="T")
        logger.stop(GameStats(pieces=1, rows_cleared=0, rows_by_count=[], pieces_by_type={}))

        path = logger.save()

        assert path.parent == log_dir
        assert fs.exists(str(path))
        assert "T" in path.read_text()

    def test_config_saved_in_log(self) -> None:
        """Test that game config is saved with the log."""
        config = GameConfig()
        config.board.width = 15
        config.board.height = 25

        logger = EventLogger()
        logger.start(config)

        from typing import cast

        log = logger.get_log()
        assert log.config is not None
        board_cfg = cast(dict[str, object], log.config["board"])
        assert board_cfg["width"] == 15
        assert board_cfg["height"] == 25

    def test_seed_reproducibility(self) -> None:
        """Test that seed is recorded for reproducibility."""
        logger = EventLogger()
        logger.start(GameConfig(), seed=12345)

        log = logger.get_log()
        assert log.seed == 12345
