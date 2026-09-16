"""
Batch GeoIP lookups, plus flag icons.

Two representations of "flag" are provided:
  - `country_code_to_flag_emoji`: a Unicode flag emoji. Handy for plain-text
    exports (CSV/TXT), but many Linux desktops have no color-emoji font
    installed, so Tkinter renders it as two separate letters instead of a
    picture.
  - `fetch_flag_png`: downloads a small flag PNG icon from flagcdn.com. This
    is what the GUI uses so the flag always renders as an actual picture,
    regardless of installed fonts. Results are cached in-process so each
    country is only downloaded once per run.
"""

import logging
from typing import Dict, List, Optional

import requests

from . import config

log = logging.getLogger(__name__)

_flag_png_cache: Dict[str, Optional[bytes]] = {}


def country_code_to_flag_emoji(country_code: str) -> str:
    """
    Convert a 2-letter ISO country code (e.g. "US") into a flag emoji (🇺🇸).
    Falls back to a generic globe icon when the code is missing/unknown.
    Used for text-only exports (CSV/TXT), not for the GUI table.
    """
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        return "🏳️"
    offset = 0x1F1E6 - ord("A")
    return "".join(chr(ord(ch.upper()) + offset) for ch in country_code)


def fetch_flag_png(country_code: str) -> Optional[bytes]:
    """
    Download (and cache) a small PNG flag icon for a 2-letter country code.
    Returns None if the code is invalid or the download fails - callers
    should fall back to showing the plain country-code text in that case.
    """
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        return None

    code = country_code.lower()
    if code in _flag_png_cache:
        return _flag_png_cache[code]

    url = config.FLAG_ICON_URL.format(code=code)
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        _flag_png_cache[code] = response.content
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to fetch flag icon for %s: %s", country_code, exc)
        _flag_png_cache[code] = None

    return _flag_png_cache[code]


def _chunk(items: List[str], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def lookup_countries(ip_list: List[str]) -> Dict[str, str]:
    """
    Resolve a list of IP addresses to 2-letter country codes.

    Returns a dict {ip: country_code}. IPs that fail to resolve are omitted,
    callers should treat a missing entry as "unknown".
    """
    result: Dict[str, str] = {}

    for batch in _chunk(ip_list, config.GEOIP_BATCH_SIZE):
        payload = [{"query": ip, "fields": "query,countryCode,status"} for ip in batch]
        try:
            response = requests.post(config.GEOIP_BATCH_URL, json=payload, timeout=15)
            response.raise_for_status()
            for entry in response.json():
                if entry.get("status") == "success":
                    result[entry["query"]] = entry.get("countryCode", "")
        except Exception as exc:  # noqa: BLE001
            log.warning("GeoIP batch lookup failed: %s", exc)

    return result
