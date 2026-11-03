import boto3

from enterprise_rag.cloud.signing import sign_headers


def test_signed_headers_carry_a_sigv4_authorization() -> None:
    session = boto3.Session(
        aws_access_key_id="AKIAEXAMPLE", aws_secret_access_key="example", region_name="ap-south-1"
    )
    url = "https://abc.execute-api.ap-south-1.amazonaws.com/status?key=x"
    headers = sign_headers("GET", url, "", session, "ap-south-1")
    assert headers["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIAEXAMPLE/")
    assert "execute-api" in headers["Authorization"]
    assert "X-Amz-Date" in headers