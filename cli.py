#!/usr/bin/env python3
"""Git Diff RAG - Command Line Interface

Cross-platform Python CLI for git_diff_rag, replacing bash scripts.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.orchestrator import run_workflow, WorkflowConfig, WorkflowError
from scripts import call_copilot_cli, call_gemini, config_utils
import logging

logger = logging.getLogger(__name__)


def cmd_analyze(args: argparse.Namespace) -> int:
    """Execute analysis workflow.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
    
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
                print(f"\n👉 Review prompt and run without --dry-run to execute")
            elif result.get('message'):
                print(f"ℹ️  {result['message']}")
            else:
                if result.get('cached'):
                    print("⚡ Result from cache")
                print(f"\n👉 Review results in: {result['output_dir']}")
            
            print(f"{'=' * 80}\n")
            return 0
        
        return 1
        
    except WorkflowError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_explain(args: argparse.Namespace) -> int:
    """Execute explain_diff workflow (convenience wrapper).
    
    Returns:
        Exit code
    """
    # Override workflow to explain_diff
    args.workflow = 'explain_diff'
    return cmd_analyze(args)


def cmd_list_models(args: argparse.Namespace) -> int:
    """List available models for each LLM provider.
    
    Returns:
        Exit code
    """
    print("Available Models by Provider:\n")
    
    # Gemini models
    print("🔷 Gemini API:")
    try:
        models = call_gemini.list_models()
        if models:
            for model in models:
                print(f"  • {model}")
        else:
            print("  ⚠️  No models found (check GEMINI_API_KEY)")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print()
    
    # Copilot CLI models
    print("🤖 GitHub Copilot CLI:")
    if call_copilot_cli.is_copilot_installed():
        models = call_copilot_cli.get_available_models()
        for model in models:
            default_marker = " (default)" if model == call_copilot_cli.DEFAULT_MODEL else ""
            print(f"  • {model}{default_marker}")
        print(f"  ℹ️  Model selection via /model in interactive mode")
        print(f"  ℹ️  Programmatic mode uses current session model")
    else:
        print("  ❌ Copilot CLI not installed")
        print("  ℹ️  Install from: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli")
    
    print()
    
    # Manual Copilot (clipboard mode)
    print("📋 Copilot (Manual/Clipboard):")
    print("  • N/A - Uses whatever Copilot Chat model you have access to")
    print("  ℹ️  Prompt is copied to clipboard for manual paste")
    
    return 0


def cmd_check_setup(args: argparse.Namespace) -> int:
    """Check installation and authentication status.
    
    Returns:
        Exit code
    """
    print("Git Diff RAG - Setup Check\n")
    print("=" * 60)
    
    all_ok = True
    
    # Check Git
    print("\n📦 Git:")
    import subprocess
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✓ Installed: {version}")
        else:
            print(f"  ✗ Error checking git")
            all_ok = False
    except:
        print(f"  ✗ Not installed or not in PATH")
        all_ok = False
    
    # Check Python dependencies
    print("\n🐍 Python Dependencies:")
    dependencies = {
        'google-genai': ('google.genai', 'Gemini API'),
        'jinja2': ('jinja2', 'Template engine'),
        'pyyaml': ('yaml', 'Config parsing'),
        'streamlit': ('streamlit', 'Web UI (optional)')
    }
    
    for package, (import_name, description) in dependencies.items():
        try:
            __import__(import_name)
            print(f"  ✓ {package}: {description}")
        except ImportError:
            print(f"  ✗ {package}: {description} - Not installed")
            if package != 'streamlit':  # streamlit is optional
                all_ok = False
    
    # Check Gemini API
    print("\n🔷 Gemini API:")
    import os
    if os.getenv('GEMINI_API_KEY'):
        print(f"  ✓ GEMINI_API_KEY is set")
        try:
            call_gemini.get_client()
            print(f"  ✓ API client initialized successfully")
        except Exception as e:
            print(f"  ✗ API client error: {e}")
            all_ok = False
    else:
        print(f"  ⚠️  GEMINI_API_KEY not set (optional)")
    
    # Check Copilot CLI
    print("\n🤖 GitHub Copilot CLI:")
    if call_copilot_cli.is_copilot_installed():
        print(f"  ✓ Copilot CLI is installed")
        
        if call_copilot_cli.check_authentication():
            print(f"  ✓ Authenticated")
        else:
            print(f"  ⚠️  Not authenticated - run 'copilot' to authenticate")
            print(f"     (This is optional if using other LLM providers)")
    else:
        print(f"  ⚠️  Copilot CLI not installed (optional)")
        print(f"     Install from: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli")
    
    # Check clipboard
    print("\n📋 Clipboard:")
    from scripts import clipboard
    if clipboard.is_clipboard_available():
        print(f"  ✓ Clipboard support available")
    else:
        print(f"  ⚠️  No clipboard tool found (manual mode will require file copy)")
    
    # Summary
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All required components are properly configured!")
    else:
        print("⚠️  Some components need attention (see above)")
        print("   Core functionality may still work depending on your workflow")
    
    return 0 if all_ok else 1


