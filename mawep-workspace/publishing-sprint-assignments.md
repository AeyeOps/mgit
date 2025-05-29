# Publishing Sprint Assignments

## Sprint Overview
**Objective**: Make mgit publicly available for the first time
**Duration**: 25 minutes
**Status**: ACTIVE
**Critical Gap**: mgit is enterprise-ready but NOT publicly accessible

## Pod Assignments

### Pod 1: GitHub Release Pod (#1601)
**Priority**: CRITICAL (Blocking)
**Assignment**: Create GitHub release v0.2.1 with artifacts

#### Tasks:
1. Build distribution artifacts:
   - Python wheel: `python -m build --wheel`
   - Source distribution: `python -m build --sdist`
   - Binary executable: `pyinstaller --onefile mgit/__main__.py`

2. Create GitHub release:
   - Tag: v0.2.1
   - Title: "mgit v0.2.1 - Enterprise-Ready Multi-Provider Git Management"
   - Include RELEASE_NOTES_v0.2.1.md content
   - Upload all artifacts (wheel, tar.gz, binary)
   - Link to MIGRATION_GUIDE_v0.2.1.md

3. Verify release:
   - Check tag is created
   - Verify artifacts are downloadable
   - Ensure release notes are formatted correctly

#### Deliverables:
- [ ] GitHub release v0.2.1 published
- [ ] All artifacts uploaded and accessible
- [ ] Release properly tagged
- [ ] Migration guide linked

---

### Pod 2: PyPI Publishing Pod (#1602)
**Priority**: CRITICAL (Blocking)
**Assignment**: Publish mgit to PyPI
**Dependencies**: #1601 (GitHub release)

#### Tasks:
1. Prepare package:
   - Verify pyproject.toml metadata
   - Ensure version is 0.2.1
   - Check package description and classifiers
   - Build distribution: `python -m build`

2. Test with TestPyPI:
   - Upload to TestPyPI: `twine upload --repository testpypi dist/*`
   - Test installation: `pip install -i https://test.pypi.org/simple/ mgit`
   - Verify functionality

3. Publish to PyPI:
   - Upload to PyPI: `twine upload dist/*`
   - Verify: `pip install mgit`
   - Test installed command: `mgit --version`

#### Deliverables:
- [ ] TestPyPI validation complete
- [ ] PyPI package published
- [ ] pip install mgit works
- [ ] Package metadata correct

---

### Pod 3: Docker Registry Pod (#1603)
**Priority**: HIGH
**Assignment**: Push Docker images to registries
**Dependencies**: #1601 (GitHub release)

#### Tasks:
1. Build Docker images:
   - Tag with version: `docker build -t mgit:v0.2.1 .`
   - Tag as latest: `docker tag mgit:v0.2.1 mgit:latest`
   - Create multi-arch builds if possible

2. Push to GitHub Container Registry:
   - Login: `docker login ghcr.io`
   - Tag: `docker tag mgit:v0.2.1 ghcr.io/steveant/mgit:v0.2.1`
   - Push: `docker push ghcr.io/steveant/mgit:v0.2.1`
   - Push latest: `docker push ghcr.io/steveant/mgit:latest`

3. Optional - Push to Docker Hub:
   - Tag: `docker tag mgit:v0.2.1 steveant/mgit:v0.2.1`
   - Push if credentials available

4. Verify pulls:
   - Test: `docker pull ghcr.io/steveant/mgit:v0.2.1`
   - Run: `docker run --rm ghcr.io/steveant/mgit:v0.2.1 --version`

#### Deliverables:
- [ ] Docker images built and tagged
- [ ] Images pushed to GitHub Container Registry
- [ ] docker pull verification successful
- [ ] Container runs correctly

---

### Pod 4: Documentation Update Pod (#1604)
**Priority**: HIGH
**Assignment**: Update installation documentation
**Dependencies**: #1601, #1602, #1603 (All publishing tasks)

#### Tasks:
1. Update README.md:
   - Add installation section with all methods
   - Add badges (PyPI version, Docker pulls, GitHub release)
   - Update quick start examples
   - Add links to detailed guides

2. Create/Update INSTALLATION_GUIDE.md:
   - PyPI installation: `pip install mgit`
   - Docker installation: `docker pull ghcr.io/steveant/mgit:latest`
   - Binary download from GitHub releases
   - Development installation from source

3. Create quick start guide:
   - Basic usage examples
   - Common workflows
   - Provider setup guides
   - Link to full documentation

4. Update badges:
   ```markdown
   [![PyPI version](https://badge.fury.io/py/mgit.svg)](https://pypi.org/project/mgit/)
   [![Docker Image](https://img.shields.io/docker/v/steveant/mgit)](https://ghcr.io/steveant/mgit)
   [![GitHub release](https://img.shields.io/github/release/steveant/mgit.svg)](https://github.com/steveant/mgit/releases)
   ```

#### Deliverables:
- [ ] README updated with installation instructions
- [ ] Badges added and working
- [ ] INSTALLATION_GUIDE.md complete
- [ ] Quick start guide created

---

## Sprint Coordination

### Execution Order:
1. **Pod 1** creates GitHub release (BLOCKING)
2. **Pod 2** publishes to PyPI (depends on Pod 1)
3. **Pod 3** pushes Docker images (can start after Pod 1)
4. **Pod 4** updates documentation (after all publishing complete)

### Success Metrics:
- GitHub release v0.2.1 available
- `pip install mgit` works globally
- `docker pull ghcr.io/steveant/mgit:latest` works
- Users have clear installation instructions

### Time Allocation:
- Pod 1: 10 minutes (GitHub release)
- Pod 2: 10 minutes (PyPI publishing)
- Pod 3: 10 minutes (Docker registry)
- Pod 4: 5 minutes (Documentation)
- Buffer: 5 minutes

## Critical Reminders

1. **This is the FIRST public release** - Be extra careful with:
   - Version numbers (must be 0.2.1)
   - Package metadata accuracy
   - Documentation clarity

2. **Test everything** before final publication:
   - TestPyPI before PyPI
   - Verify Docker pulls work
   - Check all download links

3. **Update state file** as tasks complete

## Publishing Checklist

Pre-flight:
- [ ] Version number is 0.2.1 everywhere
- [ ] CHANGELOG.md is up to date
- [ ] Release notes are prepared
- [ ] All tests pass

Publishing:
- [ ] GitHub release created
- [ ] PyPI package published
- [ ] Docker images pushed
- [ ] Documentation updated

Verification:
- [ ] pip install mgit works
- [ ] docker pull works
- [ ] GitHub artifacts downloadable
- [ ] All badges showing correct info

## LAUNCH SEQUENCE

```bash
# Pod 1: Create GitHub Release
git tag v0.2.1
git push origin v0.2.1
# Use GitHub UI or gh CLI to create release

# Pod 2: Publish to PyPI
python -m build
twine upload --repository testpypi dist/*
twine upload dist/*

# Pod 3: Push Docker Images
docker build -t mgit:v0.2.1 .
docker push ghcr.io/steveant/mgit:v0.2.1

# Pod 4: Update Documentation
# Update README.md with installation instructions
```

**CRITICAL**: Without this sprint, all the enterprise work is meaningless. Users need access to mgit!