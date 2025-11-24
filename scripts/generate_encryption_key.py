#!/usr/bin/env python3
"""Generate a Fernet encryption key for use in ENCRYPTION_KEY environment variable."""

from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key()
    print(f"Generated Fernet encryption key:")
    print(key.decode())
    print("\nAdd this to your .env file as:")
    print(f"ENCRYPTION_KEY={key.decode()}")

