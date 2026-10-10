from app.passwords import hash_password, verify_password

MALFORMED = (
    "",
    "plain",
    "scrypt$1$2",
    "bcrypt$16384$8$1$aa$bb",
    "scrypt$x$8$1$aa$bb",
    "scrypt$16384$8$1$zz$bb",
)


def test_hash_round_trip() -> None:
    encoded = hash_password("s3cret")
    assert encoded.startswith("scrypt$")
    assert verify_password("s3cret", encoded)
    assert not verify_password("other", encoded)


def test_hash_is_salted() -> None:
    assert hash_password("s3cret") != hash_password("s3cret")


def test_malformed_hash_rejected() -> None:
    for bad in MALFORMED:
        assert not verify_password("s3cret", bad)
