from ebooklib import epub
import uuid
import re
from typing import Dict, Optional
from datetime import datetime
from security import obfuscate

class EpubBuilder:
    """
    Compiles sanitized HTML and media assets into an EPUB 3 file.
    """

    def __init__(self, title: str, author: str):
        self.book = epub.EpubBook()
        
        # Set metadata
        self.book.set_identifier(str(uuid.uuid4()))
        self.book.set_title(title)
        self.book.set_language('en')
        self.book.add_author(author)
        
        # Add Dublin Core metadata for better Kindle parsing
        self.book.add_metadata('DC', 'publisher', 'Oasis Refresher')
        self.book.add_metadata('DC', 'description', f'Newsletter curated for Kindle Oasis')
        self.book.add_metadata('DC', 'date', datetime.now().isoformat())
        
        # Internal tracking
        self.chapters = []

    def add_chapter(self, title: str, content: str, assets: Dict[str, bytes], subtitle: Optional[str] = None):
        """
        Adds a chapter to the EPUB and embeds its associated assets.
        """
        # 1. Create the chapter object
        # Filename should be unique within the EPUB
        file_name = f"chapter_{len(self.chapters) + 1}.xhtml"
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang='en')
        
        # Add basic CSS for e-ink readability
        style = """
            @page { margin: 5pt; }
            body { font-family: serif; text-align: justify; line-height: 1.4; }
            img { max-width: 100%; height: auto; display: block; margin: 10px auto; }
            figure { margin: 20px 0; text-align: center; }
            figcaption { font-size: 0.8em; color: #333; margin-top: 5px; }
            h1 { text-align: center; margin-bottom: 0.2em; }
            .subtitle { text-align: center; font-style: italic; color: #555; margin-bottom: 2em; border-bottom: 1px solid #ccc; padding-bottom: 1em; }
        """
        subtitle_html = f'<div class="subtitle">{subtitle}</div>' if subtitle else ''
        chapter.content = f'<html><head><style>{style}</style></head><body><h1>{title}</h1>{subtitle_html}{content}</body></html>'
        
        # 2. Add assets (images/QR codes) to the book
        for filename, data in assets.items():
            # Check if asset already exists in the book to avoid duplicates
            if not any(item.file_name == filename for item in self.book.items):
                # Determine media type
                media_type = 'image/jpeg' if filename.endswith('.jpg') else 'image/png'
                item = epub.EpubItem(
                    uid=filename.split('.')[0],
                    file_name=filename,
                    media_type=media_type,
                    content=data
                )
                self.book.add_item(item)

        # 3. Register chapter
        self.book.add_item(chapter)
        self.chapters.append(chapter)

    def compile(self, output_path: str):
        """
        Finalizes the EPUB structure and writes it to disk.
        """
        # Define Table of Contents and spine
        self.book.toc = (self.chapters)
        
        # Add default NCX and Nav pages (required for EPUB 3)
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        
        # Define the reading order
        # Put 'nav' at the end so it starts on the first chapter
        self.book.spine = self.chapters + ['nav']
        
        # Write the file
        epub.write_epub(output_path, self.book, {})
        print(f"Successfully compiled EPUB to: {obfuscate(output_path)}")

    @staticmethod
    def generate_filename(title: str, author: str) -> str:
        """Generates a safe but readable filename for the EPUB. Preserves spaces for Kindle UX."""
        # 1. Clean the title: remove (Date), noisy symbols, preserve spaces
        clean_title = re.sub(r'\s*\([^)]+\)$', '', title) # Remove date in brackets
        clean_title = "".join([c if (c.isalnum() or c.isspace()) else " " for c in clean_title])
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        # 2. Clean the author
        clean_author = "".join([c if (c.isalnum() or c.isspace()) else "" for c in author])
        clean_author = re.sub(r'\s+', ' ', clean_author).strip()
        
        # 3. Combine: "Title - Author.epub"
        return f"{clean_title} - {clean_author}.epub"
