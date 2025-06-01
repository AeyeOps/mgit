# ruamel.yaml Best Practices & Reference Implementation

## Overview

ruamel.yaml is a YAML 1.2 parser/emitter for Python that excels at preserving formatting, comments, and document structure during round-trip processing. This guide covers best practices for configuration file management with comment preservation.

## Installation & Configuration

### pyproject.toml Setup

```toml
[project]
dependencies = [
    "ruamel.yaml >=0.18.5, <1.0"
]

# Optional: For performance-critical applications
[project.optional-dependencies]
performance = [
    "PyYAML >=6.0.1, <7.0"  # Fallback for simple parsing
]
```

**Important**: Package name requires quotes in TOML due to the dot:
```toml
"ruamel.yaml" = "^0.18.0"
```

### Basic Initialization

```python
from ruamel.yaml import YAML

# Recommended configuration for config files
yaml = YAML()
yaml.preserve_quotes = True
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 80  # Line wrapping for VCS-friendly diffs
yaml.allow_unicode = True
```

## Comment Preservation Patterns

### Loading with Comment Preservation

```python
from ruamel.yaml import YAML
from pathlib import Path

def load_config_with_comments(config_path: Path):
    """Load YAML config preserving all comments and formatting."""
    yaml = YAML()
    
    if not config_path.exists():
        return {"global": {}, "providers": {}}
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = yaml.load(f) or {}
            
        # Convert ruamel objects to regular dicts for compatibility
        if hasattr(config, 'items'):
            config = dict(config)
            for section in ['global', 'providers']:
                if section in config and hasattr(config[section], 'items'):
                    config[section] = dict(config[section])
                    
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {"global": {}, "providers": {}}
```

### Saving with Comment Preservation

```python
def save_config_with_comments(config_path: Path, new_config: dict):
    """Save config while preserving existing comments and structure."""
    yaml = YAML()
    
    if config_path.exists():
        # Preserve existing structure and comments
        try:
            with config_path.open("r", encoding="utf-8") as f:
                existing = yaml.load(f)
            
            if existing is None:
                existing = yaml.map()
            
            # Update sections while preserving comments
            for section, data in new_config.items():
                if section not in existing:
                    existing[section] = yaml.map()
                
                existing[section].clear()
                for key, value in data.items():
                    existing[section][key] = value
            
            # Write with preserved comments
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(existing, f)
                
        except Exception as preserve_error:
            logger.warning(f"Comment preservation failed: {preserve_error}")
            # Fallback to clean write
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(new_config, f)
    else:
        # New file - add helpful structure comments
        config_with_comments = yaml.map()
        
        # Add sections with explanatory comments
        for section, data in new_config.items():
            config_with_comments[section] = yaml.map(data)
            
        # Add section comments for new files
        if "global" in config_with_comments:
            config_with_comments.yaml_set_comment_before_after_key(
                "global",
                before="# Global application settings\n"
            )
            
        if "providers" in config_with_comments:
            config_with_comments.yaml_set_comment_before_after_key(
                "providers", 
                before="# Provider configurations\n# Each provider can have multiple named configurations\n"
            )
        
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_with_comments, f)
```

## Advanced Comment Manipulation

### Adding Comments Programmatically

```python
def add_helpful_comments(data, yaml_instance):
    """Add contextual comments to configuration data."""
    
    # Add comments before keys
    data.yaml_set_comment_before_after_key(
        'database',
        before='# Database connection settings\n# Modify with caution in production\n'
    )
    
    # Add end-of-line comments
    data.yaml_add_eol_comment('Required field', 'api_key')
    data.yaml_add_eol_comment('Optional: defaults to 30s', 'timeout')
    
    # Add comments before specific values in lists
    if 'servers' in data and isinstance(data['servers'], list):
        for i, server in enumerate(data['servers']):
            if server.get('env') == 'production':
                data['servers'].yaml_add_eol_comment('Production server', i)
```

### Preserving Complex Structures

