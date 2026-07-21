import requests
import json
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
        response = requests.post(self.url, json=payload)
        self._handle_response(response)

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Retrieves rows where Status is APPROVED or SKIP via the Web App."""
        params = {
            "action": "get_pending",
            "secret": self.secret,
            "version": self.API_VERSION
        }
        response = requests.get(self.url, params=params)
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
        response = requests.post(self.url, json=payload)
        self._handle_response(response)
