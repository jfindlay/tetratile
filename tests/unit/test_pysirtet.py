"""Unit tests for tetratile."""

import copy
import functools
import random
from collections.abc import Generator
from contextlib import contextmanager

import pytest

from tetratile import (
    Colors,
    Degree,
    Dimension,
    EigenTransformation,
    Grid,
    Polyomino,
    Transformation,
    tetrominoes,
)
from tetratile.config import GameConfig


@contextmanager
def not_raises(exception: Exception) -> Generator[None, None, None]:
    """Context manager to verify an exception is NOT raised.

    :param exception: The exception type that should not be raised.
    :yields: Nothing.
    """
    try:
        yield
    except exception:
        raise pytest.fail(f"DID RAISE {exception}") from None


@functools.cache
def grid_superset(width: int, height: int) -> tuple[list[int], list[int]]:
    """Generate coordinates outside the grid boundaries.

    :param width: Grid width.
    :param height: Grid height.
    :returns: (x_out, y_out) lists of out-of-bounds coordinates.
    """
    x_out = list(range(-height // 2, -1)) + list(range(width, width + height // 2))
    y_out = list(range(-width // 2, -1)) + list(range(height, height + width // 2))
    return (x_out, y_out)


class TestPolyomino:
    """Tests for Polyomino class."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_check(self) -> None:
        """Test Grid.check validates coordinates correctly."""
        for v in self.grid:
            assert Grid.check(self.grid, [v])

        for _i in range(random.randint(min(self.grid.width, self.grid.height), self.grid.width * self.grid.height)):
            self.grid[random.randint(0, self.grid.width - 1), random.randint(0, self.grid.height - 1)].type = random.choice(
                list(tetrominoes)
            ).name
        for v in self.grid:
            assert Grid.check(self.grid, [v]) is (self.grid[v].type is None)

        (x_out, y_out) = grid_superset(self.grid.width, self.grid.height)
        for x in x_out:
            for y in y_out:
                assert not Grid.check(self.grid, [(x, y)])
        for x in range(self.grid.width):
            for y in y_out:
                assert not Grid.check(self.grid, [(x, y)])
        for x in x_out:
            for y in range(self.grid.height):
                assert not Grid.check(self.grid, [(x, y)])

    def test_min(self) -> None:
        """Test Polyomino.min returns correct minimum coordinate."""
        ordinal: int = random.randint(2, 11)
        coords: list[list[int]] = [[random.randint(0, self.grid.height) for _i in range(2)] for _j in range(ordinal)]
        p = Polyomino(dim=Dimension.D2, deg=Degree.monimo, colors=Colors(), coords=coords)

        for dim in (Dimension.D1, Dimension.D2):
            assert p.min(dim) == min([c[dim.value - 1] for c in coords])

    def test_max(self) -> None:
        """Test Polyomino.max returns correct maximum coordinate."""
        ordinal: int = random.randint(2, 11)
        coords: list[list[int]] = [[random.randint(0, self.grid.height) for _i in range(2)] for _j in range(ordinal)]
        p = Polyomino(dim=Dimension.D2, deg=Degree.monimo, colors=Colors(), coords=coords)

        for dim in (Dimension.D1, Dimension.D2):
            assert p.max(dim) == max([c[dim.value - 1] for c in coords])

    def test_rotate(self) -> None:
        """Test Polyomino.rotate performs correct rotations."""
        for tetromino_type in tetrominoes:
            tetromino = copy.deepcopy(tetromino_type)
            tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
            rotation_states = {}
            for quarter in range(9):
                assert tetromino.rotate(Transformation(EigenTransformation.rotation, 1), self.grid)
                rotation_states[quarter] = tetromino.coords
                if quarter - 4 in rotation_states:
                    assert rotation_states[quarter] == rotation_states[quarter - 4]

    def test_translate(self) -> None:
        """Test Polyomino.translate handles all translation types."""
        for tetromino_type in tetrominoes:
            tetromino = copy.deepcopy(tetromino_type)
            for dx, dy in ([-1, 0], [1, 0], [0, -1]):
                tetromino.translate(
                    [
                        self.grid.width // 2 - int(tetromino.o[0]),
                        self.grid.height // 2 - int(tetromino.o[1]),
                    ],
                    self.grid,
                )
                assert tetromino.translate([dx, dy], self.grid)

            for translation in (EigenTransformation.min, EigenTransformation.max, EigenTransformation.bottom):
                tetromino.translate(
                    [
                        self.grid.width // 2 - int(tetromino.o[0]),
                        self.grid.height // 2 - int(tetromino.o[1]),
                    ],
                    self.grid,
                )
                t = Transformation(translation)
                assert tetromino.translate(t, self.grid)
                coords = tetromino.coords
                tetromino.translate(t, self.grid)
                assert coords == tetromino.coords
                if translation == EigenTransformation.min:
                    assert tetromino.min(Dimension.D1) == 0
                if translation == EigenTransformation.max:
                    assert self.grid.width == tetromino.max(Dimension.D1) + 1
                if translation == EigenTransformation.bottom:
                    assert tetromino.min(Dimension.D2) == 0


class TestGrid:
    """Tests for Grid class."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_get(self) -> None:
        """Test Grid.__getitem__ retrieves squares correctly."""
        for v in self.grid:
            with not_raises(IndexError):
                assert self.grid[v].type is None

        (x_out, y_out) = grid_superset(self.grid.width, self.grid.height)
        for x in x_out:
            for y in y_out:
                with pytest.raises(IndexError):
                    self.grid[[x, y]]
        for x in range(self.grid.width):
            for y in y_out:
                with pytest.raises(IndexError):
                    self.grid[[x, y]]
        for x in x_out:
            for y in range(self.grid.height):
                with pytest.raises(IndexError):
                    self.grid[[x, y]]

    def test_set(self) -> None:
        """Test Grid.__setitem__ sets squares correctly."""
        for i in range(self.grid.width):
            for j in range(self.grid.height):
                with not_raises(IndexError):
                    tetromino_name: str = random.choice(list(tetrominoes)).name
                    self.grid[[i, j]].type = tetromino_name
                    assert self.grid[[i, j]].type == tetromino_name

        (x_out, y_out) = grid_superset(self.grid.width, self.grid.height)
        for x in x_out:
            for y in y_out:
                with pytest.raises(IndexError):
                    self.grid[[x, y]].type = random.choice(list(tetrominoes)).name
        for x in range(self.grid.width):
            for y in y_out:
                with pytest.raises(IndexError):
                    self.grid[[x, y]].type = random.choice(list(tetrominoes)).name
        for x in x_out:
            for y in range(self.grid.height):
                with pytest.raises(IndexError):
                    self.grid[[x, y]].type = random.choice(list(tetrominoes)).name
