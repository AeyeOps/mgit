# BitBucket Hierarchical Filtering Design

## Overview

BitBucket Cloud has a three-tier hierarchy that allows for sophisticated filtering at each level:
- **Workspace** (top level - like an organization)
- **Project** (optional grouping within workspace)
- **Repository** (actual git repositories)

This document outlines the design for hierarchical filtering that allows users to apply wildcard case-insensitive searches at each level, progressively narrowing down the repositories to clone.

## BitBucket Hierarchy Structure

```
Workspace (e.g., "atlassian")
├── Project: CLOUD
│   ├── Repository: cloud-api
│   ├── Repository: cloud-frontend
│   └── Repository: cloud-auth-service
├── Project: MOBILE
│   ├── Repository: mobile-ios
│   ├── Repository: mobile-android
│   └── Repository: mobile-shared
├── Project: INTERNAL
│   ├── Repository: internal-tools
│   └── Repository: internal-docs
└── (No Project)
    ├── Repository: legacy-monolith
    └── Repository: experimental-ai
```

## Command Line Interface for Hierarchical Filtering

### Basic Usage

```bash
# Filter at workspace level only (gets ALL repos from matching workspaces)
mgit clone-all --provider bitbucket "*labs" ./repos

# Filter at workspace and project level
mgit clone-all --provider bitbucket "atlassian/*cloud*" ./repos

# Filter at all three levels
mgit clone-all --provider bitbucket "atlassian/*cloud*/*api*" ./repos

# Alternative syntax with explicit level specification
mgit clone-all --provider bitbucket \
  --workspace "*labs" \
  --project "*cloud*" \
  --repo "*api*" \
  ./repos
```

### Advanced Hierarchical Filtering

```bash
# Multiple patterns at each level
mgit clone-all --provider bitbucket \
  --workspace "atlassian,bitbucket-*" \
  --project "CLOUD,MOBILE" \
  --repo "*-service,*-api" \
  --exclude-repo "*-deprecated" \
  ./repos

# Case sensitivity control per level
mgit clone-all --provider bitbucket \
  --workspace "Atlassian" --workspace-case-sensitive \
  --project "*cloud*" \
  --repo "*API*" --repo-case-sensitive \
  ./repos

# Include repositories without projects
mgit clone-all --provider bitbucket \
  --workspace "atlassian" \
  --project "*,NONE" \  # NONE = repos without project
  ./repos
```

## Hierarchical Filter Architecture

### Filter Data Structures

```python
from dataclasses import dataclass
from typing import List, Optional, Set
from enum import Enum

@dataclass
class HierarchicalFilter:
    """Hierarchical filter for BitBucket repositories"""
    
    # Workspace level filters
    workspace_patterns: List[str] = None
    workspace_exclude_patterns: List[str] = None
    workspace_case_sensitive: bool = False
    
    # Project level filters
    project_patterns: List[str] = None
    project_exclude_patterns: List[str] = None
    project_case_sensitive: bool = False
    include_no_project: bool = True  # Include repos without project
    
    # Repository level filters
    repo_patterns: List[str] = None
    repo_exclude_patterns: List[str] = None
    repo_case_sensitive: bool = False
    
    # Additional repository metadata filters
    languages: List[str] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    updated_since: Optional[str] = None

class FilterLevel(Enum):
    WORKSPACE = "workspace"
    PROJECT = "project"
    REPOSITORY = "repository"

@dataclass
class FilterMatch:
    """Result of hierarchical filter matching"""
    workspace: str
    project: Optional[str]  # None for repos without project
    repositories: List[str]
    total_matches: int
    
@dataclass
class FilterContext:
    """Context passed through filtering pipeline"""
    workspace_matches: Set[str]
    project_matches: Dict[str, Set[str]]  # workspace -> projects
    repository_matches: Dict[str, Dict[str, List[Repository]]]  # workspace -> project -> repos
```

### BitBucket Provider Enhancement

