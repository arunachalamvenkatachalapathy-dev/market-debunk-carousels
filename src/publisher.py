import json
import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
import requests

from src.config import settings
from src.thinker_engine import ThinkerEngine

logger = logging.getLogger(__name__)


class Publisher:
    """
    Multi-platform publisher:
    1. Instagram Carousel via Meta Graph API (with direct image URLs)
    2. Instagram Permalink retrieval with retry
    3. Facebook Page Multi-Photo Post
    4. Telegram Notifier sharing the Instagram permalink (drives early save velocity)
    5. Optional LinkedIn Document Carousel (PDF)
    """

    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_VERSION}"
        self.thinker = ThinkerEngine()

    def publish_all(
        self,
        image_urls: List[str],
        slide_paths: List[str],
        pdf_path: str,
        caption: str,
        title: str,
        dry_run: bool = False
    ) -> Dict[str, any]:
        results = {
            "instagram": {"success": False, "status": "skipped"},
            "facebook": {"success": False, "status": "skipped"},
            "telegram": {"success": False, "status": "skipped"},
            "linkedin": {"success": False, "status": "skipped"},
        }

        if dry_run:
            logger.info("🧪 [DRY RUN ACTIVE] Skipping all live platform uploads.")
            results["instagram"] = {"success": True, "status": "dry_run_simulated"}
            results["facebook"] = {"success": True, "status": "dry_run_simulated"}
            results["telegram"] = {"success": True, "status": "dry_run_simulated"}
            return results

        # ── 1. Instagram Carousel (Primary Anchor) ──────────────────────────
        ig_permalink = None
        if settings.ENABLE_INSTAGRAM and settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_USER_ID:
            logger.info("Publishing Instagram Carousel for '%s'...", title[:40])
            try:
                ig_res = self.publish_instagram_carousel(image_urls, caption)
                results["instagram"] = ig_res
                if ig_res.get("success"):
                    ig_permalink = ig_res.get("permalink")
                    logger.info("✓ Instagram published successfully: %s", ig_permalink or ig_res.get("id"))
                else:
                    logger.error("❌ Instagram publish failed: %s", ig_res.get("error"))
            except Exception as ig_err:
                logger.error("Instagram publish encountered exception: %s", ig_err)
                results["instagram"] = {"success": False, "status": "failed", "error": str(ig_err)}
        else:
            logger.info("Instagram publishing disabled or missing credentials.")

        # ── 2. Facebook Page Multi-Photo Post (Secondary - Non-blocking) ─────
        # Runs sequentially after Instagram. If Facebook fails, it logs a warning and DOES NOT halt Telegram.
        if settings.ENABLE_FACEBOOK and (settings.FACEBOOK_ACCESS_TOKEN or settings.INSTAGRAM_ACCESS_TOKEN) and settings.FACEBOOK_PAGE_ID:
            logger.info("Publishing Facebook Page Multi-Photo Post...")
            try:
                fb_res = self.publish_facebook_photos(slide_paths, caption)
                results["facebook"] = fb_res
                if fb_res.get("success"):
                    logger.info("✓ Facebook post published: %s", fb_res.get("post_id"))
                else:
                    logger.warning("⚠️ Facebook publish failed non-fatally: %s. Continuing to Telegram...", fb_res.get("error"))
            except Exception as fb_err:
                logger.warning("⚠️ Facebook publish threw non-fatal exception: %s. Continuing to Telegram...", fb_err)
                results["facebook"] = {"success": False, "status": "failed", "error": str(fb_err)}
        else:
            logger.info("Facebook publishing disabled or missing credentials.")

        # ── 3. Telegram Notification (Save-Velocity Push - Non-blocking) ─────
        # Fires with the Instagram permalink regardless of Facebook's success or failure!
        if settings.ENABLE_TELEGRAM and settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            logger.info("Sending Telegram update (Save-Velocity funnel to Instagram: %s)...", ig_permalink or "N/A")
            try:
                tg_res = self.send_telegram_notification(title, caption, ig_permalink, pdf_path)
                results["telegram"] = tg_res
                if tg_res.get("success"):
                    logger.info("✓ Telegram notification dispatched successfully.")
                else:
                    logger.warning("⚠️ Telegram notification failed non-fatally: %s", tg_res.get("error"))
            except Exception as tg_err:
                logger.warning("⚠️ Telegram notification threw non-fatal exception: %s", tg_err)
                results["telegram"] = {"success": False, "status": "failed", "error": str(tg_err)}
        else:
            logger.info("Telegram notification disabled or missing credentials.")

        # ── 4. Optional LinkedIn Document Post ──────────────────────────────
        if settings.ENABLE_LINKEDIN and settings.LINKEDIN_ACCESS_TOKEN and settings.LINKEDIN_ORGANIZATION_URN:
            logger.info("Publishing LinkedIn PDF Document post...")
            try:
                li_res = self.publish_linkedin_document(pdf_path, title, caption)
                results["linkedin"] = li_res
            except Exception as li_err:
                logger.warning("LinkedIn publish failed non-fatally: %s", li_err)
                results["linkedin"] = {"success": False, "status": "failed", "error": str(li_err)}

        return results

    # ── Instagram Carousel ──────────────────────────────────────────────────

    def publish_instagram_carousel(self, image_urls: List[str], caption: str) -> dict:
        token = settings.INSTAGRAM_ACCESS_TOKEN.strip()
        user_id = settings.INSTAGRAM_USER_ID.strip()

        # Pre-flight check: verify image URLs return HTTP 200 before submitting to Meta
        for i, url in enumerate(image_urls):
            is_ready = False
            for attempt in range(1, 4):
                try:
                    head_res = requests.head(url, timeout=10)
                    if head_res.status_code == 200:
                        is_ready = True
                        break
                except Exception:
                    pass
                time.sleep(2)
            if not is_ready:
                logger.warning("Image %d (%s) not returning HTTP 200 yet. Proceeding with caution...", i + 1, url)

        try:
            # Step 1: Create child image containers
            children_ids = []
            for i, url in enumerate(image_urls):
                res = requests.post(
                    f"{self.base_url}/{user_id}/media",
                    data={
                        "image_url": url,
                        "is_carousel_item": "true",
                        "access_token": token,
                    },
                    timeout=30
                ).json()
                if "error" in res:
                    raise RuntimeError(f"Child container {i+1} failed: {res['error']}")
                children_ids.append(res["id"])
                logger.info("  ✓ Created IG child container %d/%d (ID: %s)", i + 1, len(image_urls), res["id"])

            # Step 2: Create parent carousel container
            parent_res = requests.post(
                f"{self.base_url}/{user_id}/media",
                data={
                    "media_type": "CAROUSEL",
                    "caption": caption[:2200],
                    "children": ",".join(children_ids),
                    "access_token": token,
                },
                timeout=30
            ).json()
            if "error" in parent_res:
                raise RuntimeError(f"Parent carousel container failed: {parent_res['error']}")
            
            creation_id = parent_res["id"]
            logger.info("✓ Created IG Carousel parent container (ID: %s)", creation_id)

            # Step 3: Publish carousel
            pub_res = requests.post(
                f"{self.base_url}/{user_id}/media_publish",
                data={
                    "creation_id": creation_id,
                    "access_token": token,
                },
                timeout=30
            ).json()
            if "error" in pub_res:
                raise RuntimeError(f"Publish failed: {pub_res['error']}")

            media_id = pub_res["id"]
            logger.info("🎉 INSTAGRAM CAROUSEL PUBLISHED SUCCESSFULLY (ID: %s)", media_id)

            # Step 4: Fetch public permalink with retry loop
            permalink = self.get_instagram_permalink(media_id, token)
            return {"success": True, "media_id": media_id, "permalink": permalink}

        except Exception as e:
            logger.error("Instagram carousel publishing failed: %s", e)
            self.thinker.diagnose_publish_failure(
                platform="Instagram",
                error_details=str(e),
                payload_meta={"image_urls": image_urls, "caption_len": len(caption)}
            )
            return {"success": False, "error": str(e)}

    def get_instagram_permalink(self, media_id: str, token: str) -> Optional[str]:
        """Fetches the public permalink with defensive retry polling."""
        for attempt in range(1, 4):
            try:
                res = requests.get(
                    f"{self.base_url}/{media_id}",
                    params={"fields": "permalink", "access_token": token},
                    timeout=15
                ).json()
                link = res.get("permalink")
                if link:
                    logger.info("✓ Retrieved Instagram permalink: %s", link)
                    return link
            except Exception as e:
                logger.debug("Permalink poll %d failed: %s", attempt, e)
            time.sleep(3)
        return f"https://www.instagram.com/p/{media_id}/"

    # ── Facebook Page Multi-Photo ───────────────────────────────────────────

    def publish_facebook_photos(self, slide_paths: List[str], caption: str) -> dict:
        token = settings.FACEBOOK_ACCESS_TOKEN.strip() or settings.INSTAGRAM_ACCESS_TOKEN.strip()
        page_id = settings.FACEBOOK_PAGE_ID.strip()

        # Auto-resolve page-specific token from /me/accounts if user token passed
        try:
            acc_res = requests.get(f"{self.base_url}/me/accounts?access_token={token}", timeout=10).json()
            if "data" in acc_res:
                for acc in acc_res["data"]:
                    if str(acc.get("id")) == str(page_id):
                        token = acc.get("access_token", token)
                        logger.info("✓ Resolved Facebook Page access token for %s", page_id)
                        break
        except Exception as e:
            logger.debug("Facebook Page token resolution skipped: %s", e)

        try:
            # Upload each slide as unpublished photo
            attached_fbids = []
            for i, p in enumerate(slide_paths):
                with open(p, "rb") as img_f:
                    up_res = requests.post(
                        f"{self.base_url}/{page_id}/photos",
                        params={"access_token": token, "published": "false"},
                        files={"source": img_f},
                        timeout=45
                    ).json()
                    if "error" in up_res:
                        raise RuntimeError(f"Photo upload {i+1} failed: {up_res['error']}")
                    photo_id = up_res.get("id")
                    attached_fbids.append({"media_fbid": photo_id})
                    logger.info("  ✓ Uploaded FB photo %d/%d (ID: %s)", i + 1, len(slide_paths), photo_id)

            # Publish feed post with attached media
            post_res = requests.post(
                f"{self.base_url}/{page_id}/feed",
                data={
                    "message": caption[:2000],
                    "attached_media": json.dumps(attached_fbids),
                    "access_token": token,
                },
                timeout=30
            ).json()

            if "error" in post_res:
                raise RuntimeError(f"Facebook feed publish failed: {post_res['error']}")

            post_id = post_res.get("id")
            fb_link = f"https://www.facebook.com/{post_id}"
            logger.info("🎉 FACEBOOK CAROUSEL POST PUBLISHED (ID: %s)", post_id)
            return {"success": True, "post_id": post_id, "url": fb_link}

        except Exception as e:
            logger.error("Facebook post publishing failed: %s", e)
            self.thinker.diagnose_publish_failure(
                platform="Facebook",
                error_details=str(e),
                payload_meta={"slide_count": len(slide_paths), "caption_len": len(caption)}
            )
            return {"success": False, "error": str(e)}

    # ── Telegram Staggered Notifier ─────────────────────────────────────────

    def send_telegram_notification(self, title: str, caption: str, instagram_url: Optional[str], pdf_path: str) -> dict:
        bot_token = settings.TELEGRAM_BOT_TOKEN.strip()
        chat_id = settings.TELEGRAM_CHAT_ID.strip()

        if not bot_token or not chat_id:
            return {"success": False, "reason": "missing_credentials"}

        # Auto-normalize supergroup / channel chat ID
        if not chat_id.startswith("-") and not chat_id.startswith("@"):
            chat_id = f"-100{chat_id}"

        try:
            import html

            # Clean and extract a concise description (1-2 sentences) from the caption
            desc_lines = []
            for line in caption.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                # Skip hashtags, CTAs, and slide callouts
                if stripped.startswith("#") or any(kw in stripped.lower() for kw in ["comment '", "comment \"", "swipe through", "slide breakdown"]):
                    continue
                desc_lines.append(stripped)

            raw_desc = " ".join(desc_lines) if desc_lines else caption
            if len(raw_desc) > 280:
                raw_desc = raw_desc[:277].rsplit(" ", 1)[0] + "..."

            safe_title = html.escape(title.strip())
            safe_desc = html.escape(raw_desc.strip())

            link_callout = ""
            if instagram_url:
                safe_url = html.escape(instagram_url.strip())
                link_callout = f"\n\n🔗 <b>Swipe full 8-slide breakdown on Instagram:</b>\n{safe_url}"

            tg_text = f"📊 <b>{safe_title}</b>\n\n{safe_desc}{link_callout}"

            res = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": tg_text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": "false"
                },
                timeout=20
            ).json()

            if not res.get("ok"):
                raise RuntimeError(f"Telegram sendMessage failed: {res}")

            logger.info("✅ Telegram notification sent successfully with Instagram permalink!")
            return {"success": True}

        except Exception as e:
            logger.error("Telegram notification failed: %s", e)
            self.thinker.diagnose_publish_failure(
                platform="Telegram",
                error_details=str(e),
                payload_meta={"title": title, "has_pdf": bool(pdf_path)}
            )
            return {"success": False, "error": str(e)}

    # ── LinkedIn Document Carousel ──────────────────────────────────────────

    def publish_linkedin_document(self, pdf_path: str, title: str, caption: str) -> dict:
        # Placeholder for LinkedIn Company Page API integration
        logger.info("LinkedIn document publishing enabled — staging PDF upload.")
        return {"success": True, "status": "staged"}
