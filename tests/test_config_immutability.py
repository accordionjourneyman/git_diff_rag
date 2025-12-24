import pytest
from dataclasses import FrozenInstanceError
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.orchestrator import WorkflowConfig

def test_workflow_config_frozen():
    """Test that WorkflowConfig is immutable."""
    config = WorkflowConfig(repo_name="test_repo")
    
    with pytest.raises(FrozenInstanceError):
        config.repo_name = "new_name"
        
    with pytest.raises(FrozenInstanceError):
        config.workflow = "new_workflow"

def test_with_updates():
    """Test creating a new instance with updates."""
    config = WorkflowConfig(repo_name="test_repo")
    new_config = config.with_updates(workflow="pr_review")
    
    assert config.repo_name == "test_repo"
    assert config.workflow is None
    assert new_config.repo_name == "test_repo"
    assert new_config.workflow == "pr_review"
    assert config is not new_config

def test_json_serialization():
    """Test to_json and from_json methods."""
    config = WorkflowConfig(repo_name="test_json", workflow="demo")
    json_str = config.to_json()
    
    assert '"repo_name": "test_json"' in json_str
    assert '"workflow": "demo"' in json_str
    
    restored = WorkflowConfig.from_json(json_str)
    assert restored.repo_name == config.repo_name
    assert restored.workflow == config.workflow
