import json
import uuid
import os
import tempfile
from pathlib import Path

def create_task(title: str, path: str = "tasks.json") -> dict:
    task_id = str(uuid.uuid4())
    clean_title = title.strip()

    if not clean_title:
        raise ValueError("Task title cannot be empty.")

    task = {
        "id": task_id,
        "title": clean_title,
        "status": "open"
    }

    try:
        with open(path, "r", encoding="utf-8") as file:
            tasks = json.load(file)
    except FileNotFoundError:
        tasks = []

    if not isinstance(tasks, list):
        raise ValueError("Tasks file must contain a list of tasks.")

    tasks.append(task)

    destination = Path(path)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(tasks, file, ensure_ascii=False, indent=2)

        # The with block has ended, so the temporary file is closed.
        os.replace(temporary_path, destination)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return task

def list_tasks(path: str = "tasks.json") -> list:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def update_task(
    task_id: str,
    title: str | None = None,
    status: str | None = None,
    path: str = "tasks.json",
) -> dict:

    if title is None and status is None:
        raise ValueError("At least one of title or status must be provided.")
     
    try:
        with open(path, "r", encoding="utf-8") as file:
            tasks = json.load(file)
    except FileNotFoundError:
        tasks = []

    if not isinstance(tasks, list):
        raise ValueError("Tasks file must contain a list of tasks.")

    match = next(
        (task for task in tasks if task.get("id") == task_id), 
        None,
    )
    
    if match is None:
        raise ValueError(f"Task with ID {task_id} not found.")

    if title is not None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        match["title"] = clean_title

    if status is not None:
        if status not in ["open", "done"]:
            raise ValueError("Invalid status. Must be one of 'open' and 'done'.")
        match["status"] = status

    destination = Path(path)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(tasks, file, ensure_ascii=False, indent=2)

        # The with block has ended, so the temporary file is closed.
        os.replace(temporary_path, destination)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return match

    