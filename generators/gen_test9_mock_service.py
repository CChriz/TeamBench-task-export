"""
Parameterized generator for TEST9: Mock-Based API Testing.

Each seed produces:
  - Different API endpoint URLs and function names
  - A service.py with 3 external API calls (one missing error handling)
  - Different response shapes
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

API_CONFIGS = [
    {
        "user_fn": "get_user",
        "weather_fn": "get_weather",
        "notify_fn": "send_notification",
        "user_url": "https://api.users.example.com/v1/users",
        "weather_url": "https://api.weather.example.com/v2/current",
        "notify_url": "https://api.notify.example.com/v1/send",
    },
    {
        "user_fn": "fetch_profile",
        "weather_fn": "fetch_forecast",
        "notify_fn": "push_alert",
        "user_url": "https://users.service.io/api/profiles",
        "weather_url": "https://weather.service.io/api/forecast",
        "notify_url": "https://alerts.service.io/api/push",
    },
    {
        "user_fn": "load_account",
        "weather_fn": "load_conditions",
        "notify_fn": "dispatch_message",
        "user_url": "https://accounts.internal.dev/api/v3/accounts",
        "weather_url": "https://weather.internal.dev/api/v1/conditions",
        "notify_url": "https://messaging.internal.dev/api/v2/dispatch",
    },
]


class Generator(TaskGenerator):
    task_id = "TEST9_mock_service"
    domain = "testing"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        config = API_CONFIGS[seed % len(API_CONFIGS)]

        workspace_files = {
            "service.py": self._make_service(config),
            "requirements.txt": "requests>=2.28.0\npytest>=7.0.0\n",
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
                "api_functions": [config["user_fn"], config["weather_fn"], config["notify_fn"]],
                "timeout_function": config["notify_fn"],
                "user_url": config["user_url"],
                "weather_url": config["weather_url"],
                "notify_url": config["notify_url"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "medium", "category": "Testing"},
        )

    def _make_service(self, config: dict) -> str:
        return f'''"""Service module that calls 3 external APIs."""
import requests


BASE_USER_URL = "{config["user_url"]}"
BASE_WEATHER_URL = "{config["weather_url"]}"
BASE_NOTIFY_URL = "{config["notify_url"]}"


def {config["user_fn"]}(user_id: str) -> dict:
    """Fetch user profile from the user API."""
    response = requests.get(f"{{BASE_USER_URL}}/{{user_id}}", timeout=10)
    response.raise_for_status()
    return response.json()


def {config["weather_fn"]}(city: str) -> dict:
    """Fetch current weather for a city."""
    response = requests.get(BASE_WEATHER_URL, params={{"city": city}}, timeout=10)
    response.raise_for_status()
    return response.json()


def {config["notify_fn"]}(user_id: str, message: str) -> dict:
    """Send a notification to a user.

    BUG: No error handling for timeout/connection errors.
    Should catch requests.exceptions.Timeout and requests.exceptions.ConnectionError
    and return {{"status": "error", "reason": "timeout"}} instead of crashing.
    """
    response = requests.post(
        BASE_NOTIFY_URL,
        json={{"user_id": user_id, "message": message}},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def process_user_weather(user_id: str, city: str) -> dict:
    """Get user info and weather, then notify them."""
    user = {config["user_fn"]}(user_id)
    weather = {config["weather_fn"]}(city)
    msg = f"Hi {{user.get(\'name\', \'User\')}}, weather in {{city}}: {{weather.get(\'temp\', \'?\')}}F"
    result = {config["notify_fn"]}(user_id, msg)
    return {{"user": user, "weather": weather, "notification": result}}
'''
