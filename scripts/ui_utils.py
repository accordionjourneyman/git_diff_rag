import os
import subprocess
import glob
import sys
import json

# Add scripts to path for internal modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import db_manager
import checker_engine

def list_repositories():
    """List all configured repositories in repository-setup/."""
    repos = []
    files = glob.glob("repository-setup/*.md")
    for f in files:
        name = os.path.basename(f).replace(".md", "")
        if name.upper() not in ["README", "TEMPLATE"]:
            repos.append(name)
    return sorted(repos)

def get_branches(repo_path):
    """Get all local and remote branches for a repository."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "branch", "-a", "--format=%(refname:short)"],
            capture_output=True, text=True, check=True
        )
        branches = list(set([b.strip() for b in result.stdout.splitlines() if b.strip()]))
        # Priority sort: HEAD, main, master first
        priority = ['HEAD', 'main', 'master', 'origin/main', 'origin/master']
        branches.sort(key=lambda x: (priority.index(x) if x in priority else 999, x))
        return branches
    except Exception:
        return ["main"]

def get_smart_refs(repo_path, target, source, target_commit=None, source_commit=None):
    """
    Intelligently determine refs. 
    If specific commits are provided, we use direct comparison (..).
    If only branches are provided, we use merge-base comparison (...).
    """
    if source == "Working Directory":
        final_target = target_commit if target_commit and target_commit != "None" else target
        return final_target, None, True

    final_target = target_commit if target_commit and target_commit != "None" else target
    final_source = source_commit if source_commit and source_commit != "None" else source
    
    # Use ".." for direct A->B diff if either is a specific commit
    # Use "..." for A...B (diff from merge-base) for branches
    is_direct = (target_commit and target_commit != "None") or (source_commit and source_commit != "None")
    
    if final_target == final_source:
        branches = get_branches(repo_path)
        base = "main" if "main" in branches else ("master" if "master" in branches else target)
        return base, "HEAD", False # False means use ... for branches
    return final_target, final_source, is_direct

def get_commits(repo_path, ref, limit=20):
    """Get list of recent commits for a reference."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", ref, "-n", str(limit), "--format=%h - %s (%cr)"],
            capture_output=True, text=True, check=True
        )
        return [{"hash": line.split(" - ")[0], "label": line} for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []

def get_changed_files(repo_path, target, source, target_commit=None, source_commit=None):
    """Get list of files changed between target and source."""
    t, s, is_direct = get_smart_refs(repo_path, target, source, target_commit, source_commit)
    
    cmd = ["git", "-C", repo_path, "diff", "--name-only"]
    if s is None:
        cmd.append(t)
    else:
        sep = ".." if is_direct else "..."
        cmd.append(f"{t}{sep}{s}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, check=True
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception:
        return []

def get_file_content(repo_path, ref, file_path):
    """Get content of a file at a specific git reference."""
    if ref is None:
        # Working Directory: Read from disk
        try:
            with open(os.path.join(repo_path, file_path), 'r') as f:
                return f.read().replace('\r\n', '\n')
        except:
            return ""
            
    try:
        # Git Reference: Read from git
        result = subprocess.run(
            ["git", "-C", repo_path, "show", f"{ref}:{file_path}"],
            capture_output=True, text=True, check=True
        )
        # Normalize line endings to LF to avoid false positives in diff viewers
        return result.stdout.replace('\r\n', '\n')
    except Exception:
        # If git show fails, it likely means the file doesn't exist in that ref (New file or Deleted file)
        return ""

def get_diff(repo_path, target, source, file_path=None, target_commit=None, source_commit=None):
    """Get raw git diff between target and source for a specific file or whole repo."""
    t, s, is_direct = get_smart_refs(repo_path, target, source, target_commit, source_commit)
    
    cmd = ["git", "-C", repo_path, "diff"]
    if s is None:
        cmd.append(t)
    else:
        sep = ".." if is_direct else "..."
        cmd.append(f"{t}{sep}{s}")

    if file_path:
        cmd.append("--")
        cmd.append(file_path)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except Exception as e:
        return f"Error getting diff: {e}"

def get_findings(repo_path, target, source, target_commit=None, source_commit=None):
    """Extract real findings using the checker engine for the active diff."""
    diff_content = get_diff(repo_path, target, source, target_commit=target_commit, source_commit=source_commit)
    rules = checker_engine.load_rules(repo_path)
    
    ignore_patterns = []
    ignore_file = os.path.join(repo_path, '.ragignore')
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r') as f:
            for line in f:
                if line.startswith('rag:disable '):
                    ignore_patterns.append(line.replace('rag:disable ', '').strip())
    
    findings = checker_engine.check_diff(diff_content, rules, ignore_patterns)
    # Enrich findings with file information for UI highlighting
    # (Simple heuristic: finding message might mention the file)
    return findings

def get_history(repo_name=None, limit=5, search_query=None):
    """Retrieve filtered history entries via db_manager."""
    db_manager.init_db()
    return db_manager.get_context(repo_name, limit, search_query)

def get_session_details(session_id):
    """Retrieve full analysis details for a session replay."""
    db_manager.init_db()
    conn = db_manager.sqlite3.connect(db_manager.DB_PATH)
    conn.row_factory = db_manager.sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM analysis_history WHERE id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def list_prompt_library():
    """Recursively list all markdown files in the prompts/ directory."""
    library = []
    prompts_dir = "prompts"
    for root, dirs, files in os.walk(prompts_dir):
        for file in files:
            if file.endswith(".md"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, prompts_dir)
                library.append({
                    "name": rel_path,
                    "full_path": os.path.abspath(full_path)
                })
    return sorted(library, key=lambda x: x['name'])

def read_file(path):
    """Read file content safely."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def save_file(path, content):
    """Save file content safely."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False

def generate_mermaid_dag(active_bundle, current_step=None, completed_steps=None):
    """Generate Mermaid DAG code for the active bundle."""
    if not active_bundle:
        return ""
    
    completed_steps = completed_steps or []
    lines = ["graph TD"]
    
    # Define styles
    lines.append("classDef pending fill:#21262d,stroke:#30363d,color:#8b949e")
    lines.append("classDef running fill:#1f6feb,stroke:#58a6ff,color:#fff,stroke-width:2px")
    lines.append("classDef done fill:#238636,stroke:#2ea043,color:#fff")
    
    nodes = []
    for i, path in enumerate(active_bundle):
        name = os.path.basename(path).replace(".md", "")
        node_id = f"node{i}"
        
        # Determine status
        status = "pending"
        if path == current_step:
            status = "running"
        elif path in completed_steps:
            status = "done"
            
        nodes.append(f'{node_id}["{name}"]::: {status}')
        
    lines.extend(nodes)
    
    # Simple linear chain for now
    for i in range(len(nodes) - 1):
        lines.append(f"node{i} --> node{i+1}")
        
    return "\n".join(lines)
