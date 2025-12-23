#!/usr/bin/env python3
import os
import sys
import yaml
import re

def load_rules(repo_path):
    # Load rules from repository-setup or repo root
    rules_paths = [
        os.path.join(repo_path, '.ragrules.yaml'),
        os.path.join(os.getcwd(), 'repository-setup', 'global_rules.yaml')
    ]
    
    all_rules = {"dependencies": [], "deprecations": []}
    for path in rules_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data:
                        all_rules["dependencies"].extend(data.get("dependencies", []))
                        all_rules["deprecations"].extend(data.get("deprecations", []))
            except Exception as e:
                print(f"[WARN] Failed to load rules from {path}: {e}", file=sys.stderr)
    return all_rules

def check_diff(diff_content, rules, ignore_patterns=None):
    findings = []
    ignore_patterns = ignore_patterns or []

    # Process Deprecations
    for rule in rules.get("deprecations", []):
        pattern = rule.get("pattern")
        if any(re.search(p, pattern) for p in ignore_patterns):
            continue
            
        if re.search(pattern, diff_content):
            findings.append({
                "type": "deprecation",
                "message": f"Deprecated pattern found: {pattern}. {rule.get('reason', '')}",
                "replacement": rule.get("replacement")
            })

    # Process Dependencies (Simplified: if file A changes, file B must change)
    for rule in rules.get("dependencies", []):
        trigger = rule.get("trigger_file_pattern")
        required = rule.get("required_file_pattern")
        
        if re.search(f"diff --git a/.*{trigger}", diff_content):
            if not re.search(f"diff --git a/.*{required}", diff_content):
                findings.append({
                    "type": "dependency_miss",
                    "message": f"Change in {trigger} usually requires an update in {required}."
                })

    return findings

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: checker_engine.py <repo_path> <diff_file>")
        sys.exit(1)

    repo_path = sys.argv[1]
    diff_file = sys.argv[2]

    if not os.path.exists(diff_file):
        print(f"Diff file not found: {diff_file}")
        sys.exit(1)

    with open(diff_file, 'r') as f:
        diff_content = f.read()

    rules = load_rules(repo_path)
    # Basic suppression via .ragignore (stub)
    ignore_patterns = []
    ignore_file = os.path.join(repo_path, '.ragignore')
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r') as f:
            for line in f:
                if line.startswith('rag:disable '):
                    ignore_patterns.append(line.replace('rag:disable ', '').strip())

    findings = check_diff(diff_content, rules, ignore_patterns)
    import json
    print(json.dumps(findings))
