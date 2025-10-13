# Provider Comparison Guide

This guide compares the three supported mgit providers (Azure DevOps, GitHub, and BitBucket) to help you understand their differences and choose the right approach for each platform.

## Table of Contents
- [Quick Comparison Table](#quick-comparison-table)
- [Repository Organization](#repository-organization)
- [Authentication Methods](#authentication-methods)
- [API Differences](#api-differences)
- [Feature Comparison](#feature-comparison)
- [When to Use Each Provider](#when-to-use-each-provider)
- [Migration Between Providers](#migration-between-providers)

## Quick Comparison Table

| Feature | Azure DevOps | GitHub | BitBucket |
|---------|--------------|---------|-----------|
| **Repository Organization** | Projects → Repositories | Organizations → Repositories | Workspaces → Projects → Repositories |
| **Authentication** | Personal Access Token (PAT) | Personal Access Token / OAuth | App Password / OAuth |
| **API Style** | REST + OData | REST + GraphQL | REST |
| **Rate Limits** | 1000/min (auth) | 5000/hour (auth) | 1000/hour (auth) |
| **Free Private Repos** | Yes (5 users) | Yes (limited) | Yes (5 users) |
| **CI/CD Integration** | Azure Pipelines | GitHub Actions | BitBucket Pipelines |
| **Self-Hosted Option** | Azure DevOps Server | GitHub Enterprise | BitBucket Server |
| **Primary Use Case** | Enterprise/.NET | Open Source/General | Small Teams/Atlassian |

## Repository Organization

### Azure DevOps: Project-Based

```
Azure DevOps Organization (myorg)
├── Project: DataEngineering
│   ├── data-pipeline-etl
│   ├── data-warehouse
│   └── analytics-api
├── Project: FrontendApps
│   ├── customer-portal
│   ├── admin-dashboard
│   └── mobile-app
└── Project: Infrastructure
    ├── terraform-modules
    ├── kubernetes-configs
    └── ci-cd-templates
```

**Key Characteristics:**
- Repositories exist within Projects
- Projects provide additional organization (boards, pipelines, artifacts)
- Repository names must be unique within a project
- Access control at project and repository level

**mgit Usage:**
```bash
# Sync all repos from a project (org/project/repo pattern)
mgit sync "myorg/DataEngineering/*" ./data-eng --provider work_ado
```

### GitHub: Organization-Based

```
GitHub
├── Personal Account (myusername)
│   ├── personal-website
│   ├── dotfiles
│   └── learning-rust
└── Organizations
    ├── AeyeOps
    │   ├── infrastructure
    │   ├── backend-api
    │   └── frontend-app
    └── CompanyOrg
        ├── product-a
        ├── product-b
        └── shared-libraries
```

**Key Characteristics:**
- Flat structure under organizations or users
- No built-in project grouping (use naming conventions)
- Repository names must be unique per owner
- Granular access control with teams

**mgit Usage:**
```bash
# Sync personal repos (use your username)
mgit sync "your-username/*/*" ./personal-repos --provider github_personal

# Sync organization repos
mgit sync "AeyeOps/*/*" ./aeyeops-repos --provider github_org
mgit sync "myusername/*/*" ./myusername-repos --provider github_personal
```

### BitBucket: Workspace-Based with Optional Projects

```
BitBucket
├── Personal Workspace (username)
│   ├── personal-project
│   └── experiments
└── Team Workspaces
    └── myworkspace
        ├── Project: Web Platform
        │   ├── frontend-react
        │   ├── backend-api
        │   └── shared-components
        ├── Project: Mobile Apps
        │   ├── ios-app
        │   └── android-app
        └── Repositories (no project)
            ├── documentation
            └── scripts
```

**Key Characteristics:**
- Workspaces are the top-level container
- Projects within workspaces are optional
- Can have repos directly in workspace or in projects
- Repository slugs must be unique per workspace

**mgit Usage:**
```bash
# Sync all repos in a workspace (project segment ignored by BitBucket)
mgit sync "myworkspace/*/*" ./myworkspace-repos --provider bitbucket_team
```

## Authentication Methods

### Azure DevOps Authentication

**Personal Access Tokens (PAT):**
- Primary authentication method
- Scoped permissions (Code, Work Items, Build, etc.)
- Maximum 1-year expiration
- Can have multiple PATs with different scopes

```bash
# Creating PAT:
# 1. User Settings → Personal Access Tokens
# 2. Set scopes: Code (Read & Write), Project (Read)
# 3. Copy token immediately

mgit login --provider azuredevops --org https://dev.azure.com/myorg --token YOUR_PAT
```

**Alternative Methods:**
- OAuth (for applications)
- Azure AD authentication (enterprise)
- SSH keys (for Git operations only)

### GitHub Authentication

**Personal Access Tokens (Classic):**
- Traditional token format (`ghp_...`)
- Broad scopes (repo, user, org, etc.)
- No expiration option available
- Simple to use with mgit

```bash
# Classic token creation:
# 1. Settings → Developer settings → Personal access tokens → Classic
# 2. Select scopes: repo, read:org
# 3. Generate and copy

mgit login --provider github --token ghp_xxxxxxxxxxxx
```

**Fine-grained Personal Access Tokens:**
- New format (`github_pat_...`)
- Repository-specific permissions
- Mandatory expiration
- More secure but complex

**Alternative Methods:**
- OAuth Apps
- GitHub Apps
- SSH keys (Git operations)
- SAML SSO (enterprise)

### BitBucket Authentication

**App Passwords:**
- Not called "PAT" but similar concept
- Specific permission sets
- No expiration
- Can have multiple app passwords

```bash
# App password creation:
# 1. Personal settings → App passwords
# 2. Select permissions: Repositories (Read, Write)
# 3. Create and copy

mgit login --provider bitbucket --org YOUR_WORKSPACE --token APP_PASSWORD
```

**Alternative Methods:**
- OAuth 2.0
- SSH keys
- Repository Access Keys (read-only)
- Atlassian account linking

## API Differences

### API Styles and Endpoints

| Provider | API Style | Base URL | Documentation |
|----------|-----------|----------|---------------|
| Azure DevOps | REST + OData | `https://dev.azure.com/{org}/_apis` | [docs.microsoft.com](https://docs.microsoft.com/en-us/rest/api/azure/devops) |
| GitHub | REST v3 + GraphQL v4 | `https://api.github.com` | [docs.github.com](https://docs.github.com/en/rest) |
| BitBucket | REST v2 | `https://api.bitbucket.org/2.0` | [developer.atlassian.com](https://developer.atlassian.com/bitbucket/api/2/reference/) |

### Pagination Handling

**Azure DevOps:**
```json
{
  "value": [...],
  "count": 100,
  "@odata.nextLink": "https://..."
}
```

**GitHub:**
```http
Link: <https://api.github.com/...?page=2>; rel="next"
X-RateLimit-Remaining: 4999
```

**BitBucket:**
```json
{
  "values": [...],
  "pagelen": 10,
  "next": "https://api.bitbucket.org/2.0/..."
}
```

### Rate Limiting Comparison

| Provider | Anonymous | Authenticated | Enterprise/Server |
|----------|-----------|---------------|-------------------|
| Azure DevOps | 100/min | 1000/min | Configurable |
| GitHub | 60/hour | 5000/hour | 15000/hour |
| BitBucket | 60/hour | 1000/hour | Configurable |

## Feature Comparison

### Repository Features

| Feature | Azure DevOps | GitHub | BitBucket |
|---------|--------------|---------|-----------|
| **Wiki** | ✅ Built-in | ✅ Built-in | ✅ Built-in |
| **Issues** | ✅ Work Items | ✅ Issues | ✅ Issues |
| **Pull Requests** | ✅ | ✅ | ✅ |
| **Code Search** | ✅ | ✅ | ✅ Limited |
| **Branch Policies** | ✅ Extensive | ✅ Protection rules | ✅ Restrictions |
| **Webhooks** | ✅ | ✅ | ✅ |
| **Git LFS** | ✅ | ✅ | ✅ |

### CI/CD Integration

**Azure DevOps:**
- Azure Pipelines (YAML/Classic)
- Deep integration with Azure services
- Extensive marketplace
- Self-hosted agents

**GitHub:**
- GitHub Actions
- Marketplace with thousands of actions
- Matrix builds
- Self-hosted runners

**BitBucket:**
- BitBucket Pipelines
- Atlassian ecosystem integration
- Pipes marketplace
- Self-hosted runners (limited)

### Collaboration Features

| Feature | Azure DevOps | GitHub | BitBucket |
|---------|--------------|---------|-----------|
| **Code Review** | ✅ Advanced | ✅ Advanced | ✅ Good |
| **Inline Comments** | ✅ | ✅ | ✅ |
| **Review Requirements** | ✅ | ✅ | ✅ |
| **Auto-merge** | ✅ | ✅ | ✅ |
| **Draft PRs** | ✅ | ✅ | ✅ |
| **Code Owners** | ✅ | ✅ CODEOWNERS | ✅ Limited |

## When to Use Each Provider

### Use Azure DevOps When:

✅ **Enterprise Environment**
- Working in Microsoft-centric organizations
- Need integration with Azure services
- Require comprehensive project management

✅ **Complex Projects**
- Need boards, pipelines, artifacts in one place
- Want hierarchical organization (Projects)
- Require advanced work item tracking

✅ **Compliance Requirements**
- Need detailed audit logs
- Require specific compliance certifications
- Want on-premises option (Azure DevOps Server)

**Example Scenarios:**
```bash
# Enterprise .NET development
mgit sync "myorg/CoreServices/*Api*" ./core-services --provider work_ado

# Multi-project deployment
for project in WebApps Services Infrastructure; do
  mgit sync "myorg/$project/*" "./$project" --provider work_ado
done
```

### Use GitHub When:

✅ **Open Source Development**
- Building public projects
- Want community contributions
- Need maximum visibility

✅ **Modern Development**
- Using GitHub Actions for CI/CD
- Want cutting-edge features
- Need extensive third-party integrations

✅ **Developer Experience**
- Prefer clean, intuitive UI
- Want mobile app support
- Need great API/CLI tools

**Example Scenarios:**
```bash
# Open source project management
mgit sync "my-oss-org/*/*" ~/oss --provider github_oss

# Personal and org repos
mgit sync "your-username/*/*" ~/personal --provider github_personal
mgit sync "company/*/*" ~/work --provider github_work
```

### Use BitBucket When:

✅ **Atlassian Ecosystem**
- Using Jira for issue tracking
- Need Confluence integration
- Want unified Atlassian experience

✅ **Small Teams**
- Free tier suits team size
- Want simple, straightforward features
- Prefer workspace organization

✅ **Mercurial Legacy**
- Migrated from Mercurial
- Have historical requirements
- Need specific BitBucket features

**Example Scenarios:**
```bash
# Atlassian-integrated development
mgit sync "team/*/*" ./jira-integration --provider bitbucket_team

# Small team management
mgit list "startup-team/*/*" --provider bitbucket_team
```

## Migration Between Providers

### General Migration Strategy

```bash
#!/bin/bash
# migrate-repos.sh - Generic migration script

SOURCE_PROVIDER_NAME="github_personal"
SOURCE_ORG="old-org"
DEST_PROVIDER_NAME="work_ado"
DEST_PROVIDER_TYPE="azuredevops"   # one of: azuredevops|github|bitbucket
DEST_ORG="new-org"
DEST_PROJECT="MigratedRepos"

# Sync from source
mgit sync "$SOURCE_ORG/*/*" ./migration --provider "$SOURCE_PROVIDER_NAME"

# Add new remotes and push
cd ./migration
for repo in */; do
    repo_name=$(basename "$repo")
    cd "$repo"
    
    # Add destination remote
    case $DEST_PROVIDER_TYPE in
        "azuredevops")
            git remote add dest "https://dev.azure.com/$DEST_ORG/$DEST_PROJECT/_git/$repo_name"
            ;;
        "github")
            git remote add dest "https://github.com/$DEST_ORG/$repo_name"
            ;;
        "bitbucket")
            git remote add dest "https://bitbucket.org/$DEST_WORKSPACE/$repo_name"
            ;;
    esac
    
    # Push all branches and tags
    git push dest --all
    git push dest --tags
    
    cd ..
done
```

### Provider-Specific Considerations

**Migrating TO Azure DevOps:**
- Create project structure first
- Consider converting issues to work items
- Update CI/CD to Azure Pipelines
- Map teams and permissions

**Migrating TO GitHub:**
- Flatten project hierarchy
- Convert work items to issues
- Update CI/CD to Actions
- Set up CODEOWNERS files

**Migrating TO BitBucket:**
- Create workspace structure
- Decide on project organization
- Update CI/CD to Pipelines
- Configure Jira integration

### Maintaining Multiple Providers

```yaml
# ~/.config/mgit/config.yaml
# Multi-provider setup for gradual migration

providers:
  github_personal:
    url: https://github.com
    user: old-org
    token: ${GITHUB_TOKEN}

  work_ado:
    url: https://dev.azure.com/new-org
    user: azure
    token: ${AZURE_PAT}

sync_pairs:
  - source: 
      provider: github_personal
      org: old-org
      repo: important-service
    destination:
      provider: work_ado
      project: MigrationProject
      repo: important-service
```

## Best Practices by Provider

### Azure DevOps Best Practices

1. **Organize by Project**: Group related repositories
2. **Use Branch Policies**: Enforce code quality
3. **Integrate Work Items**: Link commits to tasks
4. **Leverage Artifacts**: Share packages internally

### GitHub Best Practices

1. **Use Organizations**: Even for personal projects
2. **Enable Security Features**: Dependabot, code scanning
3. **Leverage Actions**: Automate everything
4. **Document Well**: README, Wiki, Pages

### BitBucket Best Practices

1. **Organize by Workspace**: Logical team grouping
2. **Use Projects**: When you have many repos
3. **Integrate with Jira**: Full traceability
4. **Configure Pipelines**: Built-in CI/CD

## Performance Considerations

### Sync Performance

```bash
# GitHub (typically fastest)
mgit sync "my-org/*/*" ./repos --provider github_personal --concurrency 20

# Azure DevOps (good parallelization)
mgit sync "myorg/MyProject/*" ./repos --provider work_ado --concurrency 15

# BitBucket (conservative due to rate limits)
mgit sync "my-workspace/*/*" ./repos --provider bitbucket_team --concurrency 5
```

### API Performance

| Operation | Azure DevOps | GitHub | BitBucket |
|-----------|--------------|---------|-----------|
| List Repos | Fast (OData) | Fast | Moderate |
| Clone | Fast | Fastest | Moderate |
| Bulk Operations | Good | Excellent | Limited |

## Conclusion

Choose your provider based on:

1. **Ecosystem**: What tools does your team use?
2. **Scale**: How many repos and developers?
3. **Features**: What specific features do you need?
4. **Budget**: What can you afford for private repos?
5. **Integration**: What other services do you use?

Remember that mgit supports all three providers equally well, so you can:
- Use multiple providers simultaneously
- Migrate between providers easily
- Maintain synchronized mirrors
- Choose the best provider for each project

## Related Documentation

- [Azure DevOps Usage Guide](./azure-devops-usage-guide.md)
- [GitHub Usage Guide](./github-usage-guide.md)  
- [BitBucket Usage Guide](./bitbucket-usage-guide.md)
- [Provider Feature Matrix](./provider-feature-matrix.md)
- [Configuration Examples](../configuration/mgit-configuration-examples.md)
