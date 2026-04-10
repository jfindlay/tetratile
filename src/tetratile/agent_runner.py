"""Agent runner for running games with AI control.

This module provides the AgentRunner class that runs the game
with agent input while optionally allowing human observation.
"""

from __future__ import annotations

import random
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .config import GameConfig
from .input_handler import InputHandler
from .output import AgentOutputHandler

if TYPE_CHECKING:
    from . import GameObservation

# Imported at module level (not TYPE_CHECKING) because needed at runtime
from . import GameState, TetraTile  # noqa: E402


@dataclass
class GameResult:
    """Result of a completed game.

    :attr stats: Final game statistics.
    :attr events: Complete event log.
    :attr final_observation: Final game state observation.
    :attr steps: Number of input actions taken.
    """

    stats: dict[str, Any]
    events: list[Any]
    final_observation: GameObservation
    steps: int


class AgentRunner:
    """Runner for games with AI agent control.

    Allows running games with agent input, optionally with human
    GUI observation enabled in real-time.
    """

    def __init__(
        self,
        config: GameConfig | None = None,
        agent_class: str = "random",
        verbose: bool = False,
    ) -> None:
        """Initialize the agent runner.

        :param config: Game configuration. If None, uses default.
        :param agent_class: Agent class to use (currently only "random" supported).
        :param verbose: If True, output game state to stdout after each iteration.
        """
        self._config = config or GameConfig()
        self._agent_class = agent_class
        self._verbose = verbose
        self._game: TetraTile | None = None
        self._agent: RandomAgent | None = None
        self._agent_output: AgentOutputHandler | None = None

    def _create_agent(self, game: TetraTile) -> RandomAgent:
        """Create an agent of the specified class.

        :param game: The TetraTile game instance.
        :returns: InputHandler instance for the agent.
        :raises ValueError: If agent_class is not recognized.
        """
        if self._agent_class == "random":
            return RandomAgent(game)
        raise ValueError(f"Unknown agent class: {self._agent_class}")

    def run(self, max_steps: int | None = None) -> GameResult:
        """Run the game until completion or max_steps.

        :param max_steps: Maximum number of agent actions. If None, run to game over.
        :returns: GameResult with stats, events, and final observation.
        """
        # Create Tk root (required for TetraTile)
        root = tk.Tk(className="tetratile-agent")
        root.withdraw()  # Hide window for headless mode

        # Create game
        game = TetraTile(self._config, master=root)
        self._game = game

        # Set up agent
        agent = self._create_agent(game)
        self._agent = agent
        game.set_input_handler(agent)

        # Enable verbose output if requested
        if self._verbose:
            game.set_verbose_output(True)

        # Set up agent output for observation
        self._agent_output = AgentOutputHandler(game)

        # Run game loop
        steps = 0
        while game.state != GameState.over:
            if max_steps is not None and steps >= max_steps:
                break

            # Get observation and select action
            obs = game.get_observation()
            action = agent.select_action(obs)

            # Execute action
            action()
            steps += 1

            # Trigger game iteration to advance state
            game.iterate()

            # Process any pending tk events to keep UI responsive
            root.update()

        # Get final result
        final_obs = game.get_observation()
        events: list[Any] = game.event_logger.get_log().events or []

        return GameResult(
            stats=final_obs.stats,
            events=events,
            final_observation=final_obs,
            steps=steps,
        )


class RandomAgent(InputHandler):
    """Simple random agent for testing.

    This agent selects random valid actions for testing purposes.

    :attr _actions: List of action callables available to the agent.
    """

    def __init__(self, game: TetraTile) -> None:
        """Initialize the random agent.

        :param game: Reference to the TetraTile game instance.
        """
        super().__init__(game)
        self._actions: list[Callable[[], bool]] = [
            self.move_left,
            self.move_right,
            self.rotate_cw,
            self.rotate_ccw,
            self.soft_drop,
        ]

    def select_action(self, obs: GameObservation) -> Callable[[], bool]:
        """Select a random action given the current observation.

        :param obs: Current game observation (unused by random agent).
        :returns: A callable action to execute.
        """
        return random.choice(self._actions)

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
        """Toggle the game pause state (no-op for random agent)."""

    def lock_piece(self) -> None:
        """Lock the current piece in place without dropping."""
        self._game._do_lock_piece()
