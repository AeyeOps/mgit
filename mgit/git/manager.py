"""Git operations manager for mgit CLI tool."""

import asyncio
import contextlib
import logging
import os
import re
import signal
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mgit.git.progress import GitProgress, GitProgressParser, ProgressCallback

logger = logging.getLogger(__name__)

# Pattern to strip credentials from URLs in log messages
_CRED_URL_RE = re.compile(r"(https?://)([^@]+)@")
_EXTRA_HEADER_RE = re.compile(r"(http(?:\..+)?\.extraheader=)(.*)", re.I | re.S)


def sanitize_url(text: str) -> str:
    """Remove credentials from URLs in text."""
    return _CRED_URL_RE.sub(r"\1***@", text)


def _sanitize_cmd_for_log(cmd: list[str]) -> str:
    """Mask URL credentials and configured HTTP headers in command arguments."""
    return " ".join(
        _EXTRA_HEADER_RE.sub(r"\1***", sanitize_url(token)) for token in cmd
    )


def _sanitize_output_for_log(text: str, cmd: list[str]) -> str:
    """Mask URL credentials and headers echoed by a failed Git command."""
    safe_text = sanitize_url(text)
    for argument in cmd:
        match = _EXTRA_HEADER_RE.search(argument)
        if match and match[2]:
            safe_text = safe_text.replace(match[2], "***")
    return safe_text


class _ProgressCallbackError(Exception):
    """Carry callback failures through reader tasks without losing ownership."""

    def __init__(self, error: BaseException):
        self.error = error


