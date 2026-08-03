import requests
import json
import time
from typing import List, Dict, Any
from config import config

class SheetManager:
    """Manages interactions with the Google Sheet Triage Gateway via Apps Script Web App."""

    API_VERSION = "1.0"

    def __init__(self):
        self.url = config.WEB_APP_URL
        self.secret = config.WEB_APP_SECRET

    def _handle_response(self, response):
        """Checks for errors and version mismatches in the response."""
        response.raise_for_status()
        text = response.text
        if "VERSION_MISMATCH" in text:
            raise RuntimeError(
                f"API Version Mismatch! This code expects v{self.API_VERSION}, "
                "but your Google Apps Script is outdated. Please update templates/Code.gs "
                "in your Google Sheet project."
            )
        if "Unauthorized:" in text:
            raise PermissionError(text)
        if text in ("Invalid Action", "Message-ID not found", "No data found"):
            raise ValueError(text)
        return response

    def _make_request(self, method: str, **kwargs):
        """Makes a request with retries, handling Google Apps Script redirects manually."""
        headers = kwargs.pop('headers', {})
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        kwargs['headers'] = headers

        for attempt in range(3):
            try:
                # First request to the Web App URL (do not follow redirects automatically)
                if method == 'GET':
                    response = requests.get(self.url, allow_redirects=False, **kwargs)
                elif method == 'POST':
                    response = requests.post(self.url, allow_redirects=False, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                # Google Apps Script Web Apps always redirect on success
                if response.status_code in (302, 303) and 'Location' in response.headers:
                    redirect_url = response.headers['Location']
                    # Second hop: GET request to the redirect URL with NO cookies and no payload
                    # Apps Script returns the actual result at this redirect URL via GET
                    response = requests.get(redirect_url, headers=headers)
                
                # Check if it's a 404 before passing to standard handler
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 404 and attempt < 2:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise

    def append_email(self, message_id: str, date: str, sender: str, subject: str):
        """Appends a new email entry to the sheet via the Web App."""
        payload = {
            "action": "append",
            "secret": self.secret,
            "version": self.API_VERSION,
            "Status": "APPROVED" if config.AUTO_APPROVE else "PENDING",
            "Subject": subject,
            "Sender": sender,
            "Date": date,
            "Message-ID": message_id
        }
        response = self._make_request('POST', json=payload)
        self._handle_response(response)

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Retrieves rows where Status is APPROVED or SKIP via the Web App."""
        params = {
            "action": "get_pending",
            "secret": self.secret,
            "version": self.API_VERSION
        }
        response = self._make_request('GET', params=params)
        self._handle_response(response)
        return response.json()

    def update_status(self, message_id: str, new_status: str):
        """Updates the status of a specific email by Message-ID via the Web App."""
        payload = {
            "action": "update_status",
            "secret": self.secret,
            "version": self.API_VERSION,
            "Message-ID": message_id,
            "Status": new_status
        }
        response = self._make_request('POST', json=payload)
        self._handle_response(response)
