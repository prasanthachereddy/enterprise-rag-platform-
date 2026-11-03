"""Call the IAM-protected API: sign each request with your AWS credentials (SigV4)."""

from typing import Any

import requests


def sign_headers(method: str, url: str, body: str, session: Any, region: str) -> dict[str, str]:
    """Return the headers (including Authorization) for one signed API call."""
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    credentials = session.get_credentials().get_frozen_credentials()
    request = AWSRequest(
        method=method, url=url, data=body, headers={"Content-Type": "application/json"}
    )
    SigV4Auth(credentials, "execute-api", region).add_auth(request)
    return {name: str(value) for name, value in request.headers.items()}


def call_api(method: str, url: str, body: str, session: Any, region: str) -> requests.Response:
    headers = sign_headers(method, url, body, session, region)
    return requests.request(method, url, data=body or None, headers=headers, timeout=30)