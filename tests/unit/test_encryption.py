"""Unit tests for Fernet PAT encryption helpers."""
import pytest
from app.security.encryption import encrypt_secret, decrypt_secret


class TestEncryption:

    def test_encrypt_returns_string(self):
        result = encrypt_secret("my-pat-token")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_decrypt_round_trip(self):
        original = "my-pat-token"
        assert decrypt_secret(encrypt_secret(original)) == original

    def test_different_values_produce_different_ciphertext(self):
        a = encrypt_secret("token-a")
        b = encrypt_secret("token-b")
        assert a != b

    def test_same_value_produces_different_ciphertext_each_time(self):
        # Fernet uses a random IV so two encryptions of the same value differ
        a = encrypt_secret("token")
        b = encrypt_secret("token")
        assert a != b

    def test_encrypt_empty_string(self):
        result = decrypt_secret(encrypt_secret(""))
        assert result == ""

    def test_ciphertext_not_plaintext(self):
        pat = "super-secret-pat"
        ciphertext = encrypt_secret(pat)
        assert pat not in ciphertext
