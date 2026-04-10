"""Agent input handler for game control.

This module provides the agent input handler that exposes a Python API
for AI agents to control the game, implementing the InputHandler interface.
"""

from .input_handler import InputHandler


class AgentInputHandler(InputHandler):
    """Input handler for AI agent control via Python API.

    Provides a clean Python API for AI agents to interact with the game,
    implementing the same InputHandler interface as HumanInputHandler to
    ensure identical game behavior.
    """

    def move_left(self) -> bool:
        """Move the current piece one step left.

        :returns: True if move was successful.
        """
        return bool(self._game._do_move_left())

    def move_right(self) -> bool:
        """Move the current piece one step right.

        :returns: True if move was successful.
        """
        return bool(self._game._do_move_right())

    def rotate_cw(self) -> bool:
        """Rotate the current piece clockwise.

        :returns: True if rotation was successful.
        """
        return bool(self._game._do_rotate_cw())

    def rotate_ccw(self) -> bool:
        """Rotate the current piece counter-clockwise.

        :returns: True if rotation was successful.
        """
        return bool(self._game._do_rotate_ccw())

    def soft_drop(self) -> bool:
        """Move the current piece one step down (soft drop).

        :returns: True if move was successful.
        """
        return bool(self._game._do_soft_drop())

    def hard_drop(self) -> None:
        """Drop the current piece to the bottom immediately."""
        self._game._do_hard_drop()

    def move_left_max(self) -> None:
        """Move the current piece to the left edge (max translation)."""
        self._game._do_move_left_max()

    def move_right_max(self) -> None:
        """Move the current piece to the right edge (max translation)."""
        self._game._do_move_right_max()

    def toggle_pause(self) -> None:
        """Toggle the game pause state."""
        self._game._do_toggle_pause()

    def lock_piece(self) -> None:
        """Lock the current piece in place without dropping."""
        self._game._do_lock_piece()
