"""File Tree Component for Git Diff RAG Cockpit

Provides an interactive file tree for selecting files to view diffs.
"""

import streamlit as st
import streamlit_antd_components as sac
from scripts import ui_utils


def render_file_tree(repo_path, actual_target, actual_source, changed_files):
    """Render the interactive file tree component.

    Args:
        repo_path: Path to the git repository
        actual_target: Target ref for comparison
        actual_source: Source ref for comparison
        changed_files: List of changed files

    Returns:
        None - updates session state directly
    """
    st.markdown("### 📂 Files")

    if not changed_files:
        st.success("No changes detected.")
        return

    # Filter Input
    filter_text = st.text_input("Filter files", placeholder="e.g. .py", label_visibility="collapsed")

    # 1. Filter by text
    text_filtered = [f for f in changed_files if filter_text.lower() in f.lower()] if filter_text else changed_files

    # 2. Filter by content (remove identicals)
    final_files = []
    # We use a spinner because this might take a moment for many files
    with st.spinner("Verifying actual changes..."):
        for f in text_filtered:
            b = ui_utils.get_file_content(repo_path, actual_target, f)
            a = ui_utils.get_file_content(repo_path, actual_source, f)
            if b != a:
                final_files.append(f)

    if not final_files:
        st.success("No content changes detected (files may differ only by line endings).")
        return

    # Build Tree Structure & Label Map
    tree_items = []
    label_map = {}  # label -> full_path

    def get_unique_label(base_label):
        label = base_label
        counter = 0
        while label in label_map:
            counter += 1
            label = base_label + "\u200b" * counter
        return label

    def add_to_tree(nodes, parts, full_path):
        part = parts[0]
        is_file = len(parts) == 1

        # Find existing node (by visual label, ignoring ZWS for matching parent folders)
        existing_node = None
        for node in nodes:
            # Strip ZWS to match folder names correctly
            if node.label.rstrip('\u200b') == part and ((is_file and node.icon == 'file-code') or (not is_file and node.icon == 'folder')):
                existing_node = node
                break

        if existing_node:
            if is_file:
                pass
            else:
                add_to_tree(existing_node.children, parts[1:], full_path)
        else:
            # Create new node
            if is_file:
                unique_label = get_unique_label(part)
                new_node = sac.TreeItem(unique_label, icon='file-code')
                nodes.append(new_node)
                label_map[unique_label] = full_path
            else:
                # Folders also need unique labels in the map if we want to be safe,
                # but usually we don't select folders.
                # However, we need to store them in the tree.
                # We don't add folders to label_map for file selection,
                # but we need to ensure their labels are unique in the tree if they are siblings?
                # Actually, sibling folders with same name are impossible.
                # So folder labels are unique among siblings.
                new_node = sac.TreeItem(part, icon='folder', children=[])
                nodes.append(new_node)
                add_to_tree(new_node.children, parts[1:], full_path)

    for f in sorted(final_files):
        parts = f.split('/')
        add_to_tree(tree_items, parts, f)

    # Render SAC Tree
    selected_label = sac.tree(
        items=tree_items,
        label='',
        align='start',
        size='sm',
        show_line=True,
        icon='folder',
        open_all=True,
        return_index=False,  # Use labels
        key=f'file_tree_{filter_text}_{len(final_files)}'
    )

    # Handle Selection
    if selected_label:
        # sac returns a list if multiple, or string if single?
        # Documentation says: returns list of selected indexes or labels.
        # Wait, let's be safe.
        target_label = None
        if isinstance(selected_label, list) and len(selected_label) > 0:
            target_label = selected_label[0]
        elif isinstance(selected_label, str):
            target_label = selected_label

        if target_label and target_label in label_map:
            full_path = label_map[target_label]
            if full_path != st.session_state.selected_file:
                st.session_state.selected_file = full_path
                st.rerun()
        elif target_label:
            # It might be a folder or unmapped item
            pass