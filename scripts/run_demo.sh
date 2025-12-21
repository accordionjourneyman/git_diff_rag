#!/usr/bin/env bash
set -e

# Ensure we are in the repo root
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "=== Git Diff RAG Demo ==="
echo "Target: Self (pr_checker)"

echo ""
echo "----------------------------------------------------------------"
echo "1. Standard PR Review (Dry Run)"
echo "----------------------------------------------------------------"
./scripts/New-Bundle.sh --repo examples/demo-app --workflow pr_review --dry-run

echo ""
echo "----------------------------------------------------------------"
echo "2. Agentic Workspace Map (Dry Run)"
echo "----------------------------------------------------------------"
./scripts/New-Bundle.sh --repo examples/demo-app --workflow agentic_map --dry-run

echo ""
echo "----------------------------------------------------------------"
echo "3. JSON Output Format (Dry Run)"
echo "----------------------------------------------------------------"
./scripts/New-Bundle.sh --repo examples/demo-app --workflow pr_review --output-format json --dry-run

echo ""
echo "✅ Demo completed successfully!"
