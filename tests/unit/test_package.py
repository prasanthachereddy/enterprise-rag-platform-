import enterprise_rag


def test_package_exposes_version() -> None:
    assert enterprise_rag.__version__ == "0.1.0"