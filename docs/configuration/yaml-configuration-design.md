# YAML Configuration Design for mgit

## Overview

This document defines the YAML-based configuration schema for mgit, focusing on a clean, intuitive structure that replaces environment variables with configuration values while maintaining flexibility.

## Configuration File Location

Primary configuration file: `~/.config/mgit/config.yaml`

## YAML Schema Structure

### Complete Example Configuration

```yaml
# ~/.config/mgit/config.yaml
# mgit configuration file

# Global settings
settings:
  default_provider: azuredevops  # azuredevops, github, bitbucket
  concurrency: 4
  update_mode: skip  # skip, pull, force
  
  # Logging configuration
  logging:
    level: INFO  # DEBUG, INFO, WARNING, ERROR
    file: ~/.config/mgit/mgit.log
    console_level: INFO
    format: "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
    rotate: true
    max_size: 10MB
    keep_backups: 5
  
  # Output preferences  
  output:
    format: pretty  # pretty, json, quiet
    color: auto  # auto, always, never
    progress: true
    
  # Network configuration
  network:
    timeout: 30
    retry_count: 3
    retry_delay: 1
    verify_ssl: true
    proxy:
      http: null
      https: null
      no_proxy: ["localhost", "127.0.0.1"]

# Provider configurations
providers:
  azuredevops:
    # Organization settings
    organizations:
      default: myorg  # Default organization
      myorg:
        url: https://dev.azure.com/myorg
        pat: !env AZURE_DEVOPS_PAT  # Reference environment variable
        # OR use secure storage
        # pat: !vault azure-devops/myorg/pat
        # OR embed directly (not recommended)
        # pat: "xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        
        # Optional settings
        default_project: MyProject
        api_version: "7.0"
        
      anotherorg:
        url: https://dev.azure.com/anotherorg
        pat: !env AZURE_DEVOPS_PAT_2
        
    # Provider-specific settings
    clone_options:
      depth: 0  # 0 for full clone
      include_lfs: true
      
  github:
    # Organization/user settings
    accounts:
      default: personal  # Default account profile
      personal:
        username: myusername
        token: !env GITHUB_TOKEN
        # GitHub-specific options
        clone_protocol: https  # https or ssh
        api_url: https://api.github.com
        
      work:
        organization: mycompany
        token: !env GITHUB_WORK_TOKEN
        clone_protocol: ssh
        
      enterprise:
        organization: bigcorp
        token: !env GITHUB_ENTERPRISE_TOKEN
        api_url: https://github.bigcorp.com/api/v3
        
    # Global GitHub settings
    options:
      per_page: 100
      include_forks: false
      include_archived: false
      include_templates: false
      
    # Repository filters
    filters:
      languages: ["Python", "Go", "JavaScript"]
      topics: []
      visibility: all  # all, public, private
      
  bitbucket:
    workspaces:
      default: myworkspace
      myworkspace:
        username: !env BITBUCKET_USERNAME
        app_password: !env BITBUCKET_APP_PASSWORD
        # OR use secure reference
        # app_password: !vault bitbucket/myworkspace/app-password
        
        # Optional settings
        default_project: PROJ
        api_url: https://api.bitbucket.org/2.0
        
      clientwork:
        username: contractor@email.com
        app_password: !env BITBUCKET_CLIENT_PASSWORD
        
    # BitBucket-specific options
    clone_options:
      protocol: https  # https or ssh
      include_wiki: false
      include_downloads: false

# Profiles for different contexts
profiles:
  # Profile inherits and overrides global settings
  work:
    settings:
      default_provider: azuredevops
      concurrency: 10
      update_mode: pull
    providers:
      azuredevops:
        organizations:
          default: myorg
          
  personal:
    settings:
      default_provider: github
      concurrency: 4
    providers:
      github:
        accounts:
          default: personal
          
  client:
    settings:
      default_provider: bitbucket
      concurrency: 6
    providers:
      bitbucket:
        workspaces:
          default: clientwork

# Aliases for quick commands
aliases:
  # Define command shortcuts
  clone-work: "clone-all --profile work"
  clone-oss: "clone-all --provider github --account personal"
  update-all: "pull-all --concurrency 20"
```

### Minimal Configuration

```yaml
# Minimal working configuration
settings:
  default_provider: github

providers:
  github:
    accounts:
      default: main
      main:
        token: !env GITHUB_TOKEN
```

## YAML Features and Tags

### Environment Variable References
```yaml
# Use !env tag to reference environment variables
token: !env GITHUB_TOKEN
pat: !env AZURE_DEVOPS_PAT
```

### Secure Storage References
```yaml
# Use !vault tag for external secret managers
token: !vault github/personal/token
app_password: !vault bitbucket/work/app-password

# Use !keychain for OS keychain
token: !keychain mgit-github-token

# Use !cmd to execute command
token: !cmd "pass show mgit/github/token"
```

### Include External Files
```yaml
# Include sensitive data from separate files
providers:
  github: !include ~/.config/mgit/providers/github.yaml
  
# Include shared team configuration
settings: !include https://company.com/mgit/base-config.yaml
```

