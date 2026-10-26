"""Encryption for connector credentials (API keys, mailbox passwords) kept in the database."""

import json

from cryptography.fernet import Fernet

from app.config import get_settings


def _fernet() -> Fernet:
    return Fernet(get_settings().secret_key.encode())


def encrypt(secret: dict) -> bytes:
    return _fernet().encrypt(json.dumps(secret).encode())


def decrypt(token: bytes) -> dict:
    return json.loads(_fernet().decrypt(token))
