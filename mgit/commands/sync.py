"""
Sync command implementation.

Provides a unified interface for repository synchronization that combines
the functionality of clone-all and pull-all into a single, intuitive command.
"""

import asyncio
import logging
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm
from rich.table import Table

from mgit.commands.bulk_operations import (
    BulkOperationProcessor,
    OperationType,
    UpdateMode,
    check_force_mode_confirmation,
)
from mgit.config.yaml_manager import (
    detect_provider_type,
    get_global_setting,
    get_provider_configs,
    list_provider_names,
)
from mgit.git import GitManager
from mgit.git.utils import get_git_remote_url, resolve_local_repo_path
from mgit.providers import detect_provider_by_url
from mgit.providers.base import Repository
from mgit.providers.exceptions import RepositoryNotFoundError
from mgit.providers.manager import ProviderManager
from mgit.utils.async_executor import AsyncExecutor
from mgit.utils.directory_scanner import find_repositories_in_directory
from mgit.utils.multi_provider_resolver import MultiProviderResolver
from mgit.utils.pattern_matching import analyze_pattern

logger = logging.getLogger(__name__)
console = Console()

LOCAL_ACTION_PULL = "pull"
LOCAL_ACTION_PULLED = "pulled"
LOCAL_ACTION_SKIP_DIRTY = "skipped_dirty"
LOCAL_ACTION_SKIP_NO_REMOTE = "skipped_no_remote"
LOCAL_ACTION_FAILED = "failed"


@dataclass
class LocalRepoState:
    path: Path
    name: str
    remote_url: str | None
    provider: str
    is_dirty: bool
    error: str | None = None


@dataclass
class LocalRepoResult:
    state: LocalRepoState
    action: str
    error: str | None = None


@dataclass(frozen=True)
class ProviderAuthConfig:
    name: str
    provider_type: str
    base_url: str
    token: str | None
    user: str | None
    host: str | None


def _detect_local_provider(remote_url: str | None) -> str:
    if not remote_url:
        return "unknown"
    try:
        return detect_provider_by_url(remote_url)
    except Exception:
        return "unknown"


async def _run_git_command(repo_path: Path, args: list[str]) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(repo_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode or 0,
        stdout.decode("utf-8", errors="ignore"),
        stderr.decode("utf-8", errors="ignore"),
    )


def _normalize_http_url(url: str) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    parsed = urlparse(url)
    if not parsed.hostname:
        return None
    scheme = (parsed.scheme or "https").lower()
    host = parsed.hostname.lower()
    if parsed.port:
        host = f"{host}:{parsed.port}"
    path = parsed.path or ""
    normalized = f"{scheme}://{host}{path}".rstrip("/")
    return normalized


def _load_provider_auth_configs() -> list[ProviderAuthConfig]:
    configs: list[ProviderAuthConfig] = []
    for name, config in get_provider_configs().items():
        base_url = config.get("url")
        if not base_url:
            continue
        try:
            provider_type = detect_provider_type(name)
        except Exception:
            continue
        token = config.get("token") or config.get("pat")
        user = config.get("user") or config.get("username")
        normalized = _normalize_http_url(str(base_url))
        if not normalized:
            continue
        host = urlparse(normalized).hostname
        configs.append(
            ProviderAuthConfig(
                name=name,
                provider_type=provider_type,
                base_url=normalized,
                token=token,
                user=user,
                host=host,
            )
        )
    return configs


def _match_provider_config(
    remote_url: str, provider_type: str, configs: list[ProviderAuthConfig]
) -> ProviderAuthConfig | None:
    normalized_remote = _normalize_http_url(remote_url)
    if not normalized_remote:
        return None

    candidates = [config for config in configs if config.provider_type == provider_type]
    if not candidates:
        return None

    remote_lower = normalized_remote.lower()
    best_match = None
    for config in candidates:
        if remote_lower.startswith(config.base_url.lower()):
            if best_match is None or len(config.base_url) > len(best_match.base_url):
                best_match = config

    if best_match:
        return best_match

    remote_host = urlparse(normalized_remote).hostname
    host_matches = [config for config in candidates if config.host == remote_host]
    if host_matches:
        return sorted(host_matches, key=lambda cfg: len(cfg.base_url), reverse=True)[0]

    token_configs = [config for config in candidates if config.token]
    if len(token_configs) == 1:
        logger.debug(
            "Local sync using sole %s provider config '%s' for %s",
            provider_type,
            token_configs[0].name,
            normalized_remote,
        )
        return token_configs[0]

    return None


