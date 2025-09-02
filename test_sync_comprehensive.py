"""
Comprehensive test suite for the sync command.

Tests basic functionality, multi-provider behavior, dry-run, error handling,
progress reporting, repository state analysis, and edge cases.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typer.testing import CliRunner

from mgit.commands.sync import (
    sync_command,
    resolve_repositories_for_sync,
    analyze_repository_states,
    show_sync_preview,
    run_sync_with_progress,
    run_sync_quiet
)
from mgit.providers.base import Repository
from mgit.utils.pattern_matching import PatternAnalysis


class TestSyncBasicFunctionality:
    """Test basic sync command functionality."""

    def test_sync_help_command(self):
        """Test that sync command shows proper help."""
        runner = CliRunner()
        result = runner.invoke(sync_command, ["--help"])
        assert result.exit_code == 0
        assert "Synchronize repositories" in result.output
        assert "UNIFIED REPOSITORY SYNC" in result.output
        assert "replaces clone-all and pull-all" in result.output

    def test_sync_requires_pattern_argument(self):
        """Test that sync command requires pattern argument."""
        runner = CliRunner()
        result = runner.invoke(sync_command, [])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "requires a value" in result.output

    def test_sync_with_invalid_pattern(self):
        """Test sync command with invalid pattern."""
        runner = CliRunner()
        result = runner.invoke(sync_command, ["invalid/pattern/more/segments", "/tmp/test"])
        assert result.exit_code != 0
        assert "must have exactly 3 segments" in result.output

    @pytest.mark.asyncio
    async def test_sync_with_empty_repositories(self):
        """Test sync command when no repositories are found."""
        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.return_value = ([], False)

            with patch('mgit.commands.sync.console') as mock_console:
                await sync_command("test/*/*", "/tmp/test", dry_run=True)

                # Should print "No repositories found" message
                mock_console.print.assert_any_call("[yellow]No repositories found for pattern 'test/*/*'[/yellow]")

    @pytest.mark.asyncio
    async def test_sync_dry_run_basic(self):
        """Test basic dry-run functionality."""
        # Create mock repository
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"
        mock_repo.project = "testproj"

        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.return_value = ([mock_repo], False)

            with patch('mgit.commands.sync.show_sync_preview') as mock_preview:
                await sync_command("test/*/*", "/tmp/test", dry_run=True)

                # Should call show_sync_preview
                mock_preview.assert_called_once()


class TestSyncMultiProvider:
    """Test multi-provider functionality."""

    @pytest.mark.asyncio
    async def test_sync_multi_provider_pattern(self):
        """Test sync with multi-provider pattern."""
        with patch('mgit.commands.sync.list_provider_names') as mock_providers:
            mock_providers.return_value = ['github', 'azure', 'bitbucket']

            with patch('mgit.commands.sync.MultiProviderResolver') as mock_resolver_class:
                mock_resolver = Mock()
                mock_resolver_class.return_value = mock_resolver

                mock_result = Mock()
                mock_result.repositories = []
                mock_result.successful_providers = ['github', 'azure']
                mock_result.failed_providers = ['bitbucket']
                mock_result.duplicates_removed = 0

                mock_resolver.resolve_repositories.return_value = mock_result

                with patch('mgit.commands.sync.console') as mock_console:
                    await sync_command("org/*/*", "/tmp/test", dry_run=True)

                    # Should show multi-provider message
                    mock_console.print.assert_any_call(
                        "[blue]Synchronizing across 3 providers:[/blue] github, azure, bitbucket"
                    )

    @pytest.mark.asyncio
    async def test_sync_single_provider_explicit(self):
        """Test sync with explicit provider."""
        with patch('mgit.commands.sync.list_provider_names') as mock_providers:
            mock_providers.return_value = ['github', 'azure']

            with patch('mgit.commands.sync.MultiProviderResolver') as mock_resolver_class:
                mock_resolver = Mock()
                mock_resolver_class.return_value = mock_resolver

                mock_result = Mock()
                mock_result.repositories = []
                mock_resolver.resolve_repositories.return_value = mock_result

                with patch('mgit.commands.sync.console') as mock_console:
                    await sync_command("org/*/*", "/tmp/test", provider="github", dry_run=True)

                    # Should show single provider message
                    mock_console.print.assert_any_call(
                        "[blue]Synchronizing from provider:[/blue] github"
                    )

    @pytest.mark.asyncio
    async def test_sync_no_providers_configured(self):
        """Test sync when no providers are configured."""
        with patch('mgit.commands.sync.list_provider_names') as mock_providers:
            mock_providers.return_value = []

            with patch('mgit.commands.sync.console') as mock_console:
                # Should handle gracefully and show error message
                try:
                    await sync_command("org/*/*", "/tmp/test", dry_run=True)
                except SystemExit:
                    pass  # Expected due to typer.Exit

                mock_console.print.assert_any_call(
                    "[red]Error:[/red] No providers configured. Run 'mgit login' to add providers."
                )


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
            with patch('asyncio.subprocess.run') as mock_run:
                mock_result = Mock()
                mock_result.stdout = ""
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
            with patch('asyncio.subprocess.run') as mock_run:
                mock_result = Mock()
                mock_result.stdout = "M modified-file.txt\n?? untracked-file.txt"
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


class TestSyncDryRunPreview:
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


class TestSyncProgressReporting:
    """Test progress reporting functionality."""

    @pytest.mark.asyncio
    async def test_progress_reporting_enabled(self):
        """Test that progress reporting is shown when enabled."""
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"

        with patch('mgit.commands.sync.run_sync_with_progress') as mock_progress:
            with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
                mock_resolve.return_value = ([mock_repo], False)

                with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
                    mock_analysis = Mock()
                    mock_analysis.dirty_repos = []
                    mock_analyze.return_value = mock_analysis

                    await sync_command("test/*/*", "/tmp/test", progress=True)

                    # Should call progress version
                    mock_progress.assert_called_once()

    @pytest.mark.asyncio
    async def test_progress_reporting_disabled(self):
        """Test that quiet mode is used when progress is disabled."""
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"

        with patch('mgit.commands.sync.run_sync_quiet') as mock_quiet:
            with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
                mock_resolve.return_value = ([mock_repo], False)

                with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
                    mock_analysis = Mock()
                    mock_analysis.dirty_repos = []
                    mock_analyze.return_value = mock_analysis

                    await sync_command("test/*/*", "/tmp/test", progress=False)

                    # Should call quiet version
                    mock_quiet.assert_called_once()


class TestSyncErrorHandling:
    """Test error handling in sync command."""

    @pytest.mark.asyncio
    async def test_sync_handles_processor_failures(self):
        """Test sync handles failures from the bulk processor."""
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"

        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.return_value = ([mock_repo], False)

            with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
                mock_analysis = Mock()
                mock_analysis.dirty_repos = []
                mock_analyze.return_value = mock_analysis

                with patch('mgit.commands.sync.run_sync_with_progress') as mock_progress:
                    mock_progress.return_value = None

                    # Mock processor to return failures
                    with patch('mgit.commands.sync.BulkOperationProcessor') as mock_processor_class:
                        mock_processor = Mock()
                        mock_processor_class.return_value = mock_processor
                        mock_processor.process_repositories.return_value = ["repo1: Clone failed", "repo2: Pull failed"]

                        with patch('mgit.commands.sync.console') as mock_console:
                            try:
                                await sync_command("test/*/*", "/tmp/test")
                            except SystemExit:
                                pass  # Expected due to typer.Exit

                            # Should show failure messages
                            mock_console.print.assert_any_call(
                                "[yellow]Sync completed with issues:[/yellow]"
                            )

    @pytest.mark.asyncio
    async def test_sync_force_confirmation(self):
        """Test that force mode requires confirmation."""
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"

        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.return_value = ([mock_repo], False)

            with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
                mock_analysis = Mock()
                mock_analysis.dirty_repos = []
                mock_analyze.return_value = mock_analysis

                with patch('rich.prompt.Confirm.ask') as mock_confirm:
                    mock_confirm.return_value = False  # User cancels

                    with patch('mgit.commands.sync.console') as mock_console:
                        await sync_command("test/*/*", "/tmp/test", force=True)

                        # Should show cancellation message
                        mock_console.print.assert_any_call("Sync cancelled.")


class TestSyncEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_sync_with_non_standard_repo_structure(self):
        """Test sync with repositories that don't follow org/project/repo structure."""
        # Test with repositories that have None project
        mock_repo = Mock()
        mock_repo.organization = "testorg"
        mock_repo.name = "testrepo"
        mock_repo.project = None

        target_path = Path("/tmp/test")

        with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
            mock_analysis = Mock()
            mock_analysis.missing_repos = ["testrepo"]
            mock_analysis.dirty_repos = []
            mock_analysis.clean_repos = []
            mock_analysis.non_git_dirs = []
            mock_analyze.return_value = mock_analysis

            with patch('mgit.commands.sync.show_sync_preview') as mock_preview:
                await sync_command("test/*/*", "/tmp/test", dry_run=True)

                # Should handle None project gracefully
                mock_preview.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_concurrency_parameter(self):
        """Test that concurrency parameter is properly handled."""
        with patch('mgit.commands.sync.get_global_setting') as mock_setting:
            mock_setting.return_value = 4

            # Test with None concurrency (should use default)
            await sync_command("test/*/*", "/tmp/test", concurrency=None, dry_run=True)

            # Test with explicit concurrency
            await sync_command("test/*/*", "/tmp/test", concurrency=8, dry_run=True)

            # Verify get_global_setting was called
            assert mock_setting.call_count >= 2

    @pytest.mark.asyncio
    async def test_sync_path_resolution(self):
        """Test that paths are properly resolved."""
        with patch('pathlib.Path') as mock_path:
            mock_path_instance = Mock()
            mock_path_instance.resolve.return_value = Path("/absolute/path/test")
            mock_path_instance.mkdir = Mock()
            mock_path.return_value = mock_path_instance

            with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
                mock_resolve.return_value = ([], False)

                await sync_command("test/*/*", "relative/path", dry_run=True)

                # Should resolve the path
                mock_path_instance.resolve.assert_called_once()
                mock_path_instance.mkdir.assert_called_once()


