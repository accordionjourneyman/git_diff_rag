#!/usr/bin/env python3
import json
import sys
import os

def convert_to_sarif(findings, repo_name="git_diff_rag"):
    """
    Convert a list of findings to SARIF format.
    Each finding should have: ruleId, level, message, path, line (optional).
    """
    sarif = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Git Diff RAG",
                        "informationUri": "https://github.com/accordionjourneyman/git_diff_rag",
                        "rules": []
                    }
                },
                "results": []
            }
        ]
    }

    rules = {}
    results = []

    for finding in findings:
        rule_id = finding.get("ruleId", "GENERIC_001")
        level = finding.get("level", "warning").lower()
        if level not in ["error", "warning", "note"]:
            level = "warning"
            
        message = finding.get("message", "No message provided")
        path = finding.get("path", "unknown")
        line = finding.get("line", 1)

        # Ensure rule exists
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "shortDescription": {"text": finding.get("ruleDescription", rule_id)}
            }

        result = {
            "ruleId": rule_id,
            "level": level,
            "message": {"text": message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": path},
                        "region": {"startLine": int(line)}
                    }
                }
            ]
        }
        results.append(result)

    sarif["runs"][0]["tool"]["driver"]["rules"] = list(rules.values())
    sarif["runs"][0]["results"] = results
    return sarif

def extract_json_from_markdown(text):
    # Try to find JSON block
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    return text

if __name__ == "__main__":
    import re
    if len(sys.argv) < 2:
        print("Usage: json_to_sarif.py <llm_result_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "analysis.sarif"

    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        sys.exit(1)

    with open(input_file, 'r') as f:
        content = f.read()

    json_str = extract_json_from_markdown(content)
    try:
        data = json.loads(json_str)
        # Handle if data is a dict with a list of findings inside
        if isinstance(data, dict):
            findings = data.get("findings", [])
        elif isinstance(data, list):
            findings = data
        else:
            findings = []
            
        sarif_data = convert_to_sarif(findings)
        with open(output_file, 'w') as f:
            json.dump(sarif_data, f, indent=2)
        print(f"Successfully converted to {output_file}")
    except Exception as e:
        print(f"Failed to parse JSON or convert: {e}")
        # Fallback: create empty but valid SARIF
        sarif_data = convert_to_sarif([])
        with open(output_file, 'w') as f:
            json.dump(sarif_data, f, indent=2)
        sys.exit(1)
