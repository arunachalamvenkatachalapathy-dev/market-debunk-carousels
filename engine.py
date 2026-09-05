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


def run_pipeline(dry_run: bool = False, override_query: str = None) -> bool:
    logger.info("=" * 60)
    logger.info("🚀 MARKET DEBUNK FINANCIAL CAROUSEL ENGINE (7:00 PM DAILY)")
    logger.info("   Mode: %s", "DRY RUN (No live publishing)" if dry_run else "LIVE PRODUCTION")
    logger.info("=" * 60)

    thinker = ThinkerEngine()

    try:
        # ── Phase 1: Research & Archetype Sourcing ─────────────────────────────
        logger.info("═══ Phase 1: Market & Regulatory Research Sourcing ═══")
        research_engine = ResearchEngine()
        topic_data = research_engine.fetch_market_topic(override_query=override_query)
        logger.info("📌 Topic: '%s' | Archetype: [%s]", topic_data.get("title"), topic_data.get("archetype_name"))

        # ── Phase 2: Financial Planning & Brief ────────────────────────────────
        logger.info("═══ Phase 2: Financial Planning & Creative Brief ═══")
        planner = PlannerAgent(llm_client=EditorialEngine().client)
        plan = planner.plan(topic_data)
        prompt_eng = PromptEngineer()
        brief = prompt_eng.build_brief(plan)

        # ── Phase 3: Two-Pass Composition & Fact-Checking Gate ─────────────────
        logger.info("═══ Phase 3: Two-Pass Slide Composition & Numeric Fact-Check ═══")
        editorial_engine = EditorialEngine()
        deck = editorial_engine.compose_carousel(topic_data, brief)
        slides = deck.get("slides", [])
        logger.info("✓ Composed %d slides with verified anchor metrics.", len(slides))

        # ── Phase 4: Playwright Visual Rendering & PDF Compilation ─────────────
        logger.info("═══ Phase 4: Playwright 1080x1080 Retina Rendering ═══")
        image_director = ImageDirector()
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        visual_pkg = image_director.render_carousel(deck, run_id=run_id)
        slide_paths = visual_pkg["slide_paths"]
        pdf_path = visual_pkg["pdf_path"]

        # ── Phase 5: Export Master Package for Tamil Companion ────────────────
        master_pkg_path = STATE_DIR / "market_debunk_carousel_master.json"
        master_package = {
            "topic": topic_data,
            "plan": plan,
            "deck": deck,
            "run_id": run_id,
            "slide_count": len(slide_paths),
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        with open(master_pkg_path, "w", encoding="utf-8") as f:
            json.dump(master_package, f, indent=2, ensure_ascii=False)
        logger.info("✓ Exported Tamil Master Package to: %s", master_pkg_path)

        # ── Phase 6: Prepare Direct Raw Image URLs for Instagram ───────────────
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

        # ── Phase 7: Multi-Platform Publishing ────────────────────────────────
        logger.info("═══ Phase 7: Multi-Platform Distribution ═══")
        publisher = Publisher()
        results = publisher.publish_all(
            image_urls=image_urls,
            slide_paths=slide_paths,
            pdf_path=pdf_path,
            caption=deck.get("caption", ""),
            title=topic_data.get("title", "Market Debunk"),
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
            context={"dry_run": dry_run, "override_query": override_query}
        )
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Debunk Carousel Engine")
    parser.add_argument("--dry-run", action="store_true", help="Generate visuals and PDF without publishing")
    parser.add_argument("--query", type=str, default=None, help="Override search query for market topic")
    args = parser.parse_args()

    success = run_pipeline(dry_run=args.dry_run, override_query=args.query)
    sys.exit(0 if success else 1)
