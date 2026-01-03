#!/usr/bin/env python3
"""Enhanced progress tracking utilities for mgit.

This module provides reusable progress tracking components that integrate
with Rich's Progress display system. It supports multiple progress styles,
nested progress contexts, and common operation patterns.
"""

import asyncio
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from enum import Enum
from typing import TypeVar

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

# Type variable for generic operations
T = TypeVar("T")


class ProgressStyle(str, Enum):
    """Predefined progress bar styles for different operation types."""

    FILE_OPERATION = "file_operation"
    NETWORK_OPERATION = "network_operation"
    MULTI_STEP = "multi_step"
    SIMPLE = "simple"
    DETAILED = "detailed"


class OperationStatus(str, Enum):
    """Status indicators for operations in progress tracking."""

    PENDING = "[grey50]Pending[/grey50]"
    IN_PROGRESS = "[cyan]In Progress[/cyan]"
    SUCCESS = "[green]Success[/green]"
    FAILED = "[red]Failed[/red]"
    SKIPPED = "[yellow]Skipped[/yellow]"
    WARNING = "[orange1]Warning[/orange1]"


class PercentageColumn(ProgressColumn):
    """Renders percentage complete with color coding."""

    def render(self, task) -> str:
        """Render the percentage with color based on completion."""
        if task.total is None:
            return ""
        percentage = task.percentage
        if percentage >= 100:
            return "[green]100%[/green]"
        elif percentage >= 75:
            return f"[bright_green]{percentage:>3.0f}%[/bright_green]"
        elif percentage >= 50:
            return f"[yellow]{percentage:>3.0f}%[/yellow]"
        elif percentage >= 25:
            return f"[orange1]{percentage:>3.0f}%[/orange1]"
        else:
            return f"[red]{percentage:>3.0f}%[/red]"


class StatusColumn(ProgressColumn):
    """Renders operation status with appropriate styling."""

    def __init__(self, status_width: int = 12):
        self.status_width = status_width
        super().__init__()

    def render(self, task) -> str:
        """Render the status field from task description."""
        # Extract status from task fields if available
        status = task.fields.get("status", "")
        if not status and task.description:
            # Fall back to description
            return task.description
        return str(status).ljust(self.status_width)


def get_progress_columns(style: ProgressStyle) -> list[ProgressColumn]:
    """Get appropriate progress columns for the given style.

    Args:
        style: The progress style to use

    Returns:
        List of progress columns configured for the style
    """
    if style == ProgressStyle.FILE_OPERATION:
        return [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            PercentageColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ]
    elif style == ProgressStyle.NETWORK_OPERATION:
        return [
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            PercentageColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ]
    elif style == ProgressStyle.MULTI_STEP:
        return [
            TextColumn("[progress.description]{task.description}"),
            StatusColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ]
    elif style == ProgressStyle.SIMPLE:
        return [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ]
    else:  # DETAILED
        return [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            PercentageColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ]


class ProgressManager:
    """Manages progress tracking with support for nested contexts and multiple styles.

    This class provides a high-level interface for progress tracking with:
    - Multiple progress bar styles
    - Nested progress contexts
    - Automatic task management
    - Integration with async operations
    """

    def __init__(self, console: Console | None = None):
        """Initialize the progress manager.

        Args:
            console: Rich console instance to use (creates new if None)
        """
        self.console = console or Console()
        self._progress_stack: list[Progress] = []
        self._task_stacks: list[dict[str, TaskID]] = []

    @contextmanager
    def progress_context(
        self,
        style: ProgressStyle = ProgressStyle.FILE_OPERATION,
        disable: bool = False,
        **kwargs,
    ):
        """Create a progress context with the specified style.

        Args:
            style: Progress bar style to use
            disable: Whether to disable progress display
            **kwargs: Additional arguments passed to Progress()

        Yields:
            Progress instance for the context
        """
        columns = get_progress_columns(style)
        progress = Progress(*columns, console=self.console, disable=disable, **kwargs)

        self._progress_stack.append(progress)
        self._task_stacks.append({})

        try:
            with progress:
                yield progress
        finally:
            self._progress_stack.pop()
            self._task_stacks.pop()

    def add_task(
        self,
        description: str,
        total: float | None = None,
        progress: Progress | None = None,
        **fields,
    ) -> TaskID:
        """Add a task to the current or specified progress context.

        Args:
            description: Task description
            total: Total steps for the task
            progress: Specific progress instance to use (uses current if None)
            **fields: Additional task fields

        Returns:
            Task ID for the created task
        """
        if progress is None:
            if not self._progress_stack:
                raise RuntimeError("No active progress context")
            progress = self._progress_stack[-1]

        task_id = progress.add_task(description, total=total, **fields)

        # Store task in current context if it's the active one
        if self._progress_stack and progress == self._progress_stack[-1]:
            if "name" in fields:
                self._task_stacks[-1][fields["name"]] = task_id

        return task_id

    def update_task(
        self, task_id: TaskID | str, progress: Progress | None = None, **kwargs
    ):
        """Update a task in the current or specified progress context.

        Args:
            task_id: Task ID or name to update
            progress: Specific progress instance to use (uses current if None)
            **kwargs: Task update arguments
        """
        if progress is None:
            if not self._progress_stack:
                raise RuntimeError("No active progress context")
            progress = self._progress_stack[-1]

        # Resolve task name to ID if needed
        if isinstance(task_id, str) and self._task_stacks:
            task_id = self._task_stacks[-1].get(task_id, task_id)

        progress.update(task_id, **kwargs)

    def advance_task(
        self,
        task_id: TaskID | str,
        advance: float = 1,
        progress: Progress | None = None,
    ):
        """Advance a task by the specified amount.

        Args:
            task_id: Task ID or name to advance
            advance: Amount to advance by
            progress: Specific progress instance to use (uses current if None)
        """
        if progress is None:
            if not self._progress_stack:
                raise RuntimeError("No active progress context")
            progress = self._progress_stack[-1]

        # Resolve task name to ID if needed
        if isinstance(task_id, str) and self._task_stacks:
            task_id = self._task_stacks[-1].get(task_id, task_id)

        progress.advance(task_id, advance)

    @contextmanager
    def track_operation(
        self,
        description: str,
        total: int | None = None,
        style: ProgressStyle = ProgressStyle.SIMPLE,
    ):
        """Context manager for tracking a single operation.

        Args:
            description: Operation description
            total: Total steps (None for indeterminate)
            style: Progress style to use

        Yields:
            Task ID for the operation
        """
        with self.progress_context(style=style) as progress:
            task_id = progress.add_task(description, total=total)
            try:
                yield task_id
                if total is not None:
                    progress.update(task_id, completed=total)
            except Exception:
                progress.update(
                    task_id, description=f"[red]Failed: {description}[/red]"
                )
                raise

    async def track_async_tasks(
        self,
        tasks: Iterable[Callable[[], T]],
        description: str = "Processing tasks",
        style: ProgressStyle = ProgressStyle.FILE_OPERATION,
        max_concurrent: int = 4,
    ) -> list[T | Exception]:
        """Track progress of multiple async tasks with concurrency control.

        Args:
            tasks: Iterable of async callables to execute
            description: Overall description
            style: Progress style to use
            max_concurrent: Maximum concurrent tasks

        Returns:
            List of results (values or exceptions)
        """
        tasks_list = list(tasks)
        results: list[T | Exception] = []

        async def run_with_progress(
            task_func: Callable, index: int, progress: Progress, task_id: TaskID
        ):
            """Run a single task and update progress."""
            try:
                result = await task_func()
                results.append(result)
                progress.advance(task_id, 1)
            except Exception as e:
                results.append(e)
                progress.advance(task_id, 1)

        with self.progress_context(style=style) as progress:
            overall_task = progress.add_task(description, total=len(tasks_list))

            # Create semaphore for concurrency control
            sem = asyncio.Semaphore(max_concurrent)

            async def bounded_task(task_func, index):
                async with sem:
                    await run_with_progress(task_func, index, progress, overall_task)

            # Run all tasks
            await asyncio.gather(
                *(bounded_task(task, i) for i, task in enumerate(tasks_list)),
                return_exceptions=False,
            )

        return results


