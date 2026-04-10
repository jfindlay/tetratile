"""Entry point for ``python -m tetratile``.

The two orthogonal CLI flags ``--agent`` and ``--observe`` choose **who
plays** and **who watches**, respectively.  Either combination is valid:

.. list-table:: Mode matrix
   :header-rows: 1
   :widths: 10 10 80

   * - ``--agent``
     - ``--observe``
     - Behaviour
   * - no
     - no
     - Human plays via keyboard; GUI visible; no stdout output.
   * - no
     - yes
     - Human plays; GUI visible; :class:`.PrintObserver` on stdout.
   * - yes
     - no
     - Agent plays; GUI visible so a human can watch.
   * - yes
     - yes
     - Agent plays; GUI visible + :class:`.PrintObserver` on stdout.

Both :class:`.HumanInputHandler` and :class:`.AgentInputHandler` are
coequal frontends of the same :class:`.InputHandler` base class.  Keyboard
events are bound to :class:`.InputHandler` methods via
:meth:`.TetraTile.setup_events`; when an agent handler is active the same
key bindings are present but simply route through the agent handler, which
calls the same :meth:`.TetraTile.move_piece` path.

CLI flags
---------
``--agent [CLASS]``
    Drive the game with an :class:`.Agent`.  ``CLASS`` defaults to
    ``"random"`` (:class:`.RandomAgent`).

``--observe``
    Register a :class:`.PrintObserver` — prints the board state to stdout
    after each gravity tick.  Works for both human and agent games.

``-s WxH``, ``-a SCALE``, ``-r RATE``, ``-o``, ``-c DIR``
    Standard game-configuration overrides (size, scale, rate, constant
    rate, config-file directory).
"""

import argparse
import importlib.metadata
import tkinter as tk
from pathlib import Path

from . import TetraTile
from .agent_runner import AgentRunner
from .config import GameConfig
from .input_human import HumanInputHandler
from .output import PrintObserver

_VERSION: str = importlib.metadata.version("tetratile")


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    :returns: Configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        description="Polyomino tessellation game",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {_VERSION}")
    parser.add_argument("-c", "--config-file", type=Path, help="Directory containing config file")
    parser.add_argument(
        "-s",
        "--size",
        type=lambda s: dict(zip(["width", "height"], map(int, s.lower().split("x")), strict=True)),
        help="Board size WxH",
    )
    parser.add_argument("-a", "--scale", type=int, help="Board scale pixels/block")
    parser.add_argument("-r", "--initial-rate", type=float, help="Initial fall rate blocks/second")
    parser.add_argument("-o", "--constant", action="store_true", help="Do not increase game rate")

    parser.add_argument(
        "--agent",
        metavar="CLASS",
        nargs="?",
        const="random",
        default=None,
        help="Run with agent input; CLASS defaults to 'random'",
    )
    parser.add_argument(
        "--observe",
        action="store_true",
        help="Attach a stdout observer (prints board after each tick)",
    )
    return parser


def _load_config(args: argparse.Namespace) -> GameConfig:
    """Build :class:`.GameConfig` from CLI args.

    :param args: Parsed command-line arguments.
    :returns: Populated :class:`.GameConfig`.
    """
    config = GameConfig.from_file(
        Path(args.config_file) if args.config_file else Path.cwd(),
        create_default=True,
    )
    if args.size is not None:
        config.board.width = args.size["width"]
        config.board.height = args.size["height"]
    if args.scale is not None:
        config.board.scale = args.scale
    if args.initial_rate is not None:
        config.initial_rate = args.initial_rate
    if args.constant:
        config.constant = args.constant
    return config


def _create_agent(class_name: str) -> "Agent":  # type: ignore[name-defined]  # noqa: F821
    """Instantiate an agent by class name.

    :param class_name: Registered agent class name (e.g. ``"random"``).
    :returns: :class:`.Agent` instance.
    :raises ValueError: If ``class_name`` is not recognized.
    """
    from .agent import RandomAgent

    registry: dict[str, type] = {
        "random": RandomAgent,
    }
    if class_name not in registry:
        raise ValueError(f"Unknown agent class '{class_name}'. Available: {sorted(registry)}")
    return registry[class_name]()


def main() -> int:
    """Execute the game.

    :returns: Exit code (0 for success).
    """
    args = _build_parser().parse_args()
    config = _load_config(args)

    if args.agent is not None:
        # Agent plays
        agent = _create_agent(args.agent)
        runner = AgentRunner(
            config=config,
            agent=agent,
            show_gui=True,
            observe=args.observe,
        )
        result = runner.run()
        print("\n=== GAME OVER ===")
        print(f"Steps: {result.steps}")
        print(f"Stats: {result.stats}")
        return 0

    # Human plays
    try:
        root = tk.Tk(className="tetratile")
        game = TetraTile(config, master=root)
        game.set_input_handler(HumanInputHandler(game))
        if args.observe:
            game.add_output_handler(PrintObserver())
        game.mainloop()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    main()
