"""Integration test fixtures shared across the tetratile integration suite."""

from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from tetratile import Grid
from tetratile.config import GameConfig


@pytest.fixture
def config() -> GameConfig:
    """Provide a default :class:`GameConfig` for integration tests."""
    return GameConfig()


@pytest.fixture
def grid(config: GameConfig) -> Grid:
    """Provide a :class:`Grid` with default board dimensions."""
    return Grid(config.board.width, config.board.height)


@pytest.fixture
def mock_parent(mocker: MockerFixture) -> MagicMock:
    """Provide a mock parent widget for :class:`Board` construction.

    Returns a ``MagicMock`` configured with the ``winfo_width`` and
    ``winfo_height`` return values that :class:`Board` reads during init.
    """
    parent: MagicMock = mocker.MagicMock()
    parent.winfo_width.return_value = 320
    parent.winfo_height.return_value = 704
    return parent
