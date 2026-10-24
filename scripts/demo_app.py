"""Try the roadmap UI with a test persona, without the rest of WayPointAI.

    streamlit run scripts/demo_app.py

Pick a persona, answer the time questions, and see the timeline with the
optional items behind a button. Uses the basic roadmap (no model download).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ROADMAP_AI", "0")

import streamlit as st  # noqa: E402

from roadmap import generate_roadmap, ui  # noqa: E402

PERSONAS = Path(__file__).resolve().parent.parent / "tests" / "personas"

st.set_page_config(page_title="WayPointAI roadmap")
st.title("WayPointAI roadmap")

names = sorted(p.stem for p in PERSONAS.glob("*.json") if p.stem != "zero_gaps")
name = st.selectbox("Test persona (stands in for the resume analysis)", names,
                    index=names.index("swe_intern"))
gap_list = json.loads((PERSONAS / f"{name}.json").read_text())
background = gap_list.pop("user_context", {}).get("background", "")
st.caption(f"{gap_list['target_role']['title']}: {len(gap_list['gaps'])} gaps. {background}")

ctx = ui.availability_form(key=f"availability_{name}", background=background)
if ctx:
    gap_list["user_context"] = ctx.model_dump(mode="json")
    ui.show_roadmap(generate_roadmap(gap_list), {g["gap_id"]: g["item"] for g in gap_list["gaps"]},
                    key=f"roadmap_{name}")
