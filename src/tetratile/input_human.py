"""Human input handler for game control.

This module provides the human input handler that wraps existing
tkinter key binding methods, implementing the InputHandler interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .input_handler import InputHandler

if TYPE_CHECKING:
    pass

# Imported at bottom to avoid circular import
from . import EigenTransformation, GameState, Transformation  # noqa: E402


class HumanInputHandler(InputHandler):
    """Input handler for human keyboard control.

    Wraps existing tkinter event handlers to implement the InputHandler
    interface, ensuring identical game behavior whether input comes from
    human keyboard or AI agent.
    """

    def move_left(self) -> bool:
        """Move the current piece one step left.

        :returns: True if move was successful.
        """
        if self._game.state == GameState.running:
            return bool(self._game.move_piece(Transformation(EigenTransformation.horizontal, -1)))
        return False

    def move_right(self) -> bool:
        """Move the current piece one step right.

        :returns: True if move was successful.
        """
        if self._game.state == GameState.running:
            return bool(self._game.move_piece(Transformation(EigenTransformation.horizontal, 1)))
        return False

    def rotate_cw(self) -> bool:
        """Rotate the current piece clockwise.

        :returns: True if rotation was successful.
        """
        if self._game.state == GameState.running:
            return bool(self._game.move_piece(Transformation(EigenTransformation.rotation, 1)))
        return False

    def rotate_ccw(self) -> bool:
        """Rotate the current piece counter-clockwise.

        :returns: True if rotation was successful.
        """
        if self._game.state == GameState.running:
            return bool(self._game.move_piece(Transformation(EigenTransformation.rotation, -1)))
        return False

    def soft_drop(self) -> bool:
        """Move the current piece one step down (soft drop).

        :returns: True if move was successful.
        """
        if self._game.state == GameState.running:
            return bool(self._game.move_piece(Transformation(EigenTransformation.vertical, 1)))
        return False

    def hard_drop(self) -> None:
        """Drop the current piece to the bottom immediately."""
        if self._game.state == GameState.running:
            while self._game.move_piece(Transformation(EigenTransformation.vertical, 1)):
                pass

    def move_left_max(self) -> None:
        """Move the current piece to the left edge (max translation)."""
        if self._game.state == GameState.running:
            while self._game.move_piece(Transformation(EigenTransformation.horizontal, -1)):
                pass

    def move_right_max(self) -> None:
        """Move the current piece to the right edge (max translation)."""
        if self._game.state == GameState.running:
            while self._game.move_piece(Transformation(EigenTransformation.horizontal, 1)):
                pass

    def toggle_pause(self) -> None:
        """Toggle the game pause state."""
        self._game.pause(None)

    def lock_piece(self) -> None:
        """Lock the current piece in place without dropping."""
        if self._game.state == GameState.running and self._game.piece is not None:
            self._game._do_lock_piece()
