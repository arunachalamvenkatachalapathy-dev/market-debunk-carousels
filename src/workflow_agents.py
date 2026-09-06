"""
Workflow coordination agents for Market Debunk carousels.
Transforms real-time financial market news and deep comprehension into structured briefs.
"""
import json
import logging
import re
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Builds a structured financial debunk plan for a 6-slide carousel."""

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def plan(self, topic_data: dict) -> dict:
        # Check if deep news analysis was already performed
        news_analysis = topic_data.get("news_analysis")
        if news_analysis and news_analysis.get("headline_hook") and news_analysis.get("citable_metrics"):
            metrics = news_analysis.get("citable_metrics", [])
            primary_metric = metrics[0] if metrics else "5%"
            return {
                "hook_headline": news_analysis.get("headline_hook"),
                "core_illusion": news_analysis.get("retail_illusion"),
                "hidden_reality": news_analysis.get("institutional_reality"),
                "citable_metric": primary_metric,
                "all_metrics": metrics,
                "actionable_rule": news_analysis.get("actionable_retail_rule"),
                "breaking_event": news_analysis.get("breaking_event_summary"),
                "lead_magnet": news_analysis.get("lead_magnet", {
                    "trigger_word": "GUIDE",
                    "resource_name": "The Retail Risk Checklist"
                }),
                "banned_phrases": ["guaranteed wealth", "quick money", "easy passive income", "get rich quick"]
            }

        title = topic_data.get("title", "")
        source = topic_data.get("source", "")
        raw_text = topic_data.get("raw_text", "")

        if self.llm:
            prompt = f"""Act as a senior quantitative financial editor for 'Market Debunk' creating a 6-slide educational Instagram/LinkedIn carousel.
A financial market event occurred in India in the last 48 hours.

Breaking News: {title}
Source: {source}
Context: {raw_text[:2500]}

Rules:
1. Do not report breaking news like a news channel. Debunk the underlying mechanism or hidden math for retail investors.
2. Provide at least one concrete citable number (e.g., fee %, ₹ amount lost, percentage of traders losing).
3. The carousel must deliver actionable risk management advice.

