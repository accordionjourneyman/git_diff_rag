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
from streamlit_code_diff import st_code_diff
from streamlit_monaco import st_monaco
from scripts.render_prompt import render_template

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
    .hero-btn>button { background: linear-gradient(135deg, #238636, #2ea043) !important; color: white !important; height: 3.5rem !important; font-size: 1.1em !important; font-weight: 600 !important; border: none !important; border-radius: 8px !important; box-shadow: 0 4px 15px rgba(35, 134, 54, 0.3); }
    
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

# --- Auto-Logic & Smart Refs ---
repos = ui_utils.list_repositories()
if not st.session_state.repo and repos:
    st.session_state.repo = repos[0]

config = config_utils.load_repo_config(st.session_state.repo)
repo_path = config.get('path', '.') if config else '.'
branches = ui_utils.get_branches(repo_path)

# --- TOP BAR: Targeting (Including Specific Commits) ---
with st.container():
    c_repo, c_target, c_source = st.columns([2, 2, 2])
    
    with c_repo:
        new_repo = st.selectbox("🎯 Repository", options=repos, index=repos.index(st.session_state.repo) if st.session_state.repo in repos else 0)
        if new_repo != st.session_state.repo:
            st.session_state.repo = new_repo
            st.session_state.selected_file = None
            st.rerun()

    # Target Selection (Branch + Commit)
    with c_target:
        new_target = st.selectbox("📍 Target (Base)", options=branches, index=branches.index(st.session_state.target) if st.session_state.target in branches else 0)
        if new_target != st.session_state.target:
            st.session_state.target = new_target
            st.session_state.target_commit = None
            st.rerun()
        
        target_commits = ui_utils.get_commits(repo_path, st.session_state.target)
        target_commit_opts = ["Current HEAD"] + [c['hash'] for c in target_commits]
        st.caption("Commit (Optional)")
        new_target_commit = st.selectbox("Target Commit", options=target_commit_opts, index=0 if not st.session_state.target_commit else target_commit_opts.index(st.session_state.target_commit) if st.session_state.target_commit in target_commit_opts else 0, label_visibility="collapsed")
        st.session_state.target_commit = new_target_commit if new_target_commit != "Current HEAD" else None

    # Source Selection (Branch + Commit)
    with c_source:
        source_opts = ["Working Directory"] + branches
        new_source = st.selectbox("🌱 Source (Feature)", options=source_opts, index=source_opts.index(st.session_state.source) if st.session_state.source in source_opts else (2 if len(branches) > 1 else 0))
        if new_source != st.session_state.source:
            st.session_state.source = new_source
            st.session_state.source_commit = None
            st.rerun()
            
        if st.session_state.source != "Working Directory":
            source_commits = ui_utils.get_commits(repo_path, st.session_state.source)
            source_commit_opts = ["Current HEAD"] + [c['hash'] for c in source_commits]
            st.caption("Commit (Optional)")
            new_source_commit = st.selectbox("Source Commit", options=source_commit_opts, index=0 if not st.session_state.source_commit else source_commit_opts.index(st.session_state.source_commit) if st.session_state.source_commit in source_commit_opts else 0, label_visibility="collapsed")
            st.session_state.source_commit = new_source_commit if new_source_commit != "Current HEAD" else None
        else:
            st.session_state.source_commit = None

st.divider()

# Final Resolved Refs for Engine
actual_target, actual_source, _is_direct = ui_utils.get_smart_refs(repo_path, st.session_state.target, st.session_state.source, st.session_state.target_commit, st.session_state.source_commit)
changed_files = ui_utils.get_changed_files(repo_path, st.session_state.target, st.session_state.source, st.session_state.target_commit, st.session_state.source_commit)

if changed_files and not st.session_state.selected_file:
    st.session_state.selected_file = changed_files[0]

# --- MAIN LAYOUT ---
# Master Navigation Tabs
tab_review, tab_compose, tab_analyze, tab_history, tab_editor, tab_settings = st.tabs(["🔍 Review Changes", "🧱 Compose Prompt", "🚀 Run Analysis", "📜 History", "📝 Editor", "⚙️ Settings"])

# --- TAB 1: REVIEW ---
with tab_review:
    r_col1, r_col2 = st.columns([1, 3])
    
    with r_col1:
        st.markdown("### 📂 Files")
        if changed_files:
            # Simple Tree View Implementation
            file_tree = {}
            for f in changed_files:
                parts = f.split('/')
                current = file_tree
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = f

            def render_tree(node, prefix=""):
                for name, item in sorted(node.items()):
                    if isinstance(item, dict):
                        with st.expander(f"📂 {name}", expanded=True):
                            render_tree(item, prefix + name + "/")
                    else:
                        is_sel = item == st.session_state.selected_file
                        btn_label = f"{'👉 ' if is_sel else '📄 '}{name}"
                        if st.button(btn_label, key=f"tree_{item}", use_container_width=True):
                            st.session_state.selected_file = item
                            st.rerun()
            
            render_tree(file_tree)
        else:
            st.success("No changes detected.")

    with r_col2:
        if st.session_state.selected_file:
            st.markdown(f"### 📝 Diff: `{st.session_state.selected_file}`")
            st.caption(f"Comparing: `{actual_target}` ↔ `{actual_source}`")
            before = ui_utils.get_file_content(repo_path, actual_target, st.session_state.selected_file)
            after = ui_utils.get_file_content(repo_path, actual_source, st.session_state.selected_file)
            st_code_diff(before, after)
            
            # Context Tower (Findings) moved here for relevance
            findings = ui_utils.get_findings(repo_path, actual_target, actual_source, st.session_state.target_commit, st.session_state.source_commit)
            if findings:
                with st.expander(f"🚨 Rule Findings ({len(findings)})", expanded=False):
                    for f in findings:
                        sev = "high" if "security" in f['message'].lower() or "deprecated" in f['message'].lower() else "med"
                        st.markdown(f'<div class="finding-alert finding-{sev}"><b>{f["type"].upper()}</b>: {f["message"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Select a file from the tree to view the diff.")

# --- TAB 2: COMPOSE ---
with tab_compose:
    c_col1, c_col2 = st.columns([1, 2])
    
    with c_col1:
        st.markdown("### 📚 Library")
        library = ui_utils.list_prompt_library()
        recipes = [p for p in library if "recipes" in p['full_path']]
        snippets = [p for p in library if "snippets" in p['full_path']]
        
        with st.expander("Recipes", expanded=True):
            for r in recipes:
                if st.button(f"➕ {r['name']}", key=f"rec_{r['name']}", use_container_width=True):
                    if r['full_path'] not in st.session_state.active_bundle:
                        st.session_state.active_bundle.append(r['full_path'])
                        st.rerun()
        
        with st.expander("Snippets", expanded=False):
            for s in snippets:
                if st.button(f"➕ {s['name']}", key=f"snip_{s['name']}", use_container_width=True):
                    if s['full_path'] not in st.session_state.active_bundle:
                        st.session_state.active_bundle.append(s['full_path'])
                        st.rerun()

    with c_col2:
        st.markdown("### 🧱 Active Bundle")
        if not st.session_state.active_bundle:
            st.info("No blocks added. Bundle is empty.")
        else:
            for i, block_path in enumerate(st.session_state.active_bundle):
                name = os.path.basename(block_path)
                st.markdown(f'<div class="lego-block"><span><span class="lego-tag">MOD</span> {name}</span></div>', unsafe_allow_html=True)
            if st.button("🗑️ Clear Bundle", use_container_width=True):
                st.session_state.active_bundle = []
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 🧪 Preview")
        if not st.session_state.active_bundle:
            st.warning("Assemble a bundle to see preview.")
        else:
            composed = ""
            for p in st.session_state.active_bundle:
                try:
                    composed += render_template(p, "diff_sample", repo_name=st.session_state.repo) + "\n\n---\n\n"
                except Exception as e:
                    composed += f"Error: {e}\n"
            st.text_area("Final Prompt Payload", value=composed, height=400, disabled=True)

# --- TAB 3: ANALYZE ---
with tab_analyze:
    st.markdown("### 🚀 Execution")
    
    # Config Row
    c_tool, c_model = st.columns([1, 1])
    with c_tool:
        tool_choice = st.selectbox("Tool", ["Gemini API", "Gemini CLI", "GitHub Copilot CLI"])
    with c_model:
        # Default models to avoid blocking startup
        default_models = ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]
        
        if 'available_models' not in st.session_state:
            st.session_state.available_models = default_models
            
        def fetch_models():
            try:
                from scripts import call_gemini
                return call_gemini.list_models()
            except Exception as e:
                st.warning(f"Could not fetch models: {e}")
                return default_models

        # UI
        col_m_sel, col_m_btn = st.columns([3, 1])
        with col_m_sel:
            model_choice = st.selectbox("Model", st.session_state.available_models, index=0)
        with col_m_btn:
            if st.button("🔄", help="Refresh Model List"):
                st.session_state.available_models = fetch_models()
                st.rerun()

    # Launch Button Area
    st.markdown('<div class="hero-btn">', unsafe_allow_html=True)
    is_bundle = len(st.session_state.active_bundle) > 0
    btn_label = "🤖 AUTOMATED REVIEW" if is_bundle else "🚀 LAUNCH ANALYSIS"
    
    if st.button(btn_label, use_container_width=True, disabled=st.session_state.is_executing):
        if not is_bundle:
            st.warning("Assemble a bundle first! Go to the 'Compose Prompt' tab.")
        else:
            st.session_state.is_executing = True
            st.session_state.completed_steps = []
            st.session_state.execution_times = {}
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.is_executing:
        st.markdown("---")
        st.markdown("### 📊 Live Status")
        
        # Mermaid DAG
        dag_code = ui_utils.generate_mermaid_dag(
            st.session_state.active_bundle, 
            st.session_state.current_step, 
            st.session_state.completed_steps
        )
        st.markdown(f"```mermaid\n{dag_code}\n```")
        
        # Execution Logic
        with st.status("Running Analysis...", expanded=True) as status:
            try:
                # 1. Fetch Diff
                st.write("📥 Fetching Diff...")
                diff_content = ui_utils.get_diff(
                    repo_path, 
                    actual_target, 
                    actual_source, 
                    target_commit=st.session_state.target_commit, 
                    source_commit=st.session_state.source_commit
                )
                
                # 2. Render Prompt
                st.write("🧱 Rendering Prompt...")
                
                # Intelligent Stacking: Shared Context
                full_prompt = f"# SHARED CONTEXT\n\n## GIT DIFF\n\n```diff\n{diff_content}\n```\n\n"
                
                for p in st.session_state.active_bundle:
                    st.write(f" - Processing {os.path.basename(p)}...")
                    # Pass inject_diff_content=False to avoid duplication
                    part = render_template(p, diff_content, repo_name=st.session_state.repo, inject_diff_content=False)
                    full_prompt += f"\n---\n\n{part}"
                
                # Prepare Output
                timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
                out_folder = f"output/{timestamp}-{st.session_state.repo}-ui_run"
                os.makedirs(out_folder, exist_ok=True)
                
                prompt_path = f"{out_folder}/prompt.txt"
                response_path = f"{out_folder}/response.md"
                diff_path = f"{out_folder}/diff.patch"

                with open(prompt_path, "w") as f:
                    f.write(full_prompt)
                with open(diff_path, "w") as f:
                    f.write(diff_content)

                # 3. Call AI Model
                st.write(f"🤖 Calling {tool_choice} ({model_choice})...")
                response = ""
                
                if tool_choice == "Gemini API":
                    from scripts import call_gemini
                    response = call_gemini.call_with_retry(full_prompt, model=model_choice)
                    with open(response_path, "w") as f:
                        f.write(response)
                        
                elif tool_choice == "GitHub Copilot CLI":
                    # Direct Python integration
                    from scripts import call_copilot_cli
                    
                    try:
                        response = call_copilot_cli.call_copilot(
                            full_prompt,
                            allow_tools=['shell(git)', 'write'],
                            timeout=300
                        )
                        with open(response_path, "w") as f:
                            f.write(response)
                    except call_copilot_cli.CopilotNotInstalledError:
                        raise RuntimeError("GitHub Copilot CLI is not installed. See: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli")
                    except call_copilot_cli.CopilotAuthError:
                        raise RuntimeError("GitHub Copilot CLI is not authenticated. Run 'copilot' in terminal to authenticate.")
                    
                else:  # Gemini CLI
                    # CLI Call (via launch_agent.sh)
                    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "launch_agent.sh")
                    
                    # launch_agent.sh arguments: AGENT PROMPT_FILE APPLY
                    # We use "gemini" as agent, prompt_path, and "false" for apply
                    result = subprocess.run(
                        ["bash", script_path, "gemini", prompt_path, "false"],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        raise RuntimeError(f"CLI Error: {result.stderr}\nOutput: {result.stdout}")
                    
                    # The agent script writes to prompt_path + ".session.log"
                    log_path = f"{prompt_path}.session.log"
                    if os.path.exists(log_path):
                        with open(log_path, "r") as f:
                            response = f.read()
                        # Also save to standard response.md for consistency
                        with open(response_path, "w") as f:
                            f.write(response)
                    else:
                        raise RuntimeError(f"CLI did not generate session log at {log_path}")
                
                # 4. Save Results
                st.write("💾 Saving Results...")
                diff_hash = hashlib.md5(diff_content.encode()).hexdigest()
                prompt_hash = hashlib.md5(full_prompt.encode()).hexdigest()
                
                # DB
                db_manager.save_cache(
                    diff_hash=diff_hash,
                    prompt_hash=prompt_hash,
                    model=model_choice,
                    response=response,
                    repo_name=st.session_state.repo,
                    summary=response[:100] + "...",
                    tags="ui_run"
                )
                
                status.update(label="Analysis Complete!", state="complete", expanded=False)
                st.session_state.completed_steps = st.session_state.active_bundle
                st.session_state.is_executing = False
                st.success(f"Analysis saved to `{out_folder}`")
                
            except Exception as e:
                status.update(label="Analysis Failed", state="error")
                st.error(f"Execution failed: {e}")
                st.session_state.is_executing = False

# --- TAB 4: HISTORY ---
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

# --- TAB 5: EDITOR ---
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

# --- TAB 6: SETTINGS ---
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

# --- FOOTER / CONFIG ---
st.markdown("---")
with st.expander("⚙️ Global Configuration", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox("Code Lang", ["Auto", "Python", "Go", "TS"])
    with col2:
        st.selectbox("Answer Lang", ["English", "Portuguese", "Spanish"])
    with col3:
        st.checkbox("With Docs", value=True)

# Token Meter
total_diff = ui_utils.get_diff(repo_path, actual_target, actual_source, target_commit=st.session_state.target_commit, source_commit=st.session_state.source_commit)
usage = (len(total_diff) + 5000) / 128000
st.markdown(f"""
<div class="token-meter-bg"><div class="token-meter-fill" style="width: {min(usage*100,100):.1f}%;"></div></div>
<div style="font-size: 0.8em; text-align: right; color: #8b949e;">{min(usage*128, 128):.1f}k / 128k used</div>
""", unsafe_allow_html=True)

# --- STATUS ---
st.markdown(f"""
<div class="status-bar">
    READY | REPO: {st.session_state.repo} | TARGET: {actual_target} | SOURCE: {actual_source} | {datetime.now().strftime('%H:%M:%S')}
</div>
""", unsafe_allow_html=True)
