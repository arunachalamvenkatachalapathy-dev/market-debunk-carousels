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
from src.jitter_manager import JitterManager
from src.analytics_tracker import AnalyticsFeedbackEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("market_debunk_carousel")


def run_pipeline(dry_run: bool = False, override_query: str = None, edition: str = "daily", no_jitter: bool = False) -> bool:
    mode_str = "DRY RUN (No live publishing)" if dry_run else "LIVE DIRECT PRODUCTION"
    edition_label = f" ({edition.upper()} EDITION)" if edition != "daily" else ""
    logger.info("=" * 60)
    logger.info("🚀 MARKET DEBUNK FINANCIAL CAROUSEL ENGINE%s", edition_label)
    logger.info("   Mode: %s", mode_str)
    logger.info("   Format: Instagram Native 4:5 (1080x1350 px)")
    logger.info("=" * 60)

    thinker = ThinkerEngine()
    jitter_mgr = JitterManager()
    analytics_engine = AnalyticsFeedbackEngine()

    from src.evolutionary_memory import EvolutionaryMemory
    from src.creative_critic_agent import CreativeCriticAgent
    from src.visual_inspector_agent import VisualInspectorAgent

    evolutionary_memory = EvolutionaryMemory()
    evolutionary_directives = evolutionary_memory.get_prompt_directives()

    try:
        # ── Phase 0a: 48-Hour Closed-Loop Analytics Audit ─────────────────────
        logger.info("═══ Phase 0a: 48-Hour Feedback Sensor Audit ═══")
        analytics_engine.audit_mature_posts(min_age_hours=48.0)
        editorial_biases = analytics_engine.get_editorial_guidance()

        # ── Phase 0b: Organic Timing Jitter (Target Window Math) ──────────────
        logger.info("═══ Phase 0b: Programmatic Jitter Verification ═══")
        jitter_mgr.inject_jitter(edition=edition, skip_jitter=no_jitter, dry_run=dry_run)

        # ── Phase 0c: Mandatory 4-Hour Cooldown Guard ─────────────────────────
        if not dry_run:
            passed, cooldown_msg = jitter_mgr.check_cooldown(min_cooldown_hours=4.0)
            if not passed:
                logger.warning(cooldown_msg)
                return False
            logger.info("✓ %s", cooldown_msg)

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
        logger.info("🎯 Initial Debunk Angle: '%s' | Category: [%s]", news_analysis.get("headline_hook"), news_analysis.get("debunk_category"))

        # ── Phase 2b: Multi-Candidate Creative Darwinism & Critic Selection ──────
        logger.info("═══ Phase 2b: Multi-Candidate Creative Darwinism & Critic Selection ═══")
        critic_agent = CreativeCriticAgent()
        darwin_result = critic_agent.generate_and_evaluate(topic_data, evolutionary_directives=evolutionary_directives)
        topic_data["darwin_result"] = darwin_result
        winning_candidate = darwin_result.get("winning_candidate", {})
        critic_score = darwin_result.get("critic_score", 8.5)
        winning_archetype = darwin_result.get("archetype", "CONTRARIAN_TRAP")
        if winning_candidate.get("headline_hook"):
            news_analysis["headline_hook"] = winning_candidate["headline_hook"]
        if winning_candidate.get("highlight_word"):
            news_analysis["highlight_word"] = winning_candidate["highlight_word"]
        if darwin_result.get("final_editorial_directive"):
            news_analysis["editorial_directive"] = darwin_result["final_editorial_directive"]

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

        # ── Phase 5c: Multimodal Vision Quality Inspection ─────────────────────
        logger.info("═══ Phase 5c: Multimodal Vision Quality Inspection & Contrast Audit ═══")
        visual_inspector = VisualInspectorAgent()
        visual_audit = visual_inspector.audit_carousel_visuals(slide_paths)
        visual_score = visual_audit.get("average_score", 8.5)
        logger.info("👁️ Visual Inspection Verdict: %.1f/10 | Passed: %s", visual_score, visual_audit.get("passed", True))

        # ── Phase 6: Evolutionary Memory Mutation & Master Package Export ─────
        evolutionary_memory.record_cycle(
            winning_archetype=winning_archetype,
            critic_score=critic_score,
            visual_score=visual_score,
            topic_title=topic_data.get("title", ""),
            key_learning=darwin_result.get("selection_rationale", "")[:120] if darwin_result.get("selection_rationale") else None
        )

        analytics_engine.record_or_fetch_metrics()

        master_pkg_path = STATE_DIR / "market_debunk_carousel_master.json"
        master_package = {
            "topic": topic_data,
            "plan": plan,
            "deck": deck,
            "audio": audio_track,
            "run_id": run_id,
            "slide_count": len(slide_paths),
            "darwin_result": darwin_result,
            "visual_audit": visual_audit,
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        with open(master_pkg_path, "w", encoding="utf-8") as f:
            json.dump(master_package, f, indent=2, ensure_ascii=False)
        logger.info("✓ Exported Master Package to: %s", master_pkg_path)

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
            os.system("git add state/carousel_slides/ state/latest_carousel.pdf state/market_debunk_carousel_master.json state/evolutionary_playbook.json")
            os.system('git commit -m "chore: pre-push slides for live publishing [skip ci]" || true')
            for attempt in range(1, 4):
                os.system("git pull origin master --rebase -X ours || true")
                push_status = os.system("git push origin master")
                if push_status == 0:
                    logger.info("✓ Slides successfully pre-pushed to GitHub master (attempt %d).", attempt)
                    break
                logger.warning("⚠️ Pre-push attempt %d failed; retrying after rebase...", attempt)
                import time
                time.sleep(2)
            import time
            time.sleep(4)

        # ── Phase 8: Multi-Platform Publishing ────────────────────────────────
        logger.info("═══ Phase 8: Multi-Platform Distribution ═══")
        publisher = Publisher()
        results = publisher.publish_all(
            image_urls=image_urls,
            slide_paths=slide_paths,
            pdf_path=pdf_path,
            caption=deck.get("caption", ""),
            title=topic_data.get("title", "Market Debunk"),
            dry_run=dry_run
        )

        # Record upload in ledger for 48h analytics loop
        media_id = results.get("instagram", {}).get("container_id") or results.get("instagram", {}).get("media_id") or "simulated_id"
        jitter_mgr.record_successful_upload(
            title=topic_data.get("title", "Market Debunk"),
            media_id=media_id,
            publish_results=results,
            topic_category=news_analysis.get("debunk_category", "GENERAL"),
            hook_archetype=deck.get("hook_archetype_id", "CONTRARIAN"),
            caption_hashtag_cluster=deck.get("hashtag_cluster_id", "default")
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
    parser.add_argument("--no-jitter", action="store_true", help="Bypass programmatic anti-bot jitter delay")
    parser.add_argument("--edition", type=str, default="daily", choices=["morning", "evening", "daily"], help="Edition identifier (morning or evening)")
    parser.add_argument("--query", type=str, default=None, help="Override search query for market topic")
    args = parser.parse_args()

    success = run_pipeline(
        dry_run=args.dry_run,
        override_query=args.query,
        edition=args.edition,
        no_jitter=args.no_jitter
    )
    sys.exit(0 if success else 1)
