# Bitbucket Cloud API Endpoints

This document outlines the key Bitbucket Cloud API endpoints that will be used in our CLI application. The base URL for all Bitbucket Cloud API v2.0 endpoints is `https://api.bitbucket.org/2.0/`.

## Authentication

### Get Access Token (OAuth 2.0)

```
POST https://bitbucket.org/site/oauth2/access_token
```

**Parameters:**
- `grant_type`: The OAuth grant type (e.g., `client_credentials`)
- `client_id`: The OAuth consumer key
- `client_secret`: The OAuth consumer secret

**Response:**
```json
{
  "access_token": "your-access-token",
  "scopes": "repository:read repository:write",
  "expires_in": 7200,
  "refresh_token": "your-refresh-token",
  "token_type": "bearer"
}
```

## Workspaces

### List Workspaces

```
GET /workspaces
```

**Parameters:**
- `role` (optional): Filter by role (e.g., `owner`, `collaborator`)
- `q` (optional): Query string for filtering

**Response:**
```json
{
  "values": [
    {
      "uuid": "{workspace-uuid}",
      "name": "Workspace Name",
      "slug": "workspace-slug",
      "is_private": true
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Get Workspace

```
GET /workspaces/{workspace}
```

**Response:**
```json
{
  "uuid": "{workspace-uuid}",
  "name": "Workspace Name",
  "slug": "workspace-slug",
  "is_private": true
}
```

## Projects

### List Projects

```
GET /workspaces/{workspace}/projects
```

**Parameters:**
- `q` (optional): Query string for filtering
- `sort` (optional): Field to sort by
- `page` (optional): Page number for pagination
- `pagelen` (optional): Number of items per page

**Response:**
```json
{
  "values": [
    {
      "uuid": "{project-uuid}",
      "key": "PROJECT",
      "name": "Project Name",
      "description": "Project description"
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Get Project

```
GET /workspaces/{workspace}/projects/{project}
```

**Response:**
```json
{
  "uuid": "{project-uuid}",
  "key": "PROJECT",
  "name": "Project Name",
  "description": "Project description"
}
```

### Create Project

```
POST /workspaces/{workspace}/projects
```

**Request Body:**
```json
{
  "name": "Project Name",
  "key": "PROJECT",
  "description": "Project description",
  "is_private": true
}
```

## Repositories

### List Repositories

```
GET /repositories/{workspace}
```

**Parameters:**
- `q` (optional): Query string for filtering
- `sort` (optional): Field to sort by
- `page` (optional): Page number for pagination
- `pagelen` (optional): Number of items per page

**Response:**
```json
{
  "values": [
    {
      "uuid": "{repo-uuid}",
      "name": "repo-name",
      "full_name": "workspace/repo-name",
      "is_private": true
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### List Repositories in Project

```
GET /workspaces/{workspace}/projects/{project}/repositories
```

**Response:**
Similar to List Repositories

### Get Repository

```
GET /repositories/{workspace}/{repo_slug}
```

**Response:**
```json
{
  "uuid": "{repo-uuid}",
  "name": "repo-name",
  "full_name": "workspace/repo-name",
  "language": "python",
  "is_private": true,
  "clone_urls": [
    {
      "name": "https",
      "href": "https://bitbucket.org/workspace/repo-name.git"
    },
    {
      "name": "ssh",
      "href": "git@bitbucket.org:workspace/repo-name.git"
    }
  ]
}
```

### Create Repository

```
POST /repositories/{workspace}/{repo_slug}
```

**Request Body:**
```json
{
  "name": "My Repository",
  "is_private": true,
  "project": {
    "key": "PROJECT"
  }
}
```

### Delete Repository

```
DELETE /repositories/{workspace}/{repo_slug}
```

## Branches

### List Branches

```
GET /repositories/{workspace}/{repo_slug}/refs/branches
```

**Response:**
```json
{
  "values": [
    {
      "name": "main",
      "target": {
        "hash": "abc123",
        "date": "2023-01-01T00:00:00Z",
        "author": {
          "raw": "User <user@example.com>"
        }
      }
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Create Branch

```
POST /repositories/{workspace}/{repo_slug}/refs/branches
```

**Request Body:**
```json
{
  "name": "new-branch",
  "target": {
    "hash": "abc123"
  }
}
```

## Pull Requests

### List Pull Requests

```
GET /repositories/{workspace}/{repo_slug}/pullrequests
```

**Parameters:**
- `state` (optional): Filter by state (e.g., `OPEN`, `MERGED`, `DECLINED`)
- `q` (optional): Query string for filtering
- `sort` (optional): Field to sort by

**Response:**
```json
{
  "values": [
    {
      "id": 1,
      "title": "Pull request title",
      "description": "Pull request description",
      "state": "OPEN",
      "author": {
        "display_name": "User Name",
        "uuid": "{user-uuid}"
      },
      "source": {
        "branch": {
          "name": "feature-branch"
        }
      },
      "destination": {
        "branch": {
          "name": "main"
        }
      }
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Get Pull Request

```
GET /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}
```

**Response:**
Similar to List Pull Requests, but for a single PR

### Create Pull Request

```
POST /repositories/{workspace}/{repo_slug}/pullrequests
```

**Request Body:**
```json
{
  "title": "Pull request title",
  "description": "Pull request description",
  "source": {
    "branch": {
      "name": "feature-branch"
    }
  },
  "destination": {
    "branch": {
      "name": "main"
    }
  },
  "reviewers": [
    {
      "uuid": "{user-uuid}"
    }
  ]
}
```

### Approve Pull Request

```
POST /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/approve
```

### Merge Pull Request

```
POST /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/merge
```

**Request Body:**
```json
{
  "close_source_branch": true,
  "merge_strategy": "merge_commit"
}
```

### Decline Pull Request

```
POST /repositories/{workspace}/{repo_slug}/pullrequests/{pull_request_id}/decline
```

## Users

### Get User

```
GET /users/{username}
```

**Response:**
```json
{
  "username": "username",
  "display_name": "User Name",
  "uuid": "{user-uuid}",
  "account_id": "account-id"
}
```

### Get Current User

```
GET /user
```

**Response:**
Similar to Get User, but for the authenticated user

## Teams/Groups

### List Team Members

```
GET /workspaces/{workspace}/members
```

**Response:**
```json
{
  "values": [
    {
      "user": {
        "display_name": "User Name",
        "username": "username",
        "uuid": "{user-uuid}"
      },
      "permission": "admin"
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

## Repository Permissions

### Get Repository Permissions

```
GET /repositories/{workspace}/{repo_slug}/permissions
```

**Response:**
```json
{
  "values": [
    {
      "user": {
        "display_name": "User Name",
        "username": "username",
        "uuid": "{user-uuid}"
      },
      "permission": "write"
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Update Repository Permissions

```
PUT /repositories/{workspace}/{repo_slug}/permissions/{username}
```

**Request Body:**
```json
{
  "permission": "write"
}
```

## Source/Files

### Get Repository Files

```
GET /repositories/{workspace}/{repo_slug}/src/{commit}/{path}
```

**Response:**
For directories:
```json
{
  "values": [
    {
      "path": "file.txt",
      "type": "commit_file",
      "size": 1234
    },
    {
      "path": "directory",
      "type": "commit_directory"
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

For files:
The raw file content

### Get File Content

```
GET /repositories/{workspace}/{repo_slug}/src/{commit}/{path}
```

**Response:**
The raw file content

## Commits

### List Commits

```
GET /repositories/{workspace}/{repo_slug}/commits
```

**Parameters:**
- `include` (optional): Branches to include
- `exclude` (optional): Branches to exclude

**Response:**
```json
{
  "values": [
    {
      "hash": "abc123",
      "date": "2023-01-01T00:00:00Z",
      "message": "Commit message",
      "author": {
        "raw": "User <user@example.com>"
      }
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Get Commit

```
GET /repositories/{workspace}/{repo_slug}/commit/{commit}
```

**Response:**
```json
{
  "hash": "abc123",
  "date": "2023-01-01T00:00:00Z",
  "message": "Commit message",
  "author": {
    "raw": "User <user@example.com>"
  },
  "parents": [
    {
      "hash": "def456"
    }
  ]
}
```

## Issues

### List Issues

```
GET /repositories/{workspace}/{repo_slug}/issues
```

**Parameters:**
- `q` (optional): Query string for filtering
- `sort` (optional): Field to sort by

**Response:**
```json
{
  "values": [
    {
      "id": 1,
      "title": "Issue title",
      "state": "new",
      "reporter": {
        "display_name": "User Name",
        "uuid": "{user-uuid}"
      },
      "assignee": {
        "display_name": "User Name",
        "uuid": "{user-uuid}"
      }
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Create Issue

```
POST /repositories/{workspace}/{repo_slug}/issues
```

**Request Body:**
```json
{
  "title": "Issue title",
  "content": {
    "raw": "Issue description"
  },
  "assignee": {
    "uuid": "{user-uuid}"
  }
}
```

## Pipelines

### List Pipelines

```
GET /repositories/{workspace}/{repo_slug}/pipelines/
```

**Response:**
```json
{
  "values": [
    {
      "uuid": "{pipeline-uuid}",
      "state": {
        "name": "COMPLETED",
        "result": {
          "name": "SUCCESSFUL"
        }
      },
      "created_on": "2023-01-01T00:00:00Z",
      "target": {
        "commit": {
          "hash": "abc123"
        },
        "ref_name": "main",
        "ref_type": "branch"
      }
    }
  ],
  "page": 1,
  "size": 10,
  "pagelen": 10
}
```

### Trigger Pipeline

```
POST /repositories/{workspace}/{repo_slug}/pipelines/
```

**Request Body:**
```json
{
  "target": {
    "ref_name": "main",
    "ref_type": "branch"
  }
}
```

## Error Handling

Most Bitbucket API errors return a standard JSON error response:

```json
{
  "type": "error",
  "error": {
    "message": "Error message"
  }
}
```

Common HTTP status codes:
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Pagination

Bitbucket API uses cursor-based pagination:

- `page`: Current page number
- `pagelen`: Number of items per page
- `next`: URL to the next page (if available)
- `previous`: URL to the previous page (if available)
- `size`: Total number of items

To navigate through pages, use the `page` parameter or follow the `next` URL in the response.