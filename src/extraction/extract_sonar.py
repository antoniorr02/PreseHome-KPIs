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
        "metricKeys": "complexity"
    }

    headers = {
        "Authorization": f"Bearer {SONAR_TOKEN}"
    }

    response = requests.get(endpoint, params=params, headers=headers)
    response.raise_for_status()

    data = response.json()

    print(data)

if __name__ == "__main__":

    metrics = extract_metrics()
