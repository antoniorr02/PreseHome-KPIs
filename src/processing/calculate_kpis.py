
from kpi_model import load_weights

weights = load_weights()

def formula_description():
    """
    Formula:
    1. Normalize each metric to 0-10 scale (e.g. coverage is inverted)
    2. Multiply each normalized metric by its weight
    3. Sum all weighted metrics to obtain final KPI (0-10)
    """
    pass