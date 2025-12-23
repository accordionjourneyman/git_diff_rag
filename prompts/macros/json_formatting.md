<output_format>
You MUST strictly output valid JSON. Do not return markdown, do not wrap in `json` blocks. Just the raw JSON object.
Follow this schema:
{
"summary": "High-level summary of changes...",
"issues": [
{
"type": "security|bug|quality|style",
"severity": "critical|high|medium|low",
"file": "filename",
"line": 123,
"description": "...",
"suggestion": "..."
}
],
"suggestions": [
"General suggestion 1..."
]
}
</output_format>
