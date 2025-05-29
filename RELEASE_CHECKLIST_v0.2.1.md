# Release Checklist for mgit v0.2.1

## Pre-Release Verification
- [x] Version updated in `mgit/constants.py` to "0.2.1"
- [x] Version updated in `pyproject.toml` to "0.2.1"
- [x] CHANGELOG.md updated with v0.2.1 section
- [x] Release notes created (RELEASE_NOTES_v0.2.1.md)
- [x] Migration guide created (MIGRATION_GUIDE_v0.2.1.md)
- [x] Release summary created (RELEASE_v0.2.1_SUMMARY.md)

## Documentation Updates
- [x] README.md reflects multi-provider capabilities
- [x] Provider comparison table included
- [x] Installation instructions current
- [x] Quick start examples for all providers
- [x] Architecture documentation complete
- [x] Configuration documentation updated

## Testing Confirmation
- [x] Azure DevOps provider tested
- [x] GitHub provider tested
- [x] BitBucket provider implemented
- [x] Cross-provider sessions validated
- [x] Backward compatibility verified
- [x] CLI help text updated

## Breaking Changes Documentation
- [x] Environment variable changes documented
- [x] Configuration file format changes explained
- [x] Command syntax updates clarified
- [x] Migration path clearly defined

## Release Artifacts
- [x] CHANGELOG.md - Complete changelog
- [x] RELEASE_NOTES_v0.2.1.md - User-facing announcement
- [x] MIGRATION_GUIDE_v0.2.1.md - Upgrade instructions
- [x] RELEASE_v0.2.1_SUMMARY.md - Executive summary
- [x] RELEASE_CHECKLIST_v0.2.1.md - This checklist

## Final Steps (To be done by maintainer)
- [ ] Create git tag: `git tag -a v0.2.1 -m "Release v0.2.1: Multi-Provider Support"`
- [ ] Push tag: `git push origin v0.2.1`
- [ ] Create GitHub release using RELEASE_NOTES_v0.2.1.md
- [ ] Build and upload PyPI package: `python -m build && twine upload dist/*`
- [ ] Update project website/documentation
- [ ] Announce on relevant channels

## Post-Release
- [ ] Monitor issue tracker for migration problems
- [ ] Prepare hotfix branch if needed
- [ ] Plan v0.3.0 features based on feedback

---
**Release prepared by**: Pod-2 Agent
**Date**: January 29, 2025
**Status**: READY FOR RELEASE ✅