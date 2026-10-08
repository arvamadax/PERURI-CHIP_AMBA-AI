import pytest

from ascon_sp232 import aead_decrypt, aead_encrypt, hash256
from kat import aead_kats, hash_kats

AEAD = list(aead_kats())
HASH = list(hash_kats())


def test_kat_counts():
    assert len(AEAD) == 1089 and len(HASH) == 1025


@pytest.mark.parametrize("v", AEAD, ids=lambda v: f"aead{v[0]}")
def test_aead_kat(v):
    _, key, nonce, pt, ad, ct, tag = v
    assert aead_encrypt(key, nonce, ad, pt) == (ct, tag)
    assert aead_decrypt(key, nonce, ad, ct, tag) == pt


@pytest.mark.parametrize("v", HASH, ids=lambda v: f"hash{v[0]}")
def test_hash_kat(v):
    assert hash256(v[1]) == v[2]


def test_tampered_tag_rejected():
    for _, key, nonce, pt, ad, ct, tag in AEAD[::37]:
        bad = bytes([tag[0] ^ 1]) + tag[1:]
        assert aead_decrypt(key, nonce, ad, ct, bad) is None


def test_modified_vector_fails():
    """Satu byte vektor diubah -> perbandingan KAT harus gagal."""
    _, key, nonce, pt, ad, ct, tag = AEAD[500]
    assert aead_encrypt(key, nonce, ad, pt) != (bytes([ct[0] ^ 1]) + ct[1:], tag)
    assert aead_encrypt(key, nonce, ad, pt) != (ct, tag[:-1] + bytes([tag[-1] ^ 1]))
    assert hash256(HASH[10][1]) != bytes([HASH[10][2][0] ^ 1]) + HASH[10][2][1:]
    assert hash256(HASH[10][1][:-1] + bytes([HASH[10][1][-1] ^ 1])) != HASH[10][2]
