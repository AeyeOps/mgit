---
description: Defines a strategy for isolating and deferring stubborn problems to maintain momentum.
author: Cline (Self-Generated)
version: 1.0
tags: ["workflow", "debugging", "problem-solving"]
globs: ["*"]
---

# Problem Isolation and Deferral Strategy

## Objective
To prevent getting stuck on a single, non-critical issue when working on a larger task. This strategy ensures that overall progress is maintained by isolating and deferring stubborn problems.

## Trigger
This workflow is triggered when I fail to fix a specific test, check, or component after **three** consecutive, distinct attempts.

## Workflow

1.  **Identify the Stubborn Problem:** Clearly identify the specific test, function, or component that is causing the failure.

2.  **Assess Criticality:**
    *   **Is this a critical, blocking issue?** (e.g., a core dependency failing to install, a fundamental authentication error).
        *   If YES, I must continue trying to solve it, potentially asking the user for help or more information if I've exhausted my options.
    *   **Is this a non-critical, isolatable issue?** (e.g., a single failing test in a large suite, a linting error in a non-essential file).
        *   If YES, proceed to the next step.

3.  **Propose Deferral:**
    *   Inform the user that I am struggling with the specific issue.
    *   Propose a temporary solution to isolate the problem and move forward with the main task. This could involve:
        *   Skipping the failing test (e.g., using `@pytest.mark.skip`).
        *   Commenting out the problematic code block.
        *   Adding the failing file to an ignore list.
    *   State that this is a **temporary measure** to unblock the primary task.

4.  **Document the Issue:**
    *   Create a `TODO` comment in the relevant file, clearly explaining the problem and why it was deferred.
    *   Example: `# TODO: Re-enable this test. It was skipped because of a persistent JSON parsing issue.`

5.  **Await User Confirmation:**
    *   Ask the user to confirm the proposed deferral strategy.
    *   Example: "I'm having trouble with this test. To keep making progress, I suggest we temporarily skip it and I'll add a TODO comment to revisit it later. Do you agree?"

6.  **Implement and Proceed:**
    *   If the user agrees, implement the deferral.
    *   Continue with the rest of the original task.

7.  **Final Report:**
    *   When using `attempt_completion`, mention the deferred issue as part of the summary of work done.
