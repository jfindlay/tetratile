"""Integration tests for tetratile game."""

import copy
import random
from unittest.mock import MagicMock

import pytest

from tetratile import (
    Grid,
    Tetromino,
    tetrominoes,
)
from tetratile.config import GameConfig


@pytest.fixture
def config() -> GameConfig:
    """Create a default game config for tests."""
    return GameConfig()


@pytest.fixture
def grid(config: GameConfig) -> Grid:
    """Create a test grid with default dimensions."""
    return Grid(config.board.width, config.board.height)


@pytest.fixture
def tetromino(grid: Grid) -> Tetromino:
    """Create a random tetromino centered on the grid."""
    t = copy.deepcopy(random.choice(tetrominoes))
    t.translate([grid.width // 2, grid.height // 2], grid)
    return t


@pytest.fixture
def all_tetrominoes(grid: Grid) -> list[Tetromino]:
    """Create all tetromino types centered on the grid."""
    return [copy.deepcopy(t).translate([grid.width // 2, grid.height // 2], grid) for t in tetrominoes]


@pytest.fixture
def mock_parent() -> MagicMock:
    """Create a mock parent widget for Board creation."""
    parent = MagicMock()
    parent.winfo_width.return_value = 320
    parent.winfo_height.return_value = 704
    return parent
