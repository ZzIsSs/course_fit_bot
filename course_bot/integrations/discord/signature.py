"""Xác thực chữ ký Ed25519 của request Discord Interactions."""
import os

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

DISCORD_PUBLIC_KEY = os.environ.get('DISCORD_PUBLIC_KEY')


def verify_signature(signature, timestamp, body):
    if not DISCORD_PUBLIC_KEY:
        return False
    try:
        VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY)).verify(
            f'{timestamp}{body}'.encode(), bytes.fromhex(signature))
        return True
    except (BadSignatureError, Exception):
        return False
