---
active: true
iteration: 1
max_iterations: 0
completion_promise: "TASK_COMPLETE"
started_at: "2026-01-03T05:20:18Z"
---

# Spinning ASCII Git Tree for mgit --help - Ralph Loop Prompt

<completion-signal>
When ALL success criteria are verified true, output exactly:
<promise>TASK_COMPLETE</promise>

Only output this when the statement is genuinely true.
</completion-signal>

<context>
Python CLI using Typer/Click built with UV. Entry point at mgit/__main__.py with `typer.Typer()` app. Currently uses standard Typer help with `no_args_is_help=True`. Building a gloriously unnecessary ASCII art animation system inspired by the famous donut.c mathematics.
</context>

## Primary Objective

Add an animated spinning 3D ASCII Git tree that renders above the standard help text when `mgit --help` is invoked in an interactive terminal, with graceful degradation to static ASCII art when animation isn't supported.

## Deliverables

- [ ] 3D ASCII tree renderer module using donut math (rotation matrices, surface normals, directional lighting)
- [ ] Custom help formatter that intercepts Typer/Click's help display
- [ ] Terminal capability detection (ANSI support, TTY check, pipe detection)
- [ ] Static fallback ASCII tree for non-interactive terminals
- [ ] Animation loop with ANSI cursor control for in-place updates
- [ ] Clean exit handling (Ctrl+C, resize, etc.)
- [ ] Tests covering renderer math, terminal detection, and integration

<success-criteria>
## Verification (Check Before Signaling Done)

### Automated
- [ ] `uv run python scripts/make_test.py tests/ -v -k tree` passes
- [ ] `uv run python scripts/make_lint.py` passes (Ruff)
- [ ] `uv run pyright mgit/` passes (type checking)
- [ ] `uv run mgit --help` executes without error

### E2E Validation (Required Gate)
- [ ] `uv run mgit --help` in an interactive terminal shows animated spinning tree above help text
- [ ] `uv run mgit --help | cat` shows static ASCII tree (non-TTY fallback)
- [ ] `uv run mgit --help | head -1` works without hanging (pipe detection)
- [ ] Pressing Ctrl+C during animation exits cleanly without traceback
- [ ] `TERM=dumb uv run mgit --help` shows static fallback

### Manual
- [ ] Tree visually rotates smoothly (not choppy)
- [ ] Lighting effect creates visible "shimmer" as tree rotates
- [ ] Tree shape is recognizable as a tree (trunk + foliage canopy)
- [ ] Animation runs for ~3-5 seconds before transitioning to help text
</success-criteria>

<architecture-first>
## Phase 0: Understand Before Building

Research the codebase and external techniques:
- Read `mgit/__main__.py` to understand current Typer setup
- Study the donut.c algorithm at https://www.a1k0n.net/2011/07/20/donut-math.html
- Understand how Typer/Click handles `--help` (callback, `invoke_without_command`)
- Identify how to intercept or replace the help formatter
- Note terminal detection patterns (`sys.stdout.isatty()`, `os.get_terminal_size()`, `TERM` env var)

Key architecture decisions to document:
1. Where the animation module lives: `mgit/ui/ascii_tree.py` or `mgit/utils/`
2. How to hook into Typer's help: custom callback vs Click's `HelpFormatter`
3. Frame timing strategy: `time.sleep()` vs `select()` for responsiveness
4. 3D shape: Tree as composite of cone (foliage) + cylinder (trunk)

<idempotency-check>
If tree renderer already exists in mgit/ui/ → extend it, skip to integration
If CLAUDE.md has architecture decisions → follow them
</idempotency-check>
</architecture-first>

<e2e-strategy>
## Phase 1: E2E Test Strategy (Design Before Building)

### Questions to Answer
1. How does a user see this feature work? They type `mgit --help` and see a spinning tree
2. What's the simplest verification? Run `mgit --help` in terminal, observe animation
3. What would make you confident? Animation runs, then help text appears, no crashes

