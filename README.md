# Tetratile

A tetromino tessellation game.

## Install

When running the install command as a nonprivileged user, tetratile will be installed into standard
[XDG locations](https://specifications.freedesktop.org/basedir-spec/latest/), which typically
default to `~/.local/bin`, and `~/.local/lib/python*/site-packages`, etc.

```bash
$ uv pip install tetratile
```

## Gameplay

The game board is a grid of squares with a default size of 10 columns and 22 rows. Randomly selected
[one-sided](https://en.wikipedia.org/wiki/Tetromino#One-sided_tetrominoes) tetrominoes are placed at
the top center of the game board and translated downward in single row jumps at a speed called the
fall rate. Tetrominoes inserted into the game board always align with the grid squares.

Before the tetromino reaches either the bottom of the grid or the top of tetromino remnant squares
stacked on the bottom of the grid, the player may rotate it clockwise or counterclockwise in
increments of ±π/2, translate it left, right, or down in increments of 1 square, or translate it
to the left wall, the right wall, or the bottom wall or top of the stack.

When the tetromino reaches the bottom of the grid or the stack at the bottom, any rows in the game
board that are completely filled with tetromino squares are highlighted and removed, all incomplete
rows above them are translated downward, and another randomly selected tetromino is placed at the
top center of the game board and begins falling. The game ends when a new tetromino cannot fit at
the top center of the game board.

The fall rate scales logarithmically with the number of completed rows removed. The game window
displays a marquee on the right side of the game board showing:
- The next tetromino
- The fall rate, piece rate, and row rate
- A tally of each one-sided tetromino used: `Z`, `S`, `l`, `T`, `o`, `L`, `J`
- A tally of the number of simultaneous rows removed — tetromino geometry implies 1 to 4 rows may
  be removed simultaneously
- The elapsed time

## Configuration

The game can be configured by (in order of increasing precedence):
- Defaults defined in `tetratile.config.GameConfig`
- The config file: `~/.config/tetratile/config.toml`
  (or `$XDG_CONFIG_HOME/tetratile/config.toml`)
- Command line parameters

Not all configs available to the config file are available on the command line.

Configuration can also be modified at runtime via **File → Preferences** in the game.

### Default keys

The default keys for translating the active tetromino align with the four fingers of each hand when placed on adjacent keys on the bottom row of a US QWERTY keyboard layout.

|Key|Action|
|---|------|
|`,`|Translate left|
|`.`|Translate right|
|`x`|Translate down|
|`v`|Rotate clockwise|
|`m`|Rotate counterclockwise|
|`z`|Translate left until stopped by left wall or stack|
|`/`|Translate right until stopped by right wall or stack|
|`c`|Translate down until stopped by bottom wall or stack|
|`l`|Lock piece in place (for manual-only mode)|
|`p`|(Un)pause|

## Development

```bash
$ git clone https://github.com/jfindlay/tetratile.git
$ cd tetratile
# <edit code>
$ uv run pytest
$ uv run ruff check src/ tests/
$ uv run ruff format src/ tests/
$ uv build
```

## Event Log

Game events are logged during play and saved automatically when the game ends. Logs are saved to
`~/.local/share/tetratile/logs/` (or `$XDG_DATA_HOME/tetratile/logs/` when `XDG_DATA_HOME` is set).

### Viewing Logs

- **File → View Event Log**: Opens a viewer showing all game events
- **File → Save Event Log**: Manually save the current log

### Log Format

Events are stored as JSON with:
- `game_id`: Unique game identifier
- `timestamp_start/end`: ISO timestamps
- `seed`: Random seed for reproducibility
- `config`: Game configuration snapshot
- `events[]`: List of all game events with timestamps
- `stats`: Final statistics (pieces, rows cleared, etc.)

### Event Types

| Type | Description |
|------|-------------|
| `game_start` | Game began |
| `game_pause` / `game_resume` | Pause state changes |
| `game_over` | Game ended |
| `piece_spawn` | New piece appeared |
| `piece_move` | Piece translated (left/right/down) |
| `piece_rotate` | Piece rotated (CW/CCW) |
| `piece_lock` | Piece placed |
| `row_clear` | Rows removed |


