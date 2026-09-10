"""Progress must reflect completed repository work, including skips/errors."""

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
from mgit.processing import DiffProcessor
from mgit.providers.base import Repository
from mgit.ui.progress import create_progress


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

    async def clone(url, output_dir, dir_name):
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
    progress = create_progress(console=Console(file=output, width=40))
    completed_counts = []
    update = progress.update

    def record_update(task_id, **kwargs):
        update(task_id, **kwargs)
        completed_counts.append(progress.tasks[0].completed)

    monkeypatch.setattr(progress, "update", record_update)
    monkeypatch.setattr(sync, "create_progress", lambda: progress)

    with pytest.raises(typer.Exit) as error:
        await sync.run_sync_with_progress(
            repositories, tmp_path, processor, 1, UpdateMode.pull, False, []
        )

    assert error.value.exit_code == 1
    assert completed_counts == [1, 2, 3]
    assert progress.tasks[0].percentage == 100
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
