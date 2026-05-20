"""Fernet symmetric encryption for PAT storage per Section 27."""
import os

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.rulegraph_encryption_key.encode()
                  if isinstance(settings.rulegraph_encryption_key, str)
                  else settings.rulegraph_encryption_key)


def encrypt_secret(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