Return JSON ONLY:
{{
  "hook_headline": "Punchy contrarian 1-line hook headline (max 10 words)",
  "core_illusion": "What retail investors falsely believe",
  "hidden_reality": "The institutional math / hidden deductions",
  "citable_metric": "Exact key number or percentage present in the context",
  "actionable_rule": "The golden rule for retail investors",
  "lead_magnet": {{
    "trigger_word": "GUIDE or RULE or CHECK",
    "resource_name": "A specific, ownable deliverable name (e.g. 'The Retail Trap Checklist')"
  }},
  "banned_phrases": ["game changer", "skyrocket", "guaranteed returns", "passive income secret"]
}}"""
            try:
                response = self.llm.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                if response.text:
                    plan = json.loads(response.text)
                    if plan.get("hook_headline") and plan.get("citable_metric"):
                        return plan
            except Exception as e:
                logger.warning("LLM planning failed (%s); using deterministic financial plan.", e)

        # Deterministic fallback plan
        detected = topic_data.get("numbers_detected", ["₹34 Lakhs"])
        metric = detected[0] if detected else "₹34 Lakhs"
        return {
            "hook_headline": f"The Real Risk Behind {title[:40]}",
            "core_illusion": "Retail investors assume headline market moves represent easy momentum.",
            "hidden_reality": "Institutional order flows leverage volatility to offload risk to retail.",
            "citable_metric": metric,
            "actionable_rule": "Audit volume distribution, delivery percentages, and underlying leverage before entering.",
            "lead_magnet": {
                "trigger_word": "GUIDE",
                "resource_name": "The Retail Risk Checklist"
            },
            "banned_phrases": ["guaranteed wealth", "quick money", "easy passive income"]
        }


class PromptEngineer:
    """Converts the plan into an editorial brief for the two-pass slide composer."""

    def build_brief(self, plan: dict) -> str:
        lead_magnet = plan.get("lead_magnet", {})
        trigger = lead_magnet.get("trigger_word", "GUIDE")
        resource = lead_magnet.get("resource_name", "The Retail Risk Checklist")

        return (
            f"HOOK HEADLINE: {plan.get('hook_headline', '')}\n"
            f"BREAKING EVENT SUMMARY: {plan.get('breaking_event', '')}\n"
            f"CORE ILLUSION (THE TRAP): {plan.get('core_illusion', '')}\n"
            f"HIDDEN REALITY (INSTITUTIONAL TRUTH): {plan.get('hidden_reality', '')}\n"
            f"MANDATORY CITABLE METRIC: {plan.get('citable_metric', '')}\n"
            f"ACTIONABLE RULE: {plan.get('actionable_rule', '')}\n"
            f"LEAD MAGNET TRIGGER: Comment '{trigger}' for '{resource}'\n"
            f"AVOID: {', '.join(plan.get('banned_phrases', []))}"
        )


class GrammarAgent:
    """
    Grammar & Stylistic Verification Agent:
    1. Cross-checks spelling, grammar, punctuation, and sentence flow across all slides.
    2. Strips any leaked markdown artifacts (e.g. raw '**', '#', leading numbers inside text).
    3. Intelligently selects punchy words/phrases to wrap with '<span class="highlight-box">...</span>' (#010a20 background + white text).
    4. Ensures vertical density and clarity without forcing or rushing content.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def sanitize_text(self, text: str) -> str:
        """Removes markdown syntax, website URLs/domains, leaked publish dates, and messy quotes."""
        if not text:
            return ""
        t = str(text)
        # Remove website domains like indianexpress.com, moneycontrol.com, etc.
        t = re.sub(r"\s*[-|–—]\s*(?:indianexpress\.com|moneycontrol|economic times|ndtv profit|reuters|bloomberg|livemint|[a-zA-Z0-9.-]+\.(?:com|in|org|net)).*$", "", t, flags=re.I)
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"\b[a-zA-Z0-9.-]+\.(?:com|in|org|net)\b", "", t, flags=re.I)
        t = re.sub(r"Published:\s*\d{4}-\d{2}-\d{2}\s*[-—:]*\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"^[‘'\"“]+|[’'\"”]+$", "", t)
        t = re.sub(r"^[‘'\"“][^:’'\"]+[:’'\"]\s*", "", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"\*([^*]+)\*", r"\1", t)
        t = re.sub(r"`([^`]+)`", r"\1", t)
        t = re.sub(r":([^\s])", r": \1", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def clean_text(self, text: str) -> str:
        return self.sanitize_text(text)

    def review_and_polish_deck(self, deck: dict, topic_data: Optional[dict] = None) -> dict:
        """
        AI-Powered Grammar & Sentence Formation Gate:
        1. Formulates a concise 4-6 word hook (NOT huge, zero websites).
        2. Ensures Slides 2-7 have contextual 3-5 word titles (NO '#1' on a separate line).
        3. Fills Slide 8 with complete takeaway text so it never feels limited or empty.
        """
        topic_data = topic_data or {}
        topic_title = self.sanitize_text(topic_data.get("title", ""))
        slides = deck.get("slides", [])

        # Attempt LLM-assisted sentence refinement for maximum punchiness
        if self.llm and slides:
            try:
                prompt = f"""You are the Lead Editorial Grammar & Sentence Formation Agent for 'Market Debunk'.
Refine the headlines and titles for this 8-slide Instagram carousel to ensure premium editorial flow.

TOPIC: {topic_title}
SLIDES OVERVIEW:
{json.dumps([{"role": s.get("role"), "title": s.get("title"), "card_text": s.get("card_text", "")[:120]} for s in slides], indent=2)}

STRICT RULES:
1. Slide 1 (hook): Must be punchy and concise (4 to 6 words MAXIMUM). NEVER huge, NEVER include website names, URLs, or news domains. Include exactly ONE <span class="highlight-box">...</span> around 1-2 powerful words.
2. Slides 2 to 7 (value): Titles must be 3 to 5 words MAXIMUM. Contextual to the card content (e.g. 'The False Safety <span class="highlight-box">Of Bail Orders</span>'). NEVER use numbers like '#1', '#2' or generic 'Institutional Reality'.
3. Slide 8 (save CTA): Provide 'cta_detail' (20-30 words) explaining WHY investors must save this framework for their next trade review (fills space with valuable advice).

Return JSON ONLY:
{{
  "slide_1_hook": "Why Bail Orders <span class='highlight-box'>Trap Retail</span> Traders",
  "slide_titles": [
    "The Core Illusion <span class='highlight-box'>Exposed By Math</span>",
    "How Syndicates <span class='highlight-box'>Dump Liquidity</span>",
    "The Legal Delay <span class='highlight-box'>Capital Trap</span>",
    "The Compounding <span class='highlight-box'>Opportunity Loss</span>",
    "The Golden Rule: <span class='highlight-box'>Exit Instantly</span>",
    "The 3-Point <span class='highlight-box'>Pre-Trade Audit</span>"
  ],
  "slide_8_cta_detail": "Save this framework to your private collection. Review these institutional risk checkpoints before taking your next trade to protect your capital from operator traps."
}}"""
                resp = self.llm.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={"response_mime_type": "application/json", "temperature": 0.2}
                )
                if resp.text:
                    refined = json.loads(resp.text)
                    if refined.get("slide_1_hook"):
                        slides[0]["title"] = refined["slide_1_hook"]
                    titles = refined.get("slide_titles", [])
                    for i, t in enumerate(titles):
                        if i + 1 < len(slides) - 1:
                            slides[i + 1]["title"] = t
                    if refined.get("slide_8_cta_detail") and len(slides) >= 8:
                        slides[-1]["cta_detail"] = refined["slide_8_cta_detail"]
            except Exception as e:
                logger.warning("LLM sentence formation fallback to deterministic: %s", e)

        # Deterministic cleanup across all slides
        for i, s in enumerate(slides):
            raw_title = s.get("title", "")
            cleaned = self.sanitize_text(raw_title)
            # Remove isolated numbers like #1, #2 from title
            cleaned = re.sub(r"\s*#\d+\b", "", cleaned).strip()
            if cleaned:
                s["title"] = cleaned

            if "card_text" in s:
                ct = str(s["card_text"])
                ct = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", ct)
                ct = re.sub(r"`([^`]+)`", r"\1", ct)
                s["card_text"] = ct.strip()

            if i == len(slides) - 1 and not s.get("cta_detail"):
                s["cta_detail"] = "Save this framework to your private collection. Review these institutional risk checkpoints before entering your next trade to protect your capital."

        return deck

    def format_converting_caption(self, deck: dict, topic_data: dict, audio_track: Optional[dict] = None) -> str:
        """
        Formats a high-converting caption based on the 2026 Instagram Carousel Bible:
        1. Opening Hook (1-2 sentences creating curiosity gap)
        2. Value Preview (3 bullet points teasing what is inside)
        3. Clear single CTA with keyword trigger
        4. Reels Algorithm Audio recommendation
        5. 3-5 relevant hashtags
        """
        title = topic_data.get("title", "")
        slides = deck.get("slides", [])
        hook_text = slides[0].get("title", title) if slides else title
        clean_hook = re.sub(r"<[^>]+>", "", hook_text).strip()

        trigger = "DEBUNK"
        for s in slides:
            lm = s.get("lead_magnet")
            if lm and lm.get("trigger_word"):
                trigger = lm.get("trigger_word")
                break

        audio_str = ""
        if audio_track:
            audio_str = f"\n\n🎵 Recommended Audio: '{audio_track.get('title')}' by {audio_track.get('artist')} (Tap 'Add Music' before posting for Reels algorithm boost)"

        caption = (
            f"🚨 {clean_hook}\n\n"
            f"Most retail traders get caught on the wrong side of headline surges because they don't audit institutional positioning.\n\n"
            f"Swipe through this 8-slide breakdown to see:\n"
            f"• The structural traps behind the headline move\n"
            f"• How smart capital extracts exit liquidity\n"
            f"• The complete pre-trade risk audit checklist\n\n"
            f"💬 Comment '{trigger}' and our system will DM you the complete pre-trade Risk Playbook in 10 seconds.{audio_str}\n\n"
            f"#Commodities #StockMarket #TradingTruth #MarketDebunk #InstitutionalMath"
        )
        return caption
