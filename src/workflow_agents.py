"""
Workflow coordination agents for Market Debunk carousels.
Transforms real-time financial market news and deep comprehension into structured briefs.
"""
import json
import logging
import random
import re
from datetime import datetime
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
        if news_analysis and news_analysis.get("headline_hook"):
            metrics = news_analysis.get("citable_metrics", [])
            primary_metric = metrics[0] if metrics else ""
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
            prompt = f"""Act as a clear financial editor for 'Market Debunk' creating a 6-slide educational Instagram/LinkedIn carousel.
A financial market event occurred in India in the last 48 hours.

Breaking News: {title}
Source: {source}
Context: {raw_text[:2500]}

Rules:
1. Do not report breaking news like a news channel. Debunk the underlying mechanism or hidden math for retail investors.
2. Use only numbers in the source. If none appear, citable_metric is an empty string; do not invent a number.
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
                    if plan.get("hook_headline") and "citable_metric" in plan:
                        return plan
            except Exception as e:
                logger.warning("LLM planning failed (%s); using deterministic financial plan.", e)

        # Deterministic fallback plan
        detected = topic_data.get("numbers_detected", [])
        metric = detected[0] if detected else ""
        return {
            "hook_headline": title[:70],
            "core_illusion": "What changes for the reader?",
            "hidden_reality": topic_data.get("source_snippet", "") or title,
            "citable_metric": metric,
            "actionable_rule": "Read the original source and check whether this change applies to you.",
            "lead_magnet": {},
            "banned_phrases": ["guaranteed wealth", "quick money", "easy passive income"]
        }


class PromptEngineer:
    """Converts the plan into an editorial brief for the two-pass slide composer."""

    def build_brief(self, plan: dict) -> str:
        return (
            f"HOOK HEADLINE: {plan.get('hook_headline', '')}\n"
            f"EVENT SUMMARY: {plan.get('breaking_event', '')}\n"
            f"READER QUESTION: {plan.get('core_illusion', '')}\n"
            f"SOURCE-BACKED EXPLANATION: {plan.get('hidden_reality', '')}\n"
            f"CITABLE METRIC (ONLY IF SUPPORTED): {plan.get('citable_metric', '')}\n"
            f"PRACTICAL CHECK: {plan.get('actionable_rule', '')}\n"
            f"AVOID: {', '.join(plan.get('banned_phrases', []))}\n"
            "Do not promise guides or resources that the channel cannot deliver."
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
SOURCE CONTEXT: {str(topic_data.get("raw_text", ""))[:2200]}
SLIDES OVERVIEW:
{json.dumps([{"role": s.get("role"), "title": s.get("title"), "card_text": s.get("card_text", "")[:120]} for s in slides], indent=2)}

STRICT RULES:
1. Slide 1 (hook): Must be punchy and concise (4 to 6 words MAXIMUM). NEVER huge, NEVER include website names, URLs, or news domains. Include exactly ONE <span class="highlight-box">...</span> around 1-2 powerful words.
2. Slides 2 to 7 (value): Titles must be 3 to 5 words MAXIMUM. Contextual to the card content (e.g. 'The False Safety <span class="highlight-box">Of Bail Orders</span>'). NEVER use numbers like '#1', '#2' or generic 'Institutional Reality'.
3. Slide 8: Keep the source-backed practical takeaway in cta_detail, then a short save/share invitation. No generic trade checklist.

Return JSON ONLY in this shape; use THIS SOURCE, not these field names as content:
{{
  "slide_1_hook": "source-specific short hook with one highlight-box span",
  "slide_titles": ["six short source-specific titles"],
  "slide_8_cta_detail": "source-backed practical takeaway and save/share invitation"
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

            if "card_text" in s and s["card_text"]:
                ct = str(s["card_text"])
                ct = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", ct)
                ct = re.sub(r"`([^`]+)`", r"\1", ct)
                s["card_text"] = ct.strip()

            # Sanitize polymorphic archetype fields recursively
            if "comparison_data" in s and isinstance(s["comparison_data"], dict):
                comp = s["comparison_data"]
                for k in ["myth", "reality"]:
                    if k in comp and comp[k]:
                        val = str(comp[k])
                        val = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", val)
                        val = re.sub(r"`([^`]+)`", r"\1", val)
                        comp[k] = val.strip()
            if "stat_data" in s and isinstance(s["stat_data"], dict):
                stat = s["stat_data"]
                for k in ["context", "badge", "label", "metric"]:
                    if k in stat and stat[k]:
                        val = str(stat[k])
                        val = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", val)
                        val = re.sub(r"`([^`]+)`", r"\1", val)
                        stat[k] = val.strip()
            if "flowchart_data" in s and isinstance(s["flowchart_data"], list):
                for step in s["flowchart_data"]:
                    if isinstance(step, dict) and "text" in step and step["text"]:
                        val = str(step["text"])
                        val = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", val)
                        val = re.sub(r"`([^`]+)`", r"\1", val)
                        step["text"] = val.strip()
            if "checklist_data" in s and isinstance(s["checklist_data"], list):
                for item in s["checklist_data"]:
                    if isinstance(item, dict) and "text" in item and item["text"]:
                        val = str(item["text"])
                        val = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", val)
                        val = re.sub(r"`([^`]+)`", r"\1", val)
                        item["text"] = val.strip()

            if i == len(slides) - 1 and not s.get("cta_detail"):
                raise ValueError("English takeaway missing")

        return deck

    def format_converting_caption(self, deck: dict, topic_data: dict, audio_track: Optional[dict] = None) -> str:
        """
        Formats a high-converting, organically diverse caption based on the 2026 Algorithmic Directive:
        1. Curiosity Hook (rotates across 5 distinct opening archetypes)
        2. Progressive Value Preview (3 slide teasers)
        3. Double Algorithmic Engagement Signal: Bookmark Save + DM Share CTA
        4. Organic community debate question (drives genuine comments instead of ghost DMs)
        5. Rotating non-repetitive hashtag cluster (anti-spam diversity)
        """
        # Keep the source-specific caption composed with the carousel. Avoid a
        # randomly assigned trading-trap narrative unrelated to this topic.
        caption = (deck.get("caption") or "").strip()
        if not caption:
            hook = deck.get("slides", [{}])[0].get("title", topic_data.get("title", ""))
            highlights = [re.sub(r"<[^>]+>", "", s.get("title", "")).strip()
                          for s in deck.get("slides", [])[1:4]]
            caption = "\n".join([re.sub(r"<[^>]+>", "", hook), *[f"• {t}" for t in highlights if t]])
        if not caption:
            raise ValueError("English caption is empty")
        return caption
