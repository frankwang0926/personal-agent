import json

import pytest

from memory import recall, remember


def test_remember_updates_one_fact_and_preserves_others(tmp_path):
    path = str(tmp_path / "memory.json")
    assert remember("project_name", "Mini Agent", path) is None
    assert recall("project_name", path) == "Mini Agent"
    remember("learning_style", "动手学习", path)
    remember("project_name", "Personal Agent", path)
    assert recall("project_name", path) == "Personal Agent"
    assert recall("learning_style", path) == "动手学习"
    remember("optional_note", "", path)
    assert recall("optional_note", path) == ""


def test_recall_missing_file_or_key_raises_without_writing(tmp_path):
    path = tmp_path / "memory.json"
    with pytest.raises(ValueError):
        recall("unknown", str(path))
    assert not path.exists()

    remember("project_name", "Mini Agent", str(path))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        recall("unknown", str(path))
    assert path.read_bytes() == before


@pytest.mark.parametrize("key", ["", "  \t"])
def test_memory_rejects_blank_keys(tmp_path, key):
    path = tmp_path / "memory.json"
    with pytest.raises(ValueError):
        remember(key, "value", str(path))
    with pytest.raises(ValueError):
        recall(key, str(path))
    assert not path.exists()


@pytest.mark.parametrize("operation", ["remember", "recall"])
def test_memory_rejects_non_object_file_without_replacing_it(tmp_path, operation):
    path = tmp_path / "memory.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        if operation == "remember":
            remember("key", "value", str(path))
        else:
            recall("key", str(path))
    assert path.read_text(encoding="utf-8") == "[]"


@pytest.mark.parametrize("operation", ["remember", "recall"])
def test_memory_preserves_malformed_file_and_propagates_error(tmp_path, operation):
    path = tmp_path / "memory.json"
    path.write_text("{bad json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        if operation == "remember":
            remember("key", "value", str(path))
        else:
            recall("key", str(path))
    assert path.read_text(encoding="utf-8") == "{bad json"
