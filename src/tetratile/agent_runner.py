"""Agent runner for AI-controlled games.

:class:`AgentRunner` wires an :class:`.Agent` to a :class:`.TetraTile`
instance.  It owns the Tk root, the game, the
:class:`.AgentInputHandler` bridge, and optionally a
:class:`.PrintObserver`.

The runner calls :meth:`.TetraTile.set_manual_drive` to suppress the Tk
gravity timer, then drives :meth:`.TetraTile.iterate` directly.  This
eliminates the **double-step race** that would occur if the Tk timer *and*
the runner loop both called ``iterate`` concurrently.

The action cycle per step is:

1. ``obs = game.get_observation()`` — pull a :class:`.GameObservation` snapshot.
2. ``action = agent.select_action(obs)`` — pure agent decision.
3. ``getattr(handler, action)()`` — dispatch to the game via the
   :class:`.AgentInputHandler` (values of :class:`.Action` equal
   :class:`.InputHandler` method names).
4. ``game.iterate()`` — advance one gravity tick.
5. ``root.update()`` — process Tk events to keep GUI responsive (no-op if
   headless).
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .agent import Agent
from .config import GameConfig
from .input_agent import AgentInputHandler
from .output import PrintObserver

if TYPE_CHECKING:
    from . import GameObservation

from . import GameState, TetraTile


@dataclass
class GameResult:
    """Summary of a completed agent game run.

    Returned by :meth:`AgentRunner.run` when the game ends (either by
    game-over or by reaching ``max_steps``).

    :attr stats: Final game statistics (same dict as
        :attr:`.GameObservation.stats`).
    :attr final_observation: Complete :class:`.GameObservation` at the
        terminal state.
    :attr steps: Number of agent actions executed during the run.
    """

    stats: dict[str, Any]
    final_observation: GameObservation
    steps: int


class AgentRunner:
    """Run a :class:`.TetraTile` game driven by an :class:`.Agent`.

    Owns the Tk root, the game, and the :class:`.AgentInputHandler` bridge.
    Optionally registers a :class:`.PrintObserver` for stdout output.

    When ``show_gui=True`` (default) the game window is visible so a human
    can watch the agent play.  When ``show_gui=False`` the window is
    withdrawn for headless use (e.g. training runs, CI).

    :attr _config: Game configuration.
    :attr _agent: The :class:`.Agent` driving decisions.
    :attr _show_gui: Whether the game window is visible.
    :attr _observe: Whether to attach a :class:`.PrintObserver`.
    """

    def __init__(
        self,
        config: GameConfig | None = None,
        agent: Agent | None = None,
        show_gui: bool = True,
        observe: bool = False,
    ) -> None:
        """Initialize the runner.

        :param config: Game configuration.  Uses defaults if ``None``.
        :param agent: Agent to drive the game.  Uses :class:`.RandomAgent` if ``None``.
        :param show_gui: If ``True`` the game window is visible (human can watch).
            If ``False`` the window is withdrawn (headless).
        :param observe: If ``True`` a :class:`.PrintObserver` is attached,
            printing the board state to stdout after each tick.
        """
        from .agent import RandomAgent

        self._config = config or GameConfig()
        self._agent: Agent = agent if agent is not None else RandomAgent()
        self._show_gui = show_gui
        self._observe = observe

    def run(self, max_steps: int | None = None) -> GameResult:
        """Run the game until game-over or ``max_steps`` actions.

        The runner cancels the automatic Tk gravity timer
        (:meth:`.TetraTile.set_manual_drive`) and drives
        :meth:`.TetraTile.iterate` itself, one call per agent action.
        Each cycle is: observe → select action → execute action → iterate.

        :param max_steps: Cap on the number of agent actions.  Runs to
            game-over if ``None``.
        :returns: :class:`GameResult` with final stats and observation.
        """
        root = tk.Tk(className="tetratile-agent")
        if not self._show_gui:
            root.withdraw()

        game = TetraTile(self._config, master=root)
        handler = AgentInputHandler(game)
        game.set_input_handler(handler)
        game.set_manual_drive(True)

        if self._observe:
            game.add_output_handler(PrintObserver())

        steps = 0
        while game.state != GameState.over:
            if max_steps is not None and steps >= max_steps:
                break

            obs = game.get_observation()
            action = self._agent.select_action(obs)
            # Dispatch: Action values are InputHandler method names.
            getattr(handler, action)()
            steps += 1

            game.iterate()
            root.update()

        final_obs = game.get_observation()
        return GameResult(
            stats=final_obs.stats,
            final_observation=final_obs,
            steps=steps,
        )
