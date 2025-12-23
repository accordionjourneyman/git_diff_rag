Read the PR review bundle at: {{BUNDLE_PATH}}

Follow these steps:

1. **Start with README.txt** to understand the bundle structure
2. **Read pr_title.txt, pr_description.md, pr_comments.txt** for PR context
3. **Review repository-setup.md** (formerly acceptance.md) for validation criteria
4. **Check validation_report.txt** for automated findings
5. **Analyze diff.patch and changed_files.txt** for the actual changes

Provide a comprehensive PR review with the following structure:

## Intent Summary

[What is this PR trying to accomplish? Extract from title/description/comments]

## Acceptance Criteria Checklist

[For each criterion in repository-setup.md, provide:]

- ✓ Met | ✗ Not Met | ? Unclear
- Evidence: specific file paths from changed_files.txt
- Notes: explain why/how the criterion is addressed

## Automated Validation Findings

[Summarize validation_report.txt:]

- Highlight any critical issues
- Note warnings that need human attention
- Confirm all automated checks passed

## Code Quality Assessment

[Based on acceptance criteria and diff.patch:]

- **Pythonic/DAX Best Practices**: Are coding standards followed?
- **DRY Principle**: Any code duplication?
- **Proper Layering**: (For backend) Raw/Modeled/Views separation correct?
- **Star Schema**: (If applicable) Proper fact/dimension structure?
- **Naming Conventions**: Consistent and clear?
- **Documentation**: Code comments, docstrings adequate?

## Architecture & Design Review

- Does the change align with existing patterns?
- Are there better alternative approaches?
- Scalability considerations?
- Maintainability concerns?

## Risks & Concerns

- **Data Correctness**: Could this cause incorrect results?
- **Performance**: Any potential bottlenecks or inefficiencies?
- **Breaking Changes**: Backwards compatibility issues?
- **Security**: Any vulnerabilities introduced?
- **Dependencies**: New external dependencies added?

## Testing & Validation Recommendations

[Specific tests that should be run:]

- Unit tests needed
- Integration tests
- Edge cases to verify
- Data quality checks
- Manual testing steps

## Questions for Author

[Clarifications needed about:]

- Design decisions
- Implementation choices
- Scope of changes
- Future plans

## Approval Recommendation

**Status**: [APPROVE | REQUEST CHANGES | NEEDS DISCUSSION]

**Reasoning**: [Brief explanation of recommendation]

**Blocking Issues**: [List any must-fix items]

**Optional Improvements**: [Nice-to-have suggestions]

---

## Persist the Review (Mandatory)

After you generate the review in Copilot Chat, save it into the bundle for long-term context:

- File: {{BUNDLE_PATH}}/peer_review.md
- Command (optional helper):
  .\scripts\Save-PeerReview.ps1 -BundlePath "{{BUNDLE_PATH}}"

---

Be thorough but concise. Use evidence from the bundle files. Quote relevant code snippets when needed.
