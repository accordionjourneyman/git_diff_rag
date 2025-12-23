# Prompt Library

This directory contains the Jinja2 templates used to generate prompts for the LLM.

## Structure

- **`recipes/`**: Ready-to-use workflows. These are the entry points referenced in your `repository-setup/*.md` files.
    - `standard_pr_review.md`: A robust code review workflow.
    - `agentic_workspace_map.md`: Generates a structured JSON map of changes.
    - `comprehensive_review.md`: A 360-degree review using multiple library modules.
    - `explain_diff.md`: Simple explanation for non-technical stakeholders.

- **`library/`**: Atomic modules that can be mixed and matched in recipes.
    - **`security/`**: `vulnerabilities.md`, `pii.md`, `iac.md`
    - **`quality/`**: `performance.md`, `tests.md`, `typing.md`, `breaking_changes.md`
    - **`ops/`**: `changelog.md`, `migrations.md`
    - **`documentation/`**: `pr_description.md`

- **`macros/`**: Reusable logic and formatting helpers.
    - `_common.md`: Handles the "Language Triad" (Code/Answer/Comment languages).
    - `secret_scan.md`: The pre-flight security warning.
    - `json_formatting.md`: Standard JSON output schema.

- **`legacy/`**: Old prompts from previous versions (kept for reference).

## Creating a New Recipe

Create a new `.md` file in `recipes/` and use Jinja2 includes to compose it:

```markdown
{% include 'macros/_common.md' %}

<instructions>
Review this code for security issues only.
</instructions>

<security_check>
{% include 'library/security/vulnerabilities.md' %}
</security_check>

<diff_context>
{{ DIFF_CONTENT }}
</diff_context>
```
