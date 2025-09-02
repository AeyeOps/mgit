"""
Focused test suite for the sync command functionality.

Tests key components and integration points with proper mocking.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mgit.commands.sync import (
    analyze_repository_states,
    show_sync_preview,
    resolve_repositories_for_sync
)
from mgit.providers.base import Repository


class TestSyncRepositoryAnalysis:
    """Test repository state analysis functionality."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository."""
        repo = Mock()
        repo.organization = "testorg"
        repo.name = "testrepo"
        repo.project = "testproj"
        return repo

    @pytest.mark.asyncio
    async def test_analyze_missing_repository(self, mock_repo):
        """Test analysis of missing repository."""
        target_path = Path("/tmp/test")

        # Mock Path to simulate missing repository
        with patch('pathlib.Path') as mock_path_class:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = False
            mock_path_class.return_value = mock_path_instance

            result = await analyze_repository_states([mock_repo], target_path)

            assert len(result.missing_repos) == 1
            assert result.missing_repos[0] == "testrepo"
            assert len(result.clean_repos) == 0
            assert len(result.dirty_repos) == 0

    @pytest.mark.asyncio
    async def test_analyze_clean_repository(self, mock_repo):
        """Test analysis of clean repository."""
        target_path = Path("/tmp/test")

        with patch('pathlib.Path') as mock_path_class:
            # Mock repository directory exists and has .git
            mock_repo_path = Mock()
            mock_repo_path.exists.return_value = True
            mock_repo_path.is_dir.return_value = True

            # Mock .git directory exists
            mock_git_path = Mock()
            mock_git_path.exists.return_value = True

            # Mock subprocess for git status (clean repo)
            mock_result = Mock()
            mock_result.stdout = ""

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                def path_side_effect(path_str):
                    if ".git" in path_str:
                        return mock_git_path
                    else:
                        return mock_repo_path

                mock_path_class.side_effect = path_side_effect

                result = await analyze_repository_states([mock_repo], target_path)

                assert len(result.clean_repos) == 1
                assert result.clean_repos[0] == "testrepo"

    @pytest.mark.asyncio
    async def test_analyze_dirty_repository(self, mock_repo):
        """Test analysis of dirty repository."""
        target_path = Path("/tmp/test")

        with patch('pathlib.Path') as mock_path_class:
            # Mock repository directory exists and has .git
            mock_repo_path = Mock()
            mock_repo_path.exists.return_value = True
            mock_repo_path.is_dir.return_value = True

            mock_git_path = Mock()
            mock_git_path.exists.return_value = True

            # Mock subprocess for git status (dirty repo)
            mock_result = Mock()
            mock_result.stdout = "M modified-file.txt\n?? untracked-file.txt"

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = mock_result

                def path_side_effect(path_str):
                    if ".git" in path_str:
                        return mock_git_path
                    else:
                        return mock_repo_path

                mock_path_class.side_effect = path_side_effect

                result = await analyze_repository_states([mock_repo], target_path)

                assert len(result.dirty_repos) == 1
                assert result.dirty_repos[0] == "testrepo"


class TestSyncPreviewFunctionality:
    """Test dry-run preview functionality."""

    @pytest.mark.asyncio
    async def test_show_sync_preview_missing_repo(self):
        """Test preview for missing repository."""
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"

        target_path = Path("/tmp/test")

        with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
            mock_analysis = Mock()
            mock_analysis.missing_repos = ["testrepo"]
            mock_analysis.dirty_repos = []
            mock_analysis.clean_repos = []
            mock_analysis.non_git_dirs = []
            mock_analyze.return_value = mock_analysis

            with patch('mgit.commands.sync.console') as mock_console:
                await show_sync_preview([mock_repo], target_path, force=False, detailed=True)

                # Should show preview table with missing repo action
                mock_console.print.assert_called()

    @pytest.mark.asyncio
    async def test_show_sync_preview_dirty_repo_no_force(self):
        """Test preview for dirty repository without force."""
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"

        target_path = Path("/tmp/test")

        with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
            mock_analysis = Mock()
            mock_analysis.missing_repos = []
            mock_analysis.dirty_repos = ["testrepo"]
            mock_analysis.clean_repos = []
            mock_analysis.non_git_dirs = []
            mock_analyze.return_value = mock_analysis

            with patch('mgit.commands.sync.console') as mock_console:
                await show_sync_preview([mock_repo], target_path, force=False, detailed=True)

                # Should show skip action for dirty repo
                mock_console.print.assert_called()


