"""
Workflow coordination agents for Market Debunk carousels.
"""
import json
import logging
import re
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Builds a structured financial brief for a 6-slide carousel."""

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def plan(self, topic_data: dict) -> dict:
        title = topic_data.get("title", "")
        source = topic_data.get("source", "")
        raw_text = topic_data.get("raw_text", "")
        archetype = topic_data.get("archetype", "myth_vs_reality_math")

        if self.llm:
            prompt = f"""Act as a senior quantitative financial editor for 'Market Debunk' creating a 6-slide educational Instagram/LinkedIn carousel.
Topic: {title}
Source: {source}
Context: {raw_text}
Archetype: {archetype}

Rules:
1. Do not report breaking news like a news channel. Debunk the underlying mechanism or hidden math for retail investors.
2. Provide at least one concrete citable number (e.g., fee %, ₹ amount lost, percentage of traders losing).
3. The carousel must deliver actionable risk management advice.

Return JSON ONLY:
{{
  "hook_headline": "Punchy contrarian 1-line hook headline (max 10 words)",
  "core_illusion": "What retail investors falsely believe",
  "hidden_reality": "The institutional math / hidden deductions",
  "citable_metric": "Exact key number or percentage (e.g. ₹34 Lakhs, 93%, 1.2%)",
  "actionable_rule": "The golden rule for retail investors",
  "lead_magnet": {{
    "trigger_word": "GUIDE or RULE or CHECK",
    "resource_name": "A specific, ownable deliverable name (e.g. 'The Retail Trap Checklist', 'The Mutual Fund Audit Guide')"
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
            "hook_headline": f"The Hidden Math Behind {title[:40]}",
            "core_illusion": "Retail investors assume small percentage fees are negligible over time.",
            "hidden_reality": "Compound deduction mathematically extracts up to 30% of total lifetime gains.",
            "citable_metric": metric,
            "actionable_rule": "Audit all ongoing expense ratios, platform charges, and spread costs before investing.",
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
            f"CORE ILLUSION: {plan.get('core_illusion', '')}\n"
            f"HIDDEN REALITY: {plan.get('hidden_reality', '')}\n"
            f"MANDATORY CITABLE METRIC: {plan.get('citable_metric', '')}\n"
            f"ACTIONABLE RULE: {plan.get('actionable_rule', '')}\n"
            f"LEAD MAGNET TRIGGER: Comment '{trigger}' for '{resource}'\n"
            f"AVOID: {', '.join(plan.get('banned_phrases', []))}"
        )
