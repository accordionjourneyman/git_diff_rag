# 🛠️ Tool Reference

This document provides a reference for the core scripts and tools available in the `scripts/` directory.

## 🐚 CLI Scripts

### `New-Bundle.sh`
**Description**: The main orchestrator for the Git Diff RAG pipeline. It handles the entire flow: safety checks, diff generation, prompt rendering, and LLM execution.

**Usage**:
```bash
./scripts/New-Bundle.sh --repo <repo_name> [OPTIONS]
```

**Options**:
- `--repo <name>`: Repository identifier (must match `repository-setup/<name>.md`).
- `--workflow <name>`: Workflow to execute (default: `pr_review`).
- `--commit <sha>`: Analyze a specific commit.
- `--target <ref>`: Base reference for diff (default: `main`).
- `--source <ref>`: Feature reference for diff (default: `HEAD`).
- `--dry-run`: Render prompt and check tokens without calling the API.

---

### `launch_agent.sh`
**Description**: A wrapper script for launching the Gemini CLI agent with a specific prompt file. Used by the Cockpit for "Agentic Mode".

**Usage**:
```bash
./scripts/launch_agent.sh <agent_name> <prompt_file> [apply_changes]
```

**Arguments**:
- `agent_name`: Currently supports `gemini`.
- `prompt_file`: Path to the generated prompt text file.
- `apply_changes`: `true` or `false` (determines approval mode).

---

### `explain.sh`
**Description**: A convenience wrapper around `New-Bundle.sh` specifically for the `explain_diff` workflow.

**Usage**:
```bash
./scripts/explain.sh <repo_name>
```

---

## 🐍 Python Modules

### `db_manager.py`
**Description**: Manages the SQLite database for the Context Engine. Handles caching, history retrieval, and session logging.

**Commands**:
- `init`: Initialize the database schema.
- `save`: Save an analysis result.
- `get`: Retrieve a cached response.
- `get-context`: Fetch recent history for a repository.
- `search`: Semantic/Text search over history.

**Example**:
```bash
python3 scripts/db_manager.py search my-repo "security vulnerability"
```

---

### `render_prompt.py`
**Description**: The Jinja2 rendering engine. It combines the prompt template, the git diff, and the repository context into a final payload.

**Key Features**:
- Auto-detects code languages in the diff.
- Injects `{{ DIFF_CONTENT }}` and `{{ REPO_NAME }}` variables.
- Supports custom macros from `prompts/macros`.

---

### `call_gemini.py`
**Description**: Handles interactions with the Google Gemini API. Includes retry logic, rate limiting, and token counting.

**Key Functions**:
- `call_with_retry(prompt, model)`: Executes the prompt with exponential backoff.
- `list_models()`: Returns available Gemini models.
- `count_tokens(prompt)`: Returns the token count for a given string.

---

### `checker_engine.py`
**Description**: Runs static analysis rules defined in `.ragrules.yaml` or `global_rules.yaml`.

**Features**:
- **Secret Scanning**: Regex-based detection of keys/tokens.
- **Deprecation Checks**: Warns if deprecated patterns are found in the diff.

---

### `signal_processor.py`
**Description**: Ingests external signals (like CI/CD results, linter output) to enrich the analysis context.

---

### `session_summarizer.py`
**Description**: Analyzes past agent sessions to extract "Lessons Learned" and update the repository's long-term memory in the database.

---

### `config_utils.py`
**Description**: Utilities for loading and saving repository configurations (`repository-setup/*.md`). Used heavily by the Cockpit Settings tab.

---

### `ui_utils.py`
**Description**: Backend logic for the Streamlit Cockpit. Handles Git operations, file tree generation, and diff parsing for the UI.
