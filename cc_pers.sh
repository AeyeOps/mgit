#!/bin/bash

# Set the environment variable
export CLAUDE_CONFIG_DIR=~/claude_code_pers/

# Check if the environment variable is set correctly
if [ "$CLAUDE_CONFIG_DIR" != ~/claude_code_pers/ ]; then
    echo "WARNING: CLAUDE_CONFIG_DIR is not set to ~/claude_code_pers/"
    echo "Current value: $CLAUDE_CONFIG_DIR"
    echo "Please ensure you're using the correct configuration directory for this project."
    exit 1
fi

# Execute claude with all arguments passed to this script
claude --debug --dangerously-skip-permissions "$@"
