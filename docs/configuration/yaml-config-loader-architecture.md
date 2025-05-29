# YAML Configuration Loader Architecture

> **NOTE**: This document describes a proposed YAML configuration architecture that is NOT currently implemented in mgit. 
> The actual mgit tool uses a simple key=value configuration format (like .env files) in `~/.config/mgit/config`.
> See [mgit-configuration-examples.md](./mgit-configuration-examples.md) for the actual configuration format.

## Executive Summary

This document presents the architectural design for potentially migrating mgit from environment variable/dotenv-based configuration to a YAML-based configuration system with local override support, while maintaining all existing functionality and visual features.

## Current State Analysis

### Issues to Address
1. **Leftover ado-cli references** throughout mgit.py:
   - Help text mentions `~/.config/mgit/config`
   - Log filename defaults to `mgit.log`
   - Command descriptions reference `mgit`

2. **Configuration System**:
   - Currently uses dotenv format (key=value pairs)
   - Relies heavily on environment variables
   - Single configuration file: `~/.config/mgit/config`

3. **Strengths to Preserve**:
   - Robust async repository management
   - Beautiful Rich console output with progress bars
   - PAT masking in logs
   - Concurrent operations with semaphore control
   - Clean error handling and user feedback

## Proposed Architecture

### Configuration Loading Hierarchy

```
Priority (first found wins):
1. ./config.local.yaml              (current working directory)
2. ~/.config/mgit/config.local.yaml (user-specific local overrides)
3. ~/.config/mgit/config.yaml       (main configuration)

No defaults - configuration file is required.
```

### YAML Configuration Structure

```yaml
# config.yaml - Main configuration file
settings:
  # Logging configuration
  logging:
    file: ~/.config/mgit/mgit.log  # Changed from ado-cli.log
    level: DEBUG
    console_level: INFO
    rotate: true
    max_size: 5MB
    
  # Operation defaults
  concurrency: 4
  update_mode: skip  # skip, pull, force
  
  # Provider defaults
  default_provider: azuredevops

# Provider configurations
providers:
  azuredevops:
    organizations:
      default: myorg  # Default organization key
      myorg:
        url: https://dev.azure.com/myorg
        pat: "your-pat-token-here"  # Direct value only
        default_project: MyProject
```

### Configuration Loader Class Design

```python
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import os
import logging

class ConfigLoader:
    """YAML-based configuration loader with hierarchical override support"""
    
    # Configuration file search paths in priority order
    CONFIG_SEARCH_PATHS = [
        Path.cwd() / "config.local.yaml",
        Path.home() / ".config" / "mgit" / "config.local.yaml",
        Path.home() / ".config" / "mgit" / "config.yaml",
    ]
    
    # No defaults - configuration must be explicit
    
    def __init__(self):
        self._config = self._load_configuration()
        self._resolved_cache = {}
        
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from YAML files - fail if not found or invalid"""
        # Try to find a config file
        config_loaded = False
        for config_path in self.CONFIG_SEARCH_PATHS:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if not config:
                        raise ValueError(f"Empty configuration file: {config_path}")
                    logging.info(f"Loaded configuration from {config_path}")
                    config_loaded = True
                    break
        
        if not config_loaded:
            raise FileNotFoundError(
                f"No configuration file found. Expected one of: {', '.join(str(p) for p in self.CONFIG_SEARCH_PATHS)}"
            )
                    
        return config
    
    def _deep_merge(self, base: Dict, overlay: Dict) -> Dict:
        """Deep merge overlay configuration onto base"""
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def get(self, key_path: str) -> Any:
        """
        Get configuration value using dot notation - fail if not found
        
        Examples:
            config.get("settings.concurrency")
            config.get("providers.azuredevops.organizations.default.url")
        """
        # Check cache first
        if key_path in self._resolved_cache:
            return self._resolved_cache[key_path]
            
        # Navigate through config
        keys = key_path.split('.')
        value = self._config
        
        for i, key in enumerate(keys):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                path_so_far = '.'.join(keys[:i+1])
                raise KeyError(f"Configuration key not found: {path_so_far}")
            
        # Cache resolved value
        self._resolved_cache[key_path] = value
        return value
    
    def get_provider_config(self, provider: str, org_key: str = "default") -> Dict[str, Any]:
        """Get provider-specific configuration - fail if not found"""
        base_path = f"providers.{provider}.organizations.{org_key}"
        
        # All fields are required
        return {
            "url": self.get(f"{base_path}.url"),
            "pat": self.get(f"{base_path}.pat"),
            "default_project": self.get(f"{base_path}.default_project")
        }
    
    def set(self, key_path: str, value: Any, persist: bool = True) -> None:
        """Set configuration value and optionally persist to file"""
        keys = key_path.split('.')
        target = self._config
        
        # Navigate to parent
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
            
        # Set value
        target[keys[-1]] = value
        
        # Clear cache
        self._resolved_cache.pop(key_path, None)
        
        # Persist if requested
        if persist:
            self._save_configuration()
    
    def _save_configuration(self) -> None:
        """Save configuration to user config file"""
        config_file = Path.home() / ".config" / "mgit" / "config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
            
        # Set secure permissions
        os.chmod(config_file, 0o600)

# No custom YAML tags needed - keep it simple
```