```python
class BitBucketProvider(GitProvider):
    """Enhanced BitBucket provider with hierarchical filtering"""
    
    async def list_workspaces_filtered(
        self,
        patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        case_sensitive: bool = False
    ) -> List[str]:
        """List workspaces matching filter patterns"""
        
        # Create filter for workspace names
        name_filter = NamePatternFilter(
            include_patterns=patterns,
            exclude_patterns=exclude_patterns,
            case_sensitive=case_sensitive
        )
        
        workspaces = []
        
        # Get all accessible workspaces
        try:
            ws_data = self._client.workspaces.each()
            for ws in ws_data:
                workspace_name = ws["slug"]
                
                # Create temporary object for filter matching
                temp_obj = Repository(
                    name=workspace_name,
                    clone_url="",  # Not used for filtering
                    provider=self.PROVIDER_NAME
                )
                
                if name_filter.matches(temp_obj):
                    workspaces.append(workspace_name)
                    
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            
        return workspaces
    
    async def list_projects_filtered(
        self,
        workspace: str,
        patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        case_sensitive: bool = False,
        include_none: bool = True
    ) -> List[Optional[str]]:
        """List projects in workspace matching filter patterns"""
        
        name_filter = NamePatternFilter(
            include_patterns=patterns,
            exclude_patterns=exclude_patterns,
            case_sensitive=case_sensitive
        )
        
        projects = []
        
        try:
            # Get projects in workspace
            workspace_projects = self._client.workspaces.get(workspace).projects.each()
            
            for proj in workspace_projects:
                project_key = proj["key"]
                
                # Create temporary object for filter matching
                temp_obj = Repository(
                    name=project_key,
                    clone_url="",
                    provider=self.PROVIDER_NAME
                )
                
                if name_filter.matches(temp_obj):
                    projects.append(project_key)
                    
            # Check if we should include "no project" option
            if include_none and (not patterns or self._matches_none_pattern(patterns)):
                projects.append(None)  # None represents repos without project
                
        except Exception as e:
            logger.error(f"Failed to list projects in {workspace}: {e}")
            
        return projects
    
    async def list_repositories_hierarchical(
        self,
        filter: HierarchicalFilter,
        progress_callback: Optional[Callable] = None
    ) -> AsyncIterator[Repository]:
        """List repositories using hierarchical filtering"""
        
        # Step 1: Filter workspaces
        matching_workspaces = await self.list_workspaces_filtered(
            patterns=filter.workspace_patterns,
            exclude_patterns=filter.workspace_exclude_patterns,
            case_sensitive=filter.workspace_case_sensitive
        )
        
        if progress_callback:
            progress_callback(f"Found {len(matching_workspaces)} matching workspaces")
        
        # Step 2: For each workspace, filter projects
        for workspace in matching_workspaces:
            matching_projects = await self.list_projects_filtered(
                workspace=workspace,
                patterns=filter.project_patterns,
                exclude_patterns=filter.project_exclude_patterns,
                case_sensitive=filter.project_case_sensitive,
                include_none=filter.include_no_project
            )
            
            if progress_callback:
                progress_callback(
                    f"Workspace '{workspace}': "
                    f"Found {len(matching_projects)} matching projects"
                )
            
            # Step 3: For each project, filter repositories
            for project in matching_projects:
                # Create repository filter
                repo_filter = NamePatternFilter(
                    include_patterns=filter.repo_patterns,
                    exclude_patterns=filter.repo_exclude_patterns,
                    case_sensitive=filter.repo_case_sensitive
                )
                
                # Get repositories for this workspace/project combination
                if project is None:
                    # Get repos without project
                    query = 'project.key = null'
                else:
                    # Get repos in specific project
                    query = f'project.key="{project}"'
                
                try:
                    repos = self._client.workspaces.get(workspace).repositories.each(q=query)
                    
                    for repo_data in repos:
                        repo = self._convert_to_repository(repo_data, workspace, project)
                        
                        # Apply repository-level filter
                        if repo_filter.matches(repo):
                            # Apply metadata filters if any
                            if self._matches_metadata_filters(repo, filter):
                                yield repo
                                
                except Exception as e:
                    logger.error(
                        f"Failed to list repos in {workspace}/{project or 'NO_PROJECT'}: {e}"
                    )
    
    def _matches_metadata_filters(
        self,
        repo: Repository,
        filter: HierarchicalFilter
    ) -> bool:
        """Check if repository matches metadata filters"""
        
        # Language filter
        if filter.languages:
            repo_lang = repo.metadata.get("language", "")
            if not any(
                lang.lower() == repo_lang.lower()
                for lang in filter.languages
            ):
                return False
                
        # Size filters
        if filter.min_size and repo.size and repo.size < filter.min_size:
            return False
        if filter.max_size and repo.size and repo.size > filter.max_size:
            return False
            
        # Add more metadata filters as needed
        
        return True
    
    def _convert_to_repository(
        self,
        repo_data: dict,
        workspace: str,
        project: Optional[str]
    ) -> Repository:
        """Convert BitBucket API response to Repository object"""
        return Repository(
            name=repo_data["slug"],
            clone_url=repo_data["links"]["clone"][0]["href"],  # HTTPS
            ssh_url=repo_data["links"]["clone"][1]["href"] if len(repo_data["links"]["clone"]) > 1 else None,
            is_disabled=False,  # BitBucket doesn't have disabled state
            is_private=repo_data.get("is_private", True),
            default_branch=repo_data.get("mainbranch", {}).get("name", "main"),
            size=repo_data.get("size"),
            description=repo_data.get("description"),
            created_at=repo_data.get("created_on"),
            updated_at=repo_data.get("updated_on"),
            provider=self.PROVIDER_NAME,
            metadata={
                "uuid": repo_data["uuid"],
                "language": repo_data.get("language"),
                "workspace": workspace,
                "project": project,
                "full_path": f"{workspace}/{project}/{repo_data['slug']}" if project else f"{workspace}/{repo_data['slug']}"
            }
        )
    
    def _matches_none_pattern(self, patterns: List[str]) -> bool:
        """Check if patterns include NONE or equivalent"""
        none_patterns = ["none", "null", "no-project", "no_project", "_none_"]
        for pattern in patterns:
            if pattern.lower() in none_patterns:
                return True
            # Check if wildcard would match NONE
            if "*" in pattern:
                import fnmatch
                if fnmatch.fnmatch("NONE", pattern):
                    return True
        return False
```

