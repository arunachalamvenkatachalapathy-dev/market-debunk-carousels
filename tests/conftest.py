import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    """Stands in for google.genai client.models. `replies` is a list of strings/exceptions
    consumed in order; the last item repeats. Every prompt is recorded in `prompts`."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def generate_content(self, model=None, contents=None, config=None):
        self.prompts.append(contents)
        item = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item if isinstance(item, str) else json.dumps(item))


class FakeClient:
    def __init__(self, replies):
        self.models = FakeModels(replies)


def good_slides(extra_text="Read the lender notice first"):
    slides = [{"role": "hook", "title": "Will this change your EMI?"}]
    for i in range(1, 7):
        slides.append({"role": f"value_{i}", "title": f"Check the actual term {i}", "card_text": extra_text})
    slides.append({"role": "bookmark_save", "title": "Check your loan terms",
                   "cta_detail": "Check the lender notice before changing your repayment plan. Save this check."})
    return slides


def good_deck(extra_text="Read the lender notice first", caption="Check the notice before you act. What will you check first?"):
    return {"caption": caption, "slides": good_slides(extra_text)}
