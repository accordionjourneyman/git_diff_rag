# Git Diff RAG - Product Roadmap

## Completed ✅
- Python-first architecture migration
- Streamlit Cockpit UI
- File tree visualization with smart filtering
- Line ending normalization
- Multi-provider AI support (Gemini, Copilot CLI)

## In Progress 🚧

### Phase 1: UX Overhaul - "Instant Insight" Mode
**Goal:** Transform from configuration panel to instant-use diff reviewer

- [ ] Auto-detection & immediate diff display
- [ ] Compact top bar with humanized labels
- [ ] Hero action button ("🚀 Run AI Review")
- [ ] Collapse secondary features (prompt customization)
- [ ] Error handling with guided setup
- [ ] Status indicator (files changed, lines added/removed)

## Backlog 📋

### Phase 2: Inline Findings
**Goal:** AI-powered line-level code annotations

**Requirements:**
- Study feasibility of "second-pass" prompt for line number extraction
- Design annotation overlay system
- Implement finding-to-line-number mapping
- Create visual markers in diff viewer

**Technical Considerations:**
- LLM output parsing reliability
- Performance impact of additional API calls
- Caching strategy for findings

### Phase 3: Smart Caching & Performance
- Cache AI reviews by diff hash
- Incremental analysis for large changesets
- Background pre-analysis for common workflows

### Phase 4: Collaboration Features
- Share review links
- Comment threads on findings
- Review approval workflow

### Phase 5: Advanced Analytics
- Diff stats visualization (bar charts by file type)
- Trend analysis (code quality over time)
- Team insights dashboard

## Ideas 💡
- GitHub PR integration
- VS Code extension
- Slack/Discord notifications
- Custom rule engine for static analysis
- Multi-language documentation generation