### Integration Points

#### 1. Direct Configuration Access

```python
# Simple, direct approach
config = ConfigLoader()

# Direct access with dot notation
def get_config_value(key: str) -> str:
    """Get configuration value - no defaults, fail if not found"""
    # Map simple keys to new structure
    key_map = {
        "AZURE_DEVOPS_ORG_URL": "providers.azuredevops.organizations.default.url",
        "AZURE_DEVOPS_EXT_PAT": "providers.azuredevops.organizations.default.pat",
        "LOG_FILENAME": "settings.logging.file",
        "LOG_LEVEL": "settings.logging.level",
        "CON_LEVEL": "settings.logging.console_level",
        "DEFAULT_CONCURRENCY": "settings.concurrency",
        "DEFAULT_UPDATE_MODE": "settings.update_mode"
    }
    
    yaml_key = key_map.get(key, key)
    return str(config.get(yaml_key))
```

#### 2. Update Commands

##### generate_config Command (Replaces generate_env)

```python
@app.command(help="Generate a sample configuration file with all options.")
def generate_config():
    """Generate sample config.yaml with documentation"""
    
    sample_config = """# mgit configuration file
# Place this file at ~/.config/mgit/config.yaml

settings:
  # Logging configuration
  logging:
    file: ~/.config/mgit/mgit.log
    level: DEBUG          # File log level: DEBUG, INFO, WARNING, ERROR
    console_level: INFO   # Console output level
    rotate: true          # Enable log rotation
    max_size: 5MB        # Max size before rotation
    
  # Operation defaults
  concurrency: 4         # Number of concurrent git operations
  update_mode: skip      # How to handle existing repos: skip, pull, force
  
  # Default provider when not specified
  default_provider: azuredevops

# Provider configurations
providers:
  azuredevops:
    organizations:
      # Default organization (used when --org not specified)
      default: myorg
      
      # Organization configurations
      myorg:
        url: https://dev.azure.com/myorg
        pat: "xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        default_project: MyProject
        
      # Add more organizations as needed
      anotherorg:
        url: https://dev.azure.com/anotherorg
        pat: "another-pat-token-here"
        
  # Future providers (not yet implemented)
  github:
    accounts:
      default: personal
      personal:
        token: "ghp_xxxxxxxxxxxxxxxxxxxx"
        
  bitbucket:
    workspaces:
      default: myworkspace
      myworkspace:
        username: "your-username"
        app_password: "your-app-password"
"""
    
    # Determine output location
    if Path("config.yaml").exists():
        filename = "config.sample.yaml"
    else:
        filename = "config.yaml"
        
    Path(filename).write_text(sample_config)
    console.print(f"[green]✓[/green] Created {filename}")
    console.print("\nRequired: Edit the configuration with your actual values before using mgit")
```

##### Update config Command

