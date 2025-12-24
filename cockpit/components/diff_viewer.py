"""Diff Viewer Component for Git Diff RAG Cockpit

Displays file diffs and findings for selected files.
"""

import streamlit as st
from streamlit_code_diff import st_code_diff
from scripts import ui_utils


def render_diff_viewer(repo_path, actual_target, actual_source):
    """Render the diff viewer component.

    Args:
        repo_path: Path to the git repository
        actual_target: Target ref for comparison
        actual_source: Source ref for comparison
    """
    if st.session_state.selected_file:
        st.markdown(f"### 📝 Diff: `{st.session_state.selected_file}`")
        st.caption(f"Comparing: `{actual_target}` ↔ `{actual_source}`")

        before = ui_utils.get_file_content(repo_path, actual_target, st.session_state.selected_file)
        after = ui_utils.get_file_content(repo_path, actual_source, st.session_state.selected_file)

        # Check if content is identical after normalization
        if before == after:
            st.info("File content is identical (ignoring line endings).")
            with st.expander("Show Content"):
                st.code(after)
        else:
            st_code_diff(before, after)

        # Context Tower (Findings) moved here for relevance
        findings = ui_utils.get_findings(repo_path, actual_target, actual_source,
                                       st.session_state.target_commit, st.session_state.source_commit)
        if findings:
            with st.expander(f"🚨 Rule Findings ({len(findings)})", expanded=False):
                for f in findings:
                    sev = "high" if "security" in f['message'].lower() or "deprecated" in f['message'].lower() else "med"
                    st.markdown(f'<div class="finding-alert finding-{sev}"><b>{f["type"].upper()}</b>: {f["message"]}</div>',
                              unsafe_allow_html=True)
    else:
        st.info("Select a file from the tree to view the diff.")


def render_execution_results():
    """Render the execution results component."""
    if st.session_state.show_results and st.session_state.execution_result:
        st.divider()

        result_col1, result_col2 = st.columns([3, 1])
        with result_col1:
            st.markdown("### ✅ AI Review Results")
        with result_col2:
            if st.button("✖️ Dismiss", use_container_width=True):
                st.session_state.show_results = False
                st.session_state.execution_result = None
                st.rerun()

        # Display the review in a container for easy copying
        st.markdown("---")
        st.markdown(st.session_state.execution_result)

        # Show raw markdown in an expander for easy copying
        with st.expander("📋 Copy Raw Markdown"):
            st.code(st.session_state.execution_result, language="markdown")