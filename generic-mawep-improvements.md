# Generic MAWEP Framework Improvements

## 6-Stage MAWEP Sprint Process

### Stage 1: Pre-Sprint Analysis 🔍
**REQUIRED OUTPUTS:**
- [ ] Dependency map showing which issues depend on others
- [ ] Foundation requirements analysis (what must be built first)
- [ ] File/code conflict assessment between parallel work
- [ ] Pod capability matching (assign issues to appropriate pods)
- [ ] Reality check: Is MAWEP actually needed vs sequential work?

**ORCHESTRATOR VERIFICATION:**
Document your analysis - don't just think it. Create written dependency maps and conflict assessments.

### Stage 2: Sprint Design & Orchestration 📋
**REQUIRED OUTPUTS:**
- [ ] Pod assignments documented
- [ ] Execution sequence defined (dependency order)
- [ ] Shared interfaces/constants planned
- [ ] Integration strategy documented
- [ ] Communication protocol established

**ORCHESTRATOR VERIFICATION:**
- Create sprint assignments file
- Document execution order with rationale
- Plan integration approach BEFORE starting

### Stage 3: Parallel Execution ⚡
**CRITICAL REALITIES:**
- **Agents are ephemeral** - Task tool = single message exchange only
- **No background processing** - Must continuously invoke agents
- **Active orchestration required** - You manage ALL coordination

**⚠️ NEVER assume agents continue working between invocations**

### Stage 4: Integration & Convergence 🔗
**🚨 MOST CRITICAL STAGE - Where Most Failures Occur**

**INTEGRATION REALITY:**
- **Pods work in ISOLATION** - Each pod's work exists only in their worktree
- **Integration is MANUAL** - Changes don't automatically merge
- **Dependency order matters** - Must integrate in correct sequence

**INTEGRATION CHECKLIST:**
- [ ] All pod changes copied to integration workspace
- [ ] Import statements added for new modules
- [ ] Extracted code removed from original files
- [ ] No circular imports created
- [ ] All dependencies resolve correctly

### Stage 5: Validation & Quality Assurance ✅
**🚨 CRITICAL: Never Trust Agent Reports Without Independent Verification**

**VERIFICATION PROTOCOL:**
- Test basic functionality of the integrated system
- Test core operations work without import errors
- Check measurable improvements (lines reduced, modules created, etc.)
- Verify all modules can be imported correctly

**NEVER proceed to next sprint without completing this stage**

### Stage 6: Sprint Closure & Documentation 📝
**REQUIRED DELIVERABLES:**
- [ ] Architecture documentation updated
- [ ] Sprint metrics documented (measurable improvements)
- [ ] Lessons learned captured
- [ ] Next sprint foundation prepared

## Common MAWEP Orchestrator Mistakes 🚫

### ❌ **Mistake #1: Trusting Agent Reports**
**Problem:** Agents report "completed" but work isn't actually integrated
**Solution:** Always verify independently with tests/commands

### ❌ **Mistake #2: Skipping Integration Stage**
**Problem:** Assuming pod work automatically merges
**Solution:** Explicit integration protocol with verification steps

### ❌ **Mistake #3: Rushing to Next Sprint**
**Problem:** Moving forward with incomplete foundation
**Solution:** Complete all 6 stages before proceeding

### ❌ **Mistake #4: Poor Dependency Analysis**
**Problem:** Starting dependent work before foundation is ready
**Solution:** Map dependencies clearly and enforce execution order

### ❌ **Mistake #5: Insufficient Verification**
**Problem:** Integration breaks but not caught until later
**Solution:** Test at each stage, not just at the end

## MAWEP Success Indicators ✅
- [ ] All 6 stages completed with documented verification
- [ ] Independent testing confirms functionality preserved
- [ ] Architecture improvements measurable
- [ ] Foundation ready for next sprint
- [ ] Team understands what was accomplished

## Emergency Recovery Protocol 🚨
**If you discover a sprint is incomplete:**
1. **STOP** - Don't proceed to next sprint
2. **ASSESS** - Identify which stages were skipped
3. **RECOVERY** - Go back and complete missing stages
4. **VERIFY** - Test that recovery was successful
5. **DOCUMENT** - Update process to prevent recurrence

## Key Insight: Integration is Manual
The most critical learning is that **pod work exists in isolation** and must be **manually integrated**. This is not automatic and requires explicit orchestration following dependency order.

---

**Note:** These improvements should be integrated into the global MAWEP framework documentation to prevent the 90% of MAWEP failures that occur due to incomplete stage execution.