def _build_basic_auth_header(user: str, token: str) -> str:
    payload = f"{user}:{token}".encode("utf-8")
    encoded = b64encode(payload).decode("ascii")
    return f"Authorization: Basic {encoded}"


def _build_auth_header(config: ProviderAuthConfig) -> str | None:
    token = config.token
    if not token:
        return None

    if config.provider_type == "azuredevops":
        return _build_basic_auth_header("", token)
    if config.provider_type == "github":
        return _build_basic_auth_header(config.user or "x-access-token", token)
    if config.provider_type == "bitbucket":
        if not config.user:
            return None
        return _build_basic_auth_header(config.user, token)

    return None


def _build_git_pull_args(
    state: LocalRepoState, configs: list[ProviderAuthConfig]
) -> list[str]:
    if not state.remote_url or state.provider == "unknown":
        return ["pull"]

    config = _match_provider_config(state.remote_url, state.provider, configs)
    if not config:
        return ["pull"]

    header = _build_auth_header(config)
    if not header:
        return ["pull"]

    logger.debug(
        "Local sync using %s credentials from '%s' for %s",
        config.provider_type,
        config.name,
        state.path,
    )
    return ["-c", f"http.extraheader={header}", "pull"]


async def _inspect_local_repository(repo_path: Path) -> LocalRepoState:
    remote_url = get_git_remote_url(repo_path)
    provider = _detect_local_provider(remote_url)

    try:
        returncode, stdout, stderr = await _run_git_command(
            repo_path, ["status", "--porcelain"]
        )
        if returncode != 0:
            error_msg = stderr.strip() or stdout.strip() or "git status failed"
            return LocalRepoState(
                path=repo_path,
                name=repo_path.name,
                remote_url=remote_url,
                provider=provider,
                is_dirty=True,
                error=error_msg,
            )
        return LocalRepoState(
            path=repo_path,
            name=repo_path.name,
            remote_url=remote_url,
            provider=provider,
            is_dirty=bool(stdout.strip()),
        )
    except Exception as exc:
        return LocalRepoState(
            path=repo_path,
            name=repo_path.name,
            remote_url=remote_url,
            provider=provider,
            is_dirty=True,
            error=str(exc),
        )


def _determine_local_action(state: LocalRepoState, force: bool) -> str:
    if state.error:
        return LOCAL_ACTION_FAILED
    if not state.remote_url:
        return LOCAL_ACTION_SKIP_NO_REMOTE
    if state.is_dirty and not force:
        return LOCAL_ACTION_SKIP_DIRTY
    return LOCAL_ACTION_PULL


def _summarize_local_results(results: list[LocalRepoResult]) -> dict[str, int]:
    counts = {
        "total": len(results),
        "pulled": 0,
        "skipped_dirty": 0,
        "skipped_no_remote": 0,
        "failed": 0,
    }
    for result in results:
        if result.action in {LOCAL_ACTION_PULL, LOCAL_ACTION_PULLED}:
            counts["pulled"] += 1
        elif result.action == LOCAL_ACTION_SKIP_DIRTY:
            counts["skipped_dirty"] += 1
        elif result.action == LOCAL_ACTION_SKIP_NO_REMOTE:
            counts["skipped_no_remote"] += 1
        else:
            counts["failed"] += 1
    return counts


def _format_repo_display(root_path: Path, repo_path: Path) -> str:
    try:
        return str(repo_path.relative_to(root_path))
    except ValueError:
        return str(repo_path)


