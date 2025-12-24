"""Main orchestration module for Git Diff RAG workflows.

This module replaces New-Bundle.sh, providing Python-native workflow execution
with cross-platform compatibility and better error handling.
"""

import os
import sys
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import config_utils, db_manager
from scripts.diff_engine import (
    is_valid_repository, is_clean_working_directory, determine_refs,
    get_diff, GitError
)
from scripts.prompt_builder import build_prompt_with_context, detect_languages
from scripts.execution_engine import (
    execute_workflow_step, scan_for_secrets, ExecutionError, LLMError
)

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


class ConfigError(WorkflowError):
    """Raised when configuration is invalid."""
    pass


class GitError(WorkflowError):
    """Raised when git operations fail."""
    pass


class LLMError(WorkflowError):
    """Raised when LLM operations fail."""
    pass


@dataclass(frozen=True)
class WorkflowConfig:
    """Immutable configuration for a single workflow execution.
    
    This dataclass is frozen (immutable) to ensure:
    - Job Safety: Config cannot be accidentally modified during execution
    - Auditability: Config can be serialized and stored with each analysis
    - Reproducibility: Historical analyses can be replayed with exact config
    
    Use with_updates() to create a new config with modified values.
    """
    # Core settings (from user input)
    repo_name: str
    workflow: Optional[str] = None
    target_ref: Optional[str] = None
    source_ref: Optional[str] = None
    commit: Optional[str] = None
    dry_run: bool = False
    output_format: str = 'markdown'
    language: Optional[str] = None
    debug: bool = False
    llm: Optional[str] = None
    model: Optional[str] = None
    
    # Loaded from config file (populated by load_workflow_config)
    repo_config: Dict[str, Any] = field(default_factory=dict)
    repo_path: str = ""
    main_branch: str = "main"
    remote: str = "origin"
    workflow_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize config to JSON for storage/auditability."""
        import json
        # Convert to dict, handling non-serializable types
        data = {
            'repo_name': self.repo_name,
            'workflow': self.workflow,
            'target_ref': self.target_ref,
            'source_ref': self.source_ref,
            'commit': self.commit,
            'dry_run': self.dry_run,
            'output_format': self.output_format,
            'language': self.language,
            'debug': self.debug,
            'llm': self.llm,
            'model': self.model,
            'repo_path': self.repo_path,
            'main_branch': self.main_branch,
            'remote': self.remote,
            # Don't include repo_config/workflow_config - they're large and derived
        }
        return json.dumps(data, indent=2, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WorkflowConfig':
        """Deserialize config from JSON."""
        import json
        data = json.loads(json_str)
        return cls(**data)
    
    def with_updates(self, **kwargs) -> 'WorkflowConfig':
        """Create a new config with updated values (immutable pattern)."""
        from dataclasses import replace
        return replace(self, **kwargs)


def load_workflow_config(wf_config: WorkflowConfig) -> WorkflowConfig:
    """Load repository and workflow configuration from YAML file.
    
    Args:
        wf_config: WorkflowConfig object with repo_name set
        
    Returns:
        New WorkflowConfig with loaded settings (immutable pattern)
        
    Raises:
        WorkflowError: If config file not found or invalid
    """
    setup_file = PROJECT_ROOT / "repository-setup" / f"{wf_config.repo_name}.md"
    
    if not setup_file.exists():
        raise WorkflowError(f"Repository setup file not found: {setup_file}")
    
    repo_config = config_utils.load_repo_config(wf_config.repo_name)
    
    if not repo_config:
        raise WorkflowError(f"Failed to parse config from {setup_file}")
    
    # Extract core settings
    repo_path = repo_config.get('path', '')
    main_branch = repo_config.get('main_branch', 'main')
    remote = repo_config.get('remote', 'origin')
    
    # Determine workflow
    workflow = wf_config.workflow or repo_config.get('default_workflow', 'pr_review')
    
    # Load workflow-specific config
    workflow_config = repo_config.get(workflow, {})
    
    if not workflow_config:
        raise WorkflowError(
            f"Workflow '{workflow}' not defined in {setup_file}"
        )
    
    # Create new immutable config with loaded settings
    loaded_config = wf_config.with_updates(
        workflow=workflow,
        repo_config=repo_config,
        repo_path=repo_path,
        main_branch=main_branch,
        remote=remote,
        workflow_config=workflow_config
    )
    
    logger.info(f"Target: {loaded_config.repo_name} ({loaded_config.repo_path})")
    logger.info(f"Workflow: {loaded_config.workflow}")
    logger.info(f"Mode: {'DRY RUN' if loaded_config.dry_run else 'LIVE'}")
    
    return loaded_config


def validate_repository(wf_config: WorkflowConfig) -> None:
    """Validate that repository exists and is in clean state.
    
    Args:
        wf_config: WorkflowConfig with repo_path set
        
    Raises:
        GitError: If repository invalid or has uncommitted changes
    """
    if not is_valid_repository(wf_config.repo_path):
        raise GitError(f"Not a git repository: {wf_config.repo_path}")
    
    is_clean, status = is_clean_working_directory(wf_config.repo_path)
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
    from scripts.diff_engine import determine_refs as determine_refs_func
    target, source = determine_refs_func(
        wf_config.target_ref,
        wf_config.source_ref,
        wf_config.commit,
        wf_config.remote,
        wf_config.main_branch
    )
    logger.info(f"Generating git diff: {target}...{source}")
    return target, source


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
        diff_content = get_diff(
            wf_config.repo_path,
            target_ref,
            source_ref,
            stat_only=False
        )
    except GitError as e:
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
            diff_content = get_diff(
                wf_config.repo_path,
                target_ref,
                source_ref,
                stat_only=True
            )
    
    return diff_content








def run_workflow(wf_config: WorkflowConfig) -> Dict[str, Any]:
    """Execute the complete workflow.
    
    Args:
        wf_config: WorkflowConfig object
        
    Returns:
        Dictionary with results: 'success', 'output_dir', 'response', etc.
        
    Raises:
        WorkflowError: If workflow fails
    """
    # 1. Load configuration (returns new immutable config)
    wf_config = load_workflow_config(wf_config)
    
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
    
    # 6. Get prompt template
    prompt_template = wf_config.workflow_config.get('prompt')
    if not prompt_template:
        raise WorkflowError(f"Workflow '{wf_config.workflow}' missing 'prompt' field")
    
    # Resolve prompt template path
    prompt_path = PROJECT_ROOT / prompt_template
    if not prompt_path.exists():
        raise WorkflowError(f"Prompt template not found: {prompt_path}")
    
    # 7. Execute workflow step (LLM call, caching, results)
    wf_config_dict = {
        'repo_name': wf_config.repo_name,
        'workflow': wf_config.workflow,
        'model': wf_config.model or wf_config.workflow_config.get('model', 'unknown'),
        'llm': wf_config.llm or wf_config.workflow_config.get('llm', 'copilot'),
        'dry_run': wf_config.dry_run,
        'output_format': wf_config.output_format,
    }
    
    result = execute_workflow_step(
        wf_config_dict,
        diff_content,
        str(prompt_path),
        target_ref=target_ref,
        source_ref=source_ref
    )
    
    return result


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
