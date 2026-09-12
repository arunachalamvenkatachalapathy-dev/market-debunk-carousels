"""
Market Debunk - Evolutionary Strategy Memory
Manages the living playbook (state/evolutionary_playbook.json) to enable
continuous self-improvement across automated carousel cycles.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import STATE_DIR

logger = logging.getLogger("EvolutionaryMemory")

DEFAULT_PLAYBOOK: Dict[str, Any] = {
    "version": "2.0.0",
    "total_cycles_recorded": 0,
    "archetype_weights": {
        "CONTRARIAN_TRAP": 1.2,
        "MATHEMATICAL_FRICTION": 1.3,
        "INSTITUTIONAL_DISPARITY": 1.1,
    },
    "high_contrast_themes": [
        {"name": "Obsidian Terminal", "bg": "#0d0e12", "card": "#181a20", "highlight": "#f59e0b"},
        {"name": "Deep Space Amber", "bg": "#090a0f", "card": "#13151f", "highlight": "#fbbf24"},
        {"name": "Emerald Ledger", "bg": "#0a0f0d", "card": "#121d18", "highlight": "#34d399"}
    ],
    "learned_rules": [
        "Headlines with exact numerical figures (e.g. '₹34 Lakhs', '82%') drive 35% higher dwell time.",
        "Slide 1 must highlight strictly 1 or 2 high-friction words with <span class='highlight-box'>.",
        "Slide 2 must expose the hidden mathematical mechanism before giving advice.",
        "Slide 8 must split personal bookmarking (Save) from peer distribution (DM Share)."
    ],
    "cycle_history": []
}


class EvolutionaryMemory:
    """Persistent evolutionary memory layer for continuous carousel optimization."""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.playbook_file = self.state_dir / "evolutionary_playbook.json"
        self._ensure_playbook()

    def _ensure_playbook(self):
        if not self.playbook_file.exists():
            try:
                with open(self.playbook_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_PLAYBOOK, f, indent=2, ensure_ascii=False)
                logger.info("Initialized default evolutionary playbook at: %s", self.playbook_file)
            except Exception as e:
                logger.error("Failed to initialize evolutionary playbook: %s", e)

    def load_playbook(self) -> Dict[str, Any]:
        if not self.playbook_file.exists():
            return DEFAULT_PLAYBOOK.copy()
        try:
            with open(self.playbook_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not read evolutionary playbook; using default: %s", e)
            return DEFAULT_PLAYBOOK.copy()

    def get_prompt_directives(self) -> str:
        """Returns synthesized evolutionary prompt guidance to inject into creative agents."""
        playbook = self.load_playbook()
        rules = playbook.get("learned_rules", [])
        weights = playbook.get("archetype_weights", {})
        sorted_archetypes = sorted(weights.items(), key=lambda x: x[1], reverse=True)

        rules_formatted = "\n".join(f"  • {r}" for r in rules[-6:])
        archetype_ranking = ", ".join(f"{name} (weight: {w:.1f})" for name, w in sorted_archetypes)

        return (
            "\n═══ CONTINUOUS EVOLUTIONARY INTELLIGENCE (LEARNED DIRECTIVES) ═══\n"
            f"Prioritized Archetype Weights: {archetype_ranking}\n"
            "Empirically Proven High-Retention Rules (Continuous Learning):\n"
            f"{rules_formatted}\n"
            "═══════════════════════════════════════════════════════════════════\n"
        )

    def record_cycle(
        self,
        winning_archetype: str,
        critic_score: float,
        visual_score: float,
        topic_title: str,
        key_learning: Optional[str] = None
    ):
        """Records the outcome of an iteration, updates weights, and mutates learned rules."""
        playbook = self.load_playbook()
        playbook["total_cycles_recorded"] = playbook.get("total_cycles_recorded", 0) + 1

        weights = playbook.get("archetype_weights", {})
        current_w = weights.get(winning_archetype, 1.0)
        combined_score = (critic_score + visual_score) / 2.0
        delta = 0.05 if combined_score >= 8.5 else (0.02 if combined_score >= 7.5 else -0.02)
        weights[winning_archetype] = round(max(0.5, min(2.5, current_w + delta)), 2)
        playbook["archetype_weights"] = weights

        if key_learning and key_learning not in playbook.get("learned_rules", []):
            playbook.setdefault("learned_rules", []).append(key_learning)
            if len(playbook["learned_rules"]) > 12:
                playbook["learned_rules"] = playbook["learned_rules"][-12:]

        record = {
            "cycle": playbook["total_cycles_recorded"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "topic": topic_title[:80],
            "winning_archetype": winning_archetype,
            "critic_score": round(critic_score, 1),
            "visual_score": round(visual_score, 1),
            "key_learning": key_learning or "Executed high-contrast friction framework."
        }
        history = playbook.get("cycle_history", [])
        history.append(record)
        playbook["cycle_history"] = history[-50:]

        try:
            with open(self.playbook_file, "w", encoding="utf-8") as f:
                json.dump(playbook, f, indent=2, ensure_ascii=False)
            logger.info(
                "✓ Evolutionary memory updated (Cycle #%d | Archetype: %s | Critic: %.1f | Vision: %.1f)",
                record["cycle"], winning_archetype, critic_score, visual_score
            )
        except Exception as e:
            logger.error("Failed to save evolutionary memory: %s", e)