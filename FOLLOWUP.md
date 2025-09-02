# mgit Follow-up Items

## Bugs
1. **BitBucket clone produces empty repos** - repos clone but have no commits
2. **clone-all/pull-all timeout** - no --limit flag causes timeout on large result sets  
3. **Azure DevOps path syntax** - list shows "org/project/repo" but clone expects different format

## Missing Features
1. **--limit flag for clone-all/pull-all** - prevent timeout issues
2. **Empty repo detection** - warn when cloned repo has no commits

## Security
1. **PATs visible in git remotes** - credentials exposed in plain text URLs

## Testing Gaps
1. **Multi-provider edge cases** - patterns like `github*/*/repo*` untested
2. **Provider-specific clone verification** - only GitHub fully verified working

## Documentation
1. **Provider path format differences** - document expected syntax per provider