def _render_local_plan(
    root_path: Path, results: list[LocalRepoResult], force: bool
) -> None:
    table = Table(title="Local Sync Plan")
    table.add_column("Repository", style="cyan", overflow="fold")
    table.add_column("Provider", style="magenta")
    table.add_column("Action", style="green")
    table.add_column("Notes", style="dim")

    for result in results:
        state = result.state
        action_label = "Pull"
        notes = ""
        if result.action == LOCAL_ACTION_SKIP_DIRTY:
            action_label = "Skip"
            notes = "Dirty"
        elif result.action == LOCAL_ACTION_SKIP_NO_REMOTE:
            action_label = "Skip"
            notes = "No remote"
        elif result.action == LOCAL_ACTION_FAILED:
            action_label = "Error"
            notes = result.error or state.error or "Unknown error"
        elif force:
            notes = "Force clean"

        table.add_row(
            _format_repo_display(root_path, state.path),
            state.provider,
            action_label,
            notes,
        )

    console.print(table)


def _render_local_summary(results: list[LocalRepoResult], dry_run: bool) -> None:
    counts = _summarize_local_results(results)
    table = Table(title="Local Sync Summary")
    table.add_column("Result", style="bold")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Total", str(counts["total"]))
    table.add_row("Pull" if dry_run else "Pulled", str(counts["pulled"]))
    table.add_row("Skipped (dirty)", str(counts["skipped_dirty"]))
    table.add_row("Skipped (no remote)", str(counts["skipped_no_remote"]))
    table.add_row("Failed", str(counts["failed"]))

    console.print(table)


def _render_local_failures(results: list[LocalRepoResult], root_path: Path) -> None:
    failures = [result for result in results if result.action == LOCAL_ACTION_FAILED]
    if not failures:
        return

    table = Table(title="Local Sync Failures")
    table.add_column("Repository", style="red", overflow="fold")
    table.add_column("Error", style="yellow", overflow="fold")

    for result in failures:
        error_msg = result.error or result.state.error or "Unknown error"
        table.add_row(
            _format_repo_display(root_path, result.state.path),
            error_msg,
        )

    console.print(table)


async def resolve_repositories_for_sync(
    pattern: str,
    provider_manager,
    explicit_provider: str | None = None,
    explicit_url: str | None = None,
) -> tuple[list[Repository], bool]:
    """
    Resolve repositories for sync operation with clear logging.

    Returns:
        Tuple of (repositories, is_multi_provider_operation)
    """

    pattern_analysis = analyze_pattern(pattern, explicit_provider, explicit_url)

    # Validate pattern
    if pattern_analysis.validation_errors:
        for error in pattern_analysis.validation_errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=1)

    logger.debug(f"Resolving repositories for sync pattern: {pattern}")

    try:
        if pattern_analysis.is_multi_provider:
            # Multi-provider search
            available_providers = list_provider_names()
            console.print(
                f"[blue]Synchronizing across {len(available_providers)} providers:[/blue] {', '.join(available_providers)}"
            )

            if not available_providers:
                console.print(
                    "[red]Error:[/red] No providers configured. Run 'mgit login' to add providers."
                )
                raise typer.Exit(code=1)

            resolver = MultiProviderResolver()
            result = await resolver.resolve_repositories(
                project=pattern_analysis.normalized_pattern,
                provider_manager=None,
                config=None,
                url=None,
            )
            repositories = result.repositories

            # Log detailed results
            console.print(
                f"[green]Found {len(repositories)} repositories[/green] "
                f"from {len(result.successful_providers)} providers"
            )

            if result.failed_providers:
                console.print(
                    f"[yellow]Warning:[/yellow] Failed to query {len(result.failed_providers)} providers: "
                    f"{', '.join(result.failed_providers)}"
                )

            if result.duplicates_removed > 0:
                console.print(
                    f"[blue]Info:[/blue] Removed {result.duplicates_removed} duplicate repositories"
                )

            return repositories, True

        elif pattern_analysis.is_pattern:
            # Single provider pattern search
            provider_name = provider_manager.provider_name if provider_manager else None
            console.print(f"[blue]Synchronizing from provider:[/blue] {provider_name}")

            resolver = MultiProviderResolver()
            result = await resolver.resolve_repositories(
                project=pattern_analysis.normalized_pattern,
                provider_manager=provider_manager,
                config=provider_name,
                url=explicit_url,
            )
            repositories = result.repositories

            console.print(
                f"[green]Found {len(repositories)} repositories[/green] in provider '{provider_name}'"
            )

            return repositories, False

        else:
            # Non-pattern query: exact match (org/project/repo) when no wildcards
            segments = pattern.split("/")
            if len(segments) == 3:
                org_name, project_name, repo_name = segments
                provider = provider_manager.get_provider()
                repo_list: list[Repository] = []

                try:
                    repo = await provider.get_repository(
                        org_name, repo_name, project_name
                    )
                    if repo:
                        repo_list = [repo]
                except RepositoryNotFoundError:
                    repo_list = []
                except Exception as e:
                    logger.error(f"Error getting repository '{pattern}': {e}")
                    raise

                # Case-insensitive fallback if provider didn't return a direct match
                if not repo_list:
                    try:
                        async for repo in provider.list_repositories(
                            org_name, project_name
                        ):
                            if repo.name.lower() == repo_name.lower():
                                repo_list.append(repo)
                    except Exception as e:
                        logger.error(f"Error listing repositories for '{pattern}': {e}")
                        raise

                console.print(
                    f"[green]Found {len(repo_list)} repositories[/green] for exact match"
                )
                return repo_list, False

            # Fallback: list repositories based on provided pattern scope
            repositories = provider_manager.list_repositories(pattern)
            if hasattr(repositories, "__len__"):
                repo_list = list(repositories)
            else:
                repo_list = [repositories] if repositories else []

            console.print(
                f"[green]Found {len(repo_list)} repositories[/green] for exact match"
            )

            return repo_list, False

    except Exception as e:
        logger.error(f"Error resolving repositories: {e}")
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


