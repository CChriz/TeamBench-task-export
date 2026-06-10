#!/usr/bin/env python3
"""
Export chosen TeamBench Tasks as fully packaged workspaces to pass to agentic team.

Run from [TeamBench] repository ROOT.

e.g.
  python scripts/export_standalone_tasks.py \
    --tasks DIST1_queue_race GH10_retry_backoff D2_data_quality \
    --seeds 0 \
    --out exported_tasks
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def copy_dir_contents(src: Path, dst: Path) -> None:
    # ensure destination directory exists
    dst.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        return

    # copy all files and subdirectories  
    for item in src.iterdir():
        target = dst / item.name

        # if directory -> copy whole directory | if file -> copy file
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def read_text_if_exists(path: Path) -> str:
    # return text of file at <path> if exists
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def write_json(path: Path, obj: dict) -> None:
    # write <obj> as JSON to <path>     ensure parent directories exist
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def make_agent_task_md(task_id: str, seed: int, spec_md: str) -> str:
    # create TASK.md for agent team based on (spec_md, task_id)
    return f"""# {task_id}

Seed: {seed}

{spec_md}
"""

# some wrapper?
# You are given a mutable workspace directory. Your goal is to modify files in that workspace until the requirements below are satisfied.
# Rules:
# - Work only inside the provided workspace unless your harness explicitly permits otherwise.
# - Prefer minimal, targeted changes.
# - Run tests or validation commands when available.
# - When finished, report changed files, commands run, and any remaining risks.

# ** TB SOLO_SYSTEM_PROMPT = """You are a software engineer. You have access to the full task specification and can execute any command.
# Complete the task to the best of your ability."""


def task_has_generator(task_id: str) -> bool:
    # check if task has generator registered (generators/registry.py)
    from generators.registry import has_generator

    return bool(has_generator(task_id))


def materialize_generated_task(
    task_id: str,
    seed: int,
    bundle_dir: Path,
) -> None:
    # materialise the generated task 
    # - invoking its generator      writing [workspace + spec.md + brief.md]
    from generators.registry import get_generator

    gen = get_generator(task_id)
    generated = gen.generate(seed=seed)

    workspace_dir = bundle_dir / "workspace"
    reports_dir = bundle_dir / "_eval" / "reports"


    # * write generated workspace files AND reports/expected.json
    gen.write_to_disk(
        generated,
        workspace_dir=str(workspace_dir),
        reports_dir=str(reports_dir),
    )

    spec_md = generated.spec_md
    brief_md = generated.brief_md

    (bundle_dir / "TASK.md").write_text(
        make_agent_task_md(task_id, seed, spec_md),
        encoding="utf-8",
    )
    (bundle_dir / "spec.md").write_text(spec_md, encoding="utf-8")
    (bundle_dir / "brief.md").write_text(brief_md, encoding="utf-8")


def materialize_static_task(
    task_id: str,
    seed: int,
    bundle_dir: Path,
    task_dir: Path,
) -> None:
    # materialise a static task by copying workspace and invoking setup.sh if exists
    workspace_dir = bundle_dir / "workspace"
    reports_dir = bundle_dir / "_eval" / "reports"

    workspace_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    static_workspace = task_dir / "workspace"

    if static_workspace.exists():
        copy_dir_contents(static_workspace, workspace_dir)

    setup_sh = task_dir / "setup.sh"

    if setup_sh.exists():
        run_id = f"standalone_{now_utc()}_{uuid.uuid4().hex[:8]}"

        subprocess.run(
            [
                "bash",
                str(setup_sh.resolve()),
                str(workspace_dir.resolve()),
                str(reports_dir.resolve()),
                run_id,
                str(seed),
            ],
            check=True,
            text=True,
        )

    spec_md = read_text_if_exists(task_dir / "spec.md")
    brief_md = read_text_if_exists(task_dir / "brief.md")

    # spec.md is required for static tasks since it contains the task description and requirements. 
    # setup.sh may generate workspace files and reports, but it doesn't change the core task specification.
    if not spec_md:
        raise FileNotFoundError(f"Missing spec.md for task: {task_id}")

    (bundle_dir / "TASK.md").write_text(
        make_agent_task_md(task_id, seed, spec_md),
        encoding="utf-8",
    )
    (bundle_dir / "spec.md").write_text(spec_md, encoding="utf-8")

    if brief_md:
        (bundle_dir / "brief.md").write_text(brief_md, encoding="utf-8")


def copy_eval_assets(task_id: str, bundle_dir: Path, task_dir: Path) -> None:
    # copy evaluation assets (grade.sh, expected.json, task-local files) to _eval directory in bundle
    eval_dir = bundle_dir / "_eval"
    eval_dir.mkdir(parents=True, exist_ok=True)

    (eval_dir / "submission").mkdir(exist_ok=True)
    (eval_dir / "reports").mkdir(exist_ok=True)

    # some grade.sh scripts rely on task-local files.
    eval_task_dir = eval_dir / "task_dir"

    if eval_task_dir.exists():
        shutil.rmtree(eval_task_dir)

    shutil.copytree(task_dir, eval_task_dir, dirs_exist_ok=True)

    grade_sh = task_dir / "grade.sh"

    if grade_sh.exists():
        shutil.copy2(grade_sh, eval_dir / "grade.sh")

    for name in ["task.yaml", "spec.md", "brief.md"]:
        src = task_dir / name

        if src.exists():
            shutil.copy2(src, eval_dir / name)


def export_one_task(
    task_id: str,
    seed: int,
    out_root: Path,
    repo_root: Path,
) -> Path:
    # export one task with given seed to a bundle directory under out_root, return path to bundle
    task_dir = repo_root / "tasks" / task_id

    if not task_dir.exists():
        raise FileNotFoundError(f"Missing task directory: {task_dir}")

    bundle_dir = out_root / f"{task_id}__seed_{seed}"

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)

    bundle_dir.mkdir(parents=True, exist_ok=True)

    generated = task_has_generator(task_id)

    if generated:
        materialize_generated_task(task_id, seed, bundle_dir)
    else:
        materialize_static_task(task_id, seed, bundle_dir, task_dir)

    copy_eval_assets(task_id, bundle_dir, task_dir)

    write_json(
        bundle_dir / "metadata.json",
        {
            "task_id": task_id,
            "seed": seed,
            "generated": generated,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agent_prompt": "TASK.md",
            "agent_workspace": "workspace",
            "hidden_eval_dir": "_eval",
            "agent_visible_files": [
                "TASK.md",
                "workspace/",
            ],
            "agent_hidden_files": [
                "_eval/",
                "_eval/reports/expected.json",
                "_eval/grade.sh",
                "_eval/task_dir/",
            ],
        },
    )

    return bundle_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="+", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--out", default="exported_tasks")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    out_root = Path(args.out).resolve()

    out_root.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(repo_root))

    exported = []

    for task_id in args.tasks:
        for seed in args.seeds:
            bundle = export_one_task(task_id, seed, out_root, repo_root)
            exported.append(str(bundle))
            print(f"Exported {task_id} seed={seed} -> {bundle}")

    write_json(
        out_root / "export_manifest.json",
        {
            "exported_count": len(exported),
            "bundles": exported,
        },
    )

    print(f"\nDone. Manifest: {out_root / 'export_manifest.json'}")


if __name__ == "__main__":
    main()

