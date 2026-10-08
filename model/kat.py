"""Parser file KAT format NIST LWC."""
from pathlib import Path

KAT_DIR = Path(__file__).parent / "kat"


def _records(name):
    for blk in (KAT_DIR / name).read_text().strip().split("\n\n"):
        yield {k.strip(): bytes.fromhex(v.strip()) if k.strip() != "Count" else int(v)
               for k, v in (ln.split("=", 1) for ln in blk.splitlines())}


def aead_kats():
    """Yield (count, key, nonce, pt, ad, ct, tag)."""
    for r in _records("LWC_AEAD_KAT_128_128.txt"):
        yield r["Count"], r["Key"], r["Nonce"], r["PT"], r["AD"], r["CT"][:-16], r["CT"][-16:]


def hash_kats():
    """Yield (count, msg, digest)."""
    for r in _records("LWC_HASH_KAT_128_256.txt"):
        yield r["Count"], r["Msg"], r["MD"]
