"""Exercise story persistence under the API's concurrent worker pattern."""
from concurrent.futures import ThreadPoolExecutor

from resume import store as resume_store
def test_parallel_story_saves_do_not_lose_data_or_share_libraries(tmp_path, monkeypatch):
    monkeypatch.setenv("WAYPOINT_STORY_DB", str(tmp_path / "stories.sqlite3"))
    owners = [resume_store.key_digest(resume_store.create_library()) for _ in range(2)]

    def save(index):
        data = {
            "answers": {"context": f"Project {index}", "problem": "Manual reporting",
                        "actions": "Built a report", "tools": "Python", "outcome": ""},
            "organization": "",
            "dates": "",
            "narrative": f"Project {index}: built a report.",
        }
        return resume_store.create_story(owners[index % 2], data)

    with ThreadPoolExecutor(max_workers=8) as workers:
        saved = list(workers.map(save, range(24)))

    assert len({story["id"] for story in saved}) == 24
    for owner_index, owner in enumerate(owners):
        persisted = resume_store.list_stories(owner)
        assert {story["id"] for story in persisted} == {
            story["id"] for index, story in enumerate(saved) if index % 2 == owner_index
        }
        assert {story["answers"]["context"] for story in persisted} == {
            f"Project {index}" for index in range(24) if index % 2 == owner_index
        }
