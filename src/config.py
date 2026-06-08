import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    """Configuration for the Substack RFK pipeline."""
    
    # Gmail Configuration (Burner or Personal with Label)
    IMAP_HOST: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    GMAIL_USER: str = os.getenv("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    
    # Ingestion restricted to a specific label for safety/batching
    IMAP_FOLDER: str = os.getenv("IMAP_FOLDER", "Substack-Kindle")
    IMAP_PROCESSING_FOLDER: str = os.getenv("IMAP_PROCESSING_FOLDER", "Substack-Kindle-Processed")

    # SMTP Configuration (Kindle Delivery - uses same Gmail credentials)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    KINDLE_EMAIL: str = os.getenv("KINDLE_EMAIL", "")

    # Google Sheets Configuration (via Apps Script Web App)
    WEB_APP_URL: str = os.getenv("WEB_APP_URL", "")
    WEB_APP_SECRET: str = os.getenv("WEB_APP_SECRET", "")

    # Filtering Configuration
    ALLOWLISTED_SENDERS: str = os.getenv("ALLOWLISTED_SENDERS", "")

    def validate(self):
        """Validates that all required environment variables are set."""
        required = [
            "GMAIL_USER", "GMAIL_APP_PASSWORD", 
            "KINDLE_EMAIL", "WEB_APP_URL", "WEB_APP_SECRET"
        ]
        missing = [var for var in required if not getattr(self, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

config = Config()
