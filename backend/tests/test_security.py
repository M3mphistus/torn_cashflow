import time

from app import security


def test_session_token_round_trip():
    token = security.create_session_token(123456)
    payload = security.decode_session_token(token)
    assert payload["playerId"] == 123456
    assert abs(payload["issuedAt"] - int(time.time())) < 5


def test_decode_session_token_rejects_garbage():
    assert security.decode_session_token("not-a-real-token") is None


def test_api_key_encryption_round_trip():
    encrypted = security.encrypt_api_key("abc123XYZ")
    assert encrypted != "abc123XYZ"
    assert security.decrypt_api_key(encrypted) == "abc123XYZ"


def test_mask_key():
    assert security.mask_key("abcd1234") == "****1234"
    assert security.mask_key("abcd") == "****"
    assert security.mask_key("ab") == "**"
    assert security.mask_key("") == ""
