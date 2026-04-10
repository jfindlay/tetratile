"""Unit tests for tetratile."""

import copy
import functools
import random
from collections.abc import Generator
from contextlib import contextmanager

import pytest

from tetratile import (
    Colors,
    Dimension,
    EigenTransformation,
    Grid,
    Polyomino,
    Square,
    Transformation,
    mix_with_black,
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
        p = Polyomino(dim=Dimension.Y, colors=Colors(), coords=coords)

        for dim in (Dimension.X, Dimension.Y):
            assert p.min(dim) == min([c[dim.value - 1] for c in coords])

    def test_max(self) -> None:
        """Test Polyomino.max returns correct maximum coordinate."""
        ordinal: int = random.randint(2, 11)
        coords: list[list[int]] = [[random.randint(0, self.grid.height) for _i in range(2)] for _j in range(ordinal)]
        p = Polyomino(dim=Dimension.Y, colors=Colors(), coords=coords)

        for dim in (Dimension.X, Dimension.Y):
            assert p.max(dim) == max([c[dim.value - 1] for c in coords])

    def test_rotate(self) -> None:
        """Test Polyomino.rotate performs correct rotations."""
        for tetromino_type in tetrominoes:
            tetromino = copy.deepcopy(tetromino_type)
            tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
            rotation_states = {}
            for quarter in range(9):
                rotated = tetromino.rotate(Transformation(EigenTransformation.rotation, 1), self.grid)
                if tetromino.name == "o":
                    assert not rotated
                else:
                    assert rotated
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
                    assert tetromino.min(Dimension.X) == 0
                if translation == EigenTransformation.max:
                    assert self.grid.width == tetromino.max(Dimension.X) + 1
                if translation == EigenTransformation.bottom:
                    assert tetromino.min(Dimension.Y) == 0


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


class TestMixWithBlack:
    """Tests for mix_with_black() function."""

    def test_mix_with_black_full_black(self) -> None:
        """Test mix_with_black with factor=1.0 returns black."""
        result = mix_with_black("#FF0000", 1.0)
        assert result == "#000000"

    def test_mix_with_black_zero_factor(self) -> None:
        """Test mix_with_black with factor=0.0 returns original color."""
        result = mix_with_black("#FF0000", 0.0)
        assert result == "#ff0000"

    def test_mix_with_black_partial_mix(self) -> None:
        """Test mix_with_black with intermediate factor."""
        result = mix_with_black("#FF0000", 0.5)
        assert result.startswith("#")
        assert int(result[1:3], 16) == 127

    def test_mix_with_black_invalid_color_short(self) -> None:
        """Test mix_with_black handles invalid short color."""
        result = mix_with_black("#FF", 0.5)
        assert result == "#FF"

    def test_mix_with_black_invalid_color_empty(self) -> None:
        """Test mix_with_black handles empty string."""
        result = mix_with_black("", 0.5)
        assert result == ""

    def test_mix_with_black_invalid_color_none(self) -> None:
        """Test mix_with_black handles None-like string."""
        result = mix_with_black("invalid", 0.5)
        assert result == "invalid"

    def test_mix_with_black_green(self) -> None:
        """Test mix_with_black with green color."""
        result = mix_with_black("#00FF00", 0.5)
        assert result.startswith("#")
        assert int(result[3:5], 16) == 127

    def test_mix_with_black_blue(self) -> None:
        """Test mix_with_black with blue color."""
        result = mix_with_black("#0000FF", 0.5)
        assert result.startswith("#")
        assert int(result[5:7], 16) == 127


class TestPolyominoTransform:
    """Tests for Polyomino.transform() method."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_transform_identity(self) -> None:
        """Test transform with identity transformation returns True."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
        original_coords = [coord[:] for coord in tetromino.coords]

        result = tetromino.transform(Transformation(EigenTransformation.identity), self.grid)

        assert result is True
        assert tetromino.coords == original_coords

    def test_transform_rotation(self) -> None:
        """Test transform dispatches to rotate correctly."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
        original_coords = [coord[:] for coord in tetromino.coords]

        result = tetromino.transform(Transformation(EigenTransformation.rotation, 1), self.grid)

        assert result is True
        assert tetromino.coords != original_coords

    def test_transform_horizontal(self) -> None:
        """Test transform dispatches to translate for horizontal."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
        original_min = tetromino.min(Dimension.X)

        result = tetromino.transform(Transformation(EigenTransformation.horizontal, 1), self.grid)

        assert result is True
        assert tetromino.min(Dimension.X) == original_min + 1

    def test_transform_vertical(self) -> None:
        """Test transform dispatches to translate for vertical."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
        original_min = tetromino.min(Dimension.Y)

        result = tetromino.transform(Transformation(EigenTransformation.vertical, 1), self.grid)

        assert result is True
        assert tetromino.min(Dimension.Y) == original_min - 1

    def test_transform_min(self) -> None:
        """Test transform with min transformation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)

        result = tetromino.transform(Transformation(EigenTransformation.min), self.grid)

        assert result is True
        assert tetromino.min(Dimension.X) == 0

    def test_transform_max(self) -> None:
        """Test transform with max transformation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)

        result = tetromino.transform(Transformation(EigenTransformation.max), self.grid)

        assert result is True
        assert tetromino.max(Dimension.X) == self.grid.width - 1

    def test_transform_bottom(self) -> None:
        """Test transform with bottom transformation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)

        result = tetromino.transform(Transformation(EigenTransformation.bottom), self.grid)

        assert result is True
        assert tetromino.min(Dimension.Y) == 0


