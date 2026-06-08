# Backlog

Deferred issues and known gaps, with context for future work.

## Coverage floor

The current `fail_under` in `.coveragerc` is 39% — the measured tox
coverage — rather than 100%.  Two compounding problems block a higher floor:

**1. Tkinter UI-wiring modules are untested headlessly**

Four modules have no standalone testable logic:

| Module | Reason |
|---|---|
| `__main__.py` | CLI entry point — argument parsing and process startup |
| `config_ui.py` | Tkinter preferences dialog — pure UI wiring |
| `input_human.py` | Tkinter key-binding registration — two lines of widget setup |
| `log_viewer.py` | Tkinter log viewer widget — pure UI layout |

Testing these is a UX discipline, not a unit/integration discipline.  The
interesting behaviour (does the dialog appear, do keybindings fire) is
above the code-coverage layer.

**2. `pytest-cov` omit patterns are not applied in the isolated tox build**

`pytest-cov` starts coverage after `tetratile` is already imported during
collection (emits `CoverageWarning: module-not-measured`).  This means the
`omit` patterns in `.coveragerc` never filter the tkinter modules because
they have already been traced.  The underlying cause is that tox's
`isolated_build = true` installs the package into the tox virtualenv, not
as an editable install, so the modules are measured from the site-packages
path rather than the source tree.

**Future work:**

- Explore headless tkinter testing (`Xvfb`, or `pytest-xvfb`) so UI modules
  can be run in CI.
- Fix the `pytest-cov` import-before-measurement issue, either by switching
  to editable installs in the test env or using `--import-mode=importlib`.
- Once both are resolved, raise `fail_under` to 100.

## `AgentRunner` requires `$DISPLAY` even when `show_gui=False`

`AgentRunner.run()` unconditionally creates `tk.Tk()` at line 112 of
`agent_runner.py`, which raises `TclError: no display name and no $DISPLAY
environment variable` in headless CI.  Eight tests in
`tests/integration/test_agent_runner.py` fail for this reason.

The fix is to decouple the game-logic loop from the tkinter event loop when
`show_gui=False`, so that `AgentRunner` can run without any display.  This
requires separating the pure-logic tick path from the tkinter `after()`
scheduling in `TetraTile`.
