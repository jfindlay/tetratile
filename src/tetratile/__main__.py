"""Entry point for python -m tetratile."""

import argparse
import importlib.metadata
import tkinter as tk
from pathlib import Path

from . import TetraTile
from .agent_runner import AgentRunner
from .config import GameConfig
from .input_agent import AgentInputHandler

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
    parser.add_argument(
        "-s",
        "--size",
        type=lambda s: dict(zip(["width", "height"], map(int, s.lower().split("x")), strict=True)),
        help="Board size WxH",
    )
    parser.add_argument("-a", "--scale", type=int, help="Board scale pixels/block")
    parser.add_argument("-r", "--initial-rate", type=float, help="Initial rate blocks/second")
    parser.add_argument("-o", "--constant", action="store_true", help="Do not increase game rate")

    # Agent mode options
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Run with agent input and output (single flag for agent mode)",
    )
    parser.add_argument(
        "--agent-class",
        default="random",
        help="Agent class to use (e.g., random, greedy)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Output game state to stdout after each iteration",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run headless (agent input only, no GUI)",
    )
    parser.add_argument(
        "--repl",
        action="store_true",
        help="Run in interactive REPL mode for direct control",
    )

    args = parser.parse_args()

    config = GameConfig.from_file(Path(args.config_file) if args.config_file else Path.cwd(), create_default=True)
    if args.size is not None:
        config.board.width = args.size["width"]
        config.board.height = args.size["height"]
    if args.scale is not None:
        config.board.scale = args.scale
    if args.initial_rate is not None:
        config.initial_rate = args.initial_rate
    if args.constant:
        config.constant = args.constant

    # Handle REPL mode
    if args.repl:
        root = tk.Tk(className="tetratile-repl")
        root.withdraw()
        game = TetraTile(config, master=root)
        game.set_input_handler(AgentInputHandler(game))
        game.set_verbose_output(True)
        game._print_game_state()
        print("\n=== REPL MODE ===")
        print("Available commands:")
        print("  game.move_left()    - move piece left")
        print("  game.move_right()   - move piece right")
        print("  game.rotate_cw()    - rotate clockwise")
        print("  game.rotate_ccw()   - rotate counter-clockwise")
        print("  game.soft_drop()    - soft drop")
        print("  game.hard_drop()    - hard drop")
        print("  game.lock_piece()   - lock piece in place")
        print("  game.print_board()  - print current board")
        print("  game.iterate()      - advance game state")
        print("  game.quit           - exit REPL")
        print("\nExample: game.soft_drop()")
        print("-" * 40)

        import code
        import sys

        class GameConsole(code.InteractiveConsole):
            def push(self, line):
                if line.strip() == "game.quit":
                    print("Goodbye!")
                    sys.exit(0)
                return super().push(line)

        console = GameConsole({"game": game})
        try:
            console.interact(banner="")
        except SystemExit:
            pass
        return 0

    # Handle agent mode
    if args.agent or args.no_gui:
        # Headless agent mode
        runner = AgentRunner(
            config=config,
            agent_class=args.agent_class,
            verbose=args.verbose,
        )
        result = runner.run()
        print(f"\n=== GAME OVER ===")
        print(f"Steps: {result.steps}")
        print(f"Stats: {result.stats}")
        return 0

    # Normal GUI mode
    try:
        game = TetraTile(config, master=tk.Tk(className="tetratile"))

        # Set up agent input if requested
        if args.agent:
            agent_input = AgentInputHandler(game)
            game.set_input_handler(agent_input)

        # Enable verbose output if requested
        if args.verbose:
            game.set_verbose_output(True)

        game.mainloop()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    main()
