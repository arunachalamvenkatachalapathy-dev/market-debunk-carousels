from src.numeric_evidence import extract_metrics
from src.editorial_engine import EditorialEngine


def engine():
    ed = EditorialEngine(api_key="")
    ed.client = None
    return ed


def test_extract_metrics_units_and_currency():
    m = extract_metrics("Pay ₹1 crore, 15% and 3 years; slide 2 of 8; year 2026")
    assert {"₹1crore", "15%", "3year", "2026"} <= m
    assert "2" not in m and "8" not in m  # slide counters are ignored


def test_percent_is_not_evidence_for_crore():
    ed = engine()
    ok, _ = ed._verify_numeric_facts({"slides": [{"title": "15 crore gain"}], "caption": ""}, {"raw_text": "Returns were 15%."})
    assert ok is False


def test_invented_number_is_rejected():
    ed = engine()
    ok, report = ed._verify_numeric_facts({"slides": [{"title": "₹50,000 from a ₹10,000 deposit"}], "caption": ""},
                                          {"raw_text": "Deposit amount is ₹10,000."})
    assert ok is False and "50000" in report


def test_exact_numbers_pass():
    ed = engine()
    ok, _ = ed._verify_numeric_facts({"slides": [{"title": "₹10,000 deposit"}], "caption": ""},
                                     {"raw_text": "Deposit amount is ₹10,000."})
    assert ok is True


def test_unitless_currency_supported_by_same_figure_with_unit():
    """'₹1 and ₹5 crore thresholds' paraphrases '₹1 crore and ₹5 crore'; it must not fail the gate."""
    ed = engine()
    topic = {"raw_text": "FAST-DS: know the ₹1 crore and ₹5 crore threshold rules"}
    deck = {"slides": [{"title": "Thresholds are ₹1 and ₹5 crore"}], "caption": ""}
    ok, report = ed._verify_numeric_facts(deck, topic)
    assert ok, report


def test_unitless_currency_not_in_source_still_rejected():
    ed = engine()
    topic = {"raw_text": "thresholds of ₹1 crore and ₹5 crore"}
    ok, _ = ed._verify_numeric_facts({"slides": [{"title": "pay ₹7"}], "caption": ""}, topic)
    assert ok is False
