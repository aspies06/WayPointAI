"""python -m roadmap path/to/gap_list.json  ->  prints the roadmap JSON."""
import json
import logging
import sys

from . import generate_roadmap

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)

if len(sys.argv) != 2:
    sys.exit("usage: python -m roadmap path/to/gap_list.json")
with open(sys.argv[1]) as f:
    roadmap = generate_roadmap(json.load(f))
print(roadmap.model_dump_json(indent=2))
