"""Sync panel state and real Rich rendering across terminal dimensions."""

import asyncio
import io
import logging
from unittest.mock import Mock

import pytest
from rich.cells import cell_len
from rich.console import Console

import mgit.ui.sync_progress as sync_progress
from mgit.git.progress import GitProgress
from mgit.ui.progress import ProgressLogFilter, progress_console
from mgit.ui.sync_progress import SyncProgress


def make_panel(*, width=40, height=10, total=10, disable=True):
    console = Console(
        file=io.StringIO(), width=width, height=height, force_terminal=False
    )
    return SyncProgress(total, console=console, disable=disable)


def render(panel):
    with panel.console.capture() as capture:
        panel.console.print(panel.get_renderable())
    rows = capture.get().splitlines()
    assert all(cell_len(row) <= panel.console.width for row in rows)
    return rows


@pytest.mark.parametrize("width", [20, 40])
def test_overall_bar_preserves_repository_metrics_and_row_count(width):
    panel = make_panel(width=width)
    rows = render(panel)
    assert len(rows) == 3
    assert "0% 0/10" in rows[0]
    assert "─" in rows[0]

    for index, outcome in enumerate(("success", "skipped", "failed")):
        panel.start_repository(str(index), "Long repository name " * 8, "Cloning")
        panel.finish_repository(str(index), outcome)

    rows = render(panel)
    assert len(rows) == 3
    assert "30% 3/10" in rows[0]
    assert "━" in rows[0] and "─" in rows[0]
    assert panel.completed == 3
    assert panel.skipped == panel.failed == 1
    assert panel.active_count == 0
    assert "Long repository" not in rows[2]
    assert ("Skipped:1" if width == 40 else "S:1") in rows[1]
    assert ("Failed:1" if width == 40 else "F:1") in rows[1]


def test_unknown_and_empty_phases_never_fabricate_discovery_percentage():
    panel = make_panel(total=None)
    rows = render(panel)
    assert len(rows) == 3
    assert "0/?" in rows[0]
    assert "%" not in rows[0]
    assert rows[2].strip() == "Discovering"

    panel.set_message("Listing provider repositories")
    assert render(panel)[2].strip() == "Listing provider repositories"
    panel.begin_phase("Syncing", total=0)
    rows = render(panel)
    assert len(rows) == 3
    assert "100% 0/0" in rows[0]
    assert rows[2].strip() == "No repositories"


def test_git_stage_percentage_resets_without_completing_a_repository():
    panel = make_panel()
    panel.begin_phase("Syncing", total=10, completed=3, skipped=2, failed=1)
    panel.start_repository("repo", "repo", "Starting")
    panel.update_repository("repo", GitProgress("Receiving objects", 100))

    rows = render(panel)
    assert "30% 3/10" in rows[0]
    assert "100%" in rows[2]
    assert panel.completed == 3
    assert panel.active_count == 1

    panel.update_repository("repo", GitProgress("Resolving deltas"))
    rows = render(panel)
    assert "30% 3/10" in rows[0]
    assert "%" not in rows[2]

    panel.update_repository("repo", GitProgress("Resolving deltas", 43))
    assert "43%" in render(panel)[2]
    panel.finish_repository("repo", "success")
    rows = render(panel)
    assert "40% 4/10" in rows[0]
    assert "43%" not in rows[2]
    assert panel.skipped == 2
    assert panel.failed == 1


def test_many_workers_share_one_activity_row_and_finished_worker_disappears():
    panel = make_panel(total=20, height=4)
    for index in range(20):
        panel.start_repository(str(index), f"repo-{index}", "Starting")
    assert panel.active_count == 20
    assert len(render(panel)) == 3
    assert "repo-19" in render(panel)[2]

    panel.update_repository("1", GitProgress("Fetching", 51))
    rows = render(panel)
    assert "repo-1 " in rows[2]
    assert "51%" in rows[2]
    assert "Active:20" in rows[1]

    panel.finish_repository("1", "success")
    rows = render(panel)
    assert "repo-19" in rows[2]
    assert "51%" not in rows[2]
    assert panel.active_count == 19
    assert "5% 1/20" in rows[0]


@pytest.mark.parametrize("width", [20, 40])
def test_resize_recomputes_rows_and_keeps_metrics_visible(width):
    panel = make_panel(width=100)
    panel.start_repository("repo", "A very long name 文件 😀 " * 5, "Starting")
    panel.update_repository("repo", GitProgress("Receiving objects", 43))
    assert len(render(panel)) == 3

    panel.console.width = width
    panel.console.height = 4
    rows = render(panel)
    assert len(rows) == 3
    assert "0% 0/10" in rows[0]
    assert "43%" in rows[2]
    assert "ago" in rows[2]
    assert "…" in rows[2]

    panel.console.height = 3
    rows = render(panel)
    assert len(rows) == 2
    assert "0% 0/10" in rows[0]
    assert "43%" in rows[1]

    panel.console.height = 2
    rows = render(panel)
    assert len(rows) == 1
    assert "0% 0/10" in rows[0]


