"""
Parameterized generator for JS2: XSS Sanitization.

Each seed produces a different Express app type:
  - blog:      post/comment display, author bios
  - forum:     thread titles, user posts, profile pages
  - dashboard: widget labels, user-supplied chart titles, activity feeds

TNI Patterns:
  B (Adversarial Traps) - some naive sanitization approaches introduce new bugs
    e.g. replacing < with &lt; only in innerHTML still leaves href="javascript:" alive
  E (Compliance Rules) - CSP headers must match exact directives from spec

The spec (Planner) lists:
  - Exact injection points (file + line context + variable name)
  - Required sanitization function signatures
  - Exact CSP header string and all directive values
  - Which sanitization approaches are traps (why naive fixes fail)

The brief (Executor) says only:
  "Users report strange behavior in the web interface."

Workspace:
  app.js              — Express app with 3 XSS injection points
  package.json        — deps (express, marked for blog; express for others)
  views/<tpl>.ejs     — EJS templates with unescaped <%= %> rendering
  tests/test_xss.py   — Python test that checks for XSS vulnerabilities

Expected (grader-only):
  vuln_count           — always 3
  injection_points     — list of {file, variable, sink} dicts
  required_csp_directives — ordered list of CSP directive strings
  sanitization_functions  — list of function names that must appear in fixed code
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── App type configurations ───────────────────────────────────────────────────

APP_CONFIGS = [
    {
        "app_type": "blog",
        "label": "Blog Platform",
        "port": 3100,
        "resource": "posts",
        "views": {
            "index": "index",
            "detail": "post",
            "profile": "author",
        },
        # Three injection points: title rendered in list, body in detail, bio in profile
        "injection_points": [
            {"file": "views/index.ejs", "variable": "post.title",  "sink": "innerHTML",       "route": "/"},
            {"file": "views/post.ejs",  "variable": "post.body",   "sink": "innerHTML",        "route": "/posts/:id"},
            {"file": "views/author.ejs","variable": "author.bio",  "sink": "href attribute",   "route": "/authors/:id"},
        ],
        "trap_explanation": (
            "Replacing < and > with HTML entities in `post.body` does not prevent "
            "href-based XSS (javascript: URIs in author.bio). "
            "Using marked() without sanitize:true on `post.body` re-introduces HTML injection."
        ),
        "sanitization_functions": ["sanitizeHtml", "sanitizeUrl", "setSecurityHeaders"],
        "csp_directives": [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "object-src 'none'",
            "base-uri 'self'",
        ],
        "package_deps": {
            "express": "^4.18.2",
            "ejs": "^3.1.9",
            "dompurify": "^3.0.6",
            "jsdom": "^24.0.0",
        },
        "sample_data_js": """\
const posts = [
  { id: 1, title: req.query.title || 'Hello World', body: req.query.body || 'Welcome to the blog.', authorId: 1 },
  { id: 2, title: 'Second Post', body: 'Another article.', authorId: 2 },
];
const authors = [
  { id: 1, name: 'Alice', bio: req.query.bio || 'Tech writer' },
  { id: 2, name: 'Bob',   bio: 'Open source advocate' },
];""",
    },
    {
        "app_type": "forum",
        "label": "Discussion Forum",
        "port": 3200,
        "resource": "threads",
        "views": {
            "index": "index",
            "detail": "thread",
            "profile": "profile",
        },
        "injection_points": [
            {"file": "views/index.ejs",   "variable": "thread.title",   "sink": "innerHTML",     "route": "/"},
            {"file": "views/thread.ejs",  "variable": "post.content",   "sink": "innerHTML",     "route": "/threads/:id"},
            {"file": "views/profile.ejs", "variable": "user.website",   "sink": "href attribute","route": "/users/:id"},
        ],
        "trap_explanation": (
            "Stripping <script> tags from `post.content` does not prevent "
            "event-handler XSS (<img onerror=...>). "
            "Encoding `user.website` with encodeURIComponent does not block javascript: URIs."
        ),
        "sanitization_functions": ["sanitizeHtml", "sanitizeUrl", "setSecurityHeaders"],
        "csp_directives": [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' https:",
            "object-src 'none'",
            "base-uri 'self'",
        ],
        "package_deps": {
            "express": "^4.18.2",
            "ejs": "^3.1.9",
            "dompurify": "^3.0.6",
            "jsdom": "^24.0.0",
        },
        "sample_data_js": """\
