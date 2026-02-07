"""Unit tests for multi-provider config routing in ProviderManager.

Verifies that get_authenticated_clone_url uses the provider_config_name
metadata stamp to select the correct provider config, rather than falling
back to the default or first-matching config.
"""

from unittest.mock import MagicMock, patch

import pytest

from mgit.providers.base import Repository
from mgit.providers.manager import ProviderManager


@pytest.mark.unit
class TestProviderConfigRouting:
    """Test that repos are cloned with the token from the discovering provider."""

    @patch("mgit.providers.manager.ProviderFactory")
    @patch("mgit.providers.manager.get_provider_config")
    @patch("mgit.providers.manager.detect_provider_type")
    def test_metadata_selects_correct_config(
        self, mock_detect_type, mock_get_config, mock_factory
    ):
        """Repo with provider_config_name metadata uses that config, not default."""
        secondary_config = {
            "url": "https://github.com",
            "user": "secondary_user",
            "token": "secondary_tok",
        }
        mock_get_config.return_value = secondary_config
        mock_detect_type.return_value = "github"

        mock_provider = MagicMock()
        mock_provider.get_authenticated_clone_url.return_value = (
            "https://secondary_user:secondary_tok@github.com/org/repo"
        )
        mock_factory.create_provider.return_value = mock_provider

        repo = Repository(
            name="my-repo",
            clone_url="https://github.com/org/my-repo",
            provider="github",
            metadata={"provider_config_name": "github_secondary"},
        )

        manager = MagicMock(spec=ProviderManager)
        manager._provider_type = "github"
        manager.get_provider.return_value = MagicMock()
        manager.get_authenticated_clone_url = (
            ProviderManager.get_authenticated_clone_url.__get__(
                manager, ProviderManager
            )
        )

        url = manager.get_authenticated_clone_url(repo)

        mock_get_config.assert_called_once_with("github_secondary")
        mock_factory.create_provider.assert_called_once_with(
            "github", secondary_config
        )
        mock_provider.get_authenticated_clone_url.assert_called_once_with(repo)
        assert url == "https://secondary_user:secondary_tok@github.com/org/repo"

    @patch("mgit.providers.manager.ProviderFactory")
    @patch("mgit.providers.manager.get_provider_config")
    @patch("mgit.providers.manager.detect_provider_type")
    def test_no_metadata_falls_back_to_default(
        self, mock_detect_type, mock_get_config, mock_factory
    ):
        """Repo without provider_config_name uses the manager's own provider."""
        default_provider = MagicMock()
        default_provider.get_authenticated_clone_url.return_value = (
            "https://default:tok@github.com/org/repo"
        )

        repo = Repository(
            name="my-repo",
            clone_url="https://github.com/org/my-repo",
            provider="github",
        )

        manager = MagicMock(spec=ProviderManager)
        manager._provider_type = "github"
        manager.get_provider.return_value = default_provider
        manager._find_config_by_type = MagicMock()
        manager.get_authenticated_clone_url = (
            ProviderManager.get_authenticated_clone_url.__get__(
                manager, ProviderManager
            )
        )

        url = manager.get_authenticated_clone_url(repo)

        mock_get_config.assert_not_called()
        mock_factory.create_provider.assert_not_called()
        default_provider.get_authenticated_clone_url.assert_called_once_with(repo)
        assert url == "https://default:tok@github.com/org/repo"

    @patch("mgit.providers.manager.ProviderFactory")
    @patch("mgit.providers.manager.get_provider_config")
    @patch("mgit.providers.manager.detect_provider_type")
    def test_metadata_config_failure_falls_back(
        self, mock_detect_type, mock_get_config, mock_factory
    ):
        """If stamped config lookup fails, falls back to default provider."""
        mock_get_config.side_effect = Exception("config deleted")

        default_provider = MagicMock()
        default_provider.get_authenticated_clone_url.return_value = (
            "https://fallback:tok@github.com/org/repo"
        )

        repo = Repository(
            name="my-repo",
            clone_url="https://github.com/org/my-repo",
            provider="github",
            metadata={"provider_config_name": "github_deleted"},
        )

        manager = MagicMock(spec=ProviderManager)
        manager._provider_type = "github"
        manager.get_provider.return_value = default_provider
        manager.get_authenticated_clone_url = (
            ProviderManager.get_authenticated_clone_url.__get__(
                manager, ProviderManager
            )
        )

        url = manager.get_authenticated_clone_url(repo)

        mock_get_config.assert_called_once_with("github_deleted")
        default_provider.get_authenticated_clone_url.assert_called_once_with(repo)
        assert url == "https://fallback:tok@github.com/org/repo"

    @patch("mgit.providers.manager.ProviderFactory")
    @patch("mgit.providers.manager.get_provider_config")
    @patch("mgit.providers.manager.detect_provider_type")
    def test_metadata_overrides_cross_type_fallback(
        self, mock_detect_type, mock_get_config, mock_factory
    ):
        """Metadata takes priority even when provider types differ."""
        ado_config = {"url": "https://dev.azure.com/org", "user": "u", "token": "t"}
        mock_get_config.return_value = ado_config
        mock_detect_type.return_value = "azuredevops"

        ado_provider = MagicMock()
        ado_provider.get_authenticated_clone_url.return_value = (
            "https://u:t@dev.azure.com/org/_git/repo"
        )
        mock_factory.create_provider.return_value = ado_provider

        repo = Repository(
            name="my-repo",
            clone_url="https://dev.azure.com/org/proj/_git/my-repo",
            provider="azuredevops",
            metadata={"provider_config_name": "ado_work"},
        )

        manager = MagicMock(spec=ProviderManager)
        manager._provider_type = "github"
        manager.get_provider.return_value = MagicMock()
        manager._find_config_by_type = MagicMock()
        manager.get_authenticated_clone_url = (
            ProviderManager.get_authenticated_clone_url.__get__(
                manager, ProviderManager
            )
        )

        url = manager.get_authenticated_clone_url(repo)

        mock_get_config.assert_called_once_with("ado_work")
        mock_factory.create_provider.assert_called_once_with("azuredevops", ado_config)
        manager._find_config_by_type.assert_not_called()
        assert url == "https://u:t@dev.azure.com/org/_git/repo"
