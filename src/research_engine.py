import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict
import requests

from src.config import settings, DATA_DIR

logger = logging.getLogger(__name__)

ARCHETYPES = [
    {
        "id": "myth_vs_reality_math",
        "name": "Myth vs. Reality Math Comparison",
        "queries": [
            "mutual fund direct vs regular plan returns calculation India",
            "SIP vs lumpsum returns inflation calculation India",
            "sovereign gold bond vs gold ETF tax comparison",
            "buying vs renting house true cost EMI interest India",
            "FD real returns negative after tax inflation India"
        ]
    },
    {
        "id": "hidden_fee_audit",
        "name": "The Hidden Fee & Deduction Audit",
        "queries": [
            "credit card minimum due interest trap calculation India",
            "brokerage STT stamp duty hidden charges retail traders",
            "zero cost EMI processing fee hidden charges India",
            "personal loan prepayment penalty APR reality India",
            "car loan reducing vs flat interest rate trap India"
        ]
    },
    {
        "id": "institutional_playbook",
        "name": "The Institutional Playbook & Regulatory Debunk",
        "queries": [
            "SEBI F&O contract size new rules retail traders",
            "FII DII trading activity Nifty divergence",
            "SEBI warning small cap mid cap froth mutual funds",
            "IPO retail oversubscription listing day trap",
            "RBI repo rate change banking net interest margin impact"
        ]
    }
]

CURATED_FALLBACKS = {
    "myth_vs_reality_math": {
        "title": "The 1% Expense Ratio Illusion: How Direct Plans Save ₹34 Lakhs",
        "source": "SEBI Mutual Fund Regulations & Compounding Math",
        "raw_text": "Retail investors assume a 1% distributor commission is negligible. On a ₹15,000 monthly SIP compounding at 12% over 25 years, a Regular Plan yields ₹2.42 Crore while a Direct Plan yields ₹2.76 Crore. That 1% fee quietly transferred ₹34 Lakhs of your compounding wealth to distributors without adding a single percentage point of performance.",
        "numbers_detected": ["1%", "₹15,000", "12%", "25 years", "₹2.42 Crore", "₹2.76 Crore", "₹34 Lakhs"]
    },
    "hidden_fee_audit": {
        "title": "The Credit Card Minimum Due Trap: ₹50,000 Ballooning to ₹1.8 Lakhs",
        "source": "RBI Master Direction on Credit Card Operations & Compound Interest",
        "raw_text": "Paying only the 5% 'Minimum Amount Due' on your credit card triggers compound interest of 42% to 48% annualized. An unpaid balance of ₹50,000 takes over 14 years to clear if you pay only minimums, costing more than ₹1,80,000 in pure interest and GST. Interest-free grace periods are instantly revoked on all new transactions the moment you leave a single rupee unpaid.",
        "numbers_detected": ["5%", "42%", "48%", "₹50,000", "14 years", "₹1,80,000"]
    },
    "institutional_playbook": {
        "title": "SEBI's ₹15 Lakh F&O Rule: The Real Math Behind Retail Option Wipeouts",
        "source": "SEBI Study on Retail Trading in Equity F&O Segment",
        "raw_text": "SEBI's latest official study revealed that 93% of retail traders lose an average of ₹1.25 Lakhs in F&O trading. To curb retail leverage, SEBI raised minimum derivative contract sizes from ₹5 Lakhs to ₹15 Lakhs. While headlines claim this protects beginners, institutions use the increased liquidity barriers to tighten option spreads and dominate intraday block volumes.",
        "numbers_detected": ["93%", "₹1.25 Lakhs", "₹5 Lakhs", "₹15 Lakhs"]
    }
}


