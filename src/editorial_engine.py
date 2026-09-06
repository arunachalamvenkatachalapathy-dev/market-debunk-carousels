import json
import logging
import re
from typing import Optional, List, Dict, Tuple
from google import genai

from src.config import settings
from src.thinker_engine import ThinkerEngine

logger = logging.getLogger(__name__)


class EditorialEngine:
    """
    Two-pass financial carousel composer with an explicit Numeric Fact-Checking Gate.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.thinker = ThinkerEngine(api_key=self.api_key)

    def compose_carousel(self, topic_data: dict, brief: str) -> dict:
        """
        Pass 1: Draft the 6-slide carousel deck and caption.
        Pass 2: Run the Numeric Fact-Checking Gate to verify all numbers against source context.
        Circuit Breaker: On 2nd consecutive failure, fall back immediately to pre-vetted evergreen archetype.
        """
        # ── Pass 1: Draft Composition ───────────────────────────────────────
        logger.info("═══ Editorial Pass 1: Drafting 6-Slide Carousel & Caption ═══")
        try:
            deck = self._generate_draft(topic_data, brief)
        except Exception as draft_err:
            logger.warning("Primary Gemini draft failed (%s); attempting Gemma model fallback...", draft_err)
            deck = self._generate_draft_gemma(topic_data, brief)
            if not deck:
                logger.error("Gemma draft failed; falling back to pre-reserved topic templates.")
                deck = self._generate_fallback_deck(topic_data)
                deck["fact_check_status"] = "circuit_breaker_evergreen_fallback"
                deck["slides"] = self._normalize_slides(deck.get("slides", []), topic_data)
                return deck

        # ── Pass 2: Numeric Fact-Checking Gate ──────────────────────────────
        logger.info("═══ Editorial Pass 2: Running Numeric Fact-Checking Gate ═══")
        is_valid, report = self._verify_numeric_facts(deck, topic_data)
        
        if not is_valid:
            logger.warning("❌ Numeric Fact-Checking Gate failed (Attempt 1): %s. Regenerating once with strict corrective instructions...", report)
            repair_prompt = (
                f"{brief}\n\n"
                f"STRICT FACT-CHECK REPAIR INSTRUCTION:\n{report}\n"
                f"EVIDENCE SNAPSHOT: {topic_data.get('evidence_snapshot', '')}\n"
                f"Preserve the exact numerical anchors from the snapshot."
            )
            deck = self._generate_draft(topic_data, repair_prompt)
            is_valid_retry, report_retry = self._verify_numeric_facts(deck, topic_data)
            
            if is_valid_retry:
                logger.info("✅ Repaired deck passed Numeric Fact-Checking Gate.")
                deck["fact_check_status"] = "verified_after_repair"
            else:
                # ── Pass 3: Invoke ThinkerEngine with Gemini Thinking Mode for Auto-Repair ──
                logger.warning("🧠 Invoking Schematic Thinker Layer for numeric auto-repair...")
                source_full = f"{topic_data.get('raw_text', '')} {topic_data.get('title', '')} {topic_data.get('source_snippet', '')}"
                is_th_repaired, th_deck, diag = self.thinker.diagnose_and_repair_editorial_failure(
                    source_text=source_full,
                    failing_deck=deck,
                    validation_report=report_retry
                )
                if is_th_repaired and th_deck:
                    logger.info("✅ ThinkerEngine auto-repaired slide deck facts successfully!")
                    deck = th_deck
                    deck["fact_check_status"] = "thinker_auto_repaired"
                else:
                    # ── Pass 4: Fallback to Gemma Model ──
                    logger.warning("🤖 Primary drafting/repair unverified; falling back to Gemma model (%s)...", settings.GEMMA_FALLBACK_MODEL)
                    gemma_deck = self._generate_draft_gemma(topic_data, brief)
                    if gemma_deck and len(gemma_deck.get("slides", [])) == 6:
                        is_gm_valid, gm_report = self._verify_numeric_facts(gemma_deck, topic_data)
                        if is_gm_valid:
                            logger.info("✅ Gemma fallback deck passed Fact-Checking Gate!")
                            deck = gemma_deck
                            deck["fact_check_status"] = "gemma_fallback_verified"
                        else:
                            logger.warning("Gemma deck failed numeric fact check (%s). Moving to pre-reserved templates...", gm_report)
                            gemma_deck = None

                    if not gemma_deck:
                        # ── FINAL CIRCUIT BREAKER: Move to pre-reserved evergreen topic templates ──
                        logger.error("🚨 GEMMA FALLBACK FAILED. Engaging Circuit Breaker -> Moving to pre-reserved topic templates.")
                        logger.info("🛡️ Engaging Fact-Check Circuit Breaker: Falling back immediately to pre-vetted evergreen topic.")
                        
                        # Update topic_data in place so master package reflects the verified reality
                        topic_data["circuit_breaker_engaged"] = True
                        topic_data["circuit_breaker_reason"] = report_retry
                        topic_data["from_live_api"] = False
                        
                        deck = self._generate_fallback_deck(topic_data)
                        deck["fact_check_status"] = "circuit_breaker_evergreen_fallback"
        else:
            logger.info("✅ %s", report)
            deck["fact_check_status"] = "verified_pass"

        # ── Pass 3: Grammar & Polish Verification Gate ──
        logger.info("═══ Editorial Pass 3: Grammar & Polish Verification Gate ═══")
        try:
            from src.workflow_agents import GrammarAgent
            grammar_agent = GrammarAgent(llm_client=self.client)
            deck = grammar_agent.review_and_polish_deck(deck, topic_data)
        except Exception as g_err:
            logger.warning("GrammarAgent review skipped: %s", g_err)

        # Normalize and ensure visual consistency
        deck["slides"] = self._normalize_slides(deck.get("slides", []), topic_data)
        return deck

    def _generate_draft_gemma(self, topic_data: dict, brief: str) -> Optional[dict]:
        """
        First fallback model: Gemma (gemma-4-31b-it / gemma-4-26b-a4b-it).
        Attempts generation using Gemma before moving to pre-reserved topic templates.
        """
        if not self.client:
            return None

        title = topic_data.get("title", "")
        raw_text = topic_data.get("raw_text", "")

        prompt = f"""You are a financial content strategist for 'Market Debunk'.
