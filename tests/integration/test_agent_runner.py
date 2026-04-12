"""Integration tests for AgentRunner end-to-end game execution."""

import pytest

from tetratile import GameObservation, GameState
from tetratile.agent import Action, Agent, RandomAgent
from tetratile.agent_runner import AgentRunner, GameResult
from tetratile.config import GameConfig


class TestAgentRunnerBasic:
    """Basic AgentRunner lifecycle tests."""

    @pytest.fixture
    def config(self) -> GameConfig:
        """Minimal config: fast rate, small board, no GUI scaling."""
        return GameConfig(
            board=__import__("tetratile.config", fromlist=["BoardConfig"]).BoardConfig(width=10, height=10, scale=8),
            initial_rate=100.0,
            min_rate=100.0,
            screen_scale=False,
        )

    def test_run_returns_game_result(self, config: GameConfig) -> None:
        """AgentRunner.run() returns a GameResult."""
        runner = AgentRunner(config=config, agent=RandomAgent(), show_gui=False)
        result = runner.run(max_steps=10)
        assert isinstance(result, GameResult)

    def test_result_steps_bounded_by_max_steps(self, config: GameConfig) -> None:
        """Runner stops at max_steps even if game is not over."""
        runner = AgentRunner(config=config, agent=RandomAgent(), show_gui=False)
        result = runner.run(max_steps=5)
        assert result.steps <= 5

    def test_result_has_valid_stats(self, config: GameConfig) -> None:
        """GameResult.stats contains the expected keys."""
        runner = AgentRunner(config=config, agent=RandomAgent(), show_gui=False)
        result = runner.run(max_steps=20)
        assert "pieces" in result.stats
        assert "rows_cleared" in result.stats
        assert "rows_by_count" in result.stats
        assert "pieces_by_type" in result.stats

    def test_result_final_observation_is_game_observation(self, config: GameConfig) -> None:
        """GameResult.final_observation is a GameObservation."""
        runner = AgentRunner(config=config, agent=RandomAgent(), show_gui=False)
        result = runner.run(max_steps=10)
        assert isinstance(result.final_observation, GameObservation)

    def test_result_stats_match_final_observation(self, config: GameConfig) -> None:
        """result.stats equals result.final_observation.stats."""
        runner = AgentRunner(config=config, agent=RandomAgent(), show_gui=False)
        result = runner.run(max_steps=10)
        assert result.stats == result.final_observation.stats

    def test_zero_max_steps_exits_immediately(self, config: GameConfig) -> None:
        """max_steps=0 exits before any action is taken."""
        runner = AgentRunner(config=config, agent=RandomAgent(), show_gui=False)
        result = runner.run(max_steps=0)
        assert result.steps == 0

    def test_custom_agent_is_called(self, config: GameConfig) -> None:
        """A custom Agent.select_action is called during the run."""

        class CountingAgent(Agent):
            """Agent that counts how many times it was called."""

            def __init__(self) -> None:
                """Initialise call counter."""
                self.call_count = 0

            def select_action(self, obs: GameObservation) -> Action:
                """Record call and return a safe action."""
                self.call_count += 1
                return Action.soft_drop

        agent = CountingAgent()
        runner = AgentRunner(config=config, agent=agent, show_gui=False)
        result = runner.run(max_steps=7)
        assert agent.call_count == result.steps

    def test_game_runs_to_over_without_max_steps(self, config: GameConfig) -> None:
        """Without max_steps, runner plays until game-over (small board fills quickly)."""

        class AlwaysDropAgent(Agent):
            """Agent that only full-drops, filling the board fast."""

            def select_action(self, obs: GameObservation) -> Action:
                """Always full drop."""
                return Action.full_drop

        runner = AgentRunner(config=config, agent=AlwaysDropAgent(), show_gui=False)
        result = runner.run()
        assert result.final_observation.state == GameState.over
