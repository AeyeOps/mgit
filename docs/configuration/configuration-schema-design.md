# Configuration Schema Design for Multi-Provider mgit

> **NOTE**: This document describes proposed configuration formats (INI, YAML) that are NOT currently implemented in mgit. 
> The actual mgit tool uses a simple key=value configuration format (like .env files) in `~/.config/mgit/config`.
> See [mgit-configuration-examples.md](./mgit-configuration-examples.md) for the actual configuration format.

## Overview

This document defines a proposed configuration schema for mgit to support multiple Git providers while maintaining backward compatibility with existing Azure DevOps configurations.

## Configuration Hierarchy

Configuration values are resolved in the following order (highest to lowest priority):

1. Command-line arguments
2. Environment variables
3. Project-local configuration (`.mgit/config`)
4. User configuration (`~/.config/mgit/config`)
5. System configuration (`/etc/mgit/config`)
6. Built-in defaults

## File Formats Supported

### 1. INI Format (Primary - Backward Compatible)
```ini
# ~/.config/mgit/config
[default]
provider = github
concurrency = 4
update_mode = skip
log_level = INFO

[providers.azuredevops]
organization_url = https://dev.azure.com/myorg
pat = ${AZURE_DEVOPS_PAT}  # Environment variable reference
default_project = MyProject

[providers.github]
token = ${GITHUB_TOKEN}
default_organization = octocat
clone_protocol = https  # https or ssh
api_version = v3

[providers.bitbucket]
workspace = myworkspace
username = ${BITBUCKET_USERNAME}
app_password = ${BITBUCKET_APP_PASSWORD}
default_project = PROJ
```

### 2. TOML Format (Future)
```toml
# ~/.config/mgit/config.toml
[default]
provider = "github"
concurrency = 4
update_mode = "skip"

[providers.azuredevops]
organization_url = "https://dev.azure.com/myorg"
pat = "${AZURE_DEVOPS_PAT}"

[providers.github]
token = "${GITHUB_TOKEN}"
default_organization = "octocat"
```

### 3. YAML Format (Future)
```yaml
# ~/.config/mgit/config.yaml
default:
  provider: github
  concurrency: 4
  update_mode: skip

providers:
  azuredevops:
    organization_url: https://dev.azure.com/myorg
    pat: ${AZURE_DEVOPS_PAT}
  github:
    token: ${GITHUB_TOKEN}
    default_organization: octocat
```

## Detailed Schema Definition

### Global Settings

```ini
[default]
# Default provider when not specified
provider = azuredevops|github|bitbucket

# Number of concurrent operations
concurrency = 1-100 (default: 4)

# How to handle existing directories
update_mode = skip|pull|force (default: skip)

# Logging configuration
log_level = DEBUG|INFO|WARNING|ERROR (default: INFO)
log_file = path/to/logfile (default: ~/.config/mgit/mgit.log)
console_level = DEBUG|INFO|WARNING|ERROR (default: INFO)

# Output preferences
output_format = pretty|json|quiet (default: pretty)
color = auto|always|never (default: auto)

# Network settings
http_proxy = http://proxy:port
https_proxy = https://proxy:port
no_proxy = localhost,127.0.0.1
timeout = 30 (seconds)
retry_count = 3
retry_delay = 1 (seconds)
```

### Provider-Specific Settings

#### Azure DevOps
```ini
[providers.azuredevops]
# Required
organization_url = https://dev.azure.com/myorg
pat = <personal-access-token>

# Optional
default_project = MyProject
api_version = 7.0
connection_timeout = 30
max_retries = 3

# Clone preferences
clone_depth = 0 (0 = full clone)
include_lfs = true
```

#### GitHub
```ini
[providers.github]
# Required (one of)
token = <personal-access-token>
oauth_token = <oauth-token>
app_id = <github-app-id>
app_private_key_path = /path/to/key.pem

# Optional
default_organization = octocat
api_url = https://api.github.com (for GitHub Enterprise)
clone_protocol = https|ssh (default: https)
per_page = 100 (pagination size)

# Feature flags
include_forks = false
include_archived = false
include_private = true
include_templates = false

# Repository filters
topics = ["python", "api"]
languages = ["Python", "JavaScript"]
visibility = all|public|private
```

#### BitBucket
```ini
[providers.bitbucket]
# Required
username = myusername
app_password = <app-password>

# Optional  
workspace = myworkspace
default_project = PROJ
api_url = https://api.bitbucket.org/2.0
api_version = 2.0

# Clone preferences
clone_protocol = https|ssh
include_wiki = false
include_downloads = false
```

### Profiles (Advanced Feature)

Support multiple configurations for the same provider:

```ini
[profiles.work]
provider = azuredevops
organization_url = https://dev.azure.com/company

[profiles.personal]  
provider = github
default_organization = myusername

[profiles.oss]
provider = github
default_organization = opensource-org

# Usage: mgit --profile work clone-all MyProject ./repos
```

