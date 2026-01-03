"""
Async Executor Module

Provides reusable async execution utilities with configurable concurrency,
progress tracking, and error collection for batch operations.
"""

import asyncio
import logging
import subprocess
from collections.abc import Callable, Coroutine
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Column

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExecutionMode(str, Enum):
    """Execution modes for async operations."""

    CONCURRENT = "concurrent"  # Run all tasks concurrently (with semaphore limit)
    SEQUENTIAL = "sequential"  # Run tasks one by one


class AsyncExecutor:
    """
    A generalized async executor for running batch operations with progress tracking.

    Features:
    - Configurable concurrency limits using semaphores
    - Progress tracking with Rich Progress bars
    - Error collection without stopping batch operations
    - Support for both concurrent and sequential execution modes
    - Flexible task status updates

    Example:
        async def process_item(item: str) -> str:
            # Your async processing logic here
            await asyncio.sleep(1)
            return f"Processed {item}"

        executor = AsyncExecutor(concurrency=4)
        items = ["item1", "item2", "item3"]
        results = await executor.run_batch(
            items=items,
            process_func=process_item,
            task_description="Processing items",
            item_description=lambda item: f"Item: {item}"
        )
    """

    def __init__(
        self,
        concurrency: int = 4,
        mode: ExecutionMode = ExecutionMode.CONCURRENT,
        rich_console: Console | None = None,
    ):
        """
        Initialize the AsyncExecutor.

        Args:
            concurrency: Maximum number of concurrent operations (for CONCURRENT mode)
            mode: Execution mode (CONCURRENT or SEQUENTIAL)
            rich_console: Optional Rich Console to use for progress bars
        """
        self.concurrency = concurrency
        self.mode = mode
        self.semaphore = (
            asyncio.Semaphore(concurrency) if mode == ExecutionMode.CONCURRENT else None
        )
        self.console = rich_console or Console(stderr=True)
        self._bar_width = 28
        self._min_desc_width = 24

    async def run_batch(
        self,
        items: list[T],
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        task_description: str = "Processing items...",
        item_description: Callable[[T], str] | None = None,
        show_progress: bool = True,
        collect_errors: bool = True,
        on_error: Callable[[T, Exception], None] | None = None,
        on_success: Callable[[T, Any], None] | None = None,
    ) -> tuple[list[Any], list[tuple[T, Exception]]]:
        """
        Run a batch of async operations with progress tracking.

        Args:
            items: List of items to process
            process_func: Async function to process each item
            task_description: Description for the overall progress bar
            item_description: Function to generate description for each item
            show_progress: Whether to show progress bars
            collect_errors: Whether to collect errors (if False, first error will raise)
            on_error: Optional callback for error handling
            on_success: Optional callback for successful processing

        Returns:
            Tuple of (results, errors) where:
            - results: List of successful results (None for failed items)
            - errors: List of (item, exception) tuples for failed items
        """
        results = [None] * len(items)
        errors: list[tuple[T, Exception]] = []

        if not show_progress:
            # Run without progress bars
            if self.mode == ExecutionMode.CONCURRENT:
                tasks = [
                    self._process_item_with_semaphore(
                        idx,
                        item,
                        process_func,
                        results,
                        errors,
                        collect_errors,
                        on_error,
                        on_success,
                    )
                    for idx, item in enumerate(items)
                ]
                await asyncio.gather(*tasks)
            else:
                # Sequential execution
                for idx, item in enumerate(items):
                    await self._process_item(
                        idx,
                        item,
                        process_func,
                        results,
                        errors,
                        collect_errors,
                        on_error,
                        on_success,
                    )
        else:
            # Run with progress tracking
            with self._create_progress() as progress:
                overall_task = progress.add_task(task_description, total=len(items))

                if self.mode == ExecutionMode.CONCURRENT:
                    await self._run_concurrent_with_worker_progress(
                        items,
                        process_func,
                        results,
                        errors,
                        progress,
                        overall_task,
                        item_description,
                        collect_errors,
                        on_error,
                        on_success,
                    )
                else:
                    compact_progress = self._should_use_compact_progress(len(items))
                    if compact_progress:
                        for idx, item in enumerate(items):
                            await self._process_item_with_compact_progress(
                                idx,
                                item,
                                process_func,
                                results,
                                errors,
                                progress,
                                overall_task,
                                item_description,
                                collect_errors,
                                on_error,
                                on_success,
                            )
                    else:
                        # Create individual task tracking
                        item_tasks: dict[int, TaskID] = {}
                        for idx, item in enumerate(items):
                            raw_desc = (
                                item_description(item)
                                if item_description
                                else f"Item {idx + 1}"
                            )
                            desc = self._format_description(raw_desc)
                            task_id = progress.add_task(
                                f"[grey50]Pending: {desc}[/grey50]", total=1
                            )
                            item_tasks[idx] = task_id

                        # Sequential execution with progress
                        for idx, item in enumerate(items):
                            await self._process_item_with_progress(
                                idx,
                                item,
                                process_func,
                                results,
                                errors,
                                progress,
                                overall_task,
                                item_tasks[idx],
                                item_description,
                                collect_errors,
                                on_error,
                                on_success,
                            )

        return results, errors

    async def _process_item_with_semaphore(
        self,
        idx: int,
        item: T,
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        results: list[Any],
        errors: list[tuple[T, Exception]],
        collect_errors: bool,
        on_error: Callable[[T, Exception], None] | None,
        on_success: Callable[[T, Any], None] | None,
    ):
        """Process item with semaphore for concurrency control."""
        async with self.semaphore:
            await self._process_item(
                idx,
                item,
                process_func,
                results,
                errors,
                collect_errors,
                on_error,
                on_success,
            )

    async def _process_item(
        self,
        idx: int,
        item: T,
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        results: list[Any],
        errors: list[tuple[T, Exception]],
        collect_errors: bool,
        on_error: Callable[[T, Exception], None] | None,
        on_success: Callable[[T, Any], None] | None,
    ):
        """Process a single item."""
        try:
            result = await process_func(item)
            results[idx] = result
            if on_success:
                on_success(item, result)
        except Exception as e:
            logger.warning(f"Error processing item {item}: {e}")
            errors.append((item, e))
            if on_error:
                on_error(item, e)
            if not collect_errors:
                raise

    async def _process_item_with_progress(
        self,
        idx: int,
        item: T,
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        results: list[Any],
        errors: list[tuple[T, Exception]],
        progress: Progress,
        overall_task: TaskID,
        item_task: TaskID,
        item_description: Callable[[T], str] | None,
        collect_errors: bool,
        on_error: Callable[[T, Exception], None] | None,
        on_success: Callable[[T, Any], None] | None,
    ):
        """Process item with progress tracking."""
        raw_desc = item_description(item) if item_description else f"Item {idx + 1}"
        desc = self._format_description(raw_desc)

        if self.mode == ExecutionMode.CONCURRENT and self.semaphore:
            async with self.semaphore:
                await self._process_with_progress_update(
                    idx,
                    item,
                    process_func,
                    results,
                    errors,
                    progress,
                    overall_task,
                    item_task,
                    desc,
                    collect_errors,
                    on_error,
                    on_success,
                )
        else:
            await self._process_with_progress_update(
                idx,
                item,
                process_func,
                results,
                errors,
                progress,
                overall_task,
                item_task,
                desc,
                collect_errors,
                on_error,
                on_success,
            )

    async def _process_with_progress_update(
        self,
        idx: int,
        item: T,
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        results: list[Any],
        errors: list[tuple[T, Exception]],
        progress: Progress,
        overall_task: TaskID,
        item_task: TaskID,
        desc: str,
        collect_errors: bool,
        on_error: Callable[[T, Exception], None] | None,
        on_success: Callable[[T, Any], None] | None,
    ):
        """Process with progress bar updates."""
        progress.update(
            item_task, description=f"[cyan]Processing: {desc}...", visible=True
        )

        try:
            result = await process_func(item)
            results[idx] = result
            progress.update(
                item_task,
                description=f"[green]✓ Completed: {desc}[/green]",
                completed=1,
            )
            if on_success:
                on_success(item, result)
        except Exception as e:
            logger.warning(f"Error processing {desc}: {e}")
            errors.append((item, e))
            progress.update(
                item_task, description=f"[red]✗ Failed: {desc}[/red]", completed=1
            )
            if on_error:
                on_error(item, e)
            if not collect_errors:
                progress.advance(overall_task, 1)
                raise

        progress.advance(overall_task, 1)

    async def _run_concurrent_with_worker_progress(
        self,
        items: list[T],
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        results: list[Any],
        errors: list[tuple[T, Exception]],
        progress: Progress,
        overall_task: TaskID,
        item_description: Callable[[T], str] | None,
        collect_errors: bool,
        on_error: Callable[[T, Exception], None] | None,
        on_success: Callable[[T, Any], None] | None,
    ) -> None:
        worker_count = max(self.concurrency, 1)
        queue: asyncio.Queue[tuple[int, T] | None] = asyncio.Queue()

        for idx, item in enumerate(items):
            queue.put_nowait((idx, item))
        for _ in range(worker_count):
            queue.put_nowait(None)

        worker_tasks = [
            progress.add_task(f"[grey50]Worker {i + 1}: idle[/grey50]", total=1)
            for i in range(worker_count)
        ]

        async def worker(worker_idx: int) -> None:
            task_id = worker_tasks[worker_idx]
            while True:
                payload = await queue.get()
                if payload is None:
                    progress.update(
                        task_id,
                        description=f"[grey50]Worker {worker_idx + 1}: idle[/grey50]",
                        completed=0,
                    )
                    queue.task_done()
                    break

                idx, item = payload
                raw_desc = (
                    item_description(item) if item_description else f"Item {idx + 1}"
                )
                desc = self._format_description(
                    raw_desc, prefix=f"Worker {worker_idx + 1}: "
                )
                progress.update(
                    task_id,
                    description=f"[cyan]{desc}[/cyan]",
                    completed=1,
                )

                try:
                    result = await process_func(item)
                    results[idx] = result
                    progress.update(
                        task_id,
                        description=f"[green]✓ {desc}[/green]",
                        completed=1,
                    )
                    if on_success:
                        on_success(item, result)
                except Exception as e:
                    logger.warning(f"Error processing {desc}: {e}")
                    errors.append((item, e))
                    progress.update(
                        task_id,
                        description=f"[red]✗ {desc}[/red]",
                        completed=1,
                    )
                    if on_error:
                        on_error(item, e)
                    if not collect_errors:
                        queue.task_done()
                        raise

                progress.advance(overall_task, 1)
                queue.task_done()

        await asyncio.gather(*(worker(i) for i in range(worker_count)))

    def _create_progress(self) -> Progress:
        columns = [
            SpinnerColumn(),
            TextColumn(
                "[progress.description]{task.description}",
                justify="left",
                table_column=Column(ratio=1, overflow="ellipsis", no_wrap=True),
            ),
            BarColumn(
                bar_width=self._bar_width,
                table_column=Column(justify="right"),
            ),
            TextColumn("{task.percentage:>3.0f}%", justify="right"),
            TimeElapsedColumn(table_column=Column(justify="right")),
        ]
        return Progress(*columns, console=self.console, expand=True)

    def _format_description(self, text: str, prefix: str | None = None) -> str:
        display = f"{prefix or ''}{text}"
        max_len = self._get_max_description_width()
        return self._truncate_middle(display, max_len)

    def _get_max_description_width(self) -> int:
        try:
            width = self.console.size.width
        except Exception:
            width = 0

        if width <= 0:
            return 60

        reserved = self._bar_width + 16
        max_len = width - reserved
        return max(max_len, self._min_desc_width)

    @staticmethod
    def _truncate_middle(text: str, max_len: int) -> str:
        if max_len <= 0 or len(text) <= max_len:
            return text
        if max_len <= 3:
            return text[:max_len]
        head_len = (max_len - 3) // 2
        tail_len = max_len - 3 - head_len
        return f"{text[:head_len]}...{text[-tail_len:]}"

    def _should_use_compact_progress(self, item_count: int) -> bool:
        try:
            height = self.console.size.height
        except Exception:
            return False

        if height <= 0:
            return False

        max_visible_tasks = max(height - 5, 5)
        return item_count > max_visible_tasks

    async def _process_item_with_compact_progress(
        self,
        idx: int,
        item: T,
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        results: list[Any],
        errors: list[tuple[T, Exception]],
        progress: Progress,
        overall_task: TaskID,
        item_description: Callable[[T], str] | None,
        collect_errors: bool,
        on_error: Callable[[T, Exception], None] | None,
        on_success: Callable[[T, Any], None] | None,
    ):
        """Process item with compact progress tracking."""
        raw_desc = item_description(item) if item_description else f"Item {idx + 1}"
        desc = self._format_description(raw_desc)

        if self.mode == ExecutionMode.CONCURRENT and self.semaphore:
            async with self.semaphore:
                await self._process_with_compact_progress_update(
                    idx,
                    item,
                    process_func,
                    results,
                    errors,
                    progress,
                    overall_task,
                    desc,
                    collect_errors,
                    on_error,
                    on_success,
                )
        else:
            await self._process_with_compact_progress_update(
                idx,
                item,
                process_func,
                results,
                errors,
                progress,
                overall_task,
                desc,
                collect_errors,
                on_error,
                on_success,
            )

    async def _process_with_compact_progress_update(
        self,
        idx: int,
        item: T,
        process_func: Callable[[T], Coroutine[Any, Any, Any]],
        results: list[Any],
        errors: list[tuple[T, Exception]],
        progress: Progress,
        overall_task: TaskID,
        desc: str,
        collect_errors: bool,
        on_error: Callable[[T, Exception], None] | None,
        on_success: Callable[[T, Any], None] | None,
    ):
        progress.update(overall_task, description=f"[cyan]Processing: {desc}[/cyan]")

        try:
            result = await process_func(item)
            results[idx] = result
            progress.update(
                overall_task,
                advance=1,
                description=f"[green]✓ Completed: {desc}[/green]",
            )
            if on_success:
                on_success(item, result)
        except Exception as e:
            logger.warning(f"Error processing {desc}: {e}")
            errors.append((item, e))
            progress.update(
                overall_task,
                advance=1,
                description=f"[red]✗ Failed: {desc}[/red]",
            )
            if on_error:
                on_error(item, e)
            if not collect_errors:
                raise

    async def run_single(
        self, coro: Coroutine[Any, Any, T], timeout: float | None = None
    ) -> T:
        """
        Run a single async operation with optional timeout.

        Args:
            coro: The coroutine to run
            timeout: Optional timeout in seconds

        Returns:
            The result of the coroutine

        Raises:
            asyncio.TimeoutError: If timeout is exceeded
        """
        if timeout:
            return await asyncio.wait_for(coro, timeout=timeout)
        return await coro

    async def gather_with_errors(
        self, *coros: Coroutine[Any, Any, Any], return_exceptions: bool = True
    ) -> list[Any | Exception]:
        """
        Gather multiple coroutines, optionally returning exceptions instead of raising.

        Args:
            *coros: Coroutines to run concurrently
            return_exceptions: If True, exceptions are returned in results

        Returns:
            List of results (or exceptions if return_exceptions=True)
        """
        return await asyncio.gather(*coros, return_exceptions=return_exceptions)