const threads = [
  { id: 1, title: req.query.title || 'Welcome Thread', authorId: 1 },
  { id: 2, title: 'General Discussion', authorId: 2 },
];
const threadPosts = [
  { id: 1, threadId: 1, content: req.query.content || 'Hello everyone!', authorId: 1 },
];
const users = [
  { id: 1, name: 'Alice', website: req.query.website || 'https://example.com' },
  { id: 2, name: 'Bob',   website: 'https://bob.dev' },
];""",
    },
    {
        "app_type": "dashboard",
        "label": "Analytics Dashboard",
        "port": 3300,
        "resource": "widgets",
        "views": {
            "index": "index",
            "detail": "widget",
            "profile": "report",
        },
        "injection_points": [
            {"file": "views/index.ejs",  "variable": "widget.label",       "sink": "innerHTML",     "route": "/"},
            {"file": "views/widget.ejs", "variable": "widget.description", "sink": "innerHTML",     "route": "/widgets/:id"},
            {"file": "views/report.ejs", "variable": "report.sourceUrl",   "sink": "href attribute","route": "/reports/:id"},
        ],
        "trap_explanation": (
            "HTML-escaping `widget.description` using a regex replace misses "
            "attribute-context injection (e.g. \" onmouseover=alert(1)). "
            "Allowing report.sourceUrl without scheme validation permits javascript: URIs."
        ),
        "sanitization_functions": ["sanitizeHtml", "sanitizeUrl", "setSecurityHeaders"],
        "csp_directives": [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
        ],
        "package_deps": {
            "express": "^4.18.2",
            "ejs": "^3.1.9",
            "dompurify": "^3.0.6",
            "jsdom": "^24.0.0",
        },
        "sample_data_js": """\
const widgets = [
  { id: 1, label: req.query.label || 'Revenue', description: req.query.description || 'Monthly revenue chart.' },
  { id: 2, label: 'Users',   description: 'Active user count.' },
];
const reports = [
  { id: 1, name: 'Q1 Report', sourceUrl: req.query.sourceUrl || 'https://data.example.com/q1' },
];""",
    },
]

# ── Trap sanitization approaches agents might naively try ─────────────────────

NAIVE_TRAP_COMMENTS = {
    "blog": (
        "// TRAP: naive regex replace — misses attribute injection and href sinks\n"
        "// e.g. str.replace(/<[^>]*>/g, '') strips tags but not event handlers\n"
        "// Also: using marked() without DOMPurify re-introduces HTML execution\n"
    ),
    "forum": (
        "// TRAP: removing <script> tags only — <img onerror=...> still executes\n"
        "// TRAP: encodeURIComponent on website URL does not block javascript: URIs\n"
    ),
    "dashboard": (
        "// TRAP: character-by-character escaping misses attribute context injection\n"
        "// TRAP: checking URL prefix with startsWith('http') can be bypassed with javascript:\n"
    ),
}


class Generator(TaskGenerator):
    task_id = "JS2_xss_sanitize"
    domain = "javascript"
    difficulty = "hard"
    languages = ["javascript", "python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        # Use seed modulo to guarantee each of the 3 canonical seeds (0,1,2)
        # maps to a distinct app type, while still using rng for any future
        # per-instance variation within a config.
        cfg = APP_CONFIGS[seed % len(APP_CONFIGS)]

        workspace_files = {
            "app.js":                    self._gen_app_js(cfg),
            "package.json":              self._gen_package_json(cfg),
            f"views/{cfg['views']['index']}.ejs":   self._gen_index_ejs(cfg),
            f"views/{cfg['views']['detail']}.ejs":  self._gen_detail_ejs(cfg),
            f"views/{cfg['views']['profile']}.ejs": self._gen_profile_ejs(cfg),
            "tests/test_xss.py":         self._gen_test_xss(cfg),
        }

        expected = {
            "app_type": cfg["app_type"],
            "vuln_count": 3,
            "injection_points": cfg["injection_points"],
            "required_csp_directives": cfg["csp_directives"],
            "sanitization_functions": cfg["sanitization_functions"],
            "port": cfg["port"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(cfg),
            brief_md=self._gen_brief(cfg),
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── workspace file generators ─────────────────────────────────────────────

    def _gen_app_js(self, cfg: dict) -> str:
        app_type = cfg["app_type"]
        label = cfg["label"]
        port = cfg["port"]
        resource = cfg["resource"]
        trap_comment = NAIVE_TRAP_COMMENTS[app_type]
        views = cfg["views"]
        ip = cfg["injection_points"]  # injection_points list

        # Build route-specific render logic per app type
        if app_type == "blog":
            routes = f"""\
