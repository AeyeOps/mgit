"""Regression tests for help animation terminal ownership."""

import re
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rich.console import Console
from rich.text import Text
from ruamel.yaml.error import YAMLError

from mgit.config import yaml_manager
from mgit.ui import help_animation
from mgit.ui.terminal import TerminalCaps


@pytest.fixture
def animation_config(monkeypatch, tmp_path):
    """Read animation settings from an isolated config, without cached globals."""
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr(yaml_manager, "CONFIG_FILE", config_file)
    monkeypatch.setattr(
        yaml_manager, "config_manager", yaml_manager.ConfigurationManager()
    )
    return config_file


@pytest.mark.parametrize(
    "config,enabled",
    [
        (None, False),
        ("global: {}\n", False),
        ("global:\n  help_animation: false\n", False),
        ("global:\n  help_animation: true\n", True),
    ],
)
def test_animation_requires_saved_opt_in(animation_config, config, enabled):
    """Only an explicit configuration setting turns on the help animation."""
    if config is not None:
        animation_config.write_text(config)

    assert help_animation._is_animation_enabled() is enabled


def test_animation_config_error_is_visible(animation_config):
    """Invalid configuration must not silently enable animation."""
    animation_config.write_text("global: [\n")

    with pytest.raises(YAMLError):
        help_animation._is_animation_enabled()


@pytest.mark.parametrize("enabled", [False, True])
def test_ansi_help_respects_animation_opt_in(
    animation_config, monkeypatch, capsys, enabled
):
    """Default terminal help is static; saved opt-in retains animation."""
    if enabled:
        animation_config.write_text("global:\n  help_animation: true\n")
    animation = Mock()
    monkeypatch.setattr(help_animation, "run_tree_animation", animation)
    monkeypatch.setattr(
        help_animation, "get_terminal_capabilities", lambda: TerminalCaps.ANSI
    )

    help_animation.show_animated_help("Usage: mgit [OPTIONS]\n")

    assert animation.call_count == int(enabled)
    output = capsys.readouterr().out
    assert "M   G   I   T" in output
    assert "Usage: mgit" in output


def test_immediate_skip_does_not_erase_previous_output(monkeypatch, capsys):
    """Skipping before the first frame must leave earlier terminal rows alone."""
    monkeypatch.setattr(help_animation, "_check_for_keypress", lambda: True)
    print("earlier command output")

    help_animation.run_tree_animation()

    output = capsys.readouterr().out
    assert output.startswith("earlier command output\n")
    assert not re.search(r"\x1b\[\d*A", output)
    assert "\x1b[2K" not in output


def test_interrupt_restores_terminal_and_signal_once(monkeypatch):
    """Ctrl+C must unwind terminal ownership exactly once."""
    previous_handler = object()
    old_settings = object()
    restore_signal = Mock()
    restore_terminal = Mock()
    monkeypatch.setattr(
        help_animation, "_setup_signal_handler", lambda: previous_handler
    )
    monkeypatch.setattr(help_animation, "_set_raw_mode", lambda: old_settings)
    monkeypatch.setattr(help_animation, "_restore_signal_handler", restore_signal)
    monkeypatch.setattr(help_animation, "_restore_terminal", restore_terminal)
    monkeypatch.setattr(
        help_animation,
        "_check_for_keypress",
        Mock(side_effect=help_animation.AnimationInterrupted),
    )

    with pytest.raises(KeyboardInterrupt):
        help_animation.run_tree_animation()

    restore_terminal.assert_called_once_with(old_settings)
    restore_signal.assert_called_once_with(previous_handler)


def test_basic_terminal_static_help_has_no_colors(monkeypatch, capsys):
    """NO_COLOR/BASIC help keeps branding without ANSI color escapes."""
    monkeypatch.setattr(
        help_animation, "get_terminal_capabilities", lambda: TerminalCaps.BASIC
    )

    help_animation.show_animated_help("Usage: mgit [OPTIONS]\n")

    output = capsys.readouterr().out
    assert "M   G   I   T" in output
    assert "Usage: mgit" in output
    assert "\x1b[" not in output


def test_keyboard_poll_does_not_swallow_ctrl_c(monkeypatch):
    """SIGINT during select must propagate through the polling helper."""
    monkeypatch.setattr(help_animation, "_IS_WINDOWS", False)
    monkeypatch.setattr(
        help_animation,
        "select",
        SimpleNamespace(select=Mock(side_effect=help_animation.AnimationInterrupted)),
    )

    with pytest.raises(help_animation.AnimationInterrupted):
        help_animation._check_for_keypress()