async def analyze_repository_states(
    repositories: list[Repository],
    target_path: Path,
    flat_layout: bool = True,
    resolved_names: dict[str, str] | None = None,
):
    """Analyze current state of repositories in target path."""
    from dataclasses import dataclass

    @dataclass
    class RepoAnalysis:
        clean_repos: list[str]
        dirty_repos: list[str]
        missing_repos: list[str]
        non_git_dirs: list[str]

    clean_repos = []
    dirty_repos = []
    missing_repos = []
    non_git_dirs = []

    for repo in repositories:
        repo_path = resolve_local_repo_path(repo.clone_url, flat_layout, resolved_names)
        local_path = target_path / repo_path

        if not local_path.exists():
            missing_repos.append(repo.name)
        elif not (local_path / ".git").exists():
            non_git_dirs.append(repo.name)
        else:
            # Check if repo has uncommitted changes
            try:
                returncode, stdout, stderr = await _run_git_command(
                    local_path, ["status", "--porcelain"]
                )
                if returncode != 0 or stdout.strip():
                    dirty_repos.append(repo.name)
                else:
                    clean_repos.append(repo.name)
            except Exception:
                # If git status fails, consider it dirty for safety
                dirty_repos.append(repo.name)

    return RepoAnalysis(clean_repos, dirty_repos, missing_repos, non_git_dirs)


