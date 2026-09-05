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
