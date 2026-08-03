import pytest
from unittest.mock import patch, MagicMock
from src.sheet_manager import SheetManager
import requests

@patch('src.sheet_manager.requests.get')
def test_make_request_get_redirect_success(mock_get):
    """Test that a GET request correctly handles a 302 redirect."""
    # Simulate first hop returning 302 with Location header
    mock_resp1 = MagicMock()
    mock_resp1.status_code = 302
    mock_resp1.headers = {'Location': 'https://script.googleusercontent.com/redirect'}
    
    # Simulate second hop returning 200 OK
    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.text = "Success"
    
    mock_get.side_effect = [mock_resp1, mock_resp2]
    
    manager = SheetManager()
    response = manager._make_request('GET', params={"action": "test"})
    
    assert response.status_code == 200
    assert response.text == "Success"
    
    # Check that requests.get was called exactly twice
    assert mock_get.call_count == 2
    
    # First call checks
    first_call_args, first_call_kwargs = mock_get.call_args_list[0]
    assert first_call_kwargs.get('allow_redirects') is False
    assert first_call_kwargs.get('params') == {"action": "test"}
    
    # Second call checks (to the redirect URL)
    second_call_args, second_call_kwargs = mock_get.call_args_list[1]
    assert second_call_args[0] == 'https://script.googleusercontent.com/redirect'

@patch('src.sheet_manager.requests.get')
@patch('src.sheet_manager.requests.post')
def test_make_request_post_redirect_success(mock_post, mock_get):
    """Test that a POST request correctly handles a 302 redirect by making a GET request."""
    # Simulate first hop returning 302 with Location header
    mock_resp1 = MagicMock()
    mock_resp1.status_code = 302
    mock_resp1.headers = {'Location': 'https://script.googleusercontent.com/redirect'}
    mock_post.return_value = mock_resp1
    
    # Simulate second hop returning 200 OK
    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.text = "Success"
    mock_get.return_value = mock_resp2
    
    manager = SheetManager()
    response = manager._make_request('POST', json={"data": "test"})
    
    assert response.status_code == 200
    assert response.text == "Success"
    
    # First call is a POST
    mock_post.assert_called_once()
    first_call_kwargs = mock_post.call_args[1]
    assert first_call_kwargs.get('allow_redirects') is False
    assert first_call_kwargs.get('json') == {"data": "test"}
    
    # Second call is a GET
    mock_get.assert_called_once()
    second_call_args = mock_get.call_args[0]
    assert second_call_args[0] == 'https://script.googleusercontent.com/redirect'

@patch('src.sheet_manager.requests.get')
@patch('src.sheet_manager.time.sleep')
def test_make_request_404_retries(mock_sleep, mock_get):
    """Test that transient 404s are retried with exponential backoff."""
    # Simulate 404, 404, then 200 OK
    mock_404 = MagicMock()
    mock_404.status_code = 404
    
    # We must raise an HTTPError for 404 in requests normally when raise_for_status() is called,
    # but the retry logic catches it.
    mock_404.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Error", response=mock_404)
    
    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.text = "Success"
    
    mock_get.side_effect = [mock_404, mock_404, mock_200]
    
    manager = SheetManager()
    response = manager._make_request('GET')
    
    assert response.status_code == 200
    assert mock_get.call_count == 3
    
    # Should have slept twice (2^0 = 1, 2^1 = 2)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)

@patch('src.sheet_manager.requests.get')
def test_handle_response_version_mismatch(mock_get):
    manager = SheetManager()
    
    mock_resp = MagicMock()
    mock_resp.text = "VERSION_MISMATCH"
    
    with pytest.raises(RuntimeError, match="API Version Mismatch"):
        manager._handle_response(mock_resp)
