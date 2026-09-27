"""
Metadata Generator: Creates YouTube Shorts titles, descriptions, tags, and category IDs.
"""

from typing import Dict, List, Any, Optional


class ShortsMetadataGenerator:
    """Generates high-CTR metadata tailored for YouTube Shorts SEO and algorithmic recommendation."""

    DEFAULT_CATEGORY_ID = "28"  # Science & Technology

    CATEGORY_MAP = {
        "science": "28",
        "tech": "28",
        "space": "28",
        "education": "27",
        "business": "27",
        "podcast": "24",  # Entertainment
        "entertainment": "24",
    }

    def generate_metadata(
        self,
        short_info: Dict[str, Any],
        video_info: Optional[Dict[str, Any]] = None,
        narrative_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generates comprehensive YouTube metadata package for a short."""
        raw_title = short_info.get("title", "Must Watch Moment")
        banner = short_info.get("banner_text", "")
        text = short_info.get("text", "")
        guest = video_info.get("title", "") if video_info else ""
        channel = video_info.get("channel", "") if video_info else ""

        # 1. Shorts Title (Under 100 chars, includes #Shorts)
        clean_title = raw_title.replace("•", "|").strip()
        if "#Shorts" not in clean_title and "#shorts" not in clean_title:
            if len(clean_title) + len(" #Shorts") <= 95:
                title = f"{clean_title} #Shorts"
            else:
                title = f"{clean_title[:85]}... #Shorts"
        else:
            title = clean_title[:95]

        # 2. Hashtags
        hashtags = ["#Shorts", "#YouTubeShorts", "#Viral"]
        tags = ["shorts", "youtube shorts", "viral", "podcast"]

        if channel:
            hashtags.append(f"#{channel.replace(' ', '')}")
            tags.append(channel.lower())

        lower_text = (text + " " + banner + " " + raw_title).lower()
        if any(w in lower_text for w in ["space", "nasa", "astronaut", "orbit", "satellite"]):
            hashtags.extend(["#Space", "#NASA", "#Astronaut"])
            tags.extend(["space", "nasa", "astronaut", "iss", "space exploration"])
        if "sunita" in lower_text or "williams" in lower_text:
            hashtags.append("#SunitaWilliams")
            tags.append("sunita williams")
        if "kalpana" in lower_text or "columbia" in lower_text:
            hashtags.extend(["#KalpanaChawla", "#Columbia"])
            tags.extend(["kalpana chawla", "space shuttle columbia", "nasa tragedy"])
        if "india" in lower_text or "himalayas" in lower_text:
            hashtags.extend(["#India", "#Himalayas"])
            tags.extend(["india from space", "himalayas", "isro"])

        # 3. Description
        desc_lines = [
            f"🚀 {raw_title}",
            "",
            f"\"{text[:200]}...\"" if text else "",
            "",
            f"🎙️ Original Conversation: {video_info.get('title', 'Full Episode') if video_info else 'Full Podcast'}",
            f"👤 Host/Channel: {channel or 'Raj Shamani'}",
            "",
            "🔔 Subscribe for daily high-impact moments and life-changing conversations!",
            "",
            " ".join(hashtags[:7]),
        ]
        description = "\n".join([line for line in desc_lines if line is not None])

        # 4. Category
        category_id = self.DEFAULT_CATEGORY_ID
        if narrative_profile:
            niche = narrative_profile.get("channel_niche", "").lower()
            for k, cat in self.CATEGORY_MAP.items():
                if k in niche:
                    category_id = cat
                    break

        return {
            "title": title,
            "description": description,
            "tags": list(dict.fromkeys(tags))[:15],
            "category_id": category_id,
            "privacy_status": "unlisted",  # Safe default: review before public release
        }
