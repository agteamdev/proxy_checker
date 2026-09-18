"""
Central configuration for the proxy checker.
All tunable defaults live here so the GUI and CLI stay in sync.
"""

# Default number of worker threads used to test proxies concurrently.
DEFAULT_THREADS = 100

# Default per-request timeout (seconds) for a single proxy check.
DEFAULT_TIMEOUT = 8

# A single HTTPS endpoint used to verify that a proxy is alive AND to detect
# its anonymity level, by inspecting which headers it forwards. httpbin.org
# echoes back every request header it received, which is exactly what we
# need. Because SOCKS4/SOCKS5 tunnel raw TCP, a single HTTPS request through
# the tunnel proves both "the proxy works" and "HTTPS traffic passes".
ANONYMITY_CHECK_URL = "https://httpbin.org/get"

# Used once at startup to learn our own public IP, so we can tell whether a
# proxy is leaking it (== "transparent").
OWN_IP_URL = "https://api.ipify.org?format=json"

# Response headers that indicate a proxy is adding forwarding information.
# Their mere presence (regardless of value) already downgrades a proxy from
# "Elite" to at least "Anonymous".
PROXY_INDICATOR_HEADERS = {"via", "x-forwarded-for", "forwarded", "x-forwarded"}

# Public proxy list sources, grouped by protocol. Each entry is a plain-text
# list of "ip:port" lines. Only SOCKS4/SOCKS5 proxies are supported - plain
# HTTP proxies are intentionally not fetched or checked anymore.
# Having several sources per protocol means one dead source does not stop
# the whole run.
PROXY_SOURCES = {
    "http": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    ],
    "socks4": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    ],
    "socks5": [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    ],
}

# Free, no-API-key-required batch GeoIP endpoint (45 requests/minute limit).
# Docs: https://ip-api.com/docs/api:batch
GEOIP_BATCH_URL = "http://ip-api.com/batch"
GEOIP_BATCH_SIZE = 100  # ip-api.com allows up to 100 IPs per batch request

# Small flag icon CDN, no API key required. {code} is a lowercase ISO
# 2-letter country code, e.g. "us". Used instead of flag emoji because many
# Linux systems have no color-emoji font installed and render flag emoji as
# two separate letters instead of a picture.
FLAG_ICON_URL = "https://flagcdn.com/16x12/{code}.png"

# Default filename suggestions shown in the Export CSV/TXT save dialogs.
# Results are never written to disk automatically - only on explicit export.
RESULTS_CSV = "live_proxies.csv"
RESULTS_TXT = "live_proxies.txt"
LOG_FILE = "proxy_checker.log"