@pytest.mark.parametrize("width,height", [(80, 30), (30, 10), (8, 3)])
def test_live_frames_fit_terminal_and_restore_cursor(monkeypatch, width, height):
    """Real Rich rendering keeps colored frames within the viewport."""
    output = StringIO()
    console = Console(
        file=output,
        force_terminal=True,
        width=width,
        height=height,
        no_color=False,
        color_system="standard",
    )
    monkeypatch.setattr(help_animation, "Console", lambda **kwargs: console)
    monkeypatch.setattr(
        help_animation, "_check_for_keypress", Mock(side_effect=[False, False, True])
    )
    monkeypatch.setattr(help_animation.time, "sleep", lambda seconds: None)

    help_animation.run_tree_animation(duration=5)

    emitted = output.getvalue()
    assert "\x1b[?25l" in emitted
    assert emitted.count("\x1b[?25h") == 1
    # Each refresh begins after clear-line; measure visible cells, not ANSI bytes.
    frames = re.split(r"\r(?:\x1b\[\d*[AK])+", emitted)
    visible_frames = [Text.from_ansi(frame) for frame in frames if frame.strip()]
    assert any(frame.plain.strip() for frame in visible_frames)
    for frame in visible_frames:
        lines = frame.split("\n", allow_blank=True)
        assert all(line.cell_len <= min(60, width - 1) for line in lines)
        assert len(lines) <= min(24, height - 1) + 1
    console.print("After", highlight=False)
    assert output.getvalue()[len(emitted) :] == "After\n"


def test_animation_adapts_to_terminal_resize(monkeypatch):
    """Later frames use the updated console dimensions."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80, height=30)
    monkeypatch.setattr(help_animation, "Console", lambda **kwargs: console)
    frames = []
    render_frame = help_animation.render_tree_frame

    def record_frame(*args, **kwargs):
        frame = render_frame(*args, **kwargs)
        frames.append(Text.from_ansi(frame))
        return frame

    def resize_after_frame(seconds):
        console.width = 20
        console.height = 6

    monkeypatch.setattr(help_animation, "render_tree_frame", record_frame)
    monkeypatch.setattr(help_animation.time, "sleep", resize_after_frame)
    monkeypatch.setattr(
        help_animation, "_check_for_keypress", Mock(side_effect=[False, False, True])
    )

    help_animation.run_tree_animation(duration=5)

    assert [len(frame.split("\n")) for frame in frames] == [24, 5]
    assert [frame.split("\n")[0].cell_len for frame in frames] == [60, 19]


def test_ctrl_c_after_frame_restores_live_cursor(monkeypatch):
    """An interrupt after rendering clears Live state and shows the cursor."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=30, height=10)
    monkeypatch.setattr(help_animation, "Console", lambda **kwargs: console)
    monkeypatch.setattr(help_animation.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        help_animation,
        "_check_for_keypress",
        Mock(side_effect=[False, help_animation.AnimationInterrupted]),
    )

    with pytest.raises(KeyboardInterrupt):
        help_animation.run_tree_animation(duration=5)

    emitted = output.getvalue()
    assert emitted.count("\x1b[?25h") == 1
    console.print("After", highlight=False)
    assert output.getvalue()[len(emitted) :] == "After\n"


def test_ctrl_c_during_first_frame_restores_live_cursor(monkeypatch):
    """Initial rendering is already owned by the cleanup context."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=30, height=10)
    monkeypatch.setattr(help_animation, "Console", lambda **kwargs: console)
    monkeypatch.setattr(help_animation, "_check_for_keypress", lambda: False)
    print_frame = console.print
    interrupted = False

    def interrupt_first_frame(*args, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise help_animation.AnimationInterrupted()
        return print_frame(*args, **kwargs)

    monkeypatch.setattr(console, "print", interrupt_first_frame)

    with pytest.raises(KeyboardInterrupt):
        help_animation.run_tree_animation(duration=5)

    emitted = output.getvalue()
    assert emitted.count("\x1b[?25h") == 1
    console.print("After", highlight=False)
    assert output.getvalue()[len(emitted) :] == "After\n"