```python
# Create config subcommand app
config_app = typer.Typer(help="Configuration management commands")
app.add_typer(config_app, name="config")

@config_app.command()
def show(
    format: str = typer.Option("yaml", "--format", "-f", help="Output format: yaml, json, table"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Specific config path to show")
):
    """Display current configuration"""
    config_loader = ConfigLoader()
    
    if path:
        # Display current configuration
        console.print("[bold]Current configuration:[/bold]\n")
        
        # Show loaded config files
        console.print("[dim]Configuration sources:[/dim]")
        for path in ConfigLoader.CONFIG_SEARCH_PATHS:
            if path.exists():
                console.print(f"  ✓ {path}")
            else:
                console.print(f"  ✗ {path} [dim](not found)[/dim]")
        
        console.print("\n[dim]Effective configuration:[/dim]")
        
        # Display settings
        console.print("\n[bold]Settings:[/bold]")
        console.print(f"  Provider: {config_loader.get('settings.default_provider')}")
        console.print(f"  Concurrency: {config_loader.get('settings.concurrency')}")
        console.print(f"  Update mode: {config_loader.get('settings.update_mode')}")
        console.print(f"  Log file: {config_loader.get('settings.logging.file')}")
        console.print(f"  Log level: {config_loader.get('settings.logging.level')}")
        
        # Display provider configs
        console.print("\n[bold]Providers:[/bold]")
        providers = config_loader.get('providers', {})
        for provider, provider_config in providers.items():
            console.print(f"\n  {provider}:")
            if 'organizations' in provider_config:
                for org_key, org_config in provider_config['organizations'].items():
                    console.print(f"    {org_key}:")
                    console.print(f"      URL: {org_config.get('url', 'Not set')}")
                    # Mask PAT
                    pat = org_config.get('pat', '')
                    if pat:
                        if pat.startswith('!env'):
                            console.print(f"      PAT: {pat}")
                        else:
                            masked = pat[:4] + '*' * (len(pat) - 8) + pat[-4:] if len(pat) > 8 else '*' * len(pat)
                            console.print(f"      PAT: {masked}")
        return
    
    # Update configuration
    if organization:
        if not organization.startswith(("http://", "https://")):
            organization = f"https://{organization}"
        config_loader.set("providers.azuredevops.organizations.default.url", organization)
        
    if concurrency is not None:
        config_loader.set("settings.concurrency", concurrency)
        
    if update_mode is not None:
        config_loader.set("settings.update_mode", update_mode.value)
        
    console.print("[green]✓[/green] Configuration updated successfully")
```

#### 3. Fix ado-cli References

Replace all occurrences:
- `~/.config/ado-cli/config` → `~/.config/mgit/config.yaml`
- `ado-cli.log` → `mgit.log`
- `ado-cli` in help text → `mgit`

### Clean Implementation Approach

Since this is a single-user application, we keep it simple:

1. **No Migration Code**: Start fresh with YAML configuration
2. **No Environment Variables**: Direct values in YAML only
3. **Simple Commands**: Direct subcommand implementation
4. **No Legacy Support**: Clean codebase without compatibility layers

### Testing Requirements

1. **Configuration Loading**:
   - Test hierarchy (local overrides global)
   - Test YAML parsing and validation
   - Test environment variable resolution

2. **Command Updates**:
   - Test `mgit config show` with new format
   - Test `mgit config set/get` commands
   - Test `mgit config generate` output

3. **Error Handling**:
   - Test with missing config files
   - Test with malformed YAML
   - Test clear error messages

4. **Integration**:
   - Ensure logging still works
   - Ensure PAT masking still works
   - Ensure all commands use new config system

## Implementation Plan

### Phase 1: Core Infrastructure
1. Fix all ado-cli references to mgit
2. Implement ConfigLoader class
3. Add PyYAML to requirements.txt

### Phase 2: Command Structure
1. Implement subcommand structure with Typer
2. Create `mgit config` subcommands
3. Create `mgit auth` subcommands
4. Update `clone` and `pull` to subcommands

### Phase 3: Integration
1. Replace get_config_value() with ConfigLoader
2. Update AzDevOpsManager initialization
3. Remove all dotenv dependencies
4. Test all commands with YAML config

## Summary

This architecture provides:
- Clean YAML-based configuration with local overrides
- Simple, direct implementation without legacy baggage
- Preservation of core features (progress bars, PAT masking, etc.)
- Foundation for multi-provider support
- Clear subcommand structure for better UX

The implementation focuses on simplicity and functionality, avoiding over-engineering while maintaining the robust repository management and visual feedback that makes mgit effective.