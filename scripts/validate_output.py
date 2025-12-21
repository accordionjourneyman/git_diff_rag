#!/usr/bin/env python3
"""scripts/validate_output.py - Validate LLM-generated output"""
import json
import sys
from pathlib import Path

def extract_json(content: str) -> str:
    """Extract JSON from markdown code blocks if present."""
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        if end > start:
            return content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        if end > start:
            return content[start:end].strip()
    return content

def validate_json_output(file_path: str) -> bool:
    """Validate that output contains valid JSON (for API call workflows)."""
    try:
        content = Path(file_path).read_text(encoding='utf-8')
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return False
    
    json_content = extract_json(content)
    
    try:
        data = json.loads(json_content)
        
        # Basic validation for API call format
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    print(f"[WARN] Array item is not an object: {type(item)}")
                    return False
                # Optional: Add specific schema validation here if needed
        
        print(f"[OK] Valid JSON with {len(data) if isinstance(data, list) else 1} item(s)")
        return True
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: validate_output.py <output_file> [--strict]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    strict = "--strict" in sys.argv
    
    if not Path(file_path).exists():
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)
    
    valid = validate_json_output(file_path)
    
    if not valid and strict:
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
