import json

def remember(
    key: str, value: str, path: str = "memory.json"
) -> None:
    if key is None or key.strip() == "":
        raise ValueError("Key cannot be None or empty.")
    
    try:
        with open(path, "r", encoding="utf-8") as file:
            memory = json.load(file)
    except FileNotFoundError:
        memory = {}

    if not isinstance(memory, dict):
        raise ValueError("Memory file is not a valid JSON object.")

    memory[key] = value
    with open(path, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)

def recall(
    key: str, path: str = "memory.json"
) -> str:
    if key is None or key.strip() == "":
        raise ValueError("Key cannot be None or empty.")
    
    try:
        with open(path, "r", encoding="utf-8") as file:
            memory = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"Memory file '{path}' not found.")

    if not isinstance(memory, dict):
            raise ValueError("Memory file is not a valid JSON object.")
    
    result = memory.get(key)
    if result is None:
        raise ValueError(f"Key '{key}' not found in memory.")
    return result