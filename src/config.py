"""
Central configuration for the proxy checker.
All tunable defaults live here so the GUI and CLI stay in sync.
"""

# Default number of worker threads used to test proxies concurrently.
DEFAULT_THREADS = 100

# Default per-request timeout (seconds) for a single proxy check.
DEFAULT_TIMEOUT = 8

# Endpoints used to verify that a proxy is actually forwarding traffic.
# We only need one plain HTTP echo endpoint and one HTTPS echo endpoint.
HTTP_CHECK_URL = "http://httpbin.org/ip"
HTTPS_CHECK_URL = "https://api.ipify.org?format=json"

# Public proxy list sources. Each entry is a plain-text list of "ip:port" lines.
# Having several sources means one dead source does not stop the whole run.
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
]

# Free, no-API-key-required batch GeoIP endpoint (45 requests/minute limit).
# Docs: https://ip-api.com/docs/api:batch
GEOIP_BATCH_URL = "http://ip-api.com/batch"
GEOIP_BATCH_SIZE = 100  # ip-api.com allows up to 100 IPs per batch request

# Output files.
RESULTS_CSV = "live_proxies.csv"
LOG_FILE = "proxy_checker.log"
