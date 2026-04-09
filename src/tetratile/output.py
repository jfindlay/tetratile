"""Output handler for game observation.

This module provides output handlers that allow both human GUI
and AI agent to observe the game state simultaneously.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import GameObservation, TetraTile


class OutputHandler(ABC):
    """Abstract interface for game output (observation).

    Output handlers observe the game state without affecting gameplay.
    Both human GUI and AI agent can observe simultaneously.
    """

    @abstractmethod
    def get_observation(self) -> "GameObservation":
        """Get current game state observation.

        :returns: Current GameObservation.
        """

    @abstractmethod
    def get_events_since(self, after_index: int) -> list:
        """Get events since the given index.

        :param after_index: Index to get events after.
        :returns: List of events.
        """


class AgentOutputHandler(OutputHandler):
    """Output handler for AI agent observation.

    Provides Python API access to game state for AI agents.
    """

    def __init__(self, game: "TetraTile") -> None:
        """Initialize the output handler.

        :param game: Reference to the TetraTile game instance.
        """
        self._game = game
        self._event_index = 0

    def get_observation(self) -> "GameObservation":
        """Get current game state observation.

        :returns: Current GameObservation.
        """
        return self._game.get_observation()

    def get_events_since(self, after_index: int) -> list:
        """Get events since the given index.

        :param after_index: Index to get events after.
        :returns: List of events.
        """
        events = self._game.event_logger.get_log().events or []
        return events[after_index:]

    def reset_event_index(self) -> None:
        """Reset the event index to start from beginning."""
        self._event_index = 0

    @property
    def event_index(self) -> int:
        """Get current event index."""
        return self._event_index
