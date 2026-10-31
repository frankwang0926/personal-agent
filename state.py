import json

def load_history(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as file:
            history = json.load(file)
            if isinstance(history, list):
                return history
            else:
                raise ValueError("The loaded history is not a list.")
    except FileNotFoundError:
        return []

def save_history(path: str, history: list) -> None:
    serializable_history = []

    for item in history:
        if isinstance(item, dict):
            serializable_history.append(item)
        else:
            serializable_history.append(item.model_dump(mode="json", exclude_none=True))
    
    
    with open(path, "w", encoding="utf-8") as file:
        json.dump(serializable_history, file, ensure_ascii=False, indent=2)
