"""Output handlers for game observation.

Output handlers receive push notifications from :class:`.TetraTile` after
each game tick via :meth:`OutputHandler.on_observation`.  Multiple handlers
can be registered simultaneously using
:meth:`.TetraTile.add_output_handler`, so a human-watching-agent scenario
simply registers a :class:`PrintObserver` alongside the running game.

Provided implementations:

* :class:`AgentOutputHandler` — stores the latest observation for polling by
  an :class:`.AgentRunner`.
* :class:`PrintObserver` — prints a human-readable board snapshot to stdout
  after each tick.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import GameObservation


class OutputHandler(ABC):
    """Abstract push-notification interface for game observation.

    Registered with :meth:`.TetraTile.add_output_handler`.  Called after
    every :meth:`.TetraTile.iterate` tick with a fresh
    :class:`.GameObservation` snapshot.
    """

    @abstractmethod
    def on_observation(self, obs: GameObservation) -> None:
        """Receive a game state snapshot.

        :param obs: Current :class:`.GameObservation`.
        """


class AgentOutputHandler(OutputHandler):
    """Output handler that stores the latest observation for agent polling.

    Register with :meth:`.TetraTile.add_output_handler` to keep a
    continuously-updated snapshot; retrieve it with :meth:`get_latest`.

    :attr _latest: Most recent :class:`.GameObservation` received, or
        ``None`` before the first tick.
    """

    def __init__(self) -> None:
        """Initialize with no stored observation."""
        self._latest: GameObservation | None = None

    def on_observation(self, obs: GameObservation) -> None:
        """Store the latest observation.

        :param obs: Current :class:`.GameObservation`.
        """
        self._latest = obs

    def get_latest(self) -> GameObservation | None:
        """Return the most recently stored observation.

        :returns: Latest :class:`.GameObservation`, or ``None`` if not yet
            received.
        """
        return self._latest


class PrintObserver(OutputHandler):
    """Output handler that prints a human-readable game snapshot to stdout.

    Attach with :meth:`.TetraTile.add_output_handler` to enable verbose
    output (replaces the old ``--verbose`` / ``set_verbose_output`` approach).
    Prints after every :meth:`.TetraTile.iterate` tick.
    """

    def on_observation(self, obs: GameObservation) -> None:
        """Print the current board state and statistics.

        :param obs: Current :class:`.GameObservation`.
        """
        elapsed = obs.elapsed
        elapsed_secs = elapsed.total_seconds()

        print("=" * 40)
        print(f"STATE: {obs.state}")
        print(f"Piece: {obs.current_piece or 'None'} (state={obs.current_piece_state})")
        print(f"Next:  {obs.next_piece or 'None'}")
        print(f"Rows cleared: {obs.stats.get('rows_cleared', 0)}")
        print(f"Pieces: {obs.stats.get('pieces', 0)}")
        print(f"Time: {elapsed_secs:.1f}s")
        print()

        # Print board: y=height-1 at top, y=0 at bottom (row-major obs.board[y][x])
        height = len(obs.board)
        width = len(obs.board[0]) if height else 0
        digits = len(str(height))
        row_fmt = f"{{:0{digits}}}"
        print(digits * " " + "+" + 2 * width * "-" + "+")
        for y in range(height - 1, -1, -1):
            row = obs.board[y]
            row_image = "".join(("  " if cell is None else (cell * 2 if len(cell) == 1 else cell[:2])) for cell in row)
            print(row_fmt.format(height - 1 - y) + "|" + row_image + "|")
        print(digits * " " + "+" + 2 * width * "-" + "+")
        print("=" * 40)
        print()
