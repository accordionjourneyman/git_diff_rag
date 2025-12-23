---
path: "/home/tiago/pr_checker" # Use self for demo
main_branch: "HEAD~1"
remote: ""
default_workflow: "pr_review"
code_language: "python"
answer_language: "english"
comment_language: "english"

workflows:
  - pr_review
  - agentic_map
  - explain_diff
  - comprehensive

pr_review:
  prompt: "prompts/recipes/standard_pr_review.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

agentic_map:
  prompt: "prompts/recipes/agentic_workspace_map.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

explain_diff:
  prompt: "prompts/recipes/explain_diff.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"

comprehensive:
  prompt: "prompts/recipes/comprehensive_review.md"
  llm: "gemini"
  model: "gemini-3-flash-preview"
---
