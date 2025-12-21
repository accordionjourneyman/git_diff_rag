# Stacked PR Review (Layer Analysis)

{% include 'library/quality/role_definition.md' %}

## Context
This review targets a specific **layer** in a stacked Pull Request.
The changes below are the delta between the previous layer (base) and this one (tip).

{% include 'macros/context_history.md' %}

## Focus Areas
1. **Integration**: How does this layer interact with the code established in the base?
2. **Isolation**: Does this layer contain only what it claims to? (e.g. no accidental reverts of the base).
3. **Standard Quality**: Security, Performance, Readability.

{% include 'library/quality/style_constructive.md' %}

{% include 'library/quality/code_style.md' %}
{% include 'library/quality/review_checklist.md' %}

## Diff (Layer Changes)
{{ DIFF_CONTENT }}
