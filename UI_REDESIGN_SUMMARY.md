# UI Redesign Summary

## 1. Logo Header

Added a graphical header with the new "Git Diff RAG / Cockpit" branding.

- **Logo:** `cockpit/assets/logo.png`
- **Location:** Top of the usage container.

## 2. Compact Prompt Composer

Replaced the bulky two-column button list with a **Hierarchical Tree View**.

- **Component:** `sac.tree` (Streamlit Antd Components)
- **Features:**
  - **Folder Grouping:** Recipes vs Library vs Root.
  - **Multi-Selection:** Checkboxes to select active recipes.
  - **Tooltips:** Hover over items to see descriptions (parsed from frontmatter).
  - **Compactness:** Takes up significantly less vertical space (300px height scroller).

## 3. Frontmatter Support

Updated `ui_utils.py` to parse YAML frontmatter from Prompt Recipes.

- **Metadata:** `description`, `tags`.
- **Integration:** Descriptions are displayed as tooltips in the Prompt Composer.

## Files Modified

- `cockpit/app.py`: UI implementation.
- `scripts/ui_utils.py`: Frontmatter parsing logic.
- `prompts/recipes/standard_pr_review.md`: Added frontmatter.
- `prompts/recipes/architectural_review.md`: Added frontmatter.
- `prompts/recipes/test_coverage_advisor.md`: Added frontmatter.
