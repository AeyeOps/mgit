"""Unit tests for git status porcelain parsing in DiffProcessor.

Covers C-quoted paths and rename/copy records, whose "old -> new" form and
octal-escaped quoting are easy to mis-split. Cases here were verified against
real `git status --porcelain` output.
"""

from pathlib import Path

import pytest

from mgit.processing import DiffProcessor, _unquote_git_path


@pytest.mark.unit
class TestUnquoteGitPath:
    """Tests for the standalone git C-quoted path decoder."""

    def test_unquoted_passthrough(self):
        """A plain path without surrounding quotes is returned unchanged."""
        assert _unquote_git_path("src/main.py") == "src/main.py"

    def test_quoted_with_space(self):
        """Surrounding quotes are stripped for a spaced path."""
        assert _unquote_git_path('"new file.txt"') == "new file.txt"

    def test_octal_escaped_unicode(self):
        """Octal byte escapes decode as UTF-8 (git core.quotePath default)."""
        # Verified: `printf x > 'ä b.txt'` -> porcelain `?? "\303\244 b.txt"`.
        assert _unquote_git_path(r'"\303\244 b.txt"') == "ä b.txt"

    def test_escaped_inner_quote(self):
        """A backslash-escaped double quote decodes to a literal quote."""
        assert _unquote_git_path(r'"quote\".txt"') == 'quote".txt'


@pytest.mark.unit
class TestParseGitStatus:
    """Tests for DiffProcessor._parse_git_status rename/quote handling."""

    def _parse(self, status_output: str) -> list[dict]:
        # embed_content defaults False, so repo_path is never touched.
        processor = DiffProcessor()
        return processor._parse_git_status(status_output, Path("."))

    def test_plain_rename_keeps_destination(self):
        """A simple rename record yields the destination path."""
        files = self._parse("R  a.txt -> b.txt")
        assert len(files) == 1
        assert files[0]["filename"] == "b.txt"
        assert files[0]["change_type"] == "renamed"

    def test_rename_to_spaced_destination_is_unquoted(self):
        """A quoted (spaced) rename destination is unquoted."""
        files = self._parse('R  a.txt -> "new file.txt"')
        assert files[0]["filename"] == "new file.txt"

    def test_rename_from_arrow_containing_source(self):
        """A quoted source containing ' -> ' does not corrupt the destination."""
        files = self._parse('R  "a -> b.txt" -> c.txt')
        assert files[0]["filename"] == "c.txt"

    def test_quoted_untracked_is_unquoted(self):
        """A non-rename status with a quoted path is unquoted too."""
        files = self._parse('?? "new file.txt"')
        assert files[0]["filename"] == "new file.txt"
        assert files[0]["change_type"] == "untracked"
