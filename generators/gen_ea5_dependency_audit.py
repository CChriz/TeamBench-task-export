"""Parameterized generator for EA5: Dependency Audit."""
from __future__ import annotations
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


DEPS_VARIANTS = [
    {"werkzeug": "2.3.0", "requests": "2.28.0", "pillow": "9.5.0", "crypto": "41.0.0", "yaml": "5.4.0"},
    {"werkzeug": "2.2.0", "requests": "2.27.0", "pillow": "9.3.0", "crypto": "40.0.0", "yaml": "5.3.0"},
    {"werkzeug": "2.1.0", "requests": "2.26.0", "pillow": "9.1.0", "crypto": "39.0.0", "yaml": "5.1.0"},
]


class Generator(TaskGenerator):
    task_id = "EA5_dependency_audit"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        deps = DEPS_VARIANTS[seed % len(DEPS_VARIANTS)]
        workspace_files = self._make_workspace(deps)
        spec_md = open(__file__.replace("gen_ea5_dependency_audit.py", "../tasks/EA5_dependency_audit/spec.md")).read()
        brief_md = open(__file__.replace("gen_ea5_dependency_audit.py", "../tasks/EA5_dependency_audit/brief.md")).read()
        return GeneratedTask(
            task_id="EA5_dependency_audit",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={"cve_count": 0, "api_changes": 2, "seed": seed},
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security"},
        )

    def _make_workspace(self, deps: dict) -> dict:
        files = {}
        files["app/__init__.py"] = ""

        files["requirements.txt"] = f"""Werkzeug=={deps['werkzeug']}
requests=={deps['requests']}
Pillow=={deps['pillow']}
cryptography=={deps['crypto']}
PyYAML=={deps['yaml']}
flask==3.0.0
pytest==8.0.0
"""

        files["app/image_processor.py"] = """\"\"\"Image processing utilities.\"\"\"
from PIL import Image


def resize_image(img_path: str, width: int, height: int) -> Image.Image:
    \"\"\"Resize an image using high-quality resampling.\"\"\"
    img = Image.open(img_path)
    resized = img.resize((width, height), Image.ANTIALIAS)
    return resized


def thumbnail(img_path: str, max_size: int) -> Image.Image:
    \"\"\"Create a thumbnail.\"\"\"
    img = Image.open(img_path)
    img.thumbnail((max_size, max_size), Image.ANTIALIAS)
    return img
"""

        files["app/crypto_utils.py"] = """\"\"\"Cryptography utilities.\"\"\"
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_key() -> bytes:
    return Fernet.generate_key()


def encrypt(data: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(data)


def generate_rsa_key():
    \"\"\"Generate an RSA private key pair.\"\"\"
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
"""

        files["app/routes.py"] = """\"\"\"Flask application routes.\"\"\"
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    \"\"\"Health check endpoint.\"\"\"
    return jsonify({"status": "ok"})
"""

        files["app/api_client.py"] = """\"\"\"HTTP client utilities.\"\"\"
import requests


def fetch_resource(url: str) -> dict:
    \"\"\"Fetch a remote resource and return parsed JSON.\"\"\"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
"""

        files["app/config_loader.py"] = """\"\"\"YAML configuration loader.\"\"\"
import yaml


def load_config(path: str) -> dict:
    \"\"\"Load configuration from a YAML file.\"\"\"
    with open(path) as f:
        return yaml.safe_load(f)
"""

        files["tests/__init__.py"] = ""
        files["tests/test_crypto.py"] = """\"\"\"Tests for crypto utilities.\"\"\"


def test_encrypt_decrypt():
    from app.crypto_utils import generate_key, encrypt
    key = generate_key()
    data = b"hello world"
    encrypted = encrypt(data, key)
    assert encrypted != data
"""

        return files