# High-level convenience functions


async def run_concurrent(
    items: list[T],
    process_func: Callable[[T], Coroutine[Any, Any, Any]],
    concurrency: int = 4,
    show_progress: bool = True,
    task_description: str = "Processing items...",
) -> tuple[list[Any], list[tuple[T, Exception]]]:
    """
    Convenience function to run items concurrently with default settings.

    Args:
        items: Items to process
        process_func: Async function to process each item
        concurrency: Maximum concurrent operations
        show_progress: Whether to show progress bar
        task_description: Description for progress bar

    Returns:
        Tuple of (results, errors)
    """
    executor = AsyncExecutor(concurrency=concurrency, mode=ExecutionMode.CONCURRENT)
    return await executor.run_batch(
        items=items,
        process_func=process_func,
        task_description=task_description,
        show_progress=show_progress,
    )


async def run_sequential(
    items: list[T],
    process_func: Callable[[T], Coroutine[Any, Any, Any]],
    show_progress: bool = True,
    task_description: str = "Processing items...",
) -> tuple[list[Any], list[tuple[T, Exception]]]:
    """
    Convenience function to run items sequentially.

    Args:
        items: Items to process
        process_func: Async function to process each item
        show_progress: Whether to show progress bar
        task_description: Description for progress bar

    Returns:
        Tuple of (results, errors)
    """
    executor = AsyncExecutor(mode=ExecutionMode.SEQUENTIAL)
    return await executor.run_batch(
        items=items,
        process_func=process_func,
        task_description=task_description,
        show_progress=show_progress,
    )


