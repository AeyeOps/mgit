# Repository Filtering and Search Design

## Overview

This document outlines the design for repository filtering capabilities in mgit, allowing users to clone subsets of repositories based on various search criteria with case-insensitive matching support.

## Core Filtering Concepts

### Filter Types

1. **Name-based Filters**
   - Pattern matching (wildcards, regex)
   - Case-sensitive/insensitive options
   - Include/exclude patterns

2. **Metadata Filters**
   - Language
   - Size
   - Last updated
   - Archived status
   - Topics/tags (GitHub)
   - Project (BitBucket)

3. **Composite Filters**
   - AND/OR logic
   - Complex expressions
   - Provider-specific filters

## Command Line Interface

### Basic Filtering Syntax

```bash
# Simple name pattern (case-insensitive by default)
mgit clone-all MyProject ./repos --filter "api"
mgit clone-all MyProject ./repos --filter "*-service"
mgit clone-all MyProject ./repos --filter "frontend-*"

# Case-sensitive matching
mgit clone-all MyProject ./repos --filter "API" --case-sensitive

# Exclude pattern
mgit clone-all MyProject ./repos --exclude "*-deprecated"
mgit clone-all MyProject ./repos --exclude "test-*,temp-*"

# Multiple filters (AND logic)
mgit clone-all MyProject ./repos --filter "*-api" --exclude "*-legacy"

# Complex filter expressions
mgit clone-all MyProject ./repos --filter-expr "name:*-api AND NOT name:*-v1"
```

### Advanced Filtering Options

```bash
# Filter by metadata
mgit clone-all octocat ./repos --filter-language "python,javascript"
mgit clone-all octocat ./repos --filter-updated "30d"  # Updated in last 30 days
mgit clone-all octocat ./repos --filter-size "<1000"   # Less than 1MB

# Provider-specific filters
mgit clone-all octocat ./repos --filter-topics "machine-learning,ai"  # GitHub
mgit clone-all myworkspace ./repos --filter-project "CLOUD"            # BitBucket

# Combined filters
mgit clone-all MyProject ./repos \
  --filter "*-service" \
  --exclude "*-legacy" \
  --filter-language "python" \
  --filter-updated "90d"
```

## Filter Configuration Schema

### Configuration Support

> **NOTE**: The YAML configuration shown below is a proposed design. The actual mgit tool uses a simple key=value configuration format in `~/.config/mgit/config`.

Currently, filtering is done via command-line arguments. A future enhancement could support filter configurations in a config file:

```bash
# Potential future configuration format
# ~/.config/mgit/config
# Filter settings could be added as environment variables or command aliases
    include_patterns: ["*-ui", "*-web", "*-app"]
    languages: ["JavaScript", "TypeScript"]
    exclude_patterns: ["*-legacy"]
    
  microservices:
    include_patterns: ["*-service", "*-api"]
    exclude_patterns: ["*-monolith", "*-legacy"]
    max_size: 50000  # 50MB
```

### Using Named Filter Sets

```bash
# Use predefined filter set
mgit clone-all MyProject ./repos --filter-set backend
mgit clone-all octocat ./repos --filter-set frontend

# Combine filter set with additional filters
mgit clone-all MyProject ./repos --filter-set microservices --filter "*-payment"
```

## Filter Implementation Architecture

### Filter Classes

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Pattern, Union
import re
import fnmatch
from enum import Enum

class FilterMode(Enum):
    WILDCARD = "wildcard"
    REGEX = "regex"
    EXACT = "exact"

@dataclass
class FilterCriteria:
    """Container for all filter criteria"""
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    languages: List[str] = None
    min_size: Optional[int] = None  # KB
    max_size: Optional[int] = None  # KB
    updated_since: Optional[str] = None  # e.g., "30d", "2023-01-01"
    topics: List[str] = None  # GitHub
    projects: List[str] = None  # BitBucket/Azure DevOps
    include_archived: bool = True
    include_disabled: bool = True
    include_forks: bool = True
    case_sensitive: bool = False
    filter_mode: FilterMode = FilterMode.WILDCARD
    
