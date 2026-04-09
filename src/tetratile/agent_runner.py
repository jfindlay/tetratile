"""Agent runner for running games with AI control.

This module provides the AgentRunner class that runs the game
with agent input while optionally allowing human observation.
"""

from dataclasses import dataclass

from . import GameConfig, TetraTile
from .input_agent import AgentInputHandler
from .input_handler import InputHandler
from .output import AgentOutputHandler


@dataclass
class GameResult:
    """Result of a completed game.

    :attr stats: Final game statistics.
    :attr events: Complete event log.
    :attr final_observation: Final game state observation.
    :attr steps: Number of input actions taken.
    """

    stats: dict
    events: list
    final_observation: "GameObservation"
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
        self._agent_input: AgentInputHandler | None = None
        self._agent_output: AgentOutputHandler | None = None

    def _create_agent(self) -> InputHandler:
        """Create an agent of the specified class.

        :returns: InputHandler instance for the agent.
        """
        if self._agent_class == "random":
            return RandomAgent(self._game)
        raise ValueError(f"Unknown agent class: {self._agent_class}")

    def run(self, max_steps: int | None = None) -> GameResult:
        """Run the game until completion or max_steps.

        :param max_steps: Maximum number of agent actions. If None, run to game over.
        :returns: GameResult with stats, events, and final observation.
        """
        import tkinter as tk

        # Create Tk root (required for TetraTile)
        root = tk.Tk(className="tetratile-agent")
        root.withdraw()  # Hide window for headless mode

        # Create game
        self._game = TetraTile(self._config, master=root)

        # Set up agent input
        self._agent_input = self._create_agent()
        self._game.set_input_handler(self._agent_input)

        # Enable verbose output if requested
        if self._verbose:
            self._game.set_verbose_output(True)

        # Set up agent output for observation
        self._agent_output = AgentOutputHandler(self._game)

        # Run game loop
        steps = 0
        while self._game.state != GameState.over:
            if max_steps and steps >= max_steps:
                break

            # Get observation and select action
            obs = self._game.get_observation()
            action = self._get_agent_action(obs)
            action_name = self._get_action_name(action)

            # Execute action
            result = action()

            steps += 1

            # Trigger game iteration to update state and print verbose output
            self._game.iterate()

            # Process any pending tk events to keep UI responsive
            root.update()

        # Get final result
        final_obs = self._game.get_observation()
        events = self._game.event_logger.get_log().events or []

        return GameResult(
            stats=final_obs.stats,
            events=events,
            final_observation=final_obs,
            steps=steps,
        )

    def _get_action_name(self, action) -> str:
        """Get the name of an action for logging.

        :param action: Action callable.
        :returns: Name of the action.
        """
        action_map = {
            self._agent_input.move_left: "MOVE_LEFT",
            self._agent_input.move_right: "MOVE_RIGHT",
            self._agent_input.rotate_cw: "ROTATE_CW",
            self._agent_input.rotate_ccw: "ROTATE_CCW",
            self._agent_input.soft_drop: "SOFT_DROP",
        }
        for name, func in action_map.items():
            if action == func:
                return name
        return "UNKNOWN"

    def _get_agent_action(self, obs: "GameObservation"):
        """Get the next action from the agent.

        :param obs: Current game observation.
        :returns: Callable action.
        """
        if self._agent_class == "random":
            return self._random_action()
        raise ValueError(f"Unknown agent class: {self._agent_class}")

    def _random_action(self):
        """Get a random action.

        :returns: Random action callable.
        """
        import random

        actions = [
            self._agent_input.move_left,
            self._agent_input.move_right,
            self._agent_input.rotate_cw,
            self._agent_input.rotate_ccw,
            self._agent_input.soft_drop,
        ]
        return random.choice(actions)


class RandomAgent(InputHandler):
    """Simple random agent for testing.

    This agent selects random valid actions for testing purposes.
    """

    def __init__(self, game: TetraTile) -> None:
        """Initialize the random agent.

        :param game: Reference to the TetraTile game instance.
        """
        super().__init__(game)
        import random

        self._random = random
        self._actions = [
            self.move_left,
            self.move_right,
            self.rotate_cw,
            self.rotate_ccw,
            self.soft_drop,
        ]

    def move_left(self) -> bool:
        return self._game._do_move_left()

    def move_right(self) -> bool:
        return self._game._do_move_right()

    def rotate_cw(self) -> bool:
        return self._game._do_rotate_cw()

    def rotate_ccw(self) -> bool:
        return self._game._do_rotate_ccw()

    def soft_drop(self) -> bool:
        return self._game._do_soft_drop()

    def hard_drop(self) -> None:
        self._game._do_hard_drop()

    def move_left_max(self) -> None:
        self._game._do_move_left_max()

    def move_right_max(self) -> None:
        self._game._do_move_right_max()

    def toggle_pause(self) -> None:
        pass  # Random agent doesn't pause

    def lock_piece(self) -> None:
        self._game._do_lock_piece()


# Import at bottom to avoid circular dependency
from . import GameObservation, GameState
