import json
import uuid

import pytest

import task as task_store


def test_list_tasks_missing_file_is_empty_without_creating_file(tmp_path):
    path = tmp_path / "tasks.json"
    assert task_store.list_tasks(str(path)) == []
    assert not path.exists()


@pytest.mark.parametrize("contents", ['{"wrong":"object"}', "[unfinished"])
def test_list_tasks_rejects_invalid_storage_without_writing(tmp_path, contents):
    path = tmp_path / "tasks.json"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        task_store.list_tasks(str(path))
    assert path.read_text(encoding="utf-8") == contents


def test_create_task_returns_persisted_record(tmp_path):
    path = tmp_path / "tasks.json"
    result = task_store.create_task("  Review my agent loop  ", str(path))
    assert isinstance(result, dict)
    assert result["title"] == "Review my agent loop"
    assert result["status"] == "open"
    assert uuid.UUID(result["id"]).version == 4
    assert json.loads(path.read_text(encoding="utf-8")) == [result]


def test_create_task_preserves_existing_tasks_and_allows_duplicate_titles(tmp_path):
    path = tmp_path / "tasks.json"
    task_store.create_task("Review", str(path))
    first = json.loads(path.read_text(encoding="utf-8"))[0]
    task_store.create_task("Review", str(path))
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert len(saved) == 2
    assert saved[0] == first
    assert saved[0]["id"] != saved[1]["id"]


def test_create_task_rejects_blank_title_without_changing_file(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        task_store.create_task("  \t", str(path))
    assert path.read_text(encoding="utf-8") == "[]"


def test_failed_task_serialization_preserves_existing_file(tmp_path, monkeypatch):
    path = tmp_path / "tasks.json"
    path.write_text("[]", encoding="utf-8")
    before = path.read_bytes()

    def partial_write_then_fail(data, file, **kwargs):
        file.write("[partial")
        raise OSError("Simulated write failure")

    monkeypatch.setattr(task_store.json, "dump", partial_write_then_fail)
    with pytest.raises(OSError, match="Simulated write failure"):
        task_store.create_task("Review", str(path))
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "initial_status,changes,expected_title,expected_status",
    [
        ("open", {"title": "  Renamed  "}, "Renamed", "open"),
        ("open", {"status": "done"}, "Original", "done"),
        ("done", {"status": "done"}, "Original", "done"),
    ],
)
def test_update_only_supplied_fields(
    tmp_path, initial_status, changes, expected_title, expected_status
):
    path = tmp_path / "tasks.json"
    original = {"id": "target", "title": "Original", "status": initial_status}
    other = {"id": "other", "title": "Keep", "status": "open"}
    path.write_text(json.dumps([original, other]), encoding="utf-8")

    result = task_store.update_task("target", path=str(path), **changes)

    expected = {"id": "target", "title": expected_title, "status": expected_status}
    assert result == expected
    assert json.loads(path.read_text(encoding="utf-8")) == [expected, other]


def test_update_both_fields_returns_persisted_task(tmp_path):
    path = tmp_path / "tasks.json"
    original = task_store.create_task("Original", str(path))
    result = task_store.update_task(
        original["id"], title="  Renamed  ", status="done", path=str(path)
    )
    assert result == {"id": original["id"], "title": "Renamed", "status": "done"}
    assert json.loads(path.read_text(encoding="utf-8")) == [result]


def test_update_requires_at_least_one_change_without_writing(tmp_path):
    path = tmp_path / "tasks.json"
    original = task_store.create_task("Original", str(path))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        task_store.update_task(original["id"], path=str(path))
    assert path.read_bytes() == before


def test_update_unknown_id_preserves_file(tmp_path):
    path = tmp_path / "tasks.json"
    task_store.create_task("Original", str(path))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        task_store.update_task("unknown", title="Renamed", status="done", path=str(path))
    assert path.read_bytes() == before


def test_failed_update_replacement_preserves_file_and_cleans_temporary(tmp_path, monkeypatch):
    path = tmp_path / "tasks.json"
    original = task_store.create_task("Original", str(path))
    before = path.read_bytes()

    def fail_replace(source, destination):
        raise OSError("Simulated replacement failure")

    monkeypatch.setattr(task_store.os, "replace", fail_replace)
    with pytest.raises(OSError, match="Simulated replacement failure"):
        task_store.update_task(
            original["id"], title="Renamed", status="done", path=str(path)
        )
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
