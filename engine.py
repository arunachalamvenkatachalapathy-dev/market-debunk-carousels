"""
Market Debunk 7:00 PM Financial Carousel Engine
Main Orchestrator
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import settings, STATE_DIR
from src.research_engine import ResearchEngine
from src.news_comprehension_agent import NewsComprehensionAgent
from src.workflow_agents import PlannerAgent, PromptEngineer
from src.editorial_engine import EditorialEngine
from src.image_director import ImageDirector
from src.publisher import Publisher
from src.thinker_engine import ThinkerEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("market_debunk_carousel")


def run_pipeline(dry_run: bool = False, draft_music: bool = False, override_query: str = None) -> bool:
    is_draft_music = draft_music or getattr(settings, "DRAFT_MUSIC_MODE", False)
    mode_str = "DRY RUN (No live publishing)" if dry_run else ("DRAFT MUSIC (Staging for Instagram music attachment)" if is_draft_music else "LIVE PRODUCTION")
    logger.info("=" * 60)
    logger.info("🚀 MARKET DEBUNK FINANCIAL CAROUSEL ENGINE (7:00 AM DAILY)")
    logger.info("   Mode: %s", mode_str)
    logger.info("   Format: Instagram Native 4:5 (1080x1350 px)")
    logger.info("=" * 60)

    thinker = ThinkerEngine()

    try:
        # ── Phase 1: Real-Time Financial News Ingestion (Max 48h Freshness) ──────
        logger.info("═══ Phase 1: Real-Time Market News Ingestion (Max 48h Freshness) ═══")
        research_engine = ResearchEngine()
        topic_data = research_engine.fetch_fresh_market_news(max_age_hours=48, override_query=override_query)
        logger.info("📌 Sourced: '%s' | Age: %sh | Source: [%s]", topic_data.get("title"), topic_data.get("age_hours"), topic_data.get("source"))

        # ── Phase 2: Deep Financial Comprehension & Debunk Extraction ────────────
        logger.info("═══ Phase 2: Deep Financial News Comprehension & Debunk Extraction ═══")
        comprehension_agent = NewsComprehensionAgent()
        news_analysis = comprehension_agent.analyze_news_item(topic_data)
        topic_data["news_analysis"] = news_analysis
        logger.info("🎯 Debunk Angle: '%s' | Category: [%s]", news_analysis.get("headline_hook"), news_analysis.get("debunk_category"))

        # ── Phase 3: Financial Planning & Creative Brief ────────────────────────
        logger.info("═══ Phase 3: Financial Planning & Creative Brief ═══")
        planner = PlannerAgent(llm_client=EditorialEngine().client)
        plan = planner.plan(topic_data)
        prompt_eng = PromptEngineer()
        brief = prompt_eng.build_brief(plan)

        # ── Phase 4: Two-Pass Composition & Fact-Checking Gate ─────────────────
        logger.info("═══ Phase 4: Two-Pass Slide Composition & Numeric Fact-Check ═══")
        editorial_engine = EditorialEngine()
        deck = editorial_engine.compose_carousel(topic_data, brief)
        slides = deck.get("slides", [])
        from src.validator import CarouselValidator
        is_valid, content_report = CarouselValidator.validate_content(deck)
        if not is_valid:
            raise ValueError(f"Deck failed content validation gate: {content_report}")
        logger.info("✅ %s", content_report)

        # Audio Automation: Select trending Reels audio track
        from src.audio_director import AudioDirector
        audio_director = AudioDirector()
        audio_track = audio_director.select_audio_recommendation()
        deck["audio_recommendation"] = audio_track

        # Caption Engineering: Apply 4-part formula with audio note and keyword trigger
        from src.workflow_agents import GrammarAgent
        grammar_agent = GrammarAgent()
        deck["caption"] = grammar_agent.format_converting_caption(deck, topic_data, audio_track)

        # ── Phase 5: Playwright 1080x1350 Retina Rendering & PDF Compilation ───
        logger.info("═══ Phase 5: Playwright 1080x1350 (4:5) Retina Rendering ═══")
        image_director = ImageDirector()
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        visual_pkg = image_director.render_carousel(deck, run_id=run_id)
        slide_paths = visual_pkg["slide_paths"]
        pdf_path = visual_pkg["pdf_path"]

        # ── Phase 5b: Mandatory Per-Slide and PDF Validation Gate ────────────
        logger.info("═══ Phase 5b: Automated Render & Dimension Quality Gate ═══")
        for sp in slide_paths:
            is_png_valid, png_report = CarouselValidator.validate_slide_png(sp)
            if not is_png_valid:
                raise ValueError(f"Slide PNG validation failed: {png_report}")
            logger.info("✓ %s", png_report)

        is_pdf_valid, pdf_report = CarouselValidator.validate_pdf(pdf_path)
        if not is_pdf_valid:
            raise ValueError(f"Multi-page PDF validation failed: {pdf_report}")
        logger.info("✅ %s", pdf_report)

        # ── Phase 6: Export Master Package for Tamil Companion & Analytics ───
        from src.analytics_tracker import AnalyticsFeedbackEngine
        analytics_engine = AnalyticsFeedbackEngine(state_dir=STATE_DIR)
        analytics_engine.record_or_fetch_metrics()

        master_pkg_path = STATE_DIR / "market_debunk_carousel_master.json"
        master_package = {
            "topic": topic_data,
            "plan": plan,
            "deck": deck,
            "audio": audio_track,
            "run_id": run_id,
            "slide_count": len(slide_paths),
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        with open(master_pkg_path, "w", encoding="utf-8") as f:
            json.dump(master_package, f, indent=2, ensure_ascii=False)
        logger.info("✓ Exported Tamil Master Package to: %s", master_pkg_path)

        # ── Phase 7: Prepare Direct Raw Image URLs for Instagram ───────────────
        repo_owner = "arunachalamvenkatachalapathy-dev"
        repo_name = "market-debunk-carousels"
        image_urls = [
            f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/master/state/carousel_slides/slide_{i+1}_{run_id}.png"
            for i in range(len(slide_paths))
        ]

        # In CI, if live production run, pre-push slides so raw GitHub URLs are accessible
        if not dry_run and os.getenv("GITHUB_ACTIONS") == "true":
            logger.info("🚀 Pre-pushing generated slides to GitHub master before live publishing...")
            os.system("git config --global user.name 'github-actions[bot]'")
            os.system("git config --global user.email 'github-actions[bot]@users.noreply.github.com'")
            os.system("git add state/carousel_slides/ state/latest_carousel.pdf state/market_debunk_carousel_master.json")
            os.system('git commit -m "chore: pre-push slides for live publishing [skip ci]" || true')
            os.system("git push origin master || true")
            import time
            time.sleep(3)

        # ── Phase 8: Multi-Platform Publishing ────────────────────────────────
        logger.info("═══ Phase 8: Multi-Platform Distribution ═══")
        publisher = Publisher()
        results = publisher.publish_all(
            image_urls=image_urls,
            slide_paths=slide_paths,
            pdf_path=pdf_path,
            caption=deck.get("caption", ""),
            title=topic_data.get("title", "Market Debunk"),
            audio_track=audio_track,
            draft_music=is_draft_music,
            dry_run=dry_run
        )

        logger.info("📢 Publishing Results: %s", json.dumps(results, indent=2))
        logger.info("=" * 60)
        logger.info("🎉 CAROUSEL WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.critical("💥 Pipeline halted by unhandled exception: %s", e, exc_info=True)
        thinker.diagnose_pipeline_crash(
            phase="PIPELINE_ORCHESTRATION",
            error=e,
            context={"dry_run": dry_run, "draft_music": draft_music, "override_query": override_query}
        )
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Debunk Carousel Engine")
    parser.add_argument("--dry-run", action="store_true", help="Generate visuals and PDF without publishing")
    parser.add_argument("--draft-music", action="store_true", help="Stage carousel and dispatch to Telegram with trending audio guidance to add music on Instagram")
    parser.add_argument("--query", type=str, default=None, help="Override search query for market topic")
    args = parser.parse_args()

    success = run_pipeline(dry_run=args.dry_run, draft_music=args.draft_music, override_query=args.query)
    sys.exit(0 if success else 1)
