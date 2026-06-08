import base64
from config import config

# --- LOG PRIVACY DESIGN RATIONALE ---
# In a public GitHub repository, Action logs are visible to everyone.
# To prevent leaking private newsletter subjects or sender names while 
# still allowing for remote troubleshooting, we "obfuscate" sensitive 
# strings before printing them to the console.
#
# We use a simple XOR cipher against the WEB_APP_SECRET. Since that 
# secret is stored as a masked GitHub Secret, only the repository owner 
# can decode these logs locally using their private key.
# ------------------------------------

def obfuscate(text: str) -> str:
    """
    Encrypts a string for public logs using XOR + Base64.
    Uses WEB_APP_SECRET as the pre-shared key.
    """
    if not text:
        return ""
    key = config.WEB_APP_SECRET
    if not key:
        return text  # Fallback to plaintext if key is not configured
    
    # FIX: We encode to UTF-8 bytes before XORing to handle non-ASCII characters 
    # (like emojis or special quotes) which would otherwise cause a 
    # "ValueError: bytes must be in range(0, 256)".
    text_bytes = text.encode('utf-8')
    key_bytes = key.encode('utf-8')
    
    xor_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(text_bytes)])
    
    # URL-safe Base64 makes it safe to print and copy-paste from logs
    return base64.urlsafe_b64encode(xor_bytes).decode('utf-8')

def deobfuscate(encoded_text: str) -> str:
    """
    Decodes a Base64 string and reverses the XOR encryption.
    Used by local scripts/decode_log.py for troubleshooting.
    """
    if not encoded_text:
        return ""
    key = config.WEB_APP_SECRET
    if not key:
        return encoded_text
    
    try:
        key_bytes = key.encode('utf-8')
        decoded_bytes = base64.urlsafe_b64decode(encoded_text)
        
        # Reverse the XOR operation on bytes
        decrypted_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(decoded_bytes)])
        
        # Decode UTF-8 bytes back into a readable string
        return decrypted_bytes.decode('utf-8')
    except Exception:
        return "[Decryption Failed - Check your WEB_APP_SECRET or encoding]"
