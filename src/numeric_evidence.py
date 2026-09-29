"""Conservative, exact financial metric evidence matching for carousel copy."""
import html
import re

_METRIC = re.compile(r'(?<![\w#])(?P<currency>[₹$])?\s*(?P<number>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>%|percent(?:age)?|bps|basis\s+points?|crores?|cr|lakhs?|lacs?|million|billion|years?|months?|days?)?(?![\w])', re.I)
_UNITS = {"crores":"crore", "cr":"crore", "lakhs":"lakh", "lacs":"lakh", "percent":"%", "percentage":"%", "basispoint":"bps", "basispoints":"bps", "years":"year", "months":"month", "days":"day"}

def extract_metrics(text):
    text = html.unescape(re.sub(r'<[^>]*>', ' ', str(text)))
    result = set()
    for match in _METRIC.finditer(text):
        number = match.group('number').replace(',', '')
        if '.' in number:
            number = number.rstrip('0').rstrip('.')
        unit = re.sub(r'\s+', '', (match.group('unit') or '').lower())
        unit = _UNITS.get(unit, unit)
        currency = match.group('currency') or ''
        if not unit and not currency:
            # Exclude slide enumeration, but keep all potentially consequential
            # larger numbers and exact four-digit years.
            if float(number) <= 9:
                continue
        result.add(currency + number + unit)
    return result

def collect_slide_copy(slides):
    def copy(value):
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return ' '.join(copy(v) for k, v in value.items() if k not in
                            {'slide_index','role','tag','badge','status','archetype'})
        if isinstance(value, list):
            return ' '.join(copy(v) for v in value)
        return ''
    return ' '.join(copy(slide) for slide in slides)
