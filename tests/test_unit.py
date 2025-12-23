import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from jinja2 import UndefinedError, TemplateError

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))

import call_gemini

class TestGeminiAPI:
    @patch('scripts.call_gemini.genai.Client')
    def test_successful_call(self, mock_client_cls):
        # Setup
        os.environ['GEMINI_API_KEY'] = 'fake_key'
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value.text = "Review OK"
        
        # Test
        result = call_gemini.call_with_retry("test prompt")
        
        # Assert
        assert result == "Review OK"
        mock_client.models.generate_content.assert_called()

    def test_empty_prompt_exits(self):
        with pytest.raises(ValueError):
            call_gemini.call_with_retry("")

    @patch('time.sleep')
    @patch('scripts.call_gemini.genai.Client')
    def test_retry_logic(self, mock_client_cls, mock_sleep):
        from google.api_core import exceptions
        os.environ['GEMINI_API_KEY'] = 'fake_key'
        
        mock_client = mock_client_cls.return_value
        # Fail twice with ServiceUnavailable, then succeed
        mock_client.models.generate_content.side_effect = [
            exceptions.ServiceUnavailable("Busy"),
            exceptions.ServiceUnavailable("Busy"),
            MagicMock(text="Success")
        ]
        
        call_gemini.call_with_retry("test")
        assert mock_sleep.call_count == 2
        
    @patch('time.sleep')
    @patch('scripts.call_gemini.genai.Client')
    def test_retry_success(self, mock_client_cls, mock_sleep):
        from google.api_core import exceptions
        os.environ['GEMINI_API_KEY'] = 'fake_key'
        
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = [
            exceptions.ServiceUnavailable("Busy"),
            MagicMock(text="Success")
        ]
        
        result = call_gemini.call_with_retry("test")
        assert result == "Success"
        assert mock_sleep.call_count == 1

class TestPromptRendering:
    def test_introspection_script(self, tmp_path):
        import subprocess
        
        script = os.path.join(os.path.dirname(__file__), "../scripts/render_prompt.py")
        
        template = tmp_path / "t.md"
        template.write_text("Hello {{DIFF_CONTENT}} from {{REPO_NAME}}")
        
        diff = tmp_path / "diff.txt"
        diff.write_text("changes")
        
        # Success case
        cmd = [sys.executable, script, str(template), str(diff), "myrepo"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        assert "Hello changes from myrepo" in result.stdout
        
    def test_missing_var_error(self, tmp_path):
        import subprocess
        
        script = os.path.join(os.path.dirname(__file__), "../scripts/render_prompt.py")
        
        template = tmp_path / "t.md"
        template.write_text("Hello {{MISSING_VAR}}")
        
        diff = tmp_path / "diff.txt"
        diff.write_text("changes")
        
        # Error case
        cmd = [sys.executable, script, str(template), str(diff), "myrepo"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 1
        assert "Template requires missing vars" in result.stdout
