"""Streamlit pieces for WayPointAI: ask about the user's time first, then show
their timeline with everything else kept behind an optional button.

    from roadmap import ui
    ctx = ui.availability_form(background=...)
    if ctx:
        gap_list["user_context"] = ctx.model_dump(mode="json")
        ui.show_roadmap(generate_roadmap(gap_list), gap_names)

Only this module imports Streamlit, so the rest of the package works without it.
"""
from datetime import date, timedelta
from typing import Optional

import streamlit as st

from . import intake
from .render import optional_count, optional_markdown, timeline_markdown
from .schemas import Roadmap, UserContext

CUSTOM = "custom"


def availability_form(key: str = "availability", background: str = "",
                      today: Optional[date] = None) -> Optional[UserContext]:
    """Asks intake.QUESTIONS as a form. Returns the answers once submitted (and on every
    rerun after that, so the roadmap stays on screen), or None until then."""
    today = today or date.today()
    q = {x["id"]: x for x in intake.QUESTIONS}
    with st.form(key):
        st.subheader("First, tell us about your time")
        options = [*intake.WORKLOADS, CUSTOM]
        workload = st.radio(q["hours_per_week"]["prompt"], options, index=1, help=q["hours_per_week"]["help"],
                            format_func=lambda k: intake.WORKLOADS[k][1] if k in intake.WORKLOADS
                            else "Custom: I'll enter my own number")
        custom = st.number_input("Hours per week (if custom)", min_value=1, max_value=80, value=8)
        start = st.date_input(q["start_date"]["prompt"], value=today, min_value=today,
                              format=intake.DATE_FORMAT, help=q["start_date"]["help"])
        target = st.date_input(q["target_date"]["prompt"], value=today + timedelta(weeks=12),
                               min_value=today + timedelta(days=7), format=intake.DATE_FORMAT,
                               help=q["target_date"]["help"])
        budget = st.number_input(q["budget_usd"]["prompt"], min_value=0, value=None, step=25,
                                 placeholder="No limit", help=q["budget_usd"]["help"])
        submitted = st.form_submit_button("Make my roadmap")

    if not submitted:
        return st.session_state.get(f"{key}_answers")
    try:
        ctx = intake.answers_to_context({
            "hours_per_week": custom if workload == CUSTOM else workload,
            "start_date": start, "target_date": target, "budget_usd": budget}, background, today)
    except ValueError as e:
        st.error(intake.error_message(e))
        return None
    st.session_state[f"{key}_answers"] = ctx
    return ctx


def _toggle(state_key: str) -> None:
    st.session_state[state_key] = not st.session_state.get(state_key, False)


def show_roadmap(roadmap: Roadmap, gap_names: Optional[dict[str, str]] = None, key: str = "roadmap") -> None:
    """The timeline is always shown. Items that don't fit the user's time or budget, and gaps
    with nothing in the catalog yet, appear only after the optional button is pressed."""
    st.markdown(timeline_markdown(roadmap, gap_names))
    n = optional_count(roadmap)
    if not n:
        return
    state_key = f"{key}_show_optional"
    shown = st.session_state.get(state_key, False)
    st.button(f"{'Hide' if shown else 'Show'} optional items ({n})", key=f"{key}_optional_button",
              on_click=_toggle, args=(state_key,),
              help="Things that didn't fit your time or budget, kept here in case your plans change.")
    if shown:
        st.markdown(optional_markdown(roadmap, gap_names))
