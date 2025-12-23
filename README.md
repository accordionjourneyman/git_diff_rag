# Git Diff RAG

**Turn Git Diffs into Actionable Intelligence.**

A robust, repository-driven "Context Engine" that transforms Git diffs into actionable insights using LLMs. Whether you need a critical code review, a non-technical explanation, or a structured JSON map of changes, Git Diff RAG handles the context management so you can focus on the results.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)

## ✨ Key Features

- **Context Engine**: SQLite-based caching prevents redundant API calls for identical diffs and prompts.
- **Token Guard**: Automatically prunes context (switching to `git diff --stat`) if the token limit is exceeded.
- **Smart Defaults**: Auto-detects languages in the diff to tailor the review instructions.
- **Modular Prompts**: Uses Jinja2 templates with reusable macros (`prompts/library`, `prompts/macros`).
- **Safety First**:
    - **Secret Scanning**: Pre-flight regex scan for potential secrets in the diff.
    - **Dry Run**: Validate templates and token counts without spending API credits.

## 🎛️ Review Cockpit (GUI)

Prefer a visual interface? The **Review Cockpit** lets you manage everything from the browser.

```bash
streamlit run cockpit/app.py
```

- **Visual Diff**: Browse changes and see security alerts.
- **Prompt Builder**: Drag-and-drop recipes and snippets to compose custom workflows.
- **Editor**: Edit prompts with a VS Code-like experience.
- **History**: Browse past runs and database logs.

[👉 Read the full Cockpit Documentation](docs/COCKPIT.md)

## � Documentation

- [**Architecture**](docs/ARCHITECTURE.md): High-level design and data flow.
- [**Cockpit Guide**](docs/COCKPIT.md): How to use the GUI.
- [**Tools Reference**](docs/TOOLS.md): CLI scripts and Python modules.

## �🚀 Quick Start

### 1. Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create .env (optional, for Gemini mode)
cp .env.example .env
```

### 2. Run a Review
```bash
# Review the last commit on the current repo
./scripts/New-Bundle.sh --repo my-repo --commit HEAD
```

## 💡 Use Cases (Examples)

1.  **Self-Review**: `New-Bundle.sh --commit HEAD` before pushing.
2.  **Post-Mortem**: `New-Bundle.sh --workflow blame --commit <bad-sha>` to find root causes.
3.  **Non-Technical Update**: `New-Bundle.sh --workflow explain` to generate release notes for PMs.
4.  **Security Audit**: `New-Bundle.sh --workflow security` (custom recipe) to scan for vulnerabilities.
5.  **Migration Helper**: Generate a checklist for migrating API versions based on diffs.
...and many more by creating custom recipes in `prompts/recipes/`.

## 🛠️ CLI Reference

### Main Orchestrator (`New-Bundle.sh`)

```bash
USAGE:
    ./scripts/New-Bundle.sh --repo <repo_name> [OPTIONS]

REQUIRED:
    --repo <name>       Repository name (must match repository-setup/<name>.md)

OPTIONS:
    --workflow <name>   Workflow to execute (default: pr_review)
    --commit <sha>      Analyze a specific commit
    --language <lang>   Force specific language context (e.g., python, sql)
    --dry-run, -n       Render prompt, check tokens, and exit (Validation Gate)
    --output-format     Output format: markdown (default) or json
    --debug             Enable verbose debug output
    --help, -h          Show help message
```

### Explain Wrapper (`explain.sh`)

```bash
./scripts/explain.sh <repo_name> [options]
# Equivalent to: ./scripts/New-Bundle.sh --repo <repo_name> --workflow explain_diff ...
```

## ⚙️ Configuration

Repositories are configured in `repository-setup/{repo}.md` using YAML frontmatter.

### Basic Config
```yaml
---
path: "/absolute/path/to/repo"
main_branch: "main"
remote: "origin"
default_workflow: "pr_review"

# Language Triad (Smart Defaults)
code_language: "auto"       # auto-detects or specific (e.g., "python")
answer_language: "english"  # Language for the final summary
comment_language: "english" # Language for inline code comments
token_limit: 1000000        # Prune context if exceeded
---
```

### Workflow Configuration
Define specific workflows in the frontmatter:

```yaml
workflows:
  - pr_review
  - agentic_map
  - architectural_review
  - github_readiness
  - test_coverage_advisor

pr_review:
  prompt: "prompts/recipes/standard_pr_review.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

agentic_map:
  prompt: "prompts/recipes/agentic_workspace_map.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

architectural_review:
  prompt: "prompts/recipes/architectural_review.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

github_readiness:
  prompt: "prompts/recipes/github_readiness.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

test_coverage_advisor:
  prompt: "prompts/recipes/test_coverage_advisor.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

comprehensive:
  prompt: "prompts/recipes/comprehensive_review.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"
```

## 📚 Prompt Library

The `prompts/library` directory contains atomic modules that can be mixed and matched in your recipes.

- **Security**: `vulnerabilities.md`, `pii.md`, `iac.md`
- **Quality**: `performance.md`, `tests.md`, `typing.md`, `breaking_changes.md`
- **Ops**: `changelog.md`, `migrations.md`
- **Documentation**: `pr_description.md`

Example usage in a recipe:
```jinja2
{% include 'library/security/vulnerabilities.md' %}
```

## 🥞 Stacked PR Strategy

Git Diff RAG supports analyzing **Stacked PRs** (dependent branches) efficiently.

### The Workflow
1.  **Analyze Layer 1 (Base)**:
    ```bash
    ./scripts/New-Bundle.sh --repo my-app --target main --source feature-1
    ```
2.  **Analyze Layer 2 (The Stack)**:
    ```bash
    ./scripts/New-Bundle.sh --repo my-app --target feature-1 --source feature-2 --language python
    ```

### Why this works
*   **Context Engine**: The analysis of Layer 1 is stored in the database. When Layer 2 runs, the LLM sees the previous feedback, understanding the stack's evolution.
*   **Language Isolation**: Use `--language` to focus the LLM on the specific technology of that layer (e.g., SQL for migrations, Python for logic), reducing context noise.
*   **Composite Caching**: Updating Layer 2 doesn't invalidate the cache for Layer 1.

## 📂 Architecture

- **`scripts/`**: Core logic (`New-Bundle.sh`, `call_gemini.py`, `db_manager.py`).
- **`prompts/`**: Jinja2 templates.
    - **`recipes/`**: Ready-to-use workflows (`standard_pr_review.md`).
    - **`macros/`**: Reusable components (`_common.md`, `secret_scan.md`).
- **`repository-setup/`**: Per-repository configuration files.
- **`data/`**: SQLite database for the Context Engine (ignored by git).
- **`output/`**: Generated artifacts (prompts, diffs, responses).

## 🛡️ Security & Caching

- **Secret Scanning**: Every run performs a regex scan on the diff. If secrets are found, a warning is displayed (and logged in `dry-run`).
- **Caching**: The tool calculates a composite hash (`DiffHash` + `PromptHash` + `Model`). If a match is found in `data/history.sqlite`, the cached response is returned instantly.
