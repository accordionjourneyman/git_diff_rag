import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))
import session_summarizer

class TestIntelligenceLoop:
    
    def test_run_summarizer_mock(self, tmp_path):
        bundle_path = tmp_path / "bundle"
        bundle_path.mkdir()
        log_file = bundle_path / "session.log"
        log_file.write_text("dummy log")
        
        # Mock result from LLM
        llm_result = bundle_path / "session_summary_raw.md"
        llm_result.write_text("""
Here is the summary:
```json
{
  "summary": "Extracted Helper",
  "lessons": ["Use validate_x helper"],
  "tags": ["refactor"],
  "status": "success"
}
```
""")
        
        with patch('subprocess.run') as mock_run:
            # We don't want to actually run the LLM or render
            data = session_summarizer.run_summarizer(str(log_file), str(bundle_path))
            assert data['summary'] == "Extracted Helper"
            assert "refactor" in data['tags']

    def test_interactive_edit_yes(self):
        data = {"summary": "Old Sum", "lessons": ["L1"], "tags": ["T1"], "status": "success"}
        with patch('builtins.input', return_value='y'):
            res = session_summarizer.interactive_edit(data)
            assert res == data

    def test_interactive_edit_no(self):
        data = {"summary": "Old Sum", "lessons": ["L1"], "tags": ["T1"], "status": "success"}
        with patch('builtins.input', return_value='n'):
            res = session_summarizer.interactive_edit(data)
            assert res is None

    def test_interactive_edit_modify(self):
        data = {"summary": "Old Sum", "lessons": ["L1"], "tags": ["T1"], "status": "success"}
        # Sequence of inputs for 'e', then summary, then lessons, then tags
        inputs = iter(['e', 'New Sum', 'New L1, New L2', 'New T1'])
        with patch('builtins.input', lambda _: next(inputs)):
            res = session_summarizer.interactive_edit(data)
            assert res['summary'] == 'New Sum'
            assert len(res['lessons']) == 2
            assert 'New T1' in res['tags']
