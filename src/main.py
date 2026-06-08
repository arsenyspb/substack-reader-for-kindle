import argparse
import sys
import os
from config import config
from sheet_manager import SheetManager
from mail_client import MailClient
from media_engine import MediaEngine
from epub_builder import EpubBuilder
from security import obfuscate

def sync_mode():
    """Ingests recent emails into the Google Sheet Triage Gateway."""
    print("Starting Phase 1: Sync (Ingestion)...")
    mail = MailClient()
    sheet = SheetManager()
    
    recent_emails = mail.fetch_recent_emails(days=14)
    if not recent_emails:
        print("No recent emails found in the last 14 days.")
        return

    for email in recent_emails:
        print(f"Syncing: {obfuscate(email['subject'])} from {obfuscate(email['sender'])}")
        sheet.append_email(
            message_id=email['message_id'],
            date=email['date'],
            sender=email['sender'],
            subject=email['subject']
        )
        mail.move_to_processing(email['uid']) # Use IMAP UID to move
    
    print(f"Successfully synced {len(recent_emails)} emails.")

def process_mode():
    """Fulfills approved entries from the Google Sheet."""
    print("Starting Phase 2: Process (Fulfillment)...")
    sheet = SheetManager()
    mail = MailClient()
    media = MediaEngine()
    
    pending_actions = sheet.get_pending_actions()
    if not pending_actions:
        print("No pending actions (APPROVED/SKIP) found in sheet.")
        return

    for action in pending_actions:
        msg_id = str(action['Message-ID'])
        status = action['Status']
        subject = action['Subject']

        if status == 'SKIP':
            print(f"Skipping: {obfuscate(subject)}")
            mail.delete_email(msg_id)
            sheet.update_status(msg_id, "PURGED")
            continue

        if status == 'APPROVED':
            print(f"--- Processing: {obfuscate(subject)} ---")
            email_data = mail.fetch_by_msg_id(msg_id)
            if not email_data or not email_data.get('html'):
                print(f"Error: Could not find email data or HTML content for Message-ID {msg_id}")
                # We update status to ERROR so it doesn't loop forever
                sheet.update_status(msg_id, "ERROR: No Content")
                continue

            # 1. Clean and process media
            print(f"Cleaning HTML and processing assets for {obfuscate(subject)}...")
            clean_html, assets = media.process_content(email_data['html'])
            print(f"Found {len(assets)} assets to embed.")
            
            # 2. Build EPUB
            builder = EpubBuilder(title=subject, author=email_data['sender'])
            # Add subtitle with date
            subtitle = f"Published on {email_data['date']}"
            builder.add_chapter(title=subject, content=clean_html, assets=assets, subtitle=subtitle)
            
            output_filename = builder.generate_filename(subject, email_data['sender'])
            output_path = os.path.join(media.output_dir, output_filename)
            builder.compile(output_path)
            
            # 3. Deliver
            try:
                mail.send_to_kindle(output_path)
                print(f"Successfully sent {obfuscate(subject)} to Kindle.")
                
                mail.delete_email(msg_id)
                sheet.update_status(msg_id, "DELIVERED")
                
                # Optional: Cleanup local asset
                if os.path.exists(output_path):
                    os.remove(output_path)
                    print(f"Cleaned up local file: {obfuscate(output_path)}")
            except Exception as e:
                print(f"Failed to deliver {obfuscate(subject)}: {e}")
                sheet.update_status(msg_id, "ERROR")

    print("Processing complete.")

def main():
    parser = argparse.ArgumentParser(description="Substack RFK: Substack-to-Kindle Pipeline")
    parser.add_argument("--sync", action="store_true", help="Ingest recent emails into triage sheet")
    parser.add_argument("--process", action="store_true", help="Fulfill approved entries from triage sheet")
    
    args = parser.parse_args()

    if not args.sync and not args.process:
        parser.print_help()
        sys.exit(1)

    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please check your .env file.")
        sys.exit(1)

    if args.sync:
        sync_mode()
    
    if args.process:
        process_mode()

if __name__ == "__main__":
    main()
