import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_weights():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    return config.get("weights", {})

def load_normalization_config():
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    caps = config.get("normalization_caps", {})
    defaults = config.get("missing_value_defaults", {})
    return caps, defaults

if __name__ == "__main__":
    weights = load_weights()
    print("Loaded KPI weights:", weights)

    caps, defaults = load_normalization_config()
    print("Loaded normalization caps:", caps)
    print("Loaded missing-value defaults:", defaults)