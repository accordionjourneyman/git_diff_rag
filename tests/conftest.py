import pytest
import subprocess
from pathlib import Path

@pytest.fixture
def mock_git_repo(tmp_path):
    """Create a minimal git repo for testing."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    # Init repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    
    # Initial commit
    (repo_dir / "file.txt").write_text("initial")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "branch", "-m", "main"], cwd=repo_dir, check=True) # Ensure main branch
    
    return repo_dir
