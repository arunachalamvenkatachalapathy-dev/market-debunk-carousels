"""
Market Debunk - Programmatic Jitter & Cooldown Manager
Enforces organic publication patterns:
1. Programmatic randomized jitter delay (14 to 28 minutes) on scheduled automated runs.
2. Mandatory 4 to 6-hour upload cooldown to prevent algorithmic cannibalization and shadow-suppression.
3. Historical upload recording for 48-hour analytics loop.
"""

import json
import logging
import os
import random
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from src.config import STATE_DIR

logger = logging.getLogger("JitterManager")


class JitterManager:
    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or STATE_DIR
        self.history_file = self.state_dir / "upload_history.json"
        self._ensure_state_dir()

    def _ensure_state_dir(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _load_history(self) -> list:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("uploads", []) if isinstance(data, dict) else data
            except Exception as e:
                logger.warning("Could not read upload history: %s", e)
        return []

    def _save_history(self, uploads: list):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump({"uploads": uploads[-100:]}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save upload history: %s", e)

    def check_cooldown(self, min_cooldown_hours: float = 4.0) -> Tuple[bool, str]:
        """
        Ensures at least min_cooldown_hours have elapsed since the last live upload.
        Prevents firing posts too close to each other.
        """
        uploads = self._load_history()
        if not uploads:
            return True, "No previous upload recorded; cooldown passed."

        last_upload = uploads[-1]
        last_time_str = last_upload.get("timestamp")
        if not last_time_str:
            return True, "Last upload timestamp invalid; cooldown passed."

        try:
            last_time = datetime.fromisoformat(last_time_str)
            if not last_time.tzinfo:
                last_time = last_time.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            elapsed_hours = (now - last_time).total_seconds() / 3600.0

            if elapsed_hours < min_cooldown_hours:
                remaining_mins = int((min_cooldown_hours - elapsed_hours) * 60)
                msg = (
                    f"⛔ Cooldown active! Last upload was {elapsed_hours:.2f}h ago "
                    f"('{last_upload.get('title', 'Unknown')}'). "
                    f"Mandatory {min_cooldown_hours}h spacing requires waiting {remaining_mins} more minutes."
                )
                logger.warning(msg)
                return False, msg

            return True, f"Cooldown passed: {elapsed_hours:.2f}h elapsed since last upload."
        except Exception as e:
            logger.warning("Error parsing cooldown timestamp: %s", e)
            return True, "Timestamp parse fallback; proceeding."

    def inject_jitter(
        self,
        target_window_start_ist: Optional[Tuple[int, int]] = None,
        target_window_end_ist: Optional[Tuple[int, int]] = None,
        edition: str = "daily",
        min_seconds: int = 14 * 60,
        max_seconds: int = 28 * 60,
        skip_jitter: bool = False,
        dry_run: bool = False
    ) -> int:
        """
        Calculates intelligent organic jitter using Target-Window Math.
        Supports both Morning (09:15 AM IST) and Evening (07:30 PM IST) publication editions:
        - Morning window: 09:05 - 09:25 AM IST (centered at 09:15 AM IST).
        - Evening window: 19:25 - 19:35 PM IST (centered at 07:30 PM IST).
        Absorbs GitHub Actions queue scheduling variance.
        """
        if skip_jitter or dry_run:
            logger.info("⏩ Jitter skipped (dry_run=%s, skip_jitter=%s).", dry_run, skip_jitter)
            return 0

        if os.getenv("SKIP_JITTER") == "true":
            logger.info("⏩ Jitter skipped via SKIP_JITTER environment variable.")
            return 0

        now_utc = datetime.now(timezone.utc)
        ist_offset = timedelta(hours=5, minutes=30)
        now_ist = now_utc + ist_offset

        # Detect or configure edition window
        if edition == "evening" or (edition == "daily" and now_ist.hour >= 16):
            start_tuple = target_window_start_ist or (19, 25)  # 07:25 PM IST
            end_tuple = target_window_end_ist or (19, 35)      # 07:35 PM IST (centered at 7:30 PM)
            cycle_start = now_ist.replace(hour=18, minute=30, second=0, microsecond=0)
            cycle_end = now_ist.replace(hour=20, minute=30, second=0, microsecond=0)
            edition_label = "EVENING (7:30 PM IST)"
        else:
            start_tuple = target_window_start_ist or (9, 5)    # 09:05 AM IST
            end_tuple = target_window_end_ist or (9, 25)       # 09:25 AM IST (centered at 9:15 AM)
            cycle_start = now_ist.replace(hour=8, minute=0, second=0, microsecond=0)
            cycle_end = now_ist.replace(hour=10, minute=30, second=0, microsecond=0)
            edition_label = "MORNING (9:15 AM IST)"

        if cycle_start <= now_ist <= cycle_end:
            win_start = now_ist.replace(hour=start_tuple[0], minute=start_tuple[1], second=0, microsecond=0)
            win_end = now_ist.replace(hour=end_tuple[0], minute=end_tuple[1], second=0, microsecond=0)
            
            window_span_secs = int((win_end - win_start).total_seconds())
            random_offset_secs = random.randint(0, max(0, window_span_secs))
            target_post_ist = win_start + timedelta(seconds=random_offset_secs)

            if now_ist < target_post_ist:
                delay = int((target_post_ist - now_ist).total_seconds())
                delay = min(delay, 50 * 60)
                mins = delay // 60
                secs = delay % 60
                logger.info(
                    "⏳ [TARGET-WINDOW JITTER - %s] Current IST: %02d:%02d:%02d | Target Publish IST: %02d:%02d:%02d | "
                    "Sleeping %dm %ds to absorb CI queue variance and land organically in target window.",
                    edition_label,
                    now_ist.hour, now_ist.minute, now_ist.second,
                    target_post_ist.hour, target_post_ist.minute, target_post_ist.second,
                    mins, secs
                )
                time.sleep(delay)
                logger.info("✓ Target window reached (%s). Proceeding with organic upload.", edition_label)
                return delay
            else:
                brief_delay = random.randint(15, 30)
                logger.warning(
                    "⚠️ [QUEUE DELAY DETECTED - %s] Current IST (%02d:%02d:%02d) is already past target (%02d:%02d:%02d). "
                    "Shortening jitter to %ds buffer to avoid missing target window.",
                    edition_label,
                    now_ist.hour, now_ist.minute, now_ist.second,
                    target_post_ist.hour, target_post_ist.minute, target_post_ist.second,
                    brief_delay
                )
                time.sleep(brief_delay)
                return brief_delay
        else:
            brief_delay = random.randint(15, 45)
            logger.info("ℹ️ Off-cycle execution (Current IST: %02d:%02d:%02d). Applying brief %ds jitter.",
                        now_ist.hour, now_ist.minute, now_ist.second, brief_delay)
            time.sleep(brief_delay)
            return brief_delay

    def record_successful_upload(
        self,
        title: str,
        media_id: str,
        publish_results: Dict[str, Any],
        topic_category: str = "GENERAL",
        hook_archetype: str = "CONTRARIAN",
        caption_hashtag_cluster: str = "default"
    ):
        """Records a successful upload into the local ledger for 48h analytics polling."""
        uploads = self._load_history()
        now = datetime.now(timezone.utc)
        record = {
            "title": title,
            "media_id": media_id,
            "timestamp": now.isoformat(),
            "topic_category": topic_category,
            "hook_archetype": hook_archetype,
            "hashtag_cluster": caption_hashtag_cluster,
            "publish_results": publish_results,
            "insights_fetched_48h": False,
            "insights": {}
        }
        uploads.append(record)
        self._save_history(uploads)
        logger.info("✓ Recorded upload in ledger: '%s' (Media ID: %s)", title, media_id)