class RepositoryFilter(ABC):
    """Abstract base class for repository filters"""
    
    @abstractmethod
    def matches(self, repository: Repository) -> bool:
        """Check if repository matches filter criteria"""
        pass
        
class NamePatternFilter(RepositoryFilter):
    """Filter repositories by name patterns"""
    
    def __init__(
        self, 
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        case_sensitive: bool = False,
        mode: FilterMode = FilterMode.WILDCARD
    ):
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.case_sensitive = case_sensitive
        self.mode = mode
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile patterns based on mode"""
        if self.mode == FilterMode.WILDCARD:
            # Convert wildcards to regex
            self.include_regex = [
                self._wildcard_to_regex(p) for p in self.include_patterns
            ]
            self.exclude_regex = [
                self._wildcard_to_regex(p) for p in self.exclude_patterns
            ]
        elif self.mode == FilterMode.REGEX:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self.include_regex = [
                re.compile(p, flags) for p in self.include_patterns
            ]
            self.exclude_regex = [
                re.compile(p, flags) for p in self.exclude_patterns
            ]
            
    def _wildcard_to_regex(self, pattern: str) -> Pattern:
        """Convert wildcard pattern to compiled regex"""
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)
        # Convert wildcards
        escaped = escaped.replace(r'\*', '.*').replace(r'\?', '.')
        # Compile with case sensitivity
        flags = 0 if self.case_sensitive else re.IGNORECASE
        return re.compile(f'^{escaped}$', flags)
        
    def matches(self, repository: Repository) -> bool:
        """Check if repository name matches patterns"""
        name = repository.name
        
        # Check exclude patterns first
        for pattern in self.exclude_regex:
            if pattern.match(name):
                return False
                
        # If no include patterns, include by default
        if not self.include_regex:
            return True
            
        # Check include patterns
        for pattern in self.include_regex:
            if pattern.match(name):
                return True
                
        return False

class MetadataFilter(RepositoryFilter):
    """Filter repositories by metadata"""
    
    def __init__(self, criteria: FilterCriteria):
        self.criteria = criteria
        
    def matches(self, repository: Repository) -> bool:
        """Check if repository metadata matches criteria"""
        
        # Language filter
        if self.criteria.languages:
            repo_lang = repository.metadata.get("language", "")
            if not repo_lang:
                return False
            # Case-insensitive language matching
            if not any(
                lang.lower() == repo_lang.lower() 
                for lang in self.criteria.languages
            ):
                return False
                
        # Size filters
        if self.criteria.min_size and repository.size:
            if repository.size < self.criteria.min_size:
                return False
        if self.criteria.max_size and repository.size:
            if repository.size > self.criteria.max_size:
                return False
                
        # Archive/disabled status
        if not self.criteria.include_archived and repository.is_disabled:
            return False
            
        # Fork status (GitHub specific)
        if not self.criteria.include_forks:
            is_fork = repository.metadata.get("is_fork", False)
            if is_fork:
                return False
                
        # Topics (GitHub specific)
        if self.criteria.topics:
            repo_topics = repository.metadata.get("topics", [])
            # Case-insensitive topic matching
            repo_topics_lower = [t.lower() for t in repo_topics]
            if not any(
                topic.lower() in repo_topics_lower 
                for topic in self.criteria.topics
            ):
                return False
                
        return True

class CompositeFilter(RepositoryFilter):
    """Combine multiple filters with AND logic"""
    
    def __init__(self, filters: List[RepositoryFilter]):
        self.filters = filters
        
    def matches(self, repository: Repository) -> bool:
        """All filters must match"""
        return all(f.matches(repository) for f in self.filters)
        
class FilterFactory:
    """Create filters from criteria"""
    
    @staticmethod
    def create_from_criteria(criteria: FilterCriteria) -> RepositoryFilter:
        """Create composite filter from criteria"""
        filters = []
        
        # Name pattern filter
        if criteria.include_patterns or criteria.exclude_patterns:
            filters.append(NamePatternFilter(
                include_patterns=criteria.include_patterns,
                exclude_patterns=criteria.exclude_patterns,
                case_sensitive=criteria.case_sensitive,
                mode=criteria.filter_mode
            ))
            
        # Metadata filter
        if any([
            criteria.languages,
            criteria.min_size,
            criteria.max_size,
            criteria.topics,
            not criteria.include_archived,
            not criteria.include_forks
        ]):
            filters.append(MetadataFilter(criteria))
            
        # Return appropriate filter
        if not filters:
            return AlwaysMatchFilter()
        elif len(filters) == 1:
            return filters[0]
        else:
            return CompositeFilter(filters)

class AlwaysMatchFilter(RepositoryFilter):
    """Filter that matches all repositories"""
    
    def matches(self, repository: Repository) -> bool:
        return True
```

### Integration with Providers

```python
# In GitProvider base class
async def list_repositories_filtered(
    self,
    organization: str,
    project: Optional[str] = None,
    filter_criteria: Optional[FilterCriteria] = None
) -> AsyncIterator[Repository]:
    """List repositories with filtering applied"""
    
    # Create filter
    repo_filter = FilterFactory.create_from_criteria(
        filter_criteria or FilterCriteria()
    )
    
    # Apply filter to repository stream
    async for repo in self.list_repositories(organization, project):
        if repo_filter.matches(repo):
            yield repo
```

### CLI Integration

```python
# In cli.py
@app.command()
def clone_all(
    scope: str = typer.Argument(..., help="Project/Organization/Workspace"),
    path: Path = typer.Argument(..., help="Local directory to clone into"),
    # Basic filters
    filter: Optional[str] = typer.Option(
        None, "--filter", "-f",
        help="Include repositories matching pattern (wildcards: *, ?)"
    ),
    exclude: Optional[str] = typer.Option(
        None, "--exclude", "-e",
        help="Exclude repositories matching pattern"
    ),
    # Advanced filters
    filter_language: Optional[str] = typer.Option(
        None, "--filter-language", "--lang",
        help="Filter by programming language (comma-separated)"
    ),
    filter_size: Optional[str] = typer.Option(
        None, "--filter-size",
        help="Filter by size (e.g., '<1000', '>100', '100-1000')"
    ),
    filter_updated: Optional[str] = typer.Option(
        None, "--filter-updated",
        help="Filter by last update (e.g., '30d', '6m', '2023-01-01')"
    ),
    # Filter options
    case_sensitive: bool = typer.Option(
        False, "--case-sensitive", "-C",
        help="Use case-sensitive pattern matching"
    ),
    use_regex: bool = typer.Option(
        False, "--regex", "-r",
        help="Use regex instead of wildcards for patterns"
    ),
    # Named filter sets
    filter_set: Optional[str] = typer.Option(
        None, "--filter-set", "-s",
        help="Use predefined filter set from config"
    ),
    # Other options...
):
    """Clone repositories with optional filtering"""
    
    # Build filter criteria
    criteria = FilterCriteria(
        case_sensitive=case_sensitive,
        filter_mode=FilterMode.REGEX if use_regex else FilterMode.WILDCARD
    )
    
    # Parse simple filters
    if filter:
        criteria.include_patterns = [p.strip() for p in filter.split(",")]
    if exclude:
        criteria.exclude_patterns = [p.strip() for p in exclude.split(",")]
    if filter_language:
        criteria.languages = [l.strip() for l in filter_language.split(",")]
        
    # Load filter set if specified
    if filter_set:
        set_criteria = load_filter_set(filter_set)
        criteria = merge_criteria(criteria, set_criteria)
```

## Filter Expression Language

### Advanced Filter Expressions

```bash
# Complex filter expressions
mgit clone-all MyProject ./repos --filter-expr "
  (name:*-api OR name:*-service) AND 
  language:python AND 
  size:<10000 AND
  updated:>30d AND
  NOT name:*-deprecated
"

# Short form
mgit clone-all MyProject ./repos --expr "name~api|service & lang:py & !name~old"
```

### Expression Grammar

```
expression     := term (AND term)* | term (OR term)*
term           := NOT? (condition | '(' expression ')')
condition      := field operator value
field          := 'name' | 'lang' | 'language' | 'size' | 'updated' | 'topic'
operator       := ':' | '=' | '~' | '>' | '<' | '>=' | '<='
value          := string | number | pattern
pattern        := wildcard_pattern | /regex_pattern/
```

## Use Cases

### 1. Microservices Architecture
```bash
# Clone only microservices
mgit clone-all MyProject ./services --filter "*-service,*-api" --exclude "*-monolith"
```

### 2. Language-Specific Repos
```bash
# Clone only Python projects
mgit clone-all MyProject ./python-repos --filter-language "Python"

# Clone JavaScript/TypeScript projects
mgit clone-all octocat ./js-repos --filter-language "JavaScript,TypeScript"
```

### 3. Active Projects Only
```bash
# Clone repos updated in last 30 days, excluding archived
mgit clone-all MyProject ./active --filter-updated "30d" --no-archived
```

### 4. Size-Constrained Cloning
```bash
# Clone only small repositories (< 10MB)
mgit clone-all MyProject ./small-repos --filter-size "<10000"
```

### 5. Topic-Based (GitHub)
```bash
# Clone machine learning projects
mgit clone-all octocat ./ml-repos --filter-topics "machine-learning,deep-learning,ai"
```

## Performance Considerations

### Filtering Strategy

1. **Server-Side Filtering** (when available)
   - Some providers support API-level filtering
   - Reduces data transfer and API calls

2. **Client-Side Filtering**
   - More flexible but requires fetching all repos
   - Can be optimized with pagination

3. **Hybrid Approach**
   - Use server-side for basic filters
   - Apply advanced filters client-side

### Implementation Example

```python
# Provider-specific optimizations
class GitHubProvider(GitProvider):
    async def list_repositories_filtered(
        self,
        organization: str,
        project: Optional[str] = None,
        filter_criteria: Optional[FilterCriteria] = None
    ) -> AsyncIterator[Repository]:
        """GitHub-optimized filtering"""
        
        # Use GitHub API search when possible
        if filter_criteria and self._can_use_search_api(filter_criteria):
            query = self._build_search_query(organization, filter_criteria)
            async for repo in self._search_repositories(query):
                yield repo
        else:
            # Fall back to client-side filtering
            async for repo in super().list_repositories_filtered(
                organization, project, filter_criteria
            ):
                yield repo
```

## Configuration Examples

### Personal Developer Setup
```yaml
filter_sets:
  personal:
    include_patterns: ["*"]
    exclude_patterns: ["*-fork", "*-archive", "test-*"]
    include_archived: false
    include_forks: false
```

### Enterprise Setup
```yaml
filter_sets:
  production:
    include_patterns: ["prod-*", "prd-*"]
    exclude_patterns: ["*-test", "*-dev", "*-staging"]
    
  development:
    include_patterns: ["dev-*", "feature-*"]
    exclude_patterns: ["prod-*", "prd-*"]
    
  compliance:
    include_patterns: ["*"]
    exclude_patterns: []
    filter_expr: "topic:compliant AND updated:<90d"
```

## Error Handling

### User-Friendly Messages
```
Error: Invalid filter pattern '*-api['.
Hint: Wildcards use * and ?. For regex, use --regex flag.

Error: No repositories match filter criteria.
Found 50 repositories, but none match:
  - Include pattern: *-api
  - Language: Python
  - Updated: last 30 days
Hint: Try broadening your search criteria.
```

### Filter Validation
```python
def validate_filter_criteria(criteria: FilterCriteria) -> List[str]:
    """Validate filter criteria and return errors"""
    errors = []
    
    # Validate patterns
    for pattern in criteria.include_patterns + criteria.exclude_patterns:
        if criteria.filter_mode == FilterMode.REGEX:
            try:
                re.compile(pattern)
            except re.error as e:
                errors.append(f"Invalid regex '{pattern}': {e}")
                
    # Validate size format
    if criteria.max_size and criteria.min_size:
        if criteria.max_size < criteria.min_size:
            errors.append("Maximum size must be greater than minimum size")
            
    return errors
```