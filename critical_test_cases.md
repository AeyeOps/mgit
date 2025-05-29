# Critical Test Cases - Pod-3 Implementation Guide

## Immediate Implementation: Core CLI Functions

### 1. `clone_all()` Function Test Cases

```python
# test_cli_commands.py

class TestCloneAllCommand:
    """Test the core clone_all functionality - 0% current coverage"""
    
    def test_clone_all_basic_success(self):
        """Test successful cloning with single provider"""
        # Mock provider.list_repositories()
        # Mock git.clone() operations
        # Verify repository discovery and cloning
        
    def test_clone_all_multiple_providers(self):
        """Test cloning across multiple providers"""
        # Mock GitHub, Azure DevOps, Bitbucket providers
        # Verify provider coordination
        
    def test_clone_all_with_filters(self):
        """Test repository filtering during clone"""
        # Mock filtered repository lists
        # Verify only matching repos are cloned
        
    def test_clone_all_concurrency_control(self):
        """Test concurrent clone operations"""
        # Mock multiple repo clones with semaphore
        # Verify concurrency limits respected
        
    def test_clone_all_existing_repo_handling(self):
        """Test behavior when repos already exist"""
        # Mock existing directory detection
        # Verify skip/update logic
        
    def test_clone_all_network_failure(self):
        """Test network error handling"""
        # Mock network failures during clone
        # Verify error aggregation and reporting
        
    def test_clone_all_authentication_failure(self):
        """Test auth error handling"""
        # Mock authentication failures
        # Verify user-friendly error messages
        
    def test_clone_all_filesystem_errors(self):
        """Test filesystem permission errors"""
        # Mock filesystem write failures
        # Verify graceful error handling
        
    def test_clone_all_progress_tracking(self):
        """Test progress display functionality"""
        # Mock progress callbacks
        # Verify Rich progress integration
```

### 2. `pull_all()` Function Test Cases

```python
class TestPullAllCommand:
    """Test pull_all functionality - 0% current coverage"""
    
    def test_pull_all_basic_success(self):
        """Test successful pulling multiple repos"""
        # Mock git.pull() operations
        # Verify all repos updated
        
    def test_pull_all_update_modes(self):
        """Test different update mode behaviors"""
        # Test FORCE, SKIP_EXISTING, PROMPT modes
        # Verify mode-specific logic
        
    def test_pull_all_merge_conflicts(self):
        """Test merge conflict handling"""
        # Mock git merge conflicts
        # Verify conflict reporting
        
    def test_pull_all_partial_failures(self):
        """Test mixed success/failure scenarios"""
        # Mock some repos failing, others succeeding
        # Verify error aggregation
        
    def test_pull_all_non_git_directories(self):
        """Test handling non-git directories"""
        # Mock directories without .git
        # Verify appropriate warnings/skips
        
    def test_pull_all_branch_tracking(self):
        """Test tracking branch updates"""
        # Mock different branch scenarios
        # Verify branch switching logic
```

### 3. `login()` Function Test Cases  

```python
class TestLoginCommand:
    """Test login functionality - 0% current coverage"""
    
    def test_login_azure_devops_success(self):
        """Test successful Azure DevOps authentication"""
        # Mock Azure SDK authentication
        # Verify credential storage
        
    def test_login_github_success(self):
        """Test successful GitHub authentication"""
        # Mock GitHub API authentication
        # Verify token validation
        
    def test_login_bitbucket_success(self):
        """Test successful Bitbucket authentication"""
        # Mock Bitbucket API authentication
        # Verify credential persistence
        
    def test_login_invalid_credentials(self):
        """Test invalid credential handling"""
        # Mock authentication failures
        # Verify error messages
        
    def test_login_credential_storage(self):
        """Test secure credential storage"""
        # Mock keyring/config storage
        # Verify encryption/security
        
    def test_login_environment_variables(self):
        """Test login from environment variables"""
        # Mock env var authentication
        # Verify precedence handling
        
    def test_login_organization_validation(self):
        """Test organization/workspace validation"""
        # Mock org/workspace checks
        # Verify user feedback
```

## High-Priority Provider Tests

### 4. GitHub Provider Core Functions

