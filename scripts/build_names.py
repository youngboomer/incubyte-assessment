"""Dump the names the seed uses from the global name dataset into backend/app/names.json.

Usage: python scripts/build_names.py real-names-folder/global_name_dataset.csv [--force]

Run it once. names.json is then the file to edit by hand: delete or add names to
make the people look right. The script refuses to overwrite it without --force.
The app and the repository never contain the 113 MB CSV, only this small file.
"""

from __future__ import annotations

import csv
import json
import sys
import unicodedata
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "backend" / "app" / "names.json"

# Seed country -> dataset countries whose names its people can plausibly carry.
SOURCES = {
    "US": ("US",),
    "CA": ("CA", "US", "GB"),
    "GB": ("GB", "IE"),
    "AU": ("AU", "GB", "US", "IE"),
    "DE": ("DE",),
    "IN": ("IN",),
    "SG": ("SG", "CN", "HK", "MY", "IN"),
    "JP": ("JP",),
}

# The dataset holds ten Japanese names, so this list is written by hand.
JAPAN_GIVEN = (
    "Haruto Yuto Sota Riku Hinata Minato Ren Kaito Takumi Daiki Kenji Hiroshi Takashi Yusuke "
    "Akira Satoshi Kazuki Ryota Shota Naoki Masato Tomoya Koji Daisuke Shun Taro Jiro Kenta "
    "Yuki Haruka Yui Hina Sakura Aoi Mio Rin Akari Nanami Yuka Misaki Ayaka Emi Kaori Noriko "
    "Naoko Keiko Mayumi Rika Saki Tomomi Asuka Chihiro Eri Mai Natsuki Reina Shiori"
).split()
JAPAN_SURNAME = (
    "Sato Suzuki Takahashi Tanaka Watanabe Ito Yamamoto Nakamura Kobayashi Kato Yoshida Yamada "
    "Sasaki Yamaguchi Matsumoto Inoue Kimura Hayashi Shimizu Yamazaki Mori Abe Ikeda Hashimoto "
    "Yamashita Ishikawa Nakajima Maeda Fujita Ogawa Goto Okada Hasegawa Murakami Kondo Ishii "
    "Saito Sakamoto Endo Aoki Fujii Nishimura Fukuda Ota Miura Fujiwara Okamoto Matsuda "
    "Nakagawa Nakano Harada Ono Tamura Takeuchi Kaneko Wada Nakayama Ishida Ueda Morita Hara "
    "Shibata Sakai Kudo Yokoyama Miyazaki Miyamoto Uchida Takagi Ando Taniguchi Maruyama Imai "
    "Takada Fujimoto Takeda Murata Ueno Sugiyama Masuda Sugawara Hirano Kojima Otsuka Chiba "
    "Kubo Matsui Iwasaki Sano Noguchi Kikuchi Matsuo"
).split()

NOT_NAMES = {"Singapore", "Unknown", "Name"}


def is_usable(name: str) -> bool:
    if not 3 <= len(name) <= 15 or name in NOT_NAMES:
        return False
    if not name[0].isupper() or name.isupper():
        return False
    for char in name:
        if char in "-'":
            continue
        if not unicodedata.name(char, "").startswith("LATIN"):
            return False
    return True


def load(path: Path) -> dict[str, dict[str, set[str]]]:
    csv.field_size_limit(10**9)
    by_country: dict[str, dict[str, set[str]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            kind = row["name_type"]
            name = unicodedata.normalize("NFC", row["name"].strip())
            if kind not in ("given", "surname") or not is_usable(name):
                continue
            by_country.setdefault(row["country_code"], {"given": set(), "surname": set()})[
                kind
            ].add(name)
    return by_country


def pool(by_country: dict[str, dict[str, set[str]]], codes: tuple[str, ...], kind: str) -> list[str]:
    merged: set[str] = set()
    for code in codes:
        merged |= by_country.get(code, {}).get(kind, set())
    return sorted(merged, key=str.casefold)


def main() -> None:
    if OUTPUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUTPUT} exists and may hold hand edits. Pass --force to overwrite it.")
    by_country = load(Path(sys.argv[1]))
    pools: dict[str, dict[str, list[str]]] = {}
    for country, codes in SOURCES.items():
        given = pool(by_country, codes, "given")
        surname = pool(by_country, codes, "surname")
        if country == "JP":
            given = sorted(set(given) | set(JAPAN_GIVEN), key=str.casefold)
            surname = sorted(set(surname) | set(JAPAN_SURNAME), key=str.casefold)
        pools[country] = {"given": given, "surname": surname}
        print(f"{country}: {len(given)} given, {len(surname)} surnames")
    OUTPUT.write_text(
        json.dumps(pools, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
