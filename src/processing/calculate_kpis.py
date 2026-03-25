
import json
from kpi_model import load_weights
from normalize_metrics import normalize_metrics

weights = load_weights()

def formula_description():
    
    print("Loaded KPI weights:", weights)

    with open("data/raw/sonar_metrics.json", "r") as f:
        data = json.load(f)

    raw_metrics = data["metrics"]

    normalized = normalize_metrics(raw_metrics)
    print("Normalized metrics:", normalized)

    """
    Formula:
    2. Multiply each normalized metric by its weight
    3. Sum all weighted metrics to obtain final KPI (0-10)
    """
    pass

if __name__ == "__main__":
    formula_description()