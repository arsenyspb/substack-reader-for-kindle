import smtplib
from email.message import EmailMessage
from imap_tools import MailBox, AND
from bs4 import BeautifulSoup
from typing import List, Optional
from config import config
from security import obfuscate
import os
import re
from datetime import datetime, date, timedelta

class MailClient:
    """
    Handles IMAP state management and SMTP delivery.
    
    ARCHITECTURAL NOTE: This system uses Gmail Labels as a stateful database.
    - IMAP_FOLDER (Substack-Kindle): The "Ingestion Queue" for new mail.
    - IMAP_PROCESSING_FOLDER (Substack-Kindle-Processed): The "Archive" for synced mail.
    """

    def __init__(self):
        self.gmail_user = config.GMAIL_USER
        self.gmail_pass = config.GMAIL_APP_PASSWORD
        self.imap_host = config.IMAP_HOST
        
        self.smtp_host = config.SMTP_HOST
        self.smtp_port = config.SMTP_PORT

    def _clean_subject(self, subject: str) -> str:
        """Removes Fwd:, Re:, etc. from the subject."""
        return re.sub(r'^(Fwd|Re|FW|RE):\s*', '', subject, flags=re.IGNORECASE).strip()

    def _extract_substack_author(self, msg) -> str:
        """
        Attempts to extract a clean Substack author name from headers or body.
        Heuristics are prioritized from most specific to least specific.
        """
        import html
        
        html_body = msg.html
        if not html_body:
            return "Substack"
            
        soup = BeautifulSoup(html_body, 'lxml')
        
        # --- PHASE 1: Native Substack CSS ---
        # Look for the official author div class used in direct emails.
        author_div = soup.find(class_=re.compile(r'custom-css-email-post-author'))
        if author_div:
            author_text = author_div.get_text(separator=' ', strip=True)
            if author_text and len(author_text) > 2:
                author_text = html.unescape(author_text)
                author_text = re.sub(r'\s+', ' ', author_text).strip()
                author_text = re.split(r'[·|•-]', author_text)[0].strip()
                return f"{author_text} (Substack)"

        # --- PHASE 2: Substack Profile Links ---
        # If the email is forwarded or modified, the specific CSS classes might be lost.
        # Profile links (@username) are the most stable way to get the human name.
        profile_links = soup.find_all('a', href=re.compile(r'substack\.com/@'))
        for link in profile_links:
            name = link.get_text(strip=True)
            if name and len(name) > 2 and "profile" not in name.lower() and "substack" not in name.lower():
                return f"{name} (Substack)"

        # --- PHASE 3: Gmail Forwarding Logic ---
        # When Gmail forwards an email, it wraps original metadata in specific tags.
        sender_name_tag = soup.find(class_="gmail_sendername")
        if sender_name_tag:
            name = sender_name_tag.get_text(strip=True)
            if name and len(name) > 2 and "substack.com" not in name.lower():
                return f"{name} (Substack)"

        # Regex fallback for other forwarding clients (looks for "From: <name>")
        fwd_patterns = [
            r'From:\s*<(?:b|strong)[^>]*>([^<]+)</(?:b|strong)>',
            r'From:\s*([^<]+)<', # Plain text fallback in forwards
            r'by\s+<a[^>]*>([^<]+)</a>'
        ]
        for pattern in fwd_patterns:
            match = re.search(pattern, html_body, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                author = html.unescape(author)
                author = re.split(r'[·|•-]', author)[0].strip()
                # Ensure we don't accidentally attribute the newsletter to the forwarder
                if len(author) > 2 and "substack.com" not in author.lower() and "arseny" not in author.lower():
                    return f"{author} (Substack)"

        # --- PHASE 4: Header Fallbacks ---
        # Final attempt: parse the raw email headers if HTML extraction failed.
        from_header = msg.from_
        name_match = re.match(r'^"?([^"<]+)"?', from_header)
        if name_match:
            name = name_match.group(1).strip()
            name = html.unescape(name)
            name = re.split(r'[·|•-]', name)[0].strip()
            if "@" not in name and len(name) > 2 and "substack" not in name.lower() and "arseny" not in name.lower():
                return f"{name} (Substack)"

        return "Substack"

    def fetch_recent_emails(self, days: int = 14) -> List[dict]:
        """
        Searches for emails in the last N days in the specific label.
        
        GOTCHA: We don't use the 'UNREAD' flag because it's too easy for a user 
        to accidentally mark an email as read on their phone, which would 
        cause the script to skip it. Instead, we use a time window and rely 
        on the move-to-processed logic for deduplication.
        """
        emails = []
        allowlist = [s.strip().lower() for s in config.ALLOWLISTED_SENDERS.split(",") if s.strip()]
        
        since_date = date.today() - timedelta(days=days)
        print(f"Connecting to {self.imap_host} folder: {config.IMAP_FOLDER}...")
        print(f"Searching for emails since {since_date.strftime('%Y-%m-%d')}...")
        
        try:
            with MailBox(self.imap_host).login(self.gmail_user, self.gmail_pass, initial_folder=config.IMAP_FOLDER) as mailbox:
                # We fetch all emails in the folder within the date range.
                # Since processed emails are moved OUT of this folder, 
                # anything remaining is by definition new/unprocessed.
                for msg in mailbox.fetch(AND(date_gte=since_date)):
                    sender_email = msg.from_.lower()
                    
                    # Check if sender is in allowlist (if allowlist is not empty)
                    if allowlist and not any(allowed in sender_email for allowed in allowlist):
                        print(f"Skipping non-allowlisted email from: {obfuscate(msg.from_)}")
                        continue

                    # DISTINCTION:
                    # - Message-ID: Global persistent ID (used for sheet tracking)
                    # - UID: Session-specific IMAP ID (used for moving emails)
                    message_id = msg.headers.get('message-id', [None])[0]
                    if not message_id:
                        # Fallback to UID if header is somehow missing (rare)
                        message_id = msg.uid

                    clean_subject = self._clean_subject(msg.subject)
                    author = self._extract_substack_author(msg)
                    
                    # Format date: (June 3, 2026)
                    date_str = msg.date.strftime("%B %d, %Y")
                    display_title = f"{clean_subject} ({date_str})"

                    emails.append({
                        "message_id": message_id,
                        "uid": msg.uid,
                        "date": date_str,
                        "sender": author,
                        "subject": display_title,
                        "html": msg.html
                    })
        except Exception as e:
            if "NONEXISTENT" in str(e):
                print(f"Error: The label '{config.IMAP_FOLDER}' does not exist in your Gmail account.")
                print("Please create it and set up a filter as described in the README.")
            raise e
            
        return emails

    def move_to_processing(self, message_uid: str):
        """Moves a processed email from ingest label to the Processing label."""
        with MailBox(self.imap_host).login(self.gmail_user, self.gmail_pass, initial_folder=config.IMAP_FOLDER) as mailbox:
            # Ensure destination folder exists
            if not mailbox.folder.exists(config.IMAP_PROCESSING_FOLDER):
                print(f"Creating missing folder: {config.IMAP_PROCESSING_FOLDER}...")
                mailbox.folder.create(config.IMAP_PROCESSING_FOLDER)
            
            mailbox.move(message_uid, config.IMAP_PROCESSING_FOLDER)

    def fetch_by_msg_id(self, message_id: str) -> Optional[dict]:
        """Fetches a specific email's HTML body from the Processing label."""
        with MailBox(self.imap_host).login(self.gmail_user, self.gmail_pass, initial_folder=config.IMAP_PROCESSING_FOLDER) as mailbox:
            # Escape quotes in message_id for IMAP criteria
            safe_msg_id = message_id.replace('"', '\\"')
            criteria = f'HEADER Message-ID "{safe_msg_id}"'
            
            print(f"Searching for Message-ID in {config.IMAP_PROCESSING_FOLDER}...")
            for msg in mailbox.fetch(criteria):
                html_content = msg.html
                if not html_content:
                    print(f"Warning: Found email for {obfuscate(message_id)} but HTML body is EMPTY.")
                    continue

                clean_subject = self._clean_subject(msg.subject)
                author = self._extract_substack_author(msg)
                date_str = msg.date.strftime("%B %d, %Y")
                display_title = f"{clean_subject} ({date_str})"

                print(f"Successfully fetched email body ({len(html_content)} bytes) for: {obfuscate(clean_subject)}")
                return {
                    "subject": display_title,
                    "sender": author,
                    "html": html_content,
                    "date": date_str
                }
        
        print(f"Warning: No email found in {config.IMAP_PROCESSING_FOLDER} with Message-ID: {obfuscate(message_id)}")
        return None

    def delete_email(self, message_id: str):
        """Archives or deletes an email from the Processing label."""
        with MailBox(self.imap_host).login(self.gmail_user, self.gmail_pass, initial_folder=config.IMAP_PROCESSING_FOLDER) as mailbox:
            criteria = f'HEADER Message-ID "{message_id}"'
            uids = [msg.uid for msg in mailbox.fetch(criteria)]
            if uids:
                mailbox.delete(uids)
                print(f"Deleted email(s) with Message-ID {obfuscate(message_id)} from {config.IMAP_PROCESSING_FOLDER}")

    def send_to_kindle(self, epub_path: str):
        """Sends an EPUB file via SMTP to the Kindle email address."""
        filename = os.path.basename(epub_path)
        print(f"Initiating SMTP delivery for {obfuscate(filename)} to {obfuscate(config.KINDLE_EMAIL)}...")
        
        msg = EmailMessage()
        # Clean title for subject: just the filename without .epub
        subject = os.path.splitext(filename)[0]
        msg['Subject'] = subject
        msg['From'] = self.gmail_user
        msg['To'] = config.KINDLE_EMAIL
        msg.set_content("Automated newsletter delivery from Oasis Refresher.")

        with open(epub_path, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(
                file_data,
                maintype='application',
                subtype='epub+zip',
                filename=os.path.basename(epub_path)
            )

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.gmail_user, self.gmail_pass)
            server.send_message(msg)
        print(f"Dispatched {obfuscate(epub_path)} to {obfuscate(config.KINDLE_EMAIL)}")
