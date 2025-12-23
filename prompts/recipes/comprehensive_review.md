{% include 'macros/_common.md' %}

<!-- NOTE: This comprehensive recipe aggregates multiple modules; verify model limits (context window, response length) when changing `model`. -->

<instructions>
You are performing a comprehensive 360-degree review of the provided git diff.
Your goal is to identify critical issues across Security, Quality, and Operations.
</instructions>

<security_review>
{% include 'library/security/vulnerabilities.md' %}
{% include 'library/security/pii.md' %}
{% include 'library/security/iac.md' %}
</security_review>

<quality_review>
{% include 'library/quality/breaking_changes.md' %}
{% include 'library/quality/performance.md' %}
{% include 'library/quality/typing.md' %}
</quality_review>

<ops_review>
{% include 'library/ops/migrations.md' %}
</ops_review>

<output_format>
Please structure your response as follows:

## 🛡️ Security Audit
(Findings from security review)

## 💎 Code Quality
(Findings from quality review)

## ⚙️ Operational Impact
(Findings from ops review)

## 📝 Summary & Recommendations
(Overall verdict)
</output_format>

<diff_context>
{{ DIFF_CONTENT }}
</diff_context>