### CLI Integration for Hierarchical Filtering

```python
# Enhanced CLI command
@app.command()
def clone_all(
    scope: str = typer.Argument(
        ...,
        help="Scope specification:\n"
             "  - Azure DevOps: project name\n"
             "  - GitHub: organization name\n"
             "  - BitBucket: workspace[/project][/repo] with wildcards"
    ),
    path: Path = typer.Argument(..., help="Local directory to clone into"),
    
    # BitBucket hierarchical filters (when using explicit flags)
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w",
        help="BitBucket workspace pattern (supports wildcards)"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p",
        help="BitBucket project pattern (supports wildcards, use NONE for no project)"
    ),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r",
        help="Repository name pattern (supports wildcards)"
    ),
    
    # Exclude patterns for each level
    exclude_workspace: Optional[str] = typer.Option(
        None, "--exclude-workspace",
        help="Exclude workspaces matching pattern"
    ),
    exclude_project: Optional[str] = typer.Option(
        None, "--exclude-project",
        help="Exclude projects matching pattern"
    ),
    exclude_repo: Optional[str] = typer.Option(
        None, "--exclude-repo",
        help="Exclude repositories matching pattern"
    ),
    
    # Case sensitivity per level
    workspace_case_sensitive: bool = typer.Option(
        False, "--workspace-case-sensitive",
        help="Use case-sensitive matching for workspaces"
    ),
    project_case_sensitive: bool = typer.Option(
        False, "--project-case-sensitive",
        help="Use case-sensitive matching for projects"
    ),
    repo_case_sensitive: bool = typer.Option(
        False, "--repo-case-sensitive",
        help="Use case-sensitive matching for repositories"
    ),
    
    # Other options...
):
    """Clone repositories with hierarchical filtering support"""
    
    # Parse scope for BitBucket hierarchical patterns
    if provider == "bitbucket":
        if "/" in scope:
            # Parse hierarchical scope
            parts = scope.split("/", 2)
            
            # Override with parsed values if not explicitly set
            if not workspace and len(parts) > 0:
                workspace = parts[0]
            if not project and len(parts) > 1:
                project = parts[1]
            if not repo and len(parts) > 2:
                repo = parts[2]
        else:
            # Single value is workspace
            if not workspace:
                workspace = scope
```

## Usage Examples

### Common BitBucket Filtering Scenarios

#### 1. Clone All Repos from Multiple Workspaces
```bash
# Clone from all workspaces starting with "team-"
mgit clone-all --provider bitbucket "team-*" ./repos

# Clone from specific workspaces
mgit clone-all --provider bitbucket "atlassian,bitbucket-labs" ./repos
```

#### 2. Project-Level Filtering
```bash
# Clone all repos from CLOUD and MOBILE projects
mgit clone-all --provider bitbucket "atlassian/CLOUD,MOBILE" ./repos

# Clone all repos from projects containing "dev"
mgit clone-all --provider bitbucket "atlassian/*dev*" ./repos

# Include repos without projects
mgit clone-all --provider bitbucket "atlassian/*,NONE" ./repos
```

#### 3. Full Hierarchical Filtering
```bash
# Clone API services from cloud projects across all tech workspaces
mgit clone-all --provider bitbucket "*tech*/*cloud*/*api*" ./repos

# More explicit version
mgit clone-all --provider bitbucket \
  --workspace "*tech*" \
  --project "*cloud*" \
  --repo "*api*,*service*" \
  --exclude-repo "*legacy*,*deprecated*" \
  ./repos
```

