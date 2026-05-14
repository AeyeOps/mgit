"""Unit tests for sync reporting helpers and unquoted-glob detection."""

from mgit.__main__ import app, build_unquoted_glob_error
from mgit.commands.sync import classify_dirty_repo, parse_porcelain_z


class TestParsePorcelainZ:
    """Test parse_porcelain_z parsing of `git status --porcelain -z` output."""

    def test_empty_output(self):
        assert parse_porcelain_z("") == set()

    def test_single_modified(self):
        assert parse_porcelain_z(" M dir/STATE.sql\x00") == {"dir/STATE.sql"}

    def test_multiple_entries(self):
        out = " M a.txt\x00?? b.txt\x00 D c.txt\x00"
        assert parse_porcelain_z(out) == {"a.txt", "b.txt", "c.txt"}

    def test_rename_record_uses_new_path(self):
        # Rename: "R  new\x00old\x00" — the source path token follows the record.
        out = "R  new.txt\x00old.txt\x00 M other.txt\x00"
        assert parse_porcelain_z(out) == {"new.txt", "other.txt"}

    def test_path_with_spaces(self):
        assert parse_porcelain_z(" M dir/file with spaces.sql\x00") == {
            "dir/file with spaces.sql"
        }


class TestClassifyDirtyRepo:
    """Test classify_dirty_repo case-collision classification."""

    def test_all_dirty_paths_collide(self):
        assert (
            classify_dirty_repo({"dir/STATE.sql"}, {"dir/STATE.sql", "dir/State.sql"})
            == "case_collision"
        )

    def test_some_dirty_paths_not_collisions(self):
        # Genuine edit alongside a collision -> still "dirty".
        assert (
            classify_dirty_repo(
                {"dir/STATE.sql", "src/main.py"},
                {"dir/STATE.sql", "dir/State.sql"},
            )
            == "dirty"
        )

    def test_no_collisions(self):
        assert classify_dirty_repo({"src/main.py"}, set()) == "dirty"

    def test_empty_dirty_paths(self):
        # Defensive: no changed paths should never classify as case_collision.
        assert classify_dirty_repo(set(), {"dir/STATE.sql"}) == "dirty"


class TestBuildUnquotedGlobError:
    """Test the actionable error message for unquoted glob expansion."""

    def test_mentions_arg_count_and_quoting(self):
        msg = build_unquoted_glob_error("a/b/c", "d/e/f", ["g/h/i", "j/k/l"])
        assert "4" in msg  # pattern + path + 2 extra
        assert "quote" in msg.lower()
        assert "mgit sync" in msg


class TestUnquotedGlobDetectionCLI:
    """Test sync command CLI behavior for unquoted glob expansion."""

    def test_three_positional_args_exits_2(self, cli_runner):
        result = cli_runner.invoke(app, ["sync", "a/b/c", "d/e/f", "g/h/i"])
        assert result.exit_code == 2
        assert "quote" in result.output.lower()

    def test_two_positional_args_not_tripped(self, cli_runner):
        # pattern + path is legitimate; detection must not fire. It will fail
        # later for other reasons (no provider/repos), but not with the
        # unquoted-glob message.
        result = cli_runner.invoke(app, ["sync", "no-such-org/*/*", "/tmp/mgit-x"])
        assert "expanded an unquoted" not in result.output
