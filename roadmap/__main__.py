"""python -m roadmap path/to/gap_list.json [--json] [--ask]

Asks for your availability and workload first if the gap list doesn't include
them (or always, with --ask), then prints the roadmap as readable text.
--json prints the raw Roadmap JSON instead, for other programs.
"""
import json
import logging
import sys

from . import generate_roadmap, intake
from .render import to_markdown

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s", stream=sys.stderr)

args = [a for a in sys.argv[1:] if not a.startswith("--")]
flags = {a for a in sys.argv[1:] if a.startswith("--")}
if len(args) != 1 or flags - {"--json", "--ask"}:
    sys.exit(__doc__.strip().splitlines()[0])

with open(args[0]) as f:
    gap_list = json.load(f)

if "--ask" in flags or not gap_list.get("user_context"):
    if not sys.stdin.isatty():
        questions = "\n".join(f"  {q['id']}: {q['prompt']}" for q in intake.QUESTIONS)
        sys.exit(f"Your availability is needed before making a roadmap. Add user_context with:\n{questions}")
    background = (gap_list.get("user_context") or {}).get("background", "")
    print("Before making your roadmap, a few questions about your time.")
    gap_list["user_context"] = intake.ask_cli(background).model_dump(mode="json")

roadmap = generate_roadmap(gap_list)
if "--json" in flags:
    print(roadmap.model_dump_json(indent=2))
else:
    print(to_markdown(roadmap, {g["gap_id"]: g["item"] for g in gap_list["gaps"]}))