# Example usage for subprocess operations (common pattern in mgit)
class SubprocessExecutor(AsyncExecutor):
    """
    Specialized executor for running subprocess commands with progress tracking.

    Example:
        executor = SubprocessExecutor(concurrency=4)
        commands = [
            ("git", ["git", "pull"], Path("/repo1")),
            ("git", ["git", "pull"], Path("/repo2")),
        ]
        results, errors = await executor.run_commands(commands)
    """

    async def run_commands(
        self,
        commands: list[tuple[str, list[str], Path]],
        task_description: str = "Running commands...",
        show_progress: bool = True,
    ) -> tuple[
        list[tuple[int, bytes, bytes]],
        list[tuple[tuple[str, list[str], Path], Exception]],
    ]:
        """
        Run multiple subprocess commands with progress tracking.

        Args:
            commands: List of (name, cmd_args, working_dir) tuples
            task_description: Overall progress description
            show_progress: Whether to show progress

        Returns:
            Tuple of (results, errors) where results contain (returncode, stdout, stderr)
        """

        async def run_command(
            cmd_info: tuple[str, list[str], Path],
        ) -> tuple[int, bytes, bytes]:
            name, cmd_args, cwd = cmd_info
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode or 1, cmd_args, output=stdout, stderr=stderr
                )

            return process.returncode or 0, stdout, stderr

        return await self.run_batch(
            items=commands,
            process_func=run_command,
            task_description=task_description,
            item_description=lambda cmd: f"{cmd[0]}: {' '.join(cmd[1][:2])}...",
            show_progress=show_progress,
        )
