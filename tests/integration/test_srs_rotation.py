"""Integration tests for SRS rotation system."""

import copy
import random

from tetratile import (
    Grid,
    tetrominoes,
)


class TestSRSRotation:
    """Tests for SRS rotation behavior."""

    def test_rotation_state_cycles_four_times(self, grid: Grid) -> None:
        """Test that rotation state cycles correctly through 0,1,2,3,0."""
        non_o = [t for t in tetrominoes if t.name != "o"]
        tetromino = copy.deepcopy(random.choice(non_o))
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        assert tetromino.rotation_state == 0

        for expected_state in [1, 2, 3, 0, 1, 2, 3, 0]:
            tetromino.srs_rotate(1, grid)
            assert tetromino.rotation_state == expected_state

    def test_o_piece_does_not_rotate(self, grid: Grid) -> None:
        """Test that O piece returns False on rotation attempts."""
        o_piece = copy.deepcopy(tetrominoes[4])  # o is 5th
        o_piece.translate([grid.width // 2, grid.height // 2], grid)

        initial_coords = [c[:] for c in o_piece.coords]
        initial_state = o_piece.rotation_state

        result = o_piece.srs_rotate(1, grid)

        assert result is False
        assert o_piece.rotation_state == initial_state
        assert o_piece.coords == initial_coords

    def test_i_piece_uses_correct_kick_table(self, grid: Grid) -> None:
        """Test that I piece uses I-specific kick table."""
        l_piece = copy.deepcopy(tetrominoes[2])  # l (I) is 3rd
        l_piece.translate([grid.width // 2, grid.height // 2], grid)

        kick_table = l_piece._get_kick_table()
        assert kick_table is not None
        assert len(kick_table[(0, 1)]) == 5

    def test_jlstz_pieces_use_correct_kick_table(self, grid: Grid) -> None:
        """Test that J/L/S/T/Z pieces use JLSTZ kick table."""
        for t in [tetrominoes[0], tetrominoes[1], tetrominoes[3], tetrominoes[5], tetrominoes[6]]:
            piece = copy.deepcopy(t)
            piece.translate([grid.width // 2, grid.height // 2], grid)

            kick_table = piece._get_kick_table()
            assert kick_table is not None
            assert len(kick_table[(0, 1)]) == 5

    def test_kicks_applied_in_order(self, grid: Grid) -> None:
        """Test that kick offsets are tried in correct order."""
        tetromino = copy.deepcopy(tetrominoes[3])  # T piece
        tetromino.translate([2, grid.height // 2], grid)  # Near left wall

        initial_state = tetromino.rotation_state
        initial_coords = [c[:] for c in tetromino.coords]

        result = tetromino.srs_rotate(1, grid)

        assert result is True
        assert tetromino.rotation_state == (initial_state + 1) % 4
        assert tetromino.coords != initial_coords

    def test_four_rotations_return_to_original_position(self, grid: Grid) -> None:
        """Test that 4 rotations returns piece to original orientation."""
        non_o = [t for t in tetrominoes if t.name != "o"]
        for tetromino_type in non_o:
            tetromino = copy.deepcopy(tetromino_type)
            tetromino.translate([grid.width // 2, grid.height // 2], grid)

            original_coords = [c[:] for c in tetromino.coords]
            original_state = tetromino.rotation_state

            for _ in range(4):
                tetromino.srs_rotate(1, grid)

            assert tetromino.coords == original_coords
            assert tetromino.rotation_state == original_state

    def test_ccw_rotation_works(self, grid: Grid) -> None:
        """Test counter-clockwise rotation."""
        tetromino = copy.deepcopy(tetrominoes[3])  # T piece
        tetromino.translate([grid.width // 2, grid.height // 2], grid)

        original_state = tetromino.rotation_state
        original_coords = [c[:] for c in tetromino.coords]

        result = tetromino.srs_rotate(-1, grid)

        assert result is True
        assert tetromino.rotation_state == (original_state - 1) % 4
        assert tetromino.coords != original_coords

    def test_all_tetrominoes_have_srs_center(self) -> None:
        """Test that all tetrominoes have SRS center defined."""
        for t in tetrominoes:
            assert t.o is not None
            assert len(t.o) == 2
