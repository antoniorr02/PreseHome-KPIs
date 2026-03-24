
METRICS = ["bugs", "vulnerabilities", "code_smells", "coverage"]

DEFAULT_WEIGHTS = {
    "bugs": 0.3,
    "vulnerabilities": 0.3,
    "code_smells": 0.2,
    "coverage": 0.2
}

def formula_description():
    """
    Formula:
    1. Normalize each metric to 0-10 scale (e.g. coverage is inverted)
    2. Multiply each normalized metric by its weight
    3. Sum all weighted metrics to obtain final KPI (0-10)
    """
    pass