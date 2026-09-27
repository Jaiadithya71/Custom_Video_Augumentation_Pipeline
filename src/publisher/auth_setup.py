"""
One-time interactive OAuth setup script for YouTube Shorts publishing.
Run this script to authenticate your Google/YouTube account once.
The token will be securely cached at temp/youtube_token.json.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.publisher.yt_uploader import YouTubeUploader, SCOPES
from google_auth_oauthlib.flow import InstalledAppFlow

def authenticate():
    uploader = YouTubeUploader()
    if not uploader.client_secrets_file or not Path(uploader.client_secrets_file).exists():
        print(f"Error: client_secret.json not found in {PROJECT_ROOT}", flush=True)
        sys.exit(1)

    print("=" * 65, flush=True)
    print("  YouTube Shorts Publisher - One-Time Account Authentication", flush=True)
    print("=" * 65, flush=True)
    print(f"Found Client Secrets at: {uploader.client_secrets_file}", flush=True)
    print("A browser window will open to authenticate your YouTube channel.", flush=True)
    print("NOTE: Make sure to log into the Google Account that you added as a", flush=True)
    print("'Test user' in your Google Cloud Console OAuth consent screen.", flush=True)
    print("-" * 65, flush=True)

    flow = InstalledAppFlow.from_client_secrets_file(
        uploader.client_secrets_file,
        scopes=SCOPES,
        redirect_uri="http://localhost:8080/"
    )
    
    # Run local server on port 8080 or random free port
    try:
        creds = flow.run_local_server(port=8080, open_browser=True, prompt="consent")
    except Exception:
        # Fallback to dynamic port if 8080 in use
        flow = InstalledAppFlow.from_client_secrets_file(uploader.client_secrets_file, scopes=SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True, prompt="consent")

    with open(uploader.token_file, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print("-" * 65, flush=True)
    print("Authentication SUCCESSFUL!", flush=True)
    print(f"OAuth token saved to: {uploader.token_file}", flush=True)
    print("You can now publish shorts directly from the dashboard or CLI!", flush=True)
    print("=" * 65, flush=True)

if __name__ == "__main__":
    authenticate()
