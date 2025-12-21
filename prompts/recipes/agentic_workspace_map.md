{% include 'macros/_common.md' %}

<!-- NOTE: Verify model-specific context window and JSON output behavior when changing the `model` in repository setup. -->

<instructions>
You are an intelligent agent analyzing a software repository.
Your goal is to create a structured map of the changes in this diff to help understand the intent and scope.
</instructions>

<output_format>
You MUST strictly output valid JSON. Do not return markdown, do not wrap in `json` blocks. Just the raw JSON object.
Follow this schema:
{
  "summary": "High level summary of changes",
  "impact_analysis": {
    "breaking_changes": boolean,
    "security_risks": boolean,
    "affected_components": ["list", "of", "components"]
  },
  "suggested_actions": ["list", "of", "actions"]
}
</output_format>

<diff_context>
{{ DIFF_CONTENT }}
</diff_context>
