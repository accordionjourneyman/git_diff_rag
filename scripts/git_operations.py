"""Git operations wrapper module.

Provides a clean Python interface to git commands, replacing bash git operations
from New-Bundle.sh. All operations are read-only for safety.
"""

import subprocess
from typing import Optional, Tuple
from pathlib import Path


class GitOperationError(Exception):
    """Raised when a git operation fails."""
    pass


def run_git_command(repo_path: str, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in the specified repository.
    
    Args:
        repo_path: Path to the git repository
        args: Git command arguments (without 'git' prefix)
        check: Whether to raise exception on non-zero exit code
        
    Returns:
        CompletedProcess object with stdout, stderr, and returncode
        
    Raises:
        GitOperationError: If command fails and check=True
    """
    cmd = ['git', '-C', repo_path] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        if check and result.returncode != 0:
            raise GitOperationError(f"Git command failed: {' '.join(args)}\n{result.stderr}")
        return result
    except FileNotFoundError:
        raise GitOperationError("Git executable not found. Please ensure git is installed and in PATH.")


def get_diff(repo_path: str, target_ref: str, source_ref: str, 
             stat_only: bool = False) -> str:
    """Generate git diff between two refs.
    
    Args:
        repo_path: Path to the git repository
        target_ref: Base reference (e.g., 'main', 'origin/main')
        source_ref: Feature reference (e.g., 'HEAD', 'feature-branch')
        stat_only: If True, return only --stat summary (for token pruning)
        
    Returns:
        Git diff output as string
    """
    args = ['diff']
    if stat_only:
        args.append('--stat')
    args.append(f'{target_ref}...{source_ref}')
    
    result = run_git_command(repo_path, args)
    return result.stdout


def get_commit_diff(repo_path: str, commit_sha: str) -> str:
    """Get diff for a specific commit.
    
    Args:
        repo_path: Path to the git repository
        commit_sha: Commit SHA to analyze
        
    Returns:
        Git diff output showing changes in the commit
    """
    args = ['show', '--format=', commit_sha]
    result = run_git_command(repo_path, args)
    return result.stdout


def resolve_ref(repo_path: str, ref: str) -> str:
    """Resolve a git reference to its full SHA.
    
    Args:
        repo_path: Path to the git repository
        ref: Reference to resolve (branch name, tag, HEAD, etc.)
        
    Returns:
        Full commit SHA
        
    Raises:
        GitOperationError: If reference cannot be resolved
    """
    result = run_git_command(repo_path, ['rev-parse', ref])
    return result.stdout.strip()


def fetch_remote(repo_path: str, remote: str = 'origin') -> None:
    """Fetch latest changes from remote.
    
    Args:
        repo_path: Path to the git repository
        remote: Remote name (default: 'origin')
    """
    run_git_command(repo_path, ['fetch', remote])


def get_current_branch(repo_path: str) -> str:
    """Get the name of the current branch.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Branch name or empty string if detached HEAD
    """
    result = run_git_command(repo_path, ['rev-parse', '--abbrev-ref', 'HEAD'], check=False)
    branch = result.stdout.strip()
    return branch if branch != 'HEAD' else ''


def is_clean_working_directory(repo_path: str) -> Tuple[bool, str]:
    """Check if working directory is clean.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Tuple of (is_clean: bool, status_output: str)
    """
    result = run_git_command(repo_path, ['status', '--porcelain'], check=False)
    status = result.stdout.strip()
    return len(status) == 0, status


def get_branches(repo_path: str, remote: bool = True) -> list[str]:
    """List available branches.
    
    Args:
        repo_path: Path to the git repository
        remote: If True, include remote branches
        
    Returns:
        List of branch names
    """
    args = ['branch']
    if remote:
        args.append('-a')
    
    result = run_git_command(repo_path, args, check=False)
    branches = []
    for line in result.stdout.split('\n'):
        line = line.strip()
        if line:
            # Remove '* ' prefix from current branch
            if line.startswith('* '):
                line = line[2:]
            # Remove 'remotes/' prefix
            if line.startswith('remotes/'):
                line = line[8:]
            if line and '->' not in line:  # Skip symbolic refs
                branches.append(line)
    
    return sorted(set(branches))


def get_commits(repo_path: str, ref: str, limit: int = 10) -> list[dict]:
    """Get recent commits for a reference.
    
    Args:
        repo_path: Path to the git repository
        ref: Git reference (branch, tag, etc.)
        limit: Maximum number of commits to return
        
    Returns:
        List of commit dictionaries with 'hash', 'author', 'date', 'message'
    """
    args = ['log', f'--max-count={limit}', '--format=%H%x00%an%x00%ai%x00%s', ref]
    result = run_git_command(repo_path, args, check=False)
    
    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\x00')
        if len(parts) == 4:
            commits.append({
                'hash': parts[0],
                'author': parts[1],
                'date': parts[2],
                'message': parts[3]
            })
    
    return commits


def is_valid_repository(repo_path: str) -> bool:
    """Check if the path is a valid git repository.
    
    Args:
        repo_path: Path to check
        
    Returns:
        True if valid git repository, False otherwise
    """
    try:
        result = run_git_command(repo_path, ['rev-parse', '--git-dir'], check=False)
        return result.returncode == 0
    except GitOperationError:
        return False


def get_repository_root(repo_path: str) -> str:
    """Get the root directory of the git repository.
    
    Args:
        repo_path: Path within a git repository
        
    Returns:
        Absolute path to repository root
    """
    result = run_git_command(repo_path, ['rev-parse', '--show-toplevel'])
    return result.stdout.strip()


def get_commits_between(repo_path: str, target_ref: str, source_ref: str,
                        tier1_limit: int = 10, tier2_limit: int = 50,
                        body_max_chars: int = 500) -> dict:
    """Get commits between two refs with tiered density.
    
    Uses the "Density vs. Horizon" rule:
    - Tier 1 (1-10): Full metadata (author, date, subject, body, truncated flag)
    - Tier 2 (11-50): One-line summary only (hash, date, subject)
    - Tier 3 (50+): Excluded entirely
    
    Args:
        repo_path: Path to the git repository
        target_ref: Base reference (e.g., 'main')
        source_ref: Feature reference (e.g., 'HEAD')
        tier1_limit: Full detail for first N commits (default: 10)
        tier2_limit: One-line summary for commits up to N (default: 50)
        body_max_chars: Max chars for commit body before truncation (default: 500)
        
    Returns:
        Dictionary with:
        - 'tier1': List of full commit dicts
        - 'tier2': List of summary commit dicts
        - 'total_count': Total commits in range
        - 'truncated_count': Number of commits excluded (beyond tier2_limit)
    """
    # Format: hash, author, date, subject, body (separated by null bytes)
    # Use record separator (0x1E) between commits to handle multi-line bodies
    args = ['log', '--format=%H%x00%an%x00%ai%x00%s%x00%b%x1E', 
            f'{target_ref}..{source_ref}']
    result = run_git_command(repo_path, args, check=False)
    
    if result.returncode != 0:
        return {
            'tier1': [],
            'tier2': [],
            'total_count': 0,
            'truncated_count': 0
        }
    
    all_commits = []
    for entry in result.stdout.split('\x1E'):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split('\x00')
        if len(parts) >= 4:
            body = parts[4].strip() if len(parts) > 4 else ''
            is_truncated = len(body) > body_max_chars
            all_commits.append({
                'hash': parts[0][:8],  # Short SHA
                'full_hash': parts[0],  # Keep full hash for reference
                'author': parts[1],
                'date': parts[2].split()[0],  # Date only, no time
                'subject': parts[3],
                'body': body[:body_max_chars] + (' [...Truncated for Context...]' if is_truncated else ''),
                'truncated': is_truncated
            })
    
    total = len(all_commits)
    
    # Tier 1: Full metadata
    tier1 = all_commits[:tier1_limit]
    
    # Tier 2: Strip to one-line format (remove body and author)
    tier2_raw = all_commits[tier1_limit:tier2_limit]
    tier2 = []
    for commit in tier2_raw:
        tier2.append({
            'hash': commit['hash'],
            'date': commit['date'],
            'subject': commit['subject']
        })
    
    return {
        'tier1': tier1,
        'tier2': tier2,
        'total_count': total,
        'truncated_count': max(0, total - tier2_limit)
    }
