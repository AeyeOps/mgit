# How to Securely Add OpenAI API Key to GitHub

## Option 1: GitHub CLI (Recommended)

```bash
# First, create a new API key at https://platform.openai.com/api-keys
# Then run:
gh secret set OPENAI_API_KEY --repo AeyeOps/mgit

# It will prompt you to enter the value securely (not visible)
# Paste your NEW API key when prompted
```

## Option 2: GitHub Web UI

1. Go to https://github.com/AeyeOps/mgit/settings/secrets/actions
2. Click "New repository secret"
3. Name: `OPENAI_API_KEY`
4. Value: Your NEW OpenAI API key
5. Click "Add secret"

## Option 3: Using Environment Variable

```bash
# Store key in environment variable first (more secure)
read -s OPENAI_KEY  # Type/paste key, won't be visible
echo "$OPENAI_KEY" | gh secret set OPENAI_API_KEY --repo AeyeOps/mgit
```

## Security Best Practices

1. **Never commit API keys** to your repository
2. **Use GitHub Secrets** for all sensitive data
3. **Rotate keys regularly** especially if exposed
4. **Limit key permissions** if possible
5. **Monitor usage** on OpenAI dashboard

## Verify Secret Was Added

```bash
# List secrets (names only, not values)
gh secret list --repo AeyeOps/mgit
```

You should see:
```
NAME            UPDATED
OPENAI_API_KEY  less than a minute ago
```