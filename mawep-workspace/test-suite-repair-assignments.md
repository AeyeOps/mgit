# Test Suite Repair Sprint - Pod Assignments

## Sprint Overview
**Objective**: Restore mgit test infrastructure to working state
**Duration**: 25 minutes  
**Start**: 2025-01-29  
**Critical Issue**: Import error preventing all tests from running

## Current Test Status
- ❌ **59 tests collected, 1 import error**
- ❌ **22% overall coverage** 
- ❌ **Import error**: `mgit.utils.helpers` doesn't exist
- ❌ **Functions actually in**: `mgit.git.utils`

## Pod Assignments

### 🔴 Pod-1: Test-Import-Repair-Pod (CRITICAL - Start First)
**Issue**: #1301 - Fix incorrect test imports  
**Priority**: CRITICAL (Blocking all other pods)  
**Status**: PENDING  

**Tasks**:
1. Fix import error in `tests/unit/test_utils.py`
   - Change: `from mgit.utils.helpers import embed_pat_in_url, sanitize_repo_name`
   - To: `from mgit.git.utils import embed_pat_in_url, sanitize_repo_name`
2. Audit all test files for similar import errors
3. Verify test collection succeeds without import errors
4. Test basic function imports work correctly

**Files to Fix**:
- `tests/unit/test_utils.py` (primary)
- `tests/unit/test_git.py` (audit)
- `tests/unit/test_providers.py` (audit)

**Success Criteria**:
- `pytest --collect-only` runs without import errors
- All 59 tests can be collected successfully

---

### 🟡 Pod-2: Test-Audit-Pod (Depends on Pod-1)
**Issue**: #1302 - Comprehensive test audit  
**Priority**: HIGH  
**Status**: PENDING  

**Tasks**:
1. Run each test file individually to identify failures
2. Fix broken test logic and assertions  
3. Update test fixtures and mocks as needed
4. Ensure integration tests can run (may require mocking)

**Focus Files**:
- `tests/integration/test_commands.py` (13 tests)
- `tests/conftest.py` (fixtures)
- Any failing unit tests after Pod-1 completion

**Success Criteria**:
- Individual test files run without critical failures
- Test fixtures work correctly
- Basic test execution succeeds

---

### 🟢 Pod-3: Coverage-Analysis-Pod
**Issue**: #1303 - Test coverage analysis  
**Priority**: MEDIUM  
**Status**: PENDING  

**Tasks**:
1. Identify modules with <30% coverage (18 modules currently)
2. Prioritize critical modules for test additions:
   - `mgit/utils/progress.py` (0% coverage)
   - `mgit/providers/github.py` (13% coverage)  
   - `mgit/providers/bitbucket.py` (16% coverage)
   - `mgit/__main__.py` (17% coverage)
3. Add essential tests for core functionality
4. Focus on critical paths and error handling

**Success Criteria**:
- Core modules reach >30% coverage
- Critical functionality has basic test coverage
- Coverage reporting works correctly

---

### 🔵 Pod-4: CI-CD-Validation-Pod (Depends on Pod-1, Pod-2)
**Issue**: #1304 - CI/CD readiness validation  
**Priority**: HIGH  
**Status**: PENDING  

**Tasks**:
1. Verify pytest runs cleanly with proper exit codes
2. Confirm coverage reports generate correctly
3. Test quality gate functionality
4. Document test execution procedures
5. Verify CI/CD pipeline can run tests

**Success Criteria**:
- `pytest` exits with code 0 for passing tests
- Coverage reports generate (HTML, XML)
- Quality gates can evaluate test results
- CI/CD pipeline documentation updated

## Sprint Coordination

### Dependency Chain
1. **Pod-1 MUST complete first** (blocks all others)
2. **Pod-2 and Pod-4 depend on Pod-1**
3. **Pod-3 can work in parallel after Pod-1**

### Communication Protocol
- Pod-1 reports completion immediately to unblock others
- All pods report status every 5 minutes
- Critical issues escalated to orchestrator immediately

### Success Metrics
- [ ] Test collection: 0 import errors
- [ ] Test execution: Runs without critical failures  
- [ ] Coverage: Core modules >30%
- [ ] CI/CD: Quality gates functional

## Business Impact
**Current Risk**: HIGH - No working test infrastructure  
**Quality Assurance**: BLOCKED - Cannot verify code changes  
**CI/CD Pipeline**: BROKEN - Quality gates non-functional  

**Sprint Success** = Restore mgit test infrastructure to production-ready state