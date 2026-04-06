"""Log viewer widget for game event replay."""

from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
from collections.abc import Callable

if TYPE_CHECKING:
    from .event_log import Event, EventLogger


class LogViewer(tk.Toplevel):
    """Event log viewer with playback controls.

    :attr logger: The event logger to display.
    :attr on_highlight: Callback when event is highlighted.
    """

    def __init__(self, parent: tk.Tk, logger: EventLogger, on_highlight: Callable[[int], None] | None = None) -> None:
        """Initialize the log viewer.

        :param parent: Parent window.
        :param logger: Event logger to display.
        :param on_highlight: Callback when event is highlighted.
        """
        super().__init__(parent)
        self.title("Event Log")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._logger = logger
        self._on_highlight = on_highlight
        self._current_index = -1
        self._playing = False
        self._play_after_id: str | None = None

        self._create_widgets()
        self._populate_log()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_idletasks()
        self.geometry(
            f"+{(parent.winfo_width() - self.winfo_width()) // 2}+{(parent.winfo_height() - self.winfo_height()) // 2}"
        )

    def _create_widgets(self) -> None:
        """Create all widgets."""
        control_frame = ttk.Frame(self, padding=8)
        control_frame.pack(fill="x")

        ttk.Button(control_frame, text="|◀", width=4, command=self._step_start).pack(side="left", padx=2)
        ttk.Button(control_frame, text="◀", width=4, command=self._step_back).pack(side="left", padx=2)
        self._play_btn = ttk.Button(control_frame, text="▶", width=4, command=self._play_pause)
        self._play_btn.pack(side="left", padx=2)
        ttk.Button(control_frame, text="▶|", width=4, command=self._step_end).pack(side="left", padx=2)
        ttk.Button(control_frame, text="◀|", width=4, command=self._step_forward_end).pack(side="left", padx=2)

        ttk.Frame(self, height=2, relief="sunken").pack(fill="x", padx=8)

        list_frame = ttk.Frame(self, padding=(8, 0, 8, 8))
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self._listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Monospace", 10), height=20)
        self._listbox.pack(side="left", fill="both", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)
        scrollbar.config(command=self._listbox.yview)

    def _populate_log(self) -> None:
        """Populate the listbox with events."""
        self._listbox.delete(0, "end")
        log = self._logger.get_log()

        if log.events:
            for event in log.events:
                text = self._format_event(event)
                self._listbox.insert("end", text)

    def _format_event(self, event: Event) -> str:
        """Format an event for display.

        :param event: Event to format.
        :returns: Formatted string.
        """
        base = dt.datetime.min + event.elapsed
        time_str = base.strftime("%M:%S.%f")[:-3]

        match event.type.name:
            case "game_start":
                return f"{time_str} Game started"
            case "game_pause":
                return f"{time_str} Game paused"
            case "game_resume":
                return f"{time_str} Game resumed"
            case "game_over":
                return f"{time_str} Game over ({event.reason})"
            case "piece_spawn":
                return f"{time_str} Spawn {event.piece_type}"
            case "piece_move":
                return f"{time_str} Move {event.piece_type} {event.direction}"
            case "piece_rotate":
                return f"{time_str} Rotate {event.piece_type} {event.direction}"
            case "piece_lock":
                return f"{time_str} Lock {event.piece_type}"
            case "row_clear":
                count = event.count or 0
                return f"{time_str} Clear {count} row{'s' if count > 1 else ''}"
            case "rate_change":
                return f"{time_str} Rate changed to {event.count or 0}"
            case _:
                return f"{time_str} {event.type.name}"

    def _on_select(self, event: tk.Event) -> None:
        """Handle listbox selection."""
        selection = self._listbox.curselection()  # type: ignore[no-untyped-call]
        if selection:
            self._current_index = selection[0]
            self._highlight_current()
            if self._on_highlight:
                self._on_highlight(self._current_index)

    def _highlight_current(self) -> None:
        """Highlight the current event in the listbox."""
        self._listbox.selection_clear(0, "end")
        self._listbox.selection_set(self._current_index)
        self._listbox.see(self._current_index)

    def _step_start(self) -> None:
        """Step to the start of the log."""
        self._stop_playing()
        self._current_index = 0
        self._highlight_current()
        if self._on_highlight:
            self._on_highlight(self._current_index)

    def _step_back(self) -> None:
        """Step back one event."""
        self._stop_playing()
        if self._current_index > 0:
            self._current_index -= 1
            self._highlight_current()
            if self._on_highlight:
                self._on_highlight(self._current_index)

    def _step_forward(self) -> None:
        """Step forward one event (for auto-play)."""
        if self._current_index < self._listbox.size() - 1:
            self._current_index += 1
            self._highlight_current()
            if self._on_highlight:
                self._on_highlight(self._current_index)
        else:
            self._stop_playing()

    def _step_forward_end(self) -> None:
        """Step to the end of the log."""
        self._stop_playing()
        self._current_index = max(0, self._listbox.size() - 1)
        self._highlight_current()
        if self._on_highlight:
            self._on_highlight(self._current_index)

    def _step_end(self) -> None:
        """Step to the end (stop playback but stay at last event)."""
        self._stop_playing()

    def _play_pause(self) -> None:
        """Toggle play/pause for auto-stepping."""
        if self._playing:
            self._stop_playing()
        else:
            self._start_playing()

    def _start_playing(self) -> None:
        """Start auto-stepping through events."""
        self._playing = True
        self._play_btn.config(text="⏸")
        self._auto_step()

    def _stop_playing(self) -> None:
        """Stop auto-stepping."""
        self._playing = False
        self._play_btn.config(text="▶")
        if self._play_after_id:
            self.after_cancel(self._play_after_id)
            self._play_after_id = None

    def _auto_step(self) -> None:
        """Automatically step through events."""
        if self._playing:
            self._step_forward()
            self._play_after_id = self.after(500, self._auto_step)

    def highlight_index(self, index: int) -> None:
        """Highlight a specific event by index.

        :param index: Event index to highlight.
        """
        if 0 <= index < self._listbox.size():
            self._current_index = index
            self._highlight_current()
            self._listbox.see(index)

    def _on_close(self) -> None:
        """Handle window close."""
        self._stop_playing()
        self.grab_release()
        self.destroy()
