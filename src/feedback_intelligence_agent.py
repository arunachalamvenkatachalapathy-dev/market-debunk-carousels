"""
Feedback Intelligence & Algorithmic Finetuning Agent
Pulls 48-hour analytics performance metrics (saves, reach, impressions, shares)
and synthesizes actionable finetuning directives for downstream generation agents.
Directly enhances the next Carousel and next Video in an automated feedback loop.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import STATE_DIR

logger = logging.getLogger("FeedbackIntelligenceAgent")


class FeedbackIntelligenceAgent:
    """
    Dedicated agent to close the feedback loop between platform analytics and content generation:
    1. Audits 48-hour Meta Graph analytics from the performance ledger.
    2. Identifies high-performing patterns (Save-to-Reach >= 3.5%) vs low-performing patterns (< 1.5%).
    3. Synthesizes prescriptive directives for the next Video and next Carousel.
    4. Writes state/loop_finetuning_directive.json to guide generation agents.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.state_dir / "analytics_performance_ledger.json"
        self.history_file = self.state_dir / "upload_history.json"
        self.directive_file = self.state_dir / "loop_finetuning_directive.json"

    def audit_and_synthesize(self) -> Dict[str, Any]:
        """
        Processes ledger data to produce an actionable finetuning directive for
        both video and carousel engines.
        """
        ledger_entries = self._load_ledger()
        upload_records = self._load_upload_history()

        # Aggregate metrics across categories and hook archetypes
        cat_performance = {}
        hook_performance = {}
        all_save_rates = []

        for entry in ledger_entries:
            cat = entry.get("topic_category", "GENERAL")
            hook = entry.get("hook_archetype", "CONTRARIAN")
            sr = float(entry.get("save_to_reach_pct", 0.0))
            all_save_rates.append(sr)

            cat_performance.setdefault(cat, []).append(sr)
            hook_performance.setdefault(hook, []).append(sr)

        avg_save_rate = (sum(all_save_rates) / len(all_save_rates)) if all_save_rates else 2.5

        # Classify high-performing vs low-performing
        high_save_hooks = []
        deprecated_hooks = []
        for hook, rates in hook_performance.items():
            avg = sum(rates) / len(rates)
            if avg >= 3.5:
                high_save_hooks.append({"hook": hook, "avg_save_rate": f"{avg:.2f}%", "count": len(rates)})
            elif avg < 1.5 and len(rates) >= 2:
                deprecated_hooks.append({"hook": hook, "avg_save_rate": f"{avg:.2f}%", "reason": "Low dwell & bookmark retention"})

        high_save_cats = [cat for cat, rates in cat_performance.items() if (sum(rates) / len(rates)) >= 3.0]
        low_save_cats = [cat for cat, rates in cat_performance.items() if (sum(rates) / len(rates)) < 1.5 and len(rates) >= 2]

        # Formulate prescriptive directives for next Video and next Carousel
        directive = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_points_analyzed": len(ledger_entries),
            "historical_avg_save_rate_pct": round(avg_save_rate, 2),
            "prioritized_categories": high_save_cats or ["SMART_MONEY", "MARKET_TRAPS", "VALUATION"],
            "deprecated_categories": low_save_cats,
            "high_performing_hooks": high_save_hooks,
            "deprecated_hooks": deprecated_hooks,
            "video_finetuning_directive": {
                "opening_3s_hook": (
                    "Mandatory contrarian contrast with numerical anchor. Avoid greeting or headline recitation. "
                    "Open immediately with the hidden institutional liquidity mechanism (e.g. 'What the TV anchors didn't tell you about today's breakout')."
                ),
                "pacing_calibration": (
                    "Introduce hard mathematical friction between seconds 4 and 10 (e.g. 'A 1% fee difference erodes ₹34 Lakhs'). "
                    "This forces algorithmic dwell and repeat watches."
                ),
                "visual_friction": "Use split amber-teal photoreal lighting with blurred terminal/order-book background; zero static text inside image.",
                "retention_cta": "End with an explicit bookmark save trigger: 'Bookmark this risk checkpoint before taking your next trade.'"
            },
            "carousel_finetuning_directive": {
                "slide_1_hook_bias": "Contrarian curiosity gap with exactly one <span class='highlight-box'>...</span> tag around 1-2 friction words.",
                "slide_2_3_mechanism": "Lead with the exact citable mathematical formula or institutional orderflow disparity on Slide 2.",
                "slide_8_dual_cta": "Explicitly split personal bookmarking (Save) from peer distribution (DM Share)."
            },
            "prompt_injection_snippet": (
                f"ALGORITHMIC REINFORCEMENT DIRECTIVE: Historical performance shows audiences respond to institutional order flow "
                f"and hidden fee debunks with an average save rate of {avg_save_rate:.1f}%. "
                f"Prioritize topics covering {', '.join(high_save_cats or ['Smart Money', 'Market Traps'])}. "
                f"Ensure the opening 3 seconds / Slide 1 deliver immediate contrarian friction rather than standard market reporting."
            )
        }

        self._save_directive(directive)
        logger.info(
            "✓ FeedbackIntelligenceAgent: Synthesized loop finetuning directive (Analyzed %d posts | Avg Save: %.2f%%).",
            len(ledger_entries), avg_save_rate
        )
        return directive

    def get_prompt_injection(self) -> str:
        """Returns the dynamic prompt injection snippet for downstream LLM agents."""
        if self.directive_file.exists():
            try:
                with open(self.directive_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("prompt_injection_snippet", "")
            except Exception:
                pass
        return (
            "ALGORITHMIC REINFORCEMENT: Frame every insight around institutional liquidity mechanics "
            "vs retail investor traps to optimize algorithmic dwell and bookmark save rates."
        )

    def _load_ledger(self) -> List[Dict[str, Any]]:
        if self.ledger_file.exists():
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read analytics ledger: %s", e)
        return []

    def _load_upload_history(self) -> List[Dict[str, Any]]:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("uploads", []) if isinstance(data, dict) else data
            except Exception as e:
                logger.warning("Could not read upload history: %s", e)
        return []

    def _save_directive(self, directive: Dict[str, Any]):
        try:
            with open(self.directive_file, "w", encoding="utf-8") as f:
                json.dump(directive, f, indent=2, ensure_ascii=False)
            logger.info("✓ Saved loop finetuning directive to: %s", self.directive_file)
        except Exception as e:
            logger.error("Failed to save finetuning directive: %s", e)
