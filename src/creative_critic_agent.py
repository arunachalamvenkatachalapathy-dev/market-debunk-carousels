"""
Market Debunk - Creative Darwinism & Critic Agent
Generates 3 diverse creative hypotheses per topic, evaluates them across
viral retention criteria, and autonomously selects the winning narrative.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types

from src.config import settings

logger = logging.getLogger("CreativeCriticAgent")


class CreativeCriticAgent:
    """Generates 3 competing angles and selects the highest-retention candidate."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.models = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]

    def _call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        for m in self.models:
            try:
                cfg = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
                if "3.7" in m:
                    cfg.thinking_config = types.ThinkingConfig(thinking_budget=512)
                res = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=cfg
                )
                if res.text:
                    clean = res.text.strip()
                    if clean.startswith("```json"):
                        clean = clean[7:]
                    if clean.endswith("```"):
                        clean = clean[:-3]
                    return json.loads(clean.strip())
            except Exception as e:
                logger.warning("CreativeCriticAgent (%s) attempt failed: %s", m, e)
                continue
        return None

    def generate_and_evaluate(self, topic_data: Dict[str, Any], evolutionary_directives: str = "") -> Dict[str, Any]:
        """Generates 3 competing angles, scores them, and returns the selected winner."""
        title = topic_data.get("title", "")
        summary = topic_data.get("summary", "") or topic_data.get("context", "")

        prompt = f"""You are an elite Viral Social Media Strategist and Quantitative Content Critic.
Topic: "{title}"
Context: {summary[:1200]}

{evolutionary_directives}

TASK:
1. Generate THREE distinctly different creative carousel angles:
   - Candidate A (Archetype: CONTRARIAN_TRAP): Debunk mainstream optimism/panic.
   - Candidate B (Archetype: MATHEMATICAL_FRICTION): Focus on hard numbers, hidden fee decay, or margin risk.
   - Candidate C (Archetype: INSTITUTIONAL_DISPARITY): Expose institutional positioning vs. retail traps.

2. Act as a harsh editorial critic. Evaluate each candidate on a 0-10 scale:
   - curiosity_gap (0-10): Will a user immediately swipe slide 1?
   - retail_actionability (0-10): Does it deliver concrete pre-trade defense?
   - data_density (0-10): Does it cite specific numbers, percentages, or mechanisms?
   - friction_quotient (0-10): Does it challenge comfortable assumptions?

3. Calculate total_score (sum of 4 criteria, max 40) and pick the definitive winning candidate.

Return JSON strictly matching this schema:
{{
  "candidates": [
    {{
      "id": "A",
      "archetype": "CONTRARIAN_TRAP",
      "headline_hook": "...",
      "highlight_word": "1-2 words to put inside <span class='highlight-box'>",
      "core_mechanism": "...",
      "scores": {{"curiosity_gap": 9.0, "retail_actionability": 8.5, "data_density": 8.0, "friction_quotient": 9.0, "total": 34.5}},
      "critic_critique": "..."
    }},
    {{
      "id": "B",
      "archetype": "MATHEMATICAL_FRICTION",
      "headline_hook": "...",
      "highlight_word": "...",
      "core_mechanism": "...",
      "scores": {{"curiosity_gap": 8.5, "retail_actionability": 9.0, "data_density": 9.5, "friction_quotient": 8.5, "total": 35.5}},
      "critic_critique": "..."
    }},
    {{
      "id": "C",
      "archetype": "INSTITUTIONAL_DISPARITY",
      "headline_hook": "...",
      "highlight_word": "...",
      "core_mechanism": "...",
      "scores": {{"curiosity_gap": 9.0, "retail_actionability": 8.0, "data_density": 8.5, "friction_quotient": 9.0, "total": 34.5}},
      "critic_critique": "..."
    }}
  ],
  "winning_candidate_id": "B",
  "selection_rationale": "...",
  "final_editorial_directive": "Actionable instructions for slide copywriters."
}}"""

        result = self._call_llm(prompt)
        if not result or not result.get("candidates"):
            logger.warning("Critic LLM generation failed; using deterministic fallback angle.")
            return {
                "winning_candidate": {
                    "id": "A",
                    "archetype": "CONTRARIAN_TRAP",
                    "headline_hook": f"The Hidden Risk Behind {title[:50]}",
                    "highlight_word": "Hidden Risk",
                    "core_mechanism": "Institutional order flow disparity",
                    "scores": {"total": 34.0}
                },
                "critic_score": 8.5,
                "archetype": "CONTRARIAN_TRAP",
                "selection_rationale": "Fallback contrarian anchor."
            }

        candidates = result.get("candidates", [])
        winner_id = result.get("winning_candidate_id", "A")
        winner = next((c for c in candidates if c.get("id") == winner_id), candidates[0])
        total_score = winner.get("scores", {}).get("total", 34.0)
        normalized_score = round(total_score / 4.0, 1)

        logger.info(
            "🏆 Creative Darwinism: Selected Candidate %s (%s) with score %.1f/10. Rationale: %s",
            winner.get("id"), winner.get("archetype"), normalized_score, result.get("selection_rationale", "")[:80]
        )

        return {
            "winning_candidate": winner,
            "critic_score": normalized_score,
            "archetype": winner.get("archetype", "CONTRARIAN_TRAP"),
            "selection_rationale": result.get("selection_rationale", ""),
            "final_editorial_directive": result.get("final_editorial_directive", ""),
            "all_candidates": candidates
        }