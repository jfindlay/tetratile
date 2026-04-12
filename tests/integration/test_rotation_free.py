"""Integration tests for free rotation behavior.

Tests rotation in open space (center of standard 10x22 grid) to validate
that piece transformations are correct regardless of initial orientation.
"""

import pytest

from tetratile import Grid, Rotation, Translation, tetrominoes


class TestFreeRotationCW:
    """Test clockwise rotation in open space."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    ROTATABLE_INDICES = [i for i in range(len(tetrominoes)) if tetrominoes[i].name != "o"]

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_spawn(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation from spawn orientation produces valid coordinates."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal
        rotated = piece.rotate(Rotation(1), grid)

        assert rotated is not None, f"{piece.name} rotation from spawn failed"
        assert rotated.ordinal == initial_count, f"{piece.name} lost squares"
        assert rotated.min_x >= 0
        assert rotated.max_x < grid.width
        assert rotated.min_y >= 0
        assert rotated.max_y < grid.height

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_state_1(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation after one CW rotation produces valid coordinates."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        r1 = piece.rotate(Rotation(1), grid)
        assert r1 is not None

        initial_count = r1.ordinal
        r2 = r1.rotate(Rotation(1), grid)

        assert r2 is not None, f"{piece.name} rotation from state 1 failed"
        assert r2.ordinal == initial_count
        assert r2.min_x >= 0
        assert r2.max_x < grid.width

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_state_2(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation after two CW rotations produces valid coordinates."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        current = piece
        for _ in range(2):
            rotated = current.rotate(Rotation(1), grid)
            assert rotated is not None
            current = rotated

        initial_count = current.ordinal
        result = current.rotate(Rotation(1), grid)

        assert result is not None, f"{piece.name} rotation from state 2 failed"
        assert result.ordinal == initial_count

    @pytest.mark.parametrize("piece_idx", ROTATABLE_INDICES)
    def test_cw_rotation_from_state_3(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation after three CW rotations produces valid coordinates."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        current = piece
        for _ in range(3):
            rotated = current.rotate(Rotation(1), grid)
            assert rotated is not None
            current = rotated

        initial_count = current.ordinal
        result = current.rotate(Rotation(1), grid)

        assert result is not None, f"{piece.name} rotation from state 3 failed"
        assert result.ordinal == initial_count


class TestFreeRotationCCW:
    """Test counter-clockwise rotation in open space."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_ccw_rotation_from_spawn(self, piece_idx: int, grid: Grid) -> None:
        """CCW rotation from spawn orientation produces valid coordinates."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal
        result = piece.rotate(Rotation(-1), grid)

        if piece.name == "o":
            # O piece is symmetric; rotation either returns None or same squares
            if result is not None:
                assert result.squares == piece.squares
            return

        assert result is not None, f"{piece.name} CCW rotation from spawn failed"
        assert result.ordinal == initial_count
        assert result.min_x >= 0
        assert result.max_x < grid.width


class TestFourRotationsReturn:
    """Test that four rotations return to original position."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_four_cw_returns_original(self, piece_idx: int, grid: Grid) -> None:
        """Four CW rotations return piece to original square set."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        original_squares = piece.squares
        current = piece
        for _ in range(4):
            rotated = current.rotate(Rotation(1), grid)
            if rotated is None:
                break
            current = rotated

        assert current.squares == original_squares, f"{piece.name} 4 CW rotations did not return to original squares"

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_four_ccw_returns_original(self, piece_idx: int, grid: Grid) -> None:
        """Four CCW rotations return piece to original square set."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        original_squares = piece.squares
        current = piece
        for _ in range(4):
            rotated = current.rotate(Rotation(-1), grid)
            if rotated is None:
                break
            current = rotated

        assert current.squares == original_squares


class TestPieceCountPreserved:
    """Test that rotation preserves the same number of squares."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_preserves_square_count(self, piece_idx: int, grid: Grid) -> None:
        """Rotation preserves the number of squares."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal
        current = piece
        for _ in range(4):
            rotated = current.rotate(Rotation(1), grid)
            if rotated is None:
                break
            assert rotated.ordinal == initial_count, f"{piece.name} lost squares"
            current = rotated
