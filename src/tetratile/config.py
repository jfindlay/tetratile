"""Configuration management using Pydantic for validation."""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator


def _dict_to_toml(data: dict[str, Any], indent: int = 0) -> str:
    """Convert a dictionary to TOML format.

    :param data: Dictionary to convert.
    :param indent: Current indentation level.
    :returns: TOML-formatted string.
    """
    lines: list[str] = []
    prefix = "    " * indent

    scalars: list[tuple[str, Any]] = []
    tables: list[tuple[str, dict[str, Any]]] = []

    for key, value in data.items():
        if isinstance(value, dict):
            tables.append((key, value))
        else:
            scalars.append((key, value))

    for key, value in scalars:
        if isinstance(value, bool):
            lines.append(f"{prefix}{key} = {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"{prefix}{key} = {value}")
        elif isinstance(value, str):
            lines.append(f'{prefix}{key} = "{value}"')
        else:
            lines.append(f'{prefix}{key} = "{value}"')

    for key, value in tables:
        lines.append(f"{prefix}[{key}]")
        lines.append(_dict_to_toml(value, indent))

    return "\n".join(lines)


class KeysConfig(BaseModel):
    """Keyboard key bindings for game controls.

    :attr pause: Key to pause the game.
    :attr left: Key to move piece left.
    :attr right: Key to move piece right.
    :attr left_side: Key to move piece to left edge.
    :attr right_side: Key to move piece to right edge.
    :attr rotate_left: Key to rotate piece counterclockwise.
    :attr rotate_right: Key to rotate piece clockwise.
    :attr down: Key to move piece down.
    :attr drop: Key to drop piece to bottom.
    :attr lock: Key to lock piece in place.
    """

    pause: str = "p"
    left: str = ","
    right: str = "."
    left_side: str = "z"
    right_side: str = "/"
    rotate_left: str = "m"
    rotate_right: str = "v"
    down: str = "x"
    drop: str = "c"
    lock: str = "l"


class BoardConfig(BaseModel):
    """Game board configuration.

    :attr scale: Pixels per block.
    :attr width: Blocks wide.
    :attr height: Blocks tall.
    """

    scale: int = Field(default=32, ge=1)
    width: int = Field(default=10, ge=1)
    height: int = Field(default=22, ge=1)


class GameConfig(BaseModel):
    """Main game configuration with Pydantic validation.

    :attr config_file: Path to config file (excluded from serialization).
    :attr board: Board dimensions and scale.
    :attr epsilon: Floating point epsilon for rate calculations.
    :attr min_rate: Minimum fall rate.
    :attr initial_rate: Initial fall rate (0 = manual only).
    :attr remove_freq: Cycles between row removal.
    :attr constant: Whether to keep constant fall rate.
    :attr shadow: Shadow display type (none, projection, or shadow).
    :attr kick: Enable kick moves for rotations.
    :attr stack_transparency: Mix stack colors with black for depth.
    :attr screen_scale: Auto-calculate scale from screen size.
    :attr keys: Keyboard key bindings.
    """

    config_file: Path | None = Field(default=None, exclude=True)
    board: BoardConfig = Field(default_factory=BoardConfig)
    epsilon: float = Field(default_factory=lambda: sys.float_info.epsilon * 3)
    min_rate: float = Field(default=0.0, ge=0.0)
    initial_rate: float = Field(default=0.0, ge=0.0)
    remove_freq: int = Field(default=1, ge=1)
    constant: bool = False
    shadow: Literal["none", "projection", "shadow"] = "projection"
    kick: bool = False
    stack_transparency: bool = False
    screen_scale: bool = True
    keys: KeysConfig = Field(default_factory=KeysConfig)

    @field_validator("initial_rate")
    @classmethod
    def initial_rate_must_be_at_least_min_rate(cls, v: float, info: ValidationInfo) -> float:
        """Validate that initial_rate is at least min_rate.

        :param v: The initial_rate value.
        :param info: Pydantic validation info.
        :returns: The validated value.
        :raises ValueError: If initial_rate is less than min_rate.
        """
        if "min_rate" in info.data and v < info.data["min_rate"]:
            raise ValueError("initial_rate must be >= min_rate")
        return v

    @model_validator(mode="after")
    def set_xdg_config_path(self) -> GameConfig:
        """Set default config file path based on XDG conventions.

        :returns: Self with config_file set.
        """
        if self.config_file is None:
            if "XDG_CONFIG_HOME" in os.environ:
                self.config_file = Path(os.environ["XDG_CONFIG_HOME"])
            elif "HOME" in os.environ:
                self.config_file = Path(os.environ["HOME"]) / ".config"
            else:
                self.config_file = Path(".config")
        return self

    def write_to_file(self, path: Path | None = None) -> None:
        """Write configuration to TOML file.

        :param path: Directory to write config file. Uses config_file if None.
        :raises ValueError: If no path is specified and config_file is None.
        """
        target = path or self.config_file
        if target is None:
            raise ValueError("No config file path specified")
        target = Path(target) / "tetratile" / "tetratile.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w") as f:
            f.write(_dict_to_toml(self.model_dump(exclude_none=True)))

    @classmethod
    def from_file(cls, path: Path, *, create_default: bool = False) -> GameConfig:
        """Load configuration from TOML file with defaults.

        :param path: Directory containing tetratile.toml.
        :param create_default: If True, create default config file if missing.
        :returns: Configuration from file or defaults.
        """
        config = cls()
        config.config_file = path
        config_file = path / "tetratile" / "tetratile.toml"
        if config_file.exists():
            try:
                with open(config_file, "rb") as f:
                    data = tomllib.load(f)
                config = cls.model_validate(data)
                config.config_file = path
            except Exception:
                config = cls()
                config.config_file = path
                if create_default:
                    config.write_to_file()
        elif create_default:
            config.write_to_file()
        return config