# Convenience functions for common operations


@contextmanager
def track_operation(
    description: str,
    total: int | None = None,
    style: ProgressStyle = ProgressStyle.SIMPLE,
    console: Console | None = None,
):
    """Convenience function to track a single operation.

    Args:
        description: Operation description
        total: Total steps (None for indeterminate)
        style: Progress style to use
        console: Console instance to use

    Yields:
        Tuple of (Progress instance, Task ID)
    """
    manager = ProgressManager(console=console)
    with manager.progress_context(style=style) as progress:
        task_id = progress.add_task(description, total=total)
        try:
            yield progress, task_id
            if total is not None:
                progress.update(task_id, completed=total)
        except Exception:
            progress.update(task_id, description=f"[red]Failed: {description}[/red]")
            raise


def create_file_progress(console: Console | None = None) -> Progress:
    """Create a progress instance configured for file operations.

    Args:
        console: Console instance to use

    Returns:
        Configured Progress instance
    """
    return Progress(
        *get_progress_columns(ProgressStyle.FILE_OPERATION),
        console=console or Console(),
    )


def create_network_progress(console: Console | None = None) -> Progress:
    """Create a progress instance configured for network operations.

    Args:
        console: Console instance to use

    Returns:
        Configured Progress instance
    """
    return Progress(
        *get_progress_columns(ProgressStyle.NETWORK_OPERATION),
        console=console or Console(),
    )


def create_multi_step_progress(console: Console | None = None) -> Progress:
    """Create a progress instance configured for multi-step operations.

    Args:
        console: Console instance to use

    Returns:
        Configured Progress instance
    """
    return Progress(
        *get_progress_columns(ProgressStyle.MULTI_STEP), console=console or Console()
    )


def format_repo_name(repo_name: str, max_length: int = 40) -> str:
    """Format repository name for display in progress bars.

    Args:
        repo_name: Repository name to format
        max_length: Maximum length before truncation

    Returns:
        Formatted repository name
    """
    if len(repo_name) > max_length:
        return repo_name[: max_length - 3] + "..."
    return repo_name


def update_task_status(
    progress: Progress,
    task_id: TaskID,
    status: OperationStatus,
    description: str,
    completed: bool = True,
):
    """Update a task with status-appropriate formatting.

    Args:
        progress: Progress instance
        task_id: Task to update
        status: Operation status
        description: Task description
        completed: Whether to mark as completed
    """
    status_colors = {
        OperationStatus.SUCCESS: "green",
        OperationStatus.FAILED: "red",
        OperationStatus.SKIPPED: "yellow",
        OperationStatus.WARNING: "orange1",
        OperationStatus.PENDING: "grey50",
        OperationStatus.IN_PROGRESS: "cyan",
    }

    color = status_colors.get(status, "white")
    formatted_desc = f"[{color}]{description}[/{color}]"

    update_kwargs = {"description": formatted_desc}
    if completed and status != OperationStatus.IN_PROGRESS:
        update_kwargs["completed"] = 1

    progress.update(task_id, **update_kwargs)
