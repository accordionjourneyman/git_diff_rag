import time
import os
import sys
import sqlite3
import hashlib
import subprocess
import yaml
import glob
import streamlit as st
from datetime import datetime
# Add root to path for script imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import ui_utils, config_utils, db_manager
from cockpit.components import file_tree, diff_viewer
from streamlit_code_diff import st_code_diff
from streamlit_monaco import st_monaco
import streamlit_antd_components as sac
from scripts.render_prompt import render_template

# Token estimation constants
TOKEN_THRESHOLD = 100000  # Warn when context exceeds this
CHARS_PER_TOKEN = 4  # Rough estimate

def estimate_tokens(text: str) -> int:
    """Rough token estimate based on character count."""
    return len(text) // CHARS_PER_TOKEN if text else 0

def summarize_with_gemini(content: str, content_type: str = "diff") -> str:
    """Use Gemini API to summarize large content for context optimization.
    
    Args:
        content: The content to summarize (diff or commit history)
        content_type: Either 'diff' or 'commits'
        
    Returns:
        Summarized content string
    """
    try:
        from scripts.llm_strategy import get_provider
        provider = get_provider("gemini")
        
        if content_type == "diff":
            prompt = f"""Summarize this git diff into a concise overview (max 2000 chars).
Focus on: what files changed, key modifications, and overall intent.

```diff
{content[:50000]}
```

Provide a structured summary:
1. Files Changed (bullet list)
2. Key Modifications (grouped by area)
3. Overall Intent (1-2 sentences)"""
        else:  # commit history
            prompt = f"""Summarize these commit messages into a coherent narrative (max 1000 chars).
Focus on: the progression of work, key milestones, and overall direction.

{content[:20000]}

Provide a narrative summary capturing the developer's journey."""
        
        return provider.call(prompt, model="gemini-2.0-flash-exp")
    except Exception as e:
        return f"[Summarization failed: {str(e)}]"

