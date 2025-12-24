"""Git Diff Engine - Consolidated Git Operations Module.

This module consolidates all git operations from orchestrator.py and ui_utils.py
into a single, focused module for diff generation, ref management, and repository
analysis. Provides a clean interface for tiered commit history and file change detection.
"""

import subprocess
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Raised when git operations fail."""
    def __init__(self, message: str, repo_path: str = None, command: str = None):
        self.repo_path = repo_path
        self.command = command
        super().__init__(f"{message} (repo: {repo_path}, cmd: {command})")


def run_git_command(repo_path: str, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in the specified repository.

    Args:
        repo_path: Path to the git repository
        args: Git command arguments (without 'git' prefix)
        check: Whether to raise exception on non-zero exit code

    Returns:
        CompletedProcess object with stdout, stderr, and returncode

    Raises:
        GitError: If command fails and check=True
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
            raise GitError(f"Git command failed: {' '.join(args)}", repo_path, ' '.join(cmd))
        return result
    except FileNotFoundError:
        raise GitError("Git executable not found. Please ensure git is installed and in PATH.", repo_path)


def is_valid_repository(repo_path: str) -> bool:
    """Check if the given path is a valid git repository.

    Args:
        repo_path: Path to check

    Returns:
        True if valid git repository
    """
    try:
        result = run_git_command(repo_path, ['rev-parse', '--git-dir'])
        return result.returncode == 0
    except GitError:
        return False


def is_clean_working_directory(repo_path: str) -> Tuple[bool, str]:
    """Check if working directory is clean (no uncommitted changes).

    Args:
        repo_path: Path to git repository

    Returns:
        Tuple of (is_clean, status_output)
    """
    result = run_git_command(repo_path, ['status', '--porcelain'], check=False)
    status = result.stdout.strip()
    return status == '', status


def get_branches(repo_path: str) -> List[str]:
    """Get all local and remote branches for a repository.

    Args:
        repo_path: Path to git repository

    Returns:
        List of branch names, sorted with priority branches first
    """
    try:
        result = run_git_command(repo_path, ['branch', '-a', '--format=%(refname:short)'])
        branches = list(set([b.strip() for b in result.stdout.splitlines() if b.strip()]))
        # Priority sort: HEAD, main, master first
        priority = ['HEAD', 'main', 'master', 'origin/main', 'origin/master']
        branches.sort(key=lambda x: (priority.index(x) if x in priority else 999, x))
        return branches
    except GitError:
        return ["main"]


def get_commits(repo_path: str, ref: str, limit: int = 20) -> List[Dict[str, str]]:
    """Get list of recent commits for a reference with full metadata.

    Args:
        repo_path: Path to git repository
        ref: Git reference (branch, tag, commit)
        limit: Maximum number of commits to return

    Returns:
        List of commit dictionaries with hash, date, author, message, label
    """
    try:
        delimiter = "|||"
        result = run_git_command(repo_path, [
            'log', ref, '-n', str(limit),
            '--date=iso',
            f'--format=%h{delimiter}%ad{delimiter}%an{delimiter}%s'
        ])

        commits = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split(delimiter)
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0],
                    "date": parts[1],
                    "author": parts[2],
                    "message": parts[3],
                    "label": f"{parts[0]} - {parts[3]} ({parts[1]})"
                })
        return commits
    except GitError as e:
        logger.error(f"Error fetching commits: {e}")
        return []


def determine_refs(target_ref: Optional[str], source_ref: Optional[str],
                  commit: Optional[str], remote: str, main_branch: str) -> Tuple[str, str]:
    """Determine target and source refs for diff generation.

    Args:
        target_ref: Explicit target ref
        source_ref: Explicit source ref
        commit: Specific commit to analyze
        remote: Remote name (e.g., 'origin')
        main_branch: Main branch name (e.g., 'main')

    Returns:
        Tuple of (target_ref, source_ref)
    """
    # Determine target (base)
    if target_ref:
        target = target_ref
    elif commit:
        target = f"{commit}~1"
    else:
        target = f"{remote}/{main_branch}"

    # Determine source (tip)
    if source_ref:
        source = source_ref
    elif commit:
        source = commit
    else:
        source = "HEAD"

    return target, source


def get_smart_refs(repo_path: str, target: str, source: str,
                  target_commit: Optional[str] = None,
                  source_commit: Optional[str] = None) -> Tuple[str, str, bool]:
    """Intelligently determine refs for diff generation.

    If specific commits are provided, use direct comparison (..).
    If only branches are provided, use merge-base comparison (...).

    Args:
        repo_path: Path to git repository
        target: Target ref
        source: Source ref
        target_commit: Specific target commit
        source_commit: Specific source commit

    Returns:
        Tuple of (final_target, final_source, is_direct_comparison)
    """
    if source == "Working Directory":
        final_target = target_commit if target_commit and target_commit != "None" else target
        return final_target, None, True

    final_target = target_commit if target_commit and target_commit != "None" else target
    final_source = source_commit if source_commit and source_commit != "None" else source

    # Use ".." for direct A->B diff if either is a specific commit
    # Use "..." for A...B (diff from merge-base) for branches
    is_direct = (target_commit and target_commit != "None") or (source_commit and source_commit != "None")

    if final_target == final_source:
        branches = get_branches(repo_path)
        base = "main" if "main" in branches else ("master" if "master" in branches else target)
        return base, "HEAD", False  # False means use ... for branches
    return final_target, final_source, is_direct


def get_diff(repo_path: str, target_ref: str, source_ref: str,
             stat_only: bool = False) -> str:
    """Generate git diff between two refs.

    Args:
        repo_path: Path to git repository
        target_ref: Target reference (base)
        source_ref: Source reference (tip)
        stat_only: If True, return only diff --stat output

    Returns:
        Diff output as string

    Raises:
        GitError: If diff generation fails
    """
    if stat_only:
        args = ['diff', '--stat', target_ref, source_ref]
    else:
        args = ['diff', target_ref, source_ref]

    result = run_git_command(repo_path, args)
    return result.stdout


def get_changed_files(repo_path: str, target: str, source: str,
                     target_commit: Optional[str] = None,
                     source_commit: Optional[str] = None) -> List[str]:
    """Get list of files changed between target and source.

    Args:
        repo_path: Path to git repository
        target: Target ref
        source: Source ref
        target_commit: Specific target commit
        source_commit: Specific source commit

    Returns:
        List of changed file paths
    """
    t, s, is_direct = get_smart_refs(repo_path, target, source, target_commit, source_commit)

    cmd = ["diff", "--name-only"]
    if s is None:
        cmd.append(t)
    else:
        sep = ".." if is_direct else "..."
        cmd.append(f"{t}{sep}{s}")

    try:
        result = run_git_command(repo_path, cmd)
        return [f for f in result.stdout.splitlines() if f.strip()]
    except GitError as e:
        logger.error(f"Error getting changed files: {e}")
        return []


def get_tiered_commit_history(repo_path: str, target_ref: str, source_ref: str,
                             max_commits: int = 50) -> List[Dict[str, Any]]:
    """Get tiered commit history between two refs.

    Returns commits in hierarchical tiers based on branch structure.

    Args:
        repo_path: Path to git repository
        target_ref: Target reference
        source_ref: Source reference
        max_commits: Maximum commits to return

    Returns:
        List of commit dictionaries with tier information
    """
    try:
        # Get merge-base to understand branch structure
        merge_base_result = run_git_command(repo_path, ['merge-base', target_ref, source_ref])
        merge_base = merge_base_result.stdout.strip()

        # Get commits from merge-base to source
        commits = get_commits(repo_path, f"{merge_base}..{source_ref}", max_commits)

        # Add tier information (simplified - could be enhanced with branch analysis)
        for commit in commits:
            commit['tier'] = 1  # Default tier

        return commits
    except GitError as e:
        logger.error(f"Error getting tiered history: {e}")
        return []