---
# =============================================================================
# TEMPLATE: Repository Setup Configuration
# =============================================================================
# Copy this file to repository-setup/<your_repo_name>.md and customize.
#
# Required fields:
#   - path: Absolute path to the local git repository
#
# Optional fields (with defaults):
#   - name: Repository identifier (defaults to filename)
#   - main_branch: Branch to diff against (default: main)
#   - remote: Git remote name (default: origin)
#   - default_workflow: Workflow when --workflow not specified (default: pr_review)
#   - workflows: List of available workflows for this repo
#
# Workflow configuration:
#   Each workflow needs:
#     - prompt: Path to the Jinja2 prompt template (relative to project root)
#     - llm: 'copilot' or 'gemini'
#     - model: (Optional) Gemini model name (default: gemini-1.5-flash)
#     - post_steps: (Optional) Prefect flow to run after LLM call
# =============================================================================

name: my_repo_name
path: /absolute/path/to/your/repo
main_branch: main
remote: origin
default_workflow: pr_review

workflows:
  - pr_review
  - comprehensive
  - explain_diff

# Workflow: PR Review (Gemini)
# Uses Gemini API for code review.
pr_review:
  prompt: prompts/recipes/standard_pr_review.md
  llm: gemini
  model: "gemini-3-flash-preview"

# Workflow: Comprehensive Review
# 360-degree review using the Prompt Library.
comprehensive:
  prompt: prompts/recipes/comprehensive_review.md
  llm: gemini
  model: "gemini-3-flash-preview"

# Workflow: Explain Diff
# Simple explanation for non-technical stakeholders.
explain_diff:
  prompt: prompts/recipes/explain_diff.md
  llm: gemini
  model: "gemini-3-flash-preview"
---

# Acceptance Criteria for my_repo_name

## 1) Intent & Scope

- PR description states user-visible impact and why the change is needed.
- PR is small and focused; unrelated refactors are isolated.

## 2) Build & Lint

- Build succeeds without errors.
- No new lint warnings introduced.

## 3) Code Quality

- Functions have single responsibility.
- No code duplication.
- Naming is clear and consistent.

## 4) Testing

- New logic has test coverage or manual verification steps.
