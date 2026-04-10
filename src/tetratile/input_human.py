"""Human keyboard input handler.

Provides :class:`HumanInputHandler`, the frontend used when a human player
controls the game via keyboard.  All game-action implementations are
inherited from :class:`.InputHandler`; this subclass exists solely as a
named entry point so that ``isinstance(handler, HumanInputHandler)`` can
distinguish the human frontend from the agent frontend.

Keyboard events are bound to :class:`.InputHandler` methods by
:meth:`.TetraTile.setup_events`, so swapping this handler for an
:class:`.AgentInputHandler` transfers control to the agent without
rebinding any keys.
"""

from .input_handler import InputHandler


class HumanInputHandler(InputHandler):
    """Input handler for human keyboard control.

    Inherits all game actions from :class:`.InputHandler`.  Contains no
    overriding logic; the subclass exists as a named entry point for
    ``isinstance`` discrimination of the active frontend.
    """