async def show_sync_preview(
    repositories: list[Repository],
    target_path: Path,
    force: bool,
    detailed: bool,
    flat_layout: bool = True,
    resolved_names: dict[str, str] | None = None,
):
    """Show detailed preview of sync operations."""
    repo_analysis = await analyze_repository_states(
        repositories, target_path, flat_layout, resolved_names
    )

    # Create summary table
    table = Table(title="Sync Preview")
    table.add_column("Repository", style="cyan", no_wrap=True)
    table.add_column("Current State", style="yellow")
    table.add_column("Planned Action", style="green")
    table.add_column("Notes", style="dim")

    for repo in repositories:
        repo_path = resolve_local_repo_path(repo.clone_url, flat_layout, resolved_names)
        # Display name differs by layout mode
        if flat_layout:
            repo_name = str(repo_path)
        else:
            repo_name = f"{repo_path.parts[-3]}/{repo_path.parts[-1]}"

        if repo.name in repo_analysis.missing_repos:
            table.add_row(repo_name, "Missing", "🔄 Clone", "New repository")
        elif repo.name in repo_analysis.non_git_dirs:
            table.add_row(
                repo_name, "Non-Git", "⚠️ Skip", "Directory exists but not git repo"
            )
        elif repo.name in repo_analysis.dirty_repos:
            if force:
                table.add_row(
                    repo_name, "Dirty", "🗑️ Force Clone", "Will delete local changes"
                )
            else:
                table.add_row(repo_name, "Dirty", "⏭️ Skip", "Has uncommitted changes")
        else:  # clean repo
            if force:
                table.add_row(
                    repo_name, "Clean", "🗑️ Force Clone", "Will re-clone fresh"
                )
            else:
                table.add_row(repo_name, "Clean", "⬇️ Pull", "Update to latest")

    console.print(table)

    # Summary counts
    if detailed:
        summary_table = Table(title="Operation Summary")
        summary_table.add_column("Action", style="bold")
        summary_table.add_column("Count", justify="right", style="green")

        clone_count = len(repo_analysis.missing_repos) + (
            len(repositories) if force else 0
        )
        pull_count = len(repo_analysis.clean_repos) if not force else 0
        skip_count = len(repo_analysis.dirty_repos) + len(repo_analysis.non_git_dirs)
        if force:
            skip_count = len(
                repo_analysis.non_git_dirs
            )  # Only non-git dirs skipped in force mode

        summary_table.add_row("Clone", str(clone_count))
        summary_table.add_row("Pull", str(pull_count))
        summary_table.add_row("Skip", str(skip_count))

        console.print(summary_table)


async def _sync_local_repository(
    state: LocalRepoState, force: bool, auth_configs: list[ProviderAuthConfig]
) -> LocalRepoResult:
    action = _determine_local_action(state, force)
    if action != LOCAL_ACTION_PULL:
        return LocalRepoResult(state=state, action=action, error=state.error)

    if force:
        returncode, stdout, stderr = await _run_git_command(
            state.path, ["reset", "--hard"]
        )
        if returncode != 0:
            error_msg = stderr.strip() or stdout.strip() or "git reset --hard failed"
            return LocalRepoResult(
                state=state, action=LOCAL_ACTION_FAILED, error=error_msg
            )
        returncode, stdout, stderr = await _run_git_command(
            state.path, ["clean", "-fd"]
        )
        if returncode != 0:
            error_msg = stderr.strip() or stdout.strip() or "git clean -fd failed"
            return LocalRepoResult(
                state=state, action=LOCAL_ACTION_FAILED, error=error_msg
            )

    pull_args = _build_git_pull_args(state, auth_configs)
    returncode, stdout, stderr = await _run_git_command(state.path, pull_args)
    if returncode != 0:
        error_msg = stderr.strip() or stdout.strip() or "git pull failed"
        return LocalRepoResult(state=state, action=LOCAL_ACTION_FAILED, error=error_msg)

    return LocalRepoResult(state=state, action=LOCAL_ACTION_PULLED)


