"""End-to-end tests for LLM workflows."""
import pytest
import subprocess
import os
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
PROJECT_ROOT = Path(__file__).parent.parent

class TestOutputValidation:
    """Tests for validate_output.py script."""
    
    def test_valid_json_array(self, tmp_path):
        output_file = tmp_path / "result.md"
        output_file.write_text('''
Here are the API calls:
```json
[
  {"method": "POST", "endpoint": "/api/sessions", "body": {"name": "test"}}
]
```
''')
        result = subprocess.run(
            ["python3", str(SCRIPT_DIR / "validate_output.py"), str(output_file)],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "[OK] Valid JSON" in result.stdout
    
    def test_invalid_json(self, tmp_path):
        output_file = tmp_path / "result.md"
        output_file.write_text("This is not JSON at all")
        
        result = subprocess.run(
            ["python3", str(SCRIPT_DIR / "validate_output.py"), str(output_file)],
            capture_output=True, text=True
        )
        assert "[ERROR] Invalid JSON" in result.stdout
    
    def test_strict_mode_fails(self, tmp_path):
        output_file = tmp_path / "result.md"
        output_file.write_text("Invalid content")
        
        result = subprocess.run(
            ["python3", str(SCRIPT_DIR / "validate_output.py"), str(output_file), "--strict"],
            capture_output=True, text=True
        )
        assert result.returncode == 1

class TestGeminiE2E:
    """End-to-end tests for Gemini workflow (mocked)."""
    
    def test_gemini_workflow_with_mock(self, tmp_path, mock_git_repo):
        """Test full workflow with mocked Gemini response."""
        repo_name = "pytest_gemini_e2e"
        config_path = PROJECT_ROOT / "repository-setup" / f"{repo_name}.md"
        
        # Clone to have origin
        client_repo = tmp_path / "client"
        subprocess.run(["git", "clone", str(mock_git_repo), str(client_repo)], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=client_repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=client_repo, check=True)
        subprocess.run(["git", "checkout", "-b", "feature"], cwd=client_repo, check=True)
        (client_repo / "data.json").write_text('{"key": "value"}')
        subprocess.run(["git", "add", "."], cwd=client_repo, check=True)
        subprocess.run(["git", "commit", "-m", "add data"], cwd=client_repo, check=True)
        
        try:
            # Create config for Gemini workflow but use copilot to avoid API call
            config_path.write_text(f"""---
name: {repo_name}
path: {client_repo}
default_workflow: test_extract

workflows:
  - test_extract

test_extract:
  prompt: prompts/legacy/data_extraction.md
  llm: copilot
---
""")
            
            result = subprocess.run(
                [str(PROJECT_ROOT / "scripts" / "New-Bundle.sh"), "--repo", repo_name],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True
            )
            
            assert result.returncode == 0
            # Extract output dir from stdout
            import re
            match = re.search(r"Workflow Completed: (output/\S+)", result.stdout)
            assert match, f"Could not find output dir in stdout: {result.stdout}"
            res_file = PROJECT_ROOT / match.group(1) / "llm_result.md"
            assert res_file.exists()
            assert "Copilot workflow" in res_file.read_text()
            
        finally:
            if config_path.exists():
                config_path.unlink()

class TestCLIHelp:
    """Tests for CLI --help flag."""
    
    def test_help_flag(self):
        result = subprocess.run(
            [str(PROJECT_ROOT / "scripts" / "New-Bundle.sh"), "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "USAGE:" in result.stdout
        assert "--repo" in result.stdout
        assert "--mode" in result.stdout
        assert "--agent" in result.stdout
        assert "--apply" in result.stdout
        assert "EXAMPLES:" in result.stdout
    
    def test_short_help_flag(self):
        result = subprocess.run(
            [str(PROJECT_ROOT / "scripts" / "New-Bundle.sh"), "-h"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Git Diff RAG" in result.stdout
    
    def test_agent_dry_run(self, mock_git_repo, tmp_path):
        repo_name = "test_agent_dry_run"
        config_path = PROJECT_ROOT / "repository-setup" / f"{repo_name}.md"
        config_path.write_text(f"""---\npath: {mock_git_repo}\ndefault_workflow: review\n---""")
        
        try:
            result = subprocess.run(
                [str(PROJECT_ROOT / "scripts" / "New-Bundle.sh"), "--repo", repo_name, "--mode", "agent", "--dry-run", "--target", "HEAD"],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True
            )
            assert result.returncode == 0
            assert "Mode: agent" in result.stdout
            assert "Agent: gemini" in result.stdout
        finally:
            if config_path.exists(): config_path.unlink()
