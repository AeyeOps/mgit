# mgit Documentation Index

Documentation for the mgit multi-provider git management tool, organized by theme.

## Directory Structure

### `/architecture/`
Core architectural designs and system overview
- `architecture.md` - Original system architecture
- `multi-provider-design.md` - Multi-provider support design
- `provider-abstraction-architecture.md` - Provider abstraction layer details

### `/configuration/`
Configuration system documentation
- `yaml-config-loader-architecture.md` - YAML configuration loader implementation
- `yaml-configuration-design.md` - YAML configuration schema and structure
- `configuration-schema-design.md` - Detailed configuration schema

### `/providers/`
Provider-specific documentation and features
- `provider-feature-matrix.md` - Feature comparison across providers
- `bitbucket-hierarchical-filtering.md` - BitBucket's three-tier filtering
- `repository-filtering-design.md` - Repository filtering patterns

### `/cli-design/`
Command-line interface design
- `cli-subcommand-design.md` - Subcommand-based CLI structure
- `command-structure-design.md` - Command hierarchy and patterns

### `/framework/`
Advanced frameworks and patterns
- `mawep-framework-design.md` - Multi-Agent Workflow Execution Process

### `/kb/`
Knowledge base and reference materials
- `provider-tools-libraries.md` - Provider-specific tools and libraries reference

## Quick Links

- [Getting Started](../README.md)
- [Architecture Overview](architecture/architecture.md)
- [Configuration Guide](configuration/yaml-configuration-design.md)
- [Provider Setup](providers/provider-feature-matrix.md)
- [CLI Usage](cli-design/cli-subcommand-design.md)

## Design Principles

1. **Fail Fast** - No fallbacks, no workarounds, explicit configuration required
2. **Multi-Provider** - Support for Azure DevOps, GitHub, and BitBucket
3. **YAML Configuration** - Clear, hierarchical configuration with local overrides
4. **Subcommand CLI** - Intuitive command structure (e.g., `mgit config show`)
5. **Provider Abstraction** - Clean separation between provider implementations