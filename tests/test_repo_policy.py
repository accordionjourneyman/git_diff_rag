import subprocess
import os
from pathlib import Path

def test_gitignore_policy():
    """Ensure local repository specs are ignored, but templates are not."""
    repo_root = Path(__file__).parent.parent
    
    # Files that should be ignored
    ignored_files = [
        "repository-setup/my-local-repo.md",
        "repository-setup/accordion-practice-tracker.md",
        "repository-setup/another_project.md"
    ]
    
    # Files that should NOT be ignored
    tracked_files = [
        "repository-setup/TEMPLATE.md",
        "repository-setup/examples/demo-app.md"
    ]
    
    # Check ignored files
    for file in ignored_files:
        # git check-ignore returns 0 if ignored, 1 if not
        result = subprocess.run(
            ["git", "check-ignore", "-q", file],
            cwd=repo_root
        )
        assert result.returncode == 0, f"{file} should be ignored by git"

    # Check tracked files
    for file in tracked_files:
        result = subprocess.run(
            ["git", "check-ignore", "-q", file],
            cwd=repo_root
        )
        assert result.returncode == 1, f"{file} should NOT be ignored by git"
