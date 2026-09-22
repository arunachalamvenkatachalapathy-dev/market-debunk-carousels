import sys
from pathlib import Path

# Add project root to path
repo_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_path))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.research_engine import ResearchEngine

def test_scoring():
    engine = ResearchEngine()

    # Case 1: High-Intent Retail F&O Losses
    retail_fno_cand = {
        "title": "SEBI F&O Report: 93% of retail traders suffer average loss of ₹50,000 in options trading trap",
        "snippet": "Market regulator SEBI exposed shocking numbers showing retail investors lose crores while algo syndicates extract liquidity.",
        "numbers_detected": ["93%", "₹50,000"],
        "age_hours": 3.0
    }
    score_fno, cat_fno = engine.calculate_viral_demand_score(retail_fno_cand, ["nifty options expiry", "sebi f&o loss"])
    print(f"[TEST 1] Retail F&O Loss -> Score: {score_fno}, Category: {cat_fno}")
    assert score_fno >= 70.0, f"Expected F&O score >= 70, got {score_fno}"
    assert cat_fno != "IRRELEVANT_B2B", f"Should not be IRRELEVANT_B2B: {cat_fno}"

    # Case 2: High-Intent Mutual Fund Drag
    retail_mf_cand = {
        "title": "Mutual Fund Hidden Trap: How 1% extra expense ratio erodes ₹34 Lakhs from your SIP compounding",
        "snippet": "Beware of regular plans in mutual funds where distributor commission quietly wipes out 25% of terminal wealth.",
        "numbers_detected": ["1%", "₹34 Lakhs", "25%"],
        "age_hours": 6.0
    }
    score_mf, cat_mf = engine.calculate_viral_demand_score(retail_mf_cand, ["mutual fund direct vs regular", "sip calculator"])
    print(f"[TEST 2] Retail Mutual Fund Trap -> Score: {score_mf}, Category: {cat_mf}")
    assert score_mf >= 70.0, f"Expected MF score >= 70, got {score_mf}"

    # Case 3: B2B Foreign Law Firm / China STAR Market
    b2b_cand = {
        "title": "DeHeng Law Firm advises Enflame on STAR Market RMB corporate debt restructuring SEC filing",
        "snippet": "Foreign legal counsel completes municipal bond advisory for South Korea battery X overseas listing.",
        "numbers_detected": ["100M", "5%"],
        "age_hours": 2.0
    }
    score_b2b, cat_b2b = engine.calculate_viral_demand_score(b2b_cand, [])
    print(f"[TEST 3] Irrelevant B2B -> Score: {score_b2b}, Category: {cat_b2b}")
    assert score_b2b == 0.0, f"Expected 0.0 for B2B, got {score_b2b}"
    assert cat_b2b == "IRRELEVANT_B2B", f"Expected IRRELEVANT_B2B, got {cat_b2b}"

    # Case 4: Generic Corporate News without Retail Terms (Penalized 0.5x)
    generic_cand = {
        "title": "Steel manufacturer reports annual machinery maintenance schedule",
        "snippet": "Factory operations continue with steady output across central divisions.",
        "numbers_detected": ["2"],
        "age_hours": 12.0
    }
    score_gen, cat_gen = engine.calculate_viral_demand_score(generic_cand, [])
    print(f"[TEST 4] Generic Business News -> Score: {score_gen}, Category: {cat_gen}")
    assert score_gen < 40.0, f"Generic news should be heavily penalized (<40), got {score_gen}"

    print("\n✅ ALL TOPIC SCORING UNIT TESTS PASSED!")

if __name__ == "__main__":
    test_scoring()
