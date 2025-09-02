#!/bin/bash

# Multi-Provider Search Verification Script
# This script will definitively prove whether multi-provider search works or not

set -e

echo "=== MULTI-PROVIDER SEARCH VERIFICATION ==="
echo "Date: $(date)"
echo "Working directory: $(pwd)"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[LOG]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to run mgit command with full logging
run_mgit() {
    local cmd="$1"
    local description="$2"
    
    echo
    echo "=========================================="
    echo "TEST: $description"
    echo "COMMAND: poetry run mgit $cmd"
    echo "=========================================="
    
    # Capture both stdout and stderr
    if eval "poetry run mgit $cmd" 2>&1; then
        echo "Command completed successfully"
    else
        local exit_code=$?
        error "Command failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to test individual provider connectivity
test_provider_connectivity() {
    local provider_name="$1"
    
    log "Testing connectivity for provider: $provider_name"
    
    # Try to list a small number of repos to test connectivity
    if run_mgit "list \"gas-buddy/*/*\" --provider $provider_name --limit 3" "Individual provider test: $provider_name"; then
        success "Provider $provider_name is accessible"
        return 0
    else
        error "Provider $provider_name failed connectivity test"
        return 1
    fi
}

# Function to count actual output lines (excluding headers/formatting)
count_results() {
    local output="$1"
    # Count lines that look like repository entries (contain '/')
    echo "$output" | grep -c '/' || echo "0"
}

# Main test execution
main() {
    log "Starting multi-provider search verification..."
    
    # Step 1: Show configuration
    echo
    echo "=== STEP 1: CONFIGURATION DISCOVERY ==="
    run_mgit "config --list" "List all configured providers"
    
    # Extract provider names from config list output
    echo
    log "Extracting provider names..."
    PROVIDERS=$(poetry run mgit config --list 2>/dev/null | grep -E '^  [a-z]' | sed 's/^  //' | cut -d' ' -f1)
    
    if [ -z "$PROVIDERS" ]; then
        error "No providers found in configuration!"
        exit 1
    fi
    
    echo "Found providers:"
    echo "$PROVIDERS" | while read -r provider; do
        echo "  - $provider"
    done
    
    # Step 2: Test individual provider connectivity
    echo
    echo "=== STEP 2: INDIVIDUAL PROVIDER CONNECTIVITY ==="
    WORKING_PROVIDERS=()
    
    echo "$PROVIDERS" | while read -r provider; do
        if [ -n "$provider" ]; then
            if test_provider_connectivity "$provider"; then
                echo "$provider" >> /tmp/working_providers.txt
            fi
        fi
    done
    
    # Read working providers from temp file (subshell issue workaround)
    if [ -f /tmp/working_providers.txt ]; then
        WORKING_PROVIDERS=($(cat /tmp/working_providers.txt))
        rm -f /tmp/working_providers.txt
    else
        error "No providers are working!"
        exit 1
    fi
    
    success "Working providers: ${WORKING_PROVIDERS[*]}"
    
    # Step 3: Test single-provider patterns (baseline)
    echo
    echo "=== STEP 3: SINGLE-PROVIDER BASELINE TESTS ==="
    
    for provider in "${WORKING_PROVIDERS[@]}"; do
        log "Testing single provider pattern for: $provider"
        
        # Test with explicit provider
        run_mgit "list \"*/*/*\" --provider $provider --limit 5" "Single provider with --provider: $provider"
    done
    
    # Step 4: Test multi-provider patterns 
    echo
    echo "=== STEP 4: MULTI-PROVIDER PATTERN TESTS ==="
    
    log "Testing wildcard pattern that should search ALL providers..."
    MULTI_OUTPUT=$(mktemp)
    
    # Capture output for analysis
    if poetry run mgit list "gas-buddy/*/*" --limit 10 2>&1 | tee "$MULTI_OUTPUT"; then
        MULTI_RESULT_COUNT=$(count_results "$(cat "$MULTI_OUTPUT")")
        log "Multi-provider search returned $MULTI_RESULT_COUNT results"
        
        # Check if output mentions multiple providers
        if grep -q "provider" "$MULTI_OUTPUT"; then
            success "Output mentions providers - good sign"
        else
            warning "Output doesn't mention providers - might only be using one"
        fi
        
        # Look for provider-specific indicators in output
        echo
        log "Analyzing output for provider-specific patterns..."
        
        if grep -q "github\.com" "$MULTI_OUTPUT"; then
            echo "  ✓ Found GitHub repositories"
        fi
        
        if grep -q "dev\.azure\.com" "$MULTI_OUTPUT"; then
            echo "  ✓ Found Azure DevOps repositories"
        fi
        
        if grep -q "bitbucket\.org" "$MULTI_OUTPUT"; then
            echo "  ✓ Found Bitbucket repositories"
        fi
        
    else
        error "Multi-provider search failed completely"
        rm -f "$MULTI_OUTPUT"
        exit 1
    fi
    
    # Step 5: Compare single vs multi results
    echo
    echo "=== STEP 5: RESULT COMPARISON ANALYSIS ==="
    
    SINGLE_TOTAL=0
    for provider in "${WORKING_PROVIDERS[@]}"; do
        SINGLE_OUTPUT=$(mktemp)
        if poetry run mgit list "*/*/*" --provider "$provider" --limit 20 2>&1 > "$SINGLE_OUTPUT"; then
            SINGLE_COUNT=$(count_results "$(cat "$SINGLE_OUTPUT")")
            log "Provider $provider returned $SINGLE_COUNT results"
            SINGLE_TOTAL=$((SINGLE_TOTAL + SINGLE_COUNT))
        fi
        rm -f "$SINGLE_OUTPUT"
    done
    
    log "Total from individual providers: $SINGLE_TOTAL"
    log "Total from multi-provider search: $MULTI_RESULT_COUNT"
    
    # Analysis
    if [ "$MULTI_RESULT_COUNT" -gt "$SINGLE_TOTAL" ]; then
        success "Multi-provider search returned MORE results than sum of individuals - this suggests it's working correctly with deduplication or different limits"
    elif [ "$MULTI_RESULT_COUNT" -eq "$SINGLE_TOTAL" ]; then
        success "Multi-provider search returned SAME as sum of individuals - likely working correctly"
    elif [ "$MULTI_RESULT_COUNT" -gt 0 ] && [ "$MULTI_RESULT_COUNT" -lt "$SINGLE_TOTAL" ]; then
        warning "Multi-provider search returned FEWER results than sum of individuals - might be limiting per provider or deduplicating"
    elif [ "$MULTI_RESULT_COUNT" -eq 0 ]; then
        error "Multi-provider search returned ZERO results - this is suspicious if individuals returned results"
    else
        warning "Unexpected result comparison - needs investigation"
    fi
    
    # Step 6: Test provider-specific patterns
    echo
    echo "=== STEP 6: PROVIDER-SPECIFIC PATTERN TESTS ==="
    
    # Test patterns that should only match specific providers
    run_mgit "list \"github*/*/*\" --limit 5" "GitHub-specific pattern test"
    run_mgit "list \"dev.azure*/*/*\" --limit 5" "Azure DevOps-specific pattern test"
    
    # Step 7: Verbose logging analysis
    echo
    echo "=== STEP 7: VERBOSE OUTPUT ANALYSIS ==="
    
    log "Re-running multi-provider search with maximum verbosity to analyze internal behavior..."
    
    VERBOSE_OUTPUT=$(mktemp)
    if poetry run mgit list "*/*/*" --limit 10 2>&1 | tee "$VERBOSE_OUTPUT"; then
        echo
        log "Analyzing verbose output for provider activity..."
        
        # Check for signs of multiple provider activity
        if grep -i "provider" "$VERBOSE_OUTPUT" | head -10; then
            echo "Found provider-related log entries above"
        else
            warning "No provider-related entries found in verbose output"
        fi
        
        # Check for authentication/connection messages
        if grep -i "auth\|connect\|login" "$VERBOSE_OUTPUT"; then
            echo "Found authentication/connection activity above"
        else
            warning "No authentication activity visible in logs"
        fi
        
        # Check for concurrent/async activity indicators
        if grep -i "concurrent\|async\|session" "$VERBOSE_OUTPUT"; then
            echo "Found concurrency indicators above"
        else
            warning "No concurrency indicators found"
        fi
    fi
    
    rm -f "$VERBOSE_OUTPUT" "$MULTI_OUTPUT"
    
    # Final verdict
    echo
    echo "=========================================="
    echo "=== FINAL VERDICT ==="
    echo "=========================================="
    
    if [ "$MULTI_RESULT_COUNT" -gt 0 ] && [ "${#WORKING_PROVIDERS[@]}" -gt 1 ]; then
        if [ "$MULTI_RESULT_COUNT" -ge "$SINGLE_TOTAL" ] || [ "$SINGLE_TOTAL" -eq 0 ]; then
            success "VERDICT: Multi-provider search appears to be WORKING"
            echo "Evidence:"
            echo "  - Multiple providers are configured and accessible"
            echo "  - Multi-provider pattern returned results"
            echo "  - Result counts are reasonable compared to individual provider totals"
        else
            warning "VERDICT: Multi-provider search is PARTIALLY WORKING but may have issues"
            echo "Concerns:"
            echo "  - Multi-provider returned fewer results than expected"
            echo "  - May not be searching all configured providers"
        fi
    elif [ "$MULTI_RESULT_COUNT" -eq 0 ] && [ "$SINGLE_TOTAL" -gt 0 ]; then
        error "VERDICT: Multi-provider search is BROKEN"
        echo "Evidence:"
        echo "  - Individual providers return results"
        echo "  - Multi-provider pattern returns zero results"
        echo "  - This indicates the wildcard logic is not working"
    elif [ "${#WORKING_PROVIDERS[@]}" -eq 1 ]; then
        warning "VERDICT: Cannot test multi-provider - only one provider available"
        echo "Note: Only one working provider found, so multi-provider search cannot be properly tested"
    else
        error "VERDICT: Inconclusive - insufficient data"
        echo "Unable to determine status due to lack of working providers or other issues"
    fi
    
    echo
    log "Test completed. Review the detailed output above for full analysis."
}

# Run the main function
main "$@"