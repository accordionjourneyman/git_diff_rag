#!/usr/bin/env bash
# ============================================================================
# Git Diff RAG - Explain Wrapper (DEPRECATED)
# ============================================================================
# 
# ⚠️  DEPRECATION NOTICE:
# This bash script is deprecated. Please use:
#   python cli.py explain --repo <repo_name>
# ============================================================================

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Find Python
PYTHON_CMD="python3"
if [[ -f "$PROJECT_ROOT/.venv/bin/python3" ]]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python3"
elif [[ -f "$PROJECT_ROOT/venv/bin/python3" ]]; then
    PYTHON_CMD="$PROJECT_ROOT/venv/bin/python3"
fi

# Delegate to Python CLI
exec "$PYTHON_CMD" "$PROJECT_ROOT/cli.py" explain "$@"
