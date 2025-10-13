#!/bin/bash

# mgit special characters regression test suite
# Tests handling of spaces, dots, dashes, and other special characters in patterns

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/mgit_special_chars_test.log"
TEST_DIR="$SCRIPT_DIR/../tmp/mgit_special_chars_test"

# Clear previous log
echo "=== mgit special characters test suite - $(date) ===" > "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Setup test environment
echo "=== SETUP: Creating test directories ===" | tee -a "$LOG_FILE"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
echo "--- SETUP COMPLETE ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 1: Repository names with dots ===" | tee -a "$LOG_FILE"
echo "Testing pattern: cstorepro/*/CStoreProMobileApp.API" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "cstorepro/*/CStoreProMobileApp.API" --provider bitbucket_pdi 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 1 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 2: Repository names with dashes ===" | tee -a "$LOG_FILE"
echo "Testing pattern: cstorepro/*/MobileApp-Server" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "cstorepro/*/MobileApp-Server" --provider bitbucket_pdi 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 2 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 3: Repository names with underscores ===" | tee -a "$LOG_FILE"
echo "Testing pattern: pdidev/*/automation_smoke_signals" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "pdidev/*/automation_smoke_signals" --provider ado_pdidev 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 3 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 4: Project names with spaces (URL encoding test) ===" | tee -a "$LOG_FILE"
echo "Testing pattern with space: pdidev/Blue Cow/*" | tee -a "$LOG_FILE"
echo "Note: Spaces in project names may require special API handling" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "pdidev/Blue Cow/*" --limit 3 --provider ado_pdidev 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 4 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 5: Project names with dashes ===" | tee -a "$LOG_FILE"
echo "Testing pattern: p97networks/Loyalty-Platform/*" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/Loyalty-Platform/*" --limit 3 --provider ado_p97 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 5 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 6: Repository names with mixed special chars ===" | tee -a "$LOG_FILE"
echo "Testing pattern: cstorepro/*/CSP-Admin" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "cstorepro/*/CSP-Admin" --provider bitbucket_pdi 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 6 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 7: Complex pattern with dots and dashes ===" | tee -a "$LOG_FILE"
echo "Testing: p97networks/*/Loyalty-*" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/*/Loyalty-*" --provider ado_p97 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 7 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 8: Pattern with all wildcards (cross-provider) ===" | tee -a "$LOG_FILE"
echo "Testing: */*/*-*" | tee -a "$LOG_FILE"
echo "Looking for any repo with a dash in the name" | tee -a "$LOG_FILE"
timeout 20s /opt/bin/mgit list "*/*/*-*" --provider bitbucket_pdi --limit 5 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 8 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 9: Testing numeric characters in patterns ===" | tee -a "$LOG_FILE"
echo "Testing pattern: p97networks/*/*" | tee -a "$LOG_FILE"
echo "Organization name contains numbers" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/*/*" --limit 3 --provider ado_p97 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 9 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 10: BitBucket long project names with dashes ===" | tee -a "$LOG_FILE"
echo "Testing: cstorepro/Rocket-To-Cosmos-Migration/*" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "cstorepro/Rocket-To-Cosmos-Migration/*" --provider bitbucket_pdi 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 10 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 11: Pattern matching with dots in wildcards ===" | tee -a "$LOG_FILE"
echo "Testing: */*/CStoreProMobileApp.*" | tee -a "$LOG_FILE"
echo "Looking for repos starting with 'CStoreProMobileApp.'" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "*/*/CStoreProMobileApp.*" --provider bitbucket_pdi --limit 3 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 11 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 12: Edge case - single character segments ===" | tee -a "$LOG_FILE"
echo "Testing single char wildcard: */*/?" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "*/*/?" --provider bitbucket_pdi --limit 2 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 12 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 13: Sync operation with special chars (dry-run) ===" | tee -a "$LOG_FILE"
echo "Testing sync with dots: p97networks/Loyalty-Platform/Loyalty-Settlement" | tee -a "$LOG_FILE"
timeout 20s /opt/bin/mgit sync "p97networks/Loyalty-Platform/Loyalty-Settlement" "$TEST_DIR/sync_test" --dry-run --provider ado_p97 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 13 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 14: Mixed case with special chars ===" | tee -a "$LOG_FILE"
echo "Testing: cstorepro/*/QBMapping" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "cstorepro/*/QBMapping" --provider bitbucket_pdi 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 14 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 15: Status check with special char repos ===" | tee -a "$LOG_FILE"
echo "Creating test repo with dots and dashes in name..." | tee -a "$LOG_FILE"
mkdir -p "$TEST_DIR/status_test"
cd "$TEST_DIR/status_test"
# Create repos with special characters in names
mkdir "repo.with.dots" && cd "repo.with.dots" && git init > /dev/null 2>&1
echo "test" > file.txt && git add . && git commit -m "init" > /dev/null 2>&1
cd ..
mkdir "repo-with-dashes" && cd "repo-with-dashes" && git init > /dev/null 2>&1
echo "test" > file.txt && git add . && git commit -m "init" > /dev/null 2>&1
cd ..
mkdir "repo_with_underscores" && cd "repo_with_underscores" && git init > /dev/null 2>&1
echo "test" > file.txt && git add . && git commit -m "init" > /dev/null 2>&1
echo "modified" >> file.txt  # Make it dirty
cd "$SCRIPT_DIR"
timeout 10s /opt/bin/mgit status "$TEST_DIR/status_test" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 15 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 16: Invalid characters that should still fail ===" | tee -a "$LOG_FILE"
echo "Testing with invalid chars: org/proj/repo|invalid" | tee -a "$LOG_FILE"
timeout 10s /opt/bin/mgit list "org/proj/repo|invalid" --provider ado_pdidev 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be non-zero)" | tee -a "$LOG_FILE"
echo "--- END TEST 16 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 17: URL special characters in clone URLs ===" | tee -a "$LOG_FILE"
echo "Testing if special chars in URLs are handled correctly" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/Card Present/Card Present Payment Host" --provider ado_p97 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 17 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 18: Consecutive special characters ===" | tee -a "$LOG_FILE"
echo "Looking for repos with multiple consecutive special chars" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "*/*/*.*.*" --provider bitbucket_pdi --limit 2 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "--- END TEST 18 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 19: Special chars in all three segments ===" | tee -a "$LOG_FILE"
echo "Testing: p97networks/Loyalty-Platform/Loyalty-Settlement" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/Loyalty-Platform/Loyalty-Settlement" --provider ado_p97 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
echo "Exit code: $EXIT_CODE (should be 0)" | tee -a "$LOG_FILE"
echo "--- END TEST 19 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 20: Performance test with complex patterns ===" | tee -a "$LOG_FILE"
echo "Testing complex pattern across providers: */*-*/*-*" | tee -a "$LOG_FILE"
echo "Looking for org-project-repo patterns with dashes" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)
timeout 20s /opt/bin/mgit list "*/*-*/*-*" --provider bitbucket_pdi --limit 5 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "Exit code: $EXIT_CODE, Time taken: ${ELAPSED}s" | tee -a "$LOG_FILE"
echo "--- END TEST 20 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Cleanup
echo "=== CLEANUP: Removing test directories ===" | tee -a "$LOG_FILE"
rm -rf "$TEST_DIR"
echo "--- CLEANUP COMPLETE ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== mgit special characters test suite completed at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo ""
echo "=== TEST RESULTS SUMMARY ==="
echo "✅ CHARACTERS TESTED:"
echo "  - Dots (.) in repository and project names"
echo "  - Dashes (-) in repository and project names"
echo "  - Underscores (_) in repository names"
echo "  - Spaces ( ) in project names"
echo "  - Numbers (0-9) in organization names"
echo "  - Mixed special characters combinations"
echo ""
echo "📊 OPERATIONS TESTED:"
echo "  - List with exact patterns"
echo "  - List with wildcard patterns"
echo "  - Sync operations (dry-run)"
echo "  - Status operations"
echo "  - Cross-provider searches"
echo "  - Invalid character rejection"
echo ""
echo "🔍 EDGE CASES COVERED:"
echo "  - Consecutive special characters"
echo "  - Single character segments"
echo "  - Long project names with multiple dashes"
echo "  - Mixed case with special characters"
echo "  - URL encoding requirements"
echo "  - Performance with complex patterns"
echo ""
echo "📁 Log file: $LOG_FILE"
echo "🔧 Binary location: /opt/bin/mgit"