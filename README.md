# Enterprise Internal Policy & Operations Knowledge Assistant

A portfolio project that ingests policy and operations documents, indexes them, retrieves
the most relevant passages, and answers questions with source citations.

## Status

Built in six phases (0-5), local first and cloud later. A component is described as
deployed only after it has actually been deployed and verified.

## Local setup (Windows CMD)

    py -3.11 -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
    copy .env.example .env
    python -m pytest -q

## Security

Never commit `.env`, credentials, or real company documents. Use synthetic or public
documents only.