```python
def merge_configs_preserve_comments(base_config, override_config, yaml_instance):
    """Merge configurations while preserving base config comments."""
    
    # Load base with comments preserved
    base = yaml_instance.load(base_config)
    override = yaml_instance.load(override_config)
    
    for section_key, section_data in override.items():
        if section_key in base:
            if isinstance(section_data, dict):
                # Merge dictionaries, preserving base comments
                for key, value in section_data.items():
                    base[section_key][key] = value
                    # Add merge tracking comment
                    base[section_key].yaml_add_eol_comment(
                        f'Updated from {override_config}', key
                    )
            else:
                # Replace entire section
                base[section_key] = section_data
                base.yaml_add_eol_comment(
                    f'Replaced from {override_config}', section_key
                )
        else:
            # New section from override
            base[section_key] = section_data
            base.yaml_set_comment_before_after_key(
                section_key,
                before=f'# Added from {override_config}\n'
            )
    
    return base
```

## Configuration Management Best Practices

### 1. Structured Comment Strategy

```yaml
# Application Configuration
# Last updated: 2024-01-15
# Environment: production

global:
  # Logging configuration
  log_level: INFO        # Options: DEBUG, INFO, WARN, ERROR
  log_file: app.log      # Relative to application directory
  
  # Performance tuning
  worker_count: 4        # Adjust based on CPU cores
  timeout: 30           # Request timeout in seconds

providers:
  # Primary database connection
  primary_db:
    host: localhost      # Database server hostname
    port: 5432          # Standard PostgreSQL port
    database: myapp     # Database name
    # Credentials stored in environment variables
    
  # Backup database (read-only)
  backup_db:
    host: backup.example.com
    port: 5432
    database: myapp_backup
```

### 2. Version Control Considerations

```python
def prepare_config_for_vcs(config_path: Path):
    """Optimize config file for version control."""
    yaml = YAML()
    yaml.width = 80  # Consistent line wrapping
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    yaml.explicit_start = True  # Add --- document start
    
    with config_path.open("r") as f:
        data = yaml.load(f)
    
    # Ensure consistent ordering for stable diffs
    if isinstance(data, dict):
        # Sort sections for predictable output
        ordered_sections = ['global', 'providers', 'overrides']
        ordered_data = yaml.map()
        
        for section in ordered_sections:
            if section in data:
                ordered_data[section] = data[section]
        
        # Add any remaining sections
        for key, value in data.items():
            if key not in ordered_sections:
                ordered_data[key] = value
        
        data = ordered_data
    
    with config_path.open("w") as f:
        yaml.dump(data, f)
```

### 3. Validation with Comment Preservation

```python
from ruamel.yaml.comments import CommentedMap, CommentedSeq

def validate_config_structure(data):
    """Validate config while preserving comment metadata."""
    
    if not isinstance(data, CommentedMap):
        raise ValueError("Root must be a mapping with comment support")
    
    required_sections = ['global', 'providers']
    for section in required_sections:
        if section not in data:
            # Add missing section with explanatory comment
            data[section] = CommentedMap()
            data.yaml_set_comment_before_after_key(
                section,
                before=f'# {section.title()} configuration section\n'
            )
    
    # Validate provider configurations
    if 'providers' in data:
        for provider_name, provider_config in data['providers'].items():
            if not isinstance(provider_config, CommentedMap):
                raise ValueError(f"Provider '{provider_name}' must be a mapping")
            
            # Add validation comments for required fields
            required_fields = get_required_fields_for_provider(provider_name)
            for field in required_fields:
                if field not in provider_config:
                    provider_config.yaml_add_eol_comment(
                        'REQUIRED FIELD MISSING', field
                    )
```

## Security Considerations

### Safe Loading

```python
def load_config_safely(config_path: Path):
    """Load configuration with security considerations."""
    yaml = YAML(typ='safe')  # Use safe loader
    yaml.preserve_quotes = True
    
    try:
        with config_path.open("r", encoding="utf-8") as f:
            return yaml.load(f)
    except Exception as e:
        logger.error(f"Failed to safely load config: {e}")
        return None
```

### Sensitive Data Handling

