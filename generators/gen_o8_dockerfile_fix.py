"""
Parameterized generator for O8: Dockerfile Fix.

Each seed produces:
  - Different base image tags, app ports, and app names
  - A broken Dockerfile with 5 issues
  - A simple app.py that listens on a specific port
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

BASE_IMAGES = [
    ("python:3.11-slm", "python:3.11-slim"),   # typo: slm -> slim
    ("python:3.12-slimm", "python:3.12-slim"),  # typo: slimm -> slim
    ("python:3.10-sli", "python:3.10-slim"),    # typo: sli -> slim
]

APP_PORTS = [5000, 8000, 8080, 3000, 9000]
WRONG_PORTS = [80, 443, 8888, 4000, 7000]

APP_NAMES = ["webapp", "api_server", "microservice"]


class Generator(TaskGenerator):
    task_id = "O8_dockerfile_fix"
    domain = "operations"
    difficulty = "easy"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(BASE_IMAGES)

        wrong_image, correct_image = BASE_IMAGES[idx]
        correct_port = APP_PORTS[seed % len(APP_PORTS)]
        wrong_port = WRONG_PORTS[seed % len(WRONG_PORTS)]
        app_name = APP_NAMES[seed % len(APP_NAMES)]

        workspace_files = {
            "Dockerfile": self._make_broken_dockerfile(wrong_image, wrong_port),
            "app.py": self._make_app(correct_port, app_name),
            "requirements.txt": "flask>=2.3.0\nrequests>=2.28.0\n",
        }

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", self.task_id)
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "base_image": correct_image,
                "correct_port": correct_port,
                "wrong_port": wrong_port,
                "app_name": app_name,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "easy", "category": "Operations"},
        )

    def _make_broken_dockerfile(self, wrong_image: str, wrong_port: int) -> str:
        return f"""FROM {wrong_image}

# BUG: No WORKDIR set
# BUG: COPY all before pip install (wrong layer ordering)
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE {wrong_port}

CMD python app.py
"""

    def _make_app(self, port: int, app_name: str) -> str:
        return f'''"""Simple {app_name} application."""
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify({{"status": "ok", "app": "{app_name}"}})


@app.route("/health")
def health():
    return jsonify({{"healthy": True}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port={port})
'''
