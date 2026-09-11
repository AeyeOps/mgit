"""Progress must reflect completed repository work, including skips/errors."""

import asyncio
import io
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import typer
from rich.console import Console

from mgit.commands import sync
from mgit.commands.bulk_operations import (
    BulkOperationProcessor,
    OperationType,
    UpdateMode,
)
from mgit.git import GitManager
from mgit.git.progress import GitProgress
from mgit.processing import DiffProcessor
from mgit.providers.base import Repository
from mgit.ui.progress import create_progress
from mgit.ui.sync_progress import SyncProgress


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_progress_advances_for_success_failure_and_disabled_repo(
    tmp_path, monkeypatch
):
    repositories = [
        Repository("disabled", "https://example.com/org/disabled", is_disabled=True),
        Repository("good[1]", "https://example.com/org/good[1]"),
        Repository("failed", "https://example.com/org/failed"),
    ]

    async def clone(url, output_dir, dir_name, on_progress=None):
        on_progress(GitProgress("Receiving objects", 43))
        if dir_name == "failed":
            raise subprocess.CalledProcessError(1, ["git", "clone"], stderr="failed")

    processor = BulkOperationProcessor(
        git_manager=SimpleNamespace(git_clone=clone),
        provider_manager=SimpleNamespace(
            get_authenticated_clone_url=lambda repo: repo.clone_url
        ),
        operation_type=OperationType.clone,
    )
    output = io.StringIO()
    progress = SyncProgress(console=Console(file=output, width=40))
    completed_counts = []
    finish = progress.finish_repository

    def record_finish(key, outcome):
        finish(key, outcome)
        completed_counts.append(progress.completed)

    monkeypatch.setattr(progress, "finish_repository", record_finish)
    monkeypatch.setattr(sync, "SyncProgress", lambda *args, **kwargs: progress)

    with pytest.raises(typer.Exit) as error:
        await sync.run_sync_with_progress(
            repositories, tmp_path, processor, 1, UpdateMode.pull, False, []
        )

    assert error.value.exit_code == 1
    assert completed_counts == [1, 2, 3]
    assert progress.completed == 3
    assert progress.skipped == 1
    assert progress.failed == 1
    assert progress.active_count == 0
    assert "100%" in output.getvalue()
    assert len(processor.skipped) == 1
    assert len(processor.failures) == 1


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
async def test_diff_progress_counts_task_zero(tmp_path, monkeypatch, fails):
    processor = DiffProcessor()
    detector = AsyncMock(
        side_effect=RuntimeError("cannot inspect") if fails else None,
        return_value=SimpleNamespace(error=None),
    )
    monkeypatch.setattr(processor, "_detect_repository_changes", detector)
    progress = create_progress(disable=True)
    task = progress.add_task("Detecting changes", total=2)
    assert task == 0

    changes = await processor.process_repositories([tmp_path, tmp_path], progress, task)

    assert len(changes) == 2
    assert progress.tasks[0].completed == 2
    assert progress.tasks[0].percentage == 100


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_progress_reconciles_all_pre_skipped_repositories(
    tmp_path, monkeypatch
):
    output = io.StringIO()
    panel = SyncProgress(console=Console(file=output, width=40))
    monkeypatch.setattr(sync, "SyncProgress", lambda *args, **kwargs: panel)
    processor = BulkOperationProcessor(
        git_manager=SimpleNamespace(),
        provider_manager=SimpleNamespace(),
        operation_type=OperationType.clone,
    )
    await sync.run_sync_with_progress(
        [],
        tmp_path,
        processor,
        2,
        UpdateMode.pull,
        False,
        [],
        pre_skipped=[
            ("dirty", "uncommitted changes"),
            ("folder", "not a git repository"),
        ],
    )
    assert panel.completed == panel.skipped == 2
    assert panel.failed == panel.active_count == 0
    assert "100% 2/2" in output.getvalue()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_cancels_other_repositories_when_progress_callback_fails(tmp_path):
    second_started = asyncio.Event()
    second_stopped = asyncio.Event()

    async def clone(url, output_dir, dir_name, on_progress=None):
        if dir_name == "first":
            await second_started.wait()
            on_progress(GitProgress("Receiving objects", 43))
        else:
            second_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                second_stopped.set()

    class BrokenDisplay(SyncProgress):
        def update_repository(self, key, event):
            raise ValueError("render callback failed")

    panel = BrokenDisplay(2, console=Console(file=io.StringIO()))
    processor = BulkOperationProcessor(
        git_manager=SimpleNamespace(git_clone=clone),
        provider_manager=SimpleNamespace(
            get_authenticated_clone_url=lambda repo: repo.clone_url
        ),
        operation_type=OperationType.clone,
    )
    repos = [
        Repository(name, f"https://example.invalid/org/{name}")
        for name in ("first", "second")
    ]
    with pytest.raises(ValueError, match="render callback failed"), panel:
        await asyncio.wait_for(
            processor.process_repositories(repos, tmp_path, 2, display=panel), timeout=3
        )
    assert second_stopped.is_set()
    assert panel.completed == panel.failed == 1
    assert panel.active_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode,reason",
    [(UpdateMode.skip, "already exists"), (UpdateMode.force, "removal not confirmed")],
)
async def test_existing_directory_skips_are_counted_in_panel_and_report(
    tmp_path, mode, reason
):
    (tmp_path / "existing").mkdir()
    panel = SyncProgress(1, disable=True)
    processor = BulkOperationProcessor(
        git_manager=SimpleNamespace(),
        provider_manager=SimpleNamespace(),
        operation_type=OperationType.clone,
    )
    await processor.process_repositories(
        [Repository("existing", "https://example.invalid/org/existing")],
        tmp_path,
        update_mode=mode,
        display=panel,
    )
    assert processor.skipped == [("existing", reason)]
    assert panel.completed == panel.skipped == 1
    assert panel.failed == panel.active_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_sync_streams_real_local_clone_then_pull(tmp_path, monkeypatch):
    """Provider orchestration keeps Git-stage completion separate from repo totals."""
    seed = tmp_path / "seed"
    seed.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=seed, check=True, capture_output=True
    )
    for index in range(8):
        (seed / f"file-{index}").write_text(f"initial content {index}\n" * 500)
    subprocess.run(["git", "add", "."], cwd=seed, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=seed, check=True, capture_output=True
    )
    target = tmp_path / "target"
    target.mkdir()
    repositories = [Repository("repo", "https://example.invalid/org/repo")]
    processor = BulkOperationProcessor(
        git_manager=GitManager(),
        provider_manager=SimpleNamespace(
            get_authenticated_clone_url=lambda repo: seed.as_uri()
        ),
        operation_type=OperationType.clone,
    )
    output = io.StringIO()
    events = []

    class RecordingDisplay(SyncProgress):
        def update_repository(self, key, event):
            events.append((self.completed, event))
            super().update_repository(key, event)

    monkeypatch.setattr(
        sync,
        "SyncProgress",
        lambda *args, **kwargs: RecordingDisplay(
            *args, **kwargs, console=Console(file=output, width=40)
        ),
    )
    await sync.run_sync_with_progress(
        repositories, target, processor, 2, UpdateMode.pull, False, []
    )
    assert (0, GitProgress("Receiving objects", 100)) in events
    assert (target / "repo" / "file-0").read_text() == "initial content 0\n" * 500
    events.clear()
    (seed / "file-0").write_text("upstream update\n")
    subprocess.run(
        ["git", "commit", "-am", "update"], cwd=seed, check=True, capture_output=True
    )
    await sync.run_sync_with_progress(
        repositories, target, processor, 2, UpdateMode.pull, False, []
    )
    assert (0, GitProgress("Pulling")) in events
    assert any(
        event.percentage == 100 and completed == 0 for completed, event in events
    )
    assert (target / "repo" / "file-0").read_text() == "upstream update\n"
    assert "100% 1/1" in output.getvalue()
    assert not processor.failures
