# Repository Migration Sprint Assignments

## Sprint Overview
- **Objective**: Migrate mgit repository from github.com/steveant/mgit to github.com/AeyeOps/mgit
- **Duration**: 20 minutes
- **Start Time**: 2025-05-29T10:00:00
- **Critical Path**: Pod-1 → Verification → Push

## Pod Assignments

### Pod-1: Git Configuration Pod
**Priority**: CRITICAL - Must complete first
**Issue**: GIT-001

#### Tasks:
1. **Update Git Remote** (2 min)
   ```bash
   cd /opt/aeo/mgit
   git remote set-url origin https://github.com/AeyeOps/mgit.git
   ```

2. **Verify Configuration** (1 min)
   ```bash
   git remote -v
   # Should show:
   # origin  https://github.com/AeyeOps/mgit.git (fetch)
   # origin  https://github.com/AeyeOps/mgit.git (push)
   ```

3. **Test Connection** (2 min)
   ```bash
   git fetch origin
   # Verify no errors
   ```

4. **Update .git/config if needed** (1 min)
   - Check if any branch tracking needs updating
   - Ensure all references point to new repository

#### Verification:
- [ ] Remote URL updated
- [ ] Fetch operation successful
- [ ] No references to old repository in .git/config

---

### Pod-2: Documentation Update Pod
**Priority**: HIGH - Most work volume
**Issues**: DOC-001, DOC-002

#### Issue DOC-001: Primary Documentation
1. **Update README.md** (3 min)
   - Replace all `steveant/mgit` with `AeyeOps/mgit`
   - Update clone URLs
   - Update badges if any

2. **Update INSTALLATION_GUIDE.md** (2 min)
   - Update all repository URLs
   - Update Docker image references
   - Verify installation commands

3. **Update PROJECT_CLOSURE.md** (2 min)
   - Update repository references
   - Ensure migration is documented

4. **Update docs/deployment/deployment-guide.md** (2 min)
   - Update deployment URLs
   - Update Docker registry references

#### Issue DOC-002: Scripts and Configs
1. **Update Shell Scripts** (4 min)
   - scripts/deploy.sh
   - scripts/release-automation.sh
   - scripts/rollback.sh
   - scripts/verify-deployment.sh
   
2. **Update Configuration Files** (3 min)
   - Dockerfile
   - setup.py
   - deploy/helm/mgit/Chart.yaml
   - deploy/helm/mgit/values.yaml

#### Verification:
- [ ] No remaining references to steveant/mgit
- [ ] All URLs point to AeyeOps/mgit
- [ ] Docker images reference new registry

---

### Pod-3: Docker Registry Pod
**Priority**: MEDIUM - Post-migration support
**Issue**: DOCKER-001

#### Tasks:
1. **Document Re-tagging Process** (3 min)
   Create a DOCKER_MIGRATION.md with:
   ```bash
   # Pull existing images
   docker pull ghcr.io/steveant/mgit:latest
   docker pull ghcr.io/steveant/mgit:0.2.1
   
   # Re-tag for new registry
   docker tag ghcr.io/steveant/mgit:latest ghcr.io/AeyeOps/mgit:latest
   docker tag ghcr.io/steveant/mgit:0.2.1 ghcr.io/AeyeOps/mgit:0.2.1
   
   # Push to new registry (requires auth)
   docker push ghcr.io/AeyeOps/mgit:latest
   docker push ghcr.io/AeyeOps/mgit:0.2.1
   ```

2. **Update Docker References** (5 min)
   - Find all files with `ghcr.io/steveant/mgit`
   - Replace with `ghcr.io/AeyeOps/mgit`
   - Focus on:
     - Dockerfile
     - docker-compose files
     - Kubernetes manifests
     - Helm charts

3. **Create Migration Guide** (2 min)
   - Document steps for users to update their local images
   - Include rollback instructions if needed

#### Verification:
- [ ] All Docker references updated
- [ ] Migration guide created
- [ ] No remaining references to old registry

## Coordination Points

### Critical Dependencies:
1. Pod-1 MUST complete before final push
2. Pod-2 can work independently but has most files
3. Pod-3 can work in parallel with Pod-2

### Verification Checklist:
1. **After Pod-1**:
   - [ ] Git remote verified
   - [ ] Fetch/pull works

2. **After Pod-2**:
   - [ ] grep -r "steveant/mgit" returns no results
   - [ ] All documentation accurate

3. **After Pod-3**:
   - [ ] Docker migration documented
   - [ ] Registry references updated

### Final Steps (Orchestrator):
1. Review all pod work
2. Run comprehensive verification:
   ```bash
   # Check for any remaining old references
   grep -r "steveant/mgit" --exclude-dir=.git --exclude-dir=mawep-workspace
   grep -r "ghcr.io/steveant" --exclude-dir=.git
   ```
3. Commit all changes
4. Push to new repository

## Success Criteria
- [ ] Git remote points to AeyeOps/mgit
- [ ] All 32 documentation files updated
- [ ] Docker migration guide created
- [ ] No references to old repository remain
- [ ] Successfully pushed to new repository

## Time Allocation
- Pod-1: 6 minutes
- Pod-2: 16 minutes (largest workload)
- Pod-3: 10 minutes
- Verification: 4 minutes
- Buffer: 4 minutes
- **Total**: 20 minutes (with parallel execution)