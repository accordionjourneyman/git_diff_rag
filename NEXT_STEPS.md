# Git Diff RAG - Next Steps & Testing Guide

## Overview

The git_diff_rag tool has been modernized with:
- ✅ Python-first architecture (replacing bash orchestration)
- ✅ GitHub Copilot CLI integration
- ✅ Cross-platform support (Windows, macOS, Linux)
- ✅ Streamlit UI with Copilot CLI option

This document outlines required testing and future enhancements.

---

## 1. Prerequisites Verification

### GitHub Copilot CLI Installation

The tool expects GitHub Copilot CLI to be installed and authenticated:

```powershell
# Check if installed
copilot --version

# If not installed, follow:
# https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli

# Authenticate (will open browser)
copilot
```

**Expected:** User should already have Copilot CLI installed and configured with GitHub account.

### Python Dependencies

Install optional clipboard support:

```powershell
pip install pyperclip
```

Or on Windows, for better clipboard integration:

```powershell
pip install pywin32
```

---

## 2. End-to-End Testing Plan

### Test 1: Basic Workflow (Dry Run)

**Objective:** Verify Python orchestrator works without calling LLM

```powershell
cd C:\Users\tiago.marques\Documents\fabric\git_diff_rag

# Test with dry run
python cli.py analyze --repo <your-repo> --dry-run

# Expected output:
# - Config loads successfully
# - Git diff generated
# - Prompt rendered
# - Estimated token count shown
# - Files saved to output/ directory
```

**Success criteria:**
- No errors
- Output directory created with prompt.txt
- Token estimation displayed

---

### Test 2: Gemini API Workflow

**Objective:** Verify existing Gemini integration still works

```powershell
# Ensure GEMINI_API_KEY is set
$env:GEMINI_API_KEY = "your-key"

# Run analysis
python cli.py analyze --repo <your-repo> --workflow pr_review

# Expected output:
# - Analysis completes
# - Results saved to output/
# - Database cache updated
```

**Success criteria:**
- Gemini API called successfully
- Response saved to llm_result.markdown
- Cache entry created in data/history.sqlite

---

### Test 3: GitHub Copilot CLI Integration

**Objective:** Verify new Copilot CLI integration

**Setup:** Ensure repository config uses `gh-copilot`:

```yaml
# repository-setup/<repo>.md
---
path: /path/to/repo
workflows:
  - pr_review

pr_review:
  prompt: prompts/recipes/standard_pr_review.md
  llm: gh-copilot  # <-- Use this
  model: claude-sonnet-4.5
---
```

**Test:**

```powershell
# Check Copilot CLI is working
python cli.py check-setup

# Run analysis
python cli.py analyze --repo <your-repo>

# Expected output:
# - Copilot CLI called with prompt
# - Response returned and saved
# - Works on native Windows (no WSL needed)
```

**Success criteria:**
- Copilot CLI authenticates
- Analysis completes with Claude Sonnet 4.5
- Results saved properly

---

### Test 4: Manual Copilot Mode (Clipboard)

**Objective:** Verify clipboard fallback still works

**Setup:** Use `llm: copilot` in config (manual mode)

```powershell
python cli.py analyze --repo <your-repo>

# Expected output:
# - Prompt copied to clipboard
# - Instructions shown to paste into Copilot Chat
# - Prompt file saved
```

**Success criteria:**
- Clipboard copy succeeds (Windows native)
- User can paste into VS Code Copilot Chat
- Manual workflow still supported

---

### Test 5: Streamlit UI with Copilot CLI

**Objective:** Verify UI integration

```powershell
# Launch Streamlit
streamlit run cockpit/app.py

# In browser:
# 1. Select repository
# 2. Choose target/source refs
# 3. Go to "Run Analysis" tab
# 4. Select "GitHub Copilot CLI" from Tool dropdown
# 5. Click "LAUNCH ANALYSIS"
```

**Success criteria:**
- Copilot CLI appears in dropdown
- Analysis executes without subprocess errors
- Results display in UI
- No bash dependency

---

### Test 6: Cross-Platform Git Operations

**Objective:** Verify git_operations.py works on Windows

```powershell
# Test git operations directly
python -c "from scripts.git_operations import *; print(get_branches('.'))"

# Test diff generation
python -c "from scripts.git_operations import *; print(get_diff('.', 'main', 'HEAD')[:100])"
```

**Success criteria:**
- Git commands execute via subprocess
- Windows paths handled correctly
- No bash/WSL required

---

## 3. Unit Tests to Add

### Test Files to Create

**tests/test_git_operations.py:**

```python
import pytest
from scripts.git_operations import *

def test_is_valid_repository(tmp_path):
    # Test with non-repo
    assert not is_valid_repository(str(tmp_path))
    
    # Test with valid repo (requires git init in fixture)
    # ...

def test_get_diff_basic():
    # Mock git command execution
    # ...
```

**tests/test_clipboard.py:**

```python
import pytest
from scripts.clipboard import *

def test_clipboard_availability():
    # Should return True on all platforms
    result = is_clipboard_available()
    assert isinstance(result, bool)

def test_copy_to_clipboard():
    # Test basic copy (may fail in CI without display)
    # ...
```

**tests/test_call_copilot_cli.py:**

```python
import pytest
from scripts.call_copilot_cli import *

def test_is_copilot_installed():
    result = is_copilot_installed()
    assert isinstance(result, bool)

def test_copilot_not_installed_error(monkeypatch):
    # Mock subprocess to simulate missing copilot
    # ...
```

**tests/test_orchestrator.py:**

