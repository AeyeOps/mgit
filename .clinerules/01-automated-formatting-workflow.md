---
description: Defines an automated workflow for handling code formatting checks and fixes.
author: Cline (Self-Generated)
version: 1.0
tags: ["workflow", "formatting", "automation"]
globs: ["pyproject.toml", "package.json", "Makefile"]
---

# Automated Formatting Workflow

## Objective
To streamline the process of checking and applying code formatting by defining a clear, automated sequence of actions.

## Workflow

When a task involves running a formatting check (e.g., `lint`, `check-format`, `format-check`), I will follow this procedure:

1.  **Execute the Check Command:** I will first run the specified formatting check command (e.g., `poetry run poe format-check`, `npm run lint`).

2.  **Analyze the Outcome:**
    *   **If the check passes:** The task is complete. I will report the success.
    *   **If the check fails:** I will immediately proceed to the next step without asking for confirmation.

3.  **Execute the Fix Command:** I will identify and run the corresponding command that automatically fixes formatting issues (e.g., `poetry run poe format`, `npm run format:fix`).

4.  **Verify the Fix:** After the fix command has been executed, I will run the original check command one more time to ensure that all issues have been resolved.

5.  **Report Final Status:** I will report the final outcome of the verification step.

This workflow reduces the number of interactions required and ensures that formatting issues are resolved and verified in a single, efficient process.
