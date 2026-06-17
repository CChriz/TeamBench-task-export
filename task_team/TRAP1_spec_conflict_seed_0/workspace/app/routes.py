"""
Route handlers for marketplace_api.

NOTE: Input validation is currently missing on all endpoints.
The Planner has determined which endpoints require strict validation
and which must remain relaxed for backward compatibility.
"""
from flask import request, jsonify, Blueprint
from app.config import ALLOWED_REPORT_TYPES
from app.validators import (
    validate_user, validate_item, validate_order, validate_report,
)

bp = Blueprint("api", __name__)


# ── Endpoints that need strict validation added ───────────────────────────────

@bp.route("/users", methods=["POST"])
def create_user():
    """Create a new user. Requires name and a valid email."""
    data = request.get_json(silent=True) or {}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({"status": "created", "name": data.get("name"), "email": data.get("email")}), 201


@bp.route("/items", methods=["POST"])
def create_item():
    """Create a new item. Requires name and positive price."""
    data = request.get_json(silent=True) or {}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({"status": "created", "name": data.get("name"), "price": data.get("price")}), 201


@bp.route("/orders", methods=["POST"])
def create_order():
    """Create a new order. Requires user_id, item_id, quantity >= 1."""
    data = request.get_json(silent=True) or {}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({"status": "created", "user_id": data.get("user_id"), "item_id": data.get("item_id"), "quantity": data.get("quantity")}), 201


@bp.route("/reports", methods=["POST"])
def create_report():
    """Create a report. Requires report_type in summary, detailed, audit, export."""
    data = request.get_json(silent=True) or {}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({"status": "created", "report_type": data.get("report_type")}), 201


# ── Endpoints that must remain relaxed (do NOT add strict validation) ─────────

@bp.route("/batch-import", methods=["POST"])
def batch_import():
    """
    Bulk import records from CSV.
    INTENTIONALLY RELAXED: accepts partial records (missing optional fields).
    See CHANGELOG.md for rationale.
    """
    body = request.get_data(as_text=True)
    lines = [l for l in body.splitlines() if l.strip()]
    return jsonify({"status": "imported", "rows": max(0, len(lines) - 1)}), 200


@bp.route("/search", methods=["GET"])
def search():
    """
    Search records by query string.
    INTENTIONALLY RELAXED: accepts wildcard * in q parameter.
    See CHANGELOG.md for rationale.
    """
    q = request.args.get("q", "")
    return jsonify({"status": "ok", "query": q, "results": []}), 200


@bp.route("/webhooks", methods=["POST"])
def receive_webhook():
    """
    Receive webhook event from registered partner.
    INTENTIONALLY RELAXED: accepts arbitrary JSON payload.
    See CHANGELOG.md for rationale.
    """
    payload = request.get_json(silent=True) or {}
    return jsonify({"status": "received", "keys": list(payload.keys())}), 200


def register_routes(app):
    app.register_blueprint(bp)