## Environment Variable Mapping

### Legacy Variables (Maintained for Backward Compatibility)
```bash
AZURE_DEVOPS_ORG_URL -> providers.azuredevops.organization_url
AZURE_DEVOPS_EXT_PAT -> providers.azuredevops.pat
LOG_FILENAME -> default.log_file
LOG_LEVEL -> default.log_level
CON_LEVEL -> default.console_level
DEFAULT_CONCURRENCY -> default.concurrency
DEFAULT_UPDATE_MODE -> default.update_mode
```

### New Standardized Variables
```bash
# Global
MGIT_PROVIDER -> default.provider
MGIT_CONCURRENCY -> default.concurrency
MGIT_UPDATE_MODE -> default.update_mode
MGIT_CONFIG_PATH -> custom config file path

# Provider-specific
MGIT_AZUREDEVOPS_ORG_URL -> providers.azuredevops.organization_url
MGIT_AZUREDEVOPS_PAT -> providers.azuredevops.pat
MGIT_GITHUB_TOKEN -> providers.github.token
MGIT_GITHUB_ORG -> providers.github.default_organization
MGIT_BITBUCKET_USERNAME -> providers.bitbucket.username
MGIT_BITBUCKET_APP_PASSWORD -> providers.bitbucket.app_password
```

## Secure Credential Storage

### Option 1: OS Keychain Integration
```ini
[providers.github]
token = @keychain:mgit-github-token
# Retrieves from OS keychain/credential manager
```

### Option 2: Encrypted File Reference
```ini
[providers.github]
token = @file:~/.config/mgit/secrets/github.enc
# Decrypts file using master password
```

### Option 3: External Command
```ini
[providers.github]
token = @cmd:pass show mgit/github/token
# Executes command to retrieve token
```

## Configuration Validation

### Schema Validation Rules
```python
# Pseudocode for validation
schema = {
    "default": {
        "provider": ["azuredevops", "github", "bitbucket"],
        "concurrency": range(1, 101),
        "update_mode": ["skip", "pull", "force"],
        "log_level": ["DEBUG", "INFO", "WARNING", "ERROR"]
    },
    "providers.azuredevops": {
        "organization_url": "url",
        "pat": "string:required"
    },
    "providers.github": {
        "token": "string:required_without:oauth_token,app_id",
        "clone_protocol": ["https", "ssh"]
    }
}
```

### Validation Command
```bash
mgit config validate
mgit config validate --file custom-config.ini
```

## Migration Tools

### Automatic Migration
```bash
mgit config migrate
# Converts old format to new format, backs up original
```

### Migration Script Logic
1. Detect old configuration format
2. Create backup (`.config.backup`)
3. Convert to new schema
4. Validate migrated configuration
5. Report any manual actions needed

## Configuration Commands

### View Configuration
```bash
# Show effective configuration (all sources merged)
mgit config show
mgit config show --provider github
mgit config show --source  # Shows which file each value comes from

# Show raw configuration file
mgit config cat
mgit config cat --global
mgit config cat --system
```

### Edit Configuration
```bash
# Interactive editor
mgit config edit
mgit config edit --global

# Set specific values
mgit config set default.provider github
mgit config set providers.github.token <token>
mgit config set --global default.concurrency 8

# Unset values
mgit config unset providers.github.include_forks
```

### Configuration Debugging
```bash
# Show configuration resolution
mgit config debug
# Shows: env vars -> global config -> local config -> defaults

# Test configuration
mgit config test
# Validates configuration and tests provider connections
```

## Best Practices

1. **Don't store credentials in version control**
   - Use environment variables or secure storage
   - Add `.mgit/config` to `.gitignore`

2. **Use profiles for different contexts**
   - Work vs personal projects
   - Different organizations

3. **Set reasonable defaults globally**
   - Common concurrency limits
   - Preferred providers

4. **Project-specific overrides**
   - Higher concurrency for large projects
   - Different update modes

## Example Configurations

### Minimal Configuration
```ini
[default]
provider = github

[providers.github]
token = ${GITHUB_TOKEN}
```

### Multi-Provider Power User
```ini
[default]
provider = github
concurrency = 10
update_mode = pull
log_level = INFO

[providers.azuredevops]
organization_url = https://dev.azure.com/company
pat = @keychain:ado-work-pat
default_project = MainProject

[providers.github]
token = @keychain:github-token
default_organization = mycompany
clone_protocol = ssh
include_forks = false

[providers.bitbucket]
workspace = company-workspace
username = john.doe
app_password = @cmd:pass show bitbucket/app-password

[profiles.oss]
provider = github
default_organization = opensource-contrib
include_forks = true
```

### Enterprise Configuration
```ini
[default]
provider = github
http_proxy = http://proxy.company.com:8080
no_proxy = localhost,*.company.com

[providers.github]
api_url = https://github.company.com/api/v3
token = @cmd:corporate-vault get github-token
include_private = true
```