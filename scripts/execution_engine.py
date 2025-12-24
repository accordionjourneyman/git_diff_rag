"""Execution Engine - LLM Workflow Execution Module.

This module manages the execution flow for LLM workflows, including caching,
provider calls, result persistence, and middleware processing (e.g., secret scanning).
Consolidates execution logic from orchestrator.py into a focused, testable module.
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Raised when workflow execution fails."""
    def __init__(self, message: str, operation: str = None):
        self.operation = operation
        super().__init__(f"{message} (operation: {operation})")


class LLMError(ExecutionError):
    """Raised when LLM call fails."""
    pass


class CacheError(ExecutionError):
    """Raised when caching operations fail."""
    pass


def check_cache(diff_hash: str, prompt_hash: str, model: str) -> Optional[str]:
    """Check database cache for existing response.

    Args:
        diff_hash: SHA256 hash of diff content
        prompt_hash: SHA256 hash of base prompt
        model: LLM model name

    Returns:
        Cached response string if found, None otherwise

    Raises:
        CacheError: If cache check fails
    """
    try:
        from scripts import db_manager
        result = db_manager.get_cache(diff_hash, prompt_hash, model)
        if result:
            logger.info("✓ Cache hit! Returning cached response.")
            return result.get('response', '')
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")
        raise CacheError(f"Cache check failed: {e}", "cache_check")

    return None


def call_llm_provider(wf_config: Dict[str, Any], prompt: str) -> str:
    """Call the appropriate LLM provider based on workflow config.

    Args:
        wf_config: Workflow configuration dictionary
        prompt: Rendered prompt to send to LLM

    Returns:
        LLM response string

    Raises:
        LLMError: If LLM call fails
    """
    llm_provider = wf_config.get('llm', 'copilot')
    model = wf_config.get('model', 'gemini-1.5-flash')

    try:
        from scripts.llm_strategy import get_provider

        provider = get_provider(llm_provider)

        if not provider.is_available():
            raise LLMError(
                f"LLM provider '{llm_provider}' is not available. "
                "Check installation and authentication.",
                "provider_check"
            )

        logger.info(f"🤖 Calling {llm_provider} ({model})...")

        # Call the provider with appropriate parameters
        if llm_provider == 'gh-copilot':
            # For analysis/review workflows, don't allow file writing tools
            # Only allow git operations if needed
            workflow_name = wf_config.get('workflow', '')
            if 'review' in workflow_name.lower() or 'analyze' in workflow_name.lower():
                # Analysis workflows: no file writing, minimal tools
                response = provider.call(
                    prompt,
                    allow_tools=[],  # No tools for analysis to prevent file creation
                    timeout=300
                )
            else:
                # Other workflows may need tools
                response = provider.call(
                    prompt,
                    allow_tools=['shell(git)', 'write'],
                    timeout=300
                )
        else:
            response = provider.call(prompt, model=model)

        return response

    except ValueError as e:
        # Unknown provider
        raise LLMError(str(e), "provider_selection")
    except Exception as e:
        # Handle specific provider errors
        from scripts import call_copilot_cli
        if isinstance(e, call_copilot_cli.CopilotNotInstalledError):
            raise LLMError(f"Copilot CLI not available: {e}", "copilot_installation")
        elif isinstance(e, call_copilot_cli.CopilotAuthError):
            raise LLMError(f"Copilot CLI authentication failed: {e}", "copilot_auth")
        else:
            raise LLMError(f"LLM call failed: {e}", "llm_call")


def scan_for_secrets(diff_content: str) -> List[Dict[str, Any]]:
    """Scan diff content for potential secrets.

    Args:
        diff_content: Git diff content to scan

    Returns:
        List of findings dictionaries with secret details
    """
    findings = []

    # Simple regex patterns for common secrets
    patterns = [
        (r'password\s*[:=]\s*["\']([^"\']+)["\']', 'password'),
        (r'secret\s*[:=]\s*["\']([^"\']+)["\']', 'secret'),
        (r'api_key\s*[:=]\s*["\']([^"\']+)["\']', 'api_key'),
        (r'token\s*[:=]\s*["\']([^"\']+)["\']', 'token'),
        # Add more patterns as needed
    ]

    import re
    for pattern, secret_type in patterns:
        matches = re.findall(pattern, diff_content, re.IGNORECASE)
        for match in matches:
            findings.append({
                'type': secret_type,
                'value': match,
                'pattern': pattern
            })

    if findings:
        logger.warning(f"⚠️  Detected {len(findings)} potential secrets in diff")

    return findings