class GitManager:
    GIT_EXECUTABLE = "git"

    # Fix type hint for dir_name
    async def git_clone(
        self,
        repo_url: str,
        output_dir: Path,
        dir_name: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        """
        Use 'git clone' for the given repo_url, in output_dir.
        Optionally specify a directory name to clone into.
        Raises typer.Exit if the command fails.
        """
        # Format the message for better display in the console
        # Strip credentials and truncate long URLs to prevent log line truncation
        display_url = _CRED_URL_RE.sub(r"\1", repo_url)
        if len(display_url) > 60:
            parsed = urlparse(display_url)
            path_parts = parsed.path.split("/")
            if len(path_parts) > 2:
                short_path = "/".join(path_parts[-3:])
                display_url = f"{parsed.scheme}://{parsed.netloc}/.../{short_path}"

        if dir_name:
            display_dir = dir_name
            if len(display_dir) > 40:
                display_dir = display_dir[:37] + "..."

            logger.info(f"Cloning: [bold blue]{display_dir}[/bold blue]")
            cmd = [self.GIT_EXECUTABLE, "clone", repo_url, dir_name]
        else:
            logger.info(f"Cloning repository: {display_url} into {output_dir}")
            cmd = [self.GIT_EXECUTABLE, "clone", repo_url]

        if on_progress is not None:
            cmd.insert(2, "--progress")
            on_progress(GitProgress("Cloning"))
        await self._run_subprocess(
            cmd,
            cwd=output_dir,
            log_level=logging.DEBUG if on_progress is not None else logging.ERROR,
            on_progress=on_progress,
        )

    async def git_pull(
        self, repo_dir: Path, on_progress: ProgressCallback | None = None
    ) -> None:
        """
        Use 'git pull' for the existing repo in repo_dir.
        """
        # Extract repo name from path for nicer logging
        repo_name = repo_dir.name

        # Format the output with consistent width to prevent truncation
        # Limit the repo name to 40 characters if it's longer
        display_name = repo_name
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        logger.info(f"Pulling: [bold green]{display_name}[/bold green]")
        cmd = [self.GIT_EXECUTABLE, "pull"]
        if on_progress is not None:
            cmd.append("--progress")
            on_progress(GitProgress("Pulling"))
        await self._run_subprocess(
            cmd,
            cwd=repo_dir,
            log_level=logging.DEBUG if on_progress is not None else logging.ERROR,
            on_progress=on_progress,
        )

    async def git_fetch(
        self, repo_dir: Path, on_progress: ProgressCallback | None = None
    ) -> None:
        """Run 'git fetch' for the existing repo in repo_dir.

        Unlike pull, fetch never touches the working tree, so it succeeds even
        when the checkout is in a state git cannot cleanly update (e.g. a
        case-collision artifact on a case-insensitive filesystem).
        """
        cmd = [self.GIT_EXECUTABLE, "fetch"]
        if on_progress is not None:
            cmd.append("--progress")
            on_progress(GitProgress("Fetching"))
        await self._run_subprocess(
            cmd,
            cwd=repo_dir,
            log_level=logging.DEBUG if on_progress is not None else logging.ERROR,
            on_progress=on_progress,
        )

    async def get_upstream_ref(self, repo_dir: Path) -> str | None:
        """Return the upstream tracking ref of the current branch.

        Returns a name like ``origin/main``, or None if the current branch has
        no upstream configured (or HEAD is detached).
        """
        try:
            result = await self._run_subprocess(
                [
                    self.GIT_EXECUTABLE,
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{u}",
                ],
                cwd=repo_dir,
                capture_output=True,
                log_level=logging.DEBUG,
            )
            ref = result.stdout.strip()
            return ref or None
        except subprocess.CalledProcessError:
            logger.debug(f"No upstream ref for current branch in {repo_dir}")
            return None
        except Exception as e:
            logger.debug(f"Get upstream ref failed in {repo_dir}: {e}")
            return None

    async def git_reset_hard(self, repo_dir: Path, ref: str):
        """Run 'git reset --hard <ref>' in repo_dir.

        Discards all working-tree and index state, moving the branch to *ref*.
        Callers are responsible for confirming this is safe (no real local work
        to lose).
        """
        cmd = [self.GIT_EXECUTABLE, "reset", "--hard", ref]
        await self._run_subprocess(cmd, cwd=repo_dir)

    async def get_current_branch(self, repo_dir: Path) -> str | None:
        """
        Get the current branch name for the repository.

        Args:
            repo_dir: Path to the repository

        Returns:
            Current branch name or None if detached HEAD or error
        """
        try:
            cmd = [self.GIT_EXECUTABLE, "branch", "--show-current"]
            result = await self._run_subprocess(cmd, cwd=repo_dir, capture_output=True)

            branch_name = result.stdout.strip()
            return branch_name if branch_name else None

        except subprocess.CalledProcessError:
            logger.debug(f"Could not get current branch for {repo_dir}")
            return None
        except Exception as e:
            logger.debug(f"Get current branch failed in {repo_dir}: {e}")
            return None

    async def get_recent_commits(
        self, repo_dir: Path, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get recent commit information from the repository.

        Args:
            repo_dir: Path to repository
            limit: Maximum number of commits to return

        Returns:
            List of commit information dictionaries
        """
        try:
            # Use git log with custom format for structured output
            format_str = "--format=%H|%an|%ae|%ai|%s"
            cmd = [self.GIT_EXECUTABLE, "log", f"-{limit}", format_str, "--no-merges"]

            result = await self._run_subprocess(cmd, cwd=repo_dir, capture_output=True)

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 4)
                    if len(parts) == 5:
                        commits.append(
                            {
                                "hash": parts[0],
                                "author_name": parts[1],
                                "author_email": parts[2],
                                "date": parts[3],
                                "message": parts[4],
                            }
                        )

            return commits

        except subprocess.CalledProcessError as e:
            logger.debug(f"Git log failed in {repo_dir}: {e}")
            return []
        except Exception as e:
            logger.debug(f"Get recent commits failed in {repo_dir}: {e}")
            return []

    async def diff_files(self, repo_dir: Path) -> dict[str, Any]:
        """
        Get diff information for a repository including git status.

        Args:
            repo_dir: Path to the repository

        Returns:
            Dictionary with diff information including:
            - has_changes: bool indicating if there are uncommitted changes
            - status_output: raw git status --porcelain output
            - diff_output: raw git diff output (optional)
        """
        try:
            # Check for uncommitted changes using git status
            status_cmd = [self.GIT_EXECUTABLE, "status", "--porcelain"]
            status_result = await self._run_subprocess(
                status_cmd, cwd=repo_dir, capture_output=True
            )

            status_output = status_result.stdout.strip()
            has_changes = len(status_output) > 0

            return {
                "has_changes": has_changes,
                "status_output": status_output,
            }

        except subprocess.CalledProcessError as e:
            logger.debug(f"Git status failed in {repo_dir}: {e}")
            raise
        except Exception as e:
            logger.debug(f"Diff files operation failed in {repo_dir}: {e}")
            raise

    TRANSIENT_PATTERNS = [
        "Connection reset",
        "Connection refused",
        "timed out",
        "SSL",
        "Could not resolve host",
        "429",
        "rate limit",
    ]
    PERMANENT_PATTERNS = [
        "not found",
        "Permission denied",
        "couldn't find remote ref",
    ]

    async def is_repo_empty(self, repo_dir: Path) -> bool:
        """Return True if the repo has no commits (empty repo)."""
        try:
            await self._run_subprocess(
                [self.GIT_EXECUTABLE, "rev-parse", "HEAD"],
                cwd=repo_dir,
                capture_output=True,
                log_level=logging.DEBUG,
            )
            return False
        except subprocess.CalledProcessError:
            return True
        except Exception:
            return True

    async def _exec_once(
        self,
        cmd: list,
        cwd: Path,
        env: dict[str, str],
        timeout: float,
        on_progress: ProgressCallback | None = None,
    ) -> subprocess.CompletedProcess:
        """Run *cmd* once as a native async subprocess, mirroring subprocess.run.

        Raises subprocess.TimeoutExpired when it outlives *timeout* and
        subprocess.CalledProcessError on a non-zero exit (check=True semantics),
        so _run_subprocess handles the same exceptions the blocking call raised.
        stdout/stderr are captured and returned decoded.
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            # Keep Git and its SSH/credential helpers in a group that can be
            # terminated without signalling the CLI or concurrent Git jobs.
            start_new_session=os.name == "posix",
        )
        communication = asyncio.create_task(
            self._communicate_progress(proc, on_progress)
            if on_progress is not None
            else proc.communicate()
        )
        try:
            # wait() distinguishes our deadline from a TimeoutError raised by a
            # callback. We own and cancel the communication task explicitly.
            done, _ = await asyncio.wait({communication}, timeout=timeout)
            if not done:
                raise subprocess.TimeoutExpired(cmd, timeout)
            stdout_b, stderr_b = communication.result()
        except BaseException:
            communication.cancel()
            await asyncio.gather(communication, return_exceptions=True)
            await self._terminate_process(
                proc,
                log_level=logging.DEBUG if on_progress is not None else logging.WARNING,
            )
            raise

        # Git paths and hook diagnostics may contain bytes outside UTF-8. A
        # successful command must not become a failure while rendering them.
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        returncode = proc.returncode or 0
        if returncode != 0:
            raise subprocess.CalledProcessError(
                returncode, cmd, output=stdout, stderr=stderr
            )
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    @staticmethod
    async def _communicate_progress(
        proc: asyncio.subprocess.Process, on_progress: ProgressCallback
    ) -> tuple[bytes, bytes]:
        """Drain both pipes while forwarding only recognized stderr progress."""
        stdout_reader, stderr_reader = proc.stdout, proc.stderr
        assert stdout_reader is not None
        assert stderr_reader is not None

        def emit(events: list[GitProgress]) -> None:
            for event in events:
                try:
                    on_progress(event)
                except BaseException as error:
                    raise _ProgressCallbackError(error) from error

        async def read_stderr() -> bytes:
            parser = GitProgressParser()
            chunks = []
            while chunk := await stderr_reader.read(65536):
                chunks.append(chunk)
                emit(parser.feed(chunk))
            emit(parser.finish())
            return b"".join(chunks)

        readers = [
            asyncio.create_task(stdout_reader.read()),
            asyncio.create_task(read_stderr()),
        ]
        try:
            stdout, stderr = await asyncio.gather(*readers)
            await proc.wait()
            return stdout, stderr
        finally:
            # A callback error leaves the other reader running unless it is
            # cancelled. Finish both readers before cleanup calls communicate.
            for reader in readers:
                reader.cancel()
            await asyncio.gather(*readers, return_exceptions=True)

    async def _terminate_process(
        self, proc: asyncio.subprocess.Process, log_level: int = logging.WARNING
    ) -> None:
        """Terminate Git and its helpers, allowing at most one second to drain."""

        async def terminate_and_drain():
            if os.name == "posix":
                # The parent may have exited while a helper still holds a pipe.
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
            elif proc.returncode is None:
                # Windows kill() terminates only the parent; taskkill /T also
                # terminates its descendants. It shares the cleanup deadline.
                killer = await asyncio.create_subprocess_exec(
                    "taskkill",
                    "/F",
                    "/T",
                    "/PID",
                    str(proc.pid),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                try:
                    await killer.wait()
                    if killer.returncode:
                        logger.log(
                            log_level,
                            "Git process-tree cleanup failed with exit code %s",
                            killer.returncode,
                        )
                finally:
                    killer._transport.close()  # ty: ignore[unresolved-attribute]
                if proc.returncode is None:
                    with contextlib.suppress(ProcessLookupError):
                        proc.kill()
            await proc.communicate()

        try:
            await asyncio.wait_for(terminate_and_drain(), timeout=1.0)
        except asyncio.TimeoutError:  # noqa: UP041
            logger.log(
                log_level, "Git subprocess cleanup exceeded 1s; closing output pipes"
            )
        finally:
            # Process has no public close API. Close the owned transport so an
            # escaped helper cannot retain our pipes after the cleanup deadline.
            proc._transport.close()  # ty: ignore[unresolved-attribute]

    async def _run_subprocess(
        self,
        cmd: list,
        cwd: Path,
        capture_output: bool = False,
        log_level: int = logging.ERROR,
        timeout: float = 300,
        max_retries: int = 3,
        initial_delay: float = 2.0,
        backoff: float = 2.0,
        on_progress: ProgressCallback | None = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a subprocess command with proper error handling.

        Always captures stdout/stderr to prevent git from leaking credentials
        directly to the terminal.  When *capture_output* is False the captured
        streams are still logged at DEBUG level after sanitisation.

        Args:
            cmd: Command and arguments to run
            cwd: Working directory for the command
            capture_output: Whether to return captured stdout/stderr to caller
            log_level: Log level for CalledProcessError messages (default ERROR)
            timeout: Command timeout in seconds (default 300)
            max_retries: Max retry attempts for transient failures (default 3)
            initial_delay: Initial retry delay in seconds (default 2.0)
            backoff: Backoff multiplier for retry delay (default 2.0)
            on_progress: Optional callback for safe, measured Git activity

        Returns:
            CompletedProcess result
        """
        safe_cmd = _sanitize_cmd_for_log(cmd)

        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        if on_progress is not None:
            env["LC_ALL"] = "C"

        for attempt in range(max_retries + 1):
            try:
                # Git subprocesses must neither block the event loop nor occupy
                # an executor thread; otherwise concurrent clones serialize
                # below --concurrency and starve the Azure SDK's to_thread
                # calls (ADR-003).
                result = await self._exec_once(cmd, cwd, env, timeout, on_progress)
                if not capture_output and result.stdout:
                    logger.debug(
                        "stdout: %s",
                        _sanitize_output_for_log(result.stdout.rstrip(), cmd),
                    )
                return result

            except _ProgressCallbackError as error:
                # Callback failures must retain their type without being
                # mistaken for command failures eligible for timeout/retry.
                raise error.error from None

            except subprocess.TimeoutExpired as e:
                logger.log(
                    log_level if on_progress is not None else logging.ERROR,
                    f"Command '{safe_cmd}' timed out after {timeout}s in {cwd}",
                )
                raise subprocess.CalledProcessError(
                    124,
                    cmd,
                    output="",
                    stderr=f"Command timed out after {timeout}s",
                ) from e

            except subprocess.CalledProcessError as e:
                safe_stderr = (
                    _sanitize_output_for_log(e.stderr.rstrip(), cmd) if e.stderr else ""
                )
                stderr_lower = (e.stderr or "").lower()

                if (
                    attempt < max_retries
                    and any(p.lower() in stderr_lower for p in self.TRANSIENT_PATTERNS)
                    and not any(
                        p.lower() in stderr_lower for p in self.PERMANENT_PATTERNS
                    )
                ):
                    delay = initial_delay * (backoff**attempt)
                    logger.log(
                        log_level if on_progress is not None else logging.WARNING,
                        f"Transient failure (attempt {attempt + 1}/{max_retries + 1}) "
                        f"for '{safe_cmd}', retrying in {delay}s: {safe_stderr}",
                    )
                    if on_progress is not None:
                        on_progress(GitProgress("Retrying"))
                    await asyncio.sleep(delay)
                    continue

                logger.log(
                    log_level,
                    f"Command '{safe_cmd}' failed in {cwd}: exit code {e.returncode}",
                )
                if safe_stderr:
                    logger.log(log_level, f"  {safe_stderr}")
                if e.stdout:
                    logger.debug(
                        "stdout: %s", _sanitize_output_for_log(e.stdout.rstrip(), cmd)
                    )
                raise

            except Exception as e:
                logger.log(
                    log_level if on_progress is not None else logging.ERROR,
                    "Unexpected error running '%s' in %s: %s",
                    safe_cmd,
                    cwd,
                    _sanitize_output_for_log(str(e), cmd),
                )
                raise

        raise RuntimeError(f"Exhausted retries for '{safe_cmd}'")
