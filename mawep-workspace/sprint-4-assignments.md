# Sprint 4 Assignments: Provider Implementations

## Overview
Sprint 4 implements the concrete provider classes that were abstracted in Sprint 3A.

## Execution Strategy
- **Phase 1**: Pods 1-3 work in parallel (Azure DevOps, Registry, Config)
- **Phase 2**: Pods 4-5 work in parallel AFTER Registry completes (GitHub, BitBucket stubs)

## Pod Assignments

### Pod 1: Azure DevOps Provider Implementation
**Issue**: #10 - Implement Azure DevOps Provider
**Priority**: HIGH
**Dependencies**: Provider Interface (#7 - COMPLETED)
**Files to Create/Modify**:
- `mgit/providers/azdevops.py` - Full Azure DevOps implementation
- Import and register in `__main__.py`

**Requirements**:
- Implement all GitProvider abstract methods
- Use existing AzDevOpsManager for API calls
- Support PAT authentication
- Handle project/repo listing and filtering

### Pod 2: Provider Registry Implementation  
**Issue**: #9 - Implement Provider Registry [CRITICAL PATH]
**Priority**: CRITICAL
**Dependencies**: Provider Interface (#7 - COMPLETED)
**Files to Create/Modify**:
- `mgit/providers/registry.py` - Provider registration and lookup
- Update `mgit/providers/__init__.py` with registry exports
- Import in `__main__.py`

**Requirements**:
- Singleton registry pattern
- Auto-discovery of providers
- Provider lookup by URL patterns
- Validation of provider implementations

### Pod 3: Provider Configuration
**Issue**: #13 - Provider-specific Configuration
**Priority**: MEDIUM
**Dependencies**: Provider Interface (#7 - COMPLETED), Config Manager (#2 - COMPLETED)
**Files to Create/Modify**:
- `mgit/config/providers.py` - Provider config handling
- Update existing config manager if needed

**Requirements**:
- Per-provider config sections
- Default values per provider type
- Config validation
- Integration with existing config system

### Pod 4: GitHub Provider Stub [PHASE 2]
**Issue**: #11 - Implement GitHub Provider (Stub)
**Priority**: MEDIUM
**Dependencies**: Provider Registry (#9 - MUST COMPLETE FIRST)
**Files to Create/Modify**:
- `mgit/providers/github.py` - GitHub stub implementation
- Register with provider registry

**Requirements**:
- Implement GitProvider interface
- Stub methods with NotImplementedError
- Basic URL pattern matching for github.com
- Placeholder for future OAuth support

### Pod 5: BitBucket Provider Stub [PHASE 2]
**Issue**: #12 - Implement BitBucket Provider (Stub)
**Priority**: MEDIUM  
**Dependencies**: Provider Registry (#9 - MUST COMPLETE FIRST)
**Files to Create/Modify**:
- `mgit/providers/bitbucket.py` - BitBucket stub implementation
- Register with provider registry

**Requirements**:
- Implement GitProvider interface
- Stub methods with NotImplementedError
- Basic URL pattern matching for bitbucket.org
- Placeholder for future app password support

## Integration Protocol
1. Each pod works independently in their worktree
2. No cross-pod file access during development
3. Phase 2 pods wait for Phase 1 completion
4. Final integration updates `__main__.py` with all imports
5. Test provider system functionality

## Success Criteria
- All provider classes properly implement GitProvider ABC
- Registry can discover and instantiate providers
- Azure DevOps provider fully functional
- GitHub/BitBucket stubs ready for future implementation
- Provider config system integrated
- `python -m mgit --version` runs without errors