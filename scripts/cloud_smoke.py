"""Upload one sample document to the deployed stack and wait for its audit record."""

import json
import sys
import time
from urllib.parse import quote

import boto3
import requests

from enterprise_rag.cloud.signing import call_api
from enterprise_rag.config import project_root

STACK_NAME = "EnterpriseRagIngest"
WAIT_SECONDS = 90


def main() -> None:
    session = boto3.Session()
    region = session.region_name
    if not region:
        raise SystemExit("No AWS region configured. Run: aws configure")
    stack = session.client("cloudformation").describe_stacks(StackName=STACK_NAME)["Stacks"][0]
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stack["Outputs"]}
    api = outputs["ApiUrl"].rstrip("/")

    path = project_root() / "data" / "sample_docs" / "leave_policy.html"
    reply = call_api("POST", f"{api}/uploads", json.dumps({"filename": path.name}), session, region)
    reply.raise_for_status()
    info = reply.json()
    requests.put(info["upload_url"], data=path.read_bytes(), timeout=30).raise_for_status()
    print(f"Uploaded as {info['key']}")

    status_url = f"{api}/status?key={quote(info['key'], safe='')}"
    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline:
        status = call_api("GET", status_url, "", session, region)
        if status.status_code == 200:
            print(json.dumps(status.json(), indent=2))
            return
        if status.status_code != 404:
            raise SystemExit(f"Unexpected reply {status.status_code}")
        time.sleep(3)
    print(f"No audit record after {WAIT_SECONDS} seconds. Check the dead-letter queue.")
    sys.exit(1)


if __name__ == "__main__":
    main()