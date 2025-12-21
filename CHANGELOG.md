# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2024-12-21 - Git Diff RAG

### ⚠️ BREAKING CHANGES

This release fundamentally transforms `pr_checker` into a flexible **Git Diff RAG** tool.
Users of the previous version must migrate their configurations.

**Directory Renames:**
| Old Path | New Path |
|----------|----------|
| `acceptance-criteria/` | `repository-setup/` |
| `pr-reviews/` | `output/` |
| `pr-review-tools/` | `scripts/` |

**Script Renames:**
| Old Script | New Script |
|------------|------------|
| `New-PRReviewBundle.ps1` | (Deprecated) |
| `New-PRReviewBundle.sh` | `New-Bundle.sh` |
| `Invoke-CopilotReview.ps1` | (Logic merged into New-Bundle.sh) |

**New Dependencies:**

- Python 3.10+ required
- `pip install -r requirements.txt` (google-generativeai, jinja2, pydantic, pyyaml, pytest)

### Migration Guide

1. **Rename directories:**

   ```bash
   mv acceptance-criteria repository-setup
   mv pr-reviews output
   mv pr-review-tools scripts
   ```

2. **Add YAML frontmatter to each `repository-setup/*.md` file:**

   ```yaml
   ---
   name: my_repo
   path: /path/to/repo
   workflows: [pr_review]
   pr_review:
     prompt: prompts/pr_review.md
     llm: copilot
   ---
   # Existing acceptance criteria content...
   ```

3. **Install Python dependencies:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Update any automation/scripts** to use new CLI:

   ```bash
   # Old (deprecated)
   ./pr-review-tools/New-PRReviewBundle.sh -r myrepo

   # New
   ./scripts/New-Bundle.sh --repo myrepo
   ```

### Added

- **Repository-Driven Configuration**: YAML frontmatter in `repository-setup/*.md` defines paths, branches, and workflows.
- **Multiple Workflow Support**: Define `pr_review`, `data_extraction`, or custom workflows per repository.
- **Gemini API Integration**: Call Google Gemini with configurable models, retry logic, and specific error handling.
- **Prompt Templates**: Jinja2 templates in `prompts/` with placeholder validation.
- **LLM Output Validation**: Automatic JSON validation for structured output workflows.
- **Prefect Integration** (optional): Define `post_steps` to trigger Prefect flows after LLM calls.
- **Git Safety Safeguards**: Enforces clean working directory and remote verification.
- **Comprehensive CLI**: `--help` flag, `--workflow` selection, `--debug` mode.
- **Extensive Test Suite**: pytest-based unit and integration tests.

### Changed

- Main entry point is now `scripts/New-Bundle.sh` (cross-platform bash).
- Prompt generation is now driven by templates, not hardcoded strings.
- Output bundles are timestamped and include workflow name.

### Fixed

- N/A (complete rewrite)

### Security

- Secrets managed via `.env` (never committed).
- Input sanitization for paths.
- Read-only Git operations (no push/merge/reset).
- LLM output validation before downstream use.

---

## [1.0.0] - Previous Release

Original `pr_checker` tool with Azure DevOps integration and Copilot-focused PR review.

## [2.1.0] - 2025-12-21 - Context Engine & Prompt Library

### Added

- **Context Engine**: SQLite-based caching (`data/history.sqlite`) prevents redundant API calls for identical diffs and prompts.
- **Token Guard**: Automatically prunes context (switching to `git diff --stat`) if the token limit is exceeded.
- **Prompt Library**: Modular Jinja2 templates in `prompts/library/` (Security, Quality, Ops) and `prompts/macros/`.
- **New Workflows**:
    - `comprehensive`: 360-degree review using the prompt library.
    - `agentic_map`: Generates a structured JSON map of changes.
    - `explain_diff`: Simple explanation for non-technical stakeholders.
- **CLI Enhancements**:
    - `--dry-run`: Validates templates, checks tokens, and scans for secrets without calling the API.
    - `--output-format`: Toggle between `markdown` and `json`.
    - `scripts/explain.sh`: Wrapper for the explain workflow.
    - `scripts/run_demo.sh`: Comprehensive demo script.
- **Secret Scanning**: Pre-flight regex scan for potential secrets in the diff.

### Changed

- **Prompt Structure**: Moved legacy prompts to `prompts/legacy/`. New recipes use `prompts/recipes/`.
- **Logging**: Added timestamps to CLI output.
- **Configuration**: Added `token_limit` and Language Triad (`code_language`, `answer_language`, `comment_language`) to repository config.
