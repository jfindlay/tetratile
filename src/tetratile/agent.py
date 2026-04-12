"""Agent abstraction for AI game control.

An :class:`Agent` is a **pure decision strategy**: given a
:class:`.GameObservation` — a read-only snapshot of the game's algebraic
state (:math:`\\mathcal{G}`, active piece, game-lifecycle state) — it returns
an :class:`Action` symbol.  The agent holds no reference to the game object
and produces no side effects.

The :class:`AgentRunner` owns both the game and the agent, bridging them via
an :class:`.AgentInputHandler`.  The loop is:

1. ``obs = game.get_observation()``  (pull snapshot)
2. ``action = agent.select_action(obs)``  (pure decision)
3. ``getattr(handler, action)()``  (dispatch action to game)
4. ``game.iterate()``  (advance one gravity tick)

The :class:`Action` alphabet enumerates all valid game operations.  Each
value equals the corresponding :class:`.InputHandler` method name, so
dispatch is simply ``getattr(handler, action)()`` — no explicit mapping
table needed.

Provided implementations:

* :class:`RandomAgent` — selects uniformly at random from movement actions.
  Useful as a baseline and for integration tests.
"""

from __future__ import annotations

import enum
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import GameObservation


class Action(enum.StrEnum):
    """Enumeration of all game actions an agent can issue.

    Each value equals the corresponding :class:`.InputHandler` method name so
    that :class:`.AgentRunner` can dispatch via ``getattr(handler, action)()``.
    This makes the :class:`Action` alphabet and the :class:`.InputHandler`
    interface structurally coupled: adding a new action requires adding a
    member here *and* a method there.

    :attr move_left: Translate piece one step left (:math:`-e_x`).
    :attr move_right: Translate piece one step right (:math:`+e_x`).
    :attr rotate_cw: Rotate piece one CW quarter-turn (:math:`r`).
    :attr rotate_ccw: Rotate piece one CCW quarter-turn (:math:`r^{-1}`).
    :attr soft_drop: Translate piece one step down (:math:`-e_y`, gravity).
    :attr full_drop: Drop piece to its lowest reachable position (orbit supremum under :math:`-e_y`).
    :attr move_left_max: Translate to leftmost reachable position (orbit supremum under :math:`-e_x`).
    :attr move_right_max: Translate to rightmost reachable position (orbit supremum under :math:`+e_x`).
    :attr lock_piece: Lock piece in place without dropping.
    :attr toggle_pause: Toggle pause state.
    """

    move_left = "move_left"
    move_right = "move_right"
    rotate_cw = "rotate_cw"
    rotate_ccw = "rotate_ccw"
    soft_drop = "soft_drop"
    full_drop = "full_drop"
    move_left_max = "move_left_max"
    move_right_max = "move_right_max"
    lock_piece = "lock_piece"
    toggle_pause = "toggle_pause"


class Agent(ABC):
    """Abstract base class for game-playing agents.

    An agent is a pure decision function:

    .. math::

        f:\\; \\text{GameObservation} \\;\\longrightarrow\\; \\text{Action}.

    It has no reference to the game object and produces no side effects.
    The algebraic game state is observed through :class:`.GameObservation`;
    the agent's output is one element of the :class:`Action` alphabet.
    """

    @abstractmethod
    def select_action(self, obs: GameObservation) -> Action:
        """Choose the next action given the current game state snapshot.

        :param obs: Read-only :class:`.GameObservation` snapshot.
        :returns: The :class:`Action` to execute next.
        """


class RandomAgent(Agent):
    """Agent that samples uniformly at random from a fixed movement-action alphabet.

    Only movement actions are included in the sample pool — ``full_drop``,
    ``lock_piece``, ``move_left_max``, ``move_right_max``, and
    ``toggle_pause`` are excluded to avoid immediately terminating the game
    or disrupting the gravity loop.

    :attr _ACTIONS: Fixed tuple of :class:`Action` values to sample from.
    """

    _ACTIONS: tuple[Action, ...] = (
        Action.move_left,
        Action.move_right,
        Action.rotate_cw,
        Action.rotate_ccw,
        Action.soft_drop,
    )

    def select_action(self, obs: GameObservation) -> Action:
        """Return a uniformly random movement action.

        :param obs: Current game observation (unused by random policy).
        :returns: A randomly chosen :class:`Action` from :attr:`_ACTIONS`.
        """
        return random.choice(self._ACTIONS)
