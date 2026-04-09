"""Integration tests for free rotation behavior.

Tests rotation in open space (center of standard 10x22 grid) to validate
that piece transformations are correct regardless of initial orientation.
"""

import copy

import pytest

from tetratile import Grid, Tetromino, tetrominoes


class TestFreeRotationCW:
    """Test clockwise rotation in open space."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    # Non-rotatable pieces (O doesn't rotate)
    ROTATABLE_INDICES = [i for i in range(len(tetrominoes)) if tetrominoes[i].name != "o"]

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_state_0(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation from state 0 produces valid coordinates."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)  # Center of grid

        initial_count = len(piece.coords)
        result = piece.srs_rotate(1, grid)

        assert result is True, f"{piece.name} rotation from state 0 failed"
        assert len(piece.coords) == initial_count, f"{piece.name} lost squares"
        # Verify all coords are in bounds
        for coord in piece.coords:
            assert 0 <= coord[0] < grid.width, f"{piece.name} x out of bounds: {coord}"
            assert 0 <= coord[1] < grid.height, f"{piece.name} y out of bounds: {coord}"

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_state_1(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation from state 1 produces valid coordinates."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        # First rotate to state 1
        piece.srs_rotate(1, grid)
        assert piece.rotation_state == 1

        # Now rotate from state 1
        initial_count = len(piece.coords)
        result = piece.srs_rotate(1, grid)

        assert result is True, f"{piece.name} rotation from state 1 failed"
        assert len(piece.coords) == initial_count
        for coord in piece.coords:
            assert 0 <= coord[0] < grid.width
            assert 0 <= coord[1] < grid.height

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_state_2(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation from state 2 produces valid coordinates."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        # Rotate to state 2
        piece.srs_rotate(1, grid)
        piece.srs_rotate(1, grid)
        assert piece.rotation_state == 2

        initial_count = len(piece.coords)
        result = piece.srs_rotate(1, grid)

        assert result is True, f"{piece.name} rotation from state 2 failed"
        assert len(piece.coords) == initial_count

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_state_3(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation from state 3 produces valid coordinates."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        # Rotate to state 3
        for _ in range(3):
            piece.srs_rotate(1, grid)
        assert piece.rotation_state == 3

        initial_count = len(piece.coords)
        result = piece.srs_rotate(1, grid)

        assert result is True, f"{piece.name} rotation from state 3 failed"
        assert len(piece.coords) == initial_count


class TestFreeRotationCCW:
    """Test counter-clockwise rotation in open space."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_ccw_rotation_from_state_0(self, piece_idx: int, grid: Grid) -> None:
        """CCW rotation from state 0 produces valid coordinates."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        initial_count = len(piece.coords)
        result = piece.srs_rotate(-1, grid)

        # Skip O piece which doesn't rotate
        if piece.name == "o":
            assert result is False
            return

        assert result is True, f"{piece.name} CCW rotation from state 0 failed"
        assert len(piece.coords) == initial_count
        for coord in piece.coords:
            assert 0 <= coord[0] < grid.width
            assert 0 <= coord[1] < grid.height


class TestFourRotationsReturn:
    """Test that four rotations return to original position."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_four_cw_returns_original(self, piece_idx: int, grid: Grid) -> None:
        """Four CW rotations return piece to original position."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        original_coords = [c[:] for c in piece.coords]
        original_state = piece.rotation_state

        # Four CW rotations
        for _ in range(4):
            piece.srs_rotate(1, grid)

        assert piece.coords == original_coords, (
            f"{piece.name} 4 CW rotations did not return to original: expected {original_coords}, got {piece.coords}"
        )
        assert piece.rotation_state == original_state

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_four_ccw_returns_original(self, piece_idx: int, grid: Grid) -> None:
        """Four CCW rotations return piece to original position."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        original_coords = [c[:] for c in piece.coords]
        original_state = piece.rotation_state

        # Four CCW rotations
        for _ in range(4):
            piece.srs_rotate(-1, grid)

        assert piece.coords == original_coords
        assert piece.rotation_state == original_state


class TestPieceCountPreserved:
    """Test that rotation preserves the same number of squares."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_preserves_square_count(self, piece_idx: int, grid: Grid) -> None:
        """Rotation preserves the same number of squares."""
        piece = copy.deepcopy(tetrominoes[piece_idx])
        piece.translate([5, 11], grid)

        initial_count = len(piece.coords)

        # Do a full rotation cycle
        for _ in range(4):
            piece.srs_rotate(1, grid)

        assert len(piece.coords) == initial_count, f"{piece.name} lost squares: {initial_count} -> {len(piece.coords)}"