```python
import pytest
from scripts.orchestrator import *

def test_workflow_config_creation():
    config = WorkflowConfig(
        repo_name="test-repo",
        dry_run=True
    )
    assert config.repo_name == "test-repo"
    assert config.dry_run == True

def test_load_workflow_config_missing_file():
    config = WorkflowConfig(repo_name="nonexistent")
    with pytest.raises(WorkflowError):
        load_workflow_config(config)
```

### Run Tests

```powershell
# Install pytest if needed
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=scripts --cov-report=html
```

---

## 4. Bash Script Testing (Optional)

**Note:** Bash script testing is now optional since they're just wrappers.

If testing on Linux/macOS:

```bash
# Test deprecated wrapper
./scripts/New-Bundle.sh --repo <repo> --dry-run

# Should show deprecation notice and delegate to Python
```

**Expected:** Deprecation warning shown, then Python CLI executes.

---

## 5. Windows Native Testing Checklist

**Critical: Verify NO WSL/Git Bash dependency:**

- [ ] Run in native PowerShell (not Git Bash, not WSL)
- [ ] Git operations work (subprocess to git.exe)
- [ ] Clipboard works (PowerShell Set-Clipboard or pywin32)
- [ ] Copilot CLI calls work (native copilot.exe)
- [ ] Paths with backslashes handled correctly
- [ ] No bash scripts invoked

**Test command:**

```powershell
# In native PowerShell (not bash)
python cli.py check-setup

# All components should show ✓ or ⚠️ with clear instructions
```

---

## 6. Documentation Updates Needed

### README.md

Update to show Python CLI:

```markdown
## Quick Start

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Check setup:
   ```
   python cli.py check-setup
   ```

3. Run analysis:
   ```
   python cli.py analyze --repo myrepo
   ```
```

### TOOLS.md

Add Python CLI documentation:

```markdown
## 🐍 Python CLI

### `cli.py`

**Description:** Modern Python CLI replacing bash scripts.

**Commands:**
- `analyze`: Run analysis workflow
- `explain`: Explain changes (wrapper for explain_diff)
- `list-models`: Show available AI models
- `check-setup`: Verify installation
- `list-repos`: Show configured repositories

**Examples:**
```bash
python cli.py analyze --repo myrepo --dry-run
python cli.py explain --repo myrepo --commit abc123
python cli.py list-models
```
```

---

## 7. Known Limitations

### Copilot CLI Model Selection

- **Issue:** Programmatic mode (`copilot -p`) doesn't expose model listing API
- **Current:** Returns hardcoded default (Claude Sonnet 4.5)
- **Workaround:** Users can change model in interactive session with `/model`
- **Future:** When GitHub adds API, update `call_copilot_cli.get_available_models()`

### Token Counting for Copilot

- **Issue:** No token counting API in Copilot CLI
- **Current:** Rough estimate (4 chars = 1 token)
- **Impact:** Token pruning less accurate
- **Workaround:** Rely on Copilot's built-in limits

### Clipboard on Headless Systems

- **Issue:** Clipboard requires display server on Linux
- **Current:** Gracefully fails with warning
- **Workaround:** Manual file copy in CI/server environments

---

## 8. Future Enhancements

### High Priority

1. **Add pyperclip to requirements.txt**
   - Optional dependency with graceful fallback
   - Better cross-platform clipboard support

2. **VS Code Extension Integration**
   - Right-click on diff → "Analyze with Git Diff RAG"
   - Results in Copilot Chat panel
   - No CLI needed

3. **Automated Tests in CI**
   - GitHub Actions workflow
   - Test matrix: Windows, macOS, Linux
   - Mock LLM calls for fast testing

### Medium Priority

4. **PowerShell Module (Optional)**
   - For Windows users who prefer PowerShell
   - Import-Module GitDiffRag
   - `Invoke-GitDiffAnalysis -Repo myrepo`

5. **Configuration Wizard**
   - `python cli.py init` to create repo config interactively
   - Validates paths and git setup
   - Tests LLM authentication

6. **Result Comparison**
   - Compare Gemini vs Copilot outputs
   - Side-by-side diff of recommendations
   - Quality metrics

### Low Priority

7. **MCP Server Implementation**
   - Expose git_diff_rag as Model Context Protocol server
   - Works with Claude Desktop, VS Code Copilot, etc.
   - Future-proof AI agent integration

8. **GitHub Action**
   - Automated PR reviews
   - Post results as PR comments
   - Integration with GitHub Checks API

---

## 9. Rollback Plan

If Python migration causes issues:

1. **Revert bash scripts:**
   ```bash
   git checkout HEAD~1 scripts/New-Bundle.sh scripts/explain.sh
   ```

2. **Remove Python modules:**
   - Keep existing call_gemini.py, db_manager.py, etc.
   - Remove new orchestrator.py, git_operations.py, clipboard.py

3. **Revert Streamlit UI:**
   ```bash
   git checkout HEAD~1 cockpit/app.py
   ```

**Note:** This should not be necessary - Python modules are additive and bash wrappers preserve backward compatibility.

---

## 10. Success Criteria Summary

Implementation is successful when:

- ✅ `python cli.py check-setup` passes on Windows
- ✅ Gemini API workflow still works
- ✅ GitHub Copilot CLI integration executes
- ✅ Streamlit UI shows Copilot CLI option
- ✅ No WSL/Git Bash required on Windows
- ✅ Bash wrappers work for backward compatibility
- ✅ All core tests pass

**Next Action:** Begin with Test 1 (Basic Workflow) and work through the testing plan.

---

## Contact & Support

- **Documentation:** Check ARCHITECTURE.md, TOOLS.md, COCKPIT.md
- **Issues:** Review test output and error messages
- **Debugging:** Use `--debug` flag for verbose output

**Happy Testing! 🚀**
