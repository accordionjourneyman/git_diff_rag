import pytest
import os
import glob
from scripts.render_prompt import render_template

PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../prompts"))

def get_prompt_files():
    # Recursively find all .md files in prompts/
    files = []
    for root, _, filenames in os.walk(PROMPTS_DIR):
        for filename in filenames:
            if filename.endswith(".md"):
                files.append(os.path.join(root, filename))
    return files

class TestPrompts:
    @pytest.mark.parametrize("prompt_file", get_prompt_files())
    def test_prompt_render(self, prompt_file):
        # Dummy context that should satisfy most prompts
        diff_content = """
diff --git a/main.py b/main.py
index 83db48f..f735c5d 100644
--- a/main.py
+++ b/main.py
@@ -1,4 +1,5 @@
 def hello():
-    print("Hello")
+    print("Hello World")
+    return True
"""
        
        # Some prompts might require specific variables, but our render_prompt
        # provides a standard set. If a prompt requires more, it might fail,
        # which is good to know.
        
        # We use a try-except block to catch rendering errors and report them nicely
        try:
            rendered = render_template(prompt_file, diff_content, repo_name="test_repo")
            assert rendered is not None
            assert len(rendered) > 0
        except ValueError as e:
            # If it's missing vars, fail the test
            pytest.fail(f"Prompt {os.path.basename(prompt_file)} failed validation: {e}")
        except Exception as e:
            pytest.fail(f"Prompt {os.path.basename(prompt_file)} failed to render: {e}")
