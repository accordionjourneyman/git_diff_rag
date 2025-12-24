# 🛠️ Tool Reference

This document provides a reference for the core CLI commands and Python modules available in Git Diff RAG.

## 🐚 CLI Commands

### `python cli.py`
**Description**: The main entry point for all Git Diff RAG operations. A comprehensive Python CLI that replaces the legacy bash scripts.

**Main Commands**:

#### `analyze`
Execute analysis workflow on git diff.
```bash
python cli.py analyze --repo <repo_name> [OPTIONS]
```

**Required Options**:
- `--repo <name>`: Repository identifier (must match `repository-setup/<name>.md`).

**Optional Options**:
- `--workflow <name>`: Workflow to execute (default from config).
- `--target <ref>`: Target ref for diff (base).
- `--source <ref>`: Source ref for diff (tip).
- `--commit <sha>`: Analyze a specific commit.
- `--language <lang>`: Force specific language context.
- `--dry-run, -n`: Render prompt, check tokens, and exit.
- `--output-format`: Output format: markdown (default) or json.
- `--debug`: Enable verbose debug output.

#### `explain`
Explain changes in plain language (convenience wrapper for analyze with explain_diff workflow).
```bash
python cli.py explain --repo <repo_name> [OPTIONS]
```

#### `list-models`
List available AI models for each provider.
```bash
python cli.py list-models
```

#### `check-setup`
Verify installation and configuration.
```bash
python cli.py check-setup
```

#### `list-repos`
List configured repositories.
```bash
python cli.py list-repos
```

---

## 🐍 Python Modules

### `scripts/db_manager.py`
**Description**: Manages the SQLite database for the Context Engine. Handles caching, history retrieval, and session logging.

**Key Functions**:
- `init_database()`: Initialize the database schema.
- `save_analysis()`: Save an analysis result with composite hash.
- `get_cached_response()`: Retrieve a cached response by hash.
- `get_repository_history()`: Fetch recent history for a repository.
- `search_history()`: Semantic/Text search over history.

**Example**:
```bash
python3 scripts/db_manager.py search my-repo "security vulnerability"
```

---

### `scripts/render_prompt.py`
**Description**: The Jinja2 rendering engine. It combines the prompt template, the git diff, and the repository context into a final payload.

**Key Features**:
- Auto-detects code languages in the diff.
- Injects `{{ DIFF_CONTENT }}`, `{{ REPO_NAME }}`, and `{{ OUTPUT_DIR }}` variables.
- Supports custom macros from `prompts/macros/`.
- Handles token pruning when limits are exceeded.

---

### `scripts/call_gemini.py`
**Description**: Handles interactions with Google Gemini API. Includes retry logic, rate limiting, and token counting.

**Key Functions**:
- `call_gemini_api()`: Executes prompts via Gemini API with exponential backoff.
- `get_client()`: Initializes and returns Gemini API client.
- `list_models()`: Returns available Gemini API models.
- `count_tokens()`: Returns the token count for a given string.

---

### `scripts/call_gemini_cli.py`
**Description**: Handles interactions with Google Gemini CLI. Provides programmatic interface for CLI-based analysis.

**Key Functions**:
- `call_gemini_cli()`: Executes prompts via Gemini CLI with full path resolution.
- `is_gemini_cli_installed()`: Checks CLI availability using `shutil.which()`.
- `is_gemini_cli_authenticated()`: Verifies CLI authentication status.
- `get_available_models()`: Returns available Gemini CLI models.

---

### `scripts/call_copilot_cli.py`
**Description**: Handles interactions with GitHub Copilot CLI. Provides programmatic interface for Copilot analysis.

**Key Functions**:
- `call_copilot_cli()`: Executes prompts via Copilot CLI.
- `is_copilot_installed()`: Checks CLI availability.
- `check_authentication()`: Verifies CLI authentication.
- `get_available_models()`: Returns available Copilot models.

---

### `scripts/validate_output.py`
**Description**: Validates generated output against expected formats and performs quality checks.

**Key Features**:
- JSON schema validation for structured outputs.
- Markdown formatting checks.
- Content quality scoring.

---

### `cockpit/app.py`
**Description**: Streamlit web interface for Git Diff RAG. Provides visual diff browsing, prompt building, and history management.

**Key Components**:
- `main()`: Main application entry point.
- `render_diff_viewer()`: Visual diff display with syntax highlighting.
- `render_prompt_builder()`: Drag-and-drop prompt composition.
- `render_history()`: Browse past analysis runs.

---

### `cockpit/components/`
**Description**: Reusable UI components for the Streamlit cockpit.

- `diff_viewer.py`: Visual diff rendering with file tree navigation.
- `file_tree.py`: Repository file tree component.
- `prompt_editor.py`: VS Code-like prompt editing experience.
