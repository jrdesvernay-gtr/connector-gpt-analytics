"""Encryption utilities for GA refresh tokens using Fernet."""

from cryptography.fernet import Fernet
from typing import Optional
import base64

from app.config import get_settings

settings = get_settings()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption service with a Fernet key."""
        key = encryption_key or settings.ENCRYPTION_KEY.encode()
        # Ensure key is 32 bytes base64-encoded
        try:
            # If key is already base64-encoded, decode it
            if isinstance(key, str):
                key = key.encode()
            # Try to decode as base64 to check if it's already encoded
            base64.urlsafe_b64decode(key + b'====')  # Add padding if needed
            # If no error, it's base64, use as-is
            self.cipher = Fernet(key)
        except Exception:
            # If not valid base64, treat as raw bytes and encode
            if len(key) == 32:
                key = base64.urlsafe_b64encode(key)
            elif len(key) == 44:
                # Might be base64 without padding
                key = key + b'=' * (4 - len(key) % 4)
            else:
                raise ValueError("Encryption key must be 32 bytes or base64-encoded")
            self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        try:
            return self.cipher.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt token: {str(e)}")


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service

