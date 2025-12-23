import pytest
import os
import json
import sys
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))
import signal_processor
import docs_loader
import checker_engine

class TestContextComponents:
    
    def test_signal_processor(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("ERROR: Connection failed\nINFO: Success")
        
        # In script the logic handles a list or single via process_signals_dir / process_signal
        # Let's test process_signal
        content = signal_processor.process_signal(str(log_file))
        assert "ERROR: Connection failed" in content

    def test_docs_loader(self, tmp_path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        doc1 = docs_dir / "api.md"
        doc1.write_text("# API Docs\nDetails here.")
        
        # Test discovery
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                (str(docs_dir), [], ["api.md", "other.txt"])
            ]
            found = docs_loader.discover_docs(str(tmp_path))
            assert any(d['path'].endswith("api.md") for d in found)
            assert not any(d['path'].endswith("other.txt") for d in found)

    def test_checker_engine(self, tmp_path):
        rules = {
            "deprecations": [
                {"pattern": "old_fn", "replacement": "new_fn", "reason": "Legacy"}
            ],
            "dependencies": []
        }
        
        diff_content = "diff --git a/a.py b/a.py\n+ old_fn()"
        
        findings = checker_engine.check_diff(diff_content, rules)
        assert len(findings) == 1
        assert findings[0]['type'] == 'deprecation'
        assert findings[0]['replacement'] == 'new_fn'

    def test_checker_engine_ragignore(self, tmp_path):
        rules = {"deprecations": [{"pattern": 'old_fn'}], "dependencies": []}
        ignore_patterns = ["old_fn"]
        
        diff_content = "diff --git a/a.py b/a.py\n+ old_fn()"
        
        # Should be ignored (logic in script uses re.search(p, pattern))
        findings = checker_engine.check_diff(diff_content, rules, ignore_patterns)
        assert len(findings) == 0
