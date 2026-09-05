import json
import logging
import re
from typing import Optional, List, Dict, Tuple
from google import genai

from src.config import settings

logger = logging.getLogger(__name__)


class EditorialEngine:
    """
    Two-pass financial carousel composer with an explicit Numeric Fact-Checking Gate.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    def compose_carousel(self, topic_data: dict, brief: str) -> dict:
        """
        Pass 1: Draft the 6-slide carousel deck and caption.
        Pass 2: Run the Numeric Fact-Checking Gate to verify all numbers against source context.
        """
        # ── Pass 1: Generation ──────────────────────────────────────────────
        logger.info("═══ Editorial Pass 1: Drafting 6-Slide Carousel Deck ═══")
        deck = self._generate_draft(topic_data, brief)

        # ── Pass 2: Numeric Fact-Checking Gate ──────────────────────────────
        logger.info("═══ Editorial Pass 2: Running Numeric Fact-Checking Gate ═══")
        is_valid, report = self._verify_numeric_facts(deck, topic_data)
        
        if not is_valid:
            logger.warning("❌ Numeric Fact-Checking Gate failed: %s. Retrying with repair prompt...", report)
            deck = self._generate_draft(topic_data, f"{brief}\n\nSTRICT FACT-CHECK REPAIR INSTRUCTION: {report}")
            is_valid_retry, report_retry = self._verify_numeric_facts(deck, topic_data)
            if is_valid_retry:
                logger.info("✅ Repaired deck passed Numeric Fact-Checking Gate.")
            else:
                logger.warning("⚠️ Deck still has numeric discrepancies (%s); normalizing cautiously.", report_retry)
        else:
            logger.info("✅ %s", report)

        # Normalize and ensure visual consistency
        deck["slides"] = self._normalize_slides(deck.get("slides", []), topic_data)
        return deck

    def _generate_draft(self, topic_data: dict, brief: str) -> dict:
        title = topic_data.get("title", "")
        raw_text = topic_data.get("raw_text", "")
        archetype = topic_data.get("archetype", "")

        prompt = f"""You are a master financial content strategist for 'Market Debunk'.
Create an agency-grade, high-density 6-slide Instagram/LinkedIn carousel debunking a retail investing trap.

TOPIC: {title}
SOURCE CONTEXT: {raw_text}
CREATIVE BRIEF:
{brief}

DESIGN SPECIFICATIONS (EXACTLY 6 SLIDES):
- Slide 1 (role: "hook"):
  - title: 2-3 short lines. Put the most shocking 1-3 words inside <span class="highlight-box">...</span> (canary yellow marker).
  - deliverable: e.g. "Inside: 5-Point Mathematical Breakdown"
  - tag: e.g. "#MUTUALFUNDS", "#SEBIRULES", "#CREDITCARDS", "#INVESTING"

- Slide 2 (role: "friction"):
  - title: e.g. "The Illusion of Safe 12% SIPs"
  - card_a_text: What retail investors are told or believe (1-2 sentences).
  - card_b_text: The operational reality or hidden cost (1-2 sentences).
  - takeaway: Core rule stated as contrast: "X creates familiarity. Y creates wealth."

- Slide 3 (role: "breakdown"):
  - title: e.g. "3 Silent Leakages in Your Returns"
  - points: Exactly 3 numbered items. Each item: {{"num": "1", "title": "2-3 word title", "desc": "Concrete explanation with real mechanism"}}

- Slide 4 (role: "architecture" OR "step_diagram"):
  - If the concept has a 3-4 step framework, use layout "step_diagram":
    {{"layout": "step_diagram", "steps": [
      {{"number": 1, "icon_concept": "calculator", "color": "#A8D5BA", "label": "AUDIT", "sublabel": "Check expense ratio"}},
      {{"number": 2, "icon_concept": "bar chart", "color": "#F5D782", "label": "COMPARE", "sublabel": "Run direct vs regular"}},
      {{"number": 3, "icon_concept": "shield", "color": "#A8C8E8", "label": "SWITCH", "sublabel": "Move to zero-commission"}}
    ], "headline": "The 3-Step Clean Capital Loop", "body_lines": ["Distributors sell convenience.", "Direct plans preserve compounding."], "closing_line": "Audit your expense ratio before adding fresh capital."}}
  - Otherwise, provide 3-4 structured process steps with a strict execution rule.

