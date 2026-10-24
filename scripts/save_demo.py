"""Pre-generate roadmaps for the demo personas and save them to demo/.

    python scripts/save_demo.py swe_intern swe_new_grad swe_mid

Run before a demo. ROADMAP_DEMO=1 then serves these instantly with no model.
Only personalized roadmaps that pass every guardrail are saved; otherwise the
persona keeps the basic roadmap and this script says so. With no names, saves
one persona per level (internship, junior, mid).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roadmap import GapList  # noqa: E402
from roadmap import generate  # noqa: E402

PERSONAS = Path(__file__).resolve().parent.parent / "tests" / "personas"

names = sys.argv[1:] or ["swe_intern", "swe_new_grad", "swe_mid"]
for name in names:
    gl = GapList.model_validate_json((PERSONAS / f"{name}.json").read_text())
    roadmap = generate.generate_roadmap(gl, use_cache=False)
    if roadmap.source != "ai":
        print(f"{name}: personalized roadmap did not pass (got '{roadmap.source}'); not saved. Check the log above.")
        continue
    generate._save(generate.DEMO_DIR, generate.cache_key(gl), roadmap)
    print(f"{name}: saved demo/{generate.cache_key(gl)}.json ({len(roadmap.steps)} steps, {roadmap.total_hours}h)")