## Migration from Environment Variables

### Current Environment Variables → YAML Mapping

```yaml
# Current env var → YAML path
# AZURE_DEVOPS_ORG_URL → providers.azuredevops.organizations.{name}.url
# AZURE_DEVOPS_EXT_PAT → providers.azuredevops.organizations.{name}.pat
# LOG_FILENAME → settings.logging.file
# LOG_LEVEL → settings.logging.level
# CON_LEVEL → settings.logging.console_level
# DEFAULT_CONCURRENCY → settings.concurrency
# DEFAULT_UPDATE_MODE → settings.update_mode

# Example migration:
# Before (env vars):
# AZURE_DEVOPS_ORG_URL=https://dev.azure.com/myorg
# AZURE_DEVOPS_EXT_PAT=xxxxxxxxxxxx
# DEFAULT_CONCURRENCY=4

# After (YAML):
settings:
  concurrency: 4
  
providers:
  azuredevops:
    organizations:
      default: myorg
      myorg:
        url: https://dev.azure.com/myorg
        pat: !env AZURE_DEVOPS_PAT  # Can still reference env var
```

## Configuration Precedence

1. Command-line arguments (highest priority)
2. Environment variables (for backward compatibility)
3. Profile-specific configuration
4. Provider-specific configuration
5. Global settings in config.yaml
6. Built-in defaults (lowest priority)

## Validation Schema

```yaml
# JSON Schema for validation (in YAML format)
type: object
properties:
  settings:
    type: object
    properties:
      default_provider:
        type: string
        enum: [azuredevops, github, bitbucket]
      concurrency:
        type: integer
        minimum: 1
        maximum: 100
      update_mode:
        type: string
        enum: [skip, pull, force]
    required: [default_provider]
    
  providers:
    type: object
    properties:
      azuredevops:
        type: object
        properties:
          organizations:
            type: object
            patternProperties:
              "^[a-zA-Z0-9_-]+$":
                type: object
                properties:
                  url:
                    type: string
                    format: uri
                  pat:
                    type: string
                required: [url, pat]
```

## Profile System

Profiles allow switching between different configurations easily:

```yaml
# Use a profile
mgit --profile work clone-all MyProject ./repos
mgit -p personal pull-all ./github-repos

# Set default profile
mgit config set-default-profile work
```

## Security Considerations

### Credential Storage Options

1. **Environment Variables** (traditional)
   ```yaml
   pat: !env AZURE_DEVOPS_PAT
   ```

2. **OS Keychain Integration**
   ```yaml
   token: !keychain mgit-github-token
   ```

3. **External Secret Manager**
   ```yaml
   token: !vault github/token
   app_password: !cmd "op get item BitBucket --fields password"
   ```

4. **Encrypted File**
   ```yaml
   providers: !include-encrypted ~/.config/mgit/secrets.yaml.enc
   ```

### File Permissions
- Config file should be readable by user only: `chmod 600 ~/.config/mgit/config.yaml`
- Automatic permission check on startup
- Warning if permissions are too open

## Configuration Commands

```bash
# Initialize configuration
mgit config init
# Interactive wizard to create initial config

# Validate configuration
mgit config validate
mgit config validate --file custom-config.yaml

# Edit configuration
mgit config edit
mgit config edit --editor vim

# Show effective configuration
mgit config show
mgit config show --profile work
mgit config show providers.github

# Set values
mgit config set settings.concurrency 8
mgit config set providers.github.accounts.personal.token "new-token"

# Get values
mgit config get settings.default_provider
mgit config get providers.azuredevops.organizations.myorg.url

# Manage profiles
mgit config profiles list
mgit config profiles create mobile
mgit config profiles delete temp
mgit config profiles copy work work-backup
```

## Migration Tool

```bash
# Automatic migration from env vars to YAML
mgit config migrate

# What it does:
# 1. Detects existing env vars and ~/.config/mgit/config (INI)
# 2. Creates ~/.config/mgit/config.yaml
# 3. Backs up old configuration
# 4. Converts values to YAML format
# 5. Updates env var references to use !env tag
# 6. Validates new configuration
```

## Advanced Features

### Dynamic Configuration
```yaml
# Use anchors and aliases for DRY config
defaults: &defaults
  clone_protocol: ssh
  include_lfs: true
  
providers:
  github:
    accounts:
      personal:
        <<: *defaults
        token: !env GITHUB_TOKEN
      work:
        <<: *defaults
        token: !env GITHUB_WORK_TOKEN
```

### Conditional Configuration
```yaml
# Platform-specific settings
settings:
  network:
    proxy:
      http: !if "${os.platform == 'win32' ? 'http://proxy.corp.com:8080' : null}"
```

### Template Variables
```yaml
# Define reusable variables
variables:
  company_domain: mycompany.com
  github_org: mycompany
  
providers:
  github:
    accounts:
      work:
        organization: ${github_org}
        api_url: https://github.${company_domain}/api/v3
```