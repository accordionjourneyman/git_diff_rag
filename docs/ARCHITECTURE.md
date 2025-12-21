# Git Diff RAG - Architecture

This document describes the architecture of the **Git Diff RAG** tool (formerly `pr_checker`).

## Overview

Git Diff RAG is a repository-driven "Context Engine" that transforms Git diffs into actionable insights using LLMs. It emphasizes caching, safety, and modular prompt engineering.

## Architecture Diagram

```mermaid
graph TD
    subgraph Input
        CLI[New-Bundle.sh]
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
        HASH[Calc Stable Hash]
        DB[(SQLite Cache)]
        CHECK{Cache Hit?}
    end

    subgraph LLM["LLM Integration"]
        COPILOT[Copilot Mode]
        GEMINI[Gemini API]
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
    CHECK -- No --> GEMINI
    CHECK -- No --> COPILOT
    GEMINI --> VALIDATE
    VALIDATE --> DB
    VALIDATE --> RESULT
```

## Key Components

### 1. Core Pipeline (`scripts/New-Bundle.sh`)
- **Orchestrator**: Manages the entire flow from CLI input to final output.
- **Safety**: Enforces clean git state and scans for secrets before processing.
- **Context Injection**: Fetches the last 3 analyses for the target repository from the database and injects them into the prompt.
- **Token Guard**: Checks estimated token count against `token_limit`. If exceeded, it prunes the context (switches to `git diff --stat`) to prevent API errors.

### 2. Prompt Library (`prompts/`)
- **Jinja2 Templates**: Dynamic templates that adapt to the diff content.
- **Smart Defaults**: `render_prompt.py` detects languages in the diff and injects them into the prompt context.
- **Macros**: Reusable components like `_common.md` (Language Triad) and `context_history.md`.

### 3. Context Engine (`scripts/db_manager.py`)
- **Caching**: Stores LLM responses in `data/history.sqlite`.
- **Smart Hashing**: Cache keys are calculated from a "Base Prompt" (Template + Diff) *excluding* the dynamic context history. This ensures cache stability.
- **Repository Memory**: Tracks analysis history per repository (`repo_name`) to provide context for future runs.
- **Efficiency**: Prevents re-running expensive LLM calls for unchanged inputs.

### 4. LLM Integration (`scripts/call_gemini.py`)
- **Gemini**: Direct API integration with retry logic and rate limit handling.
- **Copilot**: Fallback mode that copies the prompt to the clipboard for manual use.
