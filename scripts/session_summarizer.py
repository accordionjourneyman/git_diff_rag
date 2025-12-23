#!/usr/bin/env python3
# scripts/session_summarizer.py - Learning from Agent Sessions
import sys
import os
import json
import subprocess
import re

def log_msg(msg):
    print(f"[$(date +'%Y-%m-%d %H:%M:%S')] [SUMMARIZER] {msg}")

def run_summarizer(log_file, bundle_path):
    if not os.path.exists(log_file):
        log_msg(f"Log file not found: {log_file}")
        return None

    # We use call_gemini.py directly but first we need to render the prompt
    # The summarizer recipe takes BUNDLE_PATH
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recipe_path = os.path.join(os.path.dirname(script_dir), "prompts/recipes/meta/summarizer.md")
    
    rendered_prompt_file = os.path.join(bundle_path, "summarizer_prompt_rendered.txt")
    llm_result_file = os.path.join(bundle_path, "session_summary_raw.md")

    # Render
    subprocess.run([
        sys.executable, os.path.join(script_dir, "render_prompt.py"),
        recipe_path, log_file, "unknown"
    ], env={**os.environ, "BUNDLE_PATH": bundle_path}, stdout=open(rendered_prompt_file, 'w'))

    # Call LLM
    subprocess.run([
        sys.executable, os.path.join(script_dir, "call_gemini.py"),
        rendered_prompt_file, llm_result_file
    ])

    if not os.path.exists(llm_result_file):
        return None

    with open(llm_result_file, 'r') as f:
        content = f.read()
    
    # Extract JSON
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            return None
    return None

def interactive_edit(data):
    print("\n" + "="*80)
    print("🤖 AI Session Summary (Draft)")
    print("="*80)
    print(f"Headline: {data.get('summary')}")
    print("Lessons:")
    for l in data.get('lessons', []):
        print(f"  - {l}")
    print(f"Tags: {', '.join(data.get('tags', []))}")
    print(f"Status: {data.get('status')}")
    print("="*80)
    
    choice = input("\nCommit to repository memory? [y]es / [n]o / [e]dit: ").lower()
    if choice == 'y':
        return data
    elif choice == 'e':
        # Simple interactive edit
        data['summary'] = input(f"New Headline [{data['summary']}]: ") or data['summary']
        new_lessons = input("New Lessons (comma separated): ")
        if new_lessons:
            data['lessons'] = [l.strip() for l in new_lessons.split(',')]
        data['tags'] = input(f"New Tags [{', '.join(data['tags'])}]: ").split(',') or data['tags']
        return data
    else:
        log_msg("Discarding session summary.")
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: session_summarizer.py <log_file> <bundle_path> [repo_name] [diff_hash] [prompt_hash]")
        sys.exit(1)

    log_file = sys.argv[1]
    bundle_path = sys.argv[2]
    repo_name = sys.argv[3] if len(sys.argv) > 3 else "unknown"
    diff_hash = sys.argv[4] if len(sys.argv) > 4 else "0"
    prompt_hash = sys.argv[5] if len(sys.argv) > 5 else "0"

    summary_data = run_summarizer(log_file, bundle_path)
    if not summary_data:
        log_msg("Failed to generate session summary.")
        sys.exit(1)

    reviewed_data = interactive_edit(summary_data)
    if reviewed_data:
        # Save to DB
        script_dir = os.path.dirname(os.path.abspath(__file__))
        summary_text = "\n".join(reviewed_data.get('lessons', []))
        tags_str = ",".join(reviewed_data.get('tags', []))
        
        subprocess.run([
            sys.executable, os.path.join(script_dir, "db_manager.py"),
            "save", diff_hash, prompt_hash, "summarizer", 
            summary_text, "0.0", repo_name, 
            reviewed_data.get('summary'), tags_str, "agent_session"
        ])
        log_msg("Session committed to memory.")

if __name__ == "__main__":
    main()
