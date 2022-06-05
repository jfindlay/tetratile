import functools
import random
from contextlib import contextmanager
from decimal import Decimal as D
from typing import Generator, List, Mapping

import pytest

from tetratile import Grid, Polyomino
from tetratile.__main__ import Config
from tetratile.tetratile import Dim, Rotation, Translation, tetrominoes


# https://stackoverflow.com/a/42327075
@contextmanager
def not_raises(exception: Exception) -> Generator[None, None, None]:
    try:
        yield
    except exception:
        raise pytest.fail("DID RAISE {}".format(exception))


@functools.cache
def grid_superset(width: int, height: int):
    """
    Generate an arbitrary covering, $(w + h)^2$, of the grid.  I could try to
    work this into a `pytest.fixture`, but do not know how to pass args to
    fixtures, and this function does what is needed.
    """
    x_out: List[int] = [i for i in range(-height // 2, -1)] + [i for i in range(width, width + height // 2)]
    y_out: List[int] = [j for j in range(-width // 2, -1)] + [j for j in range(height, height + width // 2)]
    return (x_out, y_out)


class TestPolyomino:
    """
    Test the Polyomino class
    """

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """
        Setup program options and grid state
        """
        self.opts: Mapping = Config(test=True).get_opts()
        self.grid: Grid = Grid(self.opts, self.opts["board"]["width"], self.opts["board"]["height"])

    def test__check_grid(self):
        """
        Test the constraint checking function
        """
        # Test that all interior squares of an empty grid are valid
        for v, square in self.grid:
            assert Polyomino._check_grid(Polyomino, [v], self.grid)

        # Test that interior squares that are occupied are invalid
        for i in range(random.randint(min(self.grid.width, self.grid.height), self.grid.width * self.grid.height)):
            self.grid[random.randint(0, self.grid.width - 1), random.randint(0, self.grid.height - 1)][
                "type"
            ]: str = random.choice(tetrominoes).name
        for v, square in self.grid:
            assert Polyomino._check_grid(Polyomino, [v], self.grid) is (True if self.grid[v]["type"] is None else False)

        # Test that exterior squares are invalid (pick an arbitrary covering, $(w + h)^2$, of the grid)
        (x_out, y_out) = grid_superset(self.grid.width, self.grid.height)
        for x in x_out:
            for y in y_out:
                assert not Polyomino._check_grid(Polyomino, [(x, y)], self.grid)
        for x in range(self.grid.width):
            for y in y_out:
                assert not Polyomino._check_grid(Polyomino, [(x, y)], self.grid)
        for x in x_out:
            for y in range(self.grid.height):
                assert not Polyomino._check_grid(Polyomino, [(x, y)], self.grid)

    def test_min(self):
        """
        Test the minimum coordinate function
        """
        # Setup random 'polyomino'
        ordinal: int = random.randint(2, 11)
        coords: List[List[Tuple[int, int]]] = [[random.randint(0, self.grid.height) for i in range(2)] for j in range(ordinal)]
        p: Polyomino = Polyomino(None, None, coords)

        for dim in (Dim.x, Dim.y):
            assert p.min(dim) == min([c[dim.value] for c in coords])

    def test_max(self):
        """
        Test the maximum coordinate function
        """
        # Setup random 'polyomino'
        ordinal: int = random.randint(2, 11)
        coords: List[List[Tuple[int, int]]] = [[random.randint(0, self.grid.height) for i in range(2)] for j in range(ordinal)]
        p: Polyomino = Polyomino(None, None, coords)

        for dim in (Dim.x, Dim.y):
            assert p.max(dim) == max([c[dim.value] for c in coords])

    def test_rotate(self):
        """
        Test polyomino rotations on the grid
        """
        # For each tetromino
        for tetromino in tetrominoes:
            # Test each direction
            for direction in (Rotation.cw, Rotation.ccw):
                # Move piece to center of grid
                tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
                rotation_states: Mapping = {}
                # And cover the rotation space twice
                for quarter in range(9):
                    # Test that rotation is successful
                    assert tetromino.rotate(Rotation.cw, self.grid)
                    rotation_states[quarter]: List[Tuple[D, D]] = tetromino.coords
                    if quarter - 4 in rotation_states:
                        # Test that rotations are isometric mod 4
                        assert rotation_states[quarter] == rotation_states[quarter - 4]

    def test_translate(self):
        """
        Test polyomino translations on the grid
        """
        # For each tetromino
        for tetromino in tetrominoes:
            # Test each single row/column translation
            for translation in ([-1, 0], [1, 0], [0, -1]):
                # Move piece to center of grid
                tetromino.translate(
                    [
                        self.grid.width // 2 - int(tetromino.o[0]),
                        self.grid.height // 2 - int(tetromino.o[1]),
                    ],
                    self.grid,
                )
                # Test that translation is successful
                assert tetromino.translate(translation, self.grid)

            # Test each extremal translation
            for translation in (Translation.min, Translation.max, Translation.bottom):
                # Move piece to center of grid
                tetromino.translate(
                    [
                        self.grid.width // 2 - int(tetromino.o[0]),
                        self.grid.height // 2 - int(tetromino.o[1]),
                    ],
                    self.grid,
                )
                # Test that translation is successful
                assert tetromino.translate(translation, self.grid)
                # Test that translation is idempotent
                coords: List[Tuple[D, D]] = tetromino.coords
                tetromino.translate(translation, self.grid)
                assert coords == tetromino.coords
                # Test that translation is extremal
                if translation == Translation.min:
                    assert 0 == tetromino.min(Dim.x)
                if translation == Translation.max:
                    assert self.grid.width == tetromino.max(Dim.x) + 1
                if translation == Translation.bottom:
                    assert 0 == tetromino.min(Dim.y)


class TestGrid:
    """
    Test the Grid class
    """

    @pytest.fixture(autouse=True)
    def setup_grid(self):
        """
        Setup program options and create a test grid instance
        """
        self.opts: Mapping = Config(test=True).get_opts()
        self.grid: Grid = Grid(self.opts, self.opts["board"]["width"], self.opts["board"]["height"])

    def test_get(self):
        """
        Test getting squares in the grid
        """
        # Test that interior squares are valid
        for v, square in self.grid:
            with not_raises(IndexError):
                assert square["type"] is None

        # Test that exterior squares are invalid (pick an arbitrary covering, $(w + h)^2$, of the grid)
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

    def test_set(self):
        """
        Test setting squares in the grid
        """
        # Test that interior squares are valid
        for i in range(self.grid.width):
            for j in range(self.grid.height):
                with not_raises(IndexError) as e_info:
                    tetromino_name: str = random.choice(tetrominoes).name
                    self.grid[[i, j]]["type"]: str = tetromino_name
                    assert self.grid[[i, j]]["type"] == tetromino_name

        # Test that exterior squares are invalid (pick an arbitrary covering, $(w + h)^2$, of the grid)
        (x_out, y_out) = grid_superset(self.grid.width, self.grid.height)
        for x in x_out:
            for y in y_out:
                with pytest.raises(IndexError) as e_info:
                    self.grid[[x, y]]: str = random.choice(tetrominoes).name
        for x in range(self.grid.width):
            for y in y_out:
                with pytest.raises(IndexError) as e_info:
                    self.grid[[x, y]]: str = random.choice(tetrominoes).name
        for x in x_out:
            for y in range(self.grid.height):
                with pytest.raises(IndexError) as e_info:
                    self.grid[[x, y]]: str = random.choice(tetrominoes).name
