# Bitbucket Cloud Authentication Methods

This document outlines the authentication methods available for Bitbucket Cloud API access, specifically for environments with SSO enabled through Atlassian.

## Authentication Options

### 1. Access Tokens

Access tokens provide repository, project, or workspace-scoped authentication for API access.

**Key features:**
- Repository, project, or workspace-scoped (not user-scoped)
- Do not require 2FA/2SV
- Ideal for CI/CD tools and scripts
- Limited permissions based on defined scopes
- Can be revoked at any time

**Usage in API calls:**
```python
from atlassian.bitbucket import Cloud

# Using access token
bitbucket = Cloud(
    username=None,  # Not required for access tokens
    password="YOUR_ACCESS_TOKEN",
    cloud=True)
```

### 2. App Passwords (Recommended for Bitbucket Cloud)

App passwords are tied to a user account but can have limited permissions.

**Key features:**
- User-scoped authentication
- Can define specific permissions
- Works alongside SSO
- Can be revoked independently of main account
- Atlassian's recommended approach for Bitbucket Cloud API access

**Usage in API calls:**
```python
from atlassian.bitbucket import Cloud

# Using app password
bitbucket = Cloud(
    username="your_username",  # Username, not email
    password="YOUR_APP_PASSWORD",
    cloud=True)
```

### 3. OAuth 2.0

OAuth 2.0 is ideal for third-party applications that need to access Bitbucket on behalf of users.

**Key features:**
- Standard OAuth 2.0 flows supported
- Access tokens expire after 2 hours
- Refresh tokens available
- Requires creating an OAuth consumer in Bitbucket

**OAuth flows supported:**
- Authorization Code Grant
- Implicit Grant 
- Client Credentials Grant
- Bitbucket's JWT Bearer token exchange

**Usage in API calls:**
```python
from atlassian.bitbucket import Cloud

# Using OAuth 2.0
oauth2_dict = {
    "client_id": "YOUR_CLIENT_ID",
    "token": {
        "access_token": "YOUR_ACCESS_TOKEN",
        "token_type": "bearer"
    }
}

bitbucket = Cloud(
    oauth2=oauth2_dict,
    cloud=True)
```

## SSO Considerations

When SSO is enabled through your organization's Atlassian account:

1. Traditional username/password authentication is no longer available for API access
2. You cannot use your SSO credentials directly with the API
3. App passwords or access tokens become the primary authentication method
4. OAuth can be used for more complex integration scenarios

## Creating Authentication Credentials

### Creating an App Password:
1. Log in to Bitbucket Cloud using SSO
2. Go to Personal Settings → App passwords
3. Create a new app password with appropriate permissions
4. Store the generated password securely (it will only be shown once)

### Creating an Access Token:
1. Log in to Bitbucket Cloud using SSO
2. Navigate to the repository, project, or workspace settings
3. Go to Access tokens
4. Create a new token with appropriate permissions
5. Store the generated token securely (it will only be shown once)

## Best Practices

1. Use app passwords for most API access scenarios
2. Apply the principle of least privilege - only grant permissions that are needed
3. Regularly rotate credentials
4. Never commit or share authentication tokens
5. Implement token revocation as part of your security procedures
6. Use environment variables or secure credential storage for tokens in applications
