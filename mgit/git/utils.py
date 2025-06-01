"""Git-related utility functions for mgit CLI tool."""

import re
from urllib.parse import unquote, urlparse, urlunparse


def embed_pat_in_url(repo_url: str, pat: str) -> str:
    """
    Rewrite repo_url to embed the PAT as credentials:
      https://org@dev.azure.com ->
        https://PersonalAccessToken:PAT@dev.azure.com
    That way 'git clone' won't prompt for credentials.
    """
    parsed = urlparse(repo_url)
    # Some ADOS remoteUrls look like:
    # 'https://org@dev.azure.com/org/project/_git/repo'
    # We'll embed 'PersonalAccessToken:pat@' as netloc
    # credentials, ignoring any existing user
    # Some Azure DevOps setups require this exact username
    username = "PersonalAccessToken"
    netloc = f"{username}:{pat}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"

    new_parsed = parsed._replace(netloc=netloc)
    return urlunparse(new_parsed)


def sanitize_repo_name(repo_url: str) -> str:
    """
    Extract and sanitize repository name from URL for use as a directory name.
    Handles URL encoding, spaces, and special characters.

    Example:
      Input: https://dev.azure.com/org/project/_git/Repo%20Name%20With%20Spaces
      Output: Repo_Name_With_Spaces
    """
    # Extract repo name from URL
    parsed = urlparse(repo_url)
    path_parts = parsed.path.split("/")
    # The repo name is typically the last part of the path after _git
    repo_name = ""
    for i, part in enumerate(path_parts):
        if part == "_git" and i + 1 < len(path_parts):
            repo_name = path_parts[i + 1]
            break

    # If we couldn't find it after _git, use the last part of the path
    if not repo_name and path_parts:
        repo_name = path_parts[-1]

    # Decode URL encoding
    repo_name = unquote(repo_name)

    # Replace spaces and special characters with underscores
    # Keep alphanumeric, underscore, hyphen, and period
    repo_name = re.sub(r"[^\w\-\.]", "_", repo_name)

    return repo_name
