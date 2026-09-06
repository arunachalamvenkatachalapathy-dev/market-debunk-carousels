import random
import logging
from typing import Dict, Any

logger = logging.getLogger("AudioDirector")

TRENDING_FINANCE_TRACKS = [
    {
        "title": "Cornfield Chase (Interstellar Piano/Synth)",
        "artist": "Hans Zimmer / Dorian Marko",
        "bpm": 100,
        "vibe": "Cinematic Tension & Focus",
        "reels_boost_tier": "High Velocity",
        "search_query": "Hans Zimmer Cornfield Chase Dorian Marko"
    },
    {
        "title": "Time (Institutional Minimalist Mix)",
        "artist": "Hans Zimmer",
        "bpm": 124,
        "vibe": "Deep Mathematical Compounding",
        "reels_boost_tier": "Top Tier",
        "search_query": "Hans Zimmer Time Inception"
    },
    {
        "title": "Pulse of Capital (Synthwave Focus)",
        "artist": "Maxence Cyrin / Philip Glass",
        "bpm": 118,
        "vibe": "Analytical Depth & Clarity",
        "reels_boost_tier": "Steady Evergreen",
        "search_query": "Philip Glass Opening Piano"
    },
    {
        "title": "Solitude (Dark Academic Finance)",
        "artist": "M83 / Felsmann + Tiley",
        "bpm": 110,
        "vibe": "Institutional Truth / Whistleblower",
        "reels_boost_tier": "Viral Editorial",
        "search_query": "M83 Solitude Felsmann Tiley"
    },
    {
        "title": "Experience (Ludovico Instrumental)",
        "artist": "Ludovico Einaudi",
        "bpm": 95,
        "vibe": "Compounding Breakthrough",
        "reels_boost_tier": "Top Tier",
        "search_query": "Ludovico Einaudi Experience"
    }
]

class AudioDirector:
    """
    Curates high-retention audio tracks for Instagram Carousels to activate
    the Instagram algorithm's Reels surface recommendation engine.
    """
    def __init__(self):
        self.tracks = TRENDING_FINANCE_TRACKS

    def select_audio_recommendation(self, archetype: str = "") -> Dict[str, Any]:
        track = random.choice(self.tracks)
        logger.info("🎵 Curated trending audio recommendation: %s by %s", track["title"], track["artist"])
        return track

    def format_audio_caption_note(self, track: Dict[str, Any]) -> str:
        return (
            f"\n\n🎵 Recommended Audio for Reels Algorithm: '{track['title']}' by {track['artist']} "
            f"(Tap 'Add Music' in Instagram before posting)"
        )
