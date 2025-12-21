#!/usr/bin/env bash
# Wrapper for New-Bundle.sh to run the explain_diff workflow

if [[ $# -lt 1 ]]; then
    echo "Usage: ./scripts/explain.sh <repo_name> [options]"
    exit 1
fi

REPO="$1"
shift

./scripts/New-Bundle.sh --repo "$REPO" --workflow explain_diff "$@"
