#!/usr/bin/env python3
import os
import sys
import json
import re

def process_signal(file_path, max_tokens=2000):
    """
    Process a signal file (log, coverage, test result) with prioritization.
    Heuristic: Errors and failures are prioritized.
    """
    if not os.path.exists(file_path):
        return f"[WARN] Signal file not found: {file_path}"

    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return f"[ERROR] Failed to read signal {file_path}: {e}"

    # Basic Prioritization: extract lines with FAIL, ERROR, Exception
    prioritized_lines = []
    other_lines = []
    
    lines = content.splitlines()
    for line in lines:
        if re.search(r'FAIL|ERROR|Exception|Traceback|\[x\]', line, re.IGNORECASE):
            prioritized_lines.append(line)
        else:
            other_lines.append(line)

    # Reconstruct with budget
    # Very rough token estimation: 4 chars per token
    max_chars = max_tokens * 4
    
    result_lines = prioritized_lines[:100] # Keep first 100 error lines
    remaining_chars = max_chars - sum(len(l) for l in result_lines)
    
    if remaining_chars > 0:
        # Add a bit of context or summary from other lines
        summary_lines = other_lines[:50] # Just a bit of context
        for line in summary_lines:
            if len(line) < remaining_chars:
                result_lines.append(line)
                remaining_chars -= len(line)
            else:
                break
    
    final_content = "\n".join(result_lines)
    if len(content) > len(final_content):
        final_content += f"\n... (truncated, original size: {len(content)} bytes)"
        
    return final_content

def process_signals_dir(directory, max_total_tokens=5000):
    if not os.path.isdir(directory):
        return []
    
    signals = []
    files = sorted(os.listdir(directory))
    tokens_per_file = max_total_tokens // (len(files) if files else 1)
    
    for file in files:
        full_path = os.path.join(directory, file)
        if os.path.isfile(full_path):
            signals.append({
                "name": file,
                "content": process_signal(full_path, tokens_per_file)
            })
            
    return signals

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: signal_processor.py <file_or_dir> [max_tokens]")
        sys.exit(1)

    path = sys.argv[1]
    max_tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    
    if os.path.isdir(path):
        print(json.dumps(process_signals_dir(path, max_tokens)))
    else:
        print(json.dumps([{"name": os.path.basename(path), "content": process_signal(path, max_tokens)}]))
