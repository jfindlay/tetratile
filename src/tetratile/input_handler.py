"""Abstract input handler for game control.

This module provides the interface for different input sources (human keyboard or AI agent).
Both frontends use identical input methods, ensuring parity between human and agent control.
"""

from abc import ABC, abstractmethod


class InputHandler(ABC):
    """Abstract interface for game input.

    Input handlers translate external commands (key presses or API calls)
    into game actions. Both human and agent handlers implement this interface
    to ensure identical game behavior regardless of input source.

    :attr game: Reference to the TetraTile game instance.
    """

    def __init__(self, game: "TetraTile") -> None:
        """Initialize the input handler.

        :param game: Reference to the TetraTile game instance.
        """
        self._game = game

    @abstractmethod
    def move_left(self) -> bool:
        """Move the current piece one step left.

        :returns: True if move was successful.
        """

    @abstractmethod
    def move_right(self) -> bool:
        """Move the current piece one step right.

        :returns: True if move was successful.
        """

    @abstractmethod
    def rotate_cw(self) -> bool:
        """Rotate the current piece clockwise.

        :returns: True if rotation was successful.
        """

    @abstractmethod
    def rotate_ccw(self) -> bool:
        """Rotate the current piece counter-clockwise.

        :returns: True if rotation was successful.
        """

    @abstractmethod
    def soft_drop(self) -> bool:
        """Move the current piece one step down (soft drop).

        :returns: True if move was successful.
        """

    @abstractmethod
    def hard_drop(self) -> None:
        """Drop the current piece to the bottom immediately."""

    @abstractmethod
    def move_left_max(self) -> None:
        """Move the current piece to the left edge (max translation)."""

    @abstractmethod
    def move_right_max(self) -> None:
        """Move the current piece to the right edge (max translation)."""

    @abstractmethod
    def toggle_pause(self) -> None:
        """Toggle the game pause state."""

    @abstractmethod
    def lock_piece(self) -> None:
        """Lock the current piece in place without dropping."""
