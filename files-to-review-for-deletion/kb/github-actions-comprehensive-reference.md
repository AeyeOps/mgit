# GitHub Actions Comprehensive Reference for LLM Context

## Table of Contents
1. [Core Concepts](#core-concepts)
2. [Workflow Syntax](#workflow-syntax)
3. [Events and Triggers](#events-and-triggers)
4. [Jobs Configuration](#jobs-configuration)
5. [Steps and Actions](#steps-and-actions)
6. [Environment Variables and Secrets](#environment-variables-and-secrets)
7. [Matrix Builds](#matrix-builds)
8. [Conditional Execution](#conditional-execution)
9. [Artifacts and Caching](#artifacts-and-caching)
10. [Service Containers](#service-containers)
11. [Self-Hosted Runners](#self-hosted-runners)
12. [Composite Actions](#composite-actions)
13. [Reusable Workflows](#reusable-workflows)
14. [Security Best Practices](#security-best-practices)
15. [GITHUB_TOKEN and Permissions](#github_token-and-permissions)
16. [Python-Specific Patterns](#python-specific-patterns)
17. [mgit Project CI/CD Requirements](#mgit-project-cicd-requirements)

## Core Concepts

### Workflow Structure
```yaml
name: Workflow Name
run-name: Dynamic run name ${{ github.actor }} - ${{ github.event_name }}

on:
  push:
    branches: [ main, develop ]
  pull_request:
    types: [ opened, synchronize, reopened ]

permissions:
  contents: read
  issues: write

env:
  PYTHON_VERSION: "3.11"

jobs:
  job-id:
    name: Human-readable job name
    runs-on: ubuntu-latest
    steps:
      - name: Step name
        uses: actions/checkout@v4
```

### Key Components
- **Workflow**: YAML file in `.github/workflows/` directory
- **Job**: Set of steps executed on the same runner
- **Step**: Individual task that runs commands or actions
- **Action**: Reusable unit of code (from marketplace or custom)
- **Runner**: Server that runs workflows (GitHub-hosted or self-hosted)

## Workflow Syntax

### Complete Syntax Reference
```yaml
name: string  # Workflow name displayed in UI
run-name: string  # Dynamic run name with expressions

on:  # Events that trigger workflow
  push:
    branches: [ pattern ]
    branches-ignore: [ pattern ]
    tags: [ pattern ]
    tags-ignore: [ pattern ]
    paths: [ pattern ]
    paths-ignore: [ pattern ]
  pull_request:
    types: [ opened, closed, synchronize, reopened ]
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:
    inputs:
      input-name:
        description: string
        required: boolean
        default: string
        type: choice|boolean|string|environment
        options: [ array-for-choice ]
  workflow_call:
    inputs:
      input-name:
        description: string
        required: boolean
        default: string
        type: string|boolean|number
    secrets:
      secret-name:
        required: boolean
        description: string
    outputs:
      output-name:
        description: string
        value: ${{ jobs.job-id.outputs.output-name }}

permissions:  # Can be top-level or job-level
  actions: read|write|none
  checks: read|write|none
  contents: read|write|none
  deployments: read|write|none
  issues: read|write|none
  packages: read|write|none
  pages: read|write|none
  pull-requests: read|write|none
  repository-projects: read|write|none
  security-events: read|write|none
  statuses: read|write|none

env:  # Environment variables
  KEY: value

defaults:
  run:
    shell: bash|pwsh|python|sh|cmd|powershell
    working-directory: path

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true|false

jobs:
  job-id:
    name: string
    runs-on: ubuntu-latest|windows-latest|macos-latest|self-hosted
    permissions: {}  # Job-specific permissions
    needs: [ job-id ]  # Job dependencies
    if: condition  # Conditional execution
    outputs:
      output-name: ${{ steps.step-id.outputs.output-name }}
    strategy:
      matrix:
        key: [ values ]
      fail-fast: true|false
      max-parallel: number
    timeout-minutes: number
    continue-on-error: true|false
    container:
      image: docker-image
      credentials:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
      env: {}
      ports: [ ]
      volumes: [ ]
      options: string
    services:
      service-name:
        image: docker-image
        credentials: {}
        env: {}
        ports: [ ]
        volumes: [ ]
        options: string
    environment:
      name: environment-name
      url: string
    concurrency:
      group: string
      cancel-in-progress: boolean
    steps:
      - name: string
        id: string
        if: condition
        uses: action@version
        with:
          key: value
        env:
          KEY: value
        continue-on-error: boolean
        timeout-minutes: number
      - name: string
        run: |
          command
        shell: bash|pwsh|python|sh|cmd|powershell
        working-directory: path
```

## Events and Triggers

### Push Events
```yaml
on:
  push:
    branches:
      - main
      - 'releases/**'
      - '!releases/**-alpha'  # Exclude pattern
    tags:
      - v1.*
      - '!v1.*.alpha'
    paths:
      - '**.py'
      - 'requirements.txt'
    paths-ignore:
      - 'docs/**'
      - '**.md'
```

### Pull Request Events
```yaml
on:
  pull_request:
    types:
      - opened
      - synchronize
      - reopened
      - closed
      - labeled
      - unlabeled
      - assigned
      - unassigned
      - review_requested
      - review_request_removed
      - ready_for_review
      - converted_to_draft
    branches:
      - main
      - develop
```

### Schedule Events
```yaml
on:
  schedule:
    # Every day at 2:30 UTC
    - cron: '30 2 * * *'
    # Every Monday at 9:00 UTC
    - cron: '0 9 * * 1'
    # First day of month at midnight
    - cron: '0 0 1 * *'
```

### Manual Triggers
```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        type: choice
        options:
          - development
          - staging
          - production
        default: 'development'
      debug:
        description: 'Enable debug mode'
        required: false
        type: boolean
        default: false
      version:
        description: 'Version to deploy'
        required: false
        type: string
```

### Repository Dispatch
```yaml
on:
  repository_dispatch:
    types: [custom-event, deployment-trigger]
```

### Workflow Events
```yaml
on:
  workflow_call:
    inputs:
      config-path:
        required: true
        type: string
    secrets:
      token:
        required: true
  workflow_run:
    workflows: ["CI Pipeline"]
    types:
      - completed
      - requested
```

## Jobs Configuration

### Basic Job Structure
```yaml
jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest

  deploy:
    name: Deploy Application
    needs: test  # Depends on test job
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://app.example.com
    steps:
      - name: Deploy
        run: echo "Deploying..."
```

### Job Outputs
```yaml
jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
      version: ${{ steps.get-version.outputs.version }}
    steps:
      - id: set-matrix
        run: echo "matrix={\"include\":[{\"python\":\"3.8\"},{\"python\":\"3.9\"}]}" >> $GITHUB_OUTPUT
      - id: get-version
        run: echo "version=1.2.3" >> $GITHUB_OUTPUT

  test:
    needs: setup
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.setup.outputs.matrix) }}
    steps:
      - run: echo "Testing on Python ${{ matrix.python }}"
      - run: echo "Version ${{ needs.setup.outputs.version }}"
```

### Job Dependencies
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Building..."

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Testing..."

  deploy:
    needs: [build, test]  # Multiple dependencies
    if: success()  # Only if all dependencies succeed
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying..."
```

## Steps and Actions

### Using Actions
```yaml
steps:
  # Marketplace action
  - name: Checkout code
    uses: actions/checkout@v4
    with:
      fetch-depth: 0  # Full history
      token: ${{ secrets.GITHUB_TOKEN }}
      submodules: recursive

  # Docker action
  - name: Run custom Docker action
    uses: docker://alpine:3.18
    with:
      args: echo "Hello from Docker"

  # Local action
  - name: Run local action
    uses: ./.github/actions/my-action
    with:
      input: value

  # Specific commit
  - name: Use action at commit
    uses: actions/setup-python@0a5c61591373683505ea898e09a3ea4f39ef2b9c
```

### Running Commands
```yaml
steps:
  # Single line command
  - name: Install dependencies
    run: pip install -r requirements.txt

  # Multi-line command
  - name: Run multiple commands
    run: |
      echo "Starting build"
      python setup.py build
      python setup.py test

  # Different shells
  - name: PowerShell command
    shell: pwsh
    run: |
      Write-Host "PowerShell script"
      $PSVersionTable

  - name: Python script
    shell: python
    run: |
      import sys
      print(f"Python {sys.version}")

  # Working directory
  - name: Run in subdirectory
    working-directory: ./src
    run: pytest
```

### Step Outputs
```yaml
steps:
  - name: Generate output
    id: generator
    run: |
      echo "version=1.2.3" >> $GITHUB_OUTPUT
      echo "hash=$(git rev-parse HEAD)" >> $GITHUB_OUTPUT
      # Multiline output
      {
        echo 'json<<EOF'
        echo '{"key": "value"}'
        echo 'EOF'
      } >> $GITHUB_OUTPUT

  - name: Use output
    run: |
      echo "Version: ${{ steps.generator.outputs.version }}"
      echo "Hash: ${{ steps.generator.outputs.hash }}"
      echo "JSON: ${{ steps.generator.outputs.json }}"
```

## Environment Variables and Secrets

### Environment Variables Hierarchy
```yaml
# Workflow level
env:
  GLOBAL_VAR: "workflow-value"

jobs:
  example:
    # Job level
    env:
      JOB_VAR: "job-value"
    runs-on: ubuntu-latest
    steps:
      # Step level
      - name: Use variables
        env:
          STEP_VAR: "step-value"
        run: |
          echo "Global: $GLOBAL_VAR"
          echo "Job: $JOB_VAR"
          echo "Step: $STEP_VAR"
```

### GitHub Context Variables
```yaml
steps:
  - name: Context examples
    run: |
      echo "Repository: ${{ github.repository }}"
      echo "Branch: ${{ github.ref_name }}"
      echo "SHA: ${{ github.sha }}"
      echo "Actor: ${{ github.actor }}"
      echo "Event: ${{ github.event_name }}"
      echo "Run ID: ${{ github.run_id }}"
      echo "Run Number: ${{ github.run_number }}"
      echo "Workspace: ${{ github.workspace }}"
```

### Using Secrets
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: aws configure set region us-east-1

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Create secret file
        run: |
          echo "${{ secrets.SSH_PRIVATE_KEY }}" > id_rsa
          chmod 600 id_rsa
```

### Organization and Repository Secrets
```yaml
# Repository secrets: Available to all workflows in repo
# Organization secrets: Can be limited to specific repos
# Environment secrets: Only available when job references environment

jobs:
  deploy:
    environment: production  # Access environment-specific secrets
    runs-on: ubuntu-latest
    steps:
      - run: echo "Using ${{ secrets.PROD_API_KEY }}"
```

## Matrix Builds

### Basic Matrix
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python: ["3.8", "3.9", "3.10", "3.11"]
    
runs-on: ${{ matrix.os }}
steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python }}
```

### Matrix Include/Exclude
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    python: ["3.8", "3.9", "3.10"]
    include:
      # Add specific combinations
      - os: macos-latest
        python: "3.11"
        experimental: true
      # Add extra variables
      - os: ubuntu-latest
        python: "3.8"
        coverage: true
    exclude:
      # Remove specific combinations
      - os: windows-latest
        python: "3.8"
```

### Dynamic Matrix
```yaml
jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4
      - id: set-matrix
        run: |
          # Generate matrix from file or API
          matrix=$(python scripts/generate_matrix.py)
          echo "matrix=$matrix" >> $GITHUB_OUTPUT

  test:
    needs: setup
    strategy:
      matrix: ${{ fromJson(needs.setup.outputs.matrix) }}
    runs-on: ${{ matrix.os }}
    steps:
      - run: echo "Testing ${{ matrix.name }}"
```

### Matrix Strategy Options
```yaml
strategy:
  matrix:
    python: ["3.8", "3.9", "3.10"]
  fail-fast: false  # Continue other jobs if one fails
  max-parallel: 2   # Run max 2 jobs in parallel
```

## Conditional Execution

### Basic Conditions
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' || github.event_name == 'pull_request'

  deploy:
    runs-on: ubuntu-latest
    if: |
      github.ref == 'refs/heads/main' &&
      github.event_name == 'push' &&
      contains(github.event.head_commit.message, '[deploy]')
```

### Step Conditions
```yaml
steps:
  - name: Checkout
    uses: actions/checkout@v4

  - name: Test
    run: pytest
    id: test

  - name: Upload coverage on success
    if: success()
    run: codecov

  - name: Notify on failure
    if: failure()
    run: |
      curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
        -d '{"text": "Tests failed!"}'

  - name: Always cleanup
    if: always()
    run: rm -rf temp/

  - name: Only on main branch
    if: github.ref == 'refs/heads/main'
    run: echo "Main branch only"

  - name: Check file exists
    id: check
    run: |
      if [ -f "config.yaml" ]; then
        echo "exists=true" >> $GITHUB_OUTPUT
      else
        echo "exists=false" >> $GITHUB_OUTPUT
      fi

  - name: Use file if exists
    if: steps.check.outputs.exists == 'true'
    run: cat config.yaml
```

### Advanced Expressions
```yaml
if: |
  (
    github.event_name == 'push' ||
    (github.event_name == 'pull_request' && github.event.action != 'closed')
  ) &&
  !contains(github.event.head_commit.message, '[skip ci]') &&
  !contains(github.event.head_commit.message, '[ci skip]')
```

### Functions in Conditions
```yaml
# contains()
if: contains(github.ref, 'release')
if: contains(fromJson('["push", "pull_request"]'), github.event_name)
if: contains(github.event.labels.*.name, 'bug')

# startsWith() / endsWith()
if: startsWith(github.ref, 'refs/heads/feature/')
if: endsWith(github.ref, '-dev')

# format()
if: format('refs/heads/{0}', github.event.inputs.branch) == github.ref

# join()
if: contains(join(github.event.labels.*.name, ','), 'urgent')

# toJSON() / fromJSON()
if: fromJSON(env.DEPLOY_ENABLED)
```

## Artifacts and Caching

### Upload/Download Artifacts
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build
        run: |
          python setup.py build
          python -m build --wheel

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: python-package-${{ github.sha }}
          path: |
            dist/*.whl
            dist/*.tar.gz
          retention-days: 7
          if-no-files-found: error  # warn, error, or ignore

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/
          retention-days: 30

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: python-package-${{ github.sha }}
          path: ./dist

      - name: List artifacts
        run: ls -la dist/
```

### Dependency Caching
```yaml
# Python pip cache
- name: Cache pip
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

# Python Poetry cache
- name: Cache Poetry
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pypoetry
      ~/.cache/pip
    key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}

# Node.js cache
- name: Cache node modules
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

# Multiple cache paths
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.cache/pre-commit
      ~/.mypy_cache
    key: ${{ runner.os }}-deps-${{ hashFiles('**/*.txt', '.pre-commit-config.yaml') }}
```

### Advanced Cache Patterns
```yaml
# Restore cache even if key doesn't match exactly
- name: Cache with fallback
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}-${{ hashFiles('**/requirements-dev.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}-
      ${{ runner.os }}-pip-

# Save cache conditionally
- name: Cache build
  uses: actions/cache@v4
  id: cache
  with:
    path: ./build
    key: ${{ runner.os }}-build-${{ github.sha }}

- name: Build if not cached
  if: steps.cache.outputs.cache-hit != 'true'
  run: make build

# Cache with timeout
- name: Restore cache
  uses: actions/cache/restore@v4
  with:
    path: ~/.cache
    key: cache-key
    restore-keys: cache-
  timeout-minutes: 5
  continue-on-error: true
```

## Service Containers

### PostgreSQL Service
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        run: pytest
```

### Redis Service
```yaml
services:
  redis:
    image: redis:7-alpine
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
    ports:
      - 6379:6379
```

### Multiple Services
```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: postgres
    ports:
      - 5432:5432
  
  redis:
    image: redis:7
    ports:
      - 6379:6379
  
  elasticsearch:
    image: elasticsearch:8.11.0
    env:
      discovery.type: single-node
      xpack.security.enabled: false
    ports:
      - 9200:9200
    options: >-
      --health-cmd "curl -f http://localhost:9200/_cluster/health"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 10
```

### Container Jobs
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: python:3.11-slim
      credentials:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
      env:
        ENV_VAR: value
      volumes:
        - my_volume:/data
      options: --cpus 2 --memory 4g
```

## Self-Hosted Runners

### Basic Configuration
```yaml
runs-on: self-hosted

# With labels
runs-on: [self-hosted, linux, x64, gpu]

# Matrix with self-hosted
strategy:
  matrix:
    include:
      - os: ubuntu-latest
        runner: ubuntu-latest
      - os: self-hosted
        runner: [self-hosted, linux, gpu]
runs-on: ${{ matrix.runner }}
```

### Security Considerations
```yaml
# NEVER use self-hosted runners for public repositories!
# For private repos only:

jobs:
  secure-job:
    if: github.event_name == 'push' && github.repository_owner == 'myorg'
    runs-on: [self-hosted, trusted]
    steps:
      - uses: actions/checkout@v4
        with:
          # Use fetch-depth 1 for security
          fetch-depth: 1
          
      - name: Clean workspace
        run: |
          git clean -ffdx
          git reset --hard HEAD
```

## Composite Actions

### Creating Composite Action
```yaml
# .github/actions/setup-python-env/action.yml
name: 'Setup Python Environment'
description: 'Setup Python with caching and dependencies'
inputs:
  python-version:
    description: 'Python version to use'
    required: true
    default: '3.11'
  requirements-file:
    description: 'Path to requirements file'
    required: false
    default: 'requirements.txt'
  cache-key:
    description: 'Additional cache key'
    required: false
    default: ''

outputs:
  python-version:
    description: 'Installed Python version'
    value: ${{ steps.setup-python.outputs.python-version }}
  cache-hit:
    description: 'Whether cache was hit'
    value: ${{ steps.cache.outputs.cache-hit }}

runs:
  using: "composite"
  steps:
    - name: Setup Python
      id: setup-python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}

    - name: Cache pip
      id: cache
      uses: actions/cache@v4
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ inputs.python-version }}-${{ hashFiles(inputs.requirements-file) }}-${{ inputs.cache-key }}
        restore-keys: |
          ${{ runner.os }}-pip-${{ inputs.python-version }}-

    - name: Install dependencies
      if: inputs.requirements-file != ''
      shell: bash
      run: |
        python -m pip install --upgrade pip
        pip install -r ${{ inputs.requirements-file }}
```

### Using Composite Action
```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Python environment
    uses: ./.github/actions/setup-python-env
    with:
      python-version: '3.11'
      requirements-file: 'requirements-dev.txt'
      cache-key: ${{ github.sha }}
```

## Reusable Workflows

### Creating Reusable Workflow
```yaml
# .github/workflows/reusable-tests.yml
name: Reusable Test Workflow

on:
  workflow_call:
    inputs:
      python-version:
        description: 'Python version'
        required: false
        type: string
        default: '3.11'
      os:
        description: 'Operating system'
        required: false
        type: string
        default: 'ubuntu-latest'
      coverage:
        description: 'Upload coverage'
        required: false
        type: boolean
        default: true
    secrets:
      CODECOV_TOKEN:
        required: false
        description: 'Codecov token'
    outputs:
      test-result:
        description: 'Test result'
        value: ${{ jobs.test.outputs.result }}

jobs:
  test:
    runs-on: ${{ inputs.os }}
    outputs:
      result: ${{ steps.test.outcome }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}
          
      - name: Run tests
        id: test
        run: pytest --cov
        
      - name: Upload coverage
        if: inputs.coverage && secrets.CODECOV_TOKEN != ''
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
```

### Using Reusable Workflow
```yaml
name: CI

on: [push, pull_request]

jobs:
  test-matrix:
    strategy:
      matrix:
        python: ["3.8", "3.9", "3.10", "3.11"]
        os: [ubuntu-latest, windows-latest, macos-latest]
    uses: ./.github/workflows/reusable-tests.yml
    with:
      python-version: ${{ matrix.python }}
      os: ${{ matrix.os }}
      coverage: ${{ matrix.python == '3.11' && matrix.os == 'ubuntu-latest' }}
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  deploy:
    needs: test-matrix
    if: success() && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: echo "All tests passed, deploying..."
```

## Security Best Practices

### Pinning Actions
```yaml
# Bad - uses mutable tag
- uses: actions/checkout@v4

# Good - uses immutable SHA
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1

# Also good - Dependabot can update
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4
```

### Least Privilege Permissions
```yaml
# Top level - restrictive defaults
permissions:
  contents: read

jobs:
  release:
    # Job level - specific permissions
    permissions:
      contents: write  # For creating releases
      packages: write  # For publishing packages
    runs-on: ubuntu-latest
```

### Secret Scanning Prevention
```yaml
steps:
  - name: Check for secrets
    uses: trufflesecurity/trufflehog@main
    with:
      path: ./
      base: ${{ github.event.repository.default_branch }}
      head: HEAD

  - name: Validate no hardcoded secrets
    run: |
      # Check for common secret patterns
      ! grep -r "password\s*=\s*[\"'][^\"']+[\"']" . || exit 1
      ! grep -r "api[_-]?key\s*=\s*[\"'][^\"']+[\"']" . || exit 1
```

### Dependency Security
```yaml
- name: Security audit
  run: |
    pip install safety
    safety check --json

- name: License check
  run: |
    pip install pip-licenses
    pip-licenses --fail-on="GPL*"
```

### Code Scanning
```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: python
    queries: security-and-quality

- name: Autobuild
  uses: github/codeql-action/autobuild@v3

- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v3

- name: Run Bandit
  run: |
    pip install bandit[toml]
    bandit -r mgit/ -f json -o bandit-report.json

- name: Upload Bandit results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: bandit-report.json
```

## GITHUB_TOKEN and Permissions

### Default GITHUB_TOKEN Permissions
```yaml
# Restrictive by default
permissions:
  contents: read

# Or explicitly set all
permissions:
  actions: read
  checks: read
  contents: read
  deployments: read
  id-token: none
  issues: read
  discussions: read
  packages: read
  pages: read
  pull-requests: read
  repository-projects: read
  security-events: read
  statuses: read
```

### Common Permission Requirements
```yaml
# Creating releases
permissions:
  contents: write

# Commenting on PRs
permissions:
  pull-requests: write

# Publishing packages
permissions:
  packages: write

# Creating/updating checks
permissions:
  checks: write

# OIDC token for cloud providers
permissions:
  id-token: write

# Security scanning
permissions:
  security-events: write
```

### Using GITHUB_TOKEN
```yaml
steps:
  - name: Create release
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: |
      gh release create v1.0.0 \
        --title "Release v1.0.0" \
        --notes "Release notes"

  - name: Comment on PR
    uses: actions/github-script@v7
    with:
      github-token: ${{ secrets.GITHUB_TOKEN }}
      script: |
        github.rest.issues.createComment({
          issue_number: context.issue.number,
          owner: context.repo.owner,
          repo: context.repo.repo,
          body: 'Deployment successful! 🎉'
        })
```

### Personal Access Token for Extended Permissions
```yaml
# When GITHUB_TOKEN isn't enough (e.g., triggering other workflows)
steps:
  - uses: actions/checkout@v4
    with:
      token: ${{ secrets.PAT }}  # Personal Access Token
      
  - name: Push changes
    run: |
      git config user.name "github-actions[bot]"
      git config user.email "github-actions[bot]@users.noreply.github.com"
      git add .
      git commit -m "Auto-update"
      git push  # This can trigger other workflows with PAT
```

## Python-Specific Patterns

### Complete Python CI/CD Pipeline
```yaml
name: Python CI/CD

on:
  push:
    branches: [main, develop]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-lint-${{ hashFiles('**/requirements*.txt') }}
          
      - name: Install linting tools
        run: |
          python -m pip install --upgrade pip
          pip install black ruff mypy
          
      - name: Black formatting
        run: black --check .
        
      - name: Ruff linting
        run: ruff check .
        
      - name: MyPy type checking
        run: mypy mgit/

  test:
    needs: lint
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]
        exclude:
          - os: macos-latest
            python-version: "3.8"
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pip
            .venv
          key: ${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('**/requirements*.txt') }}
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          
      - name: Run tests with coverage
        run: |
          pytest tests/ \
            --cov=mgit \
            --cov-report=xml \
            --cov-report=html \
            --junitxml=junit/test-results-${{ matrix.os }}-${{ matrix.python-version }}.xml
            
      - name: Upload coverage
        if: matrix.python-version == '3.11' && matrix.os == 'ubuntu-latest'
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pytest-results-${{ matrix.os }}-${{ matrix.python-version }}
          path: junit/test-results-*.xml

  security:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Bandit
        uses: gaurav-nelson/bandit-action@v1
        with:
          path: "mgit/"
          level: medium
          confidence: medium
          exit_zero: false
          
      - name: Safety check
        run: |
          pip install safety
          safety check --json --continue-on-error
          
      - name: CodeQL Analysis
        uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # For versioning
          
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install build tools
        run: |
          python -m pip install --upgrade pip
          pip install build twine
          
      - name: Build package
        run: python -m build
        
      - name: Check package
        run: twine check dist/*
        
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: python-package-distributions
          path: dist/

  publish:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/mgit
    permissions:
      id-token: write  # For trusted publishing
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: python-package-distributions
          path: dist/
          
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        # Uses trusted publishing, no password needed

  docker:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      packages: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha
            
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Poetry-based Project
```yaml
name: Poetry CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          
      - name: Cache Poetry
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pypoetry
            ~/.cache/pip
            .venv
          key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
          
      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH
          
      - name: Configure Poetry
        run: |
          poetry config virtualenvs.in-project true
          poetry config virtualenvs.create true
          
      - name: Install dependencies
        run: poetry install --with dev
        
      - name: Run tests
        run: poetry run pytest
        
      - name: Build package
        run: poetry build
        
      - name: Run custom task
        run: poetry run poe build-linux
```

### Integration Testing with Services
```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
          
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
          
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install psycopg2-binary redis
          
      - name: Wait for services
        run: |
          python -c "
          import psycopg2
          import redis
          import time
          
          # Wait for PostgreSQL
          for _ in range(30):
              try:
                  conn = psycopg2.connect(
                      host='localhost',
                      port=5432,
                      database='testdb',
                      user='postgres',
                      password='testpass'
                  )
                  conn.close()
                  print('PostgreSQL is ready')
                  break
              except:
                  time.sleep(1)
                  
          # Wait for Redis
          r = redis.Redis(host='localhost', port=6379)
          r.ping()
          print('Redis is ready')
          "
          
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
        run: pytest tests/integration/
```

## mgit Project CI/CD Requirements

### Comprehensive CI/CD Workflow for mgit
```yaml
name: mgit CI/CD

on:
  push:
    branches: [main, develop]
    tags: ['v*']
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      debug_enabled:
        type: boolean
        description: 'Enable debug mode'
        required: false
        default: false

env:
  PYTHON_VERSION: "3.11"
  POETRY_VERSION: "1.7.1"

jobs:
  # Code quality checks
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pip
            ~/.cache/pypoetry
            .venv
          key: ${{ runner.os }}-quality-${{ hashFiles('**/poetry.lock', '**/pyproject.toml') }}
          
      - name: Install Poetry
        run: |
          pipx install poetry==${{ env.POETRY_VERSION }}
          poetry config virtualenvs.in-project true
          
      - name: Install dependencies
        run: poetry install --with dev
        
      - name: Run formatters
        run: |
          poetry run black --check .
          poetry run ruff check .
          
      - name: Type checking
        run: poetry run mypy mgit/
        
      - name: Security scan
        run: |
          poetry run bandit -r mgit/ -ll
          poetry run safety check

  # Multi-provider testing
  test:
    name: Test ${{ matrix.provider }} - Py${{ matrix.python }} - ${{ matrix.os }}
    needs: quality
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.8", "3.9", "3.10", "3.11"]
        provider: [azure-devops, github, bitbucket]
        exclude:
          # Exclude some combinations to save CI time
          - os: macos-latest
            python: "3.8"
          - os: windows-latest
            python: "3.9"
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python ${{ matrix.python }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pip
            ~/.cache/pypoetry
            .venv
          key: ${{ runner.os }}-py${{ matrix.python }}-test-${{ hashFiles('**/poetry.lock') }}
          
      - name: Install Poetry
        run: |
          pipx install poetry==${{ env.POETRY_VERSION }}
          poetry config virtualenvs.in-project true
          
      - name: Install dependencies
        run: poetry install --with dev
        
      - name: Run unit tests
        env:
          MGIT_TEST_PROVIDER: ${{ matrix.provider }}
        run: |
          poetry run pytest tests/unit/ \
            -v \
            --cov=mgit \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=test-results/junit-${{ matrix.provider }}-${{ matrix.python }}-${{ matrix.os }}.xml
            
      - name: Upload coverage
        if: matrix.python == '3.11' && matrix.os == 'ubuntu-latest'
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: ${{ matrix.provider }}
          name: coverage-${{ matrix.provider }}

  # Integration tests with real services
  integration:
    name: Integration Tests
    needs: quality
    runs-on: ubuntu-latest
    services:
      # Mock git server for testing
      gitserver:
        image: rockstorm/git-server
        env:
          GIT_USER: git
          GIT_PASSWORD: git
        ports:
          - 2222:22
          
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install Poetry
        run: |
          pipx install poetry==${{ env.POETRY_VERSION }}
          poetry config virtualenvs.in-project true
          
      - name: Install dependencies
        run: poetry install --with dev
        
      - name: Setup test repositories
        run: |
          # Create test repos on mock server
          ./scripts/setup-integration-tests.sh
          
      - name: Run integration tests
        env:
          MGIT_TEST_GIT_SERVER: localhost:2222
          MGIT_TEST_GIT_USER: git
          MGIT_TEST_GIT_PASS: git
        run: |
          poetry run pytest tests/integration/ -v

  # Security scanning
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Run CodeQL Analysis
        uses: github/codeql-action/init@v3
        with:
          languages: python
          queries: security-and-quality
          
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
      
      - name: Run Trivy security scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

  # Build executables
  build:
    name: Build ${{ matrix.os }}
    needs: [test, integration, security]
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            name: mgit-linux
            path: dist/mgit
          - os: windows-latest
            name: mgit-windows.exe
            path: dist/mgit.exe
          - os: macos-latest
            name: mgit-macos
            path: dist/mgit
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install Poetry
        run: |
          pipx install poetry==${{ env.POETRY_VERSION }}
          poetry config virtualenvs.in-project true
          
      - name: Install dependencies
        run: |
          poetry install --with dev
          poetry run pip install pyinstaller
          
      - name: Build executable
        run: |
          poetry run pyinstaller \
            --onefile \
            --name mgit \
            --add-data "mgit:mgit" \
            mgit/__main__.py
            
      - name: Test executable
        run: |
          ${{ matrix.path }} --version
          ${{ matrix.path }} --help
          
      - name: Upload executable
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.name }}
          path: ${{ matrix.path }}

  # Build and push Docker images
  docker:
    name: Docker Build
    needs: [test, integration, security]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: |
            ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable={{is_default_branch}}
            
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            VERSION=${{ github.ref_name }}
            COMMIT=${{ github.sha }}

  # Release process
  release:
    name: Create Release
    if: startsWith(github.ref, 'refs/tags/v')
    needs: [build, docker]
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          
      - name: Generate changelog
        id: changelog
        run: |
          # Generate changelog from commits
          git log --pretty=format:"- %s" $(git describe --tags --abbrev=0 HEAD^)..HEAD > CHANGELOG_CURRENT.md
          
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts/
          
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          body_path: CHANGELOG_CURRENT.md
          files: |
            artifacts/mgit-linux/mgit
            artifacts/mgit-windows.exe/mgit.exe
            artifacts/mgit-macos/mgit
          draft: false
          prerelease: ${{ contains(github.ref, '-rc') || contains(github.ref, '-beta') }}
          
      - name: Publish to PyPI
        if: "!contains(github.ref, '-rc') && !contains(github.ref, '-beta')"
        env:
          POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          pipx install poetry==${{ env.POETRY_VERSION }}
          poetry build
          poetry publish

  # Monitoring and notifications
  notify:
    name: Send Notifications
    if: always()
    needs: [quality, test, integration, security, build, docker, release]
    runs-on: ubuntu-latest
    steps:
      - name: Check job statuses
        id: check
        run: |
          # Aggregate job results
          if [[ "${{ needs.quality.result }}" == "failure" ]] || \
             [[ "${{ needs.test.result }}" == "failure" ]] || \
             [[ "${{ needs.integration.result }}" == "failure" ]] || \
             [[ "${{ needs.security.result }}" == "failure" ]]; then
            echo "status=failure" >> $GITHUB_OUTPUT
          else
            echo "status=success" >> $GITHUB_OUTPUT
          fi
          
      - name: Send Slack notification
        if: github.event_name != 'pull_request'
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ steps.check.outputs.status }}
          text: |
            Workflow: ${{ github.workflow }}
            Job: ${{ github.job }}
            Repo: ${{ github.repository }}
            Ref: ${{ github.ref }}
            Commit: ${{ github.sha }}
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}

# Workflow dispatch for maintenance tasks
  maintenance:
    name: Maintenance Tasks
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Clean old artifacts
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # Delete artifacts older than 30 days
          gh api repos/${{ github.repository }}/actions/artifacts \
            --jq '.artifacts[] | select(.created_at | fromdateiso8601 < (now - 30*24*60*60)) | .id' | \
            xargs -I {} gh api -X DELETE repos/${{ github.repository }}/actions/artifacts/{}
            
      - name: Update dependencies
        run: |
          pipx install poetry==${{ env.POETRY_VERSION }}
          poetry update
          poetry export -f requirements.txt -o requirements.txt
          poetry export -f requirements.txt --with dev -o requirements-dev.txt
```

### mgit-Specific Testing Patterns
```yaml
# Test provider authentication
- name: Test Azure DevOps auth
  env:
    AZURE_DEVOPS_PAT: ${{ secrets.TEST_AZURE_PAT }}
    AZURE_DEVOPS_ORG: ${{ secrets.TEST_AZURE_ORG }}
  run: |
    poetry run mgit login \
      --provider azure-devops \
      --org $AZURE_DEVOPS_ORG \
      --token $AZURE_DEVOPS_PAT
    poetry run mgit config --show

# Test cloning functionality
- name: Test multi-repo clone
  run: |
    poetry run mgit clone-all \
      test-project \
      ./test-repos \
      --concurrency 4 \
      --provider github

# Test monitoring server
- name: Test monitoring endpoints
  run: |
    poetry run mgit monitor start --port 8080 &
    sleep 5
    curl -f http://localhost:8080/health
    curl -f http://localhost:8080/metrics
    pkill -f "mgit monitor"
```

### Performance Testing
```yaml
- name: Performance benchmark
  run: |
    # Clone 50 repos and measure time
    time poetry run mgit clone-all \
      large-project \
      ./perf-test \
      --concurrency 10 \
      --provider github \
      --stats
      
    # Generate performance report
    poetry run python scripts/analyze-performance.py \
      --input ./perf-test/.mgit/stats.json \
      --output performance-report.html
      
  - name: Upload performance report
    uses: actions/upload-artifact@v4
    with:
      name: performance-report
      path: performance-report.html
```

This comprehensive reference provides:
1. Complete GitHub Actions syntax and features
2. Security best practices and scanning
3. Python-specific CI/CD patterns
4. mgit project-specific requirements
5. Multi-provider testing strategies
6. Performance benchmarking
7. Release automation
8. Docker multi-platform builds
9. Integration testing patterns
10. Monitoring and notifications

The document is optimized for LLM consumption with clear examples, patterns, and best practices that can be directly applied to the mgit project.