### Design E2E Validation
- Primary E2E test: `timeout 10 uv run mgit --help` in TTY - expect animation then help
- Pipe fallback test: `uv run mgit --help | grep -q "Multi-Git CLI"` - expect static tree + help
- Keyboard interrupt test: Start `mgit --help`, send SIGINT, expect clean exit code 130

### Integration Test Script
Create `tests/integration/test_help_animation.py`:
```python
# Test that spawns actual process, verifies output patterns
# Uses pty.spawn() to simulate TTY for animation test
# Uses subprocess.run() with PIPE for static fallback test
```

<idempotency-check>
If E2E tests exist and pass → skip to Phase 2
</idempotency-check>
</e2e-strategy>

## Phase 2: Implement 3D Tree Renderer

Create the ASCII art engine using donut math principles.

### The Mathematics
```
1. Define tree as parametric surface:
   - Foliage: cone or paraboloid, z = height - sqrt(x² + y²)
   - Trunk: cylinder, x² + y² < radius², z < trunk_height

2. For each frame:
   a. Apply rotation matrices (Rz * Ry * Rx) for spin
   b. Project 3D → 2D using perspective or orthographic
   c. Calculate surface normal at each point
   d. Dot product normal with light direction → luminance
   e. Map luminance to character: " .,-~:;=!*#$@"

3. Z-buffer for occlusion handling
```

### Module Structure
```
mgit/ui/
├── __init__.py
├── ascii_tree.py      # 3D tree renderer, rotation, lighting
├── terminal.py        # TTY detection, ANSI capabilities
└── help_animation.py  # Orchestrates animation + help display
```

### Done When
- [ ] `python -c "from mgit.ui.ascii_tree import render_tree_frame; print(render_tree_frame(0.0))"` outputs ASCII tree
- [ ] `python -c "from mgit.ui.ascii_tree import render_tree_frame; print(render_tree_frame(1.57))"` outputs rotated tree (visibly different)
- [ ] Unit tests verify rotation math and character mapping

## Phase 3: Terminal Capability Detection

Robust detection of what the terminal can handle.

### Detection Logic
```python
def get_terminal_capabilities() -> TerminalCaps:
    if not sys.stdout.isatty():
        return TerminalCaps.PIPE  # Static only

    term = os.environ.get('TERM', '')
    if term in ('dumb', ''):
        return TerminalCaps.DUMB  # Static only

    # Check for ANSI support
    if can_use_ansi():  # CSI query or heuristic
        return TerminalCaps.ANSI  # Full animation

    return TerminalCaps.BASIC  # Static with color maybe
```

### Done When
- [ ] `python -c "from mgit.ui.terminal import get_terminal_capabilities; print(...)"` returns appropriate enum
- [ ] Piped execution correctly detects non-TTY
- [ ] `TERM=dumb` correctly triggers fallback path

## Phase 4: ANSI Animation Engine

Frame rendering with cursor control for smooth animation.

### ANSI Sequences Used
```
\033[?25l        # Hide cursor
\033[?25h        # Show cursor
\033[H           # Move cursor to home (0,0)
\033[2J          # Clear screen
\033[{n}A        # Move cursor up n lines
\033[{n}B        # Move cursor down n lines
```

### Animation Loop
```python
def run_animation(duration: float = 4.0, fps: float = 15.0):
    frame_time = 1.0 / fps
    start = time.monotonic()
    angle = 0.0

    hide_cursor()
    try:
        while time.monotonic() - start < duration:
            frame = render_tree_frame(angle)
            move_cursor_home()
            print(frame, end='', flush=True)
            angle += 0.1
            time.sleep(frame_time)
    finally:
        show_cursor()
        clear_animation_area()
```

### Done When
- [ ] Animation runs smoothly at ~15 FPS
- [ ] Cursor is hidden during animation
- [ ] Ctrl+C exits cleanly with cursor restored
- [ ] Window resize doesn't break display (graceful handling)

