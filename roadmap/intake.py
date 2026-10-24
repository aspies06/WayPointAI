"""The questions to ask a user before making their roadmap.

A roadmap is only useful if it fits the person's real time, so we never guess
it: generate_roadmap() raises AvailabilityNeeded until these are answered.
QUESTIONS is the single source of truth for any front end (Streamlit form, CLI,
chat); answers_to_context() turns the answers into a validated UserContext.
"""
import re
from datetime import date, datetime, timedelta
from typing import Optional

from .schemas import UserContext

DATE_FORMAT = "MM-DD-YYYY"  # how people type dates; Streamlit: st.date_input(format=DATE_FORMAT)

# Named workloads, so people can pick a feel instead of a number.
WORKLOADS = {
    "light": (4, "Light: about 4 hours a week (an evening or two)"),
    "steady": (8, "Steady: about 8 hours a week (an hour most days)"),
    "intensive": (15, "Intensive: about 15 hours a week (a part-time job)"),
    "full_time": (30, "Full time: about 30 hours a week"),
}

QUESTIONS = [
    {"id": "hours_per_week", "kind": "workload", "required": True,
     "prompt": "How much time can you realistically give this each week without burning out?",
     "help": "Pick a workload or type a number of hours (1-80). Be honest: a plan you can keep beats an ambitious one.",
     "options": {k: label for k, (_, label) in WORKLOADS.items()}},
    {"id": "start_date", "kind": "date", "required": False,
     "prompt": "When can you start?", "format": DATE_FORMAT,
     "help": f"{DATE_FORMAT}, e.g. 11-02-2026. Leave blank to start today."},
    {"id": "target_date", "kind": "date", "required": True,
     "prompt": "When do you want to be ready to apply?", "format": DATE_FORMAT,
     "help": f"{DATE_FORMAT}, e.g. 05-31-2027, or a number of weeks from your start date, e.g. 12."},
    {"id": "budget_usd", "kind": "int", "required": False,
     "prompt": "How much do you want to spend on courses, books and exams, in US dollars?",
     "help": "Any amount, including 0. Leave blank for no set limit. Your plan stays within it, and anything "
             "worth spending more on is pointed out separately."},
]


class AvailabilityNeeded(ValueError):
    """Raised instead of guessing someone's time. Ask QUESTIONS, then retry."""

    def __init__(self, missing: Optional[list[str]] = None):
        self.questions = [q for q in QUESTIONS if not missing or q["id"] in missing]
        super().__init__("Ask the user about their availability first: "
                         + ", ".join(q["id"] for q in self.questions))


def parse_hours(value) -> int:
    if isinstance(value, str) and value.strip().lower() in WORKLOADS:
        return WORKLOADS[value.strip().lower()][0]
    text = str(value).strip().lower().removesuffix("hours").removesuffix("h").strip()
    if not text.isdigit():
        raise ValueError(f"type a number of hours, or one of: {', '.join(WORKLOADS)}")
    hours = int(text)
    if not 1 <= hours <= 80:
        raise ValueError("hours per week must be between 1 and 80")
    return hours


def _parse_budget(value) -> int:
    text = str(value).strip().lstrip("$").replace(",", "")
    if not text.isdigit():
        raise ValueError("enter a whole dollar amount like 150, or leave it blank for no limit")
    return int(text)


def parse_date(value) -> date:
    """MM-DD-YYYY (or MM/DD/YYYY) as typed; date objects (st.date_input) and ISO dates also work."""
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):  # ISO from other programs; unambiguous
        return date.fromisoformat(text)
    try:
        return datetime.strptime(text.replace("/", "-").replace(".", "-"), "%m-%d-%Y").date()
    except ValueError:
        raise ValueError(f"use {DATE_FORMAT}, like 05-31-2027") from None


def parse_target(value, start: date) -> date:
    text = str(value).strip().lower()
    if text.removesuffix("weeks").removesuffix("w").strip().isdigit():
        return start + timedelta(weeks=int(text.removesuffix("weeks").removesuffix("w").strip()))
    try:
        return parse_date(value)
    except ValueError:
        raise ValueError(f"use {DATE_FORMAT}, like 05-31-2027, or a number of weeks like 12") from None


def answers_to_context(answers: dict, background: str = "", today: Optional[date] = None) -> UserContext:
    """Turns raw answers (strings or numbers, as a form gives them) into a UserContext.
    Raises AvailabilityNeeded if a required answer is missing, ValueError if one is invalid."""
    missing = [q["id"] for q in QUESTIONS if q["required"] and answers.get(q["id"]) in (None, "")]
    if missing:
        raise AvailabilityNeeded(missing)
    try:
        start = parse_date(answers["start_date"]) if answers.get("start_date") else (today or date.today())
    except ValueError:
        raise ValueError(f"use {DATE_FORMAT}, like 11-02-2026, or leave it blank to start today") from None
    budget = answers.get("budget_usd")
    return UserContext(
        hours_per_week=parse_hours(answers["hours_per_week"]),
        start_date=start,
        target_date=parse_target(answers["target_date"], start),
        budget_usd=None if budget in (None, "") else _parse_budget(budget),
        background=background,
    )


def ask_cli(background: str = "", input_fn=input, print_fn=print) -> UserContext:
    """Asks the questions in a terminal, re-asking any answer that doesn't parse."""
    answers: dict = {}
    for q in QUESTIONS:
        print_fn(f"\n{q['prompt']}\n  {q['help']}")
        for key, label in q.get("options", {}).items():
            print_fn(f"    {key:10} {label}")
        while True:
            answers[q["id"]] = input_fn("> ").strip()
            try:
                if answers[q["id"]] or q["required"]:
                    answers_to_context({**_placeholders(), **answers})
                break
            except AvailabilityNeeded:
                print_fn("  This one is needed to plan your time.")
            except ValueError as e:
                print_fn(f"  Didn't catch that: {error_message(e)}. Try again.")
    return answers_to_context(answers, background)


def error_message(e: ValueError) -> str:
    """A short, user-readable message for a bad answer (pydantic errors are long)."""
    errors = getattr(e, "errors", None)
    return errors()[0]["msg"].removeprefix("Value error, ") if callable(errors) else str(e)


def _placeholders() -> dict:
    """Valid stand-ins so each answer can be checked on its own while the rest are still blank."""
    return {"hours_per_week": "steady", "target_date": "12"}
