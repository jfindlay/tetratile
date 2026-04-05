"""Entry point for python -m tetratile."""

import argparse
import importlib.metadata
import tkinter as tk
from pathlib import Path

from . import TetraTile
from .config import GameConfig

_VERSION: str = importlib.metadata.version("tetratile")


def main() -> int:
    """Execute the game.

    :returns: Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        description="Polyomino tessellation game",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {_VERSION}")
    parser.add_argument("-c", "--config-file", type=Path, help="Directory containing config file")
    parser.add_argument("-d", "--debug", action="store_true", help="Run game in debug mode")
    parser.add_argument(
        "-s",
        "--size",
        type=lambda s: dict(zip(["width", "height"], map(int, s.lower().split("x")), strict=True)),
        help="Board size WxH",
    )
    parser.add_argument("-a", "--scale", type=int, help="Board scale pixels/block")
    parser.add_argument("-r", "--initial-rate", type=float, help="Initial rate blocks/second")
    parser.add_argument("-o", "--constant", action="store_true", help="Do not increase game rate")

    args = parser.parse_args()

    config = GameConfig.from_file(Path(args.config_file) if args.config_file else Path.cwd())
    if args.debug:
        config.debug = args.debug
    if args.size is not None:
        config.board.width = args.size["width"]
        config.board.height = args.size["height"]
    if args.scale is not None:
        config.board.scale = args.scale
    if args.initial_rate is not None:
        config.initial_rate = args.initial_rate
    if args.constant:
        config.constant = args.constant

    try:
        TetraTile(config, master=tk.Tk(className="tetratile")).mainloop()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    main()
