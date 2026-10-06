"""End-to-end editorial composition against a fake model: no network, no keys."""
import pytest

from conftest import FakeClient, good_deck
from src.editorial_engine import EditorialEngine

TOPIC = {"title": "Bank changes loan terms", "raw_text": "Bank changes loan terms. EMI stays ₹10,000.",
         "source": "Test Wire", "numbers_detected": ["₹10,000"]}


def make(replies):
    ed = EditorialEngine(api_key="")
    ed.client = FakeClient(replies)
    ed.thinker.client = None
    return ed


def test_normalize_accepts_alternate_body_key():
    ed = make([good_deck()])
    slides = good_deck()["slides"]
    slides[1] = {"role": "value_1", "title": "Check the actual term 1", "body": "Read the lender notice first"}
    out = ed._normalize_slides(slides, TOPIC)
    assert out[1]["card_text"].startswith("Read the lender notice")


def test_normalize_rejects_slide_without_any_body():
    ed = make([good_deck()])
    slides = good_deck()["slides"]
    slides[1] = {"role": "value_1", "title": "Check the actual term 1"}
    with pytest.raises(ValueError):
        ed._normalize_slides(slides, TOPIC)


def test_compose_carousel_happy_path():
    ed = make([good_deck()])
    deck = ed.compose_carousel(TOPIC, "brief text")
    assert len(deck["slides"]) == 8
    assert deck["slides"][0]["role"] == "hook" and deck["slides"][-1]["role"] == "bookmark_save"
    assert deck["fact_check_status"].startswith("verified")
    # prompt was rendered with the topic and without raising (guards f-string crashes)
    assert any("Bank changes loan terms" in str(p) for p in ed.client.models.prompts)


def test_compose_carousel_fails_closed_on_invented_numbers():
    bad = good_deck(extra_text="You will earn ₹99,999 in 10 years")
    ed = make([bad])
    with pytest.raises(ValueError):
        ed.compose_carousel(TOPIC, "brief text")


def test_compose_carousel_repairs_after_one_bad_draft():
    bad = good_deck(extra_text="You will earn ₹99,999")
    ed = make([bad, good_deck()])
    deck = ed.compose_carousel(TOPIC, "brief text")
    assert deck["fact_check_status"] in ("verified_after_repair", "verified_pass")


def test_draft_prompts_render():
    ed = make([good_deck()])
    ed._generate_draft(TOPIC, "brief")
    ed._generate_draft_gemma(TOPIC, "brief")
    assert len(ed.client.models.prompts) >= 2
