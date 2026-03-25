import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_weights():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    return config.get("weights", {})

if __name__ == "__main__":
    weights = load_weights()
    print("Loaded KPI weights:", weights)