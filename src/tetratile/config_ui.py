"""Configuration UI for Tetratile."""

import functools
import tkinter as tk
from tkinter import ttk

from .config import GameConfig


class ConfigUI(tk.Toplevel):
    """Configuration dialog for game settings.

    :attr config: The configuration being edited.
    :attr original: The original configuration before changes.
    :attr modified: Whether the configuration has been modified.
    """

    def __init__(self, parent: tk.Tk, config: GameConfig) -> None:
        """Initialize the config UI.

        :param parent: Parent window.
        :param config: Initial configuration.
        """
        super().__init__(parent)
        self.title("Tetratile Preferences")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._original = config
        self._config = GameConfig.model_validate(config.model_dump())
        self._modified = False

        self._create_widgets()
        self._populate_widgets()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.update_idletasks()
        self.geometry(
            f"+{(parent.winfo_width() - self.winfo_width()) // 2}+{(parent.winfo_height() - self.winfo_height()) // 2}"
        )

    def _create_widgets(self) -> None:
        """Create all widgets."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        board_frame = ttk.Frame(notebook, padding=8)
        gameplay_frame = ttk.Frame(notebook, padding=8)
        controls_frame = ttk.Frame(notebook, padding=8)
        notebook.add(board_frame, text="Board")
        notebook.add(gameplay_frame, text="Gameplay")
        notebook.add(controls_frame, text="Controls")

        self._create_board_tab(board_frame)
        self._create_gameplay_tab(gameplay_frame)
        self._create_controls_tab(controls_frame)
        self._create_buttons()

    def _create_board_tab(self, parent: ttk.Frame) -> None:
        """Create the board configuration tab."""
        ttk.Label(parent, text="Board Settings", font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self._screen_scale_var = tk.BooleanVar()
        ttk.Checkbutton(
            parent, text="Auto-scale to screen", variable=self._screen_scale_var, command=self._on_screen_scale_changed
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(
            parent, text="Automatically calculate scale from screen size on startup", font=("TkDefaultFont", 8, "italic")
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(parent, text="Scale:").grid(row=3, column=0, sticky="w")
        self._scale_var = tk.IntVar()
        self._scale_slider = ttk.Scale(
            parent, from_=8, to=64, orient="horizontal", variable=self._scale_var, command=self._on_modified
        )
        self._scale_slider.grid(row=3, column=1, sticky="ew")
        self._scale_value = ttk.Label(parent, text="32")
        self._scale_value.grid(row=3, column=2, padx=(8, 0))
        ttk.Label(parent, text="Pixel size of each block", font=("TkDefaultFont", 8, "italic")).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        ttk.Label(parent, text="Width:").grid(row=5, column=0, sticky="w")
        self._width_var = tk.IntVar()
        self._width_slider = ttk.Scale(
            parent, from_=5, to=30, orient="horizontal", variable=self._width_var, command=self._on_modified
        )
        self._width_slider.grid(row=5, column=1, sticky="ew")
        self._width_value = ttk.Label(parent, text="10")
        self._width_value.grid(row=5, column=2, padx=(8, 0))
        ttk.Label(parent, text="Number of columns", font=("TkDefaultFont", 8, "italic")).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        ttk.Label(parent, text="Height:").grid(row=7, column=0, sticky="w")
        self._height_var = tk.IntVar()
        self._height_slider = ttk.Scale(
            parent, from_=10, to=50, orient="horizontal", variable=self._height_var, command=self._on_modified
        )
        self._height_slider.grid(row=7, column=1, sticky="ew")
        self._height_value = ttk.Label(parent, text="22")
        self._height_value.grid(row=7, column=2, padx=(8, 0))
        ttk.Label(parent, text="Number of rows", font=("TkDefaultFont", 8, "italic")).grid(
            row=8, column=0, columnspan=3, sticky="w"
        )

        parent.columnconfigure(1, weight=1)

    def _create_gameplay_tab(self, parent: ttk.Frame) -> None:
        """Create the gameplay configuration tab."""
        ttk.Label(parent, text="Gameplay Settings", font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(parent, text="Initial Rate:").grid(row=1, column=0, sticky="w")
        self._initial_rate_var = tk.DoubleVar()
        self._initial_rate_slider = ttk.Scale(
            parent, from_=0.0, to=10.0, orient="horizontal", variable=self._initial_rate_var, command=self._on_modified
        )
        self._initial_rate_slider.grid(row=1, column=1, sticky="ew")
        self._initial_rate_value = ttk.Label(parent, text="0.0")
        self._initial_rate_value.grid(row=1, column=2, padx=(8, 0))
        ttk.Label(parent, text="Starting fall rate (blocks/second), 0 = manual only", font=("TkDefaultFont", 8, "italic")).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        ttk.Label(parent, text="Min Rate:").grid(row=3, column=0, sticky="w")
        self._min_rate_var = tk.DoubleVar()
        self._min_rate_slider = ttk.Scale(
            parent, from_=0.0, to=5.0, orient="horizontal", variable=self._min_rate_var, command=self._on_modified
        )
        self._min_rate_slider.grid(row=3, column=1, sticky="ew")
        self._min_rate_value = ttk.Label(parent, text="0.0")
        self._min_rate_value.grid(row=3, column=2, padx=(8, 0))
        ttk.Label(parent, text="Minimum fall rate floor", font=("TkDefaultFont", 8, "italic")).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        self._constant_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="Constant Fall Rate", variable=self._constant_var, command=self._on_modified).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        ttk.Label(parent, text="Keep fall rate fixed instead of increasing", font=("TkDefaultFont", 8, "italic")).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        ttk.Label(parent, text="Remove Frequency:").grid(row=7, column=0, sticky="w")
        self._remove_freq_var = tk.IntVar()
        self._remove_freq_slider = ttk.Scale(
            parent, from_=1, to=10, orient="horizontal", variable=self._remove_freq_var, command=self._on_modified
        )
        self._remove_freq_slider.grid(row=7, column=1, sticky="ew")
        self._remove_freq_value = ttk.Label(parent, text="1")
        self._remove_freq_value.grid(row=7, column=2, padx=(8, 0))
        ttk.Label(parent, text="Full rows to complete before removal check", font=("TkDefaultFont", 8, "italic")).grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Separator(parent, orient="horizontal").grid(row=9, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        ttk.Label(parent, text="Shadow Display:", font=("TkDefaultFont", 10, "bold")).grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        self._shadow_var = tk.StringVar(value="projection")
        ttk.Radiobutton(parent, text="None", variable=self._shadow_var, value="none", command=self._on_modified).grid(
            row=11, column=0, columnspan=3, sticky="w", padx=(0, 20)
        )
        ttk.Radiobutton(
            parent, text="Projection (below board)", variable=self._shadow_var, value="projection", command=self._on_modified
        ).grid(row=12, column=0, columnspan=3, sticky="w", padx=(0, 20))
        ttk.Radiobutton(
            parent, text="Shadow (overlay on stack)", variable=self._shadow_var, value="shadow", command=self._on_modified
        ).grid(row=13, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Separator(parent, orient="horizontal").grid(row=14, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self._kick_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="Enable Kick Moves", variable=self._kick_var, command=self._on_modified).grid(
            row=15, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        ttk.Label(parent, text="Try offset positions when rotation fails", font=("TkDefaultFont", 8, "italic")).grid(
            row=16, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )

        self._stack_transparency_var = tk.BooleanVar()
        ttk.Checkbutton(
            parent, text="Stack Transparency", variable=self._stack_transparency_var, command=self._on_modified
        ).grid(row=17, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(parent, text="Mix placed pieces with black for depth (~15%%)", font=("TkDefaultFont", 8, "italic")).grid(
            row=18, column=0, columnspan=3, sticky="w"
        )

        parent.columnconfigure(1, weight=1)

    def _create_controls_tab(self, parent: ttk.Frame) -> None:
        """Create the controls configuration tab."""
        ttk.Label(parent, text="Keyboard Controls", font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self._key_vars: dict[str, tk.StringVar] = {}
        self._key_entries: dict[str, ttk.Entry] = {}
        key_actions = [
            ("pause", "Pause/Resume"),
            ("left", "Move Left"),
            ("right", "Move Right"),
            ("left_side", "Move to Left Edge"),
            ("right_side", "Move to Right Edge"),
            ("rotate_left", "Rotate Left"),
            ("rotate_right", "Rotate Right"),
            ("down", "Soft Drop"),
            ("drop", "Hard Drop"),
            ("lock", "Lock Piece"),
        ]

        for i, (action, label) in enumerate(key_actions, start=1):
            ttk.Label(parent, text=f"{label}:").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=self._config.keys.model_dump()[action])
            self._key_vars[action] = var
            entry = ttk.Entry(parent, textvariable=var, width=12, state="readonly")
            entry.grid(row=i, column=1, sticky="w", pady=2)
            self._key_entries[action] = entry
            btn = ttk.Button(parent, text="Record", command=functools.partial(self._record_key, action))
            btn.grid(row=i, column=2, padx=(8, 0), pady=2)

        ttk.Label(parent, text="Click Record, then press a key to assign", font=("TkDefaultFont", 8, "italic")).grid(
            row=len(key_actions) + 1, column=0, columnspan=3, sticky="w", pady=(12, 0)
        )

        parent.columnconfigure(1, weight=1)

    def _create_buttons(self) -> None:
        """Create bottom buttons."""
        btn_frame = ttk.Frame(self, padding=8)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side="right", padx=(4, 0))
        ttk.Button(btn_frame, text="Apply", command=self._on_apply).pack(side="right")
        ttk.Button(btn_frame, text="Save & Close", command=self._on_save_close).pack(side="right", padx=(0, 4))

    def _record_key(self, action: str) -> None:
        """Start key recording for an action."""
        entry = self._key_entries[action]

        def on_keypress(event: tk.Event) -> None:
            key = event.keysym
            if key == "Escape":
                entry.focus_set()
                return
            self._key_vars[action].set(key)
            self._modified = True
            entry.focus_set()

        entry.focus_set()
        entry.bind("<KeyPress>", on_keypress)

    def _populate_widgets(self) -> None:
        """Populate widgets with current config values."""
        self._screen_scale_var.set(self._config.screen_scale)
        self._scale_var.set(self._config.board.scale)
        self._width_var.set(self._config.board.width)
        self._height_var.set(self._config.board.height)
        self._initial_rate_var.set(self._config.initial_rate)
        self._min_rate_var.set(self._config.min_rate)
        self._constant_var.set(self._config.constant)
        self._remove_freq_var.set(self._config.remove_freq)
        self._shadow_var.set(self._config.shadow)
        self._kick_var.set(self._config.kick)
        self._stack_transparency_var.set(self._config.stack_transparency)

        self._update_scale_value()
        self._update_width_value()
        self._update_height_value()
        self._update_initial_rate_value()
        self._update_min_rate_value()
        self._update_remove_freq_value()

        for action, var in self._key_vars.items():
            var.set(self._config.keys.model_dump()[action])

    def _update_scale_value(self) -> None:
        """Update scale value label."""
        self._scale_value.config(text=str(self._scale_var.get()))

    def _update_width_value(self) -> None:
        """Update width value label."""
        self._width_value.config(text=str(self._width_var.get()))

    def _update_height_value(self) -> None:
        """Update height value label."""
        self._height_value.config(text=str(self._height_var.get()))

    def _update_initial_rate_value(self) -> None:
        """Update initial rate value label."""
        self._initial_rate_value.config(text=f"{self._initial_rate_var.get():.1f}")

    def _update_min_rate_value(self) -> None:
        """Update min rate value label."""
        self._min_rate_value.config(text=f"{self._min_rate_var.get():.1f}")

    def _update_remove_freq_value(self) -> None:
        """Update remove frequency value label."""
        self._remove_freq_value.config(text=str(self._remove_freq_var.get()))

    def _on_modified(self, *args: object) -> None:
        """Handle any modification."""
        self._modified = True
        self._update_scale_value()
        self._update_width_value()
        self._update_height_value()
        self._update_initial_rate_value()
        self._update_min_rate_value()
        self._update_remove_freq_value()

    def _on_screen_scale_changed(self) -> None:
        """Handle screen scale checkbox change."""
        self._modified = True
        enabled = self._screen_scale_var.get()
        self._scale_slider.config(state="normal" if enabled else "disabled")
        if enabled:
            self._scale_slider.config(state="disabled")

    def _gather_config(self) -> GameConfig:
        """Gather values from widgets into a GameConfig."""
        self._config.screen_scale = self._screen_scale_var.get()
        self._config.board.scale = self._scale_var.get()
        self._config.board.width = self._width_var.get()
        self._config.board.height = self._height_var.get()
        self._config.initial_rate = self._initial_rate_var.get()
        self._config.min_rate = self._min_rate_var.get()
        self._config.constant = self._constant_var.get()
        self._config.remove_freq = self._remove_freq_var.get()
        self._config.shadow = self._shadow_var.get()  # type: ignore[assignment]
        self._config.kick = self._kick_var.get()
        self._config.stack_transparency = self._stack_transparency_var.get()

        for action, var in self._key_vars.items():
            setattr(self._config.keys, action, var.get())

        return self._config

    def _on_apply(self) -> None:
        """Apply changes and continue editing."""
        self._gather_config()
        self._original.screen_scale = self._config.screen_scale
        self._original.board = self._config.board
        self._original.initial_rate = self._config.initial_rate
        self._original.min_rate = self._config.min_rate
        self._original.constant = self._config.constant
        self._original.remove_freq = self._config.remove_freq
        self._original.shadow = self._config.shadow
        self._original.kick = self._config.kick
        self._original.stack_transparency = self._config.stack_transparency
        self._original.keys = self._config.keys

    def _on_save_close(self) -> None:
        """Save to file, apply, and close."""
        self._gather_config()
        self._original.screen_scale = self._config.screen_scale
        self._original.board = self._config.board
        self._original.initial_rate = self._config.initial_rate
        self._original.min_rate = self._config.min_rate
        self._original.constant = self._config.constant
        self._original.remove_freq = self._config.remove_freq
        self._original.shadow = self._config.shadow
        self._original.kick = self._config.kick
        self._original.stack_transparency = self._config.stack_transparency
        self._original.keys = self._config.keys
        self._original.write_to_file()
        self.grab_release()
        self.destroy()

    def _on_cancel(self) -> None:
        """Discard changes and close."""
        self.grab_release()
        self.destroy()
