"""The VAPID key pair: one EC P-256 key in the data dir, written once."""

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def _public(key: ec.EllipticCurvePrivateKey) -> str:
    raw = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def load(path: Path) -> tuple[str, str]:
    """Return (pem path, public key as base64url); create the key once."""
    if not path.exists():
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(pem)
        os.chmod(path, 0o600)
        return str(path), _public(key)
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError(f"{path} does not hold an EC private key")
    return str(path), _public(key)
