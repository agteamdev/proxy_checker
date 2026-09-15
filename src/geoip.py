"""
Batch GeoIP lookups and country-code -> flag-emoji conversion.

We resolve countries in batches (instead of one request per proxy) to stay
well inside the free ip-api.com rate limit and to make lookups much faster.
"""

import logging
from typing import Dict, List

import requests

from . import config

log = logging.getLogger(__name__)


def country_code_to_flag(country_code: str) -> str:
    """
    Convert a 2-letter ISO country code (e.g. "US") into a flag emoji (🇺🇸).
    Falls back to a generic globe icon when the code is missing/unknown.
    """
    if not country_code or len(country_code) != 2 or not country_code.isalpha():
        return "🏳️"
    # Regional indicator symbols start at U+1F1E6 for 'A'.
    offset = 0x1F1E6 - ord("A")
    return "".join(chr(ord(ch.upper()) + offset) for ch in country_code)


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
