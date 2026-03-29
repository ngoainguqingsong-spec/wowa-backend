# wowa/core/tool_registry.py
import json
import os

TOOL_REGISTRY_FILE = "storage/tool_registry.json"

def load_registry():
    if not os.path.exists(TOOL_REGISTRY_FILE):
        return {}
    with open(TOOL_REGISTRY_FILE, "r") as f:
        return json.load(f)

def save_registry(registry):
    os.makedirs(os.path.dirname(TOOL_REGISTRY_FILE), exist_ok=True)
    with open(TOOL_REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)

def register_tool(spec: dict):
    registry = load_registry()
    name = spec.get("name")
    if not name:
        raise ValueError("Tool name required")
    registry[name] = spec
    save_registry(registry)
    return True

def get_tool(name: str):
    registry = load_registry()
    return registry.get(name)