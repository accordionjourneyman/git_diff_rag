import pytest
from scripts.validate_output import validate_json_output, extract_json

class TestValidateOutput:
    def test_extract_json_plain(self):
        content = '{"key": "value"}'
        assert extract_json(content) == content

    def test_extract_json_markdown(self):
        content = '```json\n{"key": "value"}\n```'
        assert extract_json(content) == '{"key": "value"}'

    def test_extract_json_markdown_no_lang(self):
        content = '```\n{"key": "value"}\n```'
        assert extract_json(content) == '{"key": "value"}'

    def test_validate_json_output_valid(self, tmp_path):
        f = tmp_path / "valid.json"
        f.write_text('{"key": "value"}', encoding='utf-8')
        assert validate_json_output(str(f)) is True

    def test_validate_json_output_invalid_json(self, tmp_path):
        f = tmp_path / "invalid.json"
        f.write_text('{"key": "value"', encoding='utf-8')
        assert validate_json_output(str(f)) is False

    def test_validate_json_output_list_valid(self, tmp_path):
        f = tmp_path / "list.json"
        f.write_text('[{"key": "value"}]', encoding='utf-8')
        assert validate_json_output(str(f)) is True

    def test_validate_json_output_list_invalid_item(self, tmp_path):
        f = tmp_path / "list_invalid.json"
        f.write_text('[{"key": "value"}, "string"]', encoding='utf-8')
        assert validate_json_output(str(f)) is False

    def test_validate_json_output_file_not_found(self):
        assert validate_json_output("nonexistent.json") is False
