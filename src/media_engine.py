import requests
from bs4 import BeautifulSoup
from readability import Document
from PIL import Image
from io import BytesIO
import qrcode
import hashlib
import os
import re
import copy
from typing import Dict, List, Tuple, Optional

class MediaEngine:
    """
    Handles HTML sanitization, image processing for e-ink, and 
    QR code generation for rich media embeds.
    """

    def __init__(self, output_dir: str = "temp_assets"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def process_content(self, raw_html: str) -> Tuple[str, Dict[str, bytes]]:
        """
        Main pipeline for cleaning HTML and processing assets.
        Returns (sanitized_html_string, assets_dict).
        """
        soup_orig = BeautifulSoup(raw_html, 'lxml')
        
        # 0. Pre-processing: Convert data-src to src and unwrap layout tables
        for img in soup_orig.find_all('img'):
            if not img.get('src') and img.get('data-src'):
                img['src'] = img.get('data-src')
        
        # Unwrap tables that are used for layout but contain images
        for table in soup_orig.find_all('table'):
            imgs = table.find_all('img')
            if len(imgs) == 1:
                # If table just wraps one image, pull it out
                table.replace_with(imgs[0])

        # 1. Targeted Extraction (Substack Specific)
        # Try multiple known Substack content containers
        main_content = None
        targets = [
            {'name': 'div', 'class': r'available-content|body.markup|post.typography|post-content|markup'}
        ]
        
        for target in targets:
            main_content = soup_orig.find(target['name'], class_=re.compile(target['class']))
            if main_content:
                print(f"DEBUG: Found targeted Substack content via: {target['class']}")
                break
                
        if main_content:
            # We found a specific content div, we use it directly
            soup = BeautifulSoup(str(main_content), 'lxml')
        else:
            # Final fallback: use the whole body if it exists, otherwise the whole doc
            main_content = soup_orig.find('body') or soup_orig
            print(f"DEBUG: Targeted content not found, using { 'body' if soup_orig.find('body') else 'full document'} as source.")
            
            # Protect images from readability by replacing them with tokens
            image_tokens = {}
            temp_soup = copy.copy(main_content)
            for i, img in enumerate(temp_soup.find_all('img')):
                src = img.get('src') or img.get('data-src')
                if src:
                    token = f"[[OASIS_IMG_{i}]]"
                    image_tokens[token] = src
                    img.replace_with(token)
            
            doc = Document(str(temp_soup))
            clean_html = doc.summary()
            
            # Restore tokens
            for token, src in image_tokens.items():
                clean_html = clean_html.replace(token, f'<img src="{src}" />')
            soup = BeautifulSoup(clean_html, 'lxml')

        # 2. Clean noise (scripts, styles, layout tables)
        for junk in soup.find_all(['script', 'style', 'hr', 'button', 'form', 'input']):
            junk.decompose()
            
        # Clean Substack-specific noise
        for noise in soup.find_all(class_=re.compile(r'subscribe-widget|share-button|footer')):
            noise.decompose()

        # 4. Deep Recovery (If content is too short)
        if len(soup.get_text()) < 200:
            print("DEBUG: Sources section missing in current soup, performing deep recovery...")
            sources_section = soup.new_tag("div", **{"class": "sources-recovered"})
            for p in soup_orig.find_all(['p', 'h1', 'h2']):
                if "Sources" in p.get_text():
                    header = soup.new_tag("h2")
                    header.string = "Sources & References"
                    sources_section.append(header)
                    
                    # Grab siblings
                    curr = p.next_sibling
                    limit = 0
                    while curr and limit < 30:
                        if hasattr(curr, 'name') and curr.name in ['h1', 'h2']: break
                        if curr != '\n':
                            sources_section.append(copy.copy(curr))
                        curr = curr.next_sibling
                        limit += 1
                    break
            if sources_section:
                soup.append(sources_section)

        assets = {}
        # Pre-scan image count for debugging
        all_imgs = soup.find_all('img')
        print(f"DEBUG: Total images identified for processing: {len(all_imgs)}")
        
        img_count = 0
        # 3. Process Images
        # Find all images (some might be hidden in data-attrs)
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('original-src')
            
            # Handle Substack data-attrs JSON
            data_attrs = img.get('data-attrs')
            if data_attrs:
                try:
                    import json
                    attrs = json.loads(data_attrs)
                    if attrs.get('src'): src = attrs['src']
                except: pass

            if not src: continue
            
            try:
                img_data, filename = self._process_image(src, img_count)
                if img_data:
                    assets[filename] = img_data
                    img['src'] = filename
                    img_count += 1
                    print(f"DEBUG: Successfully processed image {img_count}: {src[:50]}...")
            except Exception as e:
                print(f"Warning: Failed to process image {src}: {e}")
                img.decompose()

        # 5. Convert Embeds (YouTube/etc) to QR
        for iframe in soup.find_all(['iframe', 'audio']):
            src = iframe.get('src') or iframe.get('data-src')
            if not src: continue
            qr_img_data, filename = self._generate_qr_code(src)
            assets[filename] = qr_img_data
            
            # Replace iframe with QR code and link
            container = soup.new_tag("div", style="text-align: center; margin: 20px 0;")
            qr_img = soup.new_tag("img", src=filename, style="width: 150px;")
            caption = soup.new_tag("p")
            caption.string = "Scan to view rich media"
            
            container.append(qr_img)
            container.append(caption)
            iframe.replace_with(container)

        return str(soup), assets

    def _process_image(self, url: str, index: int) -> Tuple[Optional[bytes], str]:
        """Downloads, resizes, and converts image to grayscale PNG."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            
            # Convert to RGB (removes alpha channel) then to grayscale
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img = img.convert("L")
            
            # Kindle optimization: resize if too large
            max_size = (1200, 1600)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            out_io = BytesIO()
            img.save(out_io, format='PNG', optimize=True)
            
            filename = f"img_{index}_{hashlib.md5(url.encode()).hexdigest()[:8]}.png"
            return out_io.getvalue(), filename
        except Exception as e:
            print(f"Error processing image {url}: {e}")
            return None, ""

    def _generate_qr_code(self, url: str) -> Tuple[bytes, str]:
        """Generates a grayscale QR code for a given URL."""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        out_io = BytesIO()
        img.save(out_io, format='PNG')
        filename = f"qr_{hashlib.md5(url.encode()).hexdigest()}.png"
        return out_io.getvalue(), filename
