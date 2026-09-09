"""Unit tests for git status porcelain parsing in DiffProcessor.

Covers C-quoted paths and rename/copy records, whose "old -> new" form and
octal-escaped quoting are easy to mis-split. Cases here were verified against
real `git status --porcelain` output.
"""

import os
import subprocess
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

    @pytest.mark.parametrize("filename", ["文件 x.txt", "ä x.txt", "😀 x.txt"])
    def test_literal_unicode(self, filename: str):
        """Literal Unicode stays intact when core.quotePath is false."""
        assert _unquote_git_path(f'"{filename}"') == filename

    def test_literal_unicode_with_octal_bytes(self):
        """Literal Unicode and escaped UTF-8 bytes can share a quoted path."""
        assert _unquote_git_path(r'"文件 \303\244.txt"') == "文件 ä.txt"

    @pytest.mark.parametrize(
        ("quoted_path", "filename"),
        [
            (r'"文件\tname.txt"', "文件\tname.txt"),
            (r'"ä\nname.txt"', "ä\nname.txt"),
            (r'"😀\"name.txt"', '😀"name.txt'),
            (r'"文件\\name.txt"', "文件\\name.txt"),
        ],
    )
    def test_literal_unicode_with_escaped_characters(
        self, quoted_path: str, filename: str
    ):
        """Git C escapes decode without changing adjacent literal Unicode."""
        assert _unquote_git_path(quoted_path) == filename


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


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("quote_path", ["false", "true"])
@pytest.mark.parametrize("filename", ["文件 x.txt", "ä x.txt", "😀 x.txt"])
async def test_detect_unicode_filename_in_real_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, quote_path: str, filename: str
):
    """Real Git paths reach change reporting and content embedding unchanged."""
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    hooks_path = tmp_path / "empty-hooks"
    hooks_path.mkdir()
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    def git(*args: str) -> None:
        subprocess.run(
            [
                "git",
                "-c",
                f"core.hooksPath={hooks_path}",
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@mgit.dev",
                *args,
            ],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "--initial-branch=main")
    git("config", "core.quotePath", quote_path)
    git("commit", "--allow-empty", "--no-gpg-sign", "-m", "Initial commit")
    content = "Unicode filename regression.\n"
    (repo_path / filename).write_text(content, encoding="utf-8")

    change = await DiffProcessor(embed_content=True)._detect_repository_changes(
        repo_path
    )

    assert change.error is None
    assert change.has_uncommitted_changes is True
    assert change.git_status == "dirty"
    assert len(change.uncommitted_files) == 1
    file_info = change.uncommitted_files[0]
    assert file_info["filename"] == filename
    assert file_info["change_type"] == "untracked"
    assert file_info["embedded_content"]["error"] is None
    assert content.strip() in file_info["embedded_content"]["content"]