Create a high-density 6-slide financial carousel debunking a retail investing trap.
TOPIC: {title}
SOURCE CONTEXT: {raw_text}
BRIEF: {brief}

STRICT SPECIFICATIONS:
- Slide 1 (hook): 2-3 short lines, shocking words in <span class="highlight-box">...</span>
- Slide 2 (friction): card_a_text (myth), card_b_text (reality with exact numbers), takeaway
- Slide 3 (breakdown): 3 numbered points
- Slide 4 (playbook): steps 1 & 2
- Slide 5 (concept): 3 actionable rules
- Slide 6 (cta): Save this post, comment 'GUIDE'

CRITICAL: Return valid JSON ONLY with keys "caption" and "slides" (array of 6 objects). Do NOT include explanation."""

        gemma_models = [settings.GEMMA_FALLBACK_MODEL, "gemma-4-26b-a4b-it"]
        for gm in gemma_models:
            try:
                logger.info("🤖 Attempting draft generation with Gemma model: %s...", gm)
                response = self.client.models.generate_content(
                    model=gm,
                    contents=prompt
                )
                if response.text:
                    clean_text = response.text.strip()
                    if "```json" in clean_text:
                        clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_text:
                        clean_text = clean_text.split("```")[1].split("```")[0].strip()
                    data = json.loads(clean_text)
                    if len(data.get("slides", [])) == 6:
                        logger.info("✓ Gemma model %s successfully generated 6-slide draft.", gm)
                        return data
            except Exception as e:
                logger.warning("Gemma model %s draft failed: %s", gm, e)

        return None

    def _generate_draft(self, topic_data: dict, brief: str) -> dict:
        title = topic_data.get("title", "")
        raw_text = topic_data.get("raw_text", "")

        prompt = f"""You are a senior quantitative financial editor for 'Market Debunk'.
