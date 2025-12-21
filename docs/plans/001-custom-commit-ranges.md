# Feature Plan: Custom Commit Ranges for Diff Generation

## Objective
Enable users to specify exact commit ranges (source and target) for generating the diff, rather than relying solely on the configured main branch and current HEAD. This allows for reviewing specific commits, historical states, or arbitrary branch comparisons.

## CLI Interface Changes

New optional arguments for `scripts/New-Bundle.sh`:

- `--target <ref>`: The base reference (e.g., `main`, `origin/develop`, `v1.0`).
  - **Default**: Derived from `repository-setup` config (`remote` + `main_branch`).
  - **Behavior**: Replaces the left side of the diff (`target...source`).

- `--source <ref>`: The tip reference containing changes (e.g., `feature-branch`, `HEAD`, `sha123`).
  - **Default**: `HEAD`
  - **Behavior**: Replaces the right side of the diff (`target...source`).

## Logic Flow

1. **Determine Target (Base)**:
   - If `--target` is passed: Use it directly.
   - Else: Construct from config (`$REMOTE/$MAIN_BRANCH` or `$MAIN_BRANCH`).

2. **Determine Source (Tip)**:
   - If `--source` is passed: Use it directly.
   - Else: Use `HEAD`.

3. **Generate Diff**:
   - Command: `git diff "$TARGET...$SOURCE"`
   - Note: We will use the triple-dot syntax `...` (merge base) by default as it is safer for PR reviews, but we might consider if double-dot `..` is needed for specific commit-to-commit comparisons. For now, `...` is standard for "what changed in source since it diverged from target".

## Documentation Updates

1. **`scripts/New-Bundle.sh`**: Update `show_help()` and `usage()`.
2. **`README.md`**: Add examples of comparing specific branches.
3. **`docs/PR_REVIEW_WORKFLOW.md`**: Add a section on "Advanced Usage: Custom Comparisons".

## Verification Plan

1. **Default Behavior**: Run without args, ensure it still diffs `origin/main...HEAD`.
2. **Custom Target**: Run with `--target dev`, ensure diff is `dev...HEAD`.
3. **Custom Source**: Run with `--source HEAD~1`, ensure diff is `origin/main...HEAD~1`.
4. **Both**: Run with `--target main --source feature`, ensure diff is `main...feature`.
