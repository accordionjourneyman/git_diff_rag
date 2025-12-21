import pytest
from unittest.mock import MagicMock, patch
from google.api_core import exceptions
from scripts.call_gemini import call_with_retry, count_tokens, get_client

class TestCallGemini:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.models.generate_content.return_value.text = "Generated Content"
        client.models.count_tokens.return_value.total_tokens = 100
        return client

    def test_get_client_no_key(self):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
                get_client()

    def test_get_client_with_key(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_key'}):
            with patch('google.genai.Client') as mock_client_cls:
                get_client()
                mock_client_cls.assert_called_with(api_key='fake_key')

    def test_count_tokens(self, mock_client):
        tokens = count_tokens("test prompt", client=mock_client)
        assert tokens == 100
        # Verify call arguments if needed, or just that it was called
        mock_client.models.count_tokens.assert_called()

    def test_call_with_retry_success(self, mock_client):
        result = call_with_retry("test prompt", client=mock_client)
        assert result == "Generated Content"
        mock_client.models.generate_content.assert_called()

    def test_call_with_retry_empty_prompt(self, mock_client):
        with pytest.raises(ValueError, match="Empty prompt"):
            call_with_retry("   ", client=mock_client)

    def test_call_with_retry_invalid_argument(self, mock_client):
        mock_client.models.generate_content.side_effect = exceptions.InvalidArgument("Invalid arg")
        with pytest.raises(ValueError, match="Invalid Argument"):
            call_with_retry("test", client=mock_client)

    def test_call_with_retry_unauthenticated(self, mock_client):
        mock_client.models.generate_content.side_effect = exceptions.Unauthenticated("Auth failed")
        with pytest.raises(PermissionError, match="API Key Invalid"):
            call_with_retry("test", client=mock_client)

    @patch('time.sleep')
    def test_call_with_retry_exhausted_then_success(self, mock_sleep, mock_client):
        # Fail twice, then succeed
        mock_client.models.generate_content.side_effect = [
            exceptions.ResourceExhausted("Quota exceeded"),
            exceptions.ServiceUnavailable("Service down"),
            MagicMock(text="Success after retry")
        ]
        
        result = call_with_retry("test", client=mock_client)
        assert result == "Success after retry"
        assert mock_client.models.generate_content.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('time.sleep')
    def test_call_with_retry_max_retries(self, mock_sleep, mock_client):
        mock_client.models.generate_content.side_effect = exceptions.ResourceExhausted("Quota exceeded")
        
        with pytest.raises(RuntimeError, match="Max retries"):
            call_with_retry("test", client=mock_client)
        
        assert mock_client.models.generate_content.call_count == 3 # MAX_RETRIES is 3