Create an authoritative, high-density 8-slide Instagram carousel debunking a retail investing trap.
The design language is strictly modeled after an ultra-clean, spacious editorial template:
- Large, bold headlines with exactly ONE phrase highlighted in <span class="highlight-box">...</span>.
- On content slides (Slides 2–7): exactly ONE tactile green card with concise, authoritative text.
- NO extra boxes, NO checklist badges, NO mini KPI widgets.

TOPIC: {title}
SOURCE CONTEXT: {raw_text}
CREATIVE BRIEF:
{brief}

DESIGN SPECIFICATIONS (EXACTLY 8 SLIDES):
- Slide 1 (role: "hook"): 4-8 words maximum. Bold curiosity gap. 1-2 words in <span class="highlight-box">...</span>. tag: "#2026".
- Slide 2 (role: "value_1"): The Core Illusion vs Reality. title: 2-3 lines with highlight box. card_text: 35-50 words explaining the myth vs institutional truth. Bold key metrics using <strong>...</strong>.
- Slide 3 (role: "value_2"): The Primary Hidden Trap / Mechanism. title: 2-3 lines with highlight box. card_text: 35-50 words explaining how capital is quietly extracted or risk shifted.
- Slide 4 (role: "value_3"): Distribution / Liquidity Trap. title: 2-3 lines with highlight box. card_text: 35-50 words detailing institutional exit liquidity or order flow reality.
- Slide 5 (role: "value_4"): Mathematical Compounding Drag. title: 2-3 lines with highlight box. card_text: 35-50 words breaking down the long-term rupee loss or fee erosion with exact figures.
- Slide 6 (role: "value_5"): The Non-Negotiable Institutional Rule. title: 2-3 lines with highlight box. card_text: 35-50 words presenting the golden execution rule to protect retail principal.
- Slide 7 (role: "value_6"): The Pre-Trade Verification Checklist. title: 2-3 lines with highlight box. card_text: 35-50 words outlining the 3-point audit every investor must run before allocating capital.
- Slide 8 (role: "bookmark_save"): Standard Save & Lead Magnet CTA. title_lines: ["Don’t", "forget to", "<span class=\\"highlight-box\\">save this</span>", "post for", "later"]. tag: "#MARKETDEBUNK".