class TestSyncIntegration:
    """Integration tests that combine multiple components."""

    @pytest.mark.asyncio
    async def test_sync_full_workflow_dry_run(self):
        """Test complete sync workflow in dry-run mode."""
        # Create mock repository
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
                    # Run full sync workflow
                    await sync_command("test/*/*", "/tmp/test", dry_run=True, summary=True)

                    # Verify all components were called
                    mock_resolve.assert_called_once()
                    mock_analyze.assert_called_once()
                    mock_preview.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_error_recovery(self):
        """Test sync handles and recovers from various errors."""
        # Test with repository resolution failure
        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.side_effect = Exception("Network error")

            with patch('mgit.commands.sync.console') as mock_console:
                try:
                    await sync_command("test/*/*", "/tmp/test")
                except SystemExit:
                    pass  # Expected

                # Should show error message
                mock_console.print.assert_any_call("[red]Error:[/red] Network error")

    @pytest.mark.asyncio
    async def test_sync_large_repository_set(self):
        """Test sync with a large number of repositories."""
        # Create many mock repositories
        mock_repos = []
        for i in range(50):
            mock_repo = Mock()
            mock_repo.organization = f"org{i}"
            mock_repo.name = f"repo{i}"
            mock_repo.project = f"proj{i}"
            mock_repos.append(mock_repo)

        with patch('mgit.commands.sync.resolve_repositories_for_sync') as mock_resolve:
            mock_resolve.return_value = (mock_repos, False)

            with patch('mgit.commands.sync.analyze_repository_states') as mock_analyze:
                mock_analysis = Mock()
                mock_analysis.dirty_repos = []
                mock_analyze.return_value = mock_analysis

                with patch('mgit.commands.sync.show_sync_preview') as mock_preview:
                    await sync_command("test/*/*", "/tmp/test", dry_run=True)

                    # Should handle large repository set
                    mock_preview.assert_called_once()


# Run the tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])