// ── Routes ────────────────────────────────────────────────────────────────────

// GET / — list all posts (injection point: post.title rendered unescaped)
app.get('/', (req, res) => {{
  {cfg['sample_data_js']}
  // VULNERABILITY 1: post.title from query string rendered with <%- %> (unescaped)
  res.render('{views["index"]}', {{ posts, title: 'Blog' }});
}});

// GET /posts/:id — show post detail (injection point: post.body rendered unescaped)
app.get('/posts/:id', (req, res) => {{
  const post = {{
    id: req.params.id,
    title: 'Sample Post',
    body: req.query.body || 'Post content here.',
    authorId: 1,
  }};
  // VULNERABILITY 2: post.body rendered with <%- %> (unescaped HTML)
  res.render('{views["detail"]}', {{ post, title: post.title }});
}});

// GET /authors/:id — show author profile (injection point: author.bio in href)
app.get('/authors/:id', (req, res) => {{
  const author = {{
    id: req.params.id,
    name: 'Alice',
    bio: req.query.bio || 'Tech writer',
    website: req.query.website || 'https://alice.dev',
  }};
  // VULNERABILITY 3: author.website placed directly in href attribute (javascript: URI possible)
  res.render('{views["profile"]}', {{ author, title: author.name }});
}});"""
        elif app_type == "forum":
            routes = f"""\
// ── Routes ────────────────────────────────────────────────────────────────────

// GET / — list threads (injection point: thread.title rendered unescaped)
app.get('/', (req, res) => {{
  {cfg['sample_data_js']}
  // VULNERABILITY 1: thread.title from query string rendered with <%- %> (unescaped)
  res.render('{views["index"]}', {{ threads, title: 'Forum' }});
}});

// GET /threads/:id — show thread posts (injection point: post.content rendered unescaped)
app.get('/threads/:id', (req, res) => {{
  const post = {{
    id: 1,
    threadId: req.params.id,
    content: req.query.content || 'Hello everyone!',
    authorId: 1,
  }};
  const thread = {{ id: req.params.id, title: req.query.title || 'Welcome Thread' }};
  // VULNERABILITY 2: post.content rendered with <%- %> (unescaped HTML)
  res.render('{views["detail"]}', {{ thread, post, title: thread.title }});
}});

// GET /users/:id — show user profile (injection point: user.website in href)
app.get('/users/:id', (req, res) => {{
  const user = {{
    id: req.params.id,
    name: 'Alice',
    website: req.query.website || 'https://alice.dev',
  }};
  // VULNERABILITY 3: user.website placed directly in href attribute (javascript: URI possible)
  res.render('{views["profile"]}', {{ user, title: user.name }});
}});"""
        else:  # dashboard
            routes = f"""\
// ── Routes ────────────────────────────────────────────────────────────────────

// GET / — list widgets (injection point: widget.label rendered unescaped)
app.get('/', (req, res) => {{
  {cfg['sample_data_js']}
  // VULNERABILITY 1: widget.label from query string rendered with <%- %> (unescaped)
  res.render('{views["index"]}', {{ widgets, title: 'Dashboard' }});
}});