async def sync_local_command(
    root: str = ".",
    force: bool = False,
    concurrency: int | None = None,
    dry_run: bool = False,
    progress: bool = True,
    summary: bool = True,
) -> None:
    """
    Synchronize repositories in a local directory tree by running git pull.
    """
    default_concurrency = int(get_global_setting("default_concurrency") or 4)
    if concurrency is None:
        concurrency = default_concurrency

    root_path = Path(root).expanduser().resolve()
    if not root_path.exists() or not root_path.is_dir():
        console.print(
            f"[red]Error:[/red] Local path '{root_path}' does not exist or is not a directory."
        )
        raise typer.Exit(code=1)

    logger.info("Local sync scan: %s", root_path)
    repo_paths = sorted(find_repositories_in_directory(root_path, recursive=True))
    if not repo_paths:
        logger.info("Local sync found no git repositories under %s", root_path)
        console.print(f"[yellow]No git repositories found under {root_path}[/yellow]")
        return

    logger.info("Local sync repositories found: %d", len(repo_paths))
    console.print(f"[blue]Local sync scan:[/blue] {root_path}")

    provider_auth_configs = _load_provider_auth_configs()
    executor = AsyncExecutor(concurrency=concurrency, rich_console=console)

    async def inspect_repo(repo_path: Path) -> LocalRepoState:
        return await _inspect_local_repository(repo_path)

    repo_states, errors = await executor.run_batch(
        items=repo_paths,
        process_func=inspect_repo,
        task_description="Scanning local repositories...",
        show_progress=False,
    )
    repo_states = [state for state in repo_states if state]

    if errors:
        logger.warning("Local sync scan encountered %d errors", len(errors))

    for repo_path, error in errors:
        logger.debug("Local sync scan failed for %s: %s", repo_path, error)
        repo_states.append(
            LocalRepoState(
                path=repo_path,
                name=repo_path.name,
                remote_url=None,
                provider="unknown",
                is_dirty=True,
                error=str(error),
            )
        )

    planned_results = [
        LocalRepoResult(
            state=state,
            action=_determine_local_action(state, force),
            error=state.error,
        )
        for state in repo_states
    ]

    if dry_run:
        _render_local_plan(root_path, planned_results, force)
        if summary:
            _render_local_summary(planned_results, dry_run=True)
        return

    if force:
        force_targets = [
            result for result in planned_results if result.action == LOCAL_ACTION_PULL
        ]
        if force_targets:
            confirmed = Confirm.ask(
                "[red]WARNING:[/red] Force mode will reset and clean "
                f"{len(force_targets)} repositories before pulling. Continue?"
            )
            if not confirmed:
                console.print("Sync cancelled.")
                return

    async def process_repo(state: LocalRepoState) -> LocalRepoResult:
        return await _sync_local_repository(state, force, provider_auth_configs)

    results, errors = await executor.run_batch(
        items=repo_states,
        process_func=process_repo,
        task_description="Pulling local repositories...",
        item_description=lambda state: _format_repo_display(root_path, state.path),
        show_progress=progress,
    )
    results = [result for result in results if result]

    for repo_path, error in errors:
        results.append(
            LocalRepoResult(
                state=LocalRepoState(
                    path=repo_path,
                    name=repo_path.name,
                    remote_url=None,
                    provider="unknown",
                    is_dirty=True,
                    error=str(error),
                ),
                action=LOCAL_ACTION_FAILED,
                error=str(error),
            )
        )

    if summary:
        _render_local_summary(results, dry_run=False)

    _render_local_failures(results, root_path)

    counts = _summarize_local_results(results)
    logger.info(
        "Local sync summary: total=%s pulled=%s skipped_dirty=%s skipped_no_remote=%s failed=%s",
        counts["total"],
        counts["pulled"],
        counts["skipped_dirty"],
        counts["skipped_no_remote"],
        counts["failed"],
    )
    failures = [result for result in results if result.action == LOCAL_ACTION_FAILED]
    if failures:
        logger.warning("Local sync failed for %d repositories", len(failures))
        for result in failures:
            error_msg = result.error or result.state.error or "Unknown error"
            logger.debug("Local sync failed for %s: %s", result.state.path, error_msg)

    if any(result.action == LOCAL_ACTION_FAILED for result in results):
        raise typer.Exit(code=1)


