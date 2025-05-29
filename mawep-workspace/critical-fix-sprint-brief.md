# Critical Fix Sprint Brief

## Current State Analysis

### Issue #1201: Circular Import (CRITICAL)
- **Location**: AzDevOpsManager class in __main__.py (lines 270-338)
- **Problem**: providers/manager.py imports AzDevOpsManager from __main__.py (lines 19-20, 122)
- **Solution**: Extract AzDevOpsManager to mgit/legacy/azdevops_manager.py

### Issue #1202: Missing Dependencies (HIGH)
- **Current**: requirements.txt missing aiohttp
- **Problem**: Providers will fail at runtime without aiohttp
- **Solution**: Add aiohttp to requirements.txt

### Issue #1203: Dead Code (MEDIUM)
- **Auth module**: 891 lines of unused code in mgit/auth/
- **Empty modules**: cli/, commands/, mawep/ contain only __init__.py
- **Backup file**: __main__.py.backup exists unnecessarily
- **Solution**: Delete all these files/directories

### Issue #1204: Testing Verification (HIGH)
- **Dependency**: Must wait for issues #1201-1203 to complete
- **Goal**: Verify pytest can run without circular import errors
- **Success**: At least one test should pass

## Execution Plan

### Phase 1: Parallel Fixes (Pod 1-3)
1. **Pod-1**: Extract AzDevOpsManager to legacy module
2. **Pod-2**: Add aiohttp dependency
3. **Pod-3**: Remove dead code and empty directories

### Phase 2: Verification (Pod 4)
4. **Pod-4**: Run pytest and verify fixes work

## Expected Outcomes
- No circular import errors
- All dependencies installable
- 891 lines of dead code removed
- Clean, testable codebase ready for CI/CD