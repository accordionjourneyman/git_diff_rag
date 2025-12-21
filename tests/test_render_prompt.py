import pytest
import sys
import os
from scripts.render_prompt import render_template, detect_languages

class TestRenderPrompt:
    def test_detect_languages(self):
        diff_text = "diff --git a/script.py b/script.py\n+ print('hello')"
        assert detect_languages(diff_text) == ['python']
        
        diff_text_multi = "diff --git a/script.py b/script.py\n...\ndiff --git a/style.css b/style.css\n..."
        assert sorted(detect_languages(diff_text_multi)) == ['css', 'python']
        
        diff_text_unknown = "diff --git a/file.xyz b/file.xyz\n..."
        assert detect_languages(diff_text_unknown) == ['unknown']

    def test_render_template_python(self, tmp_path):
        # Create dummy diff
        diff_content = "diff --git a/script.py b/script.py\n+ print('hello')"
        
        # Create dummy template
        template_file = tmp_path / "template.md"
        template_file.write_text("Langs: {{ CODE_LANGS | join(',') }}")
        
        result = render_template(str(template_file), diff_content)
        assert "Langs: python" in result

    def test_render_template_multi(self, tmp_path):
        # Create dummy diff
        diff_content = "diff --git a/script.py b/script.py\n...\ndiff --git a/style.css b/style.css\n..."
        
        # Create dummy template
        template_file = tmp_path / "template.md"
        template_file.write_text("Langs: {{ CODE_LANGS | sort | join(',') }}")
        
        result = render_template(str(template_file), diff_content)
        assert "Langs: css,python" in result

    def test_missing_variable_validation(self, tmp_path):
        # Create dummy diff
        diff_content = ""
        
        # Create template with missing var
        template_file = tmp_path / "template.md"
        template_file.write_text("{{ MISSING_VAR }}")
        
        with pytest.raises(ValueError, match="Template requires missing vars"):
            render_template(str(template_file), diff_content)

    def test_output_format_env(self, tmp_path):
        # Create dummy diff
        diff_content = ""
        
        # Create template
        template_file = tmp_path / "template.md"
        template_file.write_text("Format: {{ OUTPUT_FORMAT }}")
        
        env = {"OUTPUT_FORMAT": "json"}
        
        result = render_template(str(template_file), diff_content, env_vars=env)
        assert "Format: json" in result
