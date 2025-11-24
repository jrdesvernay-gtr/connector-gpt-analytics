#!/usr/bin/env python3
"""
Generate secure keys for production deployment.
Run this script to generate SECRET_KEY and ENCRYPTION_KEY.
"""

import secrets
from cryptography.fernet import Fernet

print("=" * 80)
print("Production Key Generator")
print("=" * 80)
print()

# Generate SECRET_KEY
secret_key = secrets.token_urlsafe(32)
print("SECRET_KEY:")
print(secret_key)
print()

# Generate ENCRYPTION_KEY
encryption_key = Fernet.generate_key().decode()
print("ENCRYPTION_KEY:")
print(encryption_key)
print()

print("=" * 80)
print("Copy these values to your production environment variables:")
print("=" * 80)
print()
print("⚠️  IMPORTANT:")
print("- Never commit these keys to version control")
print("- Use different keys for each environment (dev, staging, prod)")
print("- Store these securely (password manager, secrets manager)")
print()