# Page Config
st.set_page_config(
    page_title="Git Diff RAG — Review Cockpit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# World-Class HMI Styling
st.markdown("""
<style>
    .main { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px 6px 0 0; color: #8b949e; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #0d1117; color: #58a6ff; border-bottom: 2px solid #58a6ff; }
    
    .hero-panel { background: #161b22; padding: 1.5rem; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .finding-alert { padding: 12px; border-radius: 6px; margin-bottom: 8px; border-left: 5px solid; }
    .finding-high { background: rgba(248, 81, 79, 0.1); border-color: #f85149; color: #ff7b72; }
    .finding-med { background: rgba(210, 153, 34, 0.1); border-color: #d29922; color: #d29922; }
    
    .lego-block { background: #21262d; border: 1px solid #30363d; padding: 10px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
    .lego-block:hover { border-color: #58a6ff; }
    .lego-tag { font-size: 0.7em; padding: 2px 6px; border-radius: 10px; background: #30363d; color: #8b949e; margin-right: 8px; }
    
    .status-bar { padding: 8px 20px; background: #161b22; border-top: 1px solid #30363d; position: fixed; bottom: 0; left: 0; width: 100%; color: #8b949e; z-index: 1000; font-family: monospace; font-size: 0.85em; }
    .hero-btn>button { background: linear-gradient(135deg, #1f6feb, #58a6ff) !important; color: white !important; height: 3.5rem !important; font-size: 1.2em !important; font-weight: 700 !important; border: none !important; border-radius: 8px !important; box-shadow: 0 4px 20px rgba(31, 111, 235, 0.4) !important; transition: all 0.3s !important; }
    .hero-btn>button:hover { transform: translateY(-2px) !important; box-shadow: 0 6px 25px rgba(31, 111, 235, 0.6) !important; }
    .status-indicator { display: inline-block; padding: 6px 14px; background: #21262d; border: 1px solid #30363d; border-radius: 20px; font-size: 0.9em; color: #8b949e; font-weight: 500; }
    .status-indicator.ready { border-color: #238636; color: #2ea043; }
    .compact-select { margin-bottom: 0.5rem; }
    /* Mermaid Styles Override */
    .mermaid { background: transparent !important; }
    .timer-badge { font-family: monospace; background: #30363d; color: #58a6ff; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if 'repo' not in st.session_state: st.session_state.repo = None
if 'target' not in st.session_state: st.session_state.target = "main"
if 'source' not in st.session_state: st.session_state.source = "HEAD"
if 'target_commit' not in st.session_state: st.session_state.target_commit = None
if 'source_commit' not in st.session_state: st.session_state.source_commit = None
if 'active_bundle' not in st.session_state: st.session_state.active_bundle = []
if 'selected_file' not in st.session_state: st.session_state.selected_file = None
if 'agent_active' not in st.session_state: st.session_state.agent_active = False
if 'is_executing' not in st.session_state: st.session_state.is_executing = False
if 'current_step' not in st.session_state: st.session_state.current_step = None
if 'completed_steps' not in st.session_state: st.session_state.completed_steps = []
if 'execution_times' not in st.session_state: st.session_state.execution_times = {}
if 'show_advanced' not in st.session_state: st.session_state.show_advanced = False
if 'show_advanced' not in st.session_state: st.session_state.show_advanced = False
if 'setup_complete' not in st.session_state: st.session_state.setup_complete = False
if 'execution_result' not in st.session_state: st.session_state.execution_result = None
if 'show_results' not in st.session_state: st.session_state.show_results = False
if 'tool_choice' not in st.session_state: st.session_state.tool_choice = "GitHub Copilot CLI"
if 'model_choice' not in st.session_state: st.session_state.model_choice = "gpt-4"
# Summarization state
if 'use_summarized' not in st.session_state: st.session_state.use_summarized = False
if 'summarized_diff' not in st.session_state: st.session_state.summarized_diff = None
if 'summarized_commits' not in st.session_state: st.session_state.summarized_commits = None
if 'commit_search' not in st.session_state: st.session_state.commit_search = ""

# --- Auto-Detection & Error Handling ---
repos = ui_utils.list_repositories()

# Auto-detect current repo if not set, or if current repo is invalid
if not st.session_state.repo or st.session_state.repo not in repos:
    if repos:
        st.session_state.repo = repos[0]
        st.session_state.setup_complete = True
    else:
        st.session_state.setup_complete = False

if not st.session_state.setup_complete:
    # Show setup wizard
    st.error("⚠️ No repository configuration found")
    st.markdown("""
    ### Let's Get Started
    
    To use the Git Diff RAG Cockpit, you need to configure at least one repository.
    
    **Quick Setup:**
    1. Go to the **⚙️ Settings** tab
    2. Click **"+ Add New"** under Repositories
    3. Fill in the repository details (name, path, main branch)
    4. Click **"💾 Save Configuration"**
    
    **Need Help?** Check the [Setup Guide](../docs/COCKPIT.md) for detailed instructions.
    """)
    st.stop()

config = config_utils.load_repo_config(st.session_state.repo)
repo_path = config.get('path', '.') if config else '.'

# Validate repo path
try:
    result = subprocess.run(["git", "-C", repo_path, "rev-parse", "--git-dir"], 
                          capture_output=True, text=True, check=True)
    branches = ui_utils.get_branches(repo_path)
    
    # Auto-detect main branch if default doesn't exist
    if st.session_state.target not in branches:
        if "main" in branches:
            st.session_state.target = "main"
        elif "master" in branches:
            st.session_state.target = "master"
        elif branches:
            st.session_state.target = branches[0]
except (subprocess.CalledProcessError, FileNotFoundError):
    st.error(f"⚠️ Invalid repository path: `{repo_path}`")
    st.markdown("""
    The configured repository path is not a valid git repository.
    
    **To fix this:**
    1. Go to **⚙️ Settings** tab
    2. Update the **Local Path** for `{}`
    3. Make sure it points to a valid git repository
    """.format(st.session_state.repo))
    st.stop()

# --- HEADER ---
with st.container():
    h_col1, h_col2 = st.columns([0.8, 8], gap="small")
    with h_col1:
        if os.path.exists("cockpit/assets/logo.png"):
            st.image("cockpit/assets/logo.png", width=72)
        else:
            st.markdown("<h1>🤖</h1>", unsafe_allow_html=True)
    with h_col2:
        st.markdown('<h1 style="margin-top:0; padding-top:10px;">Git Diff RAG <span style="font-size:0.5em; color:#8b949e; font-weight:normal;">/ Cockpit</span></h1>', unsafe_allow_html=True)

# --- COMPACT TOP BAR ---
with st.container():
    col1, col2, col3, col4 = st.columns([2, 2, 2, 0.8])
    
    with col1:
        new_repo = st.selectbox("📦 Repository", options=repos, 
                               index=repos.index(st.session_state.repo) if st.session_state.repo in repos else 0,
                               key="repo_select")
        if new_repo != st.session_state.repo:
            st.session_state.repo = new_repo
            st.session_state.selected_file = None
            st.rerun()

    with col2:
        new_target = st.selectbox("📍 Compare Against", options=branches, 
                                 index=branches.index(st.session_state.target) if st.session_state.target in branches else 0,
                                 key="target_select")
        if new_target != st.session_state.target:
            st.session_state.target = new_target
            st.session_state.target_commit = None
            st.rerun()

    with col3:
        source_opts = ["Working Directory"] + branches
        new_source = st.selectbox("✨ Your Changes", options=source_opts, 
                                 index=source_opts.index(st.session_state.source) if st.session_state.source in source_opts else 0,
                                 key="source_select")
        if new_source != st.session_state.source:
            st.session_state.source = new_source
            st.session_state.source_commit = None
            st.rerun()
    
    with col4:
        # Invisible header to align the Advanced button vertically with the selects
        st.markdown("<p style='padding-top: 12px;'></p>", unsafe_allow_html=True)
        if st.button("⚙️ Advanced", use_container_width=True):
            st.session_state.show_advanced = not st.session_state.show_advanced
            st.rerun()

# Advanced Options (Collapsed by Default)
if st.session_state.show_advanced:
    with st.expander("🔧 Advanced Options", expanded=True):
        # Helper function for commit display
        def format_commit_option(commit: dict) -> str:
            """Format commit for dropdown: 'abc1234 • Dec 23 • @author • Fix login bug'"""
            short_hash = commit['hash'][:7]
            date_str = commit.get('date', '').split()[0] if commit.get('date') else ''
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_display = date_obj.strftime('%b %d')
            except:
                date_display = date_str[:10] if date_str else '?'
            author = commit.get('author', 'unknown').split()[0][:10]
            subject = commit.get('message', '')[:35]
            if len(commit.get('message', '')) > 35:
                subject += '...'
            return f"{short_hash} • {date_display} • @{author} • {subject}"
        
        adv_col1, adv_col2 = st.columns(2)
        
        with adv_col1:
            st.markdown("**Compare Against - Specific Commit**")
            target_commits = ui_utils.get_commits(repo_path, st.session_state.target)
            
            # Search filter
            target_search = st.text_input("🔍 Filter", placeholder="hash, author, or message...", key="target_commit_search")
            
            # Filter commits
            filtered_target = target_commits
            if target_search:
                search_lower = target_search.lower()
                filtered_target = [c for c in target_commits if (
                    search_lower in c['hash'].lower() or 
                    search_lower in c.get('author', '').lower() or 
                    search_lower in c.get('message', '').lower()
                )]
            
            # Build display options
            target_commit_opts = ["Current HEAD"] + [format_commit_option(c) for c in filtered_target]
            label_to_hash_target = {format_commit_option(c): c['hash'] for c in filtered_target}
            hash_to_label_target = {c['hash']: format_commit_option(c) for c in filtered_target}
            
            current_label = "Current HEAD"
            if st.session_state.target_commit and st.session_state.target_commit in hash_to_label_target:
                current_label = hash_to_label_target[st.session_state.target_commit]
            
            selected_label = st.selectbox("Target Commit", options=target_commit_opts,
                index=target_commit_opts.index(current_label) if current_label in target_commit_opts else 0,
                label_visibility="collapsed", key="target_commit_select")
            
            st.session_state.target_commit = label_to_hash_target.get(selected_label) if selected_label != "Current HEAD" else None
            
            if target_search:
                st.caption(f"Showing {len(filtered_target)} of {len(target_commits)} commits")
        
        with adv_col2:
            if st.session_state.source != "Working Directory":
                st.markdown("**Your Changes - Specific Commit**")
                source_commits = ui_utils.get_commits(repo_path, st.session_state.source)
                
                # Search filter
                source_search = st.text_input("🔍 Filter", placeholder="hash, author, or message...", key="source_commit_search")
                
                # Filter commits
                filtered_source = source_commits
                if source_search:
                    search_lower = source_search.lower()
                    filtered_source = [c for c in source_commits if (
                        search_lower in c['hash'].lower() or 
                        search_lower in c.get('author', '').lower() or 
                        search_lower in c.get('message', '').lower()
                    )]
                
                source_commit_opts = ["Current HEAD"] + [format_commit_option(c) for c in filtered_source]
                label_to_hash_source = {format_commit_option(c): c['hash'] for c in filtered_source}
                hash_to_label_source = {c['hash']: format_commit_option(c) for c in filtered_source}
                
                current_source_label = "Current HEAD"
                if st.session_state.source_commit and st.session_state.source_commit in hash_to_label_source:
                    current_source_label = hash_to_label_source[st.session_state.source_commit]
                
                selected_source = st.selectbox("Source Commit", options=source_commit_opts,
                    index=source_commit_opts.index(current_source_label) if current_source_label in source_commit_opts else 0,
                    label_visibility="collapsed", key="source_commit_select")
                
                st.session_state.source_commit = label_to_hash_source.get(selected_source) if selected_source != "Current HEAD" else None
                
                if source_search:
                    st.caption(f"Showing {len(filtered_source)} of {len(source_commits)} commits")
            else:
                st.session_state.source_commit = None

# Final Resolved Refs for Engine
actual_target, actual_source, _is_direct = ui_utils.get_smart_refs(repo_path, st.session_state.target, st.session_state.source, st.session_state.target_commit, st.session_state.source_commit)
changed_files = ui_utils.get_changed_files(repo_path, st.session_state.target, st.session_state.source, st.session_state.target_commit, st.session_state.source_commit)

if changed_files and not st.session_state.selected_file:
    st.session_state.selected_file = changed_files[0]

# Status Indicator
if changed_files:
    total_diff = ui_utils.get_diff(repo_path, actual_target, actual_source, target_commit=st.session_state.target_commit, source_commit=st.session_state.source_commit)
    lines_added = total_diff.count('\n+')
    lines_removed = total_diff.count('\n-')
    st.markdown(f'<span class="status-indicator ready">🟢 {len(changed_files)} files • +{lines_added} -{lines_removed} lines</span>', unsafe_allow_html=True)
    
    # Token Estimation
    estimated_tokens = estimate_tokens(total_diff)
    if estimated_tokens > TOKEN_THRESHOLD:
        st.warning(f"⚠️ Large diff detected: ~{estimated_tokens:,} tokens. Consider using Summarize.")
        sum_col1, sum_col2 = st.columns([1, 3])
        with sum_col1:
            if st.button("⚡ Summarize", help="Use Gemini API to optimize context for large diffs"):
                with st.spinner("Summarizing with Gemini API..."):
                    st.session_state.summarized_diff = summarize_with_gemini(total_diff, "diff")
                    st.session_state.use_summarized = True
                    st.success("✅ Diff summarized")
                    st.rerun()
        with sum_col2:
            if st.session_state.use_summarized:
                st.info("📝 Using summarized diff for AI review")
                if st.button("🔄 Reset to full diff"):
                    st.session_state.use_summarized = False
                    st.session_state.summarized_diff = None
                    st.rerun()
else:
    st.markdown('<span class="status-indicator">⚪ No changes detected</span>', unsafe_allow_html=True)

# Commit History Panel
if changed_files:
    from scripts.git_operations import get_commits_between
    
    with st.expander("📝 Commit History", expanded=False):
        try:
            commits = get_commits_between(repo_path, actual_target, actual_source)
            
            if commits['total_count'] > 0:
                st.caption(f"Showing {len(commits['tier1'])} detailed + {len(commits['tier2'])} summary of {commits['total_count']} total commits")
                
                # Tier 1: Full detail
                if commits['tier1']:
                    st.markdown("**Recent Commits**")
                    for c in commits['tier1']:
                        with st.container():
                            st.markdown(f"**`{c['hash']}`** — {c['subject']}")
                            st.caption(f"{c['author']} • {c['date']}")
                            if c.get('body'):
                                body_preview = c['body'][:300] + '...' if len(c['body']) > 300 else c['body']
                                st.text(body_preview)
                
                # Tier 2: Compact
                if commits['tier2']:
                    st.markdown("---")
                    st.markdown("**Earlier Commits**")
                    for c in commits['tier2']:
                        st.text(f"{c['hash']} | {c['date']} | {c['subject'][:50]}...")
                
                # Truncation note
                if commits['truncated_count'] > 0:
                    st.info(f"ℹ️ {commits['truncated_count']} older commits not shown")
            else:
                st.info("No commits between these refs")
        except Exception as e:
            st.warning(f"Could not load commit history: {e}")

st.divider()

# --- MAIN LAYOUT ---
# Master Navigation Tabs (Simplified)
tab_review, tab_history, tab_editor, tab_settings = st.tabs(["🔍 Review & Analyze", "📜 History", "📝 Editor", "⚙️ Settings"])

# --- TAB 1: REVIEW & ANALYZE ---
with tab_review:
    # Hero Action Button (Top Right)
    action_col1, action_col2 = st.columns([3, 1])
    with action_col1:
        st.markdown("### 📝 Code Changes")
    with action_col2:
        st.markdown('<div class="hero-btn">', unsafe_allow_html=True)
        if st.button("🚀 RUN AI REVIEW", use_container_width=True, disabled=st.session_state.is_executing or not changed_files):
            if not st.session_state.active_bundle:
                # Use default bundle if none selected
                default_recipe = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                            "prompts", "recipes", "standard_pr_review.md")
                if os.path.exists(default_recipe):
                    st.session_state.active_bundle = [default_recipe]
            
            if st.session_state.active_bundle:
                st.session_state.is_executing = True
                st.session_state.completed_steps = []
                st.session_state.execution_times = {}
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Collapsible Prompt Customization
    with st.expander("🧱 Customize Instructions (Prompt Composer)", expanded=True):
        # Layout: Tree Selector | Preview Panel
        comp_col1, comp_col2 = st.columns([1.2, 1.8], gap="medium")
        
        library = ui_utils.list_prompt_library()
        
        # Build Tree Items & Label Map (Pre-calculation)
        tree_data = {}
        label_map = {}
        lib_lookup = {item['full_path']: item for item in library}
        
        for item in library:
            folder = os.path.dirname(item['name']) or "root"
            if "macros" in folder: continue
            if folder not in tree_data: tree_data[folder] = []
            tree_data[folder].append(item)
            
        folder_order = ['recipes', 'library', 'root']
        sorted_folders = sorted(tree_data.keys(), key=lambda x: folder_order.index(x) if x in folder_order else 99)
        
        sac_items = []
        for folder in sorted_folders:
            children = []
            for item in tree_data[folder]:
                desc = item.get('description')
                
                # Unique label logic
                base_label = os.path.basename(item['name'])
                label = base_label
                counter = 1
                while label in label_map:
                    label = f"{base_label} ({counter})"
                    counter += 1
                
                label_map[label] = item['full_path']
                
                desc_str = desc if desc else ""
                children.append(sac.TreeItem(
                    label=label,
                    icon='file-text',
                    description=desc_str[:57]+"..." if len(desc_str)>60 else desc_str,
                    tooltip=desc_str
                ))
            
            icon = 'folder-open' if 'recipes' in folder else 'folder'
            sac_items.append(sac.TreeItem(
                label=folder.title(),
                icon=icon,
                children=children
            ))

        # --- LEFT COLUMN: SELECTOR ---
        with comp_col1:
            st.markdown("##### 📚 Selection")
            
            # Initial Selection Mapping
            path_to_label = {v: k for k, v in label_map.items()}
            current_selection_labels = [path_to_label[p] for p in st.session_state.active_bundle if p in path_to_label]
            
            # Fallback to Multiselect for stability
            sorted_options = sorted(list(label_map.keys()))
            default_sel = [l for l in current_selection_labels if l in sorted_options]
            selected_labels = st.multiselect("Select Recipes", sorted_options, default=default_sel, key="prompt_multiselect")
            
            # Update State
            valid_selection = [label_map[lbl] for lbl in selected_labels if lbl in label_map]
            
            if valid_selection != st.session_state.active_bundle:
                st.session_state.active_bundle = valid_selection
                st.rerun()

        # --- RIGHT COLUMN: PREVIEW ---
        with comp_col2:
            st.markdown("##### 🔮 Execution Plan")
            
            if not st.session_state.active_bundle:
                 st.info("👈 Select detailed recipes from the library to build your analysis strategy.")
                 default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "recipes", "standard_pr_review.md")
                 if os.path.exists(default_path) and default_path not in st.session_state.active_bundle:
                     st.caption("ℹ️ If empty, 'Standard PR Review' applies by default.")
            else:
                 st.caption(f"The following **{len(st.session_state.active_bundle)} recipes** will be executed in order:")
                 
                 for i, path in enumerate(st.session_state.active_bundle):
                     item = lib_lookup.get(path)
                     fname = os.path.basename(path)
                     if item:
                         desc = item.get('description', 'No description available.')
                         tags = item.get('tags', [])
                     else:
                         desc = "Unknown recipe"
                         tags = []
                     
                     tags_html = "".join([f'<span class="lego-tag">{t}</span>' for t in tags])
                     
                     st.markdown(f"""
                     <div style="background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin-bottom: 8px; display: flex; flex-direction: column;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="font-weight: 600; color: #58a6ff;">{i+1}. {fname}</span>
                            <span style="font-size: 0.8em; color: #8b949e; font-family: monospace;">{len(tags)} tags</span>
                        </div>
                        <div style="font-size: 0.9em; color: #c9d1d9; margin-bottom: 8px;">{desc}</div>
                        <div>{tags_html}</div>
                     </div>
                     """, unsafe_allow_html=True)

    # Tool Selection
    with st.expander("⚙️ AI Tool Configuration", expanded=False):
        new_tool = st.selectbox("AI Provider", ["GitHub Copilot CLI", "Gemini API", "Gemini CLI"], 
                               index=0 if st.session_state.tool_choice == "GitHub Copilot CLI" else (1 if st.session_state.tool_choice == "Gemini API" else 2))
        if new_tool != st.session_state.tool_choice:
            st.session_state.tool_choice = new_tool
            st.rerun()
        
        if st.session_state.tool_choice == "Gemini API":
            try:
                from scripts.llm_strategy import get_provider
                provider = get_provider("gemini")
                available_models = provider.list_models()
            except Exception:
                available_models = ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]
            
            if 'available_models' not in st.session_state or st.session_state.get('last_tool_choice') != st.session_state.tool_choice:
                st.session_state.available_models = available_models
                st.session_state.last_tool_choice = st.session_state.tool_choice
            
            current_index = 0
            if st.session_state.model_choice in st.session_state.available_models:
                current_index = st.session_state.available_models.index(st.session_state.model_choice)
            new_model = st.selectbox("Model", st.session_state.available_models, index=current_index)
            if new_model != st.session_state.model_choice:
                st.session_state.model_choice = new_model
        elif st.session_state.tool_choice == "Gemini CLI":
            try:
                from scripts.llm_strategy import get_provider
                provider = get_provider("gemini-cli")
                available_models = provider.list_models()
            except Exception:
                available_models = ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-3-flash-preview"]
            
            if 'available_models' not in st.session_state or st.session_state.get('last_tool_choice') != st.session_state.tool_choice:
                st.session_state.available_models = available_models
                st.session_state.last_tool_choice = st.session_state.tool_choice
            
            current_index = 0
            if st.session_state.model_choice in st.session_state.available_models:
                current_index = st.session_state.available_models.index(st.session_state.model_choice)
            new_model = st.selectbox("Model", st.session_state.available_models, index=current_index)
            if new_model != st.session_state.model_choice:
                st.session_state.model_choice = new_model
        else:
            st.session_state.model_choice = "gpt-4"  # Default for Copilot CLI
            st.caption("Using GitHub Copilot CLI (no model selection needed)")
    
    st.divider()
    
    # Execution Status (if running)
    if st.session_state.is_executing:
        st.markdown("### 🚀 AI Review In Progress")

        with st.status("Running AI Review...", expanded=True) as status:
            try:
                # Track execution time
                start_time = time.time()
                
                # Step 1: Fetch diff
                st.write("📥 **Step 1/5:** Fetching diff from repository...")
                
                # Check for summarized override
                if st.session_state.use_summarized and st.session_state.summarized_diff:
                    diff_content = st.session_state.summarized_diff
                    st.info("ℹ️ Using pre-summarized diff for context optimization")
                else:
                    diff_content = ui_utils.get_diff(repo_path, actual_target, actual_source, 
                                                    target_commit=st.session_state.target_commit, 
                                                    source_commit=st.session_state.source_commit)
                
                elapsed = time.time() - start_time
                st.write(f"   ✓ Fetched {len(diff_content)} chars of changes ({elapsed:.2f}s)")
                st.session_state.execution_times['fetch_diff'] = elapsed
                start_time = time.time()
                
                # Fetch Commit History for Context
                commit_history = {}
                try:
                    from scripts.git_operations import get_commits_between
                    commit_history = get_commits_between(
                        repo_path, 
                        actual_target, 
                        actual_source,
                        tier1_limit=10,
                        tier2_limit=50
                    )
                    st.write(f"   ✓ Loaded {commit_history.get('total_count', 0)} commits for context")
                except Exception as e:
                    st.warning(f"   ⚠️ Failed to load commit history: {e}")

                # Step 2: Prepare prompt
                st.write("🧱 **Step 2/5:** Building review prompt...")
                
                # Create output directory early for template rendering
                timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
                out_folder = f"output/{timestamp}-{st.session_state.repo}-review"
                
                # We construct the prompt manually here to support multiple recipes
                # But we must ensure the macros work
                
                full_prompt = ""
                # Inject diff at the top for some recipes, or let macros handle it?
                # The Orchestrator uses render_prompt_with_context. 
                # Here we loop through active_bundle (recipes).
                
                for p_path in st.session_state.active_bundle:
                    # Pass context data to render_template
                    part = render_template(
                        p_path, 
                        diff_content, 
                        repo_name=st.session_state.repo, 
                        inject_diff_content=False, # Recipes usually include {{ DIFF_CONTENT }} explicitly
                        commit_history_data=commit_history,
                        target_ref=actual_target,
                        source_ref=actual_source,
                        OUTPUT_DIR=out_folder
                    )
                    full_prompt += part + "\n\n---\n\n"
                
                # Fallback if no recipe includes DIFF_CONTENT
                if "{{ DIFF_CONTENT }}" not in full_prompt and "diff" not in full_prompt.lower()[:200]:
                     full_prompt += f"\n\n## DIFF\n\n```diff\n{diff_content}\n```"
                
                st.write(f"   ✓ Prompt ready ({len(st.session_state.active_bundle)} instruction(s) included)")
                
                # Step 3: Save artifacts
                st.write("💾 **Step 3/5:** Saving artifacts...")
                os.makedirs(out_folder, exist_ok=True)
                
                with open(f"{out_folder}/prompt.txt", "w") as f:
                    f.write(full_prompt)
                with open(f"{out_folder}/diff.patch", "w") as f:
                    f.write(diff_content)
                
                st.write(f"   ✓ Saved to `{out_folder}`")
                
                # Step 4: Call AI
                st.write(f"🤖 **Step 4/5:** Calling {st.session_state.tool_choice} with {st.session_state.model_choice}...")
                st.info("⏳ This may take 30-60 seconds. Please wait...")
                
                # Use Strategy Pattern for LLM provider
                from scripts.llm_strategy import get_provider
                
                provider_map = {
                    "Gemini API": "gemini",
                    "Gemini CLI": "gemini-cli",
                    "GitHub Copilot CLI": "gh-copilot"
                }
                provider_name = provider_map.get(st.session_state.tool_choice, "gemini")
                provider = get_provider(provider_name)
                
                # Call the provider
                if provider_name == "gh-copilot":
                    response = provider.call(full_prompt, allow_tools=['shell(git)', 'write'], timeout=300)
                elif provider_name == "gemini-cli":
                    response = provider.call(full_prompt, model=st.session_state.model_choice, allow_tools=['shell(git)', 'write'], timeout=300)
                else:
                    response = provider.call(full_prompt, model=st.session_state.model_choice)
                
                if response:
                    st.write(f"   ✓ Received {len(response)} characters of analysis")
                else:
                    st.warning("   ⚠️ Received empty response from AI")
                
                # Step 5: Save response
                st.write("💾 **Step 5/5:** Saving results...")
                with open(f"{out_folder}/response.md", "w") as f:
                    f.write(response)
                
                db_manager.save_cache(
                    diff_hash=hashlib.md5(diff_content.encode()).hexdigest(),
                    prompt_hash=hashlib.md5(full_prompt.encode()).hexdigest(),
                    model=st.session_state.model_choice,
                    response=response,
                    repo_name=st.session_state.repo,
                    summary=response[:100] + "..." if response else "Empty response",
                    tags="ui_review"
                )
                
                st.write("   ✓ Results saved to database and file")
                
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
                
                # Store result and trigger results display
                st.session_state.execution_result = response
                st.session_state.is_executing = False
                st.session_state.show_results = True
                st.session_state.current_step = None
                
                st.success(f"🎉 Review complete! Check the results below or in the History tab.")
                st.rerun()
                
            except Exception as e:
                status.update(label="❌ Analysis Failed", state="error")
                st.error(f"**Error during execution:**\n\n{str(e)}")
                import traceback
                with st.expander("📋 Full Traceback"):
                    st.code(traceback.format_exc())
                st.session_state.is_executing = False
                st.session_state.current_step = None
    
    r_col1, r_col2 = st.columns([1, 3])
    
    with r_col1:
        file_tree.render_file_tree(repo_path, actual_target, actual_source, changed_files)

    with r_col2:
        diff_viewer.render_diff_viewer(repo_path, actual_target, actual_source)
    
    # Display Results (after execution completes)
    diff_viewer.render_execution_results()

# --- TAB 2: HISTORY ---

with tab_history:
    st.markdown("### 📜 Execution History")
    
    ht_files, ht_db = st.tabs(["📂 File Output", "🗄️ Database"])
    
    # --- SUB-TAB: FILES ---
    with ht_files:
        # Assuming output is in the root directory, one level up from cockpit/
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        
        if os.path.exists(output_dir):
            runs = sorted([d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))], reverse=True)
            
            if runs:
                col_h1, col_h2 = st.columns([1, 3])
                with col_h1:
                    selected_run = st.radio("Select Run", runs, label_visibility="collapsed")
                
                with col_h2:
                    if selected_run:
                        run_path = os.path.join(output_dir, selected_run)
                        st.caption(f"Path: `{run_path}`")
                        
                        run_files = sorted(os.listdir(run_path))
                        tabs_files = st.tabs([f for f in run_files])
                        
                        for i, f_name in enumerate(run_files):
                            with tabs_files[i]:
                                file_path = os.path.join(run_path, f_name)
                                try:
                                    with open(file_path, "r") as f:
                                        content = f.read()
                                    
                                    if f_name.endswith(".json"):
                                        st.json(content)
                                    elif f_name.endswith(".md"):
                                        st.markdown(content)
                                        with st.expander("Source"):
                                            st.code(content, language="markdown")
                                    else:
                                        st.code(content)
                                except Exception as e:
                                    st.error(f"Error reading file: {e}")
            else:
                st.info("No runs found.")
        else:
            st.error(f"Output directory not found: {output_dir}")

    # --- SUB-TAB: DATABASE ---
    with ht_db:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "history.sqlite")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT id, timestamp, repo_name, model, cost, summary, tags FROM analysis_history ORDER BY id DESC")
                rows = c.fetchall()
                cols = [description[0] for description in c.description]
                data = [dict(zip(cols, row)) for row in rows]
                conn.close()
                
                if data:
                    st.dataframe(data, use_container_width=True)
                else:
                    st.info("Database is empty.")
            except Exception as e:
                st.error(f"Error reading database: {e}")
        else:
            st.warning(f"Database not found at {db_path}")

# --- TAB 3: EDITOR ---
with tab_editor:
    st.markdown("### 📝 Prompt Editor")
    
    e_col1, e_col2 = st.columns([1, 3])
    
    with e_col1:
        editor_mode = st.radio("Mode", ["Recipes", "Library"], horizontal=True)
        
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")
        target_dir = os.path.join(base_path, "recipes") if editor_mode == "Recipes" else os.path.join(base_path, "library")
        
        if os.path.exists(target_dir):
            files = []
            for root, dirs, filenames in os.walk(target_dir):
                for filename in filenames:
                    if filename.endswith(".md"):
                        rel_path = os.path.relpath(os.path.join(root, filename), target_dir)
                        files.append(rel_path)
            files.sort()
            
            selected_edit_file = st.selectbox("Select File", files, index=0 if files else None)
        else:
            st.error(f"Directory not found: {target_dir}")
            selected_edit_file = None

    with e_col2:
        if selected_edit_file:
            full_edit_path = os.path.join(target_dir, selected_edit_file)
            
            with open(full_edit_path, "r") as f:
                content = f.read()
                
            new_content = st_monaco(value=content, height="600px", language="markdown")
            
            if st.button("💾 Save Changes"):
                with open(full_edit_path, "w") as f:
                    f.write(new_content)
                st.success(f"Saved {selected_edit_file}")

# --- TAB 4: SETTINGS ---
with tab_settings:
    st.markdown("### ⚙️ Repository Settings")
    
    s_col1, s_col2 = st.columns([1, 2])
    
    repo_setup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "repository-setup")
    
    with s_col1:
        st.markdown("#### Repositories")
        existing_configs = [f.replace(".md", "") for f in os.listdir(repo_setup_dir) if f.endswith(".md") and f != "TEMPLATE.md"]
        existing_configs.sort()
        
        selected_config = st.selectbox("Select Repository", ["+ Add New"] + existing_configs)
        
    with s_col2:
        st.markdown("#### Configuration")
        
        if selected_config == "+ Add New":
            config_name = st.text_input("Repository Name (ID)", placeholder="my-new-repo")
            config_data = {}
            body_content = "# New Repository\n\nDescription here."
        else:
            config_name = selected_config
            full_config_path = os.path.join(repo_setup_dir, f"{selected_config}.md")
            
            with open(full_config_path, "r") as f:
                raw_content = f.read()
                
            if raw_content.startswith("---"):
                try:
                    _, frontmatter, body_content = raw_content.split("---", 2)
                    config_data = yaml.safe_load(frontmatter)
                except ValueError:
                    config_data = {}
                    body_content = raw_content
            else:
                config_data = {}
                body_content = raw_content

        # Form
        with st.form("repo_settings_form"):
            path = st.text_input("Local Path", value=config_data.get("path", ""))
            main_branch = st.text_input("Main Branch", value=config_data.get("main_branch", "main"))
            remote = st.text_input("Remote", value=config_data.get("remote", "origin"))
            
            # Workflows
            recipes_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "recipes")
            available_recipes = [f.replace(".md", "") for f in os.listdir(recipes_dir) if f.endswith(".md")]
            
            current_workflows = config_data.get("workflows", [])
            if isinstance(current_workflows, dict):
                current_workflows = list(current_workflows.keys())
            elif not isinstance(current_workflows, list):
                current_workflows = []
                
            selected_workflows = st.multiselect("Enabled Workflows", available_recipes, default=[w for w in current_workflows if w in available_recipes])
            
            default_wf_opts = selected_workflows if selected_workflows else ["pr_review"]
            current_default = config_data.get("default_workflow", "pr_review")
            default_workflow = st.selectbox("Default Workflow", default_wf_opts, index=default_wf_opts.index(current_default) if current_default in default_wf_opts else 0)
            
            # Model
            current_model = "gemini-1.5-flash"
            if default_workflow in config_data and isinstance(config_data[default_workflow], dict):
                 current_model = config_data[default_workflow].get("model", "gemini-1.5-flash")
            
            model = st.text_input("Preferred Model", value=current_model)
            
            body_editor = st.text_area("Description / Notes (Markdown)", value=body_content.strip(), height=200)
            
            submitted = st.form_submit_button("💾 Save Configuration")
            
            if submitted:
                if not config_name:
                    st.error("Repository Name is required.")
                else:
                    new_config = {
                        "path": path,
                        "main_branch": main_branch,
                        "remote": remote,
                        "default_workflow": default_workflow,
                        "workflows": selected_workflows
                    }
                    
                    # Add specific workflow configs
                    for wf in selected_workflows:
                        new_config[wf] = {
                            "prompt": f"prompts/recipes/{wf}.md",
                            "llm": "gemini",
                            "model": model
                        }
                    
                    if config_utils.save_repo_config(config_name, new_config, body_editor):
                        st.success(f"Saved configuration for {config_name}")
                        time.sleep(1)
                        st.rerun()



# --- STATUS ---
st.markdown(f"""
<div class="status-bar">
    READY | REPO: {st.session_state.repo} | TARGET: {actual_target} | SOURCE: {actual_source} | {datetime.now().strftime('%H:%M:%S')}
</div>
""", unsafe_allow_html=True)
