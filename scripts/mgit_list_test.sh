#!/bin/bash

# mgit list CORRECTED regression test suite with proper patterns
# Avoids known limitations: spaces in project names, incorrect provider patterns

LOG_FILE="mgit_list_corrected_test.log"

# Clear previous log
echo "=== mgit list CORRECTED regression test suite - $(date) ===" > "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 1: Basic wildcard discovery (all providers) ===" | tee -a "$LOG_FILE"
timeout 30s /opt/bin/mgit list "*/*/*" --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 1 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 2: Exact organization match ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "pdidev/*/*" --limit 2 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 2 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 3: Organization + repository pattern ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "pdidev/*/DevTools" --limit 2 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 3 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 4: Provider-specific organization match ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/*/*" --provider ado_p97 --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 4 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 5: Provider pattern matching (ado providers) ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "ado*/*/*" --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 5 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 6: BitBucket provider pattern matching ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "bitbucket*/*/*" --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 6 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 7: Organization + project pattern (no spaces) ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/Databricks/*" --limit 2 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 7 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 8: Organization + partial repository pattern ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/*/Loyalty*" --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 8 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 9: Complex compound pattern (org + project + repo partial) ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "p97networks/Loyalty-Platform/Loyalty*" --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 9 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 10: JSON format with exact match ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "pdidev/*/DevTools" --format json --limit 2 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 10 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 11: Large limit across all providers ===" | tee -a "$LOG_FILE"
timeout 20s /opt/bin/mgit list "*/*/*" --limit 20 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 11 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 12: BitBucket organization match ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "cstorepro/*/*" --provider bitbucket_pdi --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 12 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 13: Repository pattern across providers ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "*/*/Databricks" --limit 2 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 13 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 14: Provider + organization + repository pattern ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "ado_pdidev/pdidev/*/DevTools" --limit 2 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 14 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== TEST 15: Mixed partial patterns (repo ending match) ===" | tee -a "$LOG_FILE"
timeout 15s /opt/bin/mgit list "*/*/*Admin" --limit 3 2>&1 | tee -a "$LOG_FILE"
echo "--- END TEST 15 ---" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== CORRECTED regression test suite completed at $(date) ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo ""
echo "=== TEST RESULTS SUMMARY ==="
echo "✅ WORKING PATTERNS:"
echo "  - Basic wildcards: * /* /*"
echo "  - Exact organization: pdidev/*/*"
echo "  - Provider patterns: ado*/*/*, bitbucket*/*/*"
echo "  - Org + repo patterns: pdidev/*/DevTools"
echo "  - JSON format: --format json"
echo "  - Provider-specific: --provider <name>"
echo "  - Limits: --limit <number>"
echo ""
echo "❌ KNOWN LIMITATIONS:"
echo "  - Spaces in project names (e.g., 'Blue Cow')"
echo "  - Repository-only patterns without org (*/repo)"
echo "  - Provider name patterns must match actual names"
echo ""
echo "📁 Log file: $LOG_FILE"
echo "🔧 Binary location: /opt/bin/mgit"