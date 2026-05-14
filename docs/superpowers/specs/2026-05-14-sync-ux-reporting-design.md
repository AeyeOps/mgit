# Sync UX: trustworthy reporting and footgun detection

**Date:** 2026-05-14
**Status:** Approved (recommendation A)

## Problem

Three gaps surfaced while debugging `mgit sync "*/*/*" --provider github_mm`:

1. **Silent unquoted-glob failure.** Running `mgit sync */*/*` (no quotes) lets the
   shell expand the wildcard against the cwd before mgit runs. mgit receives a
   dozen+ positional args and emits a confusing typer usage dump.
2. **Repos vanish from the summary.** Repos pre-filtered as dirty / non-git are
   warned about near the top of stdout, then never appear in the final tally.
   `success_count = len(repositories) - failures - skipped` is computed off the
   already-filtered list, so the end-of-run summary silently under-reports.
3. **Misleading "uncommitted changes" label.** A freshly-cloned repo containing
   two paths differing only in case (e.g. `dir/STATE.sql` and `dir/State.sql`)
   cannot check out cleanly on a case-insensitive filesystem. git reports it
   permanently modified; mgit calls it "uncommitted changes" and suggests
   `--force` (which does not help — it comes back dirty next run).

## Approach (recommendation A)

Case-collision classification is **symptom-based**: a dirty repo is classified
`case_collision` only when *every* dirty path is also a case-colliding tracked
path. If any dirty path is not collision-related, the repo stays `dirty`
(genuine user edits). The dirtiness itself is the evidence — no separate
filesystem case-sensitivity probe needed.

## Design

### 1. Unquoted-glob detection — `mgit/__main__.py`

Add a hidden variadic argument to `sync()`:
```python
extra: Optional[list[str]] = typer.Argument(None, hidden=True)
```
First thing in the body: if `extra` is non-empty, the call received 3+
positional args — impossible in a legitimate invocation (`pattern` + optional
`path`). Print an actionable error via a pure helper
`build_unquoted_glob_error(pattern, path, extra)` and `raise typer.Exit(code=2)`.
The error names the arg count and shows the quoted form. High-confidence only;
expansions to exactly 1–2 args are lossy and not detectable.

### 2. Case-collision classification — `mgit/git/utils.py` + `mgit/commands/sync.py`

- New `find_case_collisions(repo_path: Path) -> set[str]` in `git/utils.py`:
  runs `git ls-files -z`, groups tracked paths by lowercased form, returns
  every path belonging to a group with >1 member. Errors → empty set.
- New pure helpers in `sync.py`:
  - `parse_porcelain_z(stdout: str) -> set[str]` — parses
    `git status --porcelain -z` into the set of changed paths (handles
    rename/copy records).
  - `classify_dirty_repo(dirty_paths, collisions) -> str` — returns
    `"case_collision"` when `dirty_paths` is non-empty and a subset of
    `collisions`, else `"dirty"`.
- `analyze_repository_states` gains a `case_collision_repos` list on its
  `RepoAnalysis` result and uses the helpers to classify each dirty repo.

### 3. Summary completeness — `mgit/commands/sync.py`

- `sync_command` builds `pre_skipped: list[tuple[str, str]]` from
  `dirty_repos` (`"uncommitted changes"`), `case_collision_repos`
  (`"case-collision (cannot check out cleanly)"`), and `non_git_dirs`
  (`"not a git repository"`). These names are filtered out of `repositories`
  as before.
- A distinct warning block prints for `case_collision_repos` — explains the
  cause, does **not** suggest `--force`.
- `pre_skipped` is passed into `run_sync_with_progress` / `run_sync_quiet`.
  The final summary merges `processor.skipped + pre_skipped`, prints a
  per-reason breakdown, and prints `Total: N` which reconciles to the
  resolved repository count (`len(repositories_after_filter) + len(pre_skipped)`).
  A run with only pre-skipped repos (no failures, no in-run skips) now still
  shows the "completed with issues" summary instead of "Successfully
  synchronized N!".

## Testing

### Unit (`tests/unit/`)
- `test_git.py`: `find_case_collisions` — colliding index entries (built via
  `git update-index --cacheinfo` plumbing so it works on any filesystem),
  no-collision repo, non-git dir.
- `test_sync_reporting.py` (new): `parse_porcelain_z` (modified, rename,
  empty), `classify_dirty_repo` (pure subset / mixed / empty),
  `build_unquoted_glob_error`, and a `CliRunner` test that `sync a b c`
  exits 2 with the quote hint while `sync a b` does not trip detection.

### E2E (`tests/e2e/`, Docker + Gitea, runs against the built binary)
- New fixture `gitea_case_collision_repo`: creates a repo and adds two
  case-colliding files via the Gitea contents API (server-side, FS-independent).
- `test_sync_edge_cases.py`:
  - Case-collision: sync once, force one colliding path dirty (`cp` the sibling
    over it — deterministic on case-sensitive *and* case-insensitive hosts),
    sync again → output labels it case-collision, not "uncommitted changes";
    exit 0.
  - Summary reconciliation: sync a mix (normal + empty) twice → final summary's
    `Total` equals the resolved count and `success + skipped + failed == total`.
  - Unquoted-glob: invoke the binary with 3+ positional args → exit 2, stdout
    carries the quote hint.

## Threading / blast radius

`pre_skipped` is computed in `sync_command` and passed as one new keyword
argument to the two `run_sync_*` functions. `BulkOperationProcessor` is
unchanged. `sync_command`'s own signature is unchanged, so `__main__.py` only
gains the `extra` argument and the detection guard.
