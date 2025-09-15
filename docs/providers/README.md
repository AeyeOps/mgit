# Provider Documentation

This directory contains comprehensive documentation for using mgit with different Git providers.

## Usage Guides

Step-by-step guides for each supported provider:

- **[Azure DevOps Usage Guide](./azure-devops-usage-guide.md)** - Complete guide for Azure DevOps/TFS integration
- **[GitHub Usage Guide](./github-usage-guide.md)** - Comprehensive GitHub and GitHub Enterprise usage
- **[BitBucket Usage Guide](./bitbucket-usage-guide.md)** - Full BitBucket Cloud and Server documentation

## Comparison and Features

- **[Provider Comparison Guide](./provider-comparison-guide.md)** - Detailed comparison of all three providers
- **[Provider Feature Matrix](./provider-feature-matrix.md)** - Feature availability across providers

## Technical Documentation

- **[Repository Filtering Design](./repository-filtering-design.md)** - How filtering works across providers
- **[BitBucket Hierarchical Filtering](./bitbucket-hierarchical-filtering.md)** - BitBucket-specific filtering details

## Configuration

- **[Configuration Examples](../configuration/mgit-configuration-examples.md)** - Complete configuration examples for all providers

## Quick Start

### Azure DevOps
```bash
mgit login --provider azuredevops --org https://dev.azure.com/yourorg --token YOUR_PAT --name work_ado
mgit sync "yourorg/YourProject/*" ./repos --provider work_ado
```

### GitHub
```bash
mgit login --provider github --token ghp_xxxxxxxxxxxx --name github_personal
mgit sync "your-org/*/*" ./repos --provider github_personal
```

### BitBucket
```bash
mgit login --provider bitbucket --name team_bb
mgit sync "your-workspace/*/*" ./repos --provider team_bb
```

## Provider Selection Guide

- **Choose Azure DevOps** if you need enterprise features, project organization, and Azure integration
- **Choose GitHub** if you want the best developer experience, open source features, and modern CI/CD
- **Choose BitBucket** if you use the Atlassian ecosystem (Jira, Confluence) or need workspace organization

## Authentication Quick Reference

| Provider | Auth Method | Format | Where to Create |
|----------|------------|--------|-----------------|
| Azure DevOps | Personal Access Token | Any string | User Settings → Personal access tokens |
| GitHub | Personal Access Token | `ghp_` + 40 chars | Settings → Developer settings → Personal access tokens |
| BitBucket | App Password | Any string | Personal settings → App passwords |

## Need Help?

- Check the [Troubleshooting Guide](../configuration/mgit-configuration-examples.md#troubleshooting-guide) for common issues
- Review provider-specific usage guides for detailed examples
- See the [Provider Comparison Guide](./provider-comparison-guide.md) for feature differences
