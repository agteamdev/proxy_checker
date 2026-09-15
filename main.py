"""
Entry point.

Run with:
    python main.py

Launches the Tkinter GUI. Fetching, checking and GeoIP resolution all
happen on background threads so the interface never freezes.
"""

from src.gui import run

if __name__ == "__main__":
    run()
