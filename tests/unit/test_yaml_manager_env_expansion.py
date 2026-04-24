"""Unit tests for ${VAR} environment-variable placeholder expansion in config.yaml.

Covers both the pure helper (`_expand_env_placeholders`) and the load-time
integration through `ConfigurationManager._load_config`.
"""

from pathlib import Path

import pytest

from mgit.config import yaml_manager
from mgit.config.yaml_manager import (
    ConfigurationManager,
    _expand_env_placeholders,
)
from mgit.exceptions import ConfigurationError


@pytest.fixture
def isolated_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect yaml_manager's module-level CONFIG_FILE (and CONFIG_DIR) to tmp_path.

    Also clears any globals that the shared module-level config_manager may have
    cached; each test here builds its own ConfigurationManager instance, so the
    module-level cache is only indirectly relevant, but keep things tidy anyway.
    """
    config_dir = tmp_path / "mgit"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"
    monkeypatch.setattr(yaml_manager, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(yaml_manager, "CONFIG_FILE", config_file)
    return config_file


@pytest.mark.unit
class TestExpandEnvPlaceholdersHelper:
    """Direct tests of the `_expand_env_placeholders` pure helper."""

    def test_simple_placeholder(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A bare `${FOO}` value resolves to the env var's value."""
        monkeypatch.setenv("FOO", "bar")
        data = {"token": "${FOO}"}
        result = _expand_env_placeholders(data)
        assert result == {"token": "bar"}

    def test_partial_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A placeholder embedded in a larger string is substituted in-place."""
        monkeypatch.setenv("HOST", "example.com")
        data = {"url": "https://${HOST}/api"}
        result = _expand_env_placeholders(data)
        assert result == {"url": "https://example.com/api"}

    def test_multiple_placeholders(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multiple placeholders in one string are all substituted."""
        monkeypatch.setenv("A", "1")
        monkeypatch.setenv("B", "2")
        data = {"x": "${A}-${B}"}
        result = _expand_env_placeholders(data)
        assert result == {"x": "1-2"}

    def test_no_placeholder_passthrough(self) -> None:
        """Strings without any placeholder are returned unchanged."""
        data = {"token": "plain-value", "note": "no dollars here"}
        result = _expand_env_placeholders(data)
        assert result == {"token": "plain-value", "note": "no dollars here"}

    def test_non_string_values_untouched(self) -> None:
        """Non-string scalars (int/bool/None) and mixed structures pass through."""
        data = {
            "global": {
                "concurrency": 5,
                "enabled": True,
                "default_provider": None,
                "tags": ["a", "b", 3],
            }
        }
        result = _expand_env_placeholders(data)
        assert result == data

    def test_missing_env_var_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unresolved placeholders raise ConfigurationError naming path + var."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        data = {
            "providers": {
                "github_aeyeops": {"token": "${GITHUB_TOKEN}"},
            }
        }
        with pytest.raises(ConfigurationError) as excinfo:
            _expand_env_placeholders(data)

        message = str(excinfo.value)
        assert "providers.github_aeyeops.token" in message
        assert "${GITHUB_TOKEN}" in message
        assert "GITHUB_TOKEN" in message

    def test_malformed_placeholder_left_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bare `$VAR` and dangling `${` without a closing brace are literals."""
        # Ensure these env vars are not set so a mistaken substitution would
        # surface as an error (rather than silently "succeeding" by coincidence).
        monkeypatch.delenv("FOO", raising=False)
        monkeypatch.delenv("BAR", raising=False)
        data = {
            "bare": "$FOO",
            "open": "${BAR",
            "empty_braces": "${}",
            "numeric_start": "${1BAD}",
        }
        result = _expand_env_placeholders(data)
        # Regex `\$\{([A-Za-z_][A-Za-z0-9_]*)\}` rejects all of these forms,
        # so they survive verbatim through the helper.
        assert result == data


@pytest.mark.unit
class TestExpandEnvPlaceholdersLoadTime:
    """Integration tests: expansion runs via `ConfigurationManager._load_config`."""

    def test_nested_provider_field(
        self,
        isolated_config_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Placeholder deep in `providers.<name>.token` resolves on load."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_live_value")
        isolated_config_file.write_text(
            "providers:\n"
            "  github_aeyeops:\n"
            "    url: https://github.com\n"
            "    user: aeyeopsdev\n"
            "    token: ${GITHUB_TOKEN}\n"
            "global:\n"
            "  default_provider: github_aeyeops\n",
            encoding="utf-8",
        )

        manager = ConfigurationManager()
        config = manager.load_config()

        assert config["providers"]["github_aeyeops"]["token"] == "ghp_live_value"
        # Non-placeholder fields are untouched.
        assert config["providers"]["github_aeyeops"]["url"] == "https://github.com"
        assert config["providers"]["github_aeyeops"]["user"] == "aeyeopsdev"

    def test_raw_config_cache_preserves_placeholder(
        self,
        isolated_config_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The raw config cache (used by save_config) keeps the literal `${VAR}`.

        Expansion happens on the plain-dict view only; the ruamel CommentedMap
        held in ``_raw_config_cache`` retains the placeholder text so that the
        save-side round-trip does not bake expanded secrets into the file.
        """
        monkeypatch.setenv("FOO", "expanded-secret")
        isolated_config_file.write_text(
            "providers:\n"
            "  demo:\n"
            "    url: https://github.com\n"
            "    token: ${FOO}\n"
            "global: {}\n",
            encoding="utf-8",
        )

        manager = ConfigurationManager()
        config = manager.load_config()
        # Expanded in-memory view.
        assert config["providers"]["demo"]["token"] == "expanded-secret"

        # Raw cache preserves the original placeholder verbatim.
        raw = manager._raw_config_cache
        assert raw is not None
        assert raw["providers"]["demo"]["token"] == "${FOO}"

    def test_save_config_round_trip_preserves_placeholder(
        self,
        isolated_config_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """save_config with an unchanged expanded value keeps the ``${VAR}`` literal.

        If the caller loads the config (which expands ``${FOO}`` in memory) and
        saves it back without touching the token, the on-disk file must still
        contain ``${FOO}`` and must not contain the expanded secret.
        """
        monkeypatch.setenv("FOO", "ghp_expanded")
        isolated_config_file.write_text(
            "providers:\n"
            "  demo:\n"
            "    url: https://github.com\n"
            "    user: aeyeopsdev\n"
            "    token: ${FOO}\n"
            "global:\n"
            "  default_provider: demo\n",
            encoding="utf-8",
        )

        manager = ConfigurationManager()
        loaded = manager.load_config()
        # Sanity: the caller sees the expanded value.
        assert loaded["providers"]["demo"]["token"] == "ghp_expanded"

        # Save the loaded (expanded) config back as-is.
        manager.save_config(loaded)

        disk = isolated_config_file.read_text(encoding="utf-8")
        assert "${FOO}" in disk
        assert "ghp_expanded" not in disk
        # Sibling fields survive unchanged.
        assert "user: aeyeopsdev" in disk
        assert "default_provider: demo" in disk

    def test_save_config_overwrites_placeholder_when_value_changes(
        self,
        isolated_config_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Mutating the expanded value in memory causes save_config to overwrite
        the ``${VAR}`` literal with the new literal on disk.
        """
        monkeypatch.setenv("FOO", "ghp_expanded")
        isolated_config_file.write_text(
            "providers:\n"
            "  demo:\n"
            "    url: https://github.com\n"
            "    user: aeyeopsdev\n"
            "    token: ${FOO}\n"
            "global:\n"
            "  default_provider: demo\n",
            encoding="utf-8",
        )

        manager = ConfigurationManager()
        loaded = manager.load_config()

        # Caller explicitly sets a brand-new token literal.
        loaded["providers"]["demo"]["token"] = "ghp_new_literal"
        manager.save_config(loaded)

        disk = isolated_config_file.read_text(encoding="utf-8")
        assert "ghp_new_literal" in disk
        assert "${FOO}" not in disk
        # The old expansion should not appear either.
        assert "ghp_expanded" not in disk
