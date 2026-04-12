"""Integration tests for configuration."""

from pathlib import Path

import pytest

from tetratile.config import BoardConfig, GameConfig, KeysConfig, _xdg_config_file


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


class TestXdgConfigPath:
    """Tests for XDG config path resolution."""

    def test_default_path_uses_home_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_xdg_config_file() defaults to ~/.config/tetratile/config.toml."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        path = _xdg_config_file()
        assert path == Path.home() / ".config" / "tetratile" / "config.toml"

    def test_xdg_config_home_env_is_honoured(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """_xdg_config_file() uses $XDG_CONFIG_HOME when set."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        path = _xdg_config_file()
        assert path == tmp_path / "tetratile" / "config.toml"

    def test_from_file_no_args_uses_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """GameConfig.from_file() with no arguments resolves to the XDG path."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Write a config into the XDG location first so from_file can read it
        config_dir = tmp_path / "tetratile"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.toml"
        config_file.write_text("[board]\nwidth = 15\n")

        loaded = GameConfig.from_file()
        assert loaded.board.width == 15
        assert loaded.config_file == config_file

    def test_write_to_file_no_args_uses_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """write_to_file() with no arguments writes to the XDG path."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        config = GameConfig()
        config.board.scale = 64
        config.write_to_file()

        expected = tmp_path / "tetratile" / "config.toml"
        assert expected.exists()
        assert config.config_file == expected

        loaded = GameConfig.from_file()
        assert loaded.board.scale == 64


class TestConfigSerialization:
    """Tests for configuration save/load."""

    def test_save_and_load_config(self, tmp_path: Path) -> None:
        """Saving and loading config round-trips correctly.

        ``path`` is the app config directory; the file lands at
        ``path/config.toml``.
        """
        config = GameConfig()
        config.board.scale = 48
        config.board.width = 15
        config.initial_rate = 2.0

        config.write_to_file(tmp_path)

        config_file = tmp_path / "config.toml"
        assert config_file.exists()
        assert config.config_file == config_file

        loaded = GameConfig.from_file(tmp_path)

        assert loaded.board.scale == 48
        assert loaded.board.width == 15
        assert loaded.initial_rate == 2.0
        assert loaded.config_file == config_file

    def test_config_dump_excludes_file_path(self) -> None:
        """config_file is excluded from model_dump serialisation."""
        config = GameConfig()
        config.config_file = Path("/some/config.toml")

        dumped = config.model_dump(exclude={"config_file"})

        assert "config_file" not in dumped

    def test_toml_serialization_roundtrip(self, tmp_path: Path) -> None:
        """TOML serialisation round-trip preserves all config fields."""
        config = GameConfig()
        config.board.width = 20
        config.board.height = 30
        config.kick = True
        config.shadow = "shadow"

        config.write_to_file(tmp_path)

        loaded = GameConfig.from_file(tmp_path)

        assert loaded.board.width == 20
        assert loaded.board.height == 30
        assert loaded.kick is True
        assert loaded.shadow == "shadow"

    def test_create_default_writes_file_when_missing(self, tmp_path: Path) -> None:
        """from_file with create_default=True creates the file if absent."""
        config_file = tmp_path / "config.toml"
        assert not config_file.exists()

        GameConfig.from_file(tmp_path, create_default=True)

        assert config_file.exists()

    def test_from_file_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        """from_file returns defaults when file is missing and create_default=False."""
        loaded = GameConfig.from_file(tmp_path)
        assert loaded.initial_rate == 0.0
        assert loaded.board.width == 10

    def test_config_file_attr_set_to_resolved_path(self, tmp_path: Path) -> None:
        """from_file sets config_file to the full resolved file path."""
        GameConfig.from_file(tmp_path, create_default=True)
        loaded = GameConfig.from_file(tmp_path)
        assert loaded.config_file == tmp_path / "config.toml"


class TestConfigOptions:
    """Tests for game options conversion."""

    def test_config_model_dump_contains_all_fields(self) -> None:
        """model_dump returns all required fields."""
        config = GameConfig()
        dumped = config.model_dump()

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
        """Board dict contains scale, width, height."""
        config = GameConfig()
        dumped = config.model_dump()

        assert "scale" in dumped["board"]
        assert "width" in dumped["board"]
        assert "height" in dumped["board"]

    def test_config_keys_is_dict(self) -> None:
        """keys is returned as a dict."""
        config = GameConfig()
        dumped = config.model_dump()

        assert isinstance(dumped["keys"], dict)
        assert "pause" in dumped["keys"]
        assert "left" in dumped["keys"]
