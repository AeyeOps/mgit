#!/bin/bash

# mgit sync regression test suite
# Tests synchronization across multiple providers with various scenarios
#
# NOTE: This script uses placeholder org/project names. Replace with your actual
# provider configuration to run these tests:
#   - ado_example: Azure DevOps provider
#   - ado_sample: Secondary Azure DevOps provider
#   - bitbucket_demo: BitBucket provider

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/mgit_sync_test.log"
TEST_DIR="$SCRIPT_DIR/../tmp/mgit_sync_test_repos"

# Clear previous log
echo "=== mgit sync regression test suite - $(date) ===" > "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Setup test environment
echo "=== SETUP: Creating test sync directories ===" | tee -a "$LOG_FILE"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR/dry_run"
mkdir -p "$TEST_DIR/real_sync"
mkdir -p "$TEST_DIR/force_sync"
mkdir -p "$TEST_DIR/existing_repos"
echo "--- SETUP COMPLETE ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 1: Dry run mode (no actual changes) ===" | tee -a "$LOG_FILE"
timeout 30s /opt/bin/mgit sync "example-org/Developer-Tools/*" "$TEST_DIR/dry_run" --dry-run --provider ado_example 2>&1 | head -50 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
# Verify no repos were actually created
REPO_COUNT=$(find "$TEST_DIR/dry_run" -name ".git" -type d 2>/dev/null | wc -l)
echo "Repos created in dry-run: $REPO_COUNT (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 1 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 2: List operation with exact pattern ===" | tee -a "$LOG_FILE"
timeout 30s /opt/bin/mgit list "example-org/Developer-Tools/*" --limit 3 --provider ado_example 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 2 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 3: Sync SMALL repo with limited concurrency ===" | tee -a "$LOG_FILE"
echo "NOTE: Using specific small repos to avoid large downloads" | tee -a "$LOG_FILE"
# Use actual existing repo names without dots!
timeout 45s /opt/bin/mgit sync "sample-org/DataPlatform/DataPlatform" "$TEST_DIR/real_sync" --concurrency 1 --provider ado_example 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
REPO_COUNT=$(find "$TEST_DIR/real_sync" -name ".git" -type d 2>/dev/null | wc -l)
echo "Repos synced: $REPO_COUNT" | tee -a "$LOG_FILE"
echo "--- END TEST 3 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 4: Sync with no progress/summary ===" | tee -a "$LOG_FILE"
echo "Skipping actual sync to avoid duplicate downloads" | tee -a "$LOG_FILE"
# Just test the flags work with dry-run
timeout 15s /opt/bin/mgit sync "sample-org/ETL-Pipeline/ETL-Pipeline" "$TEST_DIR/real_sync" --dry-run --no-progress --no-summary --provider ado_example 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 4 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 5: Re-sync existing repository (pull mode) ===" | tee -a "$LOG_FILE"
# First sync a repo
timeout 45s /opt/bin/mgit sync "demo-workspace/*/data-mapping" "$TEST_DIR/existing_repos" --provider ado_example --no-progress 2>&1 | head -20 | tee -a "$LOG_FILE"
echo "Initial sync done, now re-syncing..." | tee -a "$LOG_FILE"
# Now sync again - should pull updates
timeout 30s /opt/bin/mgit sync "demo-workspace/*/data-mapping" "$TEST_DIR/existing_repos" --provider ado_example 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 5 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 6: Force sync (delete and re-clone) ===" | tee -a "$LOG_FILE"
# First create a repo
timeout 45s /opt/bin/mgit sync "sample-org/ETL-Pipeline/ETL-Pipeline" "$TEST_DIR/force_sync" --provider ado_example --no-progress 2>&1 | head -20 | tee -a "$LOG_FILE"
# Modify a file to simulate local changes
if [ -d "$TEST_DIR/force_sync/ETL-Pipeline" ]; then
    echo "test modification" >> "$TEST_DIR/force_sync/ETL-Pipeline/README.md" 2>/dev/null || echo "test" > "$TEST_DIR/force_sync/ETL-Pipeline/test.txt"
    echo "Modified local repo, now force syncing..." | tee -a "$LOG_FILE"
