"""Collision detection and resolution for flat directory layout.

When using flat layout mode, multiple repositories from different orgs/providers
may have the same name. This module detects collisions and generates unique names.
"""

from collections import defaultdict

from mgit.git.utils import extract_repo_name, get_repo_components
from mgit.providers.base import Repository


def detect_repo_name_collisions(
    repositories: list[Repository],
) -> dict[str, list[Repository]]:
    """
    Group repositories by their base name to detect collisions.

    Args:
        repositories: List of Repository objects to check

    Returns:
        Dict mapping repo names to list of repos with that name.
        Names with only one repo are not collisions.
    """
    name_groups: dict[str, list[Repository]] = defaultdict(list)

    for repo in repositories:
        try:
            base_name = extract_repo_name(repo.clone_url)
            name_groups[base_name].append(repo)
        except ValueError:
            # If we can't extract a name, use the repo.name as fallback
            name_groups[repo.name].append(repo)

    return dict(name_groups)


def resolve_collision_names(
    repositories: list[Repository],
) -> dict[str, str]:
    """
    Generate unique names for all repositories, resolving collisions.

    For repos with unique names, returns the original name.
    For colliding repos, appends disambiguation suffix (org name, then provider).

    Args:
        repositories: List of Repository objects

    Returns:
        Dict mapping clone_url to resolved unique directory name
    """
    name_groups = detect_repo_name_collisions(repositories)
    resolved: dict[str, str] = {}

    for base_name, repos in name_groups.items():
        if len(repos) == 1:
            # No collision - use base name
            resolved[repos[0].clone_url] = base_name
        else:
            # Collision detected - need disambiguation
            resolved.update(_resolve_collision_group(base_name, repos))

    return resolved


def _resolve_collision_group(base_name: str, repos: list[Repository]) -> dict[str, str]:
    """
    Resolve naming collision for a group of repos with the same base name.

    Strategy:
    1. Try: base_name_orgname
    2. If org names also collide: base_name_provider_orgname

    Args:
        base_name: The colliding repository name
        repos: List of repos with this name

    Returns:
        Dict mapping clone_url to resolved unique name
    """
    resolved: dict[str, str] = {}

    # First attempt: use org name as suffix
    org_based_names: dict[str, list[Repository]] = defaultdict(list)

    for repo in repos:
        components = get_repo_components(repo.clone_url)
        if components:
            _host, org, _project, _repo_name = components
            candidate_name = f"{base_name}_{org}"
            org_based_names[candidate_name].append(repo)
        else:
            raise ValueError(
                f"Cannot parse clone URL for collision resolution: {repo.clone_url}"
            )

    # Check if org-based names resolved all collisions
    for candidate_name, group in org_based_names.items():
        if len(group) == 1:
            resolved[group[0].clone_url] = candidate_name
        else:
            # Still have collision - add provider/host as prefix
            resolved.update(_resolve_with_provider(base_name, group))

    return resolved


def _resolve_with_provider(base_name: str, repos: list[Repository]) -> dict[str, str]:
    """
    Final resolution using provider/host in the name.

    Args:
        base_name: The original colliding repository name
        repos: List of repos still colliding after org disambiguation

    Returns:
        Dict mapping clone_url to unique name
    """
    resolved: dict[str, str] = {}
    used_names: set[str] = set()

    for repo in repos:
        components = get_repo_components(repo.clone_url)
        if components:
            host, org, _project, _repo_name = components
            # Simplify host name (github.com -> github, dev.azure.com -> azure)
            simple_host = _simplify_host(host)
            candidate_name = f"{base_name}_{simple_host}_{org}"
        else:
            raise ValueError(
                f"Cannot parse clone URL for collision resolution: {repo.clone_url}"
            )

        # Ensure uniqueness with counter if still colliding
        final_name = candidate_name
        counter = 2
        while final_name in used_names:
            final_name = f"{candidate_name}_{counter}"
            counter += 1

        used_names.add(final_name)
        resolved[repo.clone_url] = final_name

    return resolved


def _simplify_host(host: str) -> str:
    """
    Simplify a hostname to a short provider identifier.

    Examples:
        github.com -> github
        dev.azure.com -> azure
        bitbucket.org -> bitbucket
        gitlab.example.com -> gitlab
    """
    host_lower = host.lower()

    if "github" in host_lower:
        return "github"
    elif "azure" in host_lower or "visualstudio" in host_lower:
        return "azure"
    elif "bitbucket" in host_lower:
        return "bitbucket"
    elif "gitlab" in host_lower:
        return "gitlab"
    else:
        # Use first segment of hostname
        return host.split(".")[0]
