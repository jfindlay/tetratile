"""Integration tests for edge rotation behavior.

Tests rotation near grid edges (walls, floor, ceiling) and near stacks
to validate that boundary kicks work correctly and no squares are lost.
"""

import random

import pytest

from tetratile import Grid, Polyomino, Rotation, Square, Translation, tetrominoes


class TestLeftWallRotation:
    """Test rotation near the left wall."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_left_wall(self, piece_idx: int, grid: Grid) -> None:
        """Rotation near left wall preserves all squares."""
        piece = tetrominoes[piece_idx].translate(Translation(2, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal
        rotated = piece.rotate(Rotation(1), grid)

        if rotated is not None:
            assert rotated.ordinal == initial_count, (
                f"{piece.name} lost squares near left wall: {initial_count} -> {rotated.ordinal}"
            )
            assert rotated.min_x >= 0, f"{piece.name} x < 0 after left wall rotation"
            assert rotated.max_x < grid.width


class TestRightWallRotation:
    """Test rotation near the right wall."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_right_wall(self, piece_idx: int, grid: Grid) -> None:
        """Rotation near right wall preserves all squares."""
        piece = tetrominoes[piece_idx].translate(Translation(7, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal
        rotated = piece.rotate(Rotation(1), grid)

        if rotated is not None:
            assert rotated.ordinal == initial_count
            assert rotated.max_x < grid.width, f"{piece.name} x >= width after right wall rotation"


class TestFloorRotation:
    """Test rotation near the floor."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_floor(self, piece_idx: int, grid: Grid) -> None:
        """Rotation near floor preserves all squares."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 2), grid)
        assert piece is not None

        initial_count = piece.ordinal
        rotated = piece.rotate(Rotation(1), grid)

        if rotated is not None:
            assert rotated.ordinal == initial_count
            assert rotated.min_y >= 0, f"{piece.name} y < 0 after floor rotation"


class TestCeilingRotation:
    """Test rotation near the ceiling."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_ceiling(self, piece_idx: int, grid: Grid) -> None:
        """Rotation near ceiling preserves all squares."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 18), grid)
        assert piece is not None

        initial_count = piece.ordinal
        rotated = piece.rotate(Rotation(1), grid)

        if rotated is not None:
            assert rotated.ordinal == initial_count
            assert rotated.max_y < grid.height, f"{piece.name} y >= height after ceiling rotation"


class TestStackRotation:
    """Test rotation near a random stack."""

    @pytest.fixture
    def grid_with_stack(self) -> Grid:
        """Create grid with a random stack at the bottom."""
        grid = Grid(10, 22)
        rng = random.Random(42)
        for y in range(4):
            for x in range(10):
                if rng.random() > 0.5:
                    grid[Square(x, y)] = rng.choice(["Z", "S", "l", "T", "o", "L", "J"])
        return grid

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_stack(self, piece_idx: int, grid_with_stack: Grid) -> None:
        """Rotation near stack preserves all squares."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 6), grid_with_stack)
        assert piece is not None

        initial_count = piece.ordinal
        rotated = piece.rotate(Rotation(1), grid_with_stack)

        if rotated is not None:
            assert rotated.ordinal == initial_count


class TestWallKickPreservesSquares:
    """Test that boundary kicks preserve all squares."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard grid."""
        return Grid(10, 22)

    def test_all_pieces_kick_from_left_wall(self, grid: Grid) -> None:
        """All pieces can kick from left wall without losing squares."""
        for piece_type in tetrominoes:
            # Use x=3 so the I piece (local min_x=-2) also fits: 3-2=1 >= 0
            current: Polyomino | None = piece_type.translate(Translation(3, 11), grid)
            assert current is not None

            initial_count = current.ordinal
            for _ in range(4):
                rotated = current.rotate(Rotation(1), grid)
                if rotated is None:
                    break
                assert rotated.ordinal == initial_count, f"{current.name} lost squares during left wall rotation"
                current = rotated

    def test_all_pieces_kick_from_right_wall(self, grid: Grid) -> None:
        """All pieces can kick from right wall without losing squares."""
        for piece_type in tetrominoes:
            current: Polyomino | None = piece_type.translate(Translation(8, 11), grid)
            assert current is not None

            initial_count = current.ordinal
            for _ in range(4):
                rotated = current.rotate(Rotation(1), grid)
                if rotated is None:
                    break
                assert rotated.ordinal == initial_count, f"{current.name} lost squares during right wall rotation"
                current = rotated
