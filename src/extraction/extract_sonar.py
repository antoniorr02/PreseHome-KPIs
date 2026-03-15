import os
import requests
import json
from datetime import UTC, datetime
from dotenv import load_dotenv

load_dotenv()

SONAR_URL = os.getenv("SONAR_URL")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")
PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY")

def extract_metrics():

    endpoint = f"{SONAR_URL}/api/measures/component"

    params = {
        "component": PROJECT_KEY,
        "metricKeys": "bugs,vulnerabilities,code_smells,coverage"
    }

    headers = {
        "Authorization": f"Bearer {SONAR_TOKEN}"
    }

    response = requests.get(endpoint, params=params, headers=headers)
    response.raise_for_status()

    data = response.json()

    metrics = {}

    for measure in data["component"]["measures"]:
        metrics[measure["metric"]] = measure["value"]

    expected_metrics = ["bugs", "vulnerabilities", "code_smells", "coverage"]

    clean_metrics = {}

    for metric in expected_metrics:
        value = metrics.get(metric, 0)
        clean_metrics[metric] = float(value)

    result = {
        "project": "PreseHome",
        "metrics": {k: int(v) for k, v in clean_metrics.items()},
        "timestamp": datetime.now(UTC).isoformat()
    }

    return result


def save_raw_dataset(metrics):

    with open("data/raw/sonar_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)


if __name__ == "__main__":

    metrics = extract_metrics()
    print(metrics)
    save_raw_dataset(metrics)

    print("Metrics extracted successfully.")