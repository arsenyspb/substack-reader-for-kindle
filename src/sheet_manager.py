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
        """Makes a request with retries for transient 404 errors from Google's redirect."""
        for attempt in range(3):
            try:
                if method == 'GET':
                    response = requests.get(self.url, **kwargs)
                elif method == 'POST':
                    response = requests.post(self.url, allow_redirects=True, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # Check if it's a 404 before passing to standard handler
                response.raise_for_status()
                return response
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 404 and attempt < 2:
                    time.sleep(2)
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
