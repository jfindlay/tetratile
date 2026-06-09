"""Configuration management using Pydantic for validation.

The default configuration file is located at the XDG-compliant path
``$XDG_CONFIG_HOME/tetratile/config.toml``, falling back to
``~/.config/tetratile/config.toml`` when ``XDG_CONFIG_HOME`` is unset.
Use :func:`_xdg_config_file` to resolve this path programmatically.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


def _xdg_config_file() -> Path:
    """Return the XDG-compliant default configuration file path.

    Resolves to ``$XDG_CONFIG_HOME/tetratile/config.toml``, falling back
    to ``~/.config/tetratile/config.toml`` when ``XDG_CONFIG_HOME`` is
    unset, per the `XDG Base Directory Specification
    <https://specifications.freedesktop.org/basedir-spec/latest/>`_.

    :returns: Absolute path to the default configuration file.
    """
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "tetratile" / "config.toml"


def _dict_to_toml(
    data: dict[str, bool | int | float | str | dict[str, object]], indent: int = 0
) -> str:
    """Serialise a plain dictionary to TOML format.

    Scalar values are emitted before nested tables so that the output
    conforms to the TOML specification (scalars must precede ``[table]``
    headers at each level).

    :param data: Dictionary to serialise. Values may be scalar scalars
        (``bool``, ``int``, ``float``, ``str``) or nested ``dict`` tables.
    :param indent: Current indentation level (unused in flat TOML output).
    :returns: TOML-formatted string.
    """
    lines: list[str] = []
    prefix = "    " * indent

    scalars: list[tuple[str, bool | int | float | str]] = []
    tables: list[tuple[str, dict[str, object]]] = []

    for key, value in data.items():
        match value:
            case dict() as nested:
                tables.append((key, nested))
            case bool() | int() | float() | str() as scalar:
                scalars.append((key, scalar))

    for key, value in scalars:
        match value:
            case bool():
                lines.append(f"{prefix}{key} = {str(value).lower()}")
            case int() | float():
                lines.append(f"{prefix}{key} = {value}")
            case _:
                lines.append(f'{prefix}{key} = "{value}"')

    for key, value in tables:
        lines.append(f"{prefix}[{key}]")
        lines.append(_dict_to_toml(value, indent))  # type: ignore[arg-type]

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

    Loaded from and written to ``config.toml`` inside the app config
    directory (``~/.config/tetratile/`` by default; see
    :func:`_xdg_config_file`).  The :attr:`config_file` field stores the
    *full path to the config file* that was last read or written; it is
    excluded from serialisation.

    :attr config_file: Full path of the config file last read or written
        (excluded from ``model_dump``).
    :attr board: Board dimensions and scale.
    :attr epsilon: Floating-point epsilon for rate calculations.
    :attr min_rate: Minimum fall rate.
    :attr initial_rate: Initial fall rate (0 = manual only).
    :attr remove_freq: Cycles between row removal.
    :attr constant: Whether to keep constant fall rate.
    :attr shadow: Shadow display type (``none``, ``projection``, or ``shadow``).
    :attr kick: Enable kick moves for rotations.
    :attr stack_transparency: Mix stack colours with black for depth effect.
    :attr screen_scale: Auto-calculate scale from screen size.
    :attr keys: Keyboard key bindings.
    """

    config_file: Path | None = Field(default=None, exclude=True)
    board: BoardConfig = Field(default_factory=BoardConfig)
    epsilon: float = Field(default_factory=lambda: __import__("sys").float_info.epsilon * 3)
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
        """Validate that ``initial_rate`` is at least ``min_rate``.

        :param v: The ``initial_rate`` value being validated.
        :param info: Pydantic validation context.
        :returns: The validated value.
        :raises ValueError: If ``initial_rate`` is less than ``min_rate``.
        """
        if "min_rate" in info.data and v < info.data["min_rate"]:
            raise ValueError("initial_rate must be >= min_rate")
        return v

    def write_to_file(self, path: Path | None = None) -> None:
        """Write this configuration to a TOML file.

        The target file is ``config.toml`` inside ``path``.  When ``path``
        is ``None``, the XDG default is used (see :func:`_xdg_config_file`).
        The parent directory is created if it does not already exist.
        After writing, :attr:`config_file` is updated to the resolved file
        path.

        :param path: App config directory to write into.  ``None`` uses
            ``~/.config/tetratile`` (or ``$XDG_CONFIG_HOME/tetratile``).
        """
        target = (path / "config.toml") if path is not None else _xdg_config_file()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_dict_to_toml(self.model_dump(exclude_none=True)))
        self.config_file = target

    @classmethod
    def from_file(cls, path: Path | None = None, *, create_default: bool = False) -> GameConfig:
        """Load configuration from a TOML file, falling back to defaults.

        Reads ``config.toml`` from ``path``.  When ``path`` is ``None``,
        the XDG default directory is used (``~/.config/tetratile`` or
        ``$XDG_CONFIG_HOME/tetratile``).  If the file does not exist and
        ``create_default`` is ``True``, default settings are written to the
        resolved location before returning.

        :param path: App config directory (reads ``config.toml`` inside it).
            ``None`` uses the XDG default.
        :param create_default: If ``True``, write a default config file when
            none is found.
        :returns: Loaded configuration, or defaults if the file is absent or
            unreadable.
        """
        config_file = (path / "config.toml") if path is not None else _xdg_config_file()
        if config_file.exists():
            try:
                with config_file.open("rb") as f:
                    data = tomllib.load(f)
                config = cls.model_validate(data)
            except Exception:
                config = cls()
                if create_default:
                    config.write_to_file(path)
        else:
            config = cls()
            if create_default:
                config.write_to_file(path)
        config.config_file = config_file
        return config
