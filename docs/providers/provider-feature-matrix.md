# Provider Feature Matrix

## Core Features Comparison

| Feature | Azure DevOps | GitHub | BitBucket Cloud |
|---------|--------------|--------|-----------------|
| **Hierarchy** | Org → Project → Repo | Org/User → Repo | Workspace → Project → Repo |
| **Project Concept** | Required | No (use topics/teams) | Optional |
| **Max Repos/Project** | Unlimited | N/A | Unlimited |
| **Free Private Repos** | 5 users | Unlimited | 5 users |
| **API Rate Limits** | No official limit | 5,000/hour (auth) | 1,000/hour |
| **Bulk Operations** | Via API only | Via API only | Via API only |

## Authentication Methods

| Method | Azure DevOps | GitHub | BitBucket Cloud |
|--------|--------------|--------|-----------------|
| **Personal Access Token** | ✅ Primary | ✅ Supported | ❌ Deprecated |
| **OAuth 2.0** | ✅ Supported | ✅ Supported | ✅ Supported |
| **App Passwords** | ❌ | ❌ | ✅ Primary |
| **SSH Keys** | ✅ For Git | ✅ For Git | ✅ For Git |
| **API Keys** | ❌ | ❌ | ✅ Legacy |
| **Service Principal** | ✅ | ✅ GitHub Apps | ❌ |
| **2FA Compatible** | ✅ | ✅ | ✅ |

## Repository Features

| Feature | Azure DevOps | GitHub | BitBucket Cloud |
|---------|--------------|--------|-----------------|
| **Public Repos** | ✅ | ✅ | ✅ |
| **Private Repos** | ✅ | ✅ | ✅ |
| **Forking** | ✅ Limited | ✅ Full | ✅ Full |
| **Templates** | ❌ | ✅ | ❌ |
| **Archives** | ✅ Disabled state | ✅ | ❌ |
| **Mirrors** | ❌ | ❌ | ✅ |
| **Wikis** | ✅ Separate | ✅ Integrated | ✅ Integrated |
| **LFS Support** | ✅ | ✅ | ✅ |

## API Capabilities

| Feature | Azure DevOps | GitHub | BitBucket Cloud |
|---------|--------------|--------|-----------------|
| **REST API** | ✅ v7.0 | ✅ v3 | ✅ v2.0 |
| **GraphQL API** | ❌ | ✅ v4 | ❌ |
| **Webhooks** | ✅ | ✅ | ✅ |
| **Pagination** | Continuation Token | Link headers | Page-based |
| **Batch Operations** | ❌ | ✅ GraphQL | ❌ |
| **Async Operations** | ✅ Some | ❌ | ❌ |
| **SDK Quality** | ✅ Official | ✅ Multiple | ⚠️ Limited |

## Search and Filtering

| Feature | Azure DevOps | GitHub | BitBucket Cloud |
|---------|--------------|--------|-----------------|
| **Code Search** | ✅ Advanced | ✅ Advanced | ✅ Basic |
| **Repo Name Filter** | ✅ | ✅ | ✅ |
| **Language Filter** | ❌ | ✅ | ✅ |
| **Topic/Tag Filter** | ❌ | ✅ Topics | ❌ |
| **Size Filter** | ❌ | ✅ | ❌ |
| **Date Filters** | ✅ | ✅ | ✅ |
| **Fork Filter** | ❌ | ✅ | ✅ |
| **Archive Filter** | ✅ | ✅ | ❌ |

## Permissions and Access

| Feature | Azure DevOps | GitHub | BitBucket Cloud |
|---------|--------------|--------|-----------------|
| **Granular Permissions** | ✅ Very detailed | ✅ Good | ✅ Good |
| **Team Management** | ✅ | ✅ | ✅ |
| **Token Scopes** | ✅ | ✅ Fine-grained | ⚠️ Limited |
| **IP Restrictions** | ✅ Enterprise | ✅ Enterprise | ✅ Premium |
| **SSO Support** | ✅ | ✅ | ✅ |

## CI/CD Integration

| Feature | Azure DevOps | GitHub | BitBucket Cloud |
|---------|--------------|--------|-----------------|
| **Built-in CI/CD** | ✅ Pipelines | ✅ Actions | ✅ Pipelines |
| **YAML Config** | ✅ | ✅ | ✅ |
| **Marketplace/Extensions** | ✅ | ✅ | ✅ |
| **Self-hosted Runners** | ✅ | ✅ | ✅ |
| **Free Minutes** | 1,800/month | 2,000/month | 50/month |

## Repository Metadata