async def sync_command(
    pattern: str,
    path: str = ".",
    provider: str | None = None,
    force: bool = False,
    concurrency: int | None = None,
    dry_run: bool = False,
    progress: bool = True,
    summary: bool = True,
    hierarchy: bool = False,
) -> None:
    """
    Synchronize repositories with remote providers.

    🚀 UNIFIED REPOSITORY SYNC - replaces clone-all and pull-all

    Intelligently handles your repository synchronization:
    - Clones repositories that don't exist locally
    - Pulls updates for repositories that already exist and are clean
    - Skips repositories with uncommitted changes (unless --force)
    - Handles conflicts and errors gracefully
    - Provides detailed progress and summary reporting

    PATTERN can be:
    - Exact: myorg/myproject/myrepo
    - Wildcards: myorg/*/myrepo, */myproject/*, myorg/*/*
    - Cross-provider: */*/* (searches ALL providers)

    When no --provider specified, patterns search ALL configured providers.

    Examples:
        # Daily workspace sync
        mgit sync "myorg/*/*" ./workspace

        # Preview changes first
        mgit sync "myorg/*/*" ./workspace --dry-run

        # Nuclear option - fresh everything
        mgit sync "myorg/*/*" ./workspace --force

        # Quiet sync for scripts
        mgit sync "myorg/*/*" ./workspace --no-progress --no-summary
    """
    # Load configuration
    default_concurrency = int(get_global_setting("default_concurrency") or 4)
    if concurrency is None:
        concurrency = default_concurrency

    # Initialize managers
    git_manager = GitManager()

    # Setup provider manager
    if provider:
        provider_manager = ProviderManager(provider_name=provider)
    else:
        provider_manager = (
            ProviderManager()
        )  # Will be used for non-pattern queries only

    # Setup target path
    target_path = Path(path).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    # Detect NTFS mounts under WSL where git clone will fail due to chmod
    from mgit.utils.platform_compat import is_wsl_ntfs_without_metadata

    if is_wsl_ntfs_without_metadata(target_path):
        console.print(
            "[bold red]Error:[/bold red] Target path is on an NTFS mount "
            f"({target_path}). Git clone will fail because NTFS under WSL "
            "does not support chmod.\n\n"
            "[bold]Fix options:[/bold]\n"
            '  1. Use a native Linux path: mgit sync "pattern" ~/repos\n'
            "  2. Enable metadata in /etc/wsl.conf:\n"
            "     [automount]\n"
            '     options = "metadata"\n'
            "     Then restart WSL: wsl --shutdown"
        )
        raise typer.Exit(1)

    console.print(f"[blue]Synchronizing to:[/blue] {target_path}")

    # Resolve repositories
    repositories, is_multi_provider = await resolve_repositories_for_sync(
        pattern, provider_manager, provider, None
    )

    if not repositories:
        console.print(f"[yellow]No repositories found for pattern '{pattern}'[/yellow]")
        return

    # Determine layout mode (flat by default, hierarchical with --hierarchy)
    flat_layout = not hierarchy

    # Resolve collision names for flat layout mode
    resolved_names: dict[str, str] | None = None
    if flat_layout:
        from mgit.utils.collision_resolver import (
            detect_repo_name_collisions,
            resolve_collision_names,
        )

        name_groups = detect_repo_name_collisions(repositories)
        collisions = {
            name: repos for name, repos in name_groups.items() if len(repos) > 1
        }
        if collisions:
            console.print(
                f"[yellow]Note:[/yellow] {len(collisions)} name collision(s) detected, "
                "directories will be disambiguated"
            )
            for name, repos in collisions.items():
                console.print(f"  • {name}: {len(repos)} repos")
        resolved_names = resolve_collision_names(repositories)

    # Analyze repositories before operation
    if not dry_run:
        repo_analysis = await analyze_repository_states(
            repositories, target_path, flat_layout, resolved_names
        )

        if repo_analysis.dirty_repos and not force:
            console.print(
                "\n[yellow]⚠️  Repositories with uncommitted changes:[/yellow]"
            )
            for repo_name in repo_analysis.dirty_repos:
                console.print(f"  • {repo_name}")
            console.print(
                "\n[blue]These will be skipped. Use --force to override (will lose changes)[/blue]"
            )

        if repo_analysis.non_git_dirs:
            console.print(
                "\n[yellow]⚠️  Directories that exist but are not git repositories:[/yellow]"
            )
            for dir_name in repo_analysis.non_git_dirs:
                console.print(f"  • {dir_name}")
            console.print(
                "\n[blue]These will be skipped (folder exists but not a git repo)[/blue]"
            )

        # Filter out dirty repos and non-git dirs from processing (unless force mode)
        if not force:
            skip_names = set(repo_analysis.dirty_repos) | set(
                repo_analysis.non_git_dirs
            )
            if skip_names:
                repositories = [r for r in repositories if r.name not in skip_names]

    # Enhanced dry run with repository analysis
    if dry_run:
        await show_sync_preview(
            repositories, target_path, force, summary, flat_layout, resolved_names
        )
        return

    # Determine update mode based on force flag
    update_mode = UpdateMode.force if force else UpdateMode.pull

    confirmed_force_remove = False
    dirs_to_remove = []
    if force:
        confirmed_force_remove, dirs_to_remove = check_force_mode_confirmation(
            repositories, target_path, update_mode, flat_layout, resolved_names
        )
        if dirs_to_remove and not confirmed_force_remove:
            console.print("Sync cancelled.")
            return

    # Create processor - use appropriate provider manager
    if is_multi_provider:
        # For multi-provider operations, let the processor handle individual repo URLs
        processor_provider_manager = ProviderManager()
    else:
        processor_provider_manager = provider_manager

    processor = BulkOperationProcessor(
        git_manager=git_manager,
        provider_manager=processor_provider_manager,
        operation_type=OperationType.clone,  # Sync uses clone operation type but with pull update mode
        flat_layout=flat_layout,
    )

    console.print(f"\n[blue]Synchronizing {len(repositories)} repositories...[/blue]")

    # Run sync with progress tracking
    if progress:
        await run_sync_with_progress(
            repositories,
            target_path,
            processor,
            concurrency,
            update_mode,
            confirmed_force_remove,
            dirs_to_remove,
            resolved_names,
        )
    else:
        await run_sync_quiet(
            repositories,
            target_path,
            processor,
            concurrency,
            update_mode,
            confirmed_force_remove,
            dirs_to_remove,
            resolved_names,
        )


