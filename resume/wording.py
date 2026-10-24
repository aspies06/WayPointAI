"""Conservative copy-editing when generative rewriting is unavailable.

These are grammar/terminology transformations, not a substitute for a language
model. Unrecognized wording is retained and the response asks for review.
"""
import re

TERMS = {
    "TikTok Shop": r"\btik\s*tok\s*shop\b",
    "dashboard": r"\bdashbo+ard\b", "Python": r"\bpython\b",
    "Excel": r"\bexcel\b", "SQL": r"\bsql\b", "JavaScript": r"\bjavascript\b",
    "Power BI": r"\bpower\s*bi\b", "KPI": r"\bkpi\b", "KPIs": r"\bkpis\b",
    "API": r"\bapi\b", "APIs": r"\bapis\b", "Git": r"\bgit\b",
}
VERBS = {
    "make": "Developed", "create": "Created", "build": "Built", "develop": "Developed",
    "design": "Designed", "analyze": "Analyzed", "analyse": "Analyzed", "clean": "Cleaned",
    "prepare": "Prepared", "process": "Processed", "implement": "Implemented",
    "test": "Tested", "improve": "Improved", "reduce": "Reduced", "save": "Saved",
    "automate": "Automated", "support": "Supported", "help": "Helped",
    "collaborate": "Collaborated", "use": "Used", "work": "Worked", "write": "Wrote",
    "manage": "Managed", "lead": "Led", "fix": "Fixed", "organize": "Organized",
}


def terminology(text):
    text = " ".join(text.split())
    for replacement, pattern in TERMS.items():
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def copy_edit(text):
    text = terminology(text).rstrip(". ")
    text = re.sub(r"^i\s+", "", text, flags=re.I)
    # Limit tense changes to sentence/clause starts; never remove negation or
    # change phrases such as 'helped', 'planned to', or 'my teammate built'.
    verbs = "|".join(VERBS)
    pattern = rf"(^|[.;]\s+|,\s*|\band\s+)(?:i\s+)?({verbs})\b"
    def tense(match):
        prefix, verb = match.groups()
        replacement = VERBS[verb.lower()]
        return prefix + (replacement if not prefix or prefix.lstrip().startswith((".", ";")) else replacement.lower())
    text = re.sub(pattern, tense, text, flags=re.I)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s+hour\b", lambda m: m[1] + (" hour" if float(m[1]) == 1 else " hours"), text, flags=re.I)
    text = re.sub(r"\bmanually input data time\b", "of manual data entry", text, flags=re.I)
    text = re.sub(r"\bmanual(?:ly)? (?:data input|input data)\b", "manual data entry", text, flags=re.I)
    text = re.sub(r"\b(?<!a )new KPI\b", "a new KPI", text)
    text = re.sub(r"\b(Developed|Created|Built) (Power BI |Tableau )?dashboard\b", r"\1 a \2dashboard", text)
    # Combine short action clauses without changing their attribution.
    text = re.sub(r",\s+(?=(?:" + "|".join(re.escape(v.lower()) for v in VERBS.values()) + r")\b)", " and ", text)
    text = text[:1].upper() + text[1:]
    return text if not text or text[-1] in ".!?" else text + "."


def heading(text):
    text = terminology(text)
    # Existing deliberate capitalization is retained; only rough lowercase titles
    # receive title casing. Short employer acronyms follow 'at'/'for'.
    if text == text.lower():
        text = text.title()
    text = re.sub(r"\b(For|At|Of|And|In)\b", lambda m: m[0].lower(), text)
    text = re.sub(r"\b(for|at) ([A-Za-z]{2,3})\b", lambda m: m[1] + " " + m[2].upper(), text)
    return terminology(text)


def basic_bullets(story):
    answers = story["answers"]
    bullets = []
    for field in ("actions", "outcome"):
        value = answers.get(field, "").strip()
        if value:
            bullets.append({"text": copy_edit(value), "evidence": [{"field": field, "quote": value}]})
    return bullets


def follow_up_questions(stories):
    questions = []
    for story in stories:
        outcome = story["answers"].get("outcome", "")
        if re.search(r"\b\d+\s*(?:hours?|minutes?)\b", outcome, re.I) and not re.search(
            r"\b(?:per|each|every|weekly|monthly|daily|once|one.time|total)\b", outcome, re.I
        ) and re.search(r"\bsav(?:e|ed|ing)\b", outcome, re.I):
            questions.append({"story_id": story["id"], "question":
                "Was the time saved per day, week, month, or for a one-time task? Add the timeframe to your story; it has not been assumed in the draft."})
    return questions