def cmd_list_repos(args: argparse.Namespace) -> int:
    """List configured repositories.
    
    Returns:
        Exit code
    """
    from scripts import ui_utils
    
    repos = ui_utils.list_repositories()
    
    if not repos:
        print("No repositories configured.")
        print(f"\nAdd repository configs to: {PROJECT_ROOT / 'repository-setup'}/")
        return 1
    
    print("Configured Repositories:\n")
    for repo in repos:
        config = config_utils.load_repo_config(repo)
        if config:
            path = config.get('path', 'N/A')
            workflows = config.get('workflows', [])
            default_wf = config.get('default_workflow', 'N/A')
            
            print(f"📁 {repo}")
            print(f"   Path: {path}")
            print(f"   Default workflow: {default_wf}")
            print(f"   Available workflows: {', '.join(workflows)}")
            print()
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='git-diff-rag',
        description='Git Diff RAG - AI-powered code review and analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze current changes
  python cli.py analyze --repo myrepo
  
  # Dry run validation
  python cli.py analyze --repo myrepo --dry-run
  
  # Analyze specific commit
  python cli.py analyze --repo myrepo --commit abc123
  
  # Explain changes in plain language
  python cli.py explain --repo myrepo
  
  # Check setup
  python cli.py check-setup
  
  # List available models
  python cli.py list-models

For more information: https://github.com/your-org/git_diff_rag
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze git diff with AI',
        description='Execute an analysis workflow on a git diff'
    )
    analyze_parser.add_argument('--repo', required=True, help='Repository name')
    analyze_parser.add_argument('--workflow', help='Workflow to execute (default from config)')
    analyze_parser.add_argument('--target', help='Target ref for diff (base)')
    analyze_parser.add_argument('--source', help='Source ref for diff (tip)')
    analyze_parser.add_argument('--commit', help='Analyze specific commit')
    analyze_parser.add_argument('--language', help='Force specific language context')
    analyze_parser.add_argument('--dry-run', '-n', action='store_true', help='Validate without calling LLM')
    analyze_parser.add_argument('--output-format', '-o', choices=['markdown', 'json'], default='markdown')
    analyze_parser.add_argument('--debug', action='store_true', help='Enable debug output')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Explain command (convenience)
    explain_parser = subparsers.add_parser(
        'explain',
        help='Explain changes in plain language',
        description='Convenience wrapper for explain_diff workflow'
    )
    explain_parser.add_argument('--repo', required=True, help='Repository name')
    explain_parser.add_argument('--target', help='Target ref for diff')
    explain_parser.add_argument('--source', help='Source ref for diff')
    explain_parser.add_argument('--commit', help='Analyze specific commit')
    explain_parser.add_argument('--dry-run', '-n', action='store_true', help='Validate without calling LLM')
    explain_parser.add_argument('--debug', action='store_true', help='Enable debug output')
    explain_parser.set_defaults(func=cmd_explain, workflow='explain_diff', output_format='markdown', language=None)
    
    # List models command
    models_parser = subparsers.add_parser(
        'list-models',
        help='List available AI models',
        description='Show available models for each LLM provider'
    )
    models_parser.set_defaults(func=cmd_list_models)
    
    # Check setup command
    check_parser = subparsers.add_parser(
        'check-setup',
        help='Verify installation and configuration',
        description='Check that all dependencies and credentials are properly configured'
    )
    check_parser.set_defaults(func=cmd_check_setup)
    
    # List repos command
    repos_parser = subparsers.add_parser(
        'list-repos',
        help='List configured repositories',
        description='Show all repositories configured in repository-setup/'
    )
    repos_parser.set_defaults(func=cmd_list_repos)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
