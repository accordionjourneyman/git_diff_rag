"""Prompt Builder - Jinja2 Template Rendering Module.

This module handles all prompt construction, template rendering, and context
injection for LLM workflows. Consolidates functionality from render_prompt.py
and orchestrator.py into a focused, testable module.
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import logging

logger = logging.getLogger(__name__)


class PromptBuilderError(Exception):
    """Raised when prompt building fails."""
    def __init__(self, message: str, template_path: str = None):
        self.template_path = template_path
        super().__init__(f"{message} (template: {template_path})")


def detect_languages(diff_text: str) -> List[str]:
    """Detect programming languages from git diff content.

    Args:
        diff_text: Git diff output

    Returns:
        List of detected language names
    """
    # Scan for "diff --git a/path/to/file.ext"
    ext_pattern = re.compile(r'diff --git a/.*\.(\w+)\s+b/')
    extensions = set(ext_pattern.findall(diff_text))

    # Extension to language mapping
    lang_map = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript', 'java': 'java',
        'go': 'go', 'rs': 'rust', 'c': 'c', 'cpp': 'cpp', 'html': 'html',
        'css': 'css', 'sql': 'sql', 'md': 'markdown', 'sh': 'bash', 'yaml': 'yaml',
        'json': 'json', 'rb': 'ruby', 'php': 'php', 'swift': 'swift', 'kt': 'kotlin'
    }

    languages = set()
    for ext in extensions:
        if ext in lang_map:
            languages.add(lang_map[ext])

    return list(languages) if languages else ['unknown']


def load_template_environment() -> Environment:
    """Create and configure Jinja2 environment for prompt templates.

    Returns:
        Configured Jinja2 Environment
    """
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    prompts_dir = repo_root / 'prompts'

    env = Environment(loader=FileSystemLoader([prompts_dir, repo_root, Path.cwd()]))
    return env


def build_template_context(
    diff_content: str,
    repo_name: str,
    languages: Optional[List[str]] = None,
    context_data: Optional[List[Dict]] = None,
    signals_data: Optional[List[Dict]] = None,
    docs_data: Optional[List[Dict]] = None,
    findings_data: Optional[List[Dict]] = None,
    commit_history_data: Optional[Dict] = None,
    target_ref: Optional[str] = None,
    source_ref: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Build the context dictionary for Jinja2 template rendering.

    Args:
        diff_content: Git diff content
        repo_name: Repository name
        languages: Detected or specified languages
        context_data: Historical context data
        signals_data: Security signals data
        docs_data: Documentation data
        findings_data: Analysis findings data
        commit_history_data: Commit history data
        target_ref: Target reference
        source_ref: Source reference
        env_vars: Environment variables
        output_dir: Output directory path

    Returns:
        Context dictionary for template rendering
    """
    if env_vars is None:
        env_vars = os.environ

    # Detect languages if not provided
    if languages is None:
        languages = detect_languages(diff_content)

    # Build context
    context = {
        "DIFF_CONTENT": diff_content,
        "REPO_NAME": repo_name,
        "BUNDLE_PATH": env_vars.get('BUNDLE_PATH', 'unknown'),
        "CODE_LANGS": languages,
        "CODE_LANG": languages[0] if languages else 'text',
        "ANSWER_LANG": env_vars.get('ANSWER_LANGUAGE', 'english'),
        "COMMENT_LANG": env_vars.get('COMMENT_LANGUAGE', 'english'),
        "OUTPUT_FORMAT": env_vars.get('OUTPUT_FORMAT', 'markdown'),
        "OUTPUT_DIR": output_dir or "output",
        "CONTEXT": context_data or [],
        "SIGNALS": signals_data or [],
        "DOCS": docs_data or [],
        "FINDINGS": findings_data or [],
        "COMMIT_HISTORY": commit_history_data or {},
        "TARGET_REF": target_ref or "unknown",
        "SOURCE_REF": source_ref or "unknown"
    }

    return context


def render_prompt_template(
    template_path: str,
    context: Dict[str, Any]
) -> str:
    """Render a Jinja2 template with the given context.

    Args:
        template_path: Path to template file
        context: Context dictionary for rendering

    Returns:
        Rendered template string

    Raises:
        PromptBuilderError: If rendering fails
    """
    env = load_template_environment()

    try:
        if Path(template_path).exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template_src = f.read()
            template = env.from_string(template_src)
        else:
            # Try loading as template name from prompts directory
            template = env.get_template(template_path)

        return template.render(**context)

    except Exception as e:
        raise PromptBuilderError(f"Template rendering failed: {e}", template_path)


def build_prompt_with_context(
    template_path: str,
    diff_content: str,
    repo_name: str,
    languages: Optional[List[str]] = None,
    context_data: Optional[List[Dict]] = None,
    commit_history_data: Optional[Dict] = None,
    target_ref: Optional[str] = None,
    source_ref: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Tuple[str, str]:
    """Build full prompt with context and base prompt for caching.

    Args:
        template_path: Path to prompt template
        diff_content: Git diff content
        repo_name: Repository name
        languages: Detected languages
        context_data: Historical context
        commit_history_data: Commit history data
        target_ref: Target reference
        source_ref: Source reference
        output_dir: Output directory path

    Returns:
        Tuple of (full_prompt, base_prompt_for_hashing)
    """
    # Build base context (for cache key - minimal context)
    base_context = build_template_context(
        diff_content=diff_content,
        repo_name=repo_name,
        languages=languages,
        context_data=[],  # Empty for base
        commit_history_data={},  # Empty for base
        target_ref=target_ref,
        source_ref=source_ref,
        output_dir=output_dir
    )

    # Render base prompt (used for cache key)
    base_prompt = render_prompt_template(template_path, base_context)

    # Build full context (with all available data)
    full_context = build_template_context(
        diff_content=diff_content,
        repo_name=repo_name,
        languages=languages,
        context_data=context_data,
        commit_history_data=commit_history_data,
        target_ref=target_ref,
        source_ref=source_ref,
        output_dir=output_dir
    )

    # Render full prompt
    full_prompt = render_prompt_template(template_path, full_context)

    return full_prompt, base_prompt


def load_context_data(repo_name: str, limit: int = 3) -> List[Dict]:
    """Load historical context data for a repository.

    Args:
        repo_name: Repository name
        limit: Maximum number of context entries

    Returns:
        List of context dictionaries
    """
    try:
        # Import here to avoid circular imports
        from scripts import db_manager
        return db_manager.get_context(repo_name, limit=limit)
    except Exception as e:
        logger.warning(f"Failed to load context history: {e}")
        return []


def get_prompt_hash(prompt: str) -> str:
    """Generate hash for prompt content (used for caching).

    Args:
        prompt: Prompt string

    Returns:
        SHA256 hash of prompt
    """
    import hashlib
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()