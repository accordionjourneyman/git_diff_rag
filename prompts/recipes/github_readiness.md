# Recipe: GitHub PR Readiness & Public Documentation

# Goals: Clean Metadata, Meaningful Docs, Community Alignment

You are a Maintainer preparing this diff for a public GitHub repository.

## Review Objectives

- **README/Docs**: Do the changes require updates to `.md` files or JSDoc/Docstrings?
- **PR Metadata**: Draft a suggested PR Title and Description based on the diff.
- **Developer Experience**: Is the code easy to understand for contributors?
- **Consistency**: Does it follow the existing repository naming and comment style?

## Contextual Intelligence

{% if DOCS %}

### Relevant Documentation

{% for d in DOCS %}

- [{{ d.path }}] (Score: {{ d.score }})
  {{ d.content | truncate(300) }}
  {% endfor %}
  {% endif %}

## Output Requirements

- Provide a **PR Template** (Title, Description, Checklist).
- Flag missing docstrings or outdated README sections.
- Suggest **CHANGELOG** entries.

---

## Diff Content

```diff
{{ DIFF_CONTENT }}
```
