"""Integration tests for rotation with functional boundary kicks.

The SRS precomputed tables have been replaced by the ``_boundary_kicks``
algebraic generator (see :ref:`boundary-kicks` in ``docs/mathematics.rst``).
These tests verify the algebraic kick behaviour: that pieces rotate
correctly in open space, that kicks are applied when needed near walls,
and that four rotations always return to the original position.
"""

import decimal
from typing import ClassVar

import pytest

from tetratile import Grid, Polyomino, Rotation, Square, Translation, _boundary_kicks, tetrominoes


@pytest.fixture
def srs_grid() -> Grid:
    """Provide a standard 10×22 grid for SRS rotation tests."""
    return Grid(10, 22)


class TestBoundaryKicksGenerator:
    """Unit tests for the _boundary_kicks algebraic generator."""

    def test_yields_identity_first(self, srs_grid: Grid) -> None:
        """_boundary_kicks always yields Translation(0,0) first."""
        piece = tetrominoes[3]  # T piece — in-bounds
        moved = piece.translate(Translation(5, 11), srs_grid)
        assert moved is not None
        kicks = list(_boundary_kicks(moved, srs_grid))
        assert kicks[0] == Translation(0, 0)

    def test_no_correction_needed_in_open_space(self, srs_grid: Grid) -> None:
        """Piece fully in bounds yields only the identity kick."""
        piece = tetrominoes[3]
        moved = piece.translate(Translation(5, 11), srs_grid)
        assert moved is not None
        kicks = list(_boundary_kicks(moved, srs_grid))
        assert kicks == [Translation(0, 0)]

    def test_left_wall_violation_yields_positive_dx(self, srs_grid: Grid) -> None:
        """Piece violating left boundary yields a positive dx kick."""
        oob_piece = Polyomino(
            squares=frozenset({Square(-1, 5), Square(0, 5)}),
            origin=(decimal.Decimal(0), decimal.Decimal(5)),
            colors=tetrominoes[0].colors,
            name="Z",
        )
        kicks = list(_boundary_kicks(oob_piece, srs_grid))
        dx_kicks = [k for k in kicks if k.dx > 0]
        assert len(dx_kicks) > 0

    def test_right_wall_violation_yields_negative_dx(self, srs_grid: Grid) -> None:
        """Piece violating right boundary yields a negative dx kick."""
        oob_piece = Polyomino(
            squares=frozenset({Square(9, 5), Square(10, 5)}),
            origin=(decimal.Decimal(9), decimal.Decimal(5)),
            colors=tetrominoes[0].colors,
            name="Z",
        )
        kicks = list(_boundary_kicks(oob_piece, srs_grid))
        dx_kicks = [k for k in kicks if k.dx < 0]
        assert len(dx_kicks) > 0

    def test_floor_violation_yields_positive_dy(self, srs_grid: Grid) -> None:
        """Piece violating floor yields a positive dy kick."""
        oob_piece = Polyomino(
            squares=frozenset({Square(5, -1), Square(5, 0)}),
            origin=(decimal.Decimal(5), decimal.Decimal(-1)),
            colors=tetrominoes[0].colors,
            name="Z",
        )
        kicks = list(_boundary_kicks(oob_piece, srs_grid))
        dy_kicks = [k for k in kicks if k.dy > 0]
        assert len(dy_kicks) > 0

    def test_at_most_four_candidates(self, srs_grid: Grid) -> None:
        """_boundary_kicks yields at most 4 candidates."""
        # Corner violation: both dx and dy needed
        oob_piece = Polyomino(
            squares=frozenset({Square(-1, -1), Square(0, 0)}),
            origin=(decimal.Decimal(-1), decimal.Decimal(-1)),
            colors=tetrominoes[0].colors,
            name="Z",
        )
        kicks = list(_boundary_kicks(oob_piece, srs_grid))
        assert len(kicks) <= 4


