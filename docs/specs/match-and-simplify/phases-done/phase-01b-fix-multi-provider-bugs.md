# Phase 1B: Fix Multi-Provider Pattern Matching

## The Bug
Pattern `"PDI-Technologies/*/*"` only searches default provider, not all providers.

## Root Cause
Code checks if FIRST segment has wildcards. Should check if ANY part has wildcards.

## Fix These Exact Lines

### Fix 1: `/opt/aeo/mgit/mgit/__main__.py` Line 408
```python
# OLD LINE 408:
("*" in first_segment or "?" in first_segment)

# NEW LINE 408:
("*" in project or "?" in project)
```

### Fix 2: `/opt/aeo/mgit/mgit/commands/listing.py` Line 235
```python
# OLD LINE 235:
("*" in first_segment or "?" in first_segment)

# NEW LINE 235:
("*" in query or "?" in query)
```

### Fix 3: `/opt/aeo/mgit/mgit/__main__.py` Line 456
```python
# OLD LINE 456:
logger.debug(f"Provider '{pname}' listing failed: {e}")

# NEW LINE 456:
logger.error(f"Provider '{pname}' listing failed: {e}")
```

## Test Commands (Run These Exactly)

```bash
# Test 1: Should find PDI repos WITHOUT --provider flag
poetry run mgit list "PDI-Technologies/*/*" 2>&1 | head -20

# Test 2: Verify it finds repos (not "No organizations match")
poetry run mgit list "PDI-Technologies/*/*" 2>&1 | grep -c "PDI-Technologies"

# Test 3: Should find pdidev repos WITHOUT --provider flag  
poetry run mgit list "pdidev/*/*" 2>&1 | head -20
```

## Success = These All Pass
1. Test 1 shows PDI-Technologies repos (not "No organizations match")
2. Test 2 count is greater than 0
3. Test 3 shows pdidev repos

## DO NOT
- Add new files
- Refactor anything
- Create abstractions
- Write long explanations

Just fix the 3 lines, run the 3 tests, show the output.