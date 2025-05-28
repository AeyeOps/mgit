# Claude Code Settings Reference

This document explains various Claude Code settings found in configuration files.

## Core Settings

### parallelAgents
```json
"parallelAgents": {
  "enabled": true,
  "count": 20
}
```
- **Purpose**: Enables running multiple AI agents in parallel when using the Task tool
- **enabled**: Boolean flag to turn the feature on/off
- **count**: Number of agents to spawn for each Task invocation (1-20+)
- **Impact**: Each Task tool invocation creates this many parallel executions
- **MAWEP Consideration**: Should be set to 1 for orchestration patterns to avoid conflicts

### Usage Tracking

#### numStartups
- **Type**: Integer
- **Purpose**: Tracks how many times Claude Code has been launched
- **Usage**: Used for progressive tip display and onboarding flow

#### promptQueueUseCount
- **Type**: Integer  
- **Purpose**: Counts usage of the prompt queue feature
- **Note**: Prompt queue allows stacking multiple requests for sequential processing

#### memoryUsageCount
- **Type**: Integer
- **Purpose**: Tracks usage of Claude's memory/context features
- **Related**: Likely connected to Memory Bank system usage

### Tips and Onboarding

#### tipsHistory
```json
"tipsHistory": {
  "ide-hotkey": 17,
  "new-user-warmup": 2,
  "memory-command": 3,
  "theme-command": 4,
  "shift-enter": 5,
  "prompt-queue": 9,
  "enter-to-steer-in-relatime": 10,
  "todo-list": 12
}
```
- **Purpose**: Tracks which tips have been shown and when
- **Format**: "tip-name": startup_count_when_shown
- **Usage**: Prevents showing the same tips repeatedly

#### Onboarding Status
- **hasCompletedOnboarding**: Boolean indicating if initial setup is complete
- **lastOnboardingVersion**: Version string of last completed onboarding
- **firstStartTime**: ISO timestamp of first Claude Code launch

### User Configuration

#### claudeMaxTier
- **Type**: String (e.g., "20x")
- **Purpose**: Indicates subscription tier and usage limits
- **Impact**: Affects rate limits, concurrent requests, and available features

#### userID
- **Type**: String (hash)
- **Purpose**: Anonymous identifier for telemetry and feature tracking
- **Privacy**: Hashed/anonymized, not personally identifiable

#### shiftEnterKeyBindingInstalled
- **Type**: Boolean
- **Purpose**: Indicates if Shift+Enter keybinding is active
- **Function**: Enables multi-line input in chat interface

## Settings Hierarchy

According to Claude Code documentation, settings follow this precedence order:
1. Enterprise managed policy settings (highest priority)
2. Command line arguments
3. Local project settings (`.claude/settings.json`)
4. Shared project settings
5. User settings (`~/.claude/settings.json`) (lowest priority)

## Configuration Commands

- `claude config list` - Show all current settings
- `claude config get <key>` - Get specific setting value
- `claude config set <key> <value>` - Update a setting

## Important Environment Variables

- `ANTHROPIC_MODEL` - Override default model selection
- `BASH_DEFAULT_TIMEOUT_MS` - Set timeout for bash commands
- `CLAUDE_DISABLE_AUTO_UPDATE` - Disable automatic updates
- `CLAUDE_DISABLE_TELEMETRY` - Disable telemetry collection

## Best Practices

1. **For MAWEP/Orchestration**: Set `parallelAgents.count` to 1 to avoid conflicts
2. **For Independent Tasks**: Higher `parallelAgents.count` can speed up processing
3. **Project-Specific Settings**: Use `.claude/settings.json` in project root
4. **Global Defaults**: Configure in `~/.claude/settings.json`

## Sources

- Analysis of user configuration JSON
- Claude Code documentation: https://docs.anthropic.com/en/docs/claude-code/settings
- Empirical observation of parallelAgents behavior in MAWEP orchestration

---

*Last updated: 2025-05-28*