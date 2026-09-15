"""
Core proxy-checking engine.

Design notes:
- Runs entirely off the GUI thread; progress and results are reported through
  a thread-safe queue.Queue so the GUI can poll it with `root.after(...)`
  without ever blocking.
- Each proxy is tested against a plain HTTP endpoint and an HTTPS endpoint
  separately, so we can report real HTTPS support instead of guessing.
- A `threading.Event` is used as a cooperative stop flag so the user can
  cancel a run in progress from the GUI.
"""

import csv
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional

import requests

from . import config, geoip, sources

log = logging.getLogger(__name__)


@dataclass
class ProxyResult:
    ip: str
    port: str
    https: bool
    country_code: str
    latency_ms: int

    @property
    def flag(self) -> str:
        return geoip.country_code_to_flag(self.country_code)


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

        def worker(ip_port: str):
            nonlocal done
            if self._stop_event.is_set():
                return
            outcome = self._check_single(ip_port)
            with lock:
                done += 1
                on_event({"type": "progress", "done": done, "total": total})
            if outcome is not None:
                with lock:
                    alive.append(outcome)

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(worker, p) for p in raw_proxies]
            for f in futures:
                if self._stop_event.is_set():
                    break
                f.result()

        # Resolve countries for everything that is alive, in one batch pass.
        if alive:
            on_event({"type": "status", "text": "Resolving proxy countries..."})
            country_map = geoip.lookup_countries([r.ip for r in alive])
            for r in alive:
                r.country_code = country_map.get(r.ip, "")
                on_event({"type": "result", "result": r})

        self.results = alive
        self._save_csv(alive)

        elapsed = round(time.time() - start_time, 2)
        on_event({"type": "finished", "elapsed": elapsed, "found": len(alive)})

    def _check_single(self, ip_port: str) -> Optional[ProxyResult]:
        """
        Test one "ip:port" proxy. Returns a ProxyResult (country_code left
        blank, filled in later in a batch) if the proxy is alive, else None.
        """
        try:
            ip, port = ip_port.split(":")
        except ValueError:
            return None

        proxies = {"http": f"http://{ip_port}", "https": f"http://{ip_port}"}

        # 1. Plain HTTP check - this is the minimum bar for "alive".
        started = time.time()
        try:
            r = requests.get(config.HTTP_CHECK_URL, proxies=proxies, timeout=self.timeout)
            if r.status_code != 200:
                return None
        except Exception:
            return None
        latency_ms = int((time.time() - started) * 1000)

        # 2. HTTPS check - determines whether the proxy can tunnel HTTPS traffic.
        https_ok = False
        try:
            r = requests.get(config.HTTPS_CHECK_URL, proxies=proxies, timeout=self.timeout)
            https_ok = r.status_code == 200
        except Exception:
            https_ok = False

        return ProxyResult(ip=ip, port=port, https=https_ok, country_code="", latency_ms=latency_ms)

    def _save_csv(self, results: List[ProxyResult]) -> None:
        with open(config.RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Country", "IP", "Port", "HTTPS", "Latency_ms"])
            for r in results:
                writer.writerow([r.country_code, r.ip, r.port, "Yes" if r.https else "No", r.latency_ms])
        log.info("Saved %d live proxies to %s", len(results), config.RESULTS_CSV)
