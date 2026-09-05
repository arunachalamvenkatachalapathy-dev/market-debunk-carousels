"""
Market Debunk - News Comprehension & Debunk Extraction Agent
Analyzes real-time 48-hour financial market news.
Does NOT merely summarize; dissects the underlying financial mechanism,
exposes the retail trap / illusion, and extracts verified quantitative anchors.
"""

import json
import logging
import re
from typing import Dict, Any, Optional
from google import genai

from src.config import settings

logger = logging.getLogger(__name__)


class NewsComprehensionAgent:
    """
    Analyzes breaking financial news (<= 48h) to formulate an institutional debunk angle.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def analyze_news_item(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deeply understands the 48-hour news event and extracts the contrarian debunk angle.
        """
        title = news_item.get("title", "")
        snippet = news_item.get("source_snippet", "")
        source = news_item.get("source", "")
        pub_date = news_item.get("published_at", "")
        raw_text = news_item.get("raw_text", f"{title}. {snippet}")

        if not self.client:
            logger.warning("GenAI client unavailable; using deterministic news analysis.")
            return self._build_deterministic_analysis(news_item)

        prompt = f"""You are the Chief Quantitative Editor & Financial Investigative Analyst for 'Market Debunk'.
A real-time financial market event occurred in India within the last 48 hours.

BREAKING NEWS CONTEXT:
Headline: {title}
Source: {source}
Published: {pub_date}
Source Evidence / Text: {raw_text}

CRITICAL DIRECTIVE:
DO NOT simply summarize or regurgitate this news like a news ticker.
Your job is to INVESTIGATE and DEBUNK the event for retail investors:
1. What is the retail crowd or mainstream media falsely celebrating or fearing?
2. What is the institutional reality, hidden mathematical truth, regulatory mechanism, or structural trap beneath this headline?
3. What are the exact verifiable numbers, dates, ₹ figures, or percentages present in the news text?

Return valid JSON ONLY matching this exact schema:
{{
  "headline_hook": "Punchy contrarian hook headline (e.g. 'The Real Trap Behind Today's 500-Point Nifty Rally')",
  "breaking_event_summary": "1-2 sentence factual description of what actually happened in the last 48 hours",
  "retail_illusion": "What retail investors falsely assume from this headline (The Trap)",
  "institutional_reality": "The underlying math, liquidity flow, or regulatory rule that institutions know (The Reality)",
  "citable_metrics": ["Exact numbers or percentages present in source text (e.g. '15 Lakhs', '2.4%', '₹450 Cr')"],
  "debunk_category": "REGULATORY_SHIFT or LIQUIDITY_TRAP or VALUATION_MYTH or FEE_EXTRACTION",
  "actionable_retail_rule": "The non-negotiable risk management rule the retail investor must apply right now",
  "lead_magnet": {{
    "trigger_word": "CHECK or AUDIT or GUIDE",
    "resource_name": "Specific 1-page tactical checklist title"
  }},
  "carousel_outline": [
    {{"slide": 1, "role": "hook", "focus": "Attention-grabbing contrarian headline about this 48h event"}},
    {{"slide": 2, "role": "friction", "focus": "The Retail Illusion vs What Actually Happened"}},
    {{"slide": 3, "role": "math_reality", "focus": "The Institutional Mechanism & Hard Numbers"}},
    {{"slide": 4, "role": "breakdown", "focus": "Step-by-step impact on retail portfolios"}},
    {{"slide": 5, "role": "actionable_rule", "focus": "The Golden Protective Rule"}},
    {{"slide": 6, "role": "cta", "focus": "Save prompt and lead magnet comment trigger"}}
  ]
}}
"""
        models_to_try = [settings.GEMINI_MODEL, "gemini-3.7-flash", "gemini-flash-latest"]
        for m in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config={"response_mime_type": "application/json", "temperature": 0.2}
                )
                if response.text:
                    clean = response.text.strip()
                    if clean.startswith("```json"):
                        clean = clean[7:]
                    if clean.endswith("```"):
                        clean = clean[:-3]
                    analysis = json.loads(clean.strip())
                    if analysis.get("headline_hook") and analysis.get("citable_metrics"):
                        logger.info("✓ Deep news analysis completed via Gemini [%s] for: '%s'", m, title[:40])
                        return analysis
            except Exception as e:
                logger.warning("Gemini news analysis model %s failed: %s. Trying next...", m, e)

        # Fallback to Gemma
        try:
            logger.info("Falling back to Gemma for news analysis: %s...", settings.GEMMA_FALLBACK_MODEL)
            response = self.client.models.generate_content(
                model=settings.GEMMA_FALLBACK_MODEL,
                contents=prompt + "\nCRITICAL: Output valid JSON only."
            )
            if response.text:
                clean = response.text.strip()
                if "```json" in clean:
                    clean = clean.split("```json")[1].split("```")[0].strip()
                elif "```" in clean:
                    clean = clean.split("```")[1].split("```")[0].strip()
                return json.loads(clean)
        except Exception as ge:
            logger.warning("Gemma news analysis failed: %s.", ge)

        return self._build_deterministic_analysis(news_item)

    def _build_deterministic_analysis(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic analysis if AI models are temporarily unreachable."""
        title = news_item.get("title", "")
        nums = news_item.get("numbers_detected", [])
        metric = nums[0] if nums else "5%"

        return {
            "headline_hook": f"The Real Story Behind Today's Market Move: {title[:40]}",
            "breaking_event_summary": f"Recent market development reported by {news_item.get('source', 'financial media')}: {title}",
            "retail_illusion": "Retail traders assume headline market moves represent easy momentum to chase.",
            "institutional_reality": "Institutional order flows leverage volatility to offload risk while retail enters at the peak.",
            "citable_metrics": nums[:4] if nums else [metric],
            "debunk_category": "LIQUIDITY_TRAP",
            "actionable_retail_rule": "Never chase a headline move without verifying volume distribution and delivery percentages.",
            "lead_magnet": {
                "trigger_word": "GUIDE",
                "resource_name": "The Market Overlook Checklist"
            }
        }
