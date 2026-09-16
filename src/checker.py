"""
Core proxy-checking engine.

Design notes:
- Only SOCKS4 and SOCKS5 proxies are supported (plain HTTP proxies are not
  fetched or tested anymore). Connecting through them requires the
  `requests[socks]` extra (PySocks) - see requirements.txt.
- A proxy is checked with a single HTTPS request through the tunnel. That
  one request tells us three things at once:
    1. Alive or dead - if the request fails or times out, the proxy is
       dropped entirely and never appears in the results.
    2. Latency - round-trip time of that request, in milliseconds.
    3. Anonymity level - by inspecting which headers httpbin.org received,
       we can tell whether the proxy leaked our real IP address
       (Transparent), added forwarding headers without leaking it
       (Anonymous), or added nothing at all (Elite / high anonymity).
- Runs entirely off the GUI thread; progress and results are reported
  through a thread-safe queue.Queue so the GUI can poll it with
  `root.after(...)` without ever blocking.
- A `threading.Event` is used as a cooperative stop flag so the user can
  cancel a run in progress from the GUI.
"""

import csv
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from . import config, geoip, sources

log = logging.getLogger(__name__)


@dataclass
class ProxyResult:
    ip: str
    port: str
    protocol: str          # "SOCKS4" or "SOCKS5"
    anonymity: str          # "Transparent" / "Anonymous" / "Elite" / "Unknown"
    latency_ms: int
    country_code: str = ""
    flag_png: Optional[bytes] = field(default=None, repr=False)

    @property
    def flag_emoji(self) -> str:
        return geoip.country_code_to_flag_emoji(self.country_code)

    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"


class ProxyChecker:
    """
    Orchestrates fetching, checking and reporting proxies.

    Usage:
        checker = ProxyChecker(threads=100, timeout=8)
        checker.start(on_event=my_queue.put)  # runs in a background thread
        ...
        checker.stop()  # optional, requests cancellation
    """

    def __init__(self, threads: int = config.DEFAULT_THREADS,
                 timeout: int = config.DEFAULT_TIMEOUT):
        self.threads = threads
        self.timeout = timeout
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self.results: List[ProxyResult] = []
        self._own_ip: Optional[str] = None

    # -- public API ---------------------------------------------------

    def start(self, on_event: "queue.Queue.put") -> None:
        """
        Start checking in a background thread. `on_event` is called with
        dicts describing progress, e.g.:
          {"type": "status", "text": "..."}
          {"type": "progress", "done": 12, "total": 500}
          {"type": "result", "result": ProxyResult(...)}
          {"type": "finished", "elapsed": 12.3, "found": 7}
        """
        self._stop_event.clear()
        self.results = []
        self._worker_thread = threading.Thread(
            target=self._run, args=(on_event,), daemon=True
        )
        self._worker_thread.start()

    def stop(self) -> None:
        """Request cancellation of the current run (cooperative, not instant)."""
        self._stop_event.set()

    # -- internals ------------------------------------------------------

    def _run(self, on_event) -> None:
        start_time = time.time()

        on_event({"type": "status", "text": "Detecting your public IP (for anonymity checks)..."})
        try:
            self._own_ip = requests.get(config.OWN_IP_URL, timeout=10).json().get("ip")
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not determine own IP: %s", exc)
            self._own_ip = None

        on_event({"type": "status", "text": "Downloading proxy lists..."})
        raw_proxies = sources.fetch_all_proxies()
        total = len(raw_proxies)

        if total == 0:
            on_event({"type": "status", "text": "No proxies found from any source."})
            on_event({"type": "finished", "elapsed": 0, "found": 0})
            return

        on_event({"type": "status", "text": f"Checking {total} proxies with {self.threads} threads..."})

        done = 0
        alive: List[ProxyResult] = []
        lock = threading.Lock()

        def worker(item):
            nonlocal done
            if self._stop_event.is_set():
                return
            protocol, ip_port = item
            outcome = self._check_single(protocol, ip_port)
            with lock:
                done += 1
                on_event({"type": "progress", "done": done, "total": total})
            if outcome is not None:
                with lock:
                    alive.append(outcome)

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(worker, item) for item in raw_proxies]
            for f in futures:
                if self._stop_event.is_set():
                    break
                f.result()

        # Resolve countries + flag icons for everything alive, in one batch pass.
        if alive:
            on_event({"type": "status", "text": "Resolving proxy countries..."})
            country_map = geoip.lookup_countries([r.ip for r in alive])
            flag_cache = {}
            for r in alive:
                r.country_code = country_map.get(r.ip, "")
                if r.country_code and r.country_code not in flag_cache:
                    flag_cache[r.country_code] = geoip.fetch_flag_png(r.country_code)
                r.flag_png = flag_cache.get(r.country_code)
                on_event({"type": "result", "result": r})

        self.results = alive
        self._save_csv(alive)
        self._save_txt(alive)

        elapsed = round(time.time() - start_time, 2)
        on_event({"type": "finished", "elapsed": elapsed, "found": len(alive)})

    def _check_single(self, protocol: str, ip_port: str) -> Optional[ProxyResult]:
        """
        Test one SOCKS4/SOCKS5 "ip:port" proxy with a single HTTPS request.
        Returns a ProxyResult (country_code/flag filled in later, in a
        batch) if the proxy is alive, else None.
        """
        try:
            ip, port = ip_port.split(":")
        except ValueError:
            return None

        proxy_url = f"{protocol}://{ip_port}"
        proxies = {"http": proxy_url, "https": proxy_url}

        started = time.time()
        try:
            r = requests.get(config.ANONYMITY_CHECK_URL, proxies=proxies, timeout=self.timeout)
            if r.status_code != 200:
                return None
            payload = r.json()
        except Exception:
            return None
        latency_ms = int((time.time() - started) * 1000)

        anonymity = self._classify_anonymity(payload.get("headers", {}))

        return ProxyResult(
            ip=ip,
            port=port,
            protocol=protocol.upper(),
            anonymity=anonymity,
            latency_ms=latency_ms,
        )

    def _classify_anonymity(self, headers: dict) -> str:
        """
        Transparent: the proxy forwarded our real public IP to the target
                      site (the site can trivially identify who is behind it).
        Anonymous:   the proxy added forwarding-related headers, but did not
                      leak our real IP.
        Elite:       no forwarding headers were added at all - the target
                      site cannot tell a proxy is being used.
        """
        lower_headers = {k.lower(): v for k, v in headers.items()}
        combined_values = " ".join(str(v) for v in lower_headers.values())

        if self._own_ip and self._own_ip in combined_values:
            return "Transparent"
        if any(h in lower_headers for h in config.PROXY_INDICATOR_HEADERS):
            return "Anonymous"
        return "Elite"

    def _save_csv(self, results: List[ProxyResult]) -> None:
        with open(config.RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Country", "IP", "Port", "Protocol", "Anonymity", "Latency_ms"])
            for r in results:
                writer.writerow([r.country_code, r.ip, r.port, r.protocol, r.anonymity, r.latency_ms])
        log.info("Saved %d live proxies to %s", len(results), config.RESULTS_CSV)

    def _save_txt(self, results: List[ProxyResult]) -> None:
        """Plain text export, one usable proxy URL per line, e.g. socks5://1.2.3.4:1080"""
        with open(config.RESULTS_TXT, "w", encoding="utf-8") as f:
            for r in results:
                f.write(f"{r.protocol.lower()}://{r.address}\n")
        log.info("Saved %d live proxies to %s", len(results), config.RESULTS_TXT)