class GameOptions(TypedDict):
    """Typed dictionary for game options passed to TetraTile.

    :attr scale: Pixels per block.
    :attr board: Board dimensions (scale, width, height).
    :attr epsilon: Floating point epsilon.
    :attr min_rate: Minimum fall rate.
    :attr initial_rate: Initial fall rate.
    :attr remove_freq: Cycles between row removal.
    :attr constant: Whether rate is constant.
    :attr shadow: Shadow type (none, projection, shadow).
    :attr kick: Enable kick moves.
    :attr stack_transparency: Mix stack colors with black.
    :attr screen_scale: Auto-calculate scale from screen size.
    :attr keys: Key bindings.
    """

    scale: int
    board: dict[str, int]
    epsilon: float
    min_rate: float
    initial_rate: float
    remove_freq: int
    constant: bool
    shadow: str
    kick: bool
    stack_transparency: bool
    screen_scale: bool
    keys: dict[str, str]


class Config:
    """Config wrapper that provides opts dict compatible with TetraTile.

    :attr opts: Configuration options dictionary.
    """

    def __init__(self, test: bool = False) -> None:
        """Initialize the config.

        :param test: If True, use default config. Otherwise parse CLI args.
        """
        self.test = test
        self.opts: GameOptions = self.get_opts()

    def get_opts(self) -> GameOptions:
        """Get configuration options as a dictionary.

        :returns: Configuration options for TetraTile.
        """
        if self.test:
            config = GameConfig()
        else:
            args = _parse_args()
            config_path = args.config_file
            config = GameConfig.from_file(Path(config_path) if config_path else Path.cwd())
            if args.size is not None:
                config.board.width = args.size["width"]
                config.board.height = args.size["height"]
            if args.scale is not None:
                config.board.scale = args.scale
            if args.initial_rate is not None:
                config.initial_rate = args.initial_rate
            if args.constant:
                config.constant = args.constant

        opts: GameOptions = {
            "scale": config.board.scale,
            "board": {
                "scale": config.board.scale,
                "width": config.board.width,
                "height": config.board.height,
            },
            "epsilon": config.epsilon,
            "min_rate": config.min_rate,
            "initial_rate": config.initial_rate,
            "remove_freq": config.remove_freq,
            "constant": config.constant,
            "shadow": config.shadow,
            "kick": config.kick,
            "stack_transparency": config.stack_transparency,
            "screen_scale": config.screen_scale,
            "keys": config.keys.model_dump(),
        }
        return opts


_VERSION: str = importlib.metadata.version("tetratile")


def _parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    :returns: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Polyomino tessellation game",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog) {_VERSION}")
    parser.add_argument("-c", "--config-file", type=Path, help="Directory containing config file")
    parser.add_argument("-s", "--size", type=_parse_size, help="Board size WxH")
    parser.add_argument("-a", "--scale", type=int, help="Board scale pixels/block")
    parser.add_argument("-r", "--initial-rate", type=float, help="Initial rate blocks/second")
    parser.add_argument("-o", "--constant", action="store_true", help="Do not increase game rate")

    return parser.parse_args()


def _parse_size(arg: str) -> dict[str, int]:
    """Parse size argument like '10x20'.

    :param arg: Size string in WxH format.
    :returns: {"width": W, "height": H}.
    :raises argparse.ArgumentTypeError: If format is invalid or values are not positive.
    """
    match = re.match(r"(?P<width>\d+)[xX](?P<height>\d+)", arg)
    if not match:
        raise argparse.ArgumentTypeError(f"Invalid size format: {arg}")
    width = int(match.group("width"))
    height = int(match.group("height"))
    if width < 1 or height < 1:
        raise argparse.ArgumentTypeError("Size must be positive")
    return {"width": width, "height": height}
