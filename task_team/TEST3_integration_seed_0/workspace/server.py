#!/usr/bin/env python3
"""
Search Service — working implementation.
Run: python server.py
"""
import uuid
import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

VALID_API_KEY = "search-api-key-def456"
AUTH_HEADER = "X-API-Key"

_documents = {}  # document_id -> document dict


def _check_auth():
    key = request.headers.get(AUTH_HEADER, "")
    if key != VALID_API_KEY:
        return jsonify({"error": "unauthorized", "code": 401}), 401
    return None


def _now():
    return datetime.datetime.utcnow().isoformat() + "Z"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "search_service"}), 200


@app.route("/search", methods=["GET"])
def search():
    err = _check_auth()
    if err:
        return err
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "missing required query param: q"}), 400
    if len(q) > 200:
        return jsonify({"error": "query too long (max 200 chars)"}), 400
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "page must be integer >= 1"}), 400
    try:
        page_size = int(request.args.get("page_size", 10))
        if not (1 <= page_size <= 100):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "page_size must be integer 1-100"}), 400
    category_filter = request.args.get("category")
    # Simple full-text match on title + content
    results = []
    for doc in _documents.values():
        if category_filter and doc.get("category") != category_filter:
            continue
        text = (doc.get("title", "") + " " + doc.get("content", "")).lower()
        if q.lower() in text:
            results.append({
                "document_id": doc["document_id"],
                "title": doc["title"],
                "category": doc.get("category"),
                "score": 1.0,
            })
    total = len(results)
    start = (page - 1) * page_size
    results = results[start: start + page_size]
    return jsonify({
        "results": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "query": q,
    }), 200


@app.route("/documents", methods=["POST"])
def index_document():
    err = _check_auth()
    if err:
        return err
    data = request.get_json(force=True) or {}
    title = data.get("title")
    content = data.get("content")
    if not title:
        return jsonify({"error": "missing required field: title"}), 400
    if not content:
        return jsonify({"error": "missing required field: content"}), 400
    doc_id = str(uuid.uuid4())
    doc = {
        "document_id": doc_id,
        "title": title,
        "content": content,
        "category": data.get("category"),
        "tags": data.get("tags", []),
        "indexed_at": _now(),
    }
    _documents[doc_id] = doc
    return jsonify({
        "document_id": doc_id,
        "title": title,
        "category": doc.get("category"),
        "indexed_at": doc["indexed_at"],
    }), 201


@app.route("/documents/<doc_id>", methods=["GET"])
def get_document(doc_id):
    err = _check_auth()
    if err:
        return err
    doc = _documents.get(doc_id)
    if not doc:
        return jsonify({"error": "document not found"}), 404
    return jsonify(doc), 200


@app.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    err = _check_auth()
    if err:
        return err
    doc = _documents.pop(doc_id, None)
    if not doc:
        return jsonify({"error": "document not found"}), 404
    return jsonify({"deleted": True, "document_id": doc_id}), 200


@app.route("/suggest", methods=["GET"])
def suggest():
    err = _check_auth()
    if err:
        return err
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "missing required query param: q"}), 400
    if len(q) > 50:
        return jsonify({"error": "query too long (max 50 chars)"}), 400
    try:
        limit = int(request.args.get("limit", 5))
        if not (1 <= limit <= 20):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "limit must be integer 1-20"}), 400
    suggestions = []
    for doc in _documents.values():
        title = doc.get("title", "")
        if title.lower().startswith(q.lower()):
            suggestions.append(title)
    suggestions = list(dict.fromkeys(suggestions))[:limit]
    return jsonify({"suggestions": suggestions, "query": q}), 200


if __name__ == "__main__":
    app.run(port=5003, debug=False)