@pytest.mark.parametrize("width,height", [(1, 1), (2, 2), (5, 2)])
def test_smallest_terminal_sizes_remain_one_bounded_row(width, height):
    panel = make_panel(width=width, height=height)
    panel.start_repository("repo", "文件", "Starting")
    assert len(render(panel)) == 1


def test_names_and_stage_are_literal_and_cannot_inject_rows_or_terminal_codes():
    panel = make_panel(width=120)
    panel.start_repository("repo", "[red]文件😀\nnext\tline\x1b[31m", "Starting")
    panel.update_repository("repo", GitProgress("[bold]Receiving\r objects", 9))

    rows = render(panel)
    assert len(rows) == 3
    assert "[red]文件😀 next line [31m" in rows[2]
    assert "[bold]Receiving  objects" in rows[2]
    assert "\x1b" not in "".join(rows)

    panel.finish_repository("repo", "success")
    panel.set_message("[blue]Waiting\nfor\rprovider")
    rows = render(panel)
    assert len(rows) == 3
    assert rows[2].strip() == "[blue]Waiting for provider"


def test_elapsed_and_last_activity_continue_during_silence(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr(sync_progress, "monotonic", lambda: clock["now"])
    panel = make_panel()
    panel.start_repository("repo", "repo", "Connecting")

    clock["now"] = 112.0
    rows = render(panel)
    assert "00:12" in rows[1]
    assert "12s ago" in rows[2]
    assert "%" not in rows[2]

    panel.update_repository("repo", GitProgress("Receiving objects", 25))
    assert "0s ago" in render(panel)[2]
    clock["now"] = 113.0
    assert "1s ago" in render(panel)[2]
    panel.finish_repository("repo", "success")
    panel.begin_phase("Pulling", total=5)
    assert "00:13" in render(panel)[1]
    assert render(panel)[2].strip() == "Pulling"


def test_phase_changes_clear_old_workers_and_reconcile_initial_counts():
    panel = make_panel(total=None)
    panel.start_repository("old", "old-repository", "Scanning")
    panel.begin_phase("Pulling", total=5, completed=2, skipped=1, failed=1)

    assert panel.completed == 2
    assert panel.skipped == panel.failed == 1
    assert panel.active_count == 0
    rows = render(panel)
    assert len(rows) == 3
    assert "40% 2/5" in rows[0]
    assert "Pulling" in rows[0]
    assert rows[2].strip() == "Pulling"

    panel.start_repository("new", "new-repository", "Connecting")
    assert "Pulling" in render(panel)[0]


@pytest.mark.parametrize(
    "outcome,message", [("success", "Complete"), ("failed", "Finished with failures")]
)
def test_final_row_replaces_active_repository_when_finished(outcome, message):
    panel = make_panel(total=1)
    panel.start_repository("repo", "last-repository", "Starting")
    panel.finish_repository("repo", outcome)

    rows = render(panel)
    assert "100% 1/1" in rows[0]
    assert rows[2].strip() == message
    assert panel.active_count == 0


@pytest.mark.parametrize(
    "error,message",
    [
        (KeyboardInterrupt, "Cancelled"),
        (asyncio.CancelledError, "Cancelled"),
        (RuntimeError, "Stopped"),
    ],
)
def test_interruption_preserves_actual_completion_and_clears_active_workers(
    error, message
):
    panel = make_panel(total=3)
    with pytest.raises(error), panel:
        panel.start_repository("complete", "complete", "Starting")
        panel.finish_repository("complete", "success")
        panel.start_repository("active", "active", "Starting")
        raise error()

    rows = render(panel)
    assert "33% 1/3" in rows[0]
    assert rows[2].strip() == message
    assert panel.active_count == 0
    assert panel.completed == 1


def test_disabled_panel_is_silent_and_does_not_start_a_refresh_thread(
    monkeypatch, capsys
):
    panel = SyncProgress(1, disable=True)
    start = Mock()
    monkeypatch.setattr(panel.live, "start", start)
    with panel:
        panel.start_repository("repo", "repo", "Starting")
        panel.update_repository("repo", GitProgress("Receiving objects", 50))
        panel.finish_repository("repo", "success")

    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    assert panel.console is progress_console
    assert not panel.live.auto_refresh
    start.assert_not_called()


def test_panel_uses_existing_console_log_coordination():
    panel = make_panel(disable=False)
    info = logging.makeLogRecord({"levelno": logging.INFO})
    warning = logging.makeLogRecord({"levelno": logging.WARNING})
    log_filter = ProgressLogFilter()
    with panel:
        assert not log_filter.filter(info)
        assert log_filter.filter(warning)
    assert log_filter.filter(info)