async def run_sync_with_progress(
    repositories,
    target_path,
    processor,
    concurrency,
    update_mode,
    confirmed_force_remove,
    dirs_to_remove,
    resolved_names: dict[str, str] | None = None,
):
    """Run sync operation with rich progress reporting."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Add main progress task
        sync_task = progress.add_task(
            "Synchronizing repositories...", total=len(repositories)
        )

        # Custom callback to update progress
        async def progress_callback(completed: int, total: int, current_repo: str):
            progress.update(
                sync_task, completed=completed, description=f"Syncing: {current_repo}"
            )

        # Run sync with progress callback
        failures = await processor.process_repositories(
            repositories=repositories,
            target_path=target_path,
            concurrency=concurrency,
            update_mode=update_mode,
            confirmed_force_remove=confirmed_force_remove,
            dirs_to_remove=dirs_to_remove,
            show_progress=False,
            resolved_names=resolved_names,
        )

    # Show final results
    skipped = processor.skipped
    success_count = len(repositories) - len(failures) - len(skipped)

    if failures or skipped:
        console.print("\n[yellow]Sync completed with issues:[/yellow]")
        console.print(f"  [green]✅ Successful:[/green] {success_count}")
        if skipped:
            console.print(f"  [yellow]⏭ Skipped:[/yellow] {len(skipped)}")
        if failures:
            console.print(f"  [red]❌ Failed:[/red] {len(failures)}")

        if failures:
            failure_table = Table(title="Failed Operations")
            failure_table.add_column("Repository", style="red")
            failure_table.add_column("Error", style="yellow")

            for repo_name, error_msg in failures:
                failure_table.add_row(repo_name, error_msg)

            console.print(failure_table)
            raise typer.Exit(code=1)
    else:
        console.print(
            f"\n[green]✅ Successfully synchronized {success_count} repositories![/green]"
        )


async def run_sync_quiet(
    repositories,
    target_path,
    processor,
    concurrency,
    update_mode,
    confirmed_force_remove,
    dirs_to_remove,
    resolved_names: dict[str, str] | None = None,
):
    """Run sync operation without progress reporting."""
    failures = await processor.process_repositories(
        repositories=repositories,
        target_path=target_path,
        concurrency=concurrency,
        update_mode=update_mode,
        confirmed_force_remove=confirmed_force_remove,
        dirs_to_remove=dirs_to_remove,
        show_progress=False,
        resolved_names=resolved_names,
    )

    skipped = processor.skipped
    success_count = len(repositories) - len(failures) - len(skipped)

    if skipped:
        logger.info(f"Skipped {len(skipped)} repositories")
        for repo_name, reason in skipped:
            logger.info(f"Skipped: {repo_name}: {reason}")

    if failures:
        logger.error(
            f"Sync completed with {len(failures)} failures out of {len(repositories)} repositories"
        )
        for repo_name, error_msg in failures:
            logger.error(f"Failed: {repo_name}: {error_msg}")
        raise typer.Exit(code=1)
    else:
        logger.info(f"Successfully synchronized {success_count} repositories")
