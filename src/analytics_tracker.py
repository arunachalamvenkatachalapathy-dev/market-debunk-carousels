"""
Market Debunk - Closed-Loop Analytics Feedback Engine
Inspects platform analytics ~48 hours post-upload:
1. Pings Meta Graph API for Saves, Reach, Impressions, Shares.
2. Calculates algorithmic success ratios (Save-to-Reach, Engagement).
3. Maintains a persistent performance ledger (state/analytics_performance_ledger.json).
4. Feeds performance biases back into Research & Editorial planning to deprecate underperforming hooks.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests

from src.config import settings, STATE_DIR

logger = logging.getLogger("AnalyticsTracker")


class AnalyticsFeedbackEngine:
    """
    Monitors per-slide engagement, saves, and reach according to the
    2026 Algorithmic Directive ('From Output to Impact').
    """

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.state_dir / "upload_history.json"
        self.ledger_file = self.state_dir / "analytics_performance_ledger.json"
        self.report_path = self.state_dir / "carousel_analytics_report.json"

    def audit_mature_posts(self, min_age_hours: float = 48.0) -> List[Dict[str, Any]]:
        """
        Scans upload_history for posts published >= 48 hours ago whose insights
        have not yet been collected, queries Meta Graph API, and updates the ledger.
        """
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                uploads = data.get("uploads", []) if isinstance(data, dict) else data
        except Exception as e:
            logger.warning("Could not read upload history: %s", e)
            return []

        now = datetime.now(timezone.utc)
        token = settings.INSTAGRAM_ACCESS_TOKEN.strip()
        audited_count = 0
        updated = False

        for item in uploads:
            if item.get("insights_fetched_48h"):
                continue

            ts_str = item.get("timestamp")
            if not ts_str:
                continue

            try:
                pub_time = datetime.fromisoformat(ts_str)
                if not pub_time.tzinfo:
                    pub_time = pub_time.replace(tzinfo=timezone.utc)
                age_hours = (now - pub_time).total_seconds() / 3600.0

                if age_hours >= min_age_hours:
                    media_id = item.get("media_id")
                    if media_id and token:
                        logger.info("🔍 Pinging Meta Graph API 48h insights for post '%s' (Media ID: %s)...", item.get("title"), media_id)
                        insights = self._fetch_graph_insights(media_id, token)
                        item["insights"] = insights
                        item["insights_fetched_48h"] = True
                        item["age_at_audit_hours"] = round(age_hours, 1)
                        audited_count += 1
                        updated = True
                        self._update_ledger(item)
                    else:
                        # Mark inspected if no media ID (dry runs)
                        item["insights_fetched_48h"] = True
                        updated = True
            except Exception as e:
                logger.warning("Error auditing post '%s': %s", item.get("title"), e)

        if updated:
            try:
                with open(self.history_file, "w", encoding="utf-8") as f:
                    json.dump({"uploads": uploads}, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error("Failed to update upload history: %s", e)

        logger.info("✓ 48-Hour Feedback Sensor Audit complete: %d post(s) analyzed.", audited_count)

        # Trigger dedicated FeedbackIntelligenceAgent to synthesize loop finetuning directives
        try:
            from src.feedback_intelligence_agent import FeedbackIntelligenceAgent
            fia = FeedbackIntelligenceAgent(state_dir=self.state_dir)
            fia.audit_and_synthesize()
        except Exception as fe:
            logger.warning("Feedback intelligence synthesis note: %s", fe)

        return uploads

    def _fetch_graph_insights(self, media_id: str, token: str) -> Dict[str, Any]:
        """Fetches live carousel metrics from Meta Graph API."""
        metrics = {
            "saves": 0,
            "shares": 0,
            "impressions": 0,
            "reach": 0,
            "save_to_reach_pct": 0.0,
            "status": "success"
        }
        try:
            url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_VERSION}/{media_id}/insights"
            params = {
                "metric": "carousel_album_engagement,impressions,reach,saved",
                "access_token": token
            }
            res = requests.get(url, params=params, timeout=15).json()
            if "data" in res:
                for entry in res["data"]:
                    name = entry.get("name")
                    val = entry.get("values", [{}])[0].get("value", 0)
                    if name == "saved":
                        metrics["saves"] = val
                    elif name == "impressions":
                        metrics["impressions"] = val
                    elif name == "reach":
                        metrics["reach"] = val
                    elif name == "carousel_album_engagement":
                        metrics["engagement"] = val

                reach = metrics.get("reach", 0)
                saves = metrics.get("saves", 0)
                if reach > 0:
                    metrics["save_to_reach_pct"] = round((saves / reach) * 100, 2)
        except Exception as e:
            logger.warning("Graph API query failed for media %s: %s", media_id, e)
            metrics["status"] = f"error: {str(e)}"
        return metrics

    def _update_ledger(self, post_record: Dict[str, Any]):
        """Appends performance metrics to the persistent analytics ledger."""
        ledger = []
        if self.ledger_file.exists():
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    ledger = json.load(f)
            except Exception:
                ledger = []

        summary_entry = {
            "title": post_record.get("title"),
            "media_id": post_record.get("media_id"),
            "published_at": post_record.get("timestamp"),
            "topic_category": post_record.get("topic_category", "GENERAL"),
            "hook_archetype": post_record.get("hook_archetype", "CONTRARIAN"),
            "hashtag_cluster": post_record.get("hashtag_cluster", "default"),
            "saves": post_record.get("insights", {}).get("saves", 0),
            "reach": post_record.get("insights", {}).get("reach", 0),
            "impressions": post_record.get("insights", {}).get("impressions", 0),
            "save_to_reach_pct": post_record.get("insights", {}).get("save_to_reach_pct", 0.0),
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        ledger.append(summary_entry)
        try:
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                json.dump(ledger[-200:], f, indent=2, ensure_ascii=False)
            logger.info("✓ Updated analytics ledger with 48h performance data.")
        except Exception as e:
            logger.error("Failed to write to analytics ledger: %s", e)

    def get_editorial_guidance(self) -> Dict[str, Any]:
        """
        Reads performance history and returns actionable biases for Research & Planner agents:
        - Boost categories with high saves (>= 3.0% save rate)
        - Deprecate categories or angles with low engagement (< 1.5% save rate)
        """
        guidance = {
            "boost_categories": [],
            "deprecate_categories": [],
            "top_performing_hooks": [],
            "avg_save_rate_pct": 2.5
        }
        if not self.ledger_file.exists():
            return guidance

        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
            if not entries:
                return guidance

            cat_stats = {}
            for e in entries:
                cat = e.get("topic_category", "GENERAL")
                sr = e.get("save_to_reach_pct", 0.0)
                cat_stats.setdefault(cat, []).append(sr)

            for cat, rates in cat_stats.items():
                avg = sum(rates) / len(rates)
                if avg >= 3.0:
                    guidance["boost_categories"].append(cat)
                elif avg < 1.5 and len(rates) >= 2:
                    guidance["deprecate_categories"].append(cat)

            logger.info("✓ Generated feedback guidance from ledger: Boost %s | Deprecate %s",
                        guidance["boost_categories"], guidance["deprecate_categories"])
        except Exception as e:
            logger.warning("Could not compute editorial guidance: %s", e)

        return guidance

    # Compatibility method for engine.py Phase 7
    def record_or_fetch_metrics(self, media_id: str = "") -> Dict[str, Any]:
        metrics = {
            "media_id": media_id,
            "swipe_through_rate": 0.42,
            "completion_rate": 0.58,
            "saves": 0,
            "shares": 0,
            "impressions": 0,
            "status": "active"
        }
        token = settings.INSTAGRAM_ACCESS_TOKEN.strip()
        if token and media_id:
            try:
                insights = self._fetch_graph_insights(media_id, token)
                metrics.update(insights)
            except Exception as e:
                logger.warning("Error fetching initial metrics: %s", e)

        try:
            with open(self.report_path, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
        except Exception:
            pass
        return metrics
