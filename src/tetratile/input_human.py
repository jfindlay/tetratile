"""Human keyboard input handler.

Provides the :class:`HumanInputHandler` frontend, used when a human player
controls the game via keyboard.  All behaviour is inherited from
:class:`.InputHandler`; this subclass exists as a named entry point so that
``isinstance(handler, HumanInputHandler)`` can distinguish the human frontend
from the agent frontend.
"""

from .input_handler import InputHandler


class HumanInputHandler(InputHandler):
    """Input handler for human keyboard control.

    Inherits all game actions from :class:`.InputHandler`.  Keyboard events
    are wired to these methods by :meth:`.TetraTile.setup_events`.
    """
