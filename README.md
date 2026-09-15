# Proxy Checker (GUI Edition)

A fast, multithreaded HTTP/HTTPS proxy checker with a desktop GUI. It pulls
proxy lists from several free public sources, tests each proxy concurrently,
resolves the country of every live proxy and shows the results live in a
dedicated results window.

## Features

- 🖥️ **Desktop GUI** (Tkinter, no extra GUI dependency) — a single,
  resizable window split into two columns: **Process** (settings, controls,
  progress bar, log) on the left and a live-updating **Results** table on
  the right.
- 🌍 **Country flags** — each live proxy is geolocated and shown with its
  flag emoji, IP, port and HTTPS support.
- 🚀 **Multithreaded** checking (configurable thread count, default 100).
- 🔒 **Real HTTPS detection** — every proxy is tested against both a plain
  HTTP endpoint and an HTTPS endpoint, so "HTTPS" in the results means the
  proxy can actually tunnel HTTPS traffic, not just that it responded.
- 📚 **Multiple proxy sources** merged and deduplicated, so one dead source
  doesn't stop a run.
- ⏹️ **Start/Stop control** — cancel a run in progress at any time.
- 💾 **CSV export**, both automatically after each run (`live_proxies.csv`)
  and on demand from the Results window ("Export CSV" button).
- 🧵 Fully non-blocking UI — networking happens on background threads and
  reports progress through a thread-safe queue.

## Project layout

```
proxy_checker/
├── main.py              # entry point, launches the GUI
├── requirements.txt
├── src/
│   ├── config.py         # thread count, timeouts, sources, URLs
│   ├── sources.py         # downloads & merges proxy lists
│   ├── geoip.py            # batch country lookups + flag emoji
│   ├── checker.py           # threaded checking engine
│   └── gui.py                # Tkinter GUI (single window, two-column layout)
└── README.md
```

## Requirements

- Python 3.10+
- `requests` (see `requirements.txt`)

Tkinter ships with the standard Python installer on Windows and macOS.
On Linux you may need to install it separately, e.g. on Debian/Ubuntu:

```bash
sudo apt install python3-tk
```

## Installation

```bash
git clone git@github.com:agteamdev/proxy_checker.git
cd proxy_checker
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

1. (Optional) adjust **Threads** and **Timeout** in the left "Settings" panel.
2. Click **Start**.
3. Watch the right-hand "Live proxies" table fill up in real time:
   Flag | IP | Port | HTTPS, while the left panel shows progress and a log.
4. Click **Stop** at any time to cancel; already-found proxies are kept.
5. When the run finishes, results are saved to `live_proxies.csv`
   automatically. You can also click **Export CSV** under the results table
   to save a snapshot at any point.

## Configuration

All defaults (thread count, timeout, proxy sources, check endpoints, output
file names) live in `src/config.py` and can be edited directly, or adjusted
per-run from the GUI (threads/timeout).

## How HTTPS support is determined

Each proxy is first tested against a plain HTTP endpoint. If — and only
if — that succeeds, it is also tested against an HTTPS endpoint
(`https://api.ipify.org`). A proxy that passes both checks is marked
**HTTPS**; a proxy that only passes the HTTP check is marked **HTTP only**.

## GeoIP attribution

Country lookups use the free [ip-api.com](https://ip-api.com) batch
endpoint (no API key required, 45 requests/minute limit, which the batching
in `geoip.py` respects by grouping up to 100 IPs per request).

## Roadmap ideas

- SOCKS4/SOCKS5 proxy support in addition to HTTP/HTTPS.
- Column sorting and filtering in the results table.
- Anonymity level detection (transparent / anonymous / elite).
- Packaging as a standalone executable (PyInstaller) for users without
  Python installed.

## License

MIT License — see [LICENSE](LICENSE).
