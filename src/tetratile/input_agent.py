"""Agent input handler for programmatic game control.

Provides the :class:`AgentInputHandler` frontend, used when an AI agent
controls the game.  All behaviour is inherited from :class:`.InputHandler`;
this subclass exists as a named entry point so that
``isinstance(handler, AgentInputHandler)`` can distinguish the agent frontend
from the human frontend.
"""

from .input_handler import InputHandler


class AgentInputHandler(InputHandler):
    """Input handler for AI agent control via Python API.

    Inherits all game actions from :class:`.InputHandler`.  An
    :class:`.AgentRunner` calls these methods directly in response to
    :class:`.Action` values returned by an :class:`.Agent`.
    """