// GET /widgets/:id — widget detail (injection point: widget.description rendered unescaped)
app.get('/widgets/:id', (req, res) => {{
  const widget = {{
    id: req.params.id,
    label: req.query.label || 'Revenue',
    description: req.query.description || 'Monthly revenue chart.',
  }};
  // VULNERABILITY 2: widget.description rendered with <%- %> (unescaped HTML)
  res.render('{views["detail"]}', {{ widget, title: widget.label }});
}});

// GET /reports/:id — report detail (injection point: report.sourceUrl in href)
app.get('/reports/:id', (req, res) => {{
  const report = {{
    id: req.params.id,
    name: req.query.name || 'Q1 Report',
    sourceUrl: req.query.sourceUrl || 'https://data.example.com/q1',
  }};
  // VULNERABILITY 3: report.sourceUrl placed directly in href attribute (javascript: URI possible)
  res.render('{views["profile"]}', {{ report, title: report.name }});
}});"""

        return f"""\
'use strict';

/**
 * {label} — Express web application
 *
 * SECURITY NOTICE: This application has XSS vulnerabilities.
 * User-supplied input is rendered without sanitization in EJS templates.
 *
 * Known injection points:
 *   1. {ip[0]["file"]}  — {ip[0]["variable"]} via {ip[0]["sink"]}
 *   2. {ip[1]["file"]}  — {ip[1]["variable"]} via {ip[1]["sink"]}
 *   3. {ip[2]["file"]}  — {ip[2]["variable"]} via {ip[2]["sink"]}
 *
{trap_comment} */

const express = require('express');
const path = require('path');

const app = express();
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.json());
app.use(express.urlencoded({{ extended: false }}));

// TODO: Add Content-Security-Policy headers here (see spec for exact directives)
// TODO: Implement sanitizeHtml(str) to strip dangerous HTML
// TODO: Implement sanitizeUrl(url) to block javascript: URIs

{routes}

// ── Start ──────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || {port};
app.listen(PORT, () => {{
  console.log('{label} listening on port ' + PORT);
}});

module.exports = app;
"""

    def _gen_package_json(self, cfg: dict) -> str:
        app_type = cfg["app_type"]
        deps = cfg["package_deps"]
        deps_str = "\n".join(
            f'    "{k}": "{v}",' for k, v in deps.items()
        ).rstrip(",")
        # Fix trailing comma on last item
        lines = []
        dep_items = list(deps.items())
        for i, (k, v) in enumerate(dep_items):
            comma = "," if i < len(dep_items) - 1 else ""
            lines.append(f'    "{k}": "{v}"{comma}')
        deps_block = "\n".join(lines)
        return f"""\
{{
  "name": "{app_type}-app",
  "version": "1.0.0",
  "description": "{cfg['label']} with XSS vulnerabilities to fix",
  "main": "app.js",
  "scripts": {{
    "start": "node app.js",
    "test": "python3 tests/test_xss.py"
  }},
  "dependencies": {{
{deps_block}
  }}
}}
"""

    def _gen_index_ejs(self, cfg: dict) -> str:
        app_type = cfg["app_type"]
        ip0 = cfg["injection_points"][0]

        if app_type == "blog":
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1>Latest Posts</h1>
  <ul>
    <% posts.forEach(function(post) { %>
      <li>
        <%# VULNERABILITY: unescaped output — allows script injection via post.title %>
        <a href="/posts/<%= post.id %>"><%- post.title %></a>
      </li>
    <% }); %>
  </ul>
</body>
</html>
"""
        elif app_type == "forum":
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1>Discussion Threads</h1>
  <ul>
    <% threads.forEach(function(thread) { %>
      <li>
        <%# VULNERABILITY: unescaped output — allows script injection via thread.title %>
        <a href="/threads/<%= thread.id %>"><%- thread.title %></a>
      </li>
    <% }); %>
  </ul>
