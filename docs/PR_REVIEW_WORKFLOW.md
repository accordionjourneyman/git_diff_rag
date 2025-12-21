# PR Review Workflow Guide

Comprehensive guide for using the automated PR review system with Azure DevOps and VS Code Copilot.

> **⭐ NEW:** Looking to self-review your code before creating a PR? See the [Commit Mode Guide](COMMIT_MODE_GUIDE.md) for self-review workflows.

## Table of Contents
- [Setup](#setup)
- [Quick Start](#quick-start)
- [Detailed Usage](#detailed-usage)
- [Bundle Contents](#bundle-contents)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Advanced Usage](#advanced-usage)
- [Custom Commit Ranges](#custom-commit-ranges)
- [Commit Mode vs PR Mode](#commit-mode-vs-pr-mode)

---

## Setup

### One-Time Configuration

#### 0. Safety Notice

**All scripts use READ-ONLY git operations only.** The automation performs a self-check on startup to ensure no destructive commands are present.

**Safe operations used:**
- ✅ `git fetch origin` - Downloads refs but doesn't modify working tree
- ✅ `git rev-parse` - Reads commit/branch information
- ✅ `git merge-base` - Finds common ancestor (read-only)
- ✅ `git diff` - Generates diffs (read-only)
- ✅ `git log` - Reads commit history (read-only)
- ✅ `git status` - Reads working tree status (read-only)
- ✅ `git remote get-url` - Reads remote config (read-only)

**Never used (blocked by safety check):**
- ❌ `git push`, `git pull`, `git merge`, `git rebase`
- ❌ `git commit`, `git add`, `git rm`
- ❌ `git stash`, `git reset`, `git checkout` (modifying)
- ❌ `git clean`, `git branch -d`, any destructive operations

#### 1. Configure Azure DevOps Personal Access Token

1. Go to Azure DevOps: `https://dev.azure.com/{your-org}/_usersSettings/tokens`
2. Create a new Personal Access Token with:
   - **Name**: PR Review Automation
   - **Scope**: Code (Read)
   - **Expiration**: Set based on your organization's policy
3. Copy the generated token (you'll need it next)

#### 2. Create Environment File

1. Navigate to `pr-review-tools/` directory
2. Copy the template:
   ```powershell
   cd pr-review-tools
   Copy-Item .env.template .env
   ```
3. Edit `.env` with your values:
   ```bash
   ADO_PAT=your_pat_here
   ADO_ORG=your_org_name
   ADO_PROJECT=your_project_name
   PR_TARGET_BRANCH=origin/main
   ```

#### 3. Verify Git Credential Manager

Ensure your git credential manager is configured for Azure DevOps:
```powershell
git config --global credential.helper manager-core
```

This allows git commands to use your existing Azure DevOps authentication.

---

## Quick Start

### Option 1: VS Code Tasks (Recommended)

1. Press `Ctrl+Shift+P` to open Command Palette
2. Type and select: `Tasks: Run Task`
3. Choose: `PR Review: Generate Bundle`
4. Enter:
   - **PR URL or ID**: Full URL or just the PR number
   - **Repository**: `example_repo`
   - **Target Branch**: Press Enter for default (`origin/main`)
5. Wait for bundle generation (Terminal will show progress)
6. Note the output bundle path (e.g., `pr-reviews/example_repo-12345-20251219T143022`)
7. Run task: `PR Review: Analyze with Copilot`
8. Enter the bundle path when prompted
9. Follow on-screen instructions to paste prompt into Copilot Chat

### Option 2: PowerShell Scripts

**Generate Bundle:**
```powershell
cd pr-review-tools

# Full PR URL
.\New-PRReviewBundle.ps1 `
  -PRUrl "https://dev.azure.com/org/project/_git/repo/pullrequest/12345" `
  -RepoPath "example_repo"

# Or just PR ID (uses org/project from .env)
.\New-PRReviewBundle.ps1 `
  -PRUrl "12345" `
  -RepoPath "example_repo" `
  -TargetBranch "origin/develop"
```

**Analyze with Copilot:**
```powershell
.\Invoke-CopilotReview.ps1 `
  -BundlePath "../pr-reviews/example_repo-12345-20251219T143022"
```

---

## Detailed Usage

### Understanding the Bundle Generation Process

The `New-PRReviewBundle.ps1` script performs the following steps:

1. **Load Environment**: Reads `.env` file for Azure DevOps credentials
2. **Parse PR URL**: Extracts org, project, repo, and PR ID
3. **Validate Repository**: Checks that the specified repo path exists
4. **Git Operations**:
   - Fetches latest from remote: `git fetch origin`
   - Gets current branch and commit info
   - Generates diff statistics vs target branch
   - Exports full diff patch
   - Lists changed files
   - Captures recent commit history
5. **API Calls**:
   - Fetches PR metadata (title, description, author, dates)
   - Retrieves all comment threads and discussions
6. **Acceptance Criteria**: Copies repo-specific criteria from `acceptance-criteria/`
7. **Validation**:
   - For reporting repositories: runs optional reporting validation (if a validation script is present)
     - Validates JSON syntax in `.pbir` and `.json` files
     - Checks semantic model references resolve correctly
     - Validates TMDL files are not corrupted
     - Checks resource file integrity
   - For `example_repo`: (Future) Will run Python/DBT validation
8. **Bundle Assembly**: Creates timestamped folder with all outputs
9. **Failure Handling**: 
   - Exits with error if no diff content found
   - Exits with error if critical validation failures occur

### Using Copilot for Review

After running `Invoke-CopilotReview.ps1`, you'll get a comprehensive prompt template designed to guide Copilot through a thorough analysis.

#### Persist the Review (Mandatory)

Copilot Chat output is ephemeral. Every review must be persisted inside the bundle folder as Markdown so it can be referenced later.

After Copilot generates the review, save it to `peer_review.md` inside the same bundle:

- Bash:
   ```bash
   cd pr_checker
   ./pr-review-tools/Save-PeerReview.sh --bundle pr-reviews/<your-bundle>
   ```

- PowerShell:
   ```powershell
   cd pr_checker
   .\pr-review-tools\Save-PeerReview.ps1 -BundlePath "pr-reviews/<your-bundle>"
   ```

**What Copilot Analyzes:**
- **Intent**: What the PR is trying to accomplish
- **Acceptance Criteria**: Whether each criterion is met with evidence
- **Validation Results**: Automated checks and their outcomes
- **Code Quality**: Pythonic/DAX practices, DRY principle, conventions
- **Architecture**: Design patterns, layering, maintainability
- **Risks**: Data correctness, performance, breaking changes, security
- **Testing**: Recommended tests and edge cases to verify
- **Questions**: Clarifications needed from the author

**Follow-up Questions You Can Ask Copilot:**
- "Can you analyze the DAX measures in detail?"
- "What are the specific performance concerns in the SQL changes?"
- "Are there any security vulnerabilities in the new API endpoints?"
- "Can you suggest unit tests for the new functions?"
- "Is the star schema properly implemented?"

---

## Bundle Contents

Each PR review bundle is a self-contained folder with the following structure:

```
pr-reviews/
└── {repo}-{PR_ID}-{timestamp}/
    ├── README.txt                  # Guide to bundle contents
    ├── pr_url.txt                  # Original PR URL
    ├── pr_metadata.json            # Full PR data from API
    ├── pr_threads.json             # Comment threads (raw JSON)
    ├── pr_title.txt                # Extracted PR title
    ├── pr_description.md           # Extracted PR description
    ├── pr_comments.txt             # Formatted comments
    ├── branch_info.txt             # Current branch/commit info
    ├── diff_stat.txt               # Summary of changes
    ├── diff.patch                  # Full git diff
    ├── changed_files.txt           # List of changed files
    ├── commits.txt                 # Recent commit history (50 commits)
    ├── status.txt                  # Git working tree status
    ├── acceptance.md               # Repo-specific criteria
    ├── validation_report.txt       # Automated validation results
    └── copilot_prompt.txt          # Generated Copilot prompt
```

### Key Files Explained

**pr_metadata.json**
Contains complete PR information:
- Title, description, author, reviewers
- Source and target branches
- Creation and update timestamps
- Status (active, completed, abandoned)
- Merge status and strategy

**diff.patch**
Full unified diff format showing:
- Added lines (prefixed with `+`)
- Removed lines (prefixed with `-`)
- Context lines (unchanged)
- File paths and line numbers

**validation_report.txt**
Automated checks results:
- JSON syntax validation
- Semantic model reference integrity
- TMDL file corruption checks
- Resource file validation
- Summary of passes, failures, warnings

---

## Troubleshooting

### Common Issues

#### Error: "ADO_PAT not found"
**Cause**: `.env` file missing or PAT not set

**Solution**:
1. Check `.env` file exists in `pr-review-tools/`
2. Verify `ADO_PAT=` line has your token (no spaces around `=`)
3. Ensure token has "Code (Read)" permissions

#### Error: "Could not parse PR URL"
**Cause**: Invalid URL format

**Solution**:
- Use format: `https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}`
- Or just use PR ID number (e.g., `12345`) if org/project set in `.env`

#### Error: "No changes detected between HEAD and origin/main"
**Cause**: Branch not checked out or not up to date

**Solution**:
1. Ensure you're on the PR branch: `git checkout feature-branch`
2. Fetch latest: `git fetch origin`
3. Verify target branch exists: `git branch -r | grep origin/main`

#### Error: "Repository path not found"
**Cause**: Incorrect `-RepoPath` parameter

**Solution**:
- Use relative path from workspace root: `example_repo` or `example_repo`
- Check folder actually exists in workspace

#### Validation Failures

**Broken Semantic Model References**
- Check that `.SemanticModel` folders exist for all report references
- Verify relative paths in `definition.pbir` files
- Ensure semantic models weren't deleted in the PR

**Invalid JSON**
- Open affected files and check for syntax errors
- Use VS Code JSON validation (red squiggles)
- Validate manually: `Get-Content file.json | ConvertFrom-Json`

**Corrupted TMDL Files**
- Check file encoding (should be UTF-8)
- Look for binary data or special characters
- Re-export from reporting Desktop if needed

#### PowerShell Execution Policy

**Error**: "script cannot be loaded because running scripts is disabled"

**Solution**:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Or run scripts with bypass:
```powershell
pwsh -ExecutionPolicy Bypass -File .\New-PRReviewBundle.ps1 ...
```

---

## Best Practices

### When to Run PR Review

1. **Before requesting team review** - Catch obvious issues early
2. **After addressing review comments** - Verify fixes are complete
3. **Before merging** - Final check for quality and completeness
4. **For learning** - Review your own PRs to improve coding practices

### Optimizing the Review Process

1. **Keep PRs Small**: Easier to review, faster feedback
   - Target: < 500 lines changed
   - Single logical change per PR

2. **Write Good PR Descriptions**:
   - Explain the "why", not just the "what"
   - Reference tickets/issues
   - Note breaking changes explicitly
   - Include testing performed

3. **Address Validation Failures First**:
   - Fix broken references before asking for review
   - Ensure all JSON/TMDL files are valid
   - Run validation locally: Task `PR Review: Validate reporting Only`

4. **Customize Acceptance Criteria**:
   - Update `acceptance-criteria/{repo}.md` as team standards evolve
   - Add project-specific requirements
   - Document common pitfalls to avoid

5. **Iterate on Copilot Findings**:
   - Ask follow-up questions for clarity
   - Request alternative implementations
   - Use Copilot to generate test cases

### Managing Bundle History

Bundles are timestamped to preserve history:
- Compare reviews over time to see improvement
- Track common issues across PRs
- Learn from past mistakes

**Cleanup old bundles**:
```powershell
# Delete bundles older than 30 days
Get-ChildItem pr-reviews -Recurse -Directory |
  Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Recurse -Force
```

---

## Advanced Usage

### Custom Target Branch

For feature branches or different workflows:
```powershell
.\New-PRReviewBundle.ps1 `
  -PRUrl "12345" `
  -RepoPath "example_repo" `
  -TargetBranch "origin/develop"
```

### Batch Review Multiple PRs

Create a script to review multiple PRs:
```powershell
$prs = @(12345, 12346, 12347)
foreach ($pr in $prs) {
    .\New-PRReviewBundle.ps1 -PRUrl $pr -RepoPath "example_repo"
}
```

### Integration with CI/CD

Add to Azure Pipelines:
```yaml
- task: PowerShell@2
  displayName: 'Generate PR Review Bundle'
  inputs:
    targetType: 'filePath'
    filePath: 'pr-review-tools/New-PRReviewBundle.ps1'
    arguments: '-PRUrl "$(System.PullRequest.PullRequestId)" -RepoPath "example_repo"'
```

### Custom Validation Scripts

For `example_repo`, create `Test-PythonBackend.ps1`:
```powershell
[CmdletBinding()]
param(
    [string]$RepoPath,
    [string[]]$ChangedFiles,
    [string]$OutputFile
)

# Your custom validation logic
# - Check PEP 8 compliance with flake8
# - Run mypy for type checking
# - Validate SQL formatting
# - Check for DBT model dependencies
# - etc.

# Write results to $OutputFile
# Exit 1 for critical failures, 0 for success
```

Update `New-PRReviewBundle.ps1` to call your script:
```powershell
if ($RepoPath -eq "example_repo" -and (Test-Path $backendValidationScript)) {
    & $backendValidationScript -RepoPath $repoFullPath -ChangedFiles $diffInfo.Files -OutputFile $validationOutput
}
```

### Automated PR Comments (Future Enhancement)

Post review results back to Azure DevOps:
```powershell
# Example: Post validation results as PR comment
$comment = Get-Content $validationOutput -Raw
$body = @{ content = $comment } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "$orgUrl/$project/_apis/git/repositories/$repo/pullRequests/$prId/threads?api-version=7.1" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

---

## Acceptance Criteria Templates

### Reporting validation (optional)

Located at: `acceptance-criteria/example_repo.md`

**Key Areas**:
- Artifact integrity (JSON, TMDL, references)
- Naming conventions
- DAX best practices
- Visual design consistency
- Documentation requirements

**Customize for Your Team**:
- Add specific measure naming patterns
- Define required documentation sections
- Add visual design standards
- Specify performance requirements (query folding, etc.)

### Data Pipelines (example_repo)

Located at: `acceptance-criteria/example_repo.md`

**Key Areas**:
- Code quality (PEP 8, DRY, type hints)
- Pipeline architecture (raw/modeled/views layers)
- Star schema compliance
- SQL quality standards
- Testing requirements
- Documentation standards

**Customize for Your Team**:
- Add DBT-specific guidelines
- Define model naming conventions
- Specify data quality test requirements
- Add lineage documentation standards

---

## Workflow Examples

### Example 1: Frontend Report Changes

```powershell
# 1. Generate bundle
cd pr-review-tools
.\New-PRReviewBundle.ps1 -PRUrl "12345" -RepoPath "example_repo"

# Output: pr-reviews/example_repo-12345-20251219T143022

# 2. Quick check of validation
Get-Content ../pr-reviews/example_repo-12345-20251219T143022/validation_report.txt

# 3. Analyze with Copilot
.\Invoke-CopilotReview.ps1 -BundlePath "../pr-reviews/example_repo-12345-20251219T143022"

# 4. Follow Copilot's instructions, paste prompt, review analysis
```

### Example 2: Backend Pipeline Changes

```powershell
# Same workflow, different repo
.\New-PRReviewBundle.ps1 -PRUrl "12346" -RepoPath "example_repo"
.\Invoke-CopilotReview.ps1 -BundlePath "../pr-reviews/example_repo-12346-20251219T150000"

# Copilot will use example_repo acceptance criteria automatically
```

### Example 3: Review Against Feature Branch

```powershell
# When PR targets a feature branch instead of main
.\New-PRReviewBundle.ps1 `
  -PRUrl "12347" `
  -RepoPath "example_repo" `
  -TargetBranch "origin/feature-v2"
```

## Custom Commit Ranges

You can now specify exact commit ranges for generating the diff, allowing for flexible reviews beyond the standard "main vs HEAD" comparison.

### CLI Arguments

- `--target <ref>`: The base reference (e.g., `main`, `origin/develop`, `v1.0`).
  - **Default**: Derived from `repository-setup` config (`remote` + `main_branch`).
  - **Behavior**: Replaces the left side of the diff (`target...source`).

- `--source <ref>`: The tip reference containing changes (e.g., `feature-branch`, `HEAD`, `sha123`).
  - **Default**: `HEAD`
  - **Behavior**: Replaces the right side of the diff (`target...source`).

### Examples

**Compare a feature branch against `develop`:**
```bash
./scripts/New-Bundle.sh --repo myrepo --target origin/develop --source feature-branch
```

**Review the last 3 commits on the current branch:**
```bash
./scripts/New-Bundle.sh --repo myrepo --target HEAD~3 --source HEAD
```

**Compare two specific tags:**
```bash
./scripts/New-Bundle.sh --repo myrepo --target v1.0.0 --source v1.1.0
```

**Analyze a specific commit (Blame Mode):**
```bash
./scripts/New-Bundle.sh --repo myrepo --commit 8f3a2b1
```
*This is equivalent to `--target 8f3a2b1~1 --source 8f3a2b1`*

### Blame Analysis Recipe

Use the `blame` workflow to conduct a critical post-mortem analysis of a specific commit or range. This recipe focuses on identifying root causes, skill gaps, and accountability.

```bash
./scripts/New-Bundle.sh --repo myrepo --workflow blame --commit <bad-commit-sha>
```

---

## Commit Mode vs PR Mode

This guide focuses on **PR Mode** - analyzing existing Azure DevOps Pull Requests.

For **Commit Mode** (self-review before creating PRs), see the dedicated [Commit Mode Guide](COMMIT_MODE_GUIDE.md).

### Quick Comparison

| Feature | PR Mode | Commit Mode |
|---------|---------|-------------|
| **Purpose** | Team review of existing PRs | Self-review before PR creation |
| **Azure DevOps** | ✅ Fetches PR metadata | ❌ Skipped (no PR needed) |
| **Setup Required** | ✅ .env with ADO_PAT | ❌ No .env needed |
| **Command** | `-PRUrl <PR-ID>` | `-CommitRef <branch-or-commit>` |
| **Use Case** | Formal peer review | Early validation & self-check |

**Examples:**

```powershell
# PR Mode (this guide)
.\New-PRReviewBundle.ps1 -PRUrl "12345" -RepoPath "example_repo"

# Commit Mode (see other guide)
.\New-PRReviewBundle.ps1 -CommitRef "HEAD" -RepoPath "example_repo"
```

---

## Support & Contribution

### Getting Help

1. Check this documentation first
2. Review [Troubleshooting](#troubleshooting) section
3. Check script output for specific error messages
4. Run with verbose output: Add `-Verbose` to script calls

### Improving the System

1. **Update Acceptance Criteria**: As standards evolve
2. **Add Validation Rules**: Enhance validation scripts
3. **Create Templates**: Add Copilot prompt variations
4. **Share Findings**: Document common issues in criteria files

### Script Locations

- Main scripts: `pr-review-tools/`
- Acceptance criteria: `acceptance-criteria/`
- Generated bundles: `pr-reviews/`
- VS Code tasks: `.vscode/tasks.json`
- Documentation: `docs/`

---

## Summary

The PR review automation system provides:
- ✅ Automated bundle generation from Azure DevOps PRs
- ✅ Git-based diff analysis (no complex API dependencies)
- ✅ Repository-specific validation (reporting, Python, etc.)
- ✅ Copilot-assisted comprehensive reviews
- ✅ Structured acceptance criteria
- ✅ Historical bundle tracking
- ✅ VS Code task integration

Start reviewing better PRs today! 🚀
