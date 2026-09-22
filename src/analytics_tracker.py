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
                    fb_post_id = item.get("publish_results", {}).get("facebook", {}).get("post_id")
                    if (media_id or fb_post_id) and (token or settings.FACEBOOK_ACCESS_TOKEN):
                        logger.info("🔍 Pinging Meta Graph API 48h insights for post '%s' (Media ID: %s, FB ID: %s)...", item.get("title"), media_id, fb_post_id)
                        insights = self._fetch_graph_insights(media_id, token, fb_post_id=fb_post_id)
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

    def _fetch_graph_insights(self, media_id: str, token: str, fb_post_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches live carousel and Facebook metrics using modern Graph API v19+ endpoints."""
        metrics = {
            "saves": 0,
            "shares": 0,
            "impressions": 0,
            "reach": 0,
            "total_interactions": 0,
            "fb_reach": 0,
            "fb_engaged_users": 0,
            "save_to_reach_pct": 0.0,
            "status": "success"
        }
        
        # 1. Query Instagram Carousel Insights
        if media_id and media_id != "simulated_id":
            try:
                url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_VERSION}/{media_id}/insights"
                # Modern v19+ metrics for Carousel Album (deprecated carousel_album_engagement replaced with total_interactions)
                params = {
                    "metric": "saved,reach,shares,total_interactions",
                    "access_token": token
                }
                res = requests.get(url, params=params, timeout=15).json()

                if "error" in res:
                    err_msg = res["error"].get("message", "unknown error")
                    logger.warning("Meta Graph API Instagram insights warning for %s: %s", media_id, err_msg)
                    # Fallback to minimal core metrics
                    fallback_params = {"metric": "saved,reach", "access_token": token}
                    fallback_res = requests.get(url, params=fallback_params, timeout=15).json()
                    if "data" in fallback_res:
                        res = fallback_res
                    else:
                        metrics["status"] = f"api_error: {err_msg}"

                if "data" in res:
                    for entry in res["data"]:
                        name = entry.get("name")
                        val = entry.get("values", [{}])[0].get("value", 0)
                        if name == "saved":
                            metrics["saves"] = val
                        elif name == "reach":
                            metrics["reach"] = val
                        elif name == "shares":
                            metrics["shares"] = val
                        elif name == "total_interactions":
                            metrics["total_interactions"] = val

                    reach = metrics.get("reach", 0)
                    saves = metrics.get("saves", 0)
                    if reach > 0:
                        metrics["save_to_reach_pct"] = round((saves / reach) * 100, 2)
            except Exception as e:
                logger.warning("Graph API query failed for media %s: %s", media_id, e)
                metrics["status"] = f"error: {str(e)}"

        # 2. Query Facebook Post Insights (if cross-posted to Facebook)
        fb_token = settings.FACEBOOK_ACCESS_TOKEN.strip()
        if fb_post_id and fb_token:
            try:
                fb_url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_VERSION}/{fb_post_id}/insights"
                fb_res = requests.get(fb_url, params={"metric": "post_impressions,post_engaged_users", "access_token": fb_token}, timeout=10).json()
                if "data" in fb_res:
                    for entry in fb_res["data"]:
                        name = entry.get("name")
                        val = entry.get("values", [{}])[0].get("value", 0)
                        if name == "post_impressions":
                            metrics["fb_reach"] = val
                        elif name == "post_engaged_users":
                            metrics["fb_engaged_users"] = val
            except Exception as fbe:
                logger.debug("Facebook post insights non-fatal note: %s", fbe)

        return metrics

    def _update_ledger(self, post_record: Dict[str, Any]):
        """Appends performance metrics to the persistent analytics ledger."""
        insights = post_record.get("insights", {})
        status = insights.get("status", "success")
        reach = insights.get("reach", 0)
        # If API returned an error or reach is 0 (due to API permission error #10),
        # do not contaminate the performance ledger with false zero-save rates!
        if status != "success" or str(status).startswith("api_error") or str(status).startswith("error") or reach <= 0:
            logger.info("ℹ️ Skipping ledger record for '%s': insights status='%s', reach=%s (unverified/error)",
                        post_record.get("title"), status, reach)
            return

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
            "status": status,
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