class ResearchEngine:
    def __init__(self):
        self.used_topics_file = DATA_DIR / "used_carousel_topics.json"
        self._load_memory()

    def _load_memory(self):
        if self.used_topics_file.exists():
            try:
                with open(self.used_topics_file, "r", encoding="utf-8") as f:
                    self.memory = json.load(f)
            except Exception:
                self.memory = {"topics": [], "used_archetypes": []}
        else:
            self.memory = {"topics": [], "used_archetypes": []}

    def _save_memory(self):
        try:
            with open(self.used_topics_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save carousel memory: %s", e)

    def select_next_archetype(self) -> dict:
        """Cycles cleanly through the 3 archetypes to ensure daily format variety."""
        used = self.memory.get("used_archetypes", [])
        last_archetype_id = used[-1] if used else None
        
        # Pick the next one in the list
        for i, arc in enumerate(ARCHETYPES):
            if arc["id"] == last_archetype_id:
                next_arc = ARCHETYPES[(i + 1) % len(ARCHETYPES)]
                return next_arc
        return ARCHETYPES[0]

    def fetch_market_topic(self, override_query: Optional[str] = None) -> dict:
        """Fetches a high-converting topic via SerpApi or curated math fallback."""
        archetype = self.select_next_archetype()
        logger.info("Selected Carousel Archetype: [%s]", archetype["name"])

        # Try SerpApi if key is configured
        if settings.SERPAPI_KEY and settings.SERPAPI_KEY.strip():
            query = override_query or archetype["queries"][len(self.memory.get("topics", [])) % len(archetype["queries"])]
            logger.info("Querying SerpApi for market topic: '%s'...", query)
            try:
                params = {
                    "engine": "google_news",
                    "q": query,
                    "gl": "in",
                    "hl": "en",
                    "api_key": settings.SERPAPI_KEY.strip(),
                }
                res = requests.get("https://serpapi.com/search", params=params, timeout=15)
                res.raise_for_status()
                data = res.json()
                news_results = data.get("news_results", [])
                
                for item in news_results:
                    title = item.get("title", "").strip()
                    snippet = item.get("snippet", "").strip()
                    source = item.get("source", {}).get("name", "Market Financial Sources")
                    
                    if not title or len(title) < 15:
                        continue
                    
                    # Anti-repetition check
                    if self._is_repetitive(title):
                        continue
                    
                    # Detect numbers in title/snippet
                    nums = re.findall(r"(?:₹|\$)?\d+(?:[\.,]\d+)?(?:\s?(?:%|Cr|Lakh|Lakhs|Crore|Crores|bps|x|years|months))?", f"{title} {snippet}")
                    clean_nums = [n.strip() for n in nums if len(n.strip()) > 1]
                    
                    topic_data = {
                        "title": title,
                        "archetype": archetype["id"],
                        "archetype_name": archetype["name"],
                        "source": source,
                        "raw_text": f"{title}. {snippet}",
                        "numbers_detected": clean_nums[:5],
                        "date": datetime.now(timezone.utc).strftime("%d %b %Y"),
                        "from_live_api": True
                    }
                    self._record_topic(title, archetype["id"])
                    logger.info("✓ Discovered fresh market topic: '%s'", title)
                    return topic_data

            except Exception as e:
                logger.warning("SerpApi search failed (%s); using curated archetype fallback.", e)

        # Use curated fallback for selected archetype
        fallback = CURATED_FALLBACKS.get(archetype["id"], CURATED_FALLBACKS["myth_vs_reality_math"])
        topic_data = {
            "title": fallback["title"],
            "archetype": archetype["id"],
            "archetype_name": archetype["name"],
            "source": fallback["source"],
            "raw_text": fallback["raw_text"],
            "numbers_detected": fallback["numbers_detected"],
            "date": datetime.now(timezone.utc).strftime("%d %b %Y"),
            "from_live_api": False
        }
        self._record_topic(fallback["title"], archetype["id"])
        logger.info("✓ Using curated archetype topic: '%s'", fallback["title"])
        return topic_data

    def _is_repetitive(self, title: str) -> bool:
        past_topics = [t.get("title", "").lower() for t in self.memory.get("topics", [])[-30:]]
        title_words = set(re.findall(r"\w+", title.lower()))
        for past in past_topics:
            past_words = set(re.findall(r"\w+", past))
            overlap = len(title_words.intersection(past_words))
            if overlap >= 4:
                return True
        return False

    def _record_topic(self, title: str, archetype_id: str):
        self.memory.setdefault("topics", []).append({
            "title": title,
            "archetype": archetype_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.memory.setdefault("used_archetypes", []).append(archetype_id)
        # Keep last 60
        self.memory["topics"] = self.memory["topics"][-60:]
        self.memory["used_archetypes"] = self.memory["used_archetypes"][-60:]
        self._save_memory()