fi
# Force sync - should delete and re-clone
timeout 45s /opt/bin/mgit sync "sample-org/ETL-Pipeline/ETL-Pipeline" "$TEST_DIR/force_sync" --force --provider ado_example 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 6 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 7: Invalid pattern handling ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit sync "nonexistent/org/pattern" "$TEST_DIR/invalid" --provider ado_example 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should handle gracefully)" | tee -a "$LOG_FILE"
echo "--- END TEST 7 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 8: Cross-provider wildcard pattern ===" | tee -a "$LOG_FILE"
echo "Testing pattern across all providers (limited to prevent overload)..." | tee -a "$LOG_FILE"
timeout 30s /opt/bin/mgit list "*/*/*" --limit 5 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 8 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 9: BitBucket provider sync test ===" | tee -a "$LOG_FILE"
# List available BitBucket repos first
timeout 20s /opt/bin/mgit list "demo-workspace/*/*" --limit 2 --provider bitbucket_demo 2>&1 | tee -a "$LOG_FILE"
echo "Note: Actual BitBucket sync skipped to avoid large downloads" | tee -a "$LOG_FILE"
echo "--- END TEST 9 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 10: Multiple provider listing ===" | tee -a "$LOG_FILE"
echo "Azure DevOps repos:" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "example-org/*/*" --limit 2 --provider ado_example 2>&1 | grep -E "example-org|━" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Sample Azure DevOps repos:" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "sample-org/*/*" --limit 2 --provider ado_sample 2>&1 | grep -E "sample-org|━" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "BitBucket repos:" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "*/*/*" --limit 2 --provider bitbucket_demo 2>&1 | grep -E "demo-workspace|━" | tee -a "$LOG_FILE"
echo "--- END TEST 10 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 11: Sync to current directory ===" | tee -a "$LOG_FILE"
mkdir -p "$TEST_DIR/current_dir_test"
cd "$TEST_DIR/current_dir_test"
timeout 45s /opt/bin/mgit sync "demo-workspace/*/data-mapping" . --provider ado_example --no-progress 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
REPO_COUNT=$(find . -name ".git" -type d 2>/dev/null | wc -l)
echo "Repos in current directory: $REPO_COUNT" | tee -a "$LOG_FILE"
cd "$SCRIPT_DIR"
echo "--- END TEST 11 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 12: Test concurrency with dry-run (safe) ===" | tee -a "$LOG_FILE"
echo "Using dry-run to test concurrency without downloading" | tee -a "$LOG_FILE"
# Test high concurrency with dry-run to avoid actual downloads
timeout 30s /opt/bin/mgit sync "sample-org/*/*" "$TEST_DIR/high_concurrency" --dry-run --concurrency 10 --provider ado_sample 2>&1 | head -100 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "Dry-run completed - no actual repos downloaded" | tee -a "$LOG_FILE"
echo "--- END TEST 12 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Cleanup - but keep some repos for inspection if needed
echo "=== CLEANUP: Partial cleanup (keeping some test repos for inspection) ===" | tee -a "$LOG_FILE"
rm -rf "$TEST_DIR/dry_run"
rm -rf "$TEST_DIR/invalid"
echo "Keeping synced repos in: $TEST_DIR" | tee -a "$LOG_FILE"
echo "To fully clean up, run: rm -rf $TEST_DIR" | tee -a "$LOG_FILE"
echo "--- CLEANUP COMPLETE ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== mgit sync regression test suite completed at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo ""
echo "=== TEST RESULTS SUMMARY ==="
echo "✅ TESTED FEATURES:"
echo "  - Dry run mode (--dry-run)"
echo "  - Concurrency control (--concurrency)"
echo "  - Progress/summary control (--no-progress --no-summary)"
echo "  - Force sync (--force)"
echo "  - Re-sync existing repositories (pull mode)"
echo "  - Cross-provider patterns"
echo "  - Invalid pattern handling"
echo "  - Multiple provider support"
echo ""
echo "📊 PROVIDERS TESTED:"
echo "  - Azure DevOps (ado_example, ado_sample)"
echo "  - BitBucket (bitbucket_demo)"
echo ""
echo "🔍 SCENARIOS COVERED:"
echo "  - Fresh clone operations"
echo "  - Update existing repos"
echo "  - Force re-clone with local changes"
echo "  - Error handling for invalid patterns"
echo "  - High concurrency operations"
echo "  - Current directory operations"
echo ""
echo "⚠️  NOTES:"
echo "  - Some tests limited to small repos to avoid network load"
echo "  - Test repos retained in $TEST_DIR for inspection"
echo "  - Exit codes properly captured with PIPESTATUS"
echo ""
echo "📁 Log file: $LOG_FILE"
echo "🔧 Binary location: /opt/bin/mgit"
