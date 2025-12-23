#!/usr/bin/env bash
set -euo pipefail

# scripts/launch_agent.sh - Abstraction for AI Agent CLIs

AGENT="${1:-gemini}"
PROMPT_FILE="${2:-}"
APPLY="${3:-false}"

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "[ERROR] Prompt file not found: $PROMPT_FILE"
    exit 1
fi

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] [AGENT] $1"; }

case "$AGENT" in
    gemini)
        log "Launching Gemini CLI Agent..."
        
        # Determine approval mode
        APPROVAL_MODE="default"
        if [[ "$APPLY" == "true" ]]; then
            APPROVAL_MODE="yolo"
        fi
        
        # Ensure gemini is in PATH (common locations)
        export PATH=$PATH:/home/tiago/.nvm/versions/node/v24.11.1/bin
        
        # Launch interactive or piped? 
        # User requested interactive agentic CLI.
        # We pipe the prompt to gemini.
        log "Starting session. History will be available via 'gemini --list-sessions'."
        cat "$PROMPT_FILE" | gemini --approval-mode "$APPROVAL_MODE" 2>&1 | tee "$PROMPT_FILE.session.log"
        ;;
        
    claude|aider)
        echo "[ERROR] Agent '$AGENT' is not yet implemented. Use 'gemini'."
        exit 1
        ;;
        
    *)
        echo "[ERROR] Unknown agent: $AGENT"
        exit 1
        ;;
esac
