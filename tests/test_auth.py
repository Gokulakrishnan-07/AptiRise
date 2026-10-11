import pytest
from app.services.auth import hash_password, verify_password, create_access_token, decode_token
from app.models.user import User


def test_password_hashing():
    pw = "SuperSecurePass123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPass", hashed) is False


def test_jwt_token_creation_and_decoding():
    data = {"sub": "42", "role": "admin"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "42"
    assert decoded.get("role") == "admin"


def test_invalid_token():
    assert decode_token("invalid.token.signature") is None
