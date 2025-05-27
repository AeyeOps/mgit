# CLI Subcommand Design for mgit

## Overview

This document outlines the redesigned CLI structure for mgit, moving from flag-based commands to a more intuitive subcommand structure that follows modern CLI patterns.

## Design Principles

1. **Resource-Action Pattern**: Commands follow `mgit <resource> <action>` structure
2. **Intuitive Hierarchy**: Related functionality grouped under common parent commands
3. **Consistency**: Similar patterns across all command groups
4. **Discoverability**: Easy to explore available commands

## Current vs Proposed Command Structure

### Version Information
```bash
# Current (flag-based)
mgit --version

# Proposed (subcommand)
mgit version
```

### Configuration Management
```bash
# Current
mgit config --show
mgit config --edit
mgit generate-env

# Proposed
mgit config show
mgit config edit
mgit config list
mgit config set <key> <value>
mgit config get <key>
mgit config generate
```

### Repository Operations
```bash
# Current
mgit clone-all <project> <path> [options]
mgit pull-all <project> <path> [options]

# Proposed
mgit clone all <project> <path> [options]
mgit clone single <project> <repo> <path> [options]
mgit pull all <path> [options]
mgit pull single <path> [options]
```

### Authentication
```bash
# Current
mgit login --org <url> --pat <token>
mgit login --store

# Proposed
mgit auth login [provider]
mgit auth logout [provider]
mgit auth status
mgit auth list
mgit auth switch <provider>
```

## Complete Command Structure

### Top-Level Commands
```
mgit
├── version          # Show version information
├── help            # Show help information
├── init            # Initialize mgit in current directory
├── config          # Configuration management
├── auth            # Authentication management
├── clone           # Clone operations
├── pull            # Pull operations
├── list            # List operations
├── filter          # Filter management
└── provider        # Provider management
```

### Config Subcommands
```
mgit config
├── show            # Display current configuration
├── edit            # Open config in editor
├── list            # List all configuration values
├── get <key>       # Get specific config value
├── set <key> <val> # Set configuration value
├── unset <key>     # Remove configuration value
├── generate        # Generate sample config file
├── validate        # Validate configuration
└── migrate         # Migrate from old format
```

### Auth Subcommands
```
mgit auth
├── login [provider]     # Authenticate with provider
├── logout [provider]    # Remove authentication
├── status              # Show auth status
├── list                # List configured authentications
├── test [provider]     # Test authentication
└── switch <provider>   # Switch default provider
```

### Clone Subcommands
```
mgit clone
├── all <scope> <path>   # Clone all repositories
├── single <repo> <path> # Clone single repository
├── filtered <scope> <path> # Clone with filters
└── resume <path>        # Resume interrupted clone
```

### List Subcommands
```
mgit list
├── repos <scope>        # List repositories
├── projects <org>       # List projects/workspaces
├── providers           # List available providers
├── filters             # List saved filters
└── worktrees           # List active worktrees
```

### Filter Subcommands
```
mgit filter
├── create <name>       # Create named filter
├── edit <name>         # Edit existing filter
├── delete <name>       # Delete filter
├── show <name>         # Show filter details
├── list                # List all filters
└── test <name> <scope> # Test filter results
```

### Provider Subcommands
```
mgit provider
├── list                # List available providers
├── info <provider>     # Show provider details
├── configure <provider> # Configure provider
└── test <provider>     # Test provider connection
```

## Implementation Examples

### Config Commands
```python
@config_app.command()
def show(
    format: str = typer.Option("yaml", "--format", "-f", help="Output format: yaml, json, table"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Specific config path to show")
):
    """Display current configuration"""
    config_loader = ConfigLoader()
    
    if path:
        value = config_loader.get(path)
        console.print(f"{path}: {value}")
    else:
        # Show full config in requested format
        ...

@config_app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key (dot notation)"),
    value: str = typer.Argument(..., help="Configuration value"),
    global_: bool = typer.Option(False, "--global", "-g", help="Set in global config"),
):
    """Set a configuration value"""
    config_loader = ConfigLoader()
    config_loader.set(key, value, persist=True)
    console.print(f"[green]✓[/green] Set {key} = {value}")
```

### Auth Commands
```python
@auth_app.command()
def login(
    provider: Optional[str] = typer.Argument(None, help="Provider to authenticate with"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive login"),
):
    """Authenticate with a git provider"""
    if not provider:
        provider = config.get("settings.default_provider", "azuredevops")
    
    # Provider-specific login flow
    ...

@auth_app.command()
def status(
    all_providers: bool = typer.Option(False, "--all", "-a", help="Show all providers"),
):
    """Show authentication status"""
    if all_providers:
        # Show status for all configured providers
        ...
    else:
        # Show status for default provider
        ...
```

## Usage Examples

### Configuration Management
```bash
# View configuration
mgit config show
mgit config list
mgit config get settings.concurrency

# Modify configuration
mgit config set settings.concurrency 8
mgit config set providers.github.accounts.work.token "ghp_..."
mgit config unset settings.experimental_features

# Edit configuration file
mgit config edit

# Generate sample configuration
mgit config generate
```

### Authentication Workflows
```bash
# Login to default provider
mgit auth login

# Login to specific provider
mgit auth login github

# Check authentication status
mgit auth status
mgit auth test github

# Switch between providers
mgit auth switch bitbucket
```

### Repository Operations
```bash
# Clone repositories
mgit clone all MyProject ./repos
mgit clone filtered MyProject ./repos --filter "*-api"
mgit clone single MyProject/auth-service ./services

# Update repositories
mgit pull all ./repos
mgit pull single ./repos/auth-service
```

### Listing and Discovery
```bash
# List repositories
mgit list repos MyProject
mgit list repos octocat --provider github

# List projects
mgit list projects
mgit list projects --provider bitbucket

# List available filters
mgit filter list
```

## Benefits of Subcommand Structure

1. **Discoverability**: Users can explore functionality naturally
   ```bash
   mgit config <TAB>  # Shows all config subcommands
   ```

2. **Grouping**: Related functionality is clearly organized
   
3. **Extensibility**: Easy to add new subcommands without cluttering

4. **Clarity**: Intent is clearer with subcommands
   ```bash
   mgit config show     # Obviously shows config
   mgit auth login      # Clear authentication action
   ```

5. **Consistency**: Follows patterns from popular tools:
   - `git config list`
   - `docker image ls`
   - `kubectl get pods`

## Implementation Notes

Since this is a single-user application, we'll make a clean break:

1. **No Backward Compatibility**: Old command syntax will simply not work
2. **Clear Error Messages**: If someone tries old syntax, show the new command
3. **Focus on Simplicity**: No dual implementations or migration code
4. **Documentation**: All examples use the new subcommand structure

## Command Aliases

For convenience, support common aliases:

```bash
# Aliases for common operations
mgit ls → mgit list repos
mgit st → mgit auth status
mgit cfg → mgit config
```

## Conclusion

The subcommand structure makes mgit more intuitive and scalable. It provides clear organization, better discoverability, and aligns with modern CLI design patterns. This structure also provides a solid foundation for future expansion as new features are added.