def save_execution_results(
    wf_config: Dict[str, Any],
    diff_content: str,
    full_prompt: str,
    base_prompt: str,
    response: str,
    output_dir: Path
) -> None:
    """Save workflow execution results to disk and database.

    Args:
        wf_config: Workflow configuration
        diff_content: Git diff content
        full_prompt: Rendered prompt with context
        base_prompt: Rendered prompt without context (for hashing)
        response: LLM response
        output_dir: Directory to save artifacts

    Raises:
        ExecutionError: If saving fails
    """
    try:
        # Save to disk
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "diff.patch").write_text(diff_content, encoding='utf-8')
        (output_dir / "prompt.txt").write_text(full_prompt, encoding='utf-8')
        (output_dir / "prompt_base.txt").write_text(base_prompt, encoding='utf-8')

        output_format = wf_config.get('output_format', 'markdown')
        output_file = output_dir / f"llm_result.{output_format}"
        output_file.write_text(response, encoding='utf-8')

        logger.info(f"📂 Artifacts saved to: {output_dir}")

        # Save to database (if not manual copilot mode)
        if not response.startswith("[COPILOT_MANUAL_MODE]"):
            try:
                from scripts import db_manager

                diff_hash = hashlib.sha256(diff_content.encode()).hexdigest()
                prompt_hash = hashlib.sha256(base_prompt.encode()).hexdigest()
                model = wf_config.get('model', 'unknown')
                repo_name = wf_config.get('repo_name', 'unknown')

                db_manager.save_cache(
                    diff_hash=diff_hash,
                    prompt_hash=prompt_hash,
                    model=model,
                    response=response,
                    repo_name=repo_name,
                    summary=response[:200] + "...",
                    tags=wf_config.get('workflow', 'unknown'),
                    config_snapshot=None  # Could be added if needed
                )
                logger.info("💾 Results saved to database cache")
            except Exception as e:
                logger.warning(f"Failed to save to database: {e}")
                raise CacheError(f"Database save failed: {e}", "db_save")

    except Exception as e:
        raise ExecutionError(f"Failed to save results: {e}", "result_save")


def execute_workflow_step(
    wf_config: Dict[str, Any],
    diff_content: str,
    prompt_template_path: str,
    target_ref: str = None,
    source_ref: str = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Execute a single workflow step with LLM processing.

    Args:
        wf_config: Workflow configuration
        diff_content: Git diff content
        prompt_template_path: Path to prompt template
        target_ref: Target reference for context
        source_ref: Source reference for context
        use_cache: Whether to check/use cache

    Returns:
        Dictionary with execution results

    Raises:
        ExecutionError: If execution fails
    """
    # Render prompts
    from scripts.prompt_builder import build_prompt_with_context, get_prompt_hash

    full_prompt, base_prompt = build_prompt_with_context(
        template_path=prompt_template_path,
        diff_content=diff_content,
        repo_name=wf_config.get('repo_name', 'unknown'),
        languages=wf_config.get('languages'),
        target_ref=target_ref,
        source_ref=source_ref,
        output_dir=str(output_dir)
    )

    # Generate hashes for caching
    diff_hash = hashlib.sha256(diff_content.encode()).hexdigest()
    prompt_hash = get_prompt_hash(base_prompt)
    model = wf_config.get('model', 'unknown')

    # Check cache
    cached_response = None
    if use_cache:
        try:
            cached_response = check_cache(diff_hash, prompt_hash, model)
        except CacheError:
            logger.warning("Cache check failed, proceeding without cache")

    # Prepare output directory
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    repo_name = wf_config.get('repo_name', 'unknown')
    workflow = wf_config.get('workflow', 'unknown')
    output_dir = Path("output") / f"{timestamp}-{repo_name}-{workflow}"

    # Dry run mode
    if wf_config.get('dry_run'):
        logger.info("✓ Dry run: Prompt rendered successfully")
        estimated_tokens = len(full_prompt) // 4
        logger.info(f"📊 Estimated tokens: ~{estimated_tokens}")

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "prompt.txt").write_text(full_prompt, encoding='utf-8')
        logger.info(f"📄 Prompt saved to: {output_dir / 'prompt.txt'}")

        return {
            'success': True,
            'dry_run': True,
            'output_dir': str(output_dir),
            'estimated_tokens': estimated_tokens,
            'full_prompt': full_prompt
        }

    # Use cache or call LLM
    if cached_response:
        response = cached_response
        logger.info("📋 Using cached response")
    else:
        response = call_llm_provider(wf_config, full_prompt)

    # Save results
    save_execution_results(
        wf_config,
        diff_content,
        full_prompt,
        base_prompt,
        response,
        output_dir
    )

    return {
        'success': True,
        'output_dir': str(output_dir),
        'response': response,
        'cached': cached_response is not None,
        'full_prompt': full_prompt
    }