"""Coequal input handler for human and agent game control.

Both :class:`HumanInputHandler` and :class:`AgentInputHandler` inherit from
this base class and receive identical default implementations.  The two
subclasses are **coequal frontends**: swapping one for the other changes *who*
controls the game but not *how* the game responds.

All movement actions call :meth:`.TetraTile.move_piece` with an
:class:`.EigenTransformation`, so the state guard (``GameState.running``)
lives in one place.  Lock and pause actions call :meth:`.TetraTile.lock_piece`
and :meth:`.TetraTile.pause` respectively.

The extremal-translation methods :meth:`move_left_max`, :meth:`move_right_max`,
and :meth:`full_drop` compute the **supremum of the piece's orbit** under a
unit generator; see :ref:`extremal-translations` in ``docs/mathematics.rst``
for the mathematical treatment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import TetraTile


class InputHandler:
    """Default implementations of all game actions via :meth:`.TetraTile.move_piece`.

    Subclasses need not override any method.  The default implementation
    delegates every movement action directly to
    :meth:`.TetraTile.move_piece`; the :attr:`.GameState.running` guard
    lives there.

    :attr _game: Reference to the :class:`.TetraTile` game instance.
    """

    def __init__(self, game: TetraTile) -> None:
        """Initialize the input handler.

        :param game: Reference to the :class:`.TetraTile` game instance.
        """
        self._game = game

    def move_left(self) -> bool:
        """Translate the active piece one step left (:math:`-e_x`).

        :returns: ``True`` if the piece moved.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.horizontal, -1)))

    def move_right(self) -> bool:
        """Translate the active piece one step right (:math:`+e_x`).

        :returns: ``True`` if the piece moved.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.horizontal, 1)))

    def rotate_cw(self) -> bool:
        """Rotate the active piece one CW quarter-turn (:math:`r`).

        :returns: ``True`` if the rotation succeeded.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.rotation, 1)))

    def rotate_ccw(self) -> bool:
        """Rotate the active piece one CCW quarter-turn (:math:`r^{-1}`).

        :returns: ``True`` if the rotation succeeded.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.rotation, -1)))

    def soft_drop(self) -> bool:
        """Translate the active piece one step down (gravity direction, :math:`-e_y`).

        :returns: ``True`` if the piece moved.
        """
        from . import EigenTransformation, Transformation

        return bool(self._game.move_piece(Transformation(EigenTransformation.vertical, 1)))

    def full_drop(self) -> None:
        """Drop the active piece to its lowest reachable position.

        Computes the **supremum of the orbit** of the active piece under the
        unit downward generator :math:`-e_y`:

        .. math::

            \\sup\\{k \\geq 0 : P - k\\,e_y
            \\;\\text{is valid in}\\;\\mathcal{G}\\}.

        No closed form exists in general (the obstruction depends on both the
        piece shape and the current stack :math:`\\mathcal{G}`); the loop
        applies :math:`-e_y` iteratively until :meth:`.TetraTile.move_piece`
        returns ``False``.
        """
        from . import EigenTransformation, Transformation

        while self._game.move_piece(Transformation(EigenTransformation.vertical, 1)):
            pass

    def move_left_max(self) -> None:
        """Translate the active piece to its leftmost reachable position.

        Computes the **supremum of the orbit** under :math:`-e_x`:

        .. math::

            \\sup\\{k \\geq 0 : P - k\\,e_x
            \\;\\text{is valid in}\\;\\mathcal{G}\\}.

        The loop applies :math:`-e_x` iteratively until blocked by the left
        wall or the stack.  No closed form exists in general.
        """
        from . import EigenTransformation, Transformation

        while self._game.move_piece(Transformation(EigenTransformation.horizontal, -1)):
            pass

    def move_right_max(self) -> None:
        """Translate the active piece to its rightmost reachable position.

        Computes the **supremum of the orbit** under :math:`+e_x`:

        .. math::

            \\sup\\{k \\geq 0 : P + k\\,e_x
            \\;\\text{is valid in}\\;\\mathcal{G}\\}.

        The loop applies :math:`+e_x` iteratively until blocked by the right
        wall or the stack.
        """
        from . import EigenTransformation, Transformation

        while self._game.move_piece(Transformation(EigenTransformation.horizontal, 1)):
            pass

    def toggle_pause(self) -> None:
        """Toggle the game between :attr:`~.GameState.running` and :attr:`~.GameState.paused`."""
        self._game.pause()

    def lock_piece(self) -> None:
        """Lock the active piece in place without dropping it first."""
        self._game.lock_piece()
