"""Runner script for Content Agent Dashboard."""

import os
import sys
import webbrowser
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from src.dashboard.app import app

if __name__ == "__main__":
    port = 5000
    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 60)
    print(f"🚀 CONTENT AGENT DASHBOARD RUNNING AT: {url}")
    print("=" * 60)
    print("Open your browser and navigate to the link above.\n")

    # Automatically open default web browser
    try:
        webbrowser.open(url)
    except Exception:
        pass

    app.run(host="127.0.0.1", port=port, debug=False)
