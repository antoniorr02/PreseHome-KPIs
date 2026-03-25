import json
from kpi_model import load_weights
from normalize_metrics import normalize_metrics

weights = load_weights()

def calculate_kpi(normalized: dict, weights: dict) -> float:

    total_weight = sum(weights.values())
    if not (0.99 <= total_weight <= 1.01):
        print(f"WARNING: Weights sum to {total_weight:.4f}, expected 1.0")

    weighted_sum = sum(
        normalized[metric] * weight
        for metric, weight in weights.items()
        if metric in normalized
    )

    return round(max(0.0, min(10.0, weighted_sum)), 4)


def formula_description():

    print("Loaded KPI weights:", weights)

    with open("data/raw/sonar_metrics.json", "r") as f:
        data = json.load(f)

    raw_metrics = data["metrics"]

    normalized = normalize_metrics(raw_metrics)
    print("Normalized metrics:", normalized)

    kpi_score = calculate_kpi(normalized, weights)
    print(f"KPI Score: {kpi_score} / 10")

if __name__ == "__main__":
    formula_description()