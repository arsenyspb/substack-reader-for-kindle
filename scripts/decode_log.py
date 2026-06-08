import sys
from security import deobfuscate

def main():
    if len(sys.argv) < 2:
        print("Usage: python decode_log.py <obfuscated_string>")
        print("Example: python decode_log.py Base64EncodedXORString==")
        sys.exit(1)

    obfuscated_string = sys.argv[1]
    plaintext = deobfuscate(obfuscated_string)
    print(f"Decoded: {plaintext}")

if __name__ == "__main__":
    main()
