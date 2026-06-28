from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import os

from .fingerprints import file_hash


@dataclass(frozen=True)
class EncryptionPayload:
    schema: str
    algorithm: str
    kdf: str
    ephemeral_public_key_b64: str
    salt_b64: str
    nonce_b64: str
    aad_sha256: str
    ciphertext_b64: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EncryptionKeyRecord:
    private_key_path: str
    public_key_path: str
    public_key_sha256: str
    algorithm: str = "X25519+HKDF-SHA256+ChaCha20Poly1305"


def generate_x25519_private_key() -> X25519PrivateKey:
    return X25519PrivateKey.generate()


def write_encryption_private_key(path: str | Path, private_key: X25519PrivateKey) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def write_encryption_public_key(path: str | Path, public_key: X25519PublicKey) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def load_encryption_private_key(path: str | Path) -> X25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, X25519PrivateKey):
        raise TypeError("Encryption private key must be an X25519 private key.")
    return key


def load_encryption_public_key(path: str | Path) -> X25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, X25519PublicKey):
        raise TypeError("Encryption public key must be an X25519 public key.")
    return key


def create_encryption_keypair(*, private_key_path: str | Path, public_key_path: str | Path) -> EncryptionKeyRecord:
    private_key = generate_x25519_private_key()
    write_encryption_private_key(private_key_path, private_key)
    write_encryption_public_key(public_key_path, private_key.public_key())
    return EncryptionKeyRecord(
        private_key_path=str(private_key_path),
        public_key_path=str(public_key_path),
        public_key_sha256=file_hash(public_key_path),
    )


def _derive_key(shared_secret: bytes, *, salt: bytes, aad_sha256: str) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=("rank3_enforced_transfer_v1:" + aad_sha256).encode("utf-8"),
    )
    return hkdf.derive(shared_secret)


def encrypt_bytes_for_recipient(
    plaintext: bytes,
    *,
    recipient_public_key_path: str | Path,
    aad_sha256: str,
) -> EncryptionPayload:
    recipient_public_key = load_encryption_public_key(recipient_public_key_path)
    ephemeral_private = X25519PrivateKey.generate()
    ephemeral_public = ephemeral_private.public_key()
    shared_secret = ephemeral_private.exchange(recipient_public_key)
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(shared_secret, salt=salt, aad_sha256=aad_sha256)
    aead = ChaCha20Poly1305(key)
    aad = aad_sha256.encode("ascii")
    ciphertext = aead.encrypt(nonce, plaintext, aad)
    ephemeral_raw = ephemeral_public.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return EncryptionPayload(
        schema="rank3_encrypted_payload_v1",
        algorithm="X25519+HKDF-SHA256+ChaCha20Poly1305",
        kdf="HKDF-SHA256(info=rank3_enforced_transfer_v1:<aad_sha256>)",
        ephemeral_public_key_b64=base64.b64encode(ephemeral_raw).decode("ascii"),
        salt_b64=base64.b64encode(salt).decode("ascii"),
        nonce_b64=base64.b64encode(nonce).decode("ascii"),
        aad_sha256=aad_sha256,
        ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
    )


def decrypt_payload(
    payload: EncryptionPayload | dict[str, Any],
    *,
    recipient_private_key_path: str | Path,
) -> bytes:
    if isinstance(payload, dict):
        payload = EncryptionPayload(**payload)
    if payload.schema != "rank3_encrypted_payload_v1":
        raise ValueError(f"Unsupported encrypted payload schema: {payload.schema}")
    private_key = load_encryption_private_key(recipient_private_key_path)
    ephemeral_raw = base64.b64decode(payload.ephemeral_public_key_b64)
    ephemeral_public = X25519PublicKey.from_public_bytes(ephemeral_raw)
    shared_secret = private_key.exchange(ephemeral_public)
    salt = base64.b64decode(payload.salt_b64)
    nonce = base64.b64decode(payload.nonce_b64)
    ciphertext = base64.b64decode(payload.ciphertext_b64)
    key = _derive_key(shared_secret, salt=salt, aad_sha256=payload.aad_sha256)
    aead = ChaCha20Poly1305(key)
    return aead.decrypt(nonce, ciphertext, payload.aad_sha256.encode("ascii"))


def write_encrypted_payload(path: str | Path, payload: EncryptionPayload) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_encrypted_payload(path: str | Path) -> EncryptionPayload:
    return EncryptionPayload(**json.loads(Path(path).read_text(encoding="utf-8")))
