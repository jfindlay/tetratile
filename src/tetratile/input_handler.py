"""Abstract input handler for game control.

Both :class:`HumanInputHandler` and :class:`AgentInputHandler` inherit from
this base class and receive identical default implementations.  The two
subclasses are **coequal frontends**: swapping one for the other changes *who*
controls the game but not *how* the game responds.  All input is routed
through :meth:`.TetraTile.move_piece` (for movement actions) or
:meth:`.TetraTile.lock_piece` / :meth:`.TetraTile.pause` (for game-state
actions), which each enforce the :attr:`.GameState.running` precondition
internally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import TetraTile


class InputHandler:
    """Default input handler implementing all game actions via :meth:`.TetraTile.move_piece`.

    Subclasses need not override any method unless they require custom
    behaviour.  The default implementation calls :meth:`.TetraTile.move_piece`
    directly; the state guard lives there.

    :attr _game: Reference to the :class:`.TetraTile` game instance.
    """

    def __init__(self, game: TetraTile) -> None:
        """Initialize the input handler.

        :param game: Reference to the :class:`.TetraTile` game instance.
        """
        self._game = game

    def move_left(self) -> bool:
        """Move the current piece one step left.

        :returns: True if move was successful.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.horizontal, -1)))

    def move_right(self) -> bool:
        """Move the current piece one step right.

        :returns: True if move was successful.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.horizontal, 1)))

    def rotate_cw(self) -> bool:
        """Rotate the current piece clockwise.

        :returns: True if rotation was successful.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.rotation, 1)))

    def rotate_ccw(self) -> bool:
        """Rotate the current piece counter-clockwise.

        :returns: True if rotation was successful.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.rotation, -1)))

    def soft_drop(self) -> bool:
        """Move the current piece one step down (soft drop).

        :returns: True if move was successful.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.vertical, 1)))

    def hard_drop(self) -> None:
        """Drop the current piece to the bottom immediately."""
        from . import EigenTransformation, Transformation

        while self._game.move_piece(Transformation(EigenTransformation.vertical, 1)):
            pass

    def move_left_max(self) -> None:
        """Move the current piece to the left edge."""
        from . import EigenTransformation, Transformation

        while self._game.move_piece(Transformation(EigenTransformation.horizontal, -1)):
            pass

    def move_right_max(self) -> None:
        """Move the current piece to the right edge."""
        from . import EigenTransformation, Transformation

        while self._game.move_piece(Transformation(EigenTransformation.horizontal, 1)):
            pass

    def toggle_pause(self) -> None:
        """Toggle the game pause state."""
        self._game.pause()

    def lock_piece(self) -> None:
        """Lock the current piece in place without dropping."""
        self._game.lock_piece()
