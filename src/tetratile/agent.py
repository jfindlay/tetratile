"""Agent abstraction for AI game control.

An :class:`Agent` is a **pure decision strategy**: given a
:class:`.GameObservation` it returns an :class:`Action` symbol.  It has no
direct reference to the game instance; the :class:`.AgentRunner` owns both
the game and the agent, bridging them via an :class:`.AgentInputHandler`.

Provided implementations:

* :class:`RandomAgent` — selects uniformly at random from a fixed set of
  movement actions; useful as a baseline and for integration tests.
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

    Values match the corresponding :class:`.InputHandler` method names so
    that :class:`.AgentRunner` can dispatch via ``getattr(handler, action)``.

    :attr move_left: Translate piece one step left.
    :attr move_right: Translate piece one step right.
    :attr rotate_cw: Rotate piece clockwise.
    :attr rotate_ccw: Rotate piece counter-clockwise.
    :attr soft_drop: Translate piece one step down.
    :attr hard_drop: Drop piece to the bottom instantly.
    :attr move_left_max: Translate piece to the left wall.
    :attr move_right_max: Translate piece to the right wall.
    :attr lock_piece: Lock piece in place without dropping.
    :attr toggle_pause: Toggle pause state.
    """

    move_left = "move_left"
    move_right = "move_right"
    rotate_cw = "rotate_cw"
    rotate_ccw = "rotate_ccw"
    soft_drop = "soft_drop"
    hard_drop = "hard_drop"
    move_left_max = "move_left_max"
    move_right_max = "move_right_max"
    lock_piece = "lock_piece"
    toggle_pause = "toggle_pause"


class Agent(ABC):
    """Abstract base class for game-playing agents.

    An agent is a pure decision function: it receives an observation and
    returns an :class:`Action`.  It holds no game reference and produces no
    side effects.
    """

    @abstractmethod
    def select_action(self, obs: GameObservation) -> Action:
        """Choose the next action given the current game state.

        :param obs: Current :class:`.GameObservation` snapshot.
        :returns: The :class:`Action` to execute.
        """


class RandomAgent(Agent):
    """Agent that selects uniformly at random from a set of movement actions.

    Only movement actions are included (no ``hard_drop`` or ``lock_piece``)
    to avoid immediately terminating the game and to match standard Tetris
    agent benchmarks.

    :attr _ACTIONS: Fixed tuple of :class:`Action` values sampled from.
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
        :returns: A randomly chosen :class:`Action`.
        """
        return random.choice(self._ACTIONS)
