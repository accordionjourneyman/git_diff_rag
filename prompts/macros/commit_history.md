{% if COMMIT_HISTORY and COMMIT_HISTORY.total_count > 0 %}
<commit_context>

## Commit History ({{ COMMIT_HISTORY.total_count }} commits)

Comparing `{{ TARGET_REF }}` → `{{ SOURCE_REF }}`

{% if COMMIT_HISTORY.tier1 %}

### Recent Commits (Full Detail)

{% for commit in COMMIT_HISTORY.tier1 %}
**{{ loop.index }}. {{ commit.subject }}**

- SHA: `{{ commit.hash }}` | Author: {{ commit.author }} | {{ commit.date }}
  {% if commit.body %}

```
{{ commit.body }}
```

{% endif %}

{% endfor %}
{% endif %}

{% if COMMIT_HISTORY.tier2 %}

### Earlier Commits (Summary)

| #   | SHA | Date | Subject |
| --- | --- | ---- | ------- |

{% for commit in COMMIT_HISTORY.tier2 %}
| {{ loop.index + 10 }} | `{{ commit.hash }}` | {{ commit.date }} | {{ commit.subject }} |
{% endfor %}
{% endif %}

{% if COMMIT_HISTORY.truncated_count > 0 %}

> ℹ️ {{ COMMIT_HISTORY.truncated_count }} additional commits excluded for context optimization.
> {% endif %}
> </commit_context>
> {% endif %}
