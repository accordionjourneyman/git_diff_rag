#!/usr/bin/env python3
# scripts/render_prompt.py - with meta introspection & smart defaults
import sys
import os
import re
from jinja2 import Environment, meta, FileSystemLoader

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

def render_template(template_path, diff_content, repo_name="unknown", env_vars=None):
    if env_vars is None:
        env_vars = os.environ

    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    prompts_dir = os.path.join(repo_root, 'prompts')

    # Init Jinja2 with loader for relative includes (e.g. {% include 'macros/_common.md' %})
    # We search in prompts_dir explicitly so 'macros/' works.
    env = Environment(loader=FileSystemLoader([prompts_dir, repo_root, os.getcwd()]))

    # Config extraction
    code_lang_config = env_vars.get('CODE_LANGUAGE', 'auto')
    code_langs = detect_languages(diff_content) if code_lang_config == 'auto' else [code_lang_config]

    provided = {
        "DIFF_CONTENT": diff_content,
        "REPO_NAME": repo_name,
        "BUNDLE_PATH": env_vars.get('BUNDLE_PATH', 'unknown'),
        "CODE_LANGS": code_langs,
        "CODE_LANG": code_langs[0] if code_langs else 'text', # For legacy macros using single string
        "ANSWER_LANG": env_vars.get('ANSWER_LANGUAGE', 'english'),
        "COMMENT_LANG": env_vars.get('COMMENT_LANGUAGE', 'english'),
        "OUTPUT_FORMAT": env_vars.get('OUTPUT_FORMAT', 'markdown')
    }

    # Load Template
    if os.path.exists(template_path):
        # env.from_string(src) renders using the env's loader for includes
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_src = f.read()
            template = env.from_string(template_src)
        except Exception as e:
            raise RuntimeError(f"Failed to read template: {e}")
    else:
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Introspection (Validation Gate)
    try:
        ast = env.parse(template_src)
        required_vars = meta.find_undeclared_variables(ast)
        missing = [v for v in required_vars if v not in provided]

        if missing:
            raise ValueError(f"Template requires missing vars: {missing}")
            
        return template.render(**provided)
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Render failed: {e}")

def main():
    if len(sys.argv) < 3:
        print("Usage: render_prompt.py <template_file> <diff_file> [repo_name]")
        sys.exit(1)

    template_path = sys.argv[1]
    diff_file = sys.argv[2]
    repo_name = sys.argv[3] if len(sys.argv) > 3 else "unknown"

    # Read Context
    try:
        with open(diff_file, 'r', encoding='utf-8') as f:
            diff_content = f.read()
    except FileNotFoundError:
        diff_content = diff_file # fallback for raw string arg

    try:
        result = render_template(template_path, diff_content, repo_name)
        print(result)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