class TestSyncMultiProviderResolution:
    """Test multi-provider repository resolution."""

    @pytest.mark.asyncio
    async def test_resolve_repositories_multi_provider(self):
        """Test multi-provider repository resolution."""
        with patch('mgit.commands.sync.list_provider_names') as mock_providers:
            mock_providers.return_value = ['github_pdi', 'azure_pdidev']

            with patch('mgit.commands.sync.MultiProviderResolver') as mock_resolver_class:
                mock_resolver = Mock()
                mock_resolver_class.return_value = mock_resolver

                mock_result = Mock()
                mock_result.repositories = [
                    Mock(organization="testorg", name="repo1"),
                    Mock(organization="testorg", name="repo2")
                ]
                mock_result.successful_providers = ['github_pdi']
                mock_result.failed_providers = []
                mock_result.duplicates_removed = 0

                mock_resolver.resolve_repositories.return_value = mock_result

                with patch('mgit.commands.sync.console') as mock_console:
                    repos, is_multi = await resolve_repositories_for_sync(
                        "testorg/*/*", None, None, None
                    )

                    # Should find repositories
                    assert len(repos) == 2
                    assert is_multi == True

                    # Should show multi-provider message
                    mock_console.print.assert_any_call(
                        "[blue]Synchronizing across 2 providers:[/blue] github_pdi, azure_pdidev"
                    )

    @pytest.mark.asyncio
    async def test_resolve_repositories_single_provider(self):
        """Test single provider repository resolution."""
        with patch('mgit.commands.sync.MultiProviderResolver') as mock_resolver_class:
            mock_resolver = Mock()
            mock_resolver_class.return_value = mock_resolver

            mock_result = Mock()
            mock_result.repositories = [Mock(organization="testorg", name="repo1")]
            mock_resolver.resolve_repositories.return_value = mock_result

            # Mock provider manager
            mock_provider_manager = Mock()
            mock_provider_manager.provider_name = "github_pdi"

            with patch('mgit.commands.sync.console') as mock_console:
                repos, is_multi = await resolve_repositories_for_sync(
                    "testorg/*/*", mock_provider_manager, "github_pdi", None
                )

                # Should find repositories
                assert len(repos) == 1
                assert is_multi == False

                # Should show single provider message
                mock_console.print.assert_any_call(
                    "[blue]Synchronizing from provider:[/blue] github_pdi"
                )

    @pytest.mark.asyncio
    async def test_resolve_repositories_pattern_validation(self):
        """Test pattern validation in repository resolution."""
        with patch('mgit.commands.sync.console') as mock_console:
            try:
                await resolve_repositories_for_sync(
                    "invalid/pattern/more/segments", None, None, None
                )
            except SystemExit:
                pass  # Expected due to validation error

            # Should show validation error
            mock_console.print.assert_any_call(
                "[red]Error:[/red] Pattern must have exactly 3 segments separated by '/'"
            )


class TestSyncPatternAnalysis:
    """Test pattern analysis integration."""

    @pytest.mark.asyncio
    async def test_pattern_analysis_multi_provider(self):
        """Test pattern analysis for multi-provider patterns."""
        with patch('mgit.commands.sync.analyze_pattern') as mock_analyze_pattern:
            mock_pattern_result = Mock()
            mock_pattern_result.is_multi_provider = True
            mock_pattern_result.normalized_pattern = "org/*/*"
            mock_pattern_result.validation_errors = []
            mock_analyze_pattern.return_value = mock_pattern_result

            with patch('mgit.commands.sync.list_provider_names') as mock_providers:
                mock_providers.return_value = ['github_pdi']

                with patch('mgit.commands.sync.MultiProviderResolver') as mock_resolver_class:
                    mock_resolver = Mock()
                    mock_resolver_class.return_value = mock_resolver

                    mock_result = Mock()
                    mock_result.repositories = []
                    mock_resolver.resolve_repositories.return_value = mock_result

                    repos, is_multi = await resolve_repositories_for_sync(
                        "org/*/*", None, None, None
                    )

                    # Should detect as multi-provider
                    assert is_multi == True