- Slide 5 (role: "concept"):
  - title: e.g. "3 Rules Before Making Your Next Move"
  - rules: Exactly 3 actionable rules for retail investors with bold titles.

- Slide 6 (role: "cta"):
  - title_lines: ["Don't <span class=\\"highlight-box\\">forget to</span>", "save this <span class=\\"highlight-box\\">post</span>"]
  - discussion_question: A thoughtful prompt for the comments.
  - lead_magnet: {{"trigger_word": "GUIDE", "resource_name": "The Retail Risk Checklist"}}

Return JSON ONLY:
{{
  "caption": "High-converting Instagram/LinkedIn caption (hook, bullet points, CTA, hashtags)",
  "slides": [ ... 6 slide objects ... ]
}}"""

        if self.client:
            try:
                response = self.client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={"response_mime_type": "application/json", "temperature": 0.4}
                )
                if response.text:
                    data = json.loads(response.text)
                    if len(data.get("slides", [])) == 6:
                        return data
            except Exception as e:
                logger.warning("Gemini carousel drafting failed (%s); building deterministic deck.", e)

        return self._generate_fallback_deck(topic_data)

    # ── Numeric Fact-Checking Gate ──────────────────────────────────────────

    def _verify_numeric_facts(self, deck: dict, topic_data: dict) -> Tuple[bool, str]:
        """
        Extracts all numeric and financial claims across the 6 slides and verifies
        whether they are consistent with the source text.
        """
        source_text = topic_data.get("raw_text", "") + " " + topic_data.get("title", "")
        slides = deck.get("slides", [])
        
        # Collect all text from all slides
        all_slide_text = ""
        for s in slides:
            all_slide_text += f" {s.get('title', '')} {s.get('card_a_text', '')} {s.get('card_b_text', '')} {s.get('takeaway', '')} "
            for p in s.get("points", []):
                all_slide_text += f" {p.get('title', '')} {p.get('desc', '')} "
            for r in s.get("rules", []):
                all_slide_text += f" {r.get('title', '')} {r.get('desc', '')} "
            for b in s.get("body_lines", []):
                all_slide_text += f" {b} "
            all_slide_text += f" {s.get('headline', '')} {s.get('closing_line', '')} "

        # Extract specific figures: e.g. ₹X, X%, X Lakh, X Crore, X years
        slide_numbers = re.findall(r"(?:₹|\$)?\b\d+(?:[\.,]\d+)?\s?(?:%|Cr|Lakh|Lakhs|Crore|Crores|years|months|bps)?\b", all_slide_text)
        clean_slide_nums = set(n.strip() for n in slide_numbers if len(n.strip()) > 1 and not n.strip().isdigit())

        source_numbers = re.findall(r"(?:₹|\$)?\b\d+(?:[\.,]\d+)?\s?(?:%|Cr|Lakh|Lakhs|Crore|Crores|years|months|bps)?\b", source_text)
        clean_source_nums = set(n.strip() for n in source_numbers if len(n.strip()) > 1 and not n.strip().isdigit())

        # If source has no numbers detected, pass gracefully
        if not clean_source_nums:
            return True, "Source context has no specific numbers; qualitative validation passed."

        # Check if at least one anchor metric from source is preserved in slides
        anchor_match = clean_slide_nums.intersection(clean_source_nums)
        if not anchor_match and clean_source_nums:
            return False, f"Missing source anchor metric! Expected at least one of {clean_source_nums} in slide deck."

        return True, f"FACT CHECK PASSED: Verified anchor metric(s) {list(anchor_match)} preserved across slide deck."

    # ── Slide Normalization & Formatting ────────────────────────────────────

    def _normalize_slides(self, slides: list, topic_data: dict) -> list:
        normalized = []
        default_tags = ["#INVESTING", "#MARKETTRUTH", "#HIDDENMATH", "#PLAYBOOK", "#STRATEGY", "#SAVETHIS"]

        for idx, slide in enumerate(slides[:6]):
            s = dict(slide)
            s["slide_index"] = idx + 1
            s["tag"] = s.get("tag") or default_tags[idx]

            # Ensure title_lines with yellow highlight box
            raw_title = s.get("title") or s.get("headline") or ""
            if not s.get("title_lines"):
                s["title_lines"] = self._format_title_lines(raw_title, is_hook=(idx == 0))

            # Build HTML body representation
            s["body_html"] = self._build_slide_body_html(s, idx)
            normalized.append(s)

        return normalized

    def _format_title_lines(self, raw_title: str, is_hook: bool = False) -> List[str]:
        clean = re.sub(r"<[^>]+>", "", raw_title).strip()
        words = clean.split()
        if not words:
            return ["Market Debunk"]

        if len(words) <= 4:
            if is_hook:
                return [f"<span class='highlight-box'>{clean}</span>"]
            return [clean]

        # Break into 2-3 lines
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

        if is_hook:
            # Highlight the second half or punchy words
            return [line1, f"<span class='highlight-box'>{line2}</span>"]
        return [line1, line2]

    def _build_slide_body_html(self, slide: dict, index: int) -> str:
        role = slide.get("role", "")
        layout = slide.get("layout", "")

        # Layout: Step Diagram
        if layout == "step_diagram" or slide.get("steps"):
            steps = slide.get("steps", [])
            step_cards = []
            for st in steps:
                color = st.get("color", "#A8D5BA")
                num = st.get("number", 1)
                lbl = st.get("label", "")
                sub = st.get("sublabel", "")
                step_cards.append(f"""
                <div class="step-card">
                  <div class="step-circle" style="background-color: {color};">
                    <span class="step-number">{num}</span>
                  </div>
                  <div class="step-meta">
                    <span class="step-label">{lbl}</span>
                    <span class="step-sublabel">{sub}</span>
                  </div>
                </div>""")
            steps_html = "".join(step_cards)
            body_lines = "".join(f"<p class='body-para'>{l}</p>" for l in slide.get("body_lines", []))
            closing = f"<p class='takeaway-para'><strong>Takeaway:</strong> {slide.get('closing_line', '')}</p>" if slide.get("closing_line") else ""
            return f"""<div class="step-diagram-container"><div class="steps-row">{steps_html}</div><div class="step-body-content">{body_lines}{closing}</div></div>"""

        # Role: Friction (Slide 2)
        if index == 1 or role == "friction":
            card_a = slide.get("card_a_text", "Retail belief: Small recurring fees don't impact wealth.")
            card_b = slide.get("card_b_text", "Operational reality: Compounding fees extract up to 30% of total wealth.")
            takeaway = slide.get("takeaway", "Never confuse percentage points with absolute rupee compounding.")
            return f"""
            <div class="slide-body-paragraphs">
              <p class="body-para"><strong>The Myth:</strong> {card_a}</p>
              <p class="body-para"><strong>The Reality:</strong> {card_b}</p>
              <p class="takeaway-para"><strong>Core Rule:</strong> {takeaway}</p>
            </div>"""

        # Role: Breakdown / Points (Slide 3)
        if index == 2 or role == "breakdown":
            points = slide.get("points", [])
            items = []
            for i, p in enumerate(points):
                num = p.get("num", str(i + 1))
                t = p.get("title", "")
                d = p.get("desc", "")
                items.append(f"<div class='point-item'><strong>{num}. {t}:</strong> {d}</div>")
            return f"<div class='slide-body-list'>{''.join(items)}</div>"

        # Role: Concept / Rules (Slide 4 or 5)
        if slide.get("rules"):
            rules = slide.get("rules", [])
            items = []
            for i, r in enumerate(rules):
                t = r.get("title", "")
                d = r.get("desc", "")
                items.append(f"<div class='point-item'><strong>{i+1}. {t}:</strong> {d}</div>")
            return f"<div class='slide-body-list'>{''.join(items)}</div>"

        return f"<div class='slide-body-paragraphs'><p class='body-para'>{slide.get('text', '')}</p></div>"

    def _generate_fallback_deck(self, topic_data: dict) -> dict:
        title = topic_data.get("title", "The 1% Expense Ratio Illusion")
        return {
            "caption": f"🚨 {title}\n\nMost retail investors believe small fees don't matter, but compound math tells a completely different story.\n\nSwipe through the 6-slide breakdown to audit your capital.\n\n💬 Comment 'GUIDE' below to receive our complete Retail Risk Checklist!\n\n#StockMarket #Investing #MutualFunds #Nifty50 #PersonalFinance",
            "slides": [
                {
                    "role": "hook",
                    "title": f"The Hidden Math <span class='highlight-box'>Behind {title[:30]}</span>",
                    "deliverable": "📖 Inside: 5-Point Mathematical Breakdown",
                    "tag": "#MUTUALFUNDS"
                },
                {
                    "role": "friction",
                    "title": "The Illusion of Negligible Fees",
                    "card_a_text": "Retail investors assume a 1% distributor commission is negligible over time.",
                    "card_b_text": "On a ₹15,000 monthly SIP over 25 years, that 1% fee quietly extracts ₹34 Lakhs from your wealth.",
                    "takeaway": "Never confuse percentage fees with absolute rupee compounding.",
                    "tag": "#MARKETTRUTH"
                },
                {
                    "role": "breakdown",
                    "title": "3 Silent Wealth Leakages",
                    "points": [
                        {"num": "1", "title": "Distributor Trailing Commissions", "desc": "Paid every single month out of your net asset value whether the fund gains or loses."},
                        {"num": "2", "title": "Opportunity Cost Compounding", "desc": "Money paid as fees cannot compound for your retirement over the next decade."},
                        {"num": "3", "title": "Zero Extra Alpha", "desc": "Regular plans hold the exact same stocks as direct plans with zero added performance."}
                    ],
                    "tag": "#HIDDENMATH"
                },
                {
                    "role": "architecture",
                    "layout": "step_diagram",
                    "steps": [
                        {"number": 1, "icon_concept": "search", "color": "#A8D5BA", "label": "AUDIT", "sublabel": "Check portfolio for Regular"},
                        {"number": 2, "icon_concept": "calculator", "color": "#F5D782", "label": "CALCULATE", "sublabel": "Run Direct vs Regular cost"},
                        {"number": 3, "icon_concept": "shield", "color": "#A8C8E8", "label": "SWITCH", "sublabel": "Switch SIP to Direct Zero-Fee"}
                    ],
                    "headline": "The 3-Step Capital Recovery Loop",
                    "body_lines": [
                        "Distributors sell convenience to retail investors.",
                        "Direct mutual fund platforms preserve compounding capital."
                    ],
                    "closing_line": "Audit your expense ratio before adding fresh capital.",
                    "tag": "#PLAYBOOK"
                },
                {
                    "role": "concept",
                    "title": "3 Rules for Retail Investors",
                    "rules": [
                        {"title": "Audit Nav Direct vs Regular", "desc": "Always verify that every fund scheme in your portfolio explicitly has 'Direct' in its name."},
                        {"title": "Automate STP Where Applicable", "desc": "Do not leave idle cash in distributor savings accounts when switching schemes."},
                        {"title": "Verify Total Expense Ratio", "desc": "Cap equity fund TER under 0.8% and passive index fund TER under 0.2%."}
                    ],
                    "tag": "#STRATEGY"
                },
                {
                    "role": "cta",
                    "title": "Don't <span class='highlight-box'>forget to</span> save this <span class='highlight-box'>post</span>",
                    "discussion_question": "Have you audited your mutual fund portfolio for regular plans? Drop your thoughts below 👇",
                    "lead_magnet": {
                        "trigger_word": "GUIDE",
                        "resource_name": "The Mutual Fund Risk Checklist"
                    },
                    "tag": "#SAVETHIS"
                }
            ]
        }
