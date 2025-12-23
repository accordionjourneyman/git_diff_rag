#!/usr/bin/env python3
import os
import sys
import fnmatch

def discover_docs(repo_path, changed_files=None):
    """
    Recursively discover markdown documentation.
    If changed_files is provided, it can prioritize or filter relevant docs.
    """
    docs = []
    # Standard patterns to search
    patterns = ['*.md', '*.markdown', 'ARCHITECTURE.md', 'CONTRIBUTING.md']
    exclude_dirs = {'.git', '.venv', 'venv', 'node_modules', '__pycache__'}

    for root, dirs, files in os.walk(repo_path):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if any(fnmatch.fnmatch(file, p) for p in patterns):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)
                
                # Heuristic: Match filename segments with changed file segments
                relevance = 0
                if changed_files:
                    file_segments = set(rel_path.lower().replace('/', ' ').replace('.', ' ').split())
                    for cf in changed_files:
                        cf_segments = set(cf.lower().replace('/', ' ').replace('.', ' ').split())
                        common = file_segments.intersection(cf_segments)
                        if common:
                            relevance += len(common)
                
                docs.append({
                    "path": rel_path,
                    "full_path": full_path,
                    "relevance": relevance
                })

    # Sort by relevance then path
    docs.sort(key=lambda x: (-x['relevance'], x['path']))
    return docs

def load_doc_content(full_path, max_chars=5000):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read(max_chars)
            if len(content) == max_chars:
                content += "\n... (truncated)"
            return content
    except Exception as e:
        return f"[ERROR] Failed to read {full_path}: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: docs_loader.py <repo_path> [changed_files_json]")
        sys.exit(1)

    repo_path = sys.argv[1]
    changed_files = []
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        try:
            with open(sys.argv[2], 'r') as f:
                changed_files = json.load(f)
        except:
            pass

    discovered = discover_docs(repo_path, changed_files)
    
    # For integration, we might want to return a few most relevant ones
    # For now, let's just print a summary or JSON
    import json
    results = []
    for doc in discovered[:5]: # Top 5 relevant docs
        results.append({
            "path": doc['path'],
            "content": load_doc_content(doc['full_path'])
        })
    
    print(json.dumps(results))
