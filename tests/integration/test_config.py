"""Integration tests for configuration."""

from pathlib import Path

import pytest

from tetratile.config import BoardConfig, GameConfig, KeysConfig


class TestConfigDefaults:
    """Tests for default configuration values."""

    def test_default_board_config(self) -> None:
        """Test default board configuration."""
        config = BoardConfig()

        assert config.scale == 32
        assert config.width == 10
        assert config.height == 22

    def test_default_keys_config(self) -> None:
        """Test default keyboard configuration."""
        keys = KeysConfig()

        assert keys.pause == "p"
        assert keys.left == ","
        assert keys.right == "."
        assert keys.down == "x"
        assert keys.rotate_left == "m"
        assert keys.rotate_right == "v"
        assert keys.drop == "c"
        assert keys.lock == "l"

    def test_default_game_config(self) -> None:
        """Test default game configuration."""
        config = GameConfig()

        assert config.debug is False
        assert config.initial_rate == 0.0
        assert config.min_rate == 0.0
        assert config.remove_freq == 1
        assert config.constant is False
        assert config.shadow == "projection"
        assert config.kick is False
        assert config.stack_transparency is False
        assert config.screen_scale is True

    def test_shadow_literal_values(self) -> None:
        """Test shadow config accepts only valid values."""
        config = GameConfig()

        config.shadow = "none"
        assert config.shadow == "none"

        config.shadow = "projection"
        assert config.shadow == "projection"

        config.shadow = "shadow"
        assert config.shadow == "shadow"


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_initial_rate_at_least_min_rate(self) -> None:
        """Test that initial_rate must be >= min_rate."""
        config = GameConfig()
        config.min_rate = 2.0
        config.initial_rate = 1.0

        with pytest.raises(ValueError, match="initial_rate must be >= min_rate"):
            config.model_validate(config.model_dump())

    def test_board_scale_must_be_positive(self) -> None:
        """Test that board scale must be positive."""
        with pytest.raises(ValueError):
            BoardConfig(scale=0)

    def test_board_width_must_be_positive(self) -> None:
        """Test that board width must be positive."""
        with pytest.raises(ValueError):
            BoardConfig(width=0)

    def test_remove_freq_must_be_positive(self) -> None:
        """Test that remove frequency must be positive."""
        with pytest.raises(ValueError):
            GameConfig(remove_freq=0)


class TestConfigSerialization:
    """Tests for configuration save/load."""

    def test_save_and_load_config(self, tmp_path: Path) -> None:
        """Test saving and loading configuration."""
        config = GameConfig()
        config.board.scale = 48
        config.board.width = 15
        config.initial_rate = 2.0

        path = tmp_path / "tetratile"
        config.write_to_file(path)

        config_file = path / "tetratile" / "tetratile.toml"
        assert config_file.exists()

        loaded = GameConfig.from_file(path)

        assert loaded.board.scale == 48
        assert loaded.board.width == 15
        assert loaded.initial_rate == 2.0

    def test_config_dump_excludes_file_path(self) -> None:
        """Test that config_file is excluded from serialization."""
        config = GameConfig()
        config.config_file = Path("/some/path.toml")

        dumped = config.model_dump(exclude={"config_file"})

        assert "config_file" not in dumped

    def test_toml_serialization_roundtrip(self, tmp_path: Path) -> None:
        """Test TOML serialization roundtrip."""
        config = GameConfig()
        config.board.width = 20
        config.board.height = 30
        config.kick = True
        config.shadow = "shadow"

        path = tmp_path / "tetratile"
        config.write_to_file(path)

        loaded = GameConfig.from_file(path)

        assert loaded.board.width == 20
        assert loaded.board.height == 30
        assert loaded.kick is True
        assert loaded.shadow == "shadow"


class TestConfigOptions:
    """Tests for game options conversion."""

    def test_config_model_dump_contains_all_fields(self) -> None:
        """Test that model_dump returns all required fields."""
        config = GameConfig()
        dumped = config.model_dump()

        assert "debug" in dumped
        assert "board" in dumped
        assert "epsilon" in dumped
        assert "min_rate" in dumped
        assert "initial_rate" in dumped
        assert "remove_freq" in dumped
        assert "constant" in dumped
        assert "shadow" in dumped
        assert "kick" in dumped
        assert "stack_transparency" in dumped
        assert "screen_scale" in dumped
        assert "keys" in dumped

    def test_config_board_contains_dimensions(self) -> None:
        """Test that board dict contains scale, width, height."""
        config = GameConfig()
        dumped = config.model_dump()

        assert "scale" in dumped["board"]
        assert "width" in dumped["board"]
        assert "height" in dumped["board"]

    def test_config_keys_is_dict(self) -> None:
        """Test that keys is returned as dict."""
        config = GameConfig()
        dumped = config.model_dump()

        assert isinstance(dumped["keys"], dict)
        assert "pause" in dumped["keys"]
        assert "left" in dumped["keys"]