class TestPolyominoGetTranslation:
    """Tests for Polyomino._get_translation() method."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_get_translation_list(self) -> None:
        """Test _get_translation with list input returns values correctly."""
        tetromino = copy.deepcopy(tetrominoes[3])
        dx, dy, single_step = tetromino._get_translation([3, 5])
        assert dx == 3
        assert dy == 5
        assert single_step is True

    def test_get_translation_horizontal_positive(self) -> None:
        """Test _get_translation with positive horizontal."""
        tetromino = copy.deepcopy(tetrominoes[3])
        dx, dy, single_step = tetromino._get_translation(Transformation(EigenTransformation.horizontal, 2))
        assert dx == 2
        assert dy == 0
        assert single_step is True

    def test_get_translation_horizontal_negative(self) -> None:
        """Test _get_translation with negative horizontal."""
        tetromino = copy.deepcopy(tetrominoes[3])
        dx, dy, single_step = tetromino._get_translation(Transformation(EigenTransformation.horizontal, -1))
        assert dx == -1
        assert dy == 0
        assert single_step is True

    def test_get_translation_vertical(self) -> None:
        """Test _get_translation with vertical transformation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        dx, dy, single_step = tetromino._get_translation(Transformation(EigenTransformation.vertical, 2))
        assert dx == 0
        assert dy == -2
        assert single_step is True

    def test_get_translation_min(self) -> None:
        """Test _get_translation with min transformation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        dx, dy, single_step = tetromino._get_translation(Transformation(EigenTransformation.min))
        assert dx == -1
        assert dy == 0
        assert single_step is False

    def test_get_translation_max(self) -> None:
        """Test _get_translation with max transformation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        dx, dy, single_step = tetromino._get_translation(Transformation(EigenTransformation.max))
        assert dx == 1
        assert dy == 0
        assert single_step is False

    def test_get_translation_bottom(self) -> None:
        """Test _get_translation with bottom transformation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        dx, dy, single_step = tetromino._get_translation(Transformation(EigenTransformation.bottom))
        assert dx == 0
        assert dy == -1
        assert single_step is False


class TestGridErrorHandling:
    """Tests for Grid error paths."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_setitem_negative_x(self) -> None:
        """Test __setitem__ raises IndexError on negative x."""
        with pytest.raises(IndexError):
            self.grid[[-1, 0]] = Square()

    def test_setitem_negative_y(self) -> None:
        """Test __setitem__ raises IndexError on negative y."""
        with pytest.raises(IndexError):
            self.grid[[0, -1]] = Square()

    def test_setitem_negative_both(self) -> None:
        """Test __setitem__ raises IndexError on negative x and y."""
        with pytest.raises(IndexError):
            self.grid[[-1, -1]] = Square()

    def test_setitem_out_of_bounds_x(self) -> None:
        """Test __setitem__ raises IndexError on out-of-bounds x."""
        with pytest.raises(IndexError):
            self.grid[[self.grid.width, 0]] = Square()

    def test_setitem_out_of_bounds_y(self) -> None:
        """Test __setitem__ raises IndexError on out-of-bounds y."""
        with pytest.raises(IndexError):
            self.grid[[0, self.grid.height]] = Square()

    def test_setitem_out_of_bounds_both(self) -> None:
        """Test __setitem__ raises IndexError on out-of-bounds x and y."""
        with pytest.raises(IndexError):
            self.grid[[self.grid.width, self.grid.height]] = Square()

    def test_getitem_negative_x(self) -> None:
        """Test __getitem__ raises IndexError on negative x."""
        with pytest.raises(IndexError):
            _ = self.grid[[-1, 0]]

    def test_getitem_negative_y(self) -> None:
        """Test __getitem__ raises IndexError on negative y."""
        with pytest.raises(IndexError):
            _ = self.grid[[0, -1]]

    def test_getitem_negative_both(self) -> None:
        """Test __getitem__ raises IndexError on negative x and y."""
        with pytest.raises(IndexError):
            _ = self.grid[[-1, -1]]

    def test_getitem_out_of_bounds_x(self) -> None:
        """Test __getitem__ raises IndexError on out-of-bounds x."""
        with pytest.raises(IndexError):
            _ = self.grid[[self.grid.width, 0]]

    def test_getitem_out_of_bounds_y(self) -> None:
        """Test __getitem__ raises IndexError on out-of-bounds y."""
        with pytest.raises(IndexError):
            _ = self.grid[[0, self.grid.height]]

    def test_getitem_out_of_bounds_both(self) -> None:
        """Test __getitem__ raises IndexError on out-of-bounds x and y."""
        with pytest.raises(IndexError):
            _ = self.grid[[self.grid.width, self.grid.height]]


class TestPolyominoRotateError:
    """Tests for Polyomino.rotate() error paths."""

    @pytest.fixture(autouse=True)
    def setup_grid(self) -> None:
        """Set up test grid."""
        config = GameConfig()
        self.grid = Grid(config.board.width, config.board.height)

    def test_rotate_ccw(self) -> None:
        """Test counter-clockwise rotation."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
        original_coords = [coord[:] for coord in tetromino.coords]

        result = tetromino.rotate(Transformation(EigenTransformation.rotation, -1), self.grid)

        assert result is True
        assert tetromino.coords != original_coords

    def test_rotate_multiple_times(self) -> None:
        """Test multiple rotations return to original position."""
        tetromino = copy.deepcopy(tetrominoes[3])
        tetromino.translate([self.grid.width // 2, self.grid.height // 2], self.grid)
        original_coords = [coord[:] for coord in tetromino.coords]

        for _ in range(4):
            tetromino.rotate(Transformation(EigenTransformation.rotation, 1), self.grid)

        assert tetromino.coords == original_coords