</body>
</html>
"""
        else:  # dashboard
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1>Dashboard</h1>
  <div class="widgets">
    <% widgets.forEach(function(widget) { %>
      <div class="widget">
        <%# VULNERABILITY: unescaped output — allows script injection via widget.label %>
        <h2><%- widget.label %></h2>
        <a href="/widgets/<%= widget.id %>">View Details</a>
      </div>
    <% }); %>
  </div>
</body>
</html>
"""

    def _gen_detail_ejs(self, cfg: dict) -> str:
        app_type = cfg["app_type"]

        if app_type == "blog":
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <article>
    <h1><%= post.title %></h1>
    <%# VULNERABILITY: unescaped body — markdown or HTML injection via post.body %>
    <div class="post-body"><%- post.body %></div>
    <p><a href="/authors/<%= post.authorId %>">View Author</a></p>
  </article>
</body>
</html>
"""
        elif app_type == "forum":
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1><%= thread.title %></h1>
  <div class="post">
    <%# VULNERABILITY: unescaped content — event-handler injection via post.content %>
    <p><%- post.content %></p>
    <a href="/users/<%= post.authorId %>">View Profile</a>
  </div>
</body>
</html>
"""
        else:  # dashboard
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1><%= widget.label %></h1>
  <%# VULNERABILITY: unescaped description — attribute injection via widget.description %>
  <div class="description"><%- widget.description %></div>
  <p><a href="/reports/1">View Report</a></p>
</body>
</html>
"""

    def _gen_profile_ejs(self, cfg: dict) -> str:
        app_type = cfg["app_type"]

        if app_type == "blog":
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1><%= author.name %></h1>
  <p><%= author.bio %></p>
  <%# VULNERABILITY: author.website used directly in href — allows javascript: URI %>
  <p>Website: <a href="<%- author.website %>">Visit</a></p>
</body>
</html>
"""
        elif app_type == "forum":
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1><%= user.name %></h1>
  <%# VULNERABILITY: user.website used directly in href — allows javascript: URI %>
  <p>Website: <a href="<%- user.website %>">Visit</a></p>
</body>
</html>
"""
        else:  # dashboard
            return """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title><%= title %></title>
</head>
<body>
  <h1><%= report.name %></h1>
  <%# VULNERABILITY: report.sourceUrl used directly in href — allows javascript: URI %>
  <p>Data source: <a href="<%- report.sourceUrl %>">View Source</a></p>