```python
def mask_sensitive_values(data, sensitive_keys=None):
    """Mask sensitive values while preserving structure and comments."""
    if sensitive_keys is None:
        sensitive_keys = ['password', 'token', 'secret', 'key', 'pat']
    
    def mask_recursive(obj, path=""):
        if isinstance(obj, CommentedMap):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    # Mask value but preserve comments
                    if isinstance(value, str) and len(value) > 8:
                        obj[key] = f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
                    else:
                        obj[key] = "*" * len(str(value))
                    
                    # Add masking comment
                    obj.yaml_add_eol_comment('(masked)', key)
                else:
                    mask_recursive(value, current_path)
        
        elif isinstance(obj, CommentedSeq):
            for i, item in enumerate(obj):
                mask_recursive(item, f"{path}[{i}]")
    
    mask_recursive(data)
    return data
```

## Performance Optimization

### Caching Strategy

```python
from functools import lru_cache
import hashlib

class CommentPreservingConfigManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._yaml = YAML()
        self._yaml.preserve_quotes = True
        self._config_cache = None
        self._file_hash = None
    
    def _get_file_hash(self) -> str:
        """Get hash of config file for cache invalidation."""
        if not self.config_path.exists():
            return ""
        
        with self.config_path.open("rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def load_config(self, force_reload=False):
        """Load config with intelligent caching."""
        current_hash = self._get_file_hash()
        
        if (not force_reload and 
            self._config_cache is not None and 
            self._file_hash == current_hash):
            return self._config_cache
        
        with self.config_path.open("r", encoding="utf-8") as f:
            self._config_cache = self._yaml.load(f)
        
        self._file_hash = current_hash
        return self._config_cache
```

## Migration from PyYAML

### Drop-in Replacement Pattern

```python
# Before (PyYAML)
import yaml

with open('config.yaml') as f:
    data = yaml.safe_load(f)

data['new_setting'] = 'value'

with open('config.yaml', 'w') as f:
    yaml.dump(data, f, sort_keys=False)

# After (ruamel.yaml with comment preservation)
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True

with open('config.yaml') as f:
    data = yaml.load(f)

data['new_setting'] = 'value'  # Comments preserved!

with open('config.yaml', 'w') as f:
    yaml.dump(data, f)
```

### Gradual Migration Strategy

```python
def hybrid_yaml_handler(file_path: Path, preserve_comments=True):
    """Handle YAML with fallback for compatibility."""
    
    if preserve_comments:
        try:
            from ruamel.yaml import YAML
            yaml = YAML()
            yaml.preserve_quotes = True
            return yaml
        except ImportError:
            logger.warning("ruamel.yaml not available, falling back to PyYAML")
    
    # Fallback to PyYAML
    import yaml
    return yaml
```

## Common Pitfalls and Solutions

### 1. Performance Issues
**Problem**: ruamel.yaml is ~20% slower than PyYAML
**Solution**: Use caching and lazy loading for large configs

### 2. Type Conversion
**Problem**: ruamel.yaml objects aren't standard dicts
**Solution**: Convert to standard types when needed:

```python
def convert_to_standard_types(obj):
    """Convert ruamel.yaml objects to standard Python types."""
    if hasattr(obj, 'items'):  # CommentedMap
        return {k: convert_to_standard_types(v) for k, v in obj.items()}
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):  # CommentedSeq
        return [convert_to_standard_types(item) for item in obj]
    else:
        return obj
```

### 3. Comment Corruption
**Problem**: Comments lost during complex operations
**Solution**: Always work with the ruamel.yaml object types, avoid converting to standard types until necessary

## Conclusion

ruamel.yaml provides superior comment preservation and YAML 1.2 compliance compared to PyYAML, making it ideal for configuration management where human readability and documentation are important. The performance overhead is generally acceptable for configuration files, and the benefits of preserved formatting and comments significantly improve maintainability.

**Key Takeaways**:
- Use ruamel.yaml for configuration files that need human editing
- Implement proper caching for performance-critical applications  
- Always validate configuration structure after modifications
- Plan migration carefully, considering both functionality and performance requirements