| Field | Azure DevOps | GitHub | BitBucket Cloud |
|-------|--------------|--------|-----------------|
| **Name** | ✅ | ✅ | ✅ |
| **Description** | ✅ | ✅ | ✅ |
| **Default Branch** | ✅ | ✅ | ✅ |
| **Size** | ✅ | ✅ | ✅ |
| **Language** | ❌ | ✅ Auto-detected | ✅ |
| **Topics/Tags** | ❌ | ✅ | ❌ |
| **Created Date** | ✅ | ✅ | ✅ |
| **Last Updated** | ✅ | ✅ | ✅ |
| **Clone URLs** | ✅ HTTPS/SSH | ✅ HTTPS/SSH/Git | ✅ HTTPS/SSH |
| **Fork Count** | ❌ | ✅ | ✅ |
| **Star Count** | ❌ | ✅ | ❌ |
| **Visibility** | ✅ | ✅ | ✅ |
| **Archived Status** | ✅ isDisabled | ✅ | ❌ |

## Bulk Operation Support

| Operation | Azure DevOps | GitHub | BitBucket Cloud |
|-----------|--------------|--------|-----------------|
| **List All Repos** | ✅ By project | ✅ By org | ✅ By workspace |
| **Pagination Required** | ✅ | ✅ | ✅ |
| **Max Items/Page** | 100 | 100 | 100 |
| **Clone with Token** | ✅ PAT in URL | ✅ Token in URL | ✅ App Pass in URL |
| **Bulk Create** | ❌ | ❌ | ❌ |
| **Bulk Delete** | ❌ | ❌ | ❌ |
| **Bulk Archive** | ❌ | ❌ GraphQL | ❌ |
| **Bulk Transfer** | ❌ | ✅ Org only | ❌ |

## URL Patterns

### Repository URLs
| Provider | Pattern | Example |
|----------|---------|---------|
| **Azure DevOps** | `https://{instance}/{org}/{project}/_git/{repo}` | `https://dev.azure.com/contoso/MyProject/_git/my-repo` |
| **GitHub** | `https://github.com/{owner}/{repo}` | `https://github.com/octocat/hello-world` |
| **BitBucket** | `https://bitbucket.org/{workspace}/{repo}` | `https://bitbucket.org/atlassian/python-bitbucket` |

### API Endpoints
| Provider | Base URL | Example |
|----------|----------|---------|
| **Azure DevOps** | `https://dev.azure.com/{org}` | `GET /{project}/_apis/git/repositories?api-version=7.0` |
| **GitHub** | `https://api.github.com` | `GET /orgs/{org}/repos` |
| **BitBucket** | `https://api.bitbucket.org/2.0` | `GET /repositories/{workspace}` |

## Feature Gaps and Workarounds

### Azure DevOps
- **No Topics/Tags**: Use naming conventions or custom properties
- **No Language Detection**: Parse files manually or use extensions
- **Limited Forking**: Use import feature instead

### GitHub
- **No Project Hierarchy**: Use naming prefixes (e.g., `project-repo`)
- **No Built-in Grouping**: Use GitHub Projects or Teams
- **Rate Limits**: Use conditional requests and caching

### BitBucket
- **Limited API**: Some operations require multiple calls
- **No Archives**: Use access restrictions instead
- **Fewer Integrations**: Rely on webhooks for custom integrations

## Performance Considerations

| Aspect | Azure DevOps | GitHub | BitBucket Cloud |
|--------|--------------|--------|-----------------|
| **API Response Time** | Average | Fast | Average |
| **Pagination Efficiency** | Good | Excellent | Good |
| **Concurrent Requests** | Unlimited* | Rate limited | Rate limited |
| **Bulk Data Export** | ❌ | ✅ Via GraphQL | ❌ |
| **Webhook Reliability** | Good | Excellent | Good |

*No official limits but be respectful of resources

## Cost Implications

| Feature | Azure DevOps | GitHub | BitBucket Cloud |
|---------|--------------|--------|-----------------|
| **Free Tier** | 5 users | Unlimited public | 5 users |
| **Private Repos** | Unlimited | Unlimited | Unlimited |
| **Storage Limits** | 250GB/project | 100GB/repo | 10GB/repo |
| **LFS Storage** | 1GB free | 1GB free | 1GB free |
| **CI/CD Minutes** | 1,800/month | 2,000/month | 50/month |

## mgit Implementation Priority

### Phase 1 (MVP)
- ✅ List repositories
- ✅ Clone with authentication
- ✅ Pull updates
- ✅ Handle pagination

### Phase 2 (Enhanced)
- Repository filtering
- Progress tracking
- Error recovery
- Concurrent operations

### Phase 3 (Advanced)
- Cross-provider operations
- Bulk modifications
- Advanced search
- Provider-specific features