</body>
</html>
"""

    def _gen_test_xss(self, cfg: dict) -> str:
        app_type = cfg["app_type"]
        port = cfg["port"]
        ip = cfg["injection_points"]

        # Build type-specific URL and payload lines
        if app_type == "blog":
            xss_payloads = f"""\
    # Test 1: XSS in index via post.title
    r = requests.get(f'http://localhost:{port}/', params={{'title': XSS_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert XSS_PAYLOAD not in r.text, (
        "FAIL: Unescaped XSS payload found in index page (post.title)"
    )
    print("  PASS: post.title is sanitized in index view")

    # Test 2: XSS in post detail via post.body
    r = requests.get(f'http://localhost:{port}/posts/1', params={{'body': XSS_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert XSS_PAYLOAD not in r.text, (
        "FAIL: Unescaped XSS payload found in post detail (post.body)"
    )
    print("  PASS: post.body is sanitized in post detail view")

    # Test 3: javascript: URI in author.website href
    r = requests.get(f'http://localhost:{port}/authors/1', params={{'website': JS_URI_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert JS_URI_PAYLOAD not in r.text, (
        "FAIL: javascript: URI found in author profile href (author.website)"
    )
    print("  PASS: author.website href is sanitized in author view")"""
        elif app_type == "forum":
            xss_payloads = f"""\
    # Test 1: XSS in index via thread.title
    r = requests.get(f'http://localhost:{port}/', params={{'title': XSS_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert XSS_PAYLOAD not in r.text, (
        "FAIL: Unescaped XSS payload found in forum index (thread.title)"
    )
    print("  PASS: thread.title is sanitized in index view")

    # Test 2: XSS in thread detail via post.content
    r = requests.get(f'http://localhost:{port}/threads/1', params={{'content': XSS_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert XSS_PAYLOAD not in r.text, (
        "FAIL: Unescaped XSS payload found in thread detail (post.content)"
    )
    print("  PASS: post.content is sanitized in thread detail view")

    # Test 3: javascript: URI in user.website href
    r = requests.get(f'http://localhost:{port}/users/1', params={{'website': JS_URI_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert JS_URI_PAYLOAD not in r.text, (
        "FAIL: javascript: URI found in user profile href (user.website)"
    )
    print("  PASS: user.website href is sanitized in user profile view")"""
        else:  # dashboard
            xss_payloads = f"""\
    # Test 1: XSS in dashboard index via widget.label
    r = requests.get(f'http://localhost:{port}/', params={{'label': XSS_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert XSS_PAYLOAD not in r.text, (
        "FAIL: Unescaped XSS payload found in dashboard index (widget.label)"
    )
    print("  PASS: widget.label is sanitized in index view")

    # Test 2: XSS in widget detail via widget.description
    r = requests.get(f'http://localhost:{port}/widgets/1', params={{'description': XSS_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert XSS_PAYLOAD not in r.text, (
        "FAIL: Unescaped XSS payload found in widget detail (widget.description)"
    )
    print("  PASS: widget.description is sanitized in widget detail view")

    # Test 3: javascript: URI in report.sourceUrl href
    r = requests.get(f'http://localhost:{port}/reports/1', params={{'sourceUrl': JS_URI_PAYLOAD}}, timeout=5)
    assert r.status_code == 200
    assert JS_URI_PAYLOAD not in r.text, (
        "FAIL: javascript: URI found in report href (report.sourceUrl)"
    )
    print("  PASS: report.sourceUrl href is sanitized in report view")"""

        csp_directives = cfg["csp_directives"]
        csp_checks = "\n".join(
            f"    assert '{d}' in csp, f\"FAIL: CSP missing directive: {d}\""
            for d in csp_directives
        )

        return f'''\
"""
test_xss.py — XSS sanitization tests for {cfg["label"]}.

Starts the Node.js Express server, sends HTTP requests with XSS payloads,
and verifies that:
  1. Script injection payloads are not reflected unescaped in HTML responses
  2. javascript: URI payloads are not present in href attributes
  3. Content-Security-Policy headers are set with required directives

Run: python3 tests/test_xss.py
Exit 0 on all pass, exit 1 on any failure.
"""
import subprocess
import sys
import time
import os
import signal

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)

PORT = {port}
BASE_URL = f"http://localhost:{{PORT}}"

# XSS test payloads
XSS_PAYLOAD = "<script>alert('xss')</script>"
JS_URI_PAYLOAD = "javascript:alert('xss')"
EVENT_PAYLOAD = '"><img src=x onerror=alert(1)>'

# CSP directives that must be present
REQUIRED_CSP_DIRECTIVES = {csp_directives!r}


def wait_for_server(base_url: str, timeout: int = 10) -> bool:
    """Poll until server responds or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            requests.get(base_url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def run_tests(proc) -> int:
    """Run all XSS checks. Returns number of failures."""
    failures = 0

    print("\\nRunning XSS sanitization tests...")

    try:
{xss_payloads}

        # Test 4: Event-handler injection (onerror attribute)
        r = requests.get(BASE_URL + '/', params={{'title': EVENT_PAYLOAD, 'label': EVENT_PAYLOAD}}, timeout=5)
        assert r.status_code == 200
        # Raw onerror= attribute must not appear unescaped
        assert 'onerror=alert' not in r.text, (
            "FAIL: onerror event handler found in response — attribute injection not blocked"
        )
        print("  PASS: onerror event-handler injection blocked in index view")

        # Test 5: CSP header present and correct
        r = requests.get(BASE_URL + '/', timeout=5)
        csp = r.headers.get('Content-Security-Policy', '')
        assert csp, "FAIL: Content-Security-Policy header is missing"
        print(f"  INFO: CSP header: {{csp}}")
{csp_checks}
        print("  PASS: All required CSP directives present")

    except AssertionError as e:
        print(f"  ASSERTION ERROR: {{e}}")
        failures += 1
    except Exception as e:
        print(f"  UNEXPECTED ERROR: {{e}}")
        failures += 1

    return failures


def main():
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_js = os.path.join(server_dir, "app.js")

    if not os.path.exists(app_js):
        print(f"ERROR: app.js not found at {{app_js}}")
        sys.exit(1)

    print(f"Starting server: node {{app_js}}")
    proc = subprocess.Popen(
        ["node", app_js],
        cwd=server_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={{**os.environ, "PORT": str(PORT)}},
    )

    try:
        if not wait_for_server(BASE_URL):
            stdout, stderr = proc.communicate(timeout=2)
            print("ERROR: Server did not start within 10 seconds.")
            print("STDOUT:", stdout.decode(errors="replace"))
            print("STDERR:", stderr.decode(errors="replace"))
            sys.exit(1)

        print(f"Server running on port {{PORT}}")
        failures = run_tests(proc)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    if failures > 0:
        print(f"\\n{{failures}} test(s) FAILED")
        sys.exit(1)
    else:
        print("\\nAll XSS tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
'''

    # ── doc generators ────────────────────────────────────────────────────────

    def _gen_spec(self, cfg: dict) -> str:
        app_type = cfg["app_type"]
        label = cfg["label"]
        ip = cfg["injection_points"]
        csp = cfg["csp_directives"]
        fns = cfg["sanitization_functions"]
        trap = cfg["trap_explanation"]
        views = cfg["views"]
        port = cfg["port"]

        ip_rows = "\n".join(
            f"| `{p['file']}` | `{p['variable']}` | `{p['sink']}` | `{p['route']}` |"
            for p in ip
        )
        csp_str = "; ".join(csp)
        fn_list = "\n".join(f"- `{fn}()`" for fn in fns)
        csp_dir_list = "\n".join(f"- `{d}`" for d in csp)

        return f"""\
# JS2: XSS Sanitization — Full Specification (Planner/Verifier)

## Overview

The **{label}** is an Express/EJS web application that renders user-supplied
input directly into HTML using EJS's unescaped `<%- %>` tag. Three distinct
injection points allow attackers to inject arbitrary HTML/JavaScript or
navigate users to `javascript:` URIs. Additionally, no `Content-Security-Policy`
header is set.

This specification identifies all injection points, specifies the required
sanitization approach (including which naive approaches are traps), and defines
the exact CSP header value.

---

## 1. Injection Points (3 confirmed XSS vulnerabilities)

| File | Variable | Sink | Route |
|------|----------|------|-------|
{ip_rows}

### 1.1 Injection Point 1 — `{ip[0]['variable']}` in `{ip[0]['file']}`

- **Sink**: `{ip[0]['sink']}`
- **Route**: `GET {ip[0]['route']}`
- **How it works**: The value arrives via query string and is rendered with
  `<%- %>` (raw unescaped output). Any HTML tags, including `<script>` blocks
  and event-handler attributes, are passed through verbatim.
- **Required fix**: Replace `<%- {ip[0]['variable']} %>` with
  `<%- sanitizeHtml({ip[0]['variable']}) %>` where `sanitizeHtml` strips all
  dangerous tags and attributes.

### 1.2 Injection Point 2 — `{ip[1]['variable']}` in `{ip[1]['file']}`

- **Sink**: `{ip[1]['sink']}`
- **Route**: `GET {ip[1]['route']}`
- **How it works**: User content is rendered with `<%- %>`. Payload examples:
  `<img src=x onerror=alert(1)>`, `<svg onload=alert(1)>`.
- **Required fix**: Apply `sanitizeHtml()` before rendering. Must handle
  attribute-context injection (not just tag stripping).

### 1.3 Injection Point 3 — `{ip[2]['variable']}` in `{ip[2]['file']}`

- **Sink**: `{ip[2]['sink']}`
- **Route**: `GET {ip[2]['route']}`
- **How it works**: The URL value is placed directly inside `href="<%- ... %>"`.
  An attacker supplies `javascript:alert(1)` which browsers execute on click.
- **Required fix**: Apply `sanitizeUrl()` before rendering. Must block any URL
  whose scheme is not `http` or `https` (case-insensitive, trim whitespace).

---

## 2. Adversarial Traps (TNI Pattern B)

The following approaches appear to fix the issues but introduce new bugs or
leave attack surface:

{trap}

**Correct approach**:
- `sanitizeHtml(str)`: Use a proper allowlist-based sanitizer. The recommended
  implementation uses DOMPurify (via jsdom) with `ALLOWED_TAGS` and
  `ALLOWED_ATTR` restricted to safe HTML elements. Do NOT use regex tag-stripping.
- `sanitizeUrl(url)`: Parse the URL and check `new URL(url).protocol`. Accept
  only `http:` and `https:`. On parse error or disallowed scheme, return `'#'`.
  Do NOT use `startsWith` alone (bypassed with whitespace or mixed case).

---

## 3. Content-Security-Policy Header (TNI Pattern E)

The application MUST set the following `Content-Security-Policy` response header
on all routes. The exact directive values are required:

```
Content-Security-Policy: {csp_str}
```

Required directives (all must be present):
{csp_dir_list}

**Implementation**: Use `app.use()` middleware that sets this header before any
route handler. The function must be named `setSecurityHeaders`.

Example skeleton:
```javascript
function setSecurityHeaders(req, res, next) {{
  res.setHeader('Content-Security-Policy', [
    // ... directives from spec ...
  ].join('; '));
  next();
}}
app.use(setSecurityHeaders);
```

---

## 4. Required Function Names

The following functions MUST be defined in `app.js` (grader checks by name):

{fn_list}

Function signatures:
```javascript
// Strips dangerous HTML using allowlist-based sanitization.
// Returns safe HTML string. Never returns raw user input unchanged.
function sanitizeHtml(str) {{ ... }}

// Validates URL scheme. Returns url if http/https, '#' otherwise.
// Must handle javascript:, data:, vbscript:, and mixed-case variants.
function sanitizeUrl(url) {{ ... }}

// Express middleware that sets the Content-Security-Policy header.
function setSecurityHeaders(req, res, next) {{ ... }}
```

---

## 5. File Map

| File | What needs to change |
|------|----------------------|
| `app.js` | Add `sanitizeHtml`, `sanitizeUrl`, `setSecurityHeaders`; apply to all 3 injection points |
| `views/{views['index']}.ejs` | Change `<%- %>` → `<%- sanitizeHtml(...) %>` for injection point 1 |
| `views/{views['detail']}.ejs` | Change `<%- %>` → `<%- sanitizeHtml(...) %>` for injection point 2 |
| `views/{views['profile']}.ejs` | Change `<%- %>` → `<%- sanitizeUrl(...) %>` for injection point 3 |
| `package.json` | Already includes `dompurify` and `jsdom` — do not change versions |

---

## 6. Test Suite

`tests/test_xss.py` starts the server on port `{port}` and runs 5 checks:

| # | Check |
|---|-------|
| 1 | `{ip[0]['variable']}` payload not reflected unescaped |
| 2 | `{ip[1]['variable']}` payload not reflected unescaped |
| 3 | `{ip[2]['variable']}` javascript: URI not present in href |
| 4 | `onerror=` event-handler injection blocked |
| 5 | CSP header present with all required directives |

All 5 checks must pass (exit code 0).

---

## 7. Deliverables

- `app.js` with all 3 injection points fixed and CSP middleware added
- `views/` templates updated to use sanitization wrappers
- All 5 tests in `tests/test_xss.py` pass with exit code 0
- `attestation.json` with `{{"verdict": "pass"}}` once all tests pass
"""

    def _gen_brief(self, cfg: dict) -> str:
        label = cfg["label"]
        port = cfg["port"]
        return f"""\
# JS2: XSS Sanitization (Executor Brief)

Users of the **{label}** report strange behavior in the web interface —
some pages display unexpected content or act oddly when certain input is provided.

Your workspace contains:
- `app.js` — Express web application
- `views/` — EJS templates rendered by the server
- `tests/test_xss.py` — test suite (run to verify your fix)
- `package.json` — Node.js dependencies

**Run the tests**:
```
npm install
python3 tests/test_xss.py
```

The server listens on port `{port}`.

Fix whatever is causing the reported behavior so all tests pass.
Create `attestation.json` with `{{"verdict": "pass"}}` once done.
"""
