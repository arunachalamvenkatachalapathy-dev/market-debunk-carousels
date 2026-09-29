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
Explain why this verified event matters to an Indian retail reader's own money choice.
Separate what the source says from an inference. A fee change, loan rule or market
news need not be framed as a trap. Identify who is affected, what they can check,
and what the source leaves unknown. Use plain language. Quote only exact metrics
from the evidence. If no number is in the source, return an empty citable_metrics
list, not a guessed number. Do not invent investor losses, institutions' motives,
scams, guaranteed returns, or universal trading instructions.

Return valid JSON ONLY matching this exact schema:
{{
  "headline_hook": "Short source-grounded hook about a real money decision or consequence",
  "breaking_event_summary": "1-2 sentence factual description of what actually happened in the last 48 hours",
  "retail_illusion": "A common misunderstanding only if evidenced; otherwise the reader question",
  "institutional_reality": "The source-supported mechanism or relevant caveat",
  "citable_metrics": ["Exact numbers from source text only; empty list if none"],
  "debunk_category": "REGULATORY_SHIFT or LIQUIDITY_TRAP or VALUATION_MYTH or FEE_EXTRACTION",
  "actionable_retail_rule": "A source-supported practical check, not personal financial advice",
  "lead_magnet": {{}},
  "carousel_outline": []
}}
"""
        models_to_try = [settings.GEMINI_MODEL, "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]
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
                    if analysis.get("headline_hook") and "citable_metrics" in analysis:
                        logger.info("✓ Deep news analysis completed via Gemini [%s] for: '%s'", m, title[:40])
                        return analysis
            except Exception as e:
                logger.warning("Gemini news analysis model %s failed: %s. Trying next...", m, e)

        # Fallback to deterministic if models unavailable
        try:
            fallback_model = getattr(settings, "GEMMA_FALLBACK_MODEL", "gemini-3.6-flash")
            logger.info("Attempting fallback model for news analysis: %s...", fallback_model)
            response = self.client.models.generate_content(
                model=fallback_model,
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
            logger.warning("Fallback news analysis note: %s. Using deterministic analysis.", ge)

        return self._build_deterministic_analysis(news_item)

    def _build_deterministic_analysis(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic analysis if AI models are temporarily unreachable."""
        title = news_item.get("title", "")
        nums = news_item.get("numbers_detected", [])
        return {
            "headline_hook": title,
            "breaking_event_summary": f"{news_item.get('source', 'Financial press')} reports: {title}",
            "retail_illusion": "What changes for a reader's money decision?",
            "institutional_reality": news_item.get("source_snippet", "") or title,
            "citable_metrics": nums[:4],
            "debunk_category": "GENERAL",
            "actionable_retail_rule": "Read the full source and check whether this change applies to your situation.",
            "lead_magnet": {},
        }

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
