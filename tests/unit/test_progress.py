"""Progress display behavior across viewport, logging, and worker lifecycles."""

import asyncio
import io
import logging
from unittest.mock import Mock

import pytest
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text

from mgit.ui.progress import ProgressLogFilter, create_progress, progress_console
from mgit.utils.async_executor import AsyncExecutor, ExecutionMode


def render_progress(progress) -> str:
    with progress.console.capture() as capture:
        progress.console.print(progress.get_renderable())
    return capture.get()


@pytest.mark.parametrize("completed, percentage", [(0, "0%"), (3, "30%"), (10, "100%")])
def test_narrow_progress_preserves_percentage_and_count(completed, percentage):
    console = Console(file=io.StringIO(), width=40, height=8, force_terminal=False)
    progress = create_progress(console=console, disable=True)
    task = progress.add_task("A very long repository path " * 8, total=10)
    progress.update(task, completed=completed)

    output = render_progress(progress)

    assert percentage in output
    assert f"{completed}/10" in output
    assert len(output.splitlines()) == 1
    assert len(output.rstrip("\n")) <= 40
    assert "…" in output


def test_disabled_progress_has_no_output_refresh_or_logging_suppression(monkeypatch):
    output = io.StringIO()
    progress = create_progress(
        console=Console(file=output, force_terminal=True), disable=True
    )
    start = Mock()
    monkeypatch.setattr(progress.live, "start", start)
    info = logging.makeLogRecord({"levelno": logging.INFO})

    with progress:
        task = progress.add_task("Hidden", total=1)
        progress.update(task, completed=1, refresh=True)
        assert ProgressLogFilter().filter(info)

    assert not progress.live.auto_refresh
    start.assert_not_called()
    assert output.getvalue() == ""


def test_progress_uses_shared_console():
    assert create_progress().console is progress_console
    assert AsyncExecutor().console is progress_console


def test_console_logging_restores_after_progress_exception():
    console_output = io.StringIO()
    file_output = io.StringIO()
    console = Console(file=console_output, force_terminal=False)
    logger = logging.Logger("progress-test", logging.DEBUG)
    console_handler = RichHandler(
        console=console, show_time=False, show_level=False, show_path=False
    )
    console_handler.addFilter(ProgressLogFilter())
    logger.addHandler(console_handler)
    logger.addHandler(logging.StreamHandler(file_output))

    logger.info("before-progress")
    with (
        pytest.raises(RuntimeError, match="failed operation"),
        create_progress(console=console) as progress,
    ):
        progress.add_task("Repositories", total=2)
        logger.debug("hidden-debug")
        logger.info("hidden-info")
        logger.warning("visible-warning")
        raise RuntimeError("failed operation")
    logger.info("after-progress")

    captured = console_output.getvalue()
    assert "hidden-debug" not in captured
    assert "hidden-info" not in captured
    assert "before-progress" in captured
    assert "visible-warning" in captured
    assert "after-progress" in captured
    assert "hidden-debug" in file_output.getvalue()
    assert "hidden-info" in file_output.getvalue()


def test_nested_progress_keeps_logging_suppressed_until_outer_stops():
    console = Console(file=io.StringIO(), force_terminal=False)
    progress_filter = ProgressLogFilter()
    info = logging.makeLogRecord({"levelno": logging.INFO})
    with create_progress(console=console):
        with create_progress(console=console):
            assert not progress_filter.filter(info)
        assert not progress_filter.filter(info)
    assert progress_filter.filter(info)


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrency, item_count", [(20, 32), (20, 2), (4, 0)])
async def test_concurrent_rows_are_bounded_without_reducing_workers(
    monkeypatch, concurrency, item_count
):
    console = Console(file=io.StringIO(), width=40, height=6, force_terminal=False)
    executor = AsyncExecutor(concurrency=concurrency, rich_console=console)
    progress = create_progress(console=console, disable=True)
    monkeypatch.setattr(executor, "_create_progress", lambda: progress)
    running = peak_running = 0
    completed_counts = []

    async def process(item):
        nonlocal running, peak_running
        running += 1
        peak_running = max(peak_running, running)
        visible = [task for task in progress.tasks if task.visible]
        assert len(visible) <= console.height - 2
        assert len(render_progress(progress).splitlines()) <= console.height - 2
        active = next(
            task
            for task in progress.tasks[1:]
            if Text.from_markup(task.description).plain.endswith(f"repo-{item}[red]")
        )
        assert active.total is None
        assert active.completed == 0
        assert not active.finished
        completed_counts.append(progress.tasks[0].completed)
        await asyncio.sleep(0)
        running -= 1
        return item * 2

    results, errors = await executor.run_batch(
        list(range(item_count)),
        process,
        item_description=lambda item: f"repo-{item}[red]",
    )

    assert results == [item * 2 for item in range(item_count)]
    assert errors == []
    assert peak_running == min(concurrency, item_count)
    assert len(progress.tasks) == min(concurrency, item_count) + 1
    assert progress.tasks[0].completed == item_count
    if item_count:
        assert "100%" in render_progress(progress)
        assert all(task.finished for task in progress.tasks[1:])
    if item_count > concurrency:
        assert any(0 < count < item_count for count in completed_counts)


@pytest.mark.asyncio
@pytest.mark.parametrize("height, item_count", [(3, 2), (4, 3), (6, 3)])
async def test_sequential_progress_fits_short_viewports(
    monkeypatch, height, item_count
):
    console = Console(file=io.StringIO(), width=40, height=height, force_terminal=False)
    executor = AsyncExecutor(mode=ExecutionMode.SEQUENTIAL, rich_console=console)
    progress = create_progress(console=console, disable=True)
    monkeypatch.setattr(executor, "_create_progress", lambda: progress)

    async def process(item):
        assert len([task for task in progress.tasks if task.visible]) <= height - 2
        assert len(render_progress(progress).splitlines()) <= height - 2
        return item

    results, errors = await executor.run_batch(
        list(range(item_count)), process, item_description=lambda item: f"[repo]{item}"
    )

    assert results == list(range(item_count))
    assert errors == []
    assert "100%" in render_progress(progress)


@pytest.mark.asyncio
async def test_worker_errors_and_callbacks_preserve_results(monkeypatch):
    console = Console(file=io.StringIO(), force_terminal=False)
    executor = AsyncExecutor(concurrency=1, rich_console=console)
    progress = create_progress(console=console, disable=True)
    monkeypatch.setattr(executor, "_create_progress", lambda: progress)
    successes = []
    failures = []

    async def process(item):
        if item == 1:
            raise ValueError("bad repository")
        return item * 2

    results, errors = await executor.run_batch(
        [0, 1, 2],
        process,
        on_success=lambda item, result: successes.append((item, result)),
        on_error=lambda item, error: failures.append((item, error)),
    )

    assert results == [0, None, 4]
    assert successes == [(0, 0), (2, 4)]
    assert errors == failures
    assert len(errors) == 1
    assert errors[0][0] == 1
    assert isinstance(errors[0][1], ValueError)
    assert progress.tasks[0].completed == 3
