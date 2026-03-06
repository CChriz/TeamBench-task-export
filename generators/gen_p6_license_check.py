"""
Parameterized generator for P6: License Compatibility Check.

Each seed produces:
  - Different dependency sets with 2 GPL and 3 compatible packages
  - An alternatives.md with replacement suggestions
  - A LICENSE file (MIT)
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# Pool of (package_name, version, license, is_gpl)
COMPATIBLE_PKGS = [
    ("requests", "2.31.0", "Apache-2.0", False),
    ("flask", "3.0.0", "BSD-3-Clause", False),
    ("click", "8.1.7", "BSD-3-Clause", False),
    ("pydantic", "2.5.0", "MIT", False),
    ("httpx", "0.25.0", "BSD-3-Clause", False),
    ("fastapi", "0.104.0", "MIT", False),
    ("jinja2", "3.1.2", "BSD-3-Clause", False),
    ("sqlalchemy", "2.0.23", "MIT", False),
    ("pytest", "7.4.3", "MIT", False),
]

GPL_PKGS = [
    ("pycryptodome", "3.19.0", "GPL-3.0", True, "cryptography", "41.0.0", "Apache-2.0"),
    ("readline", "6.2.4", "GPL-3.0", True, "prompt-toolkit", "3.0.39", "BSD-3-Clause"),
    ("pygobject", "3.46.0", "LGPL-2.1/GPL-2.0", True, "pgi", "0.0.11", "LGPL-2.1"),
    ("gnu-getopt", "1.0.0", "GPL-2.0", True, "click", "8.1.7", "BSD-3-Clause"),
    ("gpg-tools", "2.0.0", "GPL-3.0", True, "python-gnupg", "0.5.2", "BSD-3-Clause"),
    ("chardet", "5.2.0", "LGPL-2.1", True, "charset-normalizer", "3.3.0", "MIT"),
]


class Generator(TaskGenerator):
    task_id = "P6_license_check"
    domain = "policy"
    difficulty = "easy"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick 3 compatible and 2 GPL packages
        compat = rng.sample(COMPATIBLE_PKGS, 3)
        gpl = rng.sample(GPL_PKGS, 2)

        all_pkgs = list(compat) + [(g[0], g[1], g[2], g[3]) for g in gpl]
        rng.shuffle(all_pkgs)

        gpl_names = [g[0] for g in gpl]
        keep_names = [c[0] for c in compat]
        replacement_names = [g[4] for g in gpl]

        workspace_files = {
            "requirements.txt": self._make_requirements(all_pkgs),
            "LICENSE": self._make_mit_license(),
            "alternatives.md": self._make_alternatives(gpl),
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
                "gpl_packages": gpl_names,
                "keep_packages": keep_names,
                "replacement_packages": replacement_names,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "easy", "category": "Policy"},
        )

    def _make_requirements(self, pkgs: list) -> str:
        lines = []
        for pkg in pkgs:
            name, version, lic = pkg[0], pkg[1], pkg[2]
            lines.append(f"{name}=={version}  # License: {lic}")
        return "\n".join(lines) + "\n"

    def _make_mit_license(self) -> str:
        return """MIT License

Copyright (c) 2024 Example Corp

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""

    def _make_alternatives(self, gpl_pkgs: list) -> str:
        lines = ["# License-Compatible Alternatives\n"]
        for pkg in gpl_pkgs:
            name, ver, lic, _, alt_name, alt_ver, alt_lic = pkg
            lines.append(f"## {name} ({lic})")
            lines.append(f"**Replace with**: `{alt_name}=={alt_ver}` (License: {alt_lic})")
            lines.append(f"- Drop-in replacement for the same functionality")
            lines.append("")
        return "\n".join(lines)
