# Git Diff RAG - Architecture

This document describes the architecture of the **Git Diff RAG** tool.

## Overview

Git Diff RAG is a repository-driven "Context Engine" that transforms Git diffs into actionable insights using LLMs. It emphasizes caching, safety, and modular prompt engineering with a modern Python CLI architecture.

## Architecture Diagram

```mermaid
graph TD
    subgraph Input
        CLI[python cli.py]
        CONFIG[repository-setup/*.md]
    end

    subgraph Core["Core Pipeline"]
        PARSE[Parse YAML Frontmatter]
        SAFETY[Git Safety Checks]
        DIFF[Generate Git Diff]
        SCAN[Secret Scan]
        FETCH[Fetch Repo Context]
        RENDER[Render Prompt (Jinja2)]
        GUARD[Token Guard / Pruning]
    end

    subgraph ContextEngine["Context Engine"]
        BASE[Render Base Prompt]
        HASH[Calc Composite Hash]
        DB[(SQLite Cache)]
        CHECK{Cache Hit?}
    end

    subgraph LLM["LLM Integration"]
        GEMINI_API[Gemini API]
        GEMINI_CLI[Gemini CLI]
        COPILOT_CLI[Copilot CLI]
        VALIDATE[Validate Output]
    end

    subgraph Output
        BUNDLE[output/timestamp-repo-workflow/]
        RESULT[llm_result.md]
    end

    CLI --> PARSE
    CONFIG --> PARSE
    PARSE --> SAFETY
    SAFETY --> DIFF
    DIFF --> SCAN
    SCAN --> FETCH
    FETCH --> RENDER
    RENDER --> GUARD
    GUARD --> BASE
    BASE --> HASH
    HASH --> CHECK
    CHECK -- Yes --> RESULT
    CHECK -- No --> GEMINI_API
    CHECK -- No --> GEMINI_CLI
    CHECK -- No --> COPILOT_CLI
    GEMINI_API --> VALIDATE
    GEMINI_CLI --> VALIDATE
    COPILOT_CLI --> VALIDATE
    VALIDATE --> DB
    VALIDATE --> RESULT
```

## Key Components

### 1. Core Pipeline (`cli.py` + `scripts/orchestrator.py`)
- **Orchestrator**: Python CLI manages the entire flow from command input to final output.
- **Safety**: Enforces clean git state and scans for secrets before processing.
- **Context Injection**: Fetches recent analyses for the target repository from the database and injects them into the prompt.
- **Token Guard**: Checks estimated token count against `token_limit`. If exceeded, it prunes the context (switches to `git diff --stat`) to prevent API errors.

### 2. Prompt Library (`prompts/`)
- **Jinja2 Templates**: Dynamic templates that adapt to the diff content.
- **Smart Defaults**: `render_prompt.py` detects languages in the diff and injects them into the prompt context.
- **Macros**: Reusable components like `_common.md` (Language Triad) and `context_history.md`.

### 3. Context Engine (`scripts/db_manager.py`)
- **Caching**: Stores LLM responses in `data/history.sqlite`.
- **Composite Hashing**: Cache keys combine DiffHash + PromptHash + Model to ensure cache stability.
- **Repository Memory**: Tracks analysis history per repository (`repo_name`) to provide context for future runs.
- **Efficiency**: Prevents re-running expensive LLM calls for unchanged inputs.

### 4. LLM Integration
- **Gemini API** (`scripts/call_gemini.py`): Direct API integration with retry logic and rate limit handling.
- **Gemini CLI** (`scripts/call_gemini_cli.py`): Command-line interface with cross-platform path resolution.
- **Copilot CLI** (`scripts/call_copilot_cli.py`): GitHub Copilot integration for enterprise environments.

### 5. Intelligence Loop
- **Critic Verification**: A secondary pass that cross-references the LLM's output with previous analyses and external signals to ensure consistency and accuracy.
- **Session Summarizer**: Extracts "Lessons Learned" from agent sessions and stores them in the database, improving the repository's long-term memory.
- **Signal Processing**: `scripts/signal_processor.py` handles the ingestion of external signals (e.g., linter results, test failures) to enrich the context.

### 6. Review Cockpit (`cockpit/app.py`)
- **UI Layer**: A Streamlit application that provides a visual interface for the entire system.
- **State Management**: Handles session state for active bundles, selected files, and execution progress.
- **Integration**: Directly imports core Python modules to ensure feature parity with the CLI.
