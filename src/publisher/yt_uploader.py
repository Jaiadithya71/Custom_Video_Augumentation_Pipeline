"""
YouTube Uploader: Publishes video files to YouTube using Data API v3 and OAuth 2.0.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class YouTubeAuthError(Exception):
    """Raised when YouTube credentials are not found or authorization fails."""
    pass


class YouTubeUploader:
    """Manages authentication and video uploads to YouTube channels via Data API v3."""

    def __init__(
        self,
        client_secrets_file: Optional[str] = None,
        token_file: Optional[str] = None,
    ):
        self.token_file = Path(token_file) if token_file else (PROJECT_ROOT / "temp" / "youtube_token.json")
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.client_secrets_file = client_secrets_file or self._find_client_secrets()

    def _find_client_secrets(self) -> Optional[str]:
        """Auto-discovers client_secret.json in project root or common locations."""
        candidates = [
            PROJECT_ROOT / "client_secret.json",
            PROJECT_ROOT / "client_secrets.json",
            Path("client_secret.json"),
            Path("client_secrets.json"),
            Path("credentials.json"),
            Path(os.getenv("GOOGLE_CLIENT_SECRET_FILE", "")),
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
        return None

    def get_authenticated_service(self):
        """Authenticates with YouTube API using saved token or launching OAuth flow."""
        creds = None
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                logger.warning(f"Could not load saved token: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}. Re-authenticating...")
                    creds = None

            if not creds:
                if not self.client_secrets_file or not Path(self.client_secrets_file).exists():
                    raise YouTubeAuthError(
                        "Google OAuth Client Secrets file not found.\n"
                        "To upload directly to YouTube:\n"
                        "1. Go to Google Cloud Console (https://console.cloud.google.com)\n"
                        "2. Enable 'YouTube Data API v3'\n"
                        "3. Go to 'Credentials' -> 'Create Credentials' -> 'OAuth client ID' (Application type: Desktop App)\n"
                        "4. Download the JSON file and save it as 'client_secret.json' in this project's root folder."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for next run
            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "28",
        privacy_status: str = "unlisted",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Uploads a video to YouTube with resumable chunks.
        privacy_status can be: 'public', 'unlisted', or 'private'.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        youtube = self.get_authenticated_service()

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags or ["Shorts"],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        # 2MB chunks for robust upload
        media = MediaFileUpload(
            str(path),
            chunksize=2 * 1024 * 1024,
            resumable=True,
            mimetype="video/mp4",
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and progress_callback:
                progress_callback(status.progress())

        video_id = response.get("id")
        youtube_url = f"https://youtube.com/shorts/{video_id}"
        logger.info(f"Video uploaded successfully! ID: {video_id} ({youtube_url})")

        return {
            "video_id": video_id,
            "url": youtube_url,
            "title": title,
            "privacy_status": privacy_status,
            "response": response,
        }
