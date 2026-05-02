"""Paper Section 6-D: Security — AES-256, bcrypt, input sanitization."""

import os, hashlib, base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


def _key():
    raw = os.getenv("AES_SECRET_KEY", "careerhub-aes-32chars-change!!")
    return hashlib.sha256(raw.encode()).digest()


def encrypt_data(text: str) -> str:
    key = _key(); iv = os.urandom(16)
    padder  = padding.PKCS7(128).padder()
    padded  = padder.update(text.encode()) + padder.finalize()
    cipher  = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc     = cipher.encryptor()
    ct      = enc.update(padded) + enc.finalize()
    return base64.b64encode(iv + ct).decode()


def decrypt_data(ciphertext_b64: str) -> str:
    key    = _key()
    raw    = base64.b64decode(ciphertext_b64)
    iv, ct = raw[:16], raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    dec    = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    unp    = padding.PKCS7(128).unpadder()
    return (unp.update(padded) + unp.finalize()).decode()


def sanitize(text, maxlen=500):
    if not text: return ""
    text = str(text).strip()
    for bad in ["<script", "javascript:", "onerror=", "onload=", "eval("]:
        text = text.replace(bad, "")
    return text[:maxlen]
