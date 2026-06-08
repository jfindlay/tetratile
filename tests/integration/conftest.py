"""Integration tests for tetratile game."""

import random
from unittest.mock import MagicMock

import pytest

from tetratile import (
    Grid,
    Polyomino,
    Translation,
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
def tetromino(grid: Grid) -> Polyomino:
    """Create a random tetromino translated to the grid centre."""
    p = random.choice(tetrominoes)
    moved = p.translate(Translation(grid.width // 2, grid.height // 2), grid)
    assert moved is not None
    return moved


@pytest.fixture
def all_tetrominoes(grid: Grid) -> list[Polyomino]:
    """Create all tetromino types translated to the grid centre."""
    result = []
    for p in tetrominoes:
        moved = p.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None, f"Tetromino {p.name!r} failed to translate to grid centre"
        result.append(moved)
    return result


@pytest.fixture
def mock_parent() -> MagicMock:
    """Create a mock parent widget for Board creation."""
    parent = MagicMock()
    parent.winfo_width.return_value = 320
    parent.winfo_height.return_value = 704
    return parent
