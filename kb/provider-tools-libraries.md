# Provider CLI Tools and Libraries Reference

## Azure DevOps

### Official CLI Tools
- **Azure CLI with DevOps Extension**
  - Command: `az devops`
  - Installation: `az extension add --name azure-devops`
  - Authentication: PAT or Azure AD
  - Features: Full API coverage, project/repo/pipeline management

### Python Libraries
- **azure-devops** (Official SDK)
  - Package: `azure-devops>=7.1.0`
  - Documentation: https://github.com/Microsoft/azure-devops-python-api
  - Current usage in mgit: Yes
  - Features: Complete API coverage, async support

### Alternative Libraries
- **python-vsts**: Older, deprecated in favor of azure-devops
- **requests + REST API**: Direct API calls possible but not recommended

## GitHub

### Official CLI Tools
- **GitHub CLI (gh)**
  - Command: `gh`
  - Installation: `brew install gh` / `apt install gh`
  - Authentication: OAuth, PAT, SSH
  - Features: Repos, PRs, issues, actions, full API coverage
  - Bulk operations: Limited, requires scripting

### Python Libraries
- **PyGithub**
  - Package: `PyGithub>=2.1.0`
  - Documentation: https://pygithub.readthedocs.io/
  - Features: Complete API v3 coverage, pagination support
  - Authentication: PAT, OAuth, GitHub App

- **github3.py**
  - Package: `github3.py>=3.2.0`
  - More Pythonic API design
  - Better async support

- **httpx + GitHub REST/GraphQL API**
  - Direct API access for custom implementations
  - GraphQL for complex queries

### GitHub-Specific Considerations
- No project hierarchy (flat org/repo structure)
- Organizations vs User accounts
- GitHub Projects (kanban boards) != Azure DevOps Projects
- Repository topics/labels for grouping
- GitHub Apps for better rate limits

## BitBucket Cloud

### Official CLI Tools
- **BitBucket CLI** (Limited official support)
  - Mostly via REST API
  - Some third-party tools available

### Python Libraries
- **atlassian-python-api**
  - Package: `atlassian-python-api>=3.41.0`
  - Documentation: https://atlassian-python-api.readthedocs.io/
  - Features: BitBucket Cloud & Server, Jira, Confluence
  - Authentication: App passwords, OAuth 2.0

- **python-bitbucket**
  - Package: `python-bitbucket`
  - Simpler API, less maintained
  
- **pybitbucket**
  - Package: `pybitbucket`
  - Official Atlassian library (deprecated)

### BitBucket-Specific Considerations
- Workspace (formerly Team) -> Project (optional) -> Repository
- App passwords recommended over basic auth
- Projects are optional grouping mechanism
- Different API versions (1.0 deprecated, 2.0 current)

## GitLab (Future Consideration)

### Official CLI Tools
- **GitLab CLI (glab)**
  - Command: `glab`
  - Similar to GitHub CLI

### Python Libraries
- **python-gitlab**
  - Package: `python-gitlab>=3.15.0`
  - Official library
  - Excellent API coverage

## Authentication Methods Comparison

| Provider | Methods | Recommended | Token Scope Requirements |
|----------|---------|-------------|-------------------------|
| Azure DevOps | PAT, Azure AD | PAT | Code (Read), Project (Read) |
| GitHub | PAT, OAuth, GitHub App, SSH | PAT/GitHub App | repo, read:org |
| BitBucket | App Password, OAuth 2.0 | App Password | repository:read, account:read |

## API Rate Limits

| Provider | Unauthenticated | Authenticated | Enterprise/Paid |
|----------|-----------------|---------------|-----------------|
| Azure DevOps | N/A (auth required) | No official limit | No official limit |
| GitHub | 60/hour | 5,000/hour | 15,000/hour |
| BitBucket | 60/hour | 1,000/hour | Higher limits |

## Bulk Operation Support

| Provider | Native Bulk Clone | API Batch Support | Pagination |
|----------|------------------|-------------------|------------|
| Azure DevOps | No | No | Yes (continuation tokens) |
| GitHub | No | GraphQL batching | Yes (cursor/page) |
| BitBucket | No | No | Yes (page-based) |

## Common Patterns Across Providers

1. **Authentication Token in Git URL**
   - Azure DevOps: `https://pat@dev.azure.com/...`
   - GitHub: `https://token@github.com/...`
   - BitBucket: `https://username:app-password@bitbucket.org/...`

2. **Repository Listing**
   - All require authenticated API calls
   - All support pagination
   - All return similar metadata (name, clone URLs, default branch)

3. **Error Handling**
   - 401: Authentication failure
   - 403: Permission denied
   - 404: Resource not found
   - 429: Rate limit exceeded

## Library Selection Criteria

For mgit multi-provider support, recommended libraries:

1. **Azure DevOps**: Continue with `azure-devops` (already in use)
2. **GitHub**: `PyGithub` - mature, well-documented, full coverage
3. **BitBucket**: `atlassian-python-api` - official support, active development

## Alternative Approach: Direct REST API

Using `httpx` for all providers:
- Pros: Consistent interface, full control, async native
- Cons: More code, need to handle pagination/auth manually

## References

- Azure DevOps REST API: https://docs.microsoft.com/en-us/rest/api/azure/devops/
- GitHub REST API v3: https://docs.github.com/en/rest
- BitBucket Cloud REST API: https://developer.atlassian.com/cloud/bitbucket/rest/
- Comparison of Git hosting services: https://en.wikipedia.org/wiki/Comparison_of_source-code-hosting_facilities