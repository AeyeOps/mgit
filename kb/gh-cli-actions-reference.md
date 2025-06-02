# GitHub CLI (gh) Actions Reference for LLM Context

## Table of Contents
1. [Installation and Authentication](#installation-and-authentication)
2. [Workflow Management Commands](#workflow-management-commands)
3. [Run Management Commands](#run-management-commands)
4. [Artifacts Management](#artifacts-management)
5. [Secrets Management](#secrets-management)
6. [Environment Management](#environment-management)
7. [Logs and Debugging](#logs-and-debugging)
8. [Workflow Dispatch](#workflow-dispatch)
9. [Advanced Filtering and Queries](#advanced-filtering-and-queries)
10. [JSON Output and Scripting](#json-output-and-scripting)
11. [Integration with jq](#integration-with-jq)
12. [Automation Scripts](#automation-scripts)
13. [Best Practices](#best-practices)
14. [Common Patterns for mgit](#common-patterns-for-mgit)

## Installation and Authentication

### Installing GitHub CLI
```bash
# macOS
brew install gh

# Windows
winget install --id GitHub.cli

# Linux (Debian/Ubuntu)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### Authentication
```bash
# Interactive authentication
gh auth login

# Non-interactive with token
echo $GITHUB_TOKEN | gh auth login --with-token

# Check authentication status
gh auth status

# Switch between accounts
gh auth switch

# Logout
gh auth logout
```

## Workflow Management Commands

### List Workflows
```bash
# List all workflows
gh workflow list

# List with additional details
gh workflow list --all

# List only active workflows
gh workflow list --state active

# List disabled workflows
gh workflow list --state disabled

# Limit results
gh workflow list --limit 10

# JSON output
gh workflow list --json id,name,state,path
```

### View Workflow Details
```bash
# View workflow by name
gh workflow view "CI/CD Pipeline"

# View workflow by ID
gh workflow view 1234567

# View workflow by file
gh workflow view .github/workflows/ci.yml

# View YAML content
gh workflow view "CI/CD Pipeline" --yaml

# View as JSON
gh workflow view "CI/CD Pipeline" --json
```

### Enable/Disable Workflows
```bash
# Enable workflow
gh workflow enable "CI/CD Pipeline"
gh workflow enable 1234567
gh workflow enable .github/workflows/ci.yml

# Disable workflow
gh workflow disable "CI/CD Pipeline"
gh workflow disable 1234567
gh workflow disable .github/workflows/ci.yml
```

### Run Workflows
```bash
# Run workflow (requires workflow_dispatch trigger)
gh workflow run "Manual Deploy"

# Run with inputs
gh workflow run "Deploy" -f environment=production -f debug=true

# Run specific workflow file
gh workflow run .github/workflows/deploy.yml

# Run on specific branch
gh workflow run "CI/CD Pipeline" --ref feature/new-feature

# Run with raw JSON inputs
echo '{"environment":"staging","version":"1.2.3"}' | gh workflow run deploy.yml --json
```

## Run Management Commands

### List Runs
```bash
# List recent runs
gh run list

# List runs for specific workflow
gh run list --workflow "CI/CD Pipeline"
gh run list --workflow ci.yml
gh run list --workflow 1234567

# Filter by branch
gh run list --branch main
gh run list --branch feature/new-feature

# Filter by event
gh run list --event push
gh run list --event pull_request
gh run list --event workflow_dispatch

# Filter by status
gh run list --status completed
gh run list --status in_progress
gh run list --status queued
gh run list --status failure
gh run list --status success

# Filter by actor
gh run list --user octocat

# Combine filters
gh run list --branch main --status failure --workflow "Tests"

# Limit and JSON output
gh run list --limit 20 --json databaseId,displayTitle,status,conclusion,workflowName,headBranch,event,createdAt

# Include all runs (not just recent)
gh run list --all
```

### View Run Details
```bash
# View run by ID
gh run view 1234567890

# View latest run
gh run view

# View specific job in run
gh run view 1234567890 --job 9876543210

# View as JSON
gh run view 1234567890 --json

# View web URL
gh run view 1234567890 --web

# Exit with run's exit code
gh run view 1234567890 --exit-status
```

### Watch Runs
```bash
# Watch a run in progress
gh run watch 1234567890

# Watch latest run
gh run watch

# Watch and exit with run's exit code
gh run watch 1234567890 --exit-status

# Watch with interval (seconds)
gh run watch --interval 10
```

### Rerun Workflows
```bash
# Rerun all jobs
gh run rerun 1234567890

# Rerun only failed jobs
gh run rerun 1234567890 --failed

# Rerun specific job
gh run rerun 1234567890 --job 9876543210

# Rerun with debug logging enabled
gh run rerun 1234567890 --debug
```

### Cancel Runs
```bash
# Cancel a run
gh run cancel 1234567890

# Cancel latest run
gh run cancel

# Cancel all runs for a branch
gh run list --branch feature/test --json databaseId -q ".[].databaseId" | xargs -I {} gh run cancel {}
```

### Delete Runs
```bash
# Delete a run
gh run delete 1234567890

# Delete without confirmation
gh run delete 1234567890 --confirm

# Delete multiple runs
gh run list --status completed --limit 100 --json databaseId -q ".[].databaseId" | xargs -I {} gh run delete {} --confirm
```

### Download Run Logs
```bash
# Download logs for a run
gh run download 1234567890

# Download to specific directory
gh run download 1234567890 --dir ./logs

# Download specific artifact
gh run download 1234567890 --name coverage-report

# List artifacts without downloading
gh run download 1234567890 --list
```

## Artifacts Management

### List Artifacts
```bash
# List artifacts for a repository
gh api repos/{owner}/{repo}/actions/artifacts --jq '.artifacts[] | {id, name, size_in_bytes, expired, created_at}'

# List artifacts for a specific run
gh run view 1234567890 --json artifacts --jq '.artifacts[]'

# List with size in MB
gh api repos/{owner}/{repo}/actions/artifacts --jq '.artifacts[] | {name, size_mb: (.size_in_bytes / 1048576 | round)}'
```

### Download Artifacts
```bash
# Download all artifacts from a run
gh run download 1234567890

# Download specific artifact
gh run download 1234567890 --name my-artifact

# Download to specific path
gh run download 1234567890 --name my-artifact --dir ./artifacts

# Download latest run artifacts
gh run download
```

### Delete Artifacts
```bash
# Delete artifact by ID
gh api -X DELETE repos/{owner}/{repo}/actions/artifacts/{artifact_id}

# Delete all artifacts older than 30 days
gh api repos/{owner}/{repo}/actions/artifacts --jq '.artifacts[] | select(.created_at | fromdateiso8601 < (now - 30*24*60*60)) | .id' | \
  xargs -I {} gh api -X DELETE repos/{owner}/{repo}/actions/artifacts/{}

# Delete artifacts by name pattern
gh api repos/{owner}/{repo}/actions/artifacts --jq '.artifacts[] | select(.name | test("temp-")) | .id' | \
  xargs -I {} gh api -X DELETE repos/{owner}/{repo}/actions/artifacts/{}
```

## Secrets Management

### Repository Secrets
```bash
# List repository secrets
gh secret list

# Set a secret
gh secret set MY_SECRET

# Set from file
gh secret set MY_SECRET < secret.txt

# Set with value
echo "secret-value" | gh secret set MY_SECRET

# Delete a secret
gh secret delete MY_SECRET

# Set for specific environment
gh secret set MY_SECRET --env production

# Set from env var
gh secret set MY_SECRET --body "$MY_ENV_VAR"
```

### Organization Secrets
```bash
# List organization secrets
gh api orgs/{org}/actions/secrets --jq '.secrets[] | {name, created_at, updated_at}'

# Create org secret (visible to all repos)
gh api -X PUT orgs/{org}/actions/secrets/MY_SECRET \
  -f encrypted_value="$(echo -n "secret-value" | gh api orgs/{org}/actions/secrets/public-key --jq -r '.key' | base64 -d | openssl rsautl -encrypt -pubin | base64)" \
  -f visibility="all"

# Create org secret (visible to selected repos)
gh api -X PUT orgs/{org}/actions/secrets/MY_SECRET \
  -f encrypted_value="..." \
  -f visibility="selected" \
  -f selected_repository_ids="[1234,5678]"
```

## Environment Management

### List Environments
```bash
# List environments
gh api repos/{owner}/{repo}/environments --jq '.environments[] | {name, protection_rules}'

# Get specific environment
gh api repos/{owner}/{repo}/environments/{environment_name}
```

### Environment Secrets
```bash
# List environment secrets
gh api repos/{owner}/{repo}/environments/{environment_name}/secrets

# Set environment secret
gh api -X PUT repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name} \
  -f encrypted_value="..." \
  -f key_id="..."
```

### Environment Protection Rules
```bash
# Get environment protection rules
gh api repos/{owner}/{repo}/environments/{environment_name}/protection-rules

# Add required reviewers
gh api -X POST repos/{owner}/{repo}/environments/{environment_name}/protection-rules \
  -f type="required_reviewers" \
  -f reviewers="[{\"type\":\"User\",\"id\":1234}]"

# Add wait timer
gh api -X POST repos/{owner}/{repo}/environments/{environment_name}/protection-rules \
  -f type="wait_timer" \
  -f wait_timer=30
```

## Logs and Debugging

### View Logs
```bash
# View logs for a run
gh run view 1234567890 --log

# View logs for failed steps only
gh run view 1234567890 --log-failed

# View specific job logs
gh run view 1234567890 --job 9876543210 --log

# Download logs
gh api repos/{owner}/{repo}/actions/runs/{run_id}/logs -H "Accept: application/vnd.github.v3+json" > logs.zip
```

### Debug Mode
```bash
# Rerun with debug logging
gh run rerun 1234567890 --debug

# Enable debug logging for new runs
gh secret set ACTIONS_RUNNER_DEBUG --body true
gh secret set ACTIONS_STEP_DEBUG --body true
```

### View Workflow Usage
```bash
# Get workflow usage statistics
gh api repos/{owner}/{repo}/actions/workflows/{workflow_id}/timing

# Get billable minutes
gh api repos/{owner}/{repo}/actions/workflows/{workflow_id}/timing --jq '.billable | to_entries[] | "\(.key): \(.value.total_ms / 60000) minutes"'
```

## Workflow Dispatch

### Simple Dispatch
```bash
# Trigger workflow
gh workflow run deploy.yml

# With branch
gh workflow run deploy.yml --ref develop

# With inputs
gh workflow run deploy.yml -f environment=staging -f version=1.2.3
```

### Complex Dispatch Examples
```bash
# Deploy with multiple inputs
gh workflow run deploy.yml \
  -f environment=production \
  -f version=$(git describe --tags --abbrev=0) \
  -f debug=false \
  -f regions='["us-east-1","eu-west-1"]'

# Trigger and wait for completion
run_id=$(gh workflow run test.yml --ref feature/branch -f test_suite=integration 2>&1 | grep -oP '\d{10}')
gh run watch $run_id --exit-status

# Batch trigger workflows
for branch in $(git branch -r | grep -E "release/"); do
  gh workflow run security-scan.yml --ref "${branch#origin/}"
done
```

## Advanced Filtering and Queries

### Complex JQ Queries
```bash
# Get failed runs with details
gh run list --status failure --json displayTitle,headBranch,event,conclusion,createdAt,databaseId | \
  jq -r '.[] | "\(.createdAt) | \(.databaseId) | \(.displayTitle) | \(.headBranch)"'

# Get workflow run duration
gh run list --limit 10 --json databaseId,displayTitle,createdAt,updatedAt | \
  jq -r '.[] | {
    id: .databaseId,
    title: .displayTitle,
    duration_minutes: (((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 60 | round)
  }'

# Get runs grouped by conclusion
gh run list --limit 100 --json conclusion | jq -r 'group_by(.conclusion) | map({conclusion: .[0].conclusion, count: length})'

# Find long-running workflows
gh run list --limit 50 --json databaseId,displayTitle,createdAt,updatedAt,status | \
  jq -r '.[] | select(.status == "completed") | {
    id: .databaseId,
    title: .displayTitle,
    duration_minutes: (((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 60 | round)
  } | select(.duration_minutes > 30)'
```

### Repository Statistics
```bash
# Get daily run counts
gh run list --limit 200 --json createdAt,conclusion | \
  jq -r 'group_by(.createdAt[0:10]) | map({
    date: .[0].createdAt[0:10],
    total: length,
    success: (map(select(.conclusion == "success")) | length),
    failure: (map(select(.conclusion == "failure")) | length)
  })'

# Average run duration by workflow
gh run list --limit 100 --json workflowName,createdAt,updatedAt | \
  jq -r 'group_by(.workflowName) | map({
    workflow: .[0].workflowName,
    avg_duration_min: (map(((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 60) | add / length | round)
  })'
```

## JSON Output and Scripting

### Workflow Automation Scripts
```bash
#!/bin/bash
# Monitor workflow health

check_workflow_health() {
  local workflow_name=$1
  local failure_threshold=$2
  
  recent_runs=$(gh run list --workflow "$workflow_name" --limit 10 --json conclusion)
  failure_count=$(echo "$recent_runs" | jq '[.[] | select(.conclusion == "failure")] | length')
  
  if [ "$failure_count" -gt "$failure_threshold" ]; then
    echo "WARNING: $workflow_name has $failure_count failures in last 10 runs"
    return 1
  fi
  return 0
}

# Check all workflows
for workflow in $(gh workflow list --json name -q '.[].name'); do
  check_workflow_health "$workflow" 3
done
```

### Artifact Management Script
```bash
#!/bin/bash
# Clean old artifacts

DAYS_TO_KEEP=7
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

echo "Cleaning artifacts older than $DAYS_TO_KEEP days..."

gh api "repos/$REPO/actions/artifacts" --paginate --jq '.artifacts[]' | \
  jq -r "select(.created_at | fromdateiso8601 < (now - $DAYS_TO_KEEP * 24 * 60 * 60)) | .id" | \
  while read -r artifact_id; do
    echo "Deleting artifact $artifact_id"
    gh api -X DELETE "repos/$REPO/actions/artifacts/$artifact_id"
  done
```

### Workflow Performance Report
```bash
#!/bin/bash
# Generate workflow performance report

generate_performance_report() {
  echo "# Workflow Performance Report"
  echo "Generated: $(date)"
  echo ""
  
  # Get all workflows
  workflows=$(gh workflow list --json id,name,path)
  
  echo "$workflows" | jq -r '.[] | "## \(.name)\n"' | while IFS= read -r line; do
    echo "$line"
    if [[ $line == "##"* ]]; then
      workflow_name=${line#"## "}
      
      # Get last 20 runs for this workflow
      stats=$(gh run list --workflow "$workflow_name" --limit 20 --json createdAt,updatedAt,conclusion | \
        jq -r '{
          total_runs: length,
          successful_runs: [.[] | select(.conclusion == "success")] | length,
          failed_runs: [.[] | select(.conclusion == "failure")] | length,
          avg_duration_min: (map(((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 60) | add / length | round),
          success_rate: (([.[] | select(.conclusion == "success")] | length) / length * 100 | round)
        }')
      
      echo "- Total runs: $(echo "$stats" | jq -r .total_runs)"
      echo "- Success rate: $(echo "$stats" | jq -r .success_rate)%"
      echo "- Average duration: $(echo "$stats" | jq -r .avg_duration_min) minutes"
      echo ""
    fi
  done
}

generate_performance_report > workflow_performance_report.md
```

## Integration with jq

### Common jq Patterns for GitHub Actions
```bash
# Extract specific fields
gh run list --json databaseId,displayTitle,conclusion | jq -r '.[] | "\(.databaseId)\t\(.displayTitle)\t\(.conclusion)"'

# Filter and transform
gh run list --json workflowName,headBranch,conclusion | \
  jq -r '.[] | select(.conclusion == "failure") | {workflow: .workflowName, branch: .headBranch}'

# Aggregate data
gh run list --limit 100 --json workflowName,conclusion | \
  jq -r 'group_by(.workflowName) | map({
    workflow: .[0].workflowName,
    total: length,
    failures: (map(select(.conclusion == "failure")) | length)
  })'

# Complex transformations
gh api repos/{owner}/{repo}/actions/runs --jq '.workflow_runs[] | {
  id: .id,
  name: .name,
  status: .status,
  branch: .head_branch,
  duration_sec: (if .status == "completed" then ((.updated_at | fromdateiso8601) - (.created_at | fromdateiso8601)) else null end),
  triggered_by: .actor.login,
  commit: .head_sha[0:7]
}'
```

### Useful jq Filters
```bash
# Get unique values
gh run list --json event | jq -r '[.[].event] | unique[]'

# Count by field
gh run list --json conclusion | jq -r 'group_by(.conclusion) | map({key: .[0].conclusion, count: length}) | from_entries'

# Date filtering
gh run list --json createdAt,displayTitle | \
  jq -r '.[] | select(.createdAt > "2024-01-01") | .displayTitle'

# Nested field access
gh api repos/{owner}/{repo}/actions/workflows --jq '.workflows[] | {
  name: .name,
  badge_url: .badge_url,
  last_run_status: .status
}'
```

## Automation Scripts

### Slack Notification Script
```bash
#!/bin/bash
# Send Slack notification for failed workflows

SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

check_failed_runs() {
  failed_runs=$(gh run list --status failure --limit 5 --json displayTitle,htmlUrl,headBranch,actor)
  
  if [ "$(echo "$failed_runs" | jq length)" -gt 0 ]; then
    message=$(echo "$failed_runs" | jq -r '.[] | "• <\(.htmlUrl)|\(.displayTitle)> on `\(.headBranch)` by @\(.actor.login)"' | head -5)
    
    payload=$(jq -n \
      --arg text ":x: Recent workflow failures:" \
      --arg message "$message" \
      '{
        text: $text,
        attachments: [{
          color: "danger",
          text: $message
        }]
      }')
    
    curl -X POST -H 'Content-type: application/json' \
      --data "$payload" \
      "$SLACK_WEBHOOK_URL"
  fi
}

check_failed_runs
```

### Auto-retry Failed Runs
```bash
#!/bin/bash
# Automatically retry failed runs

MAX_RETRIES=2
WORKFLOW_NAME="CI/CD Pipeline"

retry_failed_runs() {
  failed_runs=$(gh run list --workflow "$WORKFLOW_NAME" --status failure --limit 10 --json databaseId,displayTitle,attempt)
  
  echo "$failed_runs" | jq -r '.[] | select(.attempt < '"$MAX_RETRIES"') | .databaseId' | \
  while read -r run_id; do
    echo "Retrying run $run_id"
    gh run rerun "$run_id" --failed
    sleep 5  # Rate limiting
  done
}

retry_failed_runs
```

### Workflow Metrics Dashboard
```bash
#!/bin/bash
# Generate HTML dashboard for workflow metrics

generate_dashboard() {
  cat <<EOF > workflow_dashboard.html
<!DOCTYPE html>
<html>
<head>
    <title>GitHub Actions Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { display: inline-block; margin: 10px; padding: 20px; background: #f0f0f0; border-radius: 5px; }
        .success { color: green; }
        .failure { color: red; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>GitHub Actions Dashboard</h1>
    <div id="metrics">
EOF

  # Overall metrics
  total_runs=$(gh run list --limit 100 --json databaseId | jq length)
  success_runs=$(gh run list --limit 100 --json conclusion | jq '[.[] | select(.conclusion == "success")] | length')
  failure_runs=$(gh run list --limit 100 --json conclusion | jq '[.[] | select(.conclusion == "failure")] | length')
  
  cat <<EOF >> workflow_dashboard.html
        <div class="metric">
            <h3>Total Runs (Last 100)</h3>
            <p>$total_runs</p>
        </div>
        <div class="metric">
            <h3>Success Rate</h3>
            <p class="success">$(( success_runs * 100 / total_runs ))%</p>
        </div>
        <div class="metric">
            <h3>Failed Runs</h3>
            <p class="failure">$failure_runs</p>
        </div>
    </div>
    
    <h2>Recent Failures</h2>
    <table>
        <tr>
            <th>Workflow</th>
            <th>Branch</th>
            <th>Triggered By</th>
            <th>Time</th>
            <th>Link</th>
        </tr>
EOF

  # Recent failures table
  gh run list --status failure --limit 10 --json displayTitle,headBranch,actor,createdAt,htmlUrl | \
    jq -r '.[] | "<tr><td>\(.displayTitle)</td><td>\(.headBranch)</td><td>\(.actor.login)</td><td>\(.createdAt)</td><td><a href=\"\(.htmlUrl)\">View</a></td></tr>"' \
    >> workflow_dashboard.html

  cat <<EOF >> workflow_dashboard.html
    </table>
</body>
</html>
EOF

  echo "Dashboard generated: workflow_dashboard.html"
}

generate_dashboard
```

## Best Practices

### Rate Limiting
```bash
# Add delays between API calls
for run in $(gh run list --limit 50 --json databaseId -q '.[].databaseId'); do
  gh run view "$run" --json conclusion
  sleep 0.5  # Prevent rate limiting
done

# Use pagination for large datasets
gh api repos/{owner}/{repo}/actions/artifacts --paginate
```

### Error Handling
```bash
#!/bin/bash
# Robust error handling

safe_run_command() {
  local cmd=$1
  local max_retries=3
  local retry=0
  
  while [ $retry -lt $max_retries ]; do
    if output=$(eval "$cmd" 2>&1); then
      echo "$output"
      return 0
    else
      retry=$((retry + 1))
      echo "Command failed (attempt $retry/$max_retries): $output" >&2
      sleep $((retry * 2))  # Exponential backoff
    fi
  done
  
  return 1
}

# Usage
safe_run_command "gh run list --limit 10"
```

### Caching API Responses
```bash
#!/bin/bash
# Cache expensive API calls

CACHE_DIR="${HOME}/.cache/gh-actions"
CACHE_DURATION=300  # 5 minutes

get_cached_or_fetch() {
  local cache_key=$1
  local command=$2
  local cache_file="${CACHE_DIR}/${cache_key}.json"
  
  mkdir -p "$CACHE_DIR"
  
  # Check if cache exists and is fresh
  if [ -f "$cache_file" ]; then
    local cache_age=$(($(date +%s) - $(stat -f%m "$cache_file" 2>/dev/null || stat -c%Y "$cache_file")))
    if [ $cache_age -lt $CACHE_DURATION ]; then
      cat "$cache_file"
      return 0
    fi
  fi
  
  # Fetch and cache
  result=$(eval "$command")
  echo "$result" > "$cache_file"
  echo "$result"
}

# Usage
workflows=$(get_cached_or_fetch "workflows" "gh workflow list --json id,name,state")
```

## Common Patterns for mgit

### Multi-Provider CI/CD Monitoring
```bash
#!/bin/bash
# Monitor CI/CD across providers for mgit

monitor_mgit_workflows() {
  echo "# mgit CI/CD Status Report"
  echo "Generated: $(date)"
  echo ""
  
  # Check provider-specific tests
  for provider in "azure-devops" "github" "bitbucket"; do
    echo "## Provider: $provider"
    
    # Get recent runs for provider tests
    runs=$(gh run list --workflow "Test $provider" --limit 10 --json conclusion,createdAt)
    
    success_count=$(echo "$runs" | jq '[.[] | select(.conclusion == "success")] | length')
    total_count=$(echo "$runs" | jq length)
    
    echo "- Success rate: $((success_count * 100 / total_count))%"
    echo "- Recent runs: $success_count/$total_count successful"
    echo ""
  done
  
  # Check security scans
  echo "## Security Scans"
  security_runs=$(gh run list --workflow "Security Scan" --limit 5 --json conclusion,htmlUrl,createdAt)
  echo "$security_runs" | jq -r '.[] | "- [\(.createdAt)]: \(.conclusion) - \(.htmlUrl)"'
}

monitor_mgit_workflows
```

### Release Automation Helper
```bash
#!/bin/bash
# Helper script for mgit releases

prepare_release() {
  local version=$1
  
  # Check if all CI checks pass
  echo "Checking CI status..."
  latest_run=$(gh run list --branch main --workflow "CI/CD" --limit 1 --json conclusion,databaseId)
  
  if [ "$(echo "$latest_run" | jq -r '.[0].conclusion')" != "success" ]; then
    echo "ERROR: Latest CI run on main branch failed"
    exit 1
  fi
  
  # Trigger release workflow
  echo "Triggering release workflow for version $version..."
  gh workflow run release.yml \
    -f version="$version" \
    -f draft=true \
    -f platforms="linux/amd64,linux/arm64" \
    -f push_image=true
  
  # Wait for workflow to start
  sleep 5
  
  # Get the run ID
  run_id=$(gh run list --workflow release.yml --limit 1 --json databaseId -q '.[0].databaseId')
  
  echo "Release workflow started: Run ID $run_id"
  echo "Watch progress: gh run watch $run_id"
}

# Usage: ./prepare_release.sh v1.2.3
prepare_release "${1:-}"
```

### Performance Benchmarking
```bash
#!/bin/bash
# Track mgit performance over time

benchmark_mgit_performance() {
  local output_file="mgit_performance_$(date +%Y%m%d).csv"
  
  echo "date,workflow,duration_minutes,status" > "$output_file"
  
  # Get performance data for key workflows
  for workflow in "Integration Tests" "Build Executables" "Docker Build"; do
    gh run list --workflow "$workflow" --limit 20 --json createdAt,updatedAt,conclusion | \
      jq -r '.[] | [
        .createdAt[0:10],
        "'"$workflow"'",
        (((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 60 | round),
        .conclusion
      ] | @csv' >> "$output_file"
  done
  
  echo "Performance data saved to: $output_file"
  
  # Generate summary
  echo ""
  echo "Performance Summary:"
  awk -F',' 'NR>1 && $4=="\"success\"" {sum[$2]+=$3; count[$2]++} 
    END {for (w in sum) printf "%s: %.1f min (avg)\n", w, sum[w]/count[w]}' "$output_file"
}

benchmark_mgit_performance
```

### Dependency Update Checker
```bash
#!/bin/bash
# Check for dependency updates in mgit

check_dependency_updates() {
  # Trigger dependency check workflow
  gh workflow run dependency-check.yml
  
  # Wait for completion
  echo "Waiting for dependency check to complete..."
  sleep 10
  
  run_id=$(gh run list --workflow dependency-check.yml --limit 1 --json databaseId -q '.[0].databaseId')
  gh run watch "$run_id"
  
  # Download results if available
  if gh run download "$run_id" --name dependency-report 2>/dev/null; then
    echo "Dependency report downloaded"
    cat dependency-report/updates.txt
  fi
}

check_dependency_updates
```

### GitHub CLI Aliases for mgit Development
```bash
# Add useful aliases for mgit development
gh alias set mgit-ci 'run list --workflow "mgit CI/CD" --limit 10'
gh alias set mgit-test 'workflow run test.yml'
gh alias set mgit-release 'workflow run release.yml'
gh alias set mgit-security 'run list --workflow "Security Scan" --limit 5'
gh alias set mgit-perf 'run list --workflow "Performance Test" --json createdAt,updatedAt | jq -r ".[0] | \"Duration: \" + ((((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 60) | tostring) + \" minutes\""'

# Use aliases
gh mgit-ci
gh mgit-test -f provider=github
gh mgit-security
```

### Troubleshooting Guide
```bash
#!/bin/bash
# Troubleshooting helper for mgit CI/CD

troubleshoot_failure() {
  local run_id=$1
  
  echo "=== Troubleshooting Run $run_id ==="
  
  # Get run details
  run_info=$(gh run view "$run_id" --json displayTitle,event,headBranch,conclusion,jobs)
  
  echo "Workflow: $(echo "$run_info" | jq -r .displayTitle)"
  echo "Branch: $(echo "$run_info" | jq -r .headBranch)"
  echo "Event: $(echo "$run_info" | jq -r .event)"
  echo "Conclusion: $(echo "$run_info" | jq -r .conclusion)"
  echo ""
  
  # Find failed jobs
  echo "Failed Jobs:"
  echo "$run_info" | jq -r '.jobs[] | select(.conclusion == "failure") | "- \(.name): \(.steps[] | select(.conclusion == "failure") | .name)"'
  
  # Get logs for failed steps
  echo ""
  echo "Failed Step Logs:"
  gh run view "$run_id" --log-failed
  
  # Check for common issues
  echo ""
  echo "Common Issues to Check:"
  echo "- [ ] Authentication tokens expired?"
  echo "- [ ] Rate limits reached?"
  echo "- [ ] External service downtime?"
  echo "- [ ] Dependency version conflicts?"
  echo "- [ ] Insufficient permissions?"
}

# Usage: ./troubleshoot.sh <run-id>
troubleshoot_failure "${1:-}"
```

## Summary

This comprehensive guide provides:
1. Complete gh CLI command reference for GitHub Actions
2. Advanced filtering and querying techniques
3. Automation scripts for common tasks
4. Integration patterns with jq for data processing
5. Best practices for rate limiting and error handling
6. mgit-specific monitoring and automation patterns
7. Performance tracking and troubleshooting tools

The guide is optimized for LLM consumption with:
- Clear command syntax and options
- Practical examples for each command
- Ready-to-use scripts that can be adapted
- Common patterns specific to the mgit project
- Troubleshooting and debugging helpers