## Phase 5: Integrate with Typer Help

Hook into Typer/Click's help mechanism.

### Integration Strategy
Option A: Override Click's `HelpFormatter.write()`
Option B: Use Typer's `callback` with custom help logic
Option C: Replace `app()`'s behavior when `--help` is the only arg

Likely best approach - custom callback:
```python
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h")):
    if help or ctx.invoked_subcommand is None:
        if get_terminal_capabilities() == TerminalCaps.ANSI:
            run_tree_animation()
        else:
            print_static_tree()
        # Then show normal help
        click.echo(ctx.get_help())
        raise typer.Exit()
```

### Done When
- [ ] `uv run mgit --help` triggers animation before help text
- [ ] `uv run mgit` (no args) also shows animation + help
- [ ] `uv run mgit sync --help` shows only sync help (no animation)
- [ ] Existing CLI functionality unchanged

## Phase 6: Static Fallback Art

A beautiful static ASCII tree for non-animated contexts.

### Static Tree Design
```
         🌟
        /||\
       /_||_\
      /  ||  \
     /___||___\
    /    ||    \
   /_____||_____\
        |||
        |||
       /|||\
      /_____\
```

Or a more elaborate hand-crafted design. The static version should still be visually appealing and on-theme.

### Done When
- [ ] Static tree renders correctly in pipe mode
- [ ] Static tree has consistent width for terminal display
- [ ] Optional: Static tree includes subtle "git branch" visual elements

## Phase 7: Unit Tests

Comprehensive testing of the renderer and detection logic.

### Test Coverage
```python
# tests/unit/test_ascii_tree.py
def test_rotation_matrix_identity():
    """Zero rotation produces identity transformation."""

def test_rotation_matrix_90_degrees():
    """90-degree rotation produces expected coordinates."""

def test_luminance_mapping():
    """Light direction produces correct character density."""

def test_tree_frame_dimensions():
    """Rendered frame fits in 80x24 terminal."""

# tests/unit/test_terminal.py
def test_pipe_detection(monkeypatch):
    """Non-TTY stdout detected as pipe."""

def test_dumb_terminal(monkeypatch):
    """TERM=dumb triggers fallback."""

def test_ansi_detection():
    """Interactive terminal detected correctly."""
```

### Done When
- [ ] `uv run python scripts/make_test.py tests/unit/ -v -k tree` passes
- [ ] `uv run python scripts/make_test.py tests/unit/ -v -k terminal` passes

<e2e-validation>
## Phase 8: E2E Validation (Hard Gate Before Completion)

### Run E2E Tests
- [ ] Execute: `timeout 10 uv run mgit --help` in interactive terminal
- [ ] Verify: Animated tree appears, rotates smoothly, then help text displays
- [ ] Execute: `uv run mgit --help 2>&1 | head -20`
- [ ] Verify: Static tree + help text appears, no hanging
- [ ] Execute: `TERM=dumb uv run mgit --help`
- [ ] Verify: Static fallback displays

### Keyboard Interrupt Test
```bash
timeout 2 uv run mgit --help || true
# Should exit cleanly, cursor visible, no Python traceback
```

### Confirm User Experience
- [ ] A user unfamiliar with the code would see a fun spinning tree then readable help
- [ ] Animation adds whimsy without impeding actual CLI usage
- [ ] Pipe users get information immediately without animation delay
</e2e-validation>

<scope-boundaries>
## Scope Boundaries

### In Scope
- 3D ASCII tree renderer with donut math
- Rotation animation with directional lighting
- ANSI terminal animation with cursor control
- Terminal capability detection
- Static ASCII fallback
- Integration with `mgit --help` only (not subcommand help)
- Clean signal handling (Ctrl+C)
- Unit and integration tests

