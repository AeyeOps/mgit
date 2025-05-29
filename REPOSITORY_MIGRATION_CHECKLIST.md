# Repository Migration Checklist

## Current State Analysis

### Git Remote Configuration
- **Current Remote**: Still points to old repository
  ```
  origin: https://github.com/steveant/mgit.git
  ```
- **Target Remote**: Should be updated to
  ```
  origin: https://github.com/AeyeOps/mgit.git
  ```

### Files Containing Old Repository References

#### Direct GitHub Repository References (32 files)
1. **Documentation Files**:
   - README.md
   - INSTALLATION_GUIDE.md
   - INSTALLATION_FROM_GITHUB.md
   - WORKING_INSTALLATION_METHODS.md
   - PROJECT_CLOSURE.md
   - docs/deployment/deployment-guide.md

2. **Configuration Files**:
   - Dockerfile
   - setup.py
   - .pypirc
   - .git/config

3. **Scripts**:
   - scripts/deploy.sh
   - scripts/release-automation.sh
   - scripts/rollback.sh
   - scripts/verify-deployment.sh

4. **Helm Charts**:
   - deploy/helm/mgit/Chart.yaml
   - deploy/helm/mgit/values.yaml
   - deploy/README.md

5. **MAWEP Workspace**:
   - Various files in mawep-workspace/
   - Pod worktree files

#### Docker Registry References (21 files)
- All files reference: `ghcr.io/steveant/mgit`
- Should be updated to: `ghcr.io/AeyeOps/mgit`

### Other "Not Done" Indicators

#### 1. TODO/FIXME Comments in Code (19 files)
Found in:
- Security module files
- Provider implementations
- Test files
- Main entry point

#### 2. Uncommitted Changes
- Multiple modified files in git status
- Untracked documentation files

#### 3. Build Artifacts
- `/opt/aeo/mgit/build/` - Contains PyInstaller build artifacts
- `/opt/aeo/mgit/dist/` - Contains distribution packages

#### 4. Test Artifacts
- `.coverage` file
- `coverage.xml` file
- `htmlcov/` directory

#### 5. MAWEP Pod Worktrees
- pod-1 through pod-4 directories still exist
- Contains various sprint work artifacts

## Required Actions

### 1. Git Remote Update
```bash
# Update the remote URL
git remote set-url origin https://github.com/AeyeOps/mgit.git

# Verify the change
git remote -v
```

### 2. Docker Image Re-tagging
```bash
# Pull existing images
docker pull ghcr.io/steveant/mgit:latest
docker pull ghcr.io/steveant/mgit:0.2.1

# Re-tag for new registry
docker tag ghcr.io/steveant/mgit:latest ghcr.io/AeyeOps/mgit:latest
docker tag ghcr.io/steveant/mgit:0.2.1 ghcr.io/AeyeOps/mgit:0.2.1

# Push to new registry (requires authentication)
docker push ghcr.io/AeyeOps/mgit:latest
docker push ghcr.io/AeyeOps/mgit:0.2.1
```

### 3. Documentation Updates
Update all references from `steveant/mgit` to `AeyeOps/mgit` in:
- README.md
- Installation guides
- Deployment documentation
- Helm charts
- Scripts

### 4. GitHub Release Migration
- Check if releases exist on old repository
- Consider recreating releases on new repository
- Update release assets and links

### 5. Clean Up Build Artifacts
```bash
# Remove build artifacts
rm -rf build/
rm -rf htmlcov/
rm -f .coverage coverage.xml

# Clean MAWEP worktrees (after verifying no important work)
rm -rf mawep-workspace/worktrees/
```

## Prioritized Action Plan

### Priority 1 - Immediate Actions
1. **Update Git Remote** - Critical for future development
2. **Commit Current Changes** - Preserve work before migration
3. **Update Critical Documentation** - README.md, INSTALLATION_GUIDE.md

### Priority 2 - Near-term Actions
1. **Update All Documentation** - Find/replace repository references
2. **Re-tag Docker Images** - For deployment continuity
3. **Update Deployment Scripts** - Ensure they reference new repository

### Priority 3 - Cleanup Actions
1. **Remove Build Artifacts** - Clean development environment
2. **Archive MAWEP Worktrees** - After extracting any valuable content
3. **Address TODO/FIXME Comments** - Code quality improvement

### Priority 4 - Long-term Actions
1. **Migrate GitHub Releases** - If needed for historical reference
2. **Update PyPI References** - If package is published
3. **Update Any External Documentation** - Wiki, blog posts, etc.

## Verification Steps

After migration:
1. Verify git operations work with new remote
2. Test Docker image pull from new registry
3. Validate all installation methods with new URLs
4. Ensure CI/CD pipelines (if any) use new repository
5. Check that documentation accurately reflects new location

## Notes

- The repository appears to have significant uncommitted work
- Multiple sprint artifacts exist that may need preservation
- Security and monitoring modules contain TODOs that may need attention
- The project seems to be in a post-release state with cleanup needed