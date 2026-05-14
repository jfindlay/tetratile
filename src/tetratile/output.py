"""Output handlers for game observation (push-notification model).

After each gravity tick, :meth:`.TetraTile._notify_observers` calls
:meth:`OutputHandler.on_observation` on all registered handlers with a fresh
:class:`.GameObservation` snapshot.  Multiple handlers may be registered
simultaneously: for example, a human watching an agent game can attach a
:class:`PrintObserver` without any special mode switch.

This is a **push** model: :class:`TetraTile` pushes observations out; handlers
react.  Agents that need to *pull* a snapshot (e.g. in :class:`.AgentRunner`)
call :meth:`.TetraTile.get_observation` directly.

Provided implementations:

* :class:`AgentOutputHandler` — caches the latest observation for subsequent
  polling via :meth:`AgentOutputHandler.get_latest`.
* :class:`PrintObserver` — renders the board to stdout after each tick,
  replacing the former ``--verbose`` / ``set_verbose_output`` mechanism.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import GameObservation


class OutputHandler(ABC):
    """Abstract push-notification interface for game observation.

    Register with :meth:`.TetraTile.add_output_handler`.  Each registered
    handler receives a fresh :class:`.GameObservation` snapshot via
    :meth:`on_observation` after every :meth:`.TetraTile.iterate` gravity
    tick.  The observation is read-only; handlers must not modify game state.
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
    """Output handler that renders the game state to stdout after each tick.

    Attach with :meth:`.TetraTile.add_output_handler` to enable verbose
    terminal output (replaces the former ``--verbose`` / ``set_verbose_output``
    mechanism).  Renders after every :meth:`.TetraTile.iterate` gravity tick.

    The board is printed top-to-bottom (``y = height - 1`` first), matching
    visual intuition.  The underlying :attr:`.GameObservation.board` array is
    row-major — ``board[y][x]`` with ``y=0`` at the bottom — so iteration is
    reversed: ``for y in range(height - 1, -1, -1)``.
    """

    def on_observation(self, obs: GameObservation) -> None:
        """Render the current board, piece, and statistics to stdout.

        :param obs: Current :class:`.GameObservation` snapshot.
        """
        elapsed = obs.elapsed
        elapsed_secs = elapsed.total_seconds()

        print("=" * 40)
        print(f"STATE: {obs.state}")
        print(f"Piece: {obs.current_piece or 'None'}")
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