class TestSyncIntegrationWorkflow:
    """Test integrated sync workflow components."""

    @pytest.mark.asyncio
    async def test_complete_sync_workflow_dry_run(self):
        """Test complete sync workflow in dry-run mode."""
        from mgit.commands.sync import sync_command

        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"
        mock_repo.project = "testproj"

        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.return_value = ([mock_repo], False)

            with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
                mock_analysis = Mock()
                mock_analysis.dirty_repos = []
                mock_analyze.return_value = mock_analysis

                with patch('mgit.commands.sync.show_sync_preview') as mock_preview:
                    with patch('mgit.commands.sync.get_global_setting') as mock_setting:
                        mock_setting.return_value = 4

                        # Mock provider manager creation
                        with patch('mgit.commands.sync.ProviderManager') as mock_pm_class:
                            mock_pm = Mock()
                            mock_pm_class.return_value = mock_pm

                            await sync_command(
                                "test/*/*", "/tmp/test", dry_run=True, progress=True
                            )

                            # Verify workflow components were called
                            mock_resolve.assert_called_once()
                            mock_analyze.assert_called_once()
                            mock_preview.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_error_handling(self):
        """Test error handling in sync operations."""
        from mgit.commands.sync import sync_command

        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.side_effect = Exception("Network timeout")

            with patch('mgit.commands.sync.console') as mock_console:
                try:
                    await sync_command("test/*/*", "/tmp/test", dry_run=True)
                except SystemExit:
                    pass  # Expected

                # Should show error message
                mock_console.print.assert_any_call("[red]Error:[/red] Network timeout")


class TestSyncPerformance:
    """Test performance characteristics of sync operations."""

    @pytest.mark.asyncio
    async def test_sync_large_repository_analysis(self):
        """Test performance with large repository sets."""
        # Create many mock repositories
        mock_repos = []
        for i in range(100):
            mock_repo = Mock()
            mock_repo.organization = f"org{i}"
            mock_repo.name = f"repo{i}"
            mock_repo.project = f"proj{i}"
            mock_repos.append(mock_repo)

        target_path = Path("/tmp/test")

        # Mock all Path operations to be fast
        with patch('pathlib.Path') as mock_path_class:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = False
            mock_path_class.return_value = mock_path_instance

            import time
            start_time = time.time()

            result = await analyze_repository_states(mock_repos, target_path)

            end_time = time.time()
            duration = end_time - start_time

            # Should handle 100 repos quickly (under 1 second)
            assert duration < 1.0
            assert len(result.missing_repos) == 100


# Manual test scenarios to run
def test_manual_scenarios():
    """Print manual test scenarios for verification."""
    scenarios = [
        "Test basic sync help: mgit sync --help",
        "Test multi-provider sync: mgit sync '*/test/*' /tmp/sync-test --dry-run",
        "Test single provider sync: mgit sync 'testorg/*/*' /tmp/sync-test --provider github_pdi --dry-run",
        "Test invalid pattern: mgit sync 'invalid/pattern' /tmp/test",
        "Test force confirmation: mgit sync 'test/*/*' /tmp/test --force",
        "Test progress reporting: mgit sync 'test/*/*' /tmp/test --progress",
        "Test quiet mode: mgit sync 'test/*/*' /tmp/test --no-progress --no-summary",
        "Test clone-all deprecation: mgit clone-all 'test/*/*' /tmp/test",
        "Test pull-all deprecation: mgit pull-all 'test/*/*' /tmp/test",
    ]

    print("=== MANUAL TEST SCENARIOS ===")
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario}")
    print("\n=== AUTOMATED TEST RESULTS ===")
    return scenarios


# Run manual scenarios if executed directly
if __name__ == "__main__":
    scenarios = test_manual_scenarios()
    print(f"Prepared {len(scenarios)} manual test scenarios")
    print("\nRun: python -m pytest test_sync_focused.py -v")