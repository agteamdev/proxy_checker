"""
Fetches raw proxy lists (ip:port) from several free public sources
and merges/deduplicates them into a single list.
"""

import logging
import re
from typing import List

import requests

from . import config

log = logging.getLogger(__name__)

# Matches "1.2.3.4:8080" style entries and ignores anything else on the line.
IP_PORT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")


def _fetch_one(url: str, timeout: int = 15) -> List[str]:
    """Download a single proxy list source and extract ip:port pairs."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        matches = IP_PORT_RE.findall(response.text)
        pairs = [f"{ip}:{port}" for ip, port in matches]
        log.info("Source %s returned %d proxies", url, len(pairs))
        return pairs
    except Exception as exc:  # noqa: BLE001 - we want to keep going on any failure
        log.warning("Failed to fetch source %s: %s", url, exc)
        return []


def fetch_all_proxies(sources: List[str] = None) -> List[str]:
    """
    Download every configured source and return a deduplicated list
    of "ip:port" strings, preserving first-seen order.
    """
    sources = sources or config.PROXY_SOURCES
    seen = set()
    merged: List[str] = []

    for url in sources:
        for pair in _fetch_one(url):
            if pair not in seen:
                seen.add(pair)
                merged.append(pair)

    log.info("Total unique proxies collected: %d", len(merged))
    return merged
