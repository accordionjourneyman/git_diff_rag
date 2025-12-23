"""Main orchestration module for Git Diff RAG workflows.

This module replaces New-Bundle.sh, providing Python-native workflow execution
with cross-platform compatibility and better error handling.
"""

import os
import sys
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import config_utils, db_manager, git_operations, clipboard
from scripts.render_prompt import render_template, detect_languages
from scripts import call_gemini
from scripts import call_copilot_cli

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Raised when workflow execution fails."""
    pass


class WorkflowConfig:
    """Configuration for a single workflow execution."""
    
    def __init__(
        self,
        repo_name: str,
        workflow: Optional[str] = None,
        target_ref: Optional[str] = None,
        source_ref: Optional[str] = None,
        commit: Optional[str] = None,
        dry_run: bool = False,
        output_format: str = 'markdown',
        language: Optional[str] = None,
        debug: bool = False
    ):
        self.repo_name = repo_name
        self.workflow = workflow
        self.target_ref = target_ref
        self.source_ref = source_ref
        self.commit = commit
        self.dry_run = dry_run
        self.output_format = output_format
        self.language = language
        self.debug = debug
        
        # Loaded from config file
        self.repo_config: Dict[str, Any] = {}
        self.repo_path: str = ""
        self.main_branch: str = "main"
        self.remote: str = "origin"
        self.workflow_config: Dict[str, Any] = {}


def load_workflow_config(wf_config: WorkflowConfig) -> None:
    """Load repository and workflow configuration from YAML file.
    
    Args:
        wf_config: WorkflowConfig object to populate
        
    Raises:
        WorkflowError: If config file not found or invalid
    """
    setup_file = PROJECT_ROOT / "repository-setup" / f"{wf_config.repo_name}.md"
    
    if not setup_file.exists():
        raise WorkflowError(f"Repository setup file not found: {setup_file}")
    
    wf_config.repo_config = config_utils.load_repo_config(wf_config.repo_name)
    
    if not wf_config.repo_config:
        raise WorkflowError(f"Failed to parse config from {setup_file}")
    
    # Extract core settings
    wf_config.repo_path = wf_config.repo_config.get('path', '')
    wf_config.main_branch = wf_config.repo_config.get('main_branch', 'main')
    wf_config.remote = wf_config.repo_config.get('remote', 'origin')
    
    # Determine workflow
    if not wf_config.workflow:
        wf_config.workflow = wf_config.repo_config.get('default_workflow', 'pr_review')
    
    # Load workflow-specific config
    wf_config.workflow_config = wf_config.repo_config.get(wf_config.workflow, {})
    
    if not wf_config.workflow_config:
        raise WorkflowError(
            f"Workflow '{wf_config.workflow}' not defined in {setup_file}"
        )
    
    logger.info(f"Target: {wf_config.repo_name} ({wf_config.repo_path})")
    logger.info(f"Workflow: {wf_config.workflow}")
    logger.info(f"Mode: {'DRY RUN' if wf_config.dry_run else 'LIVE'}")


def validate_repository(wf_config: WorkflowConfig) -> None:
    """Validate that repository exists and is in clean state.
    
    Args:
        wf_config: WorkflowConfig with repo_path set
        
    Raises:
        WorkflowError: If repository invalid or has uncommitted changes
    """
    if not git_operations.is_valid_repository(wf_config.repo_path):
        raise WorkflowError(f"Not a git repository: {wf_config.repo_path}")
    
    is_clean, status = git_operations.is_clean_working_directory(wf_config.repo_path)
    if not is_clean:
        logger.warning(f"Uncommitted changes detected:\n{status}")
        # Don't error - just warn. Users may want to analyze work-in-progress


def determine_refs(wf_config: WorkflowConfig) -> Tuple[str, str]:
    """Determine target and source refs for diff generation.
    
    Args:
        wf_config: WorkflowConfig with ref settings
        
    Returns:
        Tuple of (target_ref, source_ref)
    """
    # Determine target (base)
    if wf_config.target_ref:
        target_ref = wf_config.target_ref
    elif wf_config.commit:
        target_ref = f"{wf_config.commit}~1"
    else:
        target_ref = f"{wf_config.remote}/{wf_config.main_branch}"
    
    # Determine source (tip)
    if wf_config.source_ref:
        source_ref = wf_config.source_ref
    elif wf_config.commit:
        source_ref = wf_config.commit
    else:
        source_ref = "HEAD"
    
    logger.info(f"Generating git diff: {target_ref}...{source_ref}")
    
    return target_ref, source_ref


def generate_diff(
    wf_config: WorkflowConfig,
    target_ref: str,
    source_ref: str,
    token_limit: Optional[int] = None
) -> str:
    """Generate git diff, with optional token pruning.
    
    Args:
        wf_config: WorkflowConfig
        target_ref: Base reference
        source_ref: Tip reference
        token_limit: If set, prune to --stat if diff exceeds limit
        
    Returns:
        Diff content as string
    """
    try:
        diff_content = git_operations.get_diff(
            wf_config.repo_path,
            target_ref,
            source_ref,
            stat_only=False
        )
    except git_operations.GitOperationError as e:
        raise WorkflowError(f"Failed to generate diff: {e}")
    
    if not diff_content.strip():
        logger.info("No changes detected. Skipping LLM call.")
        return ""
    
    # Token pruning if needed
    if token_limit:
        estimated_tokens = len(diff_content) // 4  # Rough estimate
        if estimated_tokens > token_limit:
            logger.warning(
                f"Diff too large (~{estimated_tokens} tokens > {token_limit} limit). "
                f"Pruning to --stat summary."
            )
            diff_content = git_operations.get_diff(
                wf_config.repo_path,
                target_ref,
                source_ref,
                stat_only=True
            )
    
    return diff_content


def scan_for_secrets(diff_content: str) -> list[str]:
    """Scan diff for potential secrets/credentials.
    
    Args:
        diff_content: The git diff text
        
    Returns:
        List of findings (empty if no secrets detected)
    """
    findings = []
    
    # Common secret patterns
    patterns = {
        'API Key': r'["\']?api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]{20,}',
        'Password': r'["\']?password["\']?\s*[:=]\s*["\'][^"\']{8,}',
        'Token': r'["\']?token["\']?\s*[:=]\s*["\']?[\w-]{20,}',
        'AWS Key': r'AKIA[0-9A-Z]{16}',
        'Private Key': r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
    }
    
    for secret_type, pattern in patterns.items():
        matches = re.finditer(pattern, diff_content, re.IGNORECASE)
        for match in matches:
            findings.append(f"{secret_type}: {match.group(0)[:50]}...")
    
    if findings:
        logger.warning(f"⚠️  Potential secrets detected: {len(findings)} findings")
        for finding in findings:
            logger.warning(f"  - {finding}")
    
    return findings


def check_cache(diff_hash: str, prompt_hash: str, model: str) -> Optional[str]:
    """Check database cache for existing analysis.
    
    Args:
        diff_hash: SHA256 hash of diff content
        prompt_hash: SHA256 hash of base prompt
        model: Model name
        
    Returns:
        Cached response or None
    """
    try:
        result = db_manager.get_cache(diff_hash, prompt_hash, model)
        if result:
            logger.info("✓ Cache hit! Returning cached response.")
            return result.get('response', '')
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")
    
    return None


def render_prompt_with_context(
    wf_config: WorkflowConfig,
    diff_content: str,
    prompt_template: str
) -> Tuple[str, str]:
    """Render Jinja2 prompt with context injection.
    
    Args:
        wf_config: WorkflowConfig
        diff_content: Git diff content
        prompt_template: Path to prompt template file
        
    Returns:
        Tuple of (full_prompt, base_prompt_for_hashing)
    """
    # Detect languages from diff
    languages = detect_languages(diff_content)
    if wf_config.language:
        languages = [wf_config.language]
    
    # Get historical context (last 3 analyses)
    context_history = []
    try:
        context_history = db_manager.get_context(wf_config.repo_name, limit=3)
    except Exception as e:
        logger.warning(f"Failed to load context history: {e}")
    
    # Render base prompt (without context - for cache key)
    env_vars = {}
    if languages:
        env_vars['CODE_LANGUAGE'] = languages[0]

    base_prompt = render_template(
        template_path=prompt_template,
        diff_content=diff_content,
        repo_name=wf_config.repo_name,
        context_data=[],  # Empty for base
        env_vars=env_vars,
        inject_diff_content=True
    )
    
    # Render full prompt (with context)
    full_prompt = render_template(
        template_path=prompt_template,
        diff_content=diff_content,
        repo_name=wf_config.repo_name,
        context_data=context_history,
        env_vars=env_vars,
        inject_diff_content=True
    )
    
    return full_prompt, base_prompt


def call_llm(
    wf_config: WorkflowConfig,
    prompt: str
) -> str:
    """Call the appropriate LLM based on workflow config.
    
    Args:
        wf_config: WorkflowConfig with workflow_config set
        prompt: The rendered prompt
        
    Returns:
        LLM response
        
    Raises:
        WorkflowError: If LLM call fails
    """
    llm_provider = wf_config.workflow_config.get('llm', 'copilot')
    model = wf_config.workflow_config.get('model', 'gemini-1.5-flash')
    
    try:
        # Use Strategy Pattern for LLM provider selection
        from scripts.llm_strategy import get_provider
        
        provider = get_provider(llm_provider)
        
        if not provider.is_available():
            raise WorkflowError(
                f"LLM provider '{llm_provider}' is not available. "
                f"Check installation and authentication."
            )
        
        logger.info(f"🤖 Calling {llm_provider} ({model})...")
        
        # Call the provider with appropriate parameters
        if llm_provider == 'gh-copilot':
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
        raise WorkflowError(str(e))
    except call_copilot_cli.CopilotNotInstalledError as e:
        raise WorkflowError(f"Copilot CLI not available: {e}")
    except call_copilot_cli.CopilotAuthError as e:
        raise WorkflowError(f"Copilot CLI authentication failed: {e}")
    except Exception as e:
        raise WorkflowError(f"LLM call failed: {e}")


def save_results(
    wf_config: WorkflowConfig,
    diff_content: str,
    full_prompt: str,
    base_prompt: str,
    response: str,
    output_dir: Path
) -> None:
    """Save workflow results to disk and database.
    
    Args:
        wf_config: WorkflowConfig
        diff_content: Git diff content
        full_prompt: Rendered prompt with context
        base_prompt: Rendered prompt without context (for hashing)
        response: LLM response
        output_dir: Directory to save artifacts
    """
    # Save to disk
    output_dir.mkdir(parents=True, exist_ok=True)
    
    (output_dir / "diff.patch").write_text(diff_content, encoding='utf-8')
    (output_dir / "prompt.txt").write_text(full_prompt, encoding='utf-8')
    (output_dir / "prompt_base.txt").write_text(base_prompt, encoding='utf-8')
    
    output_file = output_dir / f"llm_result.{wf_config.output_format}"
    output_file.write_text(response, encoding='utf-8')
    
    logger.info(f"📂 Artifacts saved to: {output_dir}")
    
    # Save to database (if not manual copilot mode)
    if not response.startswith("[COPILOT_MANUAL_MODE]"):
        try:
            diff_hash = hashlib.sha256(diff_content.encode()).hexdigest()
            prompt_hash = hashlib.sha256(base_prompt.encode()).hexdigest()
            model = wf_config.workflow_config.get('model', 'unknown')
            
            db_manager.save_cache(
                diff_hash=diff_hash,
                prompt_hash=prompt_hash,
                model=model,
                response=response,
                repo_name=wf_config.repo_name,
                summary=response[:200] + "...",
                tags=wf_config.workflow
            )
            logger.info("💾 Results saved to database cache")
        except Exception as e:
            logger.warning(f"Failed to save to database: {e}")


def run_workflow(wf_config: WorkflowConfig) -> Dict[str, Any]:
    """Execute the complete workflow.
    
    Args:
        wf_config: WorkflowConfig object
        
    Returns:
        Dictionary with results: 'success', 'output_dir', 'response', etc.
        
    Raises:
        WorkflowError: If workflow fails
    """
    # 1. Load configuration
    load_workflow_config(wf_config)
    
    # 2. Validate repository
    validate_repository(wf_config)
    
    # 3. Determine refs
    target_ref, source_ref = determine_refs(wf_config)
    
    # 4. Generate diff
    token_limit = wf_config.repo_config.get('token_limit')
    diff_content = generate_diff(wf_config, target_ref, source_ref, token_limit)
    
    if not diff_content:
        return {
            'success': True,
            'message': 'No changes detected',
            'output_dir': None,
            'response': None
        }
    
    # 5. Secret scanning
    findings = scan_for_secrets(diff_content)
    if findings:
        logger.warning("⚠️  Secrets detected in diff. Review before sharing.")
    
    # 6. Check cache
    diff_hash = hashlib.sha256(diff_content.encode()).hexdigest()
    prompt_template = wf_config.workflow_config.get('prompt')
    
    if not prompt_template:
        raise WorkflowError(f"Workflow '{wf_config.workflow}' missing 'prompt' field")
    
    # Resolve prompt template path
    prompt_path = PROJECT_ROOT / prompt_template
    if not prompt_path.exists():
        raise WorkflowError(f"Prompt template not found: {prompt_path}")
    
    # 7. Render prompt
    full_prompt, base_prompt = render_prompt_with_context(
        wf_config,
        diff_content,
        str(prompt_path)
    )
    
    prompt_hash = hashlib.sha256(base_prompt.encode()).hexdigest()
    model = wf_config.workflow_config.get('model', 'unknown')
    
    # Check cache
    cached_response = check_cache(diff_hash, prompt_hash, model)
    
    # 8. Prepare output directory
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_dir = PROJECT_ROOT / "output" / f"{timestamp}-{wf_config.repo_name}-{wf_config.workflow}"
    
    # 9. Dry run mode
    if wf_config.dry_run:
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
            'estimated_tokens': estimated_tokens
        }
    
    # 10. Use cache or call LLM
    if cached_response:
        response = cached_response
    else:
        response = call_llm(wf_config, full_prompt)
    
    # 11. Save results
    save_results(
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
        'cached': cached_response is not None
    }


def main():
    """Command-line entry point (for direct invocation)."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Git Diff RAG Orchestrator')
    parser.add_argument('--repo', required=True, help='Repository name')
    parser.add_argument('--workflow', help='Workflow to execute')
    parser.add_argument('--target', help='Target ref for diff')
    parser.add_argument('--source', help='Source ref for diff')
    parser.add_argument('--commit', help='Analyze specific commit')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run mode')
    parser.add_argument('--output-format', '-o', default='markdown', choices=['markdown', 'json'])
    parser.add_argument('--language', help='Force specific language')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    wf_config = WorkflowConfig(
        repo_name=args.repo,
        workflow=args.workflow,
        target_ref=args.target,
        source_ref=args.source,
        commit=args.commit,
        dry_run=args.dry_run,
        output_format=args.output_format,
        language=args.language,
        debug=args.debug
    )
    
    try:
        result = run_workflow(wf_config)
        
        if result['success']:
            print(f"\n{'=' * 80}")
            print("✅ Workflow Completed Successfully")
            print(f"{'=' * 80}")
            if result.get('output_dir'):
                print(f"📂 Artifacts: {result['output_dir']}")
            if result.get('dry_run'):
                print(f"📊 Estimated tokens: ~{result.get('estimated_tokens', 0)}")
        
        sys.exit(0)
        
    except WorkflowError as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