```python
class TestGitHubProviderCore:
    """Test critical GitHub provider functions - 13% current coverage"""
    
    def test_list_repositories_basic(self):
        """Test basic repository listing"""
        # Mock GitHub API responses
        # Verify repository parsing
        
    def test_list_repositories_pagination(self):
        """Test pagination handling"""
        # Mock paginated API responses
        # Verify all pages processed
        
    def test_authenticate_token_validation(self):
        """Test token authentication"""
        # Mock token validation API
        # Verify authentication flow
        
    def test_list_user_repositories(self):
        """Test user repository access"""
        # Mock user repo API responses
        # Verify filtering logic
        
    def test_list_organization_repositories(self):
        """Test organization repository access"""
        # Mock org repo API responses
        # Verify permission handling
        
    def test_rate_limit_handling(self):
        """Test GitHub rate limit responses"""
        # Mock rate limit errors
        # Verify backoff/retry logic
```

### 5. Bitbucket Provider Core Functions

```python
class TestBitbucketProviderCore:
    """Test critical Bitbucket provider functions - 16% current coverage"""
    
    def test_authenticate_workspace(self):
        """Test workspace authentication"""
        # Mock Bitbucket auth API
        # Verify workspace access
        
    def test_list_workspace_repositories(self):
        """Test workspace repository listing"""
        # Mock workspace repo API
        # Verify repository parsing
        
    def test_list_project_repositories(self):
        """Test project-based repository listing"""
        # Mock project repo API
        # Verify project filtering
        
    def test_workspace_enumeration(self):
        """Test workspace discovery"""
        # Mock workspace listing API
        # Verify workspace iteration
```

## Mock Strategy Implementation

### Provider API Mocks

```python
# tests/fixtures/provider_responses.py

GITHUB_REPO_RESPONSE = {
    "name": "test-repo",
    "full_name": "user/test-repo", 
    "clone_url": "https://github.com/user/test-repo.git",
    "private": False,
    # ... complete mock response
}

AZURE_DEVOPS_PROJECT_RESPONSE = {
    "name": "TestProject",
    "id": "abc-123-def",
    "url": "https://dev.azure.com/org/TestProject",
    # ... complete mock response
}

BITBUCKET_WORKSPACE_RESPONSE = {
    "name": "test-workspace",
    "slug": "test-workspace",
    "links": {
        "repositories": {
            "href": "https://api.bitbucket.org/2.0/repositories/test-workspace"
        }
    }
    # ... complete mock response
}
```

### Test Fixtures

```python
# tests/fixtures/git_repositories.py

@pytest.fixture
def mock_git_repo(tmp_path):
    """Create a mock git repository for testing"""
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "README.md").write_text("# Test Repository")
    return repo_dir

@pytest.fixture  
def mock_provider_manager():
    """Create a mock provider manager"""
    with patch('mgit.providers.manager.ProviderManager') as mock:
        mock.return_value.get_provider.return_value = Mock()
        yield mock.return_value
```

## Test Execution Priority

### Phase 1 (Week 1): Core CLI
1. `test_clone_all_basic_success()` - Prove basic functionality works
2. `test_pull_all_basic_success()` - Prove updates work
3. `test_login_azure_devops_success()` - Prove auth works
4. `test_clone_all_network_failure()` - Prove error handling works

### Phase 2 (Week 1-2): Provider Integration  
1. `test_list_repositories_basic()` for each provider
2. `test_authenticate_*()` for each provider
3. `test_*_pagination()` for providers with pagination

### Phase 3 (Week 2): Error Scenarios
1. Network failure tests
2. Authentication failure tests  
3. Filesystem error tests
4. Configuration error tests

## Success Criteria

### Coverage Targets
- `clone_all()`: 0% → 80% coverage
- `pull_all()`: 0% → 80% coverage  
- `login()`: 0% → 70% coverage
- GitHub provider: 13% → 60% coverage
- Bitbucket provider: 16% → 60% coverage

### Quality Metrics
- All critical business paths tested
- Error scenarios covered
- Mock isolation maintained
- Test execution < 30 seconds
- No flaky tests

### Implementation Verification
Each test must:
1. ✅ Mock external dependencies completely
2. ✅ Test both success and failure paths
3. ✅ Verify user-facing behavior
4. ✅ Execute in isolation
5. ✅ Provide clear failure messages

This implementation guide provides the specific test cases needed to achieve 60%+ coverage while focusing on the highest-risk, highest-impact functionality first.