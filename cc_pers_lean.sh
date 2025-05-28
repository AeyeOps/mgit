#!/bin/bash

# claude_pers.sh
# This script runs Claude Code with personal config directory and default flags

export CLAUDE_CONFIG_DIR="$HOME/claude_code_pers"
exec claude --debug --continue --dangerously-skip-permissions "$@"
