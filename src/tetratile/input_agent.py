"""Agent input handler for programmatic game control.

Provides :class:`AgentInputHandler`, the frontend used when an
:class:`.Agent` controls the game via :class:`.AgentRunner`.  All
game-action implementations are inherited from :class:`.InputHandler`;
this subclass exists solely as a named entry point so that
``isinstance(handler, AgentInputHandler)`` can distinguish the agent
frontend from the human frontend.

:class:`AgentRunner` creates one of these, sets it on the game via
:meth:`.TetraTile.set_input_handler`, and then calls its methods in
response to :class:`.Action` values returned by :meth:`.Agent.select_action`.
"""

from .input_handler import InputHandler


class AgentInputHandler(InputHandler):
    """Input handler for AI agent control via Python API.

    Inherits all game actions from :class:`.InputHandler`.  Contains no
    overriding logic; the subclass exists as a named entry point for
    ``isinstance`` discrimination of the active frontend.
    """