#### 4. Case-Sensitive Filtering
```bash
# Case-sensitive project names but case-insensitive repos
mgit clone-all --provider bitbucket \
  --workspace "Atlassian" --workspace-case-sensitive \
  --project "CLOUD" --project-case-sensitive \
  --repo "*api*" \
  ./repos
```

#### 5. Complex Filtering
```bash
# Clone Python microservices from cloud projects, excluding deprecated
mgit clone-all --provider bitbucket \
  --workspace "atlassian,bitbucket-*" \
  --project "*CLOUD*,*PLATFORM*" \
  --repo "*-service,*-api" \
  --exclude-repo "*-deprecated,*-legacy,test-*" \
  --filter-language "Python" \
  --filter-size "<50000" \
  ./repos
```

## Progress and Feedback

### Hierarchical Progress Display

```
Scanning BitBucket repositories...

🔍 Workspace Level:
   ✓ atlassian (matched)
   ✓ bitbucket-labs (matched)
   ✗ personal-workspace (excluded)
   
📁 Project Level (atlassian):
   ✓ CLOUD (15 repos)
   ✓ CLOUD-INFRASTRUCTURE (8 repos)
   ✗ MOBILE (filtered out)
   ✓ NO_PROJECT (3 repos)
   
📦 Repository Level (atlassian/CLOUD):
   ✓ cloud-api-gateway (matched)
   ✓ cloud-auth-service (matched)
   ✗ cloud-frontend (filtered out)
   ✓ cloud-payment-api (matched)
   
Total: 3 workspaces → 5 projects → 47 repositories matched

Cloning 47 repositories...
[████████████████████████] 47/47 Complete
```

### Dry Run Mode

```bash
# Preview what would be cloned
mgit clone-all --provider bitbucket \
  "atlassian/*cloud*/*api*" \
  ./repos \
  --dry-run

Would clone:
  atlassian/CLOUD/cloud-api-gateway
  atlassian/CLOUD/cloud-auth-api
  atlassian/CLOUD-INFRASTRUCTURE/infra-api
  atlassian/NO_PROJECT/legacy-api
  
Total: 4 repositories (estimated 156 MB)
```

## Configuration Support

### YAML Configuration for Hierarchical Filters

```yaml
providers:
  bitbucket:
    workspaces:
      default: atlassian
      atlassian:
        username: !env BITBUCKET_USERNAME
        app_password: !env BITBUCKET_APP_PASSWORD
        
        # Default hierarchical filters
        default_filters:
          workspace_patterns: ["atlassian", "bitbucket-*"]
          project_patterns: ["CLOUD*", "PLATFORM*"]
          repo_patterns: ["*-service", "*-api"]
          exclude_repo_patterns: ["*-deprecated", "*-archive"]
          include_no_project: false

# Named hierarchical filter sets
filter_sets:
  bitbucket_cloud:
    workspace_patterns: ["atlassian"]
    project_patterns: ["CLOUD*"]
    repo_patterns: ["*"]
    
  bitbucket_microservices:
    workspace_patterns: ["*"]
    project_patterns: ["*"]
    repo_patterns: ["*-service", "*-api", "*-worker"]
    exclude_repo_patterns: ["*-monolith", "*-legacy"]
```

## Performance Optimization

### Parallel Filtering
```python
async def list_repositories_hierarchical_optimized(
    self,
    filter: HierarchicalFilter
) -> AsyncIterator[Repository]:
    """Optimized hierarchical filtering with parallelization"""
    
    # Get all workspaces in parallel
    workspace_tasks = []
    for ws in await self.list_workspaces_filtered(...):
        task = self._filter_workspace(ws, filter)
        workspace_tasks.append(task)
    
    # Process workspaces concurrently
    workspace_results = await asyncio.gather(*workspace_tasks)
    
    # Yield results as they complete
    for repos in workspace_results:
        for repo in repos:
            yield repo
```

### Caching Strategy
- Cache workspace list (changes rarely)
- Cache project list per workspace (changes occasionally)
- Don't cache repository list (changes frequently)

## Error Handling

### Hierarchical Error Messages
```
Error: No workspaces found matching pattern '*labs'
Available workspaces: atlassian, bitbucket-archive, personal-ws

Error: No projects found in workspace 'atlassian' matching pattern 'INVALID*'
Available projects in 'atlassian': CLOUD, MOBILE, PLATFORM, INTERNAL

Error: Filter would result in 0 repositories
Workspace matches: 2
Project matches: 5  
Repository filter eliminated all candidates
Hint: Check your repository patterns or try --dry-run to debug
```