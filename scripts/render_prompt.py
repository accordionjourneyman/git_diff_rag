#!/usr/bin/env python3
# scripts/render_prompt.py - with meta introspection & smart defaults
import sys
import os
import re
import json
from jinja2 import Environment, meta, FileSystemLoader, StrictUndefined

def detect_languages(diff_text):
    # Scan for "diff --git a/path/to/file.ext"
    ext_pattern = re.compile(r'diff --git a/.*\.(\w+)\s+b/')
    extensions = set(ext_pattern.findall(diff_text))
    
    # Simple Ext -> Lang Mapping
    lang_map = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript', 'java': 'java',
        'go': 'go', 'rs': 'rust', 'c': 'c', 'cpp': 'cpp', 'html': 'html',
        'css': 'css', 'sql': 'sql', 'md': 'markdown', 'sh': 'bash', 'yaml': 'yaml',
        'json': 'json', 'rb': 'ruby', 'php': 'php', 'swift': 'swift', 'kt': 'kotlin'
    }
    
    languages = set()
    for ext in extensions:
        if ext in lang_map:
            languages.add(lang_map[ext])
    
    return list(languages) if languages else ['unknown']

def render_template(template_path, diff_content, repo_name="unknown", context_data=None, 
                    signals_data=None, docs_data=None, findings_data=None, env_vars=None, 
                    inject_diff_content=True, commit_history_data=None, target_ref=None, 
                    source_ref=None, OUTPUT_DIR=None, **kwargs):
    if env_vars is None:
        env_vars = os.environ

    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    prompts_dir = os.path.join(repo_root, 'prompts')

    # Init Jinja2 with loader
    env = Environment(loader=FileSystemLoader([prompts_dir, repo_root, os.getcwd()]), undefined=StrictUndefined)

    # Config extraction
    code_lang_config = env_vars.get('CODE_LANGUAGE', 'auto')
    code_langs = detect_languages(diff_content) if code_lang_config == 'auto' else [code_lang_config]

    provided = {
        "DIFF_CONTENT": diff_content if inject_diff_content else "<!-- Diff provided in Shared Context -->",
        "REPO_NAME": repo_name,
        "BUNDLE_PATH": env_vars.get('BUNDLE_PATH', 'unknown'),
        "CODE_LANGS": code_langs,
        "CODE_LANG": code_langs[0] if code_langs else 'text',
        "ANSWER_LANG": env_vars.get('ANSWER_LANGUAGE', 'english'),
        "COMMENT_LANG": env_vars.get('COMMENT_LANGUAGE', 'english'),
        "OUTPUT_FORMAT": env_vars.get('OUTPUT_FORMAT', 'markdown'),
        "CONTEXT": context_data or [],
        "SIGNALS": signals_data or [],
        "DOCS": docs_data or [],
        "FINDINGS": findings_data or [],
        # New: Commit history context
        "COMMIT_HISTORY": commit_history_data or {},
        "TARGET_REF": target_ref or "unknown",
        "SOURCE_REF": source_ref or "unknown",
        "OUTPUT_DIR": OUTPUT_DIR or "unknown"
    }
    
    # Add any additional kwargs to the template context
    provided.update(kwargs)

    # Load Template
    if os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_src = f.read()
            template = env.from_string(template_src)
        except Exception as e:
            raise RuntimeError(f"Failed to read template: {e}")
    else:
        raise FileNotFoundError(f"Template file not found: {template_path}")

    try:
        return template.render(**provided)
    except Exception as e:
        raise RuntimeError(f"Render failed: {e}")

def main():
    if len(sys.argv) < 3:
        print("Usage: render_prompt.py <template_file> <diff_file> [repo_name] [context_file] [signals_file] [docs_file] [findings_file]")
        sys.exit(1)

    template_path = sys.argv[1]
    diff_file = sys.argv[2]
    repo_name = sys.argv[3] if len(sys.argv) > 3 else "unknown"
    context_file = sys.argv[4] if len(sys.argv) > 4 else None
    signals_file = sys.argv[5] if len(sys.argv) > 5 else None
    docs_file = sys.argv[6] if len(sys.argv) > 6 else None
    findings_file = sys.argv[7] if len(sys.argv) > 7 else None

    # Read Diff
    try:
        with open(diff_file, 'r', encoding='utf-8') as f:
            diff_content = f.read()
    except FileNotFoundError:
        diff_content = diff_file

    def load_json(path):
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load {path}: {e}", file=sys.stderr)
        return []

    context_data = load_json(context_file)
    signals_data = load_json(signals_file)
    docs_data = load_json(docs_file)
    findings_data = load_json(findings_file)

    try:
        result = render_template(template_path, diff_content, repo_name, context_data, signals_data, docs_data, findings_data)
        print(result)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
