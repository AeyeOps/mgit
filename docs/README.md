# mgit Documentation

> **Comprehensive documentation for mgit - the multi-provider Git repository manager**

[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://github.com/AeyeOps/mgit/tree/main/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)

## 📚 Documentation Overview

This documentation provides complete guidance for using mgit across Azure DevOps, GitHub, and BitBucket. Whether you're managing a handful of repositories or thousands across multiple providers, these guides will help you get the most out of mgit.

### 🚀 Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| **Get started quickly** | [Main README Quick Start](../README.md#5-minute-quick-start) |
| **Set up a provider** | [Provider Guides](#provider-specific-guides) |
| **Configure mgit** | [Configuration Guide](configuration/mgit-configuration-examples.md) |
| **Learn query patterns** | [Query Patterns Guide](usage/query-patterns.md) |
| **Monitor operations** | [Monitoring Guide](monitoring/README.md) |
| **Compare providers** | [Provider Comparison](providers/provider-comparison-guide.md) |

## 📖 Documentation Structure

### Core Documentation

#### ⚙️ [Configuration](configuration/)
Comprehensive configuration guidance for all scenarios.

- **[Configuration Examples](configuration/mgit-configuration-examples.md)**
  - Multi-provider setup examples
  - Environment variable configuration
  - Advanced configuration patterns
  - Security best practices
  - Common troubleshooting solutions

#### 🔍 [Usage Patterns](usage/)
Advanced usage patterns and techniques.

- **[Query Patterns Guide](usage/query-patterns.md)**
  - Pattern syntax and wildcards
  - Provider-specific behaviors
  - Performance optimization
  - Real-world query examples
  - DevOps team workflows

#### 📊 [Monitoring & Observability](monitoring/)
Enterprise-grade monitoring and observability features.

- **[Monitoring Guide](monitoring/README.md)**
  - Structured logging with correlation IDs
  - Prometheus metrics collection
  - Health checks for Kubernetes
  - Performance monitoring
  - Grafana dashboards
  - Alert configuration

### Provider-Specific Guides

#### 🔗 [Provider Documentation](providers/)
Detailed guides for each supported Git provider.

- **[Provider Overview](providers/README.md)** - Quick start for all providers
- **[Azure DevOps Guide](providers/azure-devops-usage-guide.md)** - Enterprise integration with Azure DevOps
- **[GitHub Guide](providers/github-usage-guide.md)** - Complete GitHub integration
- **[BitBucket Guide](providers/bitbucket-usage-guide.md)** - BitBucket workspace management
- **[Provider Comparison](providers/provider-comparison-guide.md)** - Choose the right provider
- **[Feature Matrix](providers/provider-feature-matrix.md)** - Detailed feature support

## 🎯 Common Use Cases

### DevOps Teams
- [Clone all microservices](usage/query-patterns.md#devops-team-patterns) - `mgit clone-all "*/backend/*-service" ./services`
- [Update infrastructure repos](usage/query-patterns.md#infrastructure-management) - `mgit pull-all "*/*/terraform-*" ./infra`
- [Monitor repository health](monitoring/README.md#health-checks) - `mgit status ./repos --all`

### Enterprise Organizations
- [Multi-provider setup](configuration/mgit-configuration-examples.md#multiple-provider-configuration) - Configure Azure DevOps + GitHub
- [Large-scale operations](usage/query-patterns.md#performance-optimization) - Handle 1000+ repositories
- [Security compliance](configuration/mgit-configuration-examples.md#security-best-practices) - Credential management

### Migration Scenarios
- [Repository discovery](usage/query-patterns.md#migration-and-audit-patterns) - Find all repos to migrate
- [Bulk cloning](../README.md#clone-multiple-repositories) - Clone entire organizations
- [Cross-provider search](providers/provider-comparison-guide.md#migration-considerations) - Find similar repos

## 🔧 Advanced Topics

### Performance & Scale
- [Concurrency tuning](configuration/mgit-configuration-examples.md#performance-tuning) - Optimize for your network
- [Rate limit handling](providers/provider-feature-matrix.md#rate-limits) - Provider-specific limits
- [Memory optimization](monitoring/README.md#performance-monitoring) - Handle large repository sets

### Security & Compliance
- [Credential security](configuration/mgit-configuration-examples.md#security-best-practices) - Token management
- [Audit logging](monitoring/README.md#structured-logging) - Track all operations
- [Network security](configuration/mgit-configuration-examples.md#proxy-configuration) - Proxy and SSL setup

### Integration & Automation
- [CI/CD integration](usage/query-patterns.md#cicd-integration-patterns) - Pipeline examples
- [Monitoring integration](monitoring/README.md#prometheus-integration) - Export metrics
- [Scripting examples](configuration/mgit-configuration-examples.md#automation-scripts) - Automation patterns

## 📋 Quick Reference

### Essential Commands
```bash
# Provider setup
mgit login --provider github --name work

# Find repositories
mgit list "myorg/*/*" --limit 10

# Clone repositories
mgit clone-all "*/backend/*" ./backend-repos

# Update repositories
mgit pull-all "myproject" ./repos

# Check status
mgit status ./repos --all
```

### Configuration Locations
- **Config file**: `~/.config/mgit/config.yaml`
- **Cache directory**: `~/.cache/mgit/`
- **Log files**: `~/.local/share/mgit/logs/`

### Provider Authentication
| Provider | Auth Method | Required Scopes |
|----------|-------------|-----------------|
| Azure DevOps | Personal Access Token | Code (Read/Write), Project (Read) |
| GitHub | Personal Access Token | repo, read:org |
| BitBucket | App Password | Repositories (Read/Write), Workspaces (Read) |

## 🐛 Troubleshooting

### Common Issues
- **[Authentication failures](configuration/mgit-configuration-examples.md#authentication-issues)** - Token and permission problems
- **[Network issues](configuration/mgit-configuration-examples.md#network-and-connectivity)** - Proxy and SSL configuration
- **[Performance problems](monitoring/README.md#performance-monitoring)** - Slow operations
- **[Configuration errors](configuration/mgit-configuration-examples.md#configuration-file-issues)** - YAML syntax and field names

### Getting Help
1. Check the relevant guide in this documentation
2. Use `mgit --help` or `mgit <command> --help`
3. Enable debug mode: `mgit --debug <command>`
4. [Report an issue](https://github.com/AeyeOps/mgit/issues)

## 🤝 Contributing

We welcome contributions to both code and documentation!

- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute
- **[Security Policy](../SECURITY.md)** - How to report vulnerabilities and our procedures
- **[Code of Conduct](../CODE_OF_CONDUCT.md)** - Community guidelines

### Improving Documentation
1. Fork the repository
2. Create a feature branch
3. Make your improvements
4. Submit a pull request

Documentation style guidelines:
- Use clear, concise language
- Include practical examples
- Add troubleshooting tips
- Keep provider-specific details in provider guides

## 📈 Version History

See [CHANGELOG.md](../CHANGELOG.md) for version history and migration guides.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

**Need more help?** [Open an issue](https://github.com/AeyeOps/mgit/issues) or check our [Discussions](https://github.com/AeyeOps/mgit/discussions) forum.