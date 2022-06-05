# Tetratile

A tetromino tessellation game.

## Install

When running the install command as a nonprivileged user, tetratile will be installed into standard [XDG locations](https://specifications.freedesktop.org/basedir-spec/latest/), which typically default to `~/.local/bin`, and `~/.local/lib/python*/site-packages`, etc.

```bash
$ pip install --break-system-packages tetratile
```

## Gameplay

The game board is a grid of squares with a default size of 10 columns and 22 rows.  Randomly selected [one-sided](https://en.wikipedia.org/wiki/Tetromino#One-sided_tetrominoes) tetrominoes are placed at the top center of the game board and translated downward in single row jumps at a speed called the fall rate.  Tetrominoes inserted into the game board always align with the grid squares.

Before the tetromino reaches either the bottom of the grid or the top of tetromino remnant squares stacked on the bottom of the grid, the player may rotate it clockwise or counterclockwise in increments of ±π/2, translate it left, right, or down in increments of 1 square, or translate it to the left wall, the right wall, or the bottom wall or top of the stack.

When the tetromino reaches the bottom of the grid or the stack at the bottom, any rows in the game board that are completely filled with tetromino squares are highlighted and removed, all incomplete rows above them are translated downward, and another randomly selected tetromino is placed at the top center of the game board and begins falling.  The game ends when a new tetromino cannot fit at the top center of the game board.

The fall rate scales logarithmically with the number of completed rows removed.  The game window displays a marquee on the right side of the game board showing:
- The next tetromino
- The fall rate, piece rate, and row rate
- A tally of each one-sided tetromino used: `Z`, `S`, `l`, `T`, `o`, `L`, `J`
- A tally of the number of simultaneous rows removed--tetromino geometry implies 1 to 4 rows may be removed simultaneously
- The elapsed time

## Configuration

The game can be configured by (in order of increasing precedence):
- Defaults defined in the source code at `tetratile.tetratile.Config().opts`
- The config file: `tetratile.conf`
- Command line parameters

Not all configs available to the config file are available on the command line.

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
|`p`|(Un)pause|

## Development

```bash
$ git clone https://github.com/jfindlay/tetratile.git
$ cd tetratile
# <edit code>
$ tox run-parallel -m analyze format test
$ python -m build
```

## TODO

- Allow initial rate to be zero
  - Asynchronously trigger piece deactivation and row clearing on piece arriving at bottom rather than during game cycle event
  - Fundamentally conflicting expectations for game behavior with regular cycles?
- Configurably allow monomino, domino, trominoes(, pentominoes, ...?)
- AI
- Event log: timestamp, event type: control input, piece added, piece fixed, row removed
- UI
  - Scale game size to screen size
  - Scale widgets to window size
    - Boards must have fixed aspect ratios
  - Shadowing
    - Shadow piece on the stack of tetrominoes where it would be placed if dropped down in addition to or replacing the piece projection underneath the main game board
- Config
  - GUI dialog
  - Read and write to config file
