"""Integration tests for edge rotation behavior.

Tests rotation near grid edges (walls, floor, ceiling) and near stacks
to validate that wall kicks work correctly and no squares are lost.
"""

import copy
import random

import pytest

from tetratile import Grid, tetrominoes


class TestLeftWallRotation:
    """Test rotation near the left wall."""

    @pytest.fixture
    def grid_with_left_wall(self) -> Grid:
        """Create grid with piece near left wall."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_left_wall(self, piece_idx: int, grid_with_left_wall: Grid) -> None:
        """Rotation near left wall preserves all squares."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        # Position near left wall
        piece.translate([2, 11], grid_with_left_wall)

        initial_count = len(piece.coords)
        initial_coords = [c[:] for c in piece.coords]

        # Try to rotate
        result = piece.srs_rotate(1, grid_with_left_wall)

        if result:
            # If rotation succeeded, verify no squares lost
            assert len(piece.coords) == initial_count, (
                f"{piece.name} lost squares near left wall: {initial_count} -> {len(piece.coords)}"
            )
            # Verify all coords are in bounds
            for coord in piece.coords:
                assert coord[0] >= 0, f"{piece.name} x < 0 after left wall rotation: {coord}"
                assert coord[0] < grid_with_left_wall.width


class TestRightWallRotation:
    """Test rotation near the right wall."""

    @pytest.fixture
    def grid_with_right_wall(self) -> Grid:
        """Create grid with piece near right wall."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_right_wall(self, piece_idx: int, grid_with_right_wall: Grid) -> None:
        """Rotation near right wall preserves all squares."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        # Position near right wall
        piece.translate([7, 11], grid_with_right_wall)

        initial_count = len(piece.coords)

        result = piece.srs_rotate(1, grid_with_right_wall)

        if result:
            assert len(piece.coords) == initial_count
            for coord in piece.coords:
                assert coord[0] < grid_with_right_wall.width, f"{piece.name} x >= width after right wall rotation: {coord}"


class TestFloorRotation:
    """Test rotation near the floor."""

    @pytest.fixture
    def grid_with_floor(self) -> Grid:
        """Create grid with piece near floor."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_floor(self, piece_idx: int, grid_with_floor: Grid) -> None:
        """Rotation near floor preserves all squares."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        # Position near bottom
        piece.translate([5, 2], grid_with_floor)

        initial_count = len(piece.coords)

        result = piece.srs_rotate(1, grid_with_floor)

        if result:
            assert len(piece.coords) == initial_count
            for coord in piece.coords:
                assert coord[1] >= 0, f"{piece.name} y < 0 after floor rotation: {coord}"


class TestCeilingRotation:
    """Test rotation near the ceiling."""

    @pytest.fixture
    def grid_with_ceiling(self) -> Grid:
        """Create grid with piece near ceiling."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_ceiling(self, piece_idx: int, grid_with_ceiling: Grid) -> None:
        """Rotation near ceiling preserves all squares."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        # Position near top
        piece.translate([5, 18], grid_with_ceiling)

        initial_count = len(piece.coords)

        result = piece.srs_rotate(1, grid_with_ceiling)

        if result:
            assert len(piece.coords) == initial_count
            for coord in piece.coords:
                assert coord[1] < grid_with_ceiling.height, f"{piece.name} y >= height after ceiling rotation: {coord}"


class TestStackRotation:
    """Test rotation near a random stack."""

    @pytest.fixture
    def grid_with_stack(self) -> Grid:
        """Create grid with a random stack at the bottom."""
        grid = Grid(10, 22)
        # Create a semi-random stack in bottom rows
        rng = random.Random(42)  # Fixed seed for reproducibility
        for y in range(4):
            for x in range(10):
                if rng.random() > 0.5:
                    grid[x, y].type = rng.choice(["Z", "S", "l", "T", "o", "L", "J"])
        return grid

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_stack(self, piece_idx: int, grid_with_stack: Grid) -> None:
        """Rotation near stack preserves all squares."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        # Position just above stack
        piece.translate([5, 6], grid_with_stack)

        initial_count = len(piece.coords)

        result = piece.srs_rotate(1, grid_with_stack)

        if result:
            assert len(piece.coords) == initial_count


class TestWallKickPreservesSquares:
    """Test that wall kicks preserve all squares."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create standard grid."""
        return Grid(10, 22)

    def test_all_pieces_kick_from_left_wall(self, grid: Grid) -> None:
        """All pieces can kick from left wall without losing squares."""
        for piece_idx in range(len(tetrominoes)):
            piece = copy.deepcopy(tetrominoes[piece_idx])
            piece.translate([1, 11], grid)

            initial_count = len(piece.coords)

            for _ in range(4):
                piece.srs_rotate(1, grid)
                assert len(piece.coords) == initial_count, f"{piece.name} lost squares during left wall rotation"

    def test_all_pieces_kick_from_right_wall(self, grid: Grid) -> None:
        """All pieces can kick from right wall without losing squares."""
        for piece_idx in range(len(tetrominoes)):
            piece = copy.deepcopy(tetrominoes[piece_idx])
            piece.translate([8, 11], grid)

            initial_count = len(piece.coords)

            for _ in range(4):
                piece.srs_rotate(1, grid)
                assert len(piece.coords) == initial_count, f"{piece.name} lost squares during right wall rotation"
