#!/bin/bash

# mgit status regression test suite
# Tests various scenarios for repository status checking

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/mgit_status_test.log"
TEST_DIR="$SCRIPT_DIR/tmp/mgit_status_test_repos"

# Clear previous log
echo "=== mgit status regression test suite - $(date) ===" > "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Setup test environment
echo "=== SETUP: Creating test repository structure ===" | tee -a "$LOG_FILE"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

# Create test repos with different states
echo "Creating test repositories..." | tee -a "$LOG_FILE"

# Repo 1: Clean repository
mkdir -p "$TEST_DIR/clean_repo"
cd "$TEST_DIR/clean_repo"
git init > /dev/null 2>&1
echo "test" > file.txt
git add file.txt
git commit -m "Initial commit" > /dev/null 2>&1

# Repo 2: Repository with uncommitted changes
mkdir -p "$TEST_DIR/dirty_repo"
cd "$TEST_DIR/dirty_repo"
git init > /dev/null 2>&1
echo "test" > file.txt
git add file.txt
git commit -m "Initial commit" > /dev/null 2>&1
echo "modified" >> file.txt

# Repo 3: Repository with untracked files
mkdir -p "$TEST_DIR/untracked_repo"
cd "$TEST_DIR/untracked_repo"
git init > /dev/null 2>&1
echo "test" > file.txt
git add file.txt
git commit -m "Initial commit" > /dev/null 2>&1
echo "new file" > untracked.txt

# Repo 4: Repository with staged changes
mkdir -p "$TEST_DIR/staged_repo"
cd "$TEST_DIR/staged_repo"
git init > /dev/null 2>&1
echo "test" > file.txt
git add file.txt
git commit -m "Initial commit" > /dev/null 2>&1
echo "staged changes" > staged.txt
git add staged.txt

# Repo 5: Mixed state repository
mkdir -p "$TEST_DIR/mixed_repo"
cd "$TEST_DIR/mixed_repo"
git init > /dev/null 2>&1
echo "test" > file.txt
git add file.txt
git commit -m "Initial commit" > /dev/null 2>&1
echo "staged" > staged.txt
git add staged.txt
echo "modified" >> file.txt
echo "untracked" > untracked.txt

# Repo 6: Non-git directory
mkdir -p "$TEST_DIR/not_a_repo"
echo "just a file" > "$TEST_DIR/not_a_repo/file.txt"

cd /opt/aeo/mgit
echo "--- SETUP COMPLETE ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 1: Basic status check (default - show only dirty) ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status "$TEST_DIR" 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 1 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 2: Show all repositories including clean ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status "$TEST_DIR" --show-clean 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 2 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 3: JSON output format ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status "$TEST_DIR" --output json 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 3 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 4: Limited concurrency (sequential processing) ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status "$TEST_DIR" --concurrency 1 --show-clean 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 4 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 5: Fail on dirty repositories ===" | tee -a "$LOG_FILE"
# Use PIPESTATUS to get the exit code of mgit, not tee
timeout 10s /opt/bin/mgit status "$TEST_DIR" --fail-on-dirty 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}  # Get exit code from first command in pipeline (timeout/mgit)
echo "Exit code: $EXIT_CODE (should be non-zero due to dirty repos)" | tee -a "$LOG_FILE"
echo "--- END TEST 5 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 6: Status of current directory (mgit repo itself) ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status . 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 6 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 7: Status with high concurrency ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status "$TEST_DIR" --concurrency 20 --show-clean 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 7 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 8: Empty directory (no repos) ===" | tee -a "$LOG_FILE"
mkdir -p "$TEST_DIR/empty_dir"
timeout 10s /opt/bin/mgit status "$TEST_DIR/empty_dir" 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 8 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 9: Single repository status ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status "$TEST_DIR/dirty_repo" 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 9 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 10: Nested repositories ===" | tee -a "$LOG_FILE"
# Create a repo within a repo
mkdir -p "$TEST_DIR/parent_repo"
cd "$TEST_DIR/parent_repo"
git init > /dev/null 2>&1
echo "parent" > file.txt
git add file.txt
git commit -m "Parent commit" > /dev/null 2>&1
mkdir nested
cd nested
git init > /dev/null 2>&1
echo "nested" > file.txt
git add file.txt
git commit -m "Nested commit" > /dev/null 2>&1
echo "change" >> file.txt
cd /opt/aeo/mgit
timeout 10s /opt/bin/mgit status "$TEST_DIR/parent_repo" --show-clean 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 10 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Real-world test with actual repos
echo "=== TEST 11: Real repositories in home directory ===" | tee -a "$LOG_FILE"
if [ -d "$HOME/repos" ]; then
    timeout 15s /opt/bin/mgit status "$HOME/repos" --output json 2>&1 | head -50 | tee -a "$LOG_FILE"
else
    echo "No $HOME/repos directory found, skipping real-world test" | tee -a "$LOG_FILE"
fi
echo "--- END TEST 11 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 12: Status with table format (explicit) ===" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit status "$TEST_DIR" --output table --show-clean 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 12 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Cleanup
echo "=== CLEANUP: Removing test repositories ===" | tee -a "$LOG_FILE"
rm -rf "$TEST_DIR"
echo "--- CLEANUP COMPLETE ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== mgit status regression test suite completed at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo ""
echo "=== TEST RESULTS SUMMARY ==="
echo "✅ TESTED FEATURES:"
echo "  - Basic status checking (dirty repos only)"
echo "  - Show all repositories with --show-clean"
echo "  - JSON output format with --output json"
echo "  - Concurrency control with --concurrency"
echo "  - Exit code control with --fail-on-dirty"
echo "  - Single and multiple repository scanning"
echo "  - Nested repository handling"
echo "  - Empty directory handling"
echo ""
echo "📊 REPOSITORY STATES TESTED:"
echo "  - Clean repositories"
echo "  - Repositories with uncommitted changes"
echo "  - Repositories with untracked files"Do they need an interaction or do they run autonomously? 
echo "  - Repositories with staged changes"
echo "  - Mixed state repositories"
echo "  - Non-git directories"
echo ""
echo "📁 Log file: $LOG_FILE"
echo "🔧 Binary location: /opt/bin/mgit"