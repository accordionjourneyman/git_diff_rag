import yaml
import os

def load_repo_config(repo_name):
    """Load repository configuration from repository-setup/<name>.md."""
    path = f"repository-setup/{repo_name}.md"
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse frontmatter
        if content.startswith('---'):
            _, frontmatter, _ = content.split('---', 2)
            config = yaml.safe_load(frontmatter)
            return config
    except Exception as e:
        print(f"[ERROR] Failed to load config for {repo_name}: {e}")
    return None

def get_workflows(config):
    """Extract list of available workflows from config."""
    if not config:
        return []
    
    # Workflows can be a simple list or more complex
    workflows_section = config.get('workflows', [])
    if isinstance(workflows_section, list):
        return workflows_section
    return list(workflows_section.keys())

def get_workflow_details(config, workflow_name):
    """Get details (prompt, model, etc) for a specific workflow."""
    if not config:
        return {}
    return config.get(workflow_name, {})

def save_repo_config(repo_name, config_data, body_content=""):
    """Save repository configuration to repository-setup/<name>.md."""
    path = f"repository-setup/{repo_name}.md"
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write("---\n")
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            f.write("---\n")
            if body_content:
                f.write(body_content)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config for {repo_name}: {e}")
        return False
