FROM python:3.11-slim

RUN pip install --no-cache-dir bandit ruff pylint mypy semgrep

RUN useradd -m -u 10002 agent
USER agent
WORKDIR /
