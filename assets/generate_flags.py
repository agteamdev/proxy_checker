"""
One-off script that downloads a full set of small flag icons from
flagcdn.com and saves them locally under assets/flags/, so the running app
never has to fetch them over the network - eliminating the flag-fetching
step entirely for any bundled country (previously this was parallelized,
but for 1000+ proxies spanning many countries, no network calls at all is
faster and more reliable than any number of concurrent HTTP requests).

Run this once, whenever you want to (re)generate the bundled set - it needs
internet access, but the app itself does not once this has been run:

    pip install requests
    python assets/generate_flags.py

Each icon is 16x12px and typically well under 1KB, so the full set of ~250
countries adds only a few hundred KB to the repository - flags were never
the "heavy" part; the earlier slowness was from fetching them one at a time
(or once per proxy instead of once per country) at runtime, not their size.
"""

import os

import requests

# ISO 3166-1 alpha-2 codes for every flag flagcdn.com serves.
COUNTRY_CODES = [
    "ad", "ae", "af", "ag", "ai", "al", "am", "ao", "aq", "ar", "as", "at", "au", "aw", "ax", "az",
    "ba", "bb", "bd", "be", "bf", "bg", "bh", "bi", "bj", "bl", "bm", "bn", "bo", "bq", "br", "bs",
    "bt", "bv", "bw", "by", "bz",
    "ca", "cc", "cd", "cf", "cg", "ch", "ci", "ck", "cl", "cm", "cn", "co", "cr", "cu", "cv", "cw",
    "cx", "cy", "cz",
    "de", "dj", "dk", "dm", "do", "dz",
    "ec", "ee", "eg", "eh", "er", "es", "et",
    "fi", "fj", "fk", "fm", "fo", "fr",
    "ga", "gb", "gd", "ge", "gf", "gg", "gh", "gi", "gl", "gm", "gn", "gp", "gq", "gr", "gs", "gt",
    "gu", "gw", "gy",
    "hk", "hm", "hn", "hr", "ht", "hu",
    "id", "ie", "il", "im", "in", "io", "iq", "ir", "is", "it",
    "je", "jm", "jo", "jp",
    "ke", "kg", "kh", "ki", "km", "kn", "kp", "kr", "kw", "ky", "kz",
    "la", "lb", "lc", "li", "lk", "lr", "ls", "lt", "lu", "lv", "ly",
    "ma", "mc", "md", "me", "mf", "mg", "mh", "mk", "ml", "mm", "mn", "mo", "mp", "mq", "mr", "ms",
    "mt", "mu", "mv", "mw", "mx", "my", "mz",
    "na", "nc", "ne", "nf", "ng", "ni", "nl", "no", "np", "nr", "nu", "nz",
    "om",
    "pa", "pe", "pf", "pg", "ph", "pk", "pl", "pm", "pn", "pr", "ps", "pt", "pw", "py",
    "qa",
    "re", "ro", "rs", "ru", "rw",
    "sa", "sb", "sc", "sd", "se", "sg", "sh", "si", "sj", "sk", "sl", "sm", "sn", "so", "sr", "ss",
    "st", "sv", "sx", "sy", "sz",
    "tc", "td", "tf", "tg", "th", "tj", "tk", "tl", "tm", "tn", "to", "tr", "tt", "tv", "tw", "tz",
    "ua", "ug", "um", "us", "uy", "uz",
    "va", "vc", "ve", "vg", "vi", "vn", "vu",
    "wf", "ws",
    "ye", "yt",
    "za", "zm", "zw",
]

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flags")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ok, skipped, failed = 0, 0, []

    for code in COUNTRY_CODES:
        out_path = os.path.join(OUT_DIR, f"{code}.png")
        if os.path.exists(out_path):
            skipped += 1
            continue
        url = f"https://flagcdn.com/16x12/{code}.png"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(response.content)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            failed.append((code, str(exc)))

    print(f"Downloaded {ok} new flags, {skipped} already present, {len(failed)} failed.")
    print(f"Saved into: {OUT_DIR}")
    if failed:
        print("Failed codes:", failed)


if __name__ == "__main__":
    main()