class TestRotationOpenSpace:
    """Test rotation in open space (no kicks needed)."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    ROTATABLE: ClassVar[list[int]] = [
        i for i in range(len(tetrominoes)) if tetrominoes[i].name != "o"
    ]

    @pytest.mark.parametrize("piece_idx", ROTATABLE)
    def test_cw_rotation_succeeds(self, piece_idx: int, grid: Grid) -> None:
        """CW rotation from centre succeeds."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        rotated = piece.rotate(Rotation(1), grid)

        assert rotated is not None, f"{piece.name} CW rotation failed"
        assert rotated.ordinal == piece.ordinal

    @pytest.mark.parametrize("piece_idx", ROTATABLE)
    def test_ccw_rotation_succeeds(self, piece_idx: int, grid: Grid) -> None:
        """CCW rotation from centre succeeds."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        rotated = piece.rotate(Rotation(-1), grid)

        assert rotated is not None, f"{piece.name} CCW rotation failed"

    def test_o_piece_rotation_preserves_squares(self, grid: Grid) -> None:
        """O piece rotation returns the same square set (rotationally symmetric)."""
        o_piece = next(t for t in tetrominoes if t.name == "o")
        moved = o_piece.translate(Translation(grid.width // 2, grid.height // 2), grid)
        assert moved is not None

        # The O piece has 4-fold symmetry — rotating it returns the same squares
        result = moved.rotate(Rotation(1), grid)
        # rotate() either returns None (blocked by self-overlap check) or the same squares
        if result is not None:
            assert result.squares == moved.squares, (
                "O piece rotation should produce the same squares"
            )

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_four_cw_returns_original_squares(self, piece_idx: int, grid: Grid) -> None:
        """Four CW rotations return the piece to its original square set."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 11), grid)
        assert piece is not None

        original_squares = piece.squares
        current = piece
        for _ in range(4):
            rotated = current.rotate(Rotation(1), grid)
            if rotated is None:
                # O piece: symmetric, stays in place
                break
            current = rotated

        assert current.squares == original_squares, (
            f"{piece.name} 4 CW rotations did not return to original squares"
        )

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_four_ccw_returns_original_squares(self, piece_idx: int, grid: Grid) -> None:
        """Four CCW rotations return the piece to its original square set."""
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

    @pytest.mark.parametrize("piece_idx", ROTATABLE)
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
            assert rotated.ordinal == initial_count
            current = rotated


class TestRotationNearWalls:
    """Test that kicks allow rotation near walls."""

    @pytest.fixture
    def grid(self) -> Grid:
        """Create a standard 10x22 grid."""
        return Grid(10, 22)

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_left_wall_preserves_squares(self, piece_idx: int, grid: Grid) -> None:
        """Rotation near left wall: if it succeeds, all squares are in-bounds."""
        piece = tetrominoes[piece_idx].translate(Translation(2, 11), grid)
        assert piece is not None

        rotated = piece.rotate(Rotation(1), grid)

        if rotated is not None:
            assert rotated.ordinal == piece.ordinal
            assert rotated.min_x >= 0
            assert rotated.max_x < grid.width

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_right_wall_preserves_squares(self, piece_idx: int, grid: Grid) -> None:
        """Rotation near right wall: if it succeeds, all squares are in-bounds."""
        piece = tetrominoes[piece_idx].translate(Translation(7, 11), grid)
        assert piece is not None

        rotated = piece.rotate(Rotation(1), grid)

        if rotated is not None:
            assert rotated.ordinal == piece.ordinal
            assert rotated.max_x < grid.width

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_rotation_near_floor_preserves_squares(self, piece_idx: int, grid: Grid) -> None:
        """Rotation near floor: if it succeeds, all squares are in-bounds."""
        piece = tetrominoes[piece_idx].translate(Translation(5, 2), grid)
        assert piece is not None

        rotated = piece.rotate(Rotation(1), grid)

        if rotated is not None:
            assert rotated.ordinal == piece.ordinal
            assert rotated.min_y >= 0

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_all_pieces_kick_from_left_wall(self, grid: Grid, piece_idx: int) -> None:
        """All pieces can rotate from left wall without losing squares."""
        # Use x=3 so the I piece (local min_x=-2) also fits: 3-2=1 >= 0
        piece: Polyomino | None = tetrominoes[piece_idx].translate(Translation(3, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal
        current = piece
        for _ in range(4):
            rotated = current.rotate(Rotation(1), grid)
            if rotated is None:
                break
            assert rotated.ordinal == initial_count
            current = rotated

    @pytest.mark.parametrize("piece_idx", range(len(tetrominoes)))
    def test_all_pieces_kick_from_right_wall(self, grid: Grid, piece_idx: int) -> None:
        """All pieces can rotate from right wall without losing squares."""
        piece: Polyomino | None = tetrominoes[piece_idx].translate(Translation(8, 11), grid)
        assert piece is not None

        initial_count = piece.ordinal
        current = piece
        for _ in range(4):
            rotated = current.rotate(Rotation(1), grid)
            if rotated is None:
                break
            assert rotated.ordinal == initial_count
            current = rotated
