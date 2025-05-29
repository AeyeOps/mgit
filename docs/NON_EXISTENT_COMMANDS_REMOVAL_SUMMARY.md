# Non-Existent Commands Removal Summary

## Overview
This document summarizes the removal of references to non-implemented commands from the mgit documentation.

## Actually Implemented Commands (as of current version)
The following commands are actually implemented and available in mgit:
- `login` - Login to git provider and validate credentials
- `clone-all` - Clone all repositories from a git provider project/organization
- `pull-all` - Pull the latest changes for all repositories in the specified path
- `config` - Set or view global configuration settings for mgit
- `generate-env` - Generate a sample environment file with configuration options

## Commands That Were Referenced But Don't Exist
The following commands were referenced in documentation but are not implemented:
- `list` (and all subcommands: `list-repos`, `list-projects`, `list-workspaces`)
- `credential` (and all subcommands)
- `auth` subcommands (except `login` which is a top-level command)
- `status`
- `info`
- `filter`
- Various command options that don't exist (e.g., `--filter`, `--exclude`, `--branch`, etc.)

## Files Modified

### 1. Main Documentation Files
- **README.md** - No changes needed (already correctly documented only real commands)

### 2. Provider Usage Guides
- **docs/providers/azure-devops-usage-guide.md**
  - Removed references to `list-projects` and `list-repos` commands
  - Updated examples to use only implemented commands
  
- **docs/providers/github-usage-guide.md**
  - Removed all `list-repos` command references
  - Fixed command syntax to match actual implementation
  - Removed non-existent options like `--filter`, `--exclude`, `--branch`
  
- **docs/providers/bitbucket-usage-guide.md**
  - Removed `list-workspaces` and `list-repos` commands
  - Updated all examples to use correct command syntax
  - Removed non-existent filtering and project-specific options

### 3. Provider Comparison Guide
- **docs/providers/provider-comparison-guide.md**
  - Updated all command examples to use actual syntax
  - Fixed provider names (azdevops → azuredevops)

### 4. CLI Design Documents
- **docs/cli-design/cli-subcommand-design.md**
  - Added header noting this is a future design proposal
  - Marked non-implemented commands as "not implemented"
  
- **docs/cli-design/command-structure-design.md**
  - Added note that this describes future/potential commands

## Command Syntax Corrections

### Old (Incorrect) Syntax Examples:
```bash
mgit list-repos --provider github --org steveant
mgit clone-all --provider github --org steveant --destination ./repos
mgit pull-all --provider github --path ./repos --strategy rebase
```

### New (Correct) Syntax:
```bash
mgit clone-all steveant ./repos --provider github
mgit pull-all steveant ./repos --provider github
```

## Key Changes Made
1. All `list*` commands removed - users should use web interfaces to explore repositories
2. Command syntax corrected to match actual implementation (positional args before options)
3. Non-existent options removed (no filtering, no branch selection, etc.)
4. Provider names corrected where needed (azdevops → azuredevops)
5. Future/proposed commands clearly marked as such in design documents

## Verification
All documented commands can now be verified by running:
```bash
python -m mgit --help
python -m mgit [command] --help
```

The documentation now accurately reflects the actual functionality available in mgit.