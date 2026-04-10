"""Event logging for game replay and analysis."""

from __future__ import annotations

import enum
import json
import random
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import GameConfig


class EventType(enum.Enum):
    """Types of events that can be logged during gameplay."""

    game_start = enum.auto()
    game_pause = enum.auto()
    game_resume = enum.auto()
    game_over = enum.auto()
    piece_spawn = enum.auto()
    piece_move = enum.auto()
    piece_rotate = enum.auto()
    piece_lock = enum.auto()
    row_clear = enum.auto()
    rate_change = enum.auto()


@dataclass
class Event:
    """A single event in the game log.

    :attr elapsed: Time since game start as timedelta.
    :attr type: The type of event.
    :attr piece_type: Tetromino type (Z, S, l, T, o, L, J).
    :attr col: Column position.
    :attr rot: Rotation state.
    :attr direction: Direction of movement (left, right, down, CW, CCW).
    :attr count: Count of rows cleared or other quantity.
    :attr reason: Reason for game over or other event.
    """

    elapsed: timedelta = timedelta()
    type: EventType = EventType.game_start
    piece_type: str | None = None
    col: int | None = None
    rot: int | None = None
    direction: str | None = None
    count: int | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for JSON serialization.

        :returns: Dictionary with event data.
        """
        d = asdict(self)
        d["type"] = self.type.name
        base = datetime.min + self.elapsed
        d["elapsed"] = base.strftime("%M:%S.%f")[:-3]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        """Create event from dictionary.

        :param data: Dictionary with event data.
        :returns: Event instance.
        """
        elapsed_str = data.get("elapsed", "00:00.000")
        parts = elapsed_str.split(":")
        minutes = int(parts[0])
        sec_ms = parts[1].split(".")
        seconds = int(sec_ms[0])
        ms = int(sec_ms[1]) if len(sec_ms) > 1 else 0
        return cls(
            elapsed=timedelta(minutes=minutes, seconds=seconds, milliseconds=ms),
            type=EventType[data["type"]],
            piece_type=data.get("piece_type") or None,
            col=data.get("col") or None,
            rot=data.get("rot") or None,
            direction=data.get("direction") or None,
            count=data.get("count") or None,
            reason=data.get("reason") or None,
        )


@dataclass
class GameLog:
    """Complete game log with metadata and events.

    :attr version: Log format version.
    :attr game_id: Unique identifier for this game.
    :attr timestamp_start: ISO timestamp when game started.
    :attr timestamp_end: ISO timestamp when game ended.
    :attr seed: Random seed for reproducibility.
    :attr config: Game configuration snapshot.
    :attr events: List of game events.
    :attr stats: Final game statistics.
    """

    version: str = "1.0"
    game_id: str = ""
    timestamp_start: str = ""
    timestamp_end: str = ""
    seed: int = 0
    config: dict[str, Any] | None = None
    events: list[Event] | None = None
    stats: dict[str, Any] | None = None

    def to_json(self) -> str:
        """Serialize log to JSON string.

        :returns: JSON string representation.
        """
        data = {
            "version": self.version,
            "game_id": self.game_id,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "seed": self.seed,
            "config": self.config,
            "events": [e.to_dict() for e in (self.events or [])],
            "stats": self.stats,
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, data: str) -> GameLog:
        """Deserialize log from JSON string.

        :param data: JSON string.
        :returns: GameLog instance.
        """
        d = json.loads(data)
        events = [Event.from_dict(e) for e in d.get("events", [])]
        return cls(
            version=d["version"],
            game_id=d["game_id"],
            timestamp_start=d["timestamp_start"],
            timestamp_end=d.get("timestamp_end", ""),
            seed=d["seed"],
            config=d.get("config"),
            events=events,
            stats=d.get("stats"),
        )


class EventLogger:
    """Logger for capturing game events.

    :attr _log: The game log being built.
    :attr _start_time: Timestamp when logging began.
    :attr _log_dir: Directory for saving logs.
    :attr _elapsed_ms: Accumulated elapsed time.
    :attr _paused_ms: Time spent paused.
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        """Initialize the event logger.

        :param log_dir: Directory to save logs. Defaults to XDG data dir.
        """
        self._log_dir = log_dir
        self._log: GameLog = GameLog()
        self._start_time: datetime | None = None
        self._elapsed_ms: int = 0
        self._paused_ms: int = 0

    def start(self, config: GameConfig, seed: int | None = None) -> None:
        """Start a new game log.

        :param config: Game configuration.
        :param seed: Random seed for reproducibility.
        """
        self._log = GameLog()
        self._log.game_id = str(uuid.uuid4())[:8]
        self._log.config = config.model_dump(exclude={"config_file", "keys"})
        self._log.events = []
        self._log.stats = None
        self._seed = seed if seed is not None else random.getrandbits(32)
        self._log.seed = self._seed
        self._start_time = datetime.now(UTC)
        self._log.timestamp_start = self._start_time.isoformat()
        self._elapsed_ms = 0
        self._paused_ms = 0

    def stop(self, stats: dict[str, Any]) -> None:
        """End the current game log.

        :param stats: Final game statistics.
        """
        self._log.stats = stats
        self._log.timestamp_end = datetime.now(UTC).isoformat()

    def log(
        self,
        event_type: EventType,
        *,
        piece_type: str | None = None,
        col: int | None = None,
        rot: int | None = None,
        direction: str | None = None,
        count: int | None = None,
        reason: str | None = None,
    ) -> None:
        """Log a game event.

        :param event_type: Type of event.
        :param piece_type: Tetromino type.
        :param col: Column position.
        :param rot: Rotation state.
        :param direction: Direction of movement.
        :param count: Count of rows cleared or other quantity.
        :param reason: Reason for game over or other event.
        """
        if self._log.events is None:
            self._log.events = []
        event = Event(
            elapsed=timedelta(milliseconds=self._elapsed_ms),
            type=event_type,
            piece_type=piece_type,
            col=col,
            rot=rot,
            direction=direction,
            count=count,
            reason=reason,
        )
        self._log.events.append(event)

    def update_time(self, elapsed_ms: int, paused_ms: int) -> None:
        """Update elapsed time counters.

        :param elapsed_ms: Current elapsed time in ms.
        :param paused_ms: Time spent paused in ms.
        """
        self._elapsed_ms = elapsed_ms
        self._paused_ms = paused_ms

    def get_log(self) -> GameLog:
        """Get the current game log.

        :returns: The game log.
        """
        return self._log

    def to_json(self) -> str:
        """Serialize log to JSON.

        :returns: JSON string.
        """
        return self._log.to_json()

    def save(self, path: Path | None = None) -> Path:
        """Save log to file.

        :param path: Path to save to. If None, uses default location.
        :returns: Path where file was saved.
        """
        if path is None:
            if self._log_dir is None:
                self._log_dir = self._get_default_log_dir()
            path = self._log_dir / f"game_{self._log.game_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())
        return path

    @staticmethod
    def _get_default_log_dir() -> Path:
        """Get default log directory.

        :returns: Path to default log directory.
        """
        return Path.cwd()
