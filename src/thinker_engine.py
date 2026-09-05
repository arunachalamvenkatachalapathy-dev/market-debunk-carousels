"""
Market Debunk - Schematic Thinker Layer
Powered by Gemini Thinking Mode.
Performs deterministic error taxonomy, root cause analysis, automated remediation,
and repairs numerical fact mismatches or pipeline exceptions.
"""

import json
import logging
import os
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from google import genai
from google.genai import types

from src.config import settings, STATE_DIR

logger = logging.getLogger(__name__)


class ThinkerEngine:
    """
    Intelligent Diagnostic & Auto-Remediation Engine.
    Uses Gemini Thinking Mode to diagnose pipeline failures and provide schematic repairs.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.model = os.getenv("GEMINI_THINKER_MODEL", "gemini-3.6-flash")
        self.incident_log_path = STATE_DIR / "thinker_incident_report.json"

    def _call_thinking_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini with explicit thinking budget and strict JSON response."""
        if not self.client:
            logger.warning("ThinkerEngine: GenAI client unavailable.")
            return None

        # Stage 1: Gemini Thinking Models
        models_to_try = [self.model, "gemini-3.7-flash", "gemini-flash-latest"]
        for m in models_to_try:
            try:
                cfg = types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=512),
                    response_mime_type="application/json",
                    temperature=0.2
                )
                response = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=cfg
                )
                if response.text:
                    clean_text = response.text.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                    return json.loads(clean_text.strip())
            except Exception as e:
                logger.warning("ThinkerEngine: Gemini model %s call failed: %s. Trying next...", m, e)

        # Stage 2: First Fallback to Gemma Models
        gemma_models = [settings.GEMMA_FALLBACK_MODEL, "gemma-4-26b-a4b-it"]
        for gm in gemma_models:
            try:
                logger.info("🤖 ThinkerEngine: Falling back to Gemma model: %s...", gm)
                response = self.client.models.generate_content(
                    model=gm,
                    contents=prompt + "\nCRITICAL: Output valid JSON only with no markdown or explanation."
                )
                if response.text:
                    clean_text = response.text.strip()
                    if "```json" in clean_text:
                        clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_text:
                        clean_text = clean_text.split("```")[1].split("```")[0].strip()
                    return json.loads(clean_text)
            except Exception as ge:
                logger.warning("ThinkerEngine: Gemma model %s call failed: %s.", gm, ge)

        return None

    def _record_incident(self, report: Dict[str, Any]) -> None:
        """Persists the diagnostic report into state/thinker_incident_report.json."""
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.incident_log_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info("📝 Thinker incident recorded to: %s", self.incident_log_path)
        except Exception as err:
            logger.error("Failed to record thinker incident: %s", err)

    def diagnose_research_failure(self, query: str, error: Exception) -> Dict[str, Any]:
        """Diagnoses SerpApi / web research failure and generates structured fallback."""
        prompt = f"""You are the Schematic Thinker Layer for 'Market Debunk' finance engine.
Phase: RESEARCH & SOURCING
Target Query: "{query}"
Exception: {str(error)}
Traceback: {traceback.format_exc()}

Analyze the failure and output a SCHEMATIC diagnostic report in JSON:
{{
  "timestamp": "{datetime.now(timezone.utc).isoformat()}",
  "phase": "RESEARCH",
  "severity": "RECOVERABLE",
  "error_code": "ERR_RESEARCH_FAILED",
  "root_cause_analysis": "Precise root cause",
  "reproducibility": "TRANSIENT_NETWORK or RATE_LIMIT or INVALID_KEY",
  "automated_remediation": {{
    "action": "ENGAGE_EVERGREEN_TOPIC",
    "repaired_payload": null
  }},
  "operator_action_required": false,
  "actionable_instructions": ["Step 1...", "Step 2..."]
}}"""
        result = self._call_thinking_llm(prompt)
        if not result:
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": "RESEARCH",
                "severity": "RECOVERABLE",
                "error_code": "ERR_RESEARCH_FAILED",
                "root_cause_analysis": f"Research query failed due to network or SerpApi error: {error}",
                "reproducibility": "TRANSIENT_NETWORK",
                "automated_remediation": {"action": "ENGAGE_EVERGREEN_TOPIC", "repaired_payload": None},
                "operator_action_required": False,
                "actionable_instructions": ["Verify SERPAPI_KEY quota and network connectivity."]
            }
        self._record_incident(result)
        return result

    def diagnose_and_repair_editorial_failure(
        self,
        source_text: str,
        failing_deck: Dict[str, Any],
        validation_report: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Diagnoses editorial fact-checking gate failure.
        Attempts schematic auto-repair to reconcile slide numbers with verified source numbers.
        Returns: (is_repaired, repaired_deck, diagnostic_report)
        """
        prompt = f"""You are the Senior Quantitative Fact-Checker & Thinker Layer for 'Market Debunk'.
Phase: EDITORIAL_FACT_CHECK
Validation Error: {validation_report}

SOURCE EVIDENCE CONTEXT:
{source_text[:3000]}

FAILING 6-SLIDE DECK:
{json.dumps(failing_deck, indent=2)}

TASK:
1. Analyze why the deck failed the quantitative fact-checking gate.
2. Find the exact citable financial numbers/percentages present in the source evidence.
3. Perform a precise AUTO-REPAIR on the slides to incorporate the verified source numbers into the slides without altering the overall narrative structure.
4. Output JSON strictly matching this schema:
{{
  "timestamp": "{datetime.now(timezone.utc).isoformat()}",
  "phase": "EDITORIAL_FACT_CHECK",
  "severity": "RECOVERABLE",
  "error_code": "ERR_FACT_CHECK_MISMATCH",
  "root_cause_analysis": "Exact explanation of numeric mismatch",
  "reproducibility": "DETERMINISTIC",
  "automated_remediation": {{
    "action": "AUTO_REPAIR_PAYLOAD",
    "repaired_payload": {{
      "caption": "Repaired caption...",
      "slides": [ ... 6 repaired slide objects ... ]
    }}
  }},
  "operator_action_required": false,
  "actionable_instructions": ["Automated repair applied to match source evidence numbers."]
}}"""

        diag = self._call_thinking_llm(prompt)
        if diag and diag.get("automated_remediation", {}).get("repaired_payload"):
            repaired = diag["automated_remediation"]["repaired_payload"]
            if len(repaired.get("slides", [])) == 6:
                diag["automated_remediation"]["action"] = "AUTO_REPAIR_SUCCESS"
                self._record_incident(diag)
                logger.info("✅ ThinkerEngine successfully synthesized a repaired slide deck!")
                return True, repaired, diag

        fail_diag = diag or {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "EDITORIAL_FACT_CHECK",
            "severity": "CRITICAL",
            "error_code": "ERR_FACT_CHECK_UNREPAIRABLE",
            "root_cause_analysis": validation_report,
            "reproducibility": "DETERMINISTIC",
            "automated_remediation": {"action": "CIRCUIT_BREAKER_EVERGREEN", "repaired_payload": None},
            "operator_action_required": False,
            "actionable_instructions": ["Falling back to pre-vetted evergreen financial debunk deck."]
        }
        self._record_incident(fail_diag)
        return False, None, fail_diag

    def diagnose_render_failure(self, deck: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """Diagnoses Playwright or Jinja2 template rendering errors."""
        prompt = f"""You are the Schematic Thinker Layer for 'Market Debunk'.
Phase: VISUAL_RENDERING
Error: {str(error)}
Traceback: {traceback.format_exc()}
Slide Count: {len(deck.get('slides', []))}

Analyze if the failure is due to Playwright browser installation, HTML template formatting, or missing fonts.
Output JSON schema:
{{
  "timestamp": "{datetime.now(timezone.utc).isoformat()}",
  "phase": "RENDERING",
  "severity": "CRITICAL",
  "error_code": "ERR_PLAYWRIGHT_RENDER",
  "root_cause_analysis": "Exact root cause",
  "reproducibility": "DETERMINISTIC or ENVIRONMENT",
  "automated_remediation": {{
    "action": "RETRY_WITH_HEADLESS_FALLBACK or ABORT",
    "repaired_payload": null
  }},
  "operator_action_required": true,
  "actionable_instructions": ["Run: python -m playwright install --with-deps chromium"]
}}"""
        res = self._call_thinking_llm(prompt)
        if not res:
            res = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": "RENDERING",
                "severity": "CRITICAL",
                "error_code": "ERR_PLAYWRIGHT_RENDER",
                "root_cause_analysis": f"Playwright rendering failed: {error}",
                "reproducibility": "ENVIRONMENT",
                "automated_remediation": {"action": "ABORT", "repaired_payload": None},
                "operator_action_required": True,
                "actionable_instructions": ["Ensure Playwright Chromium is installed: python -m playwright install --with-deps chromium"]
            }
        self._record_incident(res)
        return res

    def diagnose_publish_failure(
        self,
        platform: str,
        error_details: Any,
        payload_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Diagnoses Meta Graph API (Instagram/Facebook) or Telegram publishing errors.
        Decodes OAuth codes, image URL access failures, and rate limits.
        """
        prompt = f"""You are the Schematic Thinker Layer for 'Market Debunk' Multi-Platform Publishing.
Platform: {platform}
Error Details: {json.dumps(error_details, default=str)}
Payload Metadata: {json.dumps(payload_meta, default=str)}

Analyze the exact error.
Common Meta Graph API errors:
- Error 100, Subcode 2207001: Could not download image from URL (image URL returned 404 or timed out).
- Error 190: Invalid OAuth Access Token / Token expired.
- Error 10: Application does not have permission for this action.
- Telegram 429: Rate limit.

Output JSON strictly matching this schema:
{{
  "timestamp": "{datetime.now(timezone.utc).isoformat()}",
  "phase": "PUBLISHING",
  "platform": "{platform}",
  "severity": "CRITICAL or RECOVERABLE",
  "error_code": "ERR_META_API or ERR_IMAGE_NOT_ACCESSIBLE or ERR_TOKEN_EXPIRED",
  "root_cause_analysis": "Exact technical root cause",
  "reproducibility": "BAD_CREDENTIALS or URL_UNAVAILABLE or RATE_LIMIT",
  "automated_remediation": {{
    "action": "ISOLATE_AND_CONTINUE_SECONDARY or RETRY_AFTER_DELAY or ABORT",
    "retry_delay_seconds": 0
  }},
  "operator_action_required": true,
  "actionable_instructions": [
    "Specific step to fix token or URL accessibility"
  ]
}}"""
        res = self._call_thinking_llm(prompt)
        if not res:
            res = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": "PUBLISHING",
                "platform": platform,
                "severity": "CRITICAL",
                "error_code": f"ERR_{platform.upper()}_PUBLISH",
                "root_cause_analysis": f"Platform publish error: {error_details}",
                "reproducibility": "UNKNOWN",
                "automated_remediation": {"action": "ISOLATE_AND_CONTINUE_SECONDARY", "retry_delay_seconds": 0},
                "operator_action_required": True,
                "actionable_instructions": [f"Check {platform} API credentials and network permissions."]
            }
        self._record_incident(res)
        return res

    def diagnose_pipeline_crash(self, phase: str, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Top-level pipeline crash handler and incident generator."""
        prompt = f"""You are the Schematic Thinker Layer for 'Market Debunk'.
A CRITICAL UNHANDLED EXCEPTION stopped the pipeline.
Phase: {phase}
Error: {str(error)}
Traceback: {traceback.format_exc()}
Context: {json.dumps(context, default=str)}

Generate a complete schematic incident report in JSON:
{{
  "timestamp": "{datetime.now(timezone.utc).isoformat()}",
  "phase": "{phase}",
  "severity": "CRITICAL",
  "error_code": "ERR_PIPELINE_HALT",
  "root_cause_analysis": "Detailed diagnosis of the halting defect",
  "reproducibility": "DETERMINISTIC or TRANSIENT",
  "automated_remediation": {{
    "action": "SAFE_SHUTDOWN",
    "repaired_payload": null
  }},
  "operator_action_required": true,
  "actionable_instructions": [
    "Concrete troubleshooting step 1",
    "Concrete troubleshooting step 2"
  ]
}}"""
        res = self._call_thinking_llm(prompt)
        if not res:
            res = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": phase,
                "severity": "CRITICAL",
                "error_code": "ERR_PIPELINE_HALT",
                "root_cause_analysis": f"Unhandled exception in {phase}: {error}",
                "reproducibility": "UNKNOWN",
                "automated_remediation": {"action": "SAFE_SHUTDOWN", "repaired_payload": None},
                "operator_action_required": True,
                "actionable_instructions": [f"Inspect log traceback for phase {phase}."]
            }
        self._record_incident(res)
        return res