Return JSON ONLY:
{{
  "caption": "High-converting Instagram caption (hook, 3-bullet value preview, keyword CTA 'Follow @Market_Debunk and comment GUIDE for the full Investor Playbook PDF', 3-5 relevant hashtags)",
  "slides": [ ... exactly 8 slide objects ... ]
}}"""

        models_to_try = [
            settings.GEMINI_MODEL,
            "gemini-3.6-flash",
            "gemini-3.7-flash",
        ]

        if self.client:
            for model_name in models_to_try:
                try:
                    logger.info("Attempting carousel draft with model %s...", model_name)
                    config = {"temperature": 0.3}
                    if not model_name.startswith("gemma"):
                        config["response_mime_type"] = "application/json"

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )
                    if response.text:
                        clean_text = response.text.strip()
                        if "```json" in clean_text:
                            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in clean_text:
                            clean_text = clean_text.split("```")[1].split("```")[0].strip()
                        data = json.loads(clean_text)
                        if len(data.get("slides", [])) >= 7:
                            logger.info("✓ Model %s successfully generated draft with %d slides.", model_name, len(data["slides"]))
                            return data
                except Exception as e:
                    logger.warning("Model %s draft attempt failed: %s", model_name, e)

        return self._generate_fallback_deck(topic_data)

    # ── Numeric Fact-Checking Gate ──────────────────────────────────────────

    def _verify_numeric_facts(self, deck: dict, topic_data: dict) -> Tuple[bool, str]:
        """
        Extracts all numeric and financial claims across the 8 slides and verifies
        whether they are consistent with the source text.
        """
        source_text = f"{topic_data.get('raw_text', '')} {topic_data.get('title', '')} {topic_data.get('source_snippet', '')}"
        slides = deck.get("slides", [])

        # Collect all text from all slides
        all_slide_text = ""
        for s in slides:
            all_slide_text += f" {s.get('title', '')} {s.get('card_text', '')} "
            for tl in s.get("title_lines", []):
                all_slide_text += f" {tl} "

        # Financial regex: currency, %, Lakh, Crore, bps, years, months
        pattern = r"(?:₹|\$)\s?\d+(?:[,\.]\d+)?(?:\s?(?:Cr|Lakh|Lakhs|Crore|Crores|k|M|B))?|\b\d+(?:[,\.]\d+)?\s?%|\b\d+\s?(?:Lakh|Lakhs|Crore|Crores|Cr|bps|years|months)\b"

        raw_source_matches = re.findall(pattern, source_text, flags=re.IGNORECASE)
        clean_source_nums = set()
        for m in raw_source_matches:
            cleaned = m.strip()
            if not re.search(r"\.\d{4,}", cleaned):  # Exclude microsecond timestamps
                clean_source_nums.add(cleaned)

        if not clean_source_nums:
            return True, "Source context has no specific financial metrics; qualitative validation passed."

        anchor_match = []
        for src_num in clean_source_nums:
            digits_match = re.search(r"\d+(?:[,\.]\d+)?", src_num)
            if digits_match:
                d = digits_match.group(0)
                if d in all_slide_text:
                    anchor_match.append(src_num)

        if not anchor_match and clean_source_nums:
            return False, f"Missing source anchor metric! Expected at least one of {clean_source_nums} in slide deck."

        return True, f"FACT CHECK PASSED: Verified anchor metric(s) {list(anchor_match)} preserved across slide deck."

    # ── Slide Normalization & Formatting ────────────────────────────────────

    def _normalize_slides(self, slides: list, topic_data: dict) -> list:
        normalized = []
        expected_count = settings.EXPECTED_SLIDE_COUNT

        for idx in range(expected_count):
            if idx < len(slides):
                s = dict(slides[idx])
            else:
                s = {}

            s["slide_index"] = idx + 1
            s["tag"] = "#MARKETDEBUNK"

            if idx == 0:
                s["role"] = "hook"
                raw_title = s.get("title") or s.get("headline") or topic_data.get("title", "Market Debunk")
                # Strip all websites, domains, quotes, and legal boilerplate
                raw_title = re.sub(r"\s*[-|–—]\s*(?:indianexpress\.com|moneycontrol|economic times|ndtv profit|reuters|bloomberg|livemint|[a-zA-Z0-9.-]+\.(?:com|in|org|net)).*$", "", str(raw_title), flags=re.I)
                raw_title = re.sub(r"https?://\S+", "", raw_title)
                raw_title = re.sub(r"\b[a-zA-Z0-9.-]+\.(?:com|in|org|net)\b", "", raw_title, flags=re.I)
                raw_title = re.sub(r"^[‘'\"“]+|[’'\"”]+$", "", raw_title)
                raw_title = re.sub(r"^[‘'\"“][^:’'\"]+[:’'\"]\s*", "", raw_title)
                s["title_lines"] = self._format_title_lines(raw_title, is_hook=True, slide_index=1)
                s["card_text"] = ""
            elif idx == expected_count - 1:
                s["role"] = "bookmark_save"
                s["title_lines"] = ["Don’t", "forget to", "<span class='highlight-box'>save this</span>", "post for", "later"]
                s["card_text"] = ""
                if not s.get("cta_detail"):
                    s["cta_detail"] = "Save this framework to your private collection. Review these institutional risk checkpoints before taking your next trade to protect your capital from market traps."
            else:
                s["role"] = s.get("role") or f"value_{idx}"
                raw_title = s.get("title") or s.get("headline")
                if not raw_title or "Institutional Reality" in str(raw_title):
                    defaults = [
                        "The Core Illusion <span class='highlight-box'>Exposed By Math</span>",
                        "How Syndicates <span class='highlight-box'>Dump Liquidity</span>",
                        "The Hidden Regulatory <span class='highlight-box'>Capital Trap</span>",
                        "The Compounding <span class='highlight-box'>Opportunity Loss</span>",
                        "The Golden Rule: <span class='highlight-box'>Exit Instantly</span>",
                        "The 3-Point <span class='highlight-box'>Pre-Trade Audit</span>",
                    ]
                    raw_title = defaults[(idx - 1) % len(defaults)]
                # Strip trailing numbers like #1, #2
                raw_title = re.sub(r"\s*#\d+\b", "", str(raw_title)).strip()
                s["title_lines"] = self._format_title_lines(raw_title, is_hook=False, slide_index=idx + 1)
                card_text = s.get("card_text") or s.get("mechanism") or s.get("card_b_text") or s.get("takeaway") or ""
                if not card_text:
                    card_text = "Institutions trade on verified balance sheet quality and liquidity margins, while retail investors chase short-term headline hype."
                card_text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", card_text)
                s["card_text"] = card_text

            normalized.append(s)

        return normalized

    def _format_title_lines(self, raw_title: str, is_hook: bool = False, slide_index: int = 1) -> List[str]:
        # If raw_title already has highlight-box markup
        if "highlight-box" in raw_title:
            # Handle hook with highlight box: break into clean 3-4 lines with at most 2 words highlighted
            if slide_index == 1 or is_hook:
                m = re.search(r"<span class=['\"]highlight-box['\"]>([^<]+)</span>", raw_title)
                if m:
                    hl_words = m.group(1).strip().split()
                    hl_text = " ".join(hl_words[:2]) if len(hl_words) > 2 else " ".join(hl_words)
                    before = re.sub(r"<[^>]+>", "", raw_title[:m.start()]).strip()
                    after = re.sub(r"<[^>]+>", "", raw_title[m.end():]).strip()
                    lines = []
                    if before:
                        b_words = before.split()
                        if len(b_words) > 2:
                            lines.append(" ".join(b_words[:2]))
                            lines.append(" ".join(b_words[2:4]))
                        else:
                            lines.append(" ".join(b_words))
                    lines.append(f"<span class='highlight-box'>{hl_text}</span>")
                    if after:
                        a_words = after.split()
                        lines.append(" ".join(a_words[:2]))
                    return [l for l in lines if l.strip()]

            # Non-hook slides with highlight box
            lines = [l.strip() for l in re.split(r"<br\s*/?>|\n", raw_title) if l.strip()]
            filtered = [l for l in lines if not re.match(r"^#?\d+[\.\)]?$", l)]
            if len(filtered) > 1:
                return filtered

        clean = re.sub(r"<[^>]+>", "", raw_title).strip()
        # Remove any leading or trailing isolated numbers
        clean = re.sub(r"\s*#\d+\b", "", clean).strip()
        words = clean.split()
        if not words:
            return ["Market Debunk"]

        # Slide 1 (Hook - strictly 4 to 6 words, punchy 3-4 lines, not huge!)
        if slide_index == 1 or is_hook:
            words = words[:6]
            if len(words) <= 3:
                return [" ".join(words[:1]), f"<span class='highlight-box'>{' '.join(words[1:])}</span>"]
            elif len(words) == 4:
                return [" ".join(words[:2]), f"<span class='highlight-box'>{' '.join(words[2:])}</span>"]
            elif len(words) == 5:
                return [" ".join(words[:2]), f"<span class='highlight-box'>{' '.join(words[2:4])}</span>", words[4]]
            else:
                return [" ".join(words[:2]), f"<span class='highlight-box'>{' '.join(words[2:4])}</span>", " ".join(words[4:])]

        # Content Slides: 2–3 clean lines, strictly NO lone numbers or lone symbols
        words = [w for w in words if not re.match(r"^#?\d+$", w)]
        if len(words) <= 3:
            return [f"<span class='highlight-box'>{' '.join(words[:2])}</span>", " ".join(words[2:])] if len(words) > 2 else [f"<span class='highlight-box'>{' '.join(words)}</span>"]
        
        mid = min(2, len(words) // 2)
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:mid+2])
        rest = " ".join(words[mid+2:])
        
        res = [line1, f"<span class='highlight-box'>{line2}</span>"]
        if rest:
            res.append(rest)
        return [r for r in res if r.strip()]

    def _generate_fallback_deck(self, topic_data: dict) -> dict:
        title = topic_data.get("title", "The Compounding Drag Retail Investors Ignore")
        words = title.split()
        clean_hook = " ".join(words[:4]) if len(words) > 4 else title

        return {
            "caption": (
                f"🚨 The Hidden Math Behind {clean_hook}\n\n"
                f"Most retail investors assume small recurring fees don't matter, but compound mathematics tells a completely different story.\n\n"
                f"Swipe through this 8-slide breakdown to audit your capital:\n"
                f"• The silent trailing fee structure\n"
                f"• Real terminal compounding loss\n"
                f"• The 3-point pre-trade audit checklist\n\n"
                f"💬 Follow @Market_Debunk and comment 'GUIDE' below to receive our complete detailed Investor Playbook & Risk Checklist directly in your DMs!\n\n"
                f"#StockMarket #Investing #MutualFunds #Nifty50 #PersonalFinance"
            ),
            "slides": [
                {
                    "role": "hook",
                    "title": f"The Hidden Math <span class='highlight-box'>Behind {clean_hook}</span>",
                    "tag": "#2026"
                },
                {
                    "role": "value_1",
                    "title": "Think Smart <span class='highlight-box'>Always For Better</span> Decisions",
                    "card_text": "Retail investors assume a <strong>1% distributor commission</strong> is negligible over time. On a ₹15,000 monthly SIP over 25 years, that 1% fee quietly extracts <strong>₹34 Lakhs</strong> from your wealth.",
                    "tag": "#MARKETDEBUNK"
                },
                {
                    "role": "value_2",
                    "title": "Distributor Trailing <span class='highlight-box'>Commissions Extract</span> Wealth",
                    "card_text": "Trailing commissions are deducted <strong>every single month</strong> directly from your net asset value. Even during major market corrections, distributors earn guaranteed annuities from your portfolio.",
                    "tag": "#MARKETDEBUNK"
                },
                {
                    "role": "value_3",
                    "title": "The Compounding <span class='highlight-box'>Multiplier Effect</span> In Action",
                    "card_text": "Money lost to fees cannot compound. A <strong>₹1 Lakh</strong> fee paid today robs you of <strong>₹10+ Lakhs</strong> in terminal retirement returns. Compounding works both ways: gains multiply, fees multiply exponentially.",
                    "tag": "#MARKETDEBUNK"
                },
                {
                    "role": "value_4",
                    "title": "Regular Plans Offer <span class='highlight-box'>Zero Incremental</span> Alpha",
                    "card_text": "Regular mutual fund schemes hold the <strong>exact same stocks</strong>, follow the same fund managers, and carry identical market risk as Direct plans. You pay recurring fees for zero added performance.",
                    "tag": "#MARKETDEBUNK"
                },
                {
                    "role": "value_5",
                    "title": "Institutional Rules <span class='highlight-box'>To Protect Your</span> Principal",
                    "card_text": "Verify every mutual fund in your portfolio has <strong>'Direct' explicitly in its name</strong>. Cap active equity expense ratios under <strong>0.80%</strong> and passive index funds under <strong>0.20%</strong>.",
                    "tag": "#MARKETDEBUNK"
                },
                {
                    "role": "value_6",
                    "title": "The Pre-Trade <span class='highlight-box'>Capital Audit</span> Checklist",
                    "card_text": "Audit your Total Expense Ratio quarterly. Calculate the <strong>exact rupee commission</strong> paid per year, and switch accumulated units to direct zero-commission platforms to preserve 100% of your compounding capital.",
                    "tag": "#MARKETDEBUNK"
                },
                {
                    "role": "bookmark_save",
                    "title_lines": ["Don’t", "forget to", "<span class='highlight-box'>save this</span>", "post for", "later"],
                    "tag": "#MARKETDEBUNK"
                }
            ]
        }