### Out of Scope (Do Not Do These)
- Do not add animation to subcommand help (`mgit sync --help`)
- Do not add color to the ASCII art (keep it monochrome character-density)
- Do not add configuration options for animation duration/speed
- Do not add sound effects or terminal bells
- Do not persist animation preferences
- Do not add multiple shape options (just the tree)
- Do not support Windows-specific terminal APIs (ANSI is fine)
- Do not add --no-animation flag (capability detection handles this)
- Do not over-engineer: a single ~200-line module is fine
- Do not create separate packages for this feature
- Do not add async/await where sync is sufficient
- Do not add docstrings to obvious helper functions
</scope-boundaries>

<engineering-principles>
## Engineering Principles

### Error Handling
- Animation failures should silently fall back to static
- Never crash the CLI because animation failed
- Terminal detection should be conservative (when in doubt, use static)

### Code Quality
- `uv run python scripts/make_lint.py` must pass (Ruff)
- `uv run pyright mgit/` must pass (type checking)
- Tests verify behavior, not implementation details

### Math Precision
- Use `math` module, not numpy (keep dependencies minimal)
- Precompute sin/cos tables if performance is an issue
- Frame rate should be ~15 FPS (66ms per frame) for smoothness

### Package Management
- Use UV exclusively for all Python operations
- No new dependencies for this feature (pure stdlib: math, time, sys, os)

### Architecture
- Animation code isolated in `mgit/ui/` module
- Main CLI logic unchanged except for help hook
- Clean separation: renderer | terminal | orchestration
</engineering-principles>

<loop-awareness>
## Loop Iteration Awareness

### Already Done? Skip It
- If `mgit/ui/ascii_tree.py` exists with working renderer → skip to integration
- If help animation already works → run tests, verify, complete
- If tests pass → mark complete, move on

### Progress Tracking
- Update CLAUDE.md with any architecture decisions
- Commit working increments: renderer first, then integration, then tests

### Stuck Detection
If same rendering artifact appears 3+ iterations:
1. Simplify the 3D shape (start with sphere, then add tree complexity)
2. Reduce frame rate to debug
3. Print intermediate math values
4. Consider if donut math is overkill (maybe simpler rotation)
</loop-awareness>

<creative-latitude>
## Creative Latitude

This is a whimsical feature. The implementer has creative freedom for:

### Tree Shape Options (pick one)
1. **Conifer**: Cone-shaped foliage on cylindrical trunk (classic Christmas tree)
2. **Deciduous**: Spherical canopy on trunk (like an oak)
3. **Bonsai**: Asymmetric, artistic, flowing branches
4. **Git-morphic**: Tree with "branches" that look like git branch diagrams

### Animation Style
1. **Continuous rotation**: Tree spins 360° over animation duration
2. **Wobble**: Tree rocks back and forth
3. **Growth**: Tree "grows" from seed to full size, then fades
4. **Orbit**: Camera orbits around stationary tree

### Lighting Effects
1. **Single directional light**: Classic donut.c style
2. **Moving light**: Light source orbits, creating shifting shadows
3. **Pulsing**: Light intensity varies creating "shimmer"

### Static Fallback Style
1. **Simple outline**: Basic ASCII tree shape
2. **Detailed art**: Hand-crafted multi-line ASCII masterpiece
3. **Text art**: "MGIT" spelled out in tree-like typography

The implementer should choose what looks best and is achievable. The goal is delight, not perfection.
</creative-latitude>

<emergency-stops>
## Emergency Stop Conditions

Halt the loop and report if:
- Animation causes terminal corruption that persists after exit
- Integration breaks existing `mgit` commands
- Tests cannot run due to import errors
- Renderer math produces NaN or infinite values consistently
- Terminal detection causes crashes on common terminals
- Same visual artifact (garbled output) appears 3+ consecutive iterations
- Integration with Typer requires monkey-patching Click internals
- Feature requires adding external dependencies
</emergency-stops>
