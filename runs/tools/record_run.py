#!/usr/bin/env python3
"""P0 run manifest: init, intent, rounds, feedback, steps, render RUN.md, finalize."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = REPO_ROOT / "runs"
EXAMPLES_ROOT = RUNS_ROOT / "examples"
TEMPLATE = RUNS_ROOT / "_templates" / "manifest.empty.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_dir(run_id: str) -> Path:
    direct = RUNS_ROOT / run_id
    if direct.is_dir() or (RUNS_ROOT / run_id / "manifest.json").exists():
        return direct
    under_examples = EXAMPLES_ROOT / run_id
    if under_examples.is_dir() or (under_examples / "manifest.json").exists():
        return under_examples
    return direct


def _manifest_path(run_id: str) -> Path:
    return _run_dir(run_id) / "manifest.json"


def _load_manifest(run_id: str) -> dict[str, Any]:
    path = _manifest_path(run_id)
    if not path.is_file():
        raise SystemExit(f"manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(run_id: str, manifest: dict[str, Any]) -> Path:
    manifest["updated_at"] = _utc_now()
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _current_round(manifest: dict[str, Any]) -> dict[str, Any]:
    iterations = manifest.setdefault("iterations", [])
    if not iterations or iterations[-1].get("closed"):
        iterations.append(
            {
                "round": len(iterations) + 1,
                "phase": "implement",
                "started_at": _utc_now(),
                "notes": [],
                "steps": [],
                "feedback": [],
                "sources_changed": [],
            }
        )
    return iterations[-1]


def cmd_init(args: argparse.Namespace) -> int:
    run_dir = EXAMPLES_ROOT / args.id if args.examples else _run_dir(args.id)
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists() and not args.force:
        raise SystemExit(f"already exists: {manifest_path} (use --force)")

    base = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    now = _utc_now()
    manifest: dict[str, Any] = {
        **base,
        "run_id": args.id,
        "created_at": now,
        "updated_at": now,
        "agent": {"product": args.agent or "", "model": args.model or ""},
        "task": args.task or "",
        "prompt_ref": args.prompt_ref or "",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


def cmd_intent(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.run)
    intent = manifest.setdefault("intent", {})
    if args.user:
        intent["user_request"] = args.user
    if args.brief_file:
        brief_path = Path(args.brief_file).expanduser()
        if not brief_path.is_absolute():
            brief_path = (Path.cwd() / brief_path).resolve()
        intent["cad_brief_markdown"] = brief_path.read_text(encoding="utf-8")
        run_dir = _run_dir(args.run)
        copy = run_dir / "brief.md"
        copy.write_text(intent["cad_brief_markdown"], encoding="utf-8")
        intent["cad_brief_path"] = str(copy.relative_to(REPO_ROOT))
    if args.brief_json:
        intent["cad_brief"] = json.loads(Path(args.brief_json).read_text(encoding="utf-8"))
    for item in args.assumption or []:
        intent.setdefault("assumptions", []).append(item)
    for item in args.question or []:
        intent.setdefault("open_questions", []).append(item)
    path = _save_manifest(args.run, manifest)
    print(path)
    return 0


def cmd_round(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.run)
    iterations = manifest.setdefault("iterations", [])
    if iterations and not iterations[-1].get("closed"):
        iterations[-1]["closed"] = True
        iterations[-1]["ended_at"] = _utc_now()
    iterations.append(
        {
            "round": len(iterations) + 1,
            "phase": args.phase,
            "started_at": _utc_now(),
            "notes": [args.note] if args.note else [],
            "steps": [],
            "feedback": [],
            "sources_changed": [],
        }
    )
    path = _save_manifest(args.run, manifest)
    print(path)
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.run)
    row = _current_round(manifest)
    row["steps"].append(
        {
            "at": _utc_now(),
            "tool": args.tool,
            "cmd": args.cmd,
            "exit_code": int(args.exit),
            "artifacts": [str(a) for a in args.artifact or []],
            "note": args.note or "",
        }
    )
    path = _save_manifest(args.run, manifest)
    print(path)
    return 0


def _summarize_feedback_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "error": "file not found"}
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"path": str(path), "error": str(exc)}
        if isinstance(data, dict):
            keys = ("status", "solve_ok", "residual_max", "hint", "free", "rotation_issues", "conflict")
            return {"path": str(path), "summary": {k: data[k] for k in keys if k in data}}
        return {"path": str(path), "summary": data}
    return {"path": str(path), "summary": {"lines": len(path.read_text(encoding="utf-8").splitlines())}}


def cmd_feedback(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.run)
    row = _current_round(manifest)
    entry: dict[str, Any] = {
        "at": _utc_now(),
        "kind": args.kind,
        "note": args.note or "",
    }
    if args.path:
        p = Path(args.path).expanduser()
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        try:
            entry["path"] = str(p.relative_to(REPO_ROOT))
        except ValueError:
            entry["path"] = str(p)
        if args.ingest_json:
            entry.update(_summarize_feedback_file(p))
    if args.text:
        entry["text"] = args.text
    row["feedback"].append(entry)
    path = _save_manifest(args.run, manifest)
    print(path)
    return 0


def cmd_source(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.run)
    row = _current_round(manifest)
    for rel in args.path or []:
        p = Path(rel)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        try:
            row["sources_changed"].append(str(p.relative_to(REPO_ROOT)))
        except ValueError:
            row["sources_changed"].append(str(p))
    path = _save_manifest(args.run, manifest)
    print(path)
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.run)
    iterations = manifest.get("iterations", [])
    if iterations and not iterations[-1].get("closed"):
        iterations[-1]["closed"] = True
        iterations[-1]["ended_at"] = _utc_now()
    final = manifest.setdefault("final", {})
    final["status"] = args.status
    if args.summary:
        final["summary"] = args.summary
    if args.step:
        final["step_outputs"] = list(args.step)
    if args.spec:
        final["specs"] = list(args.spec)
    path = _save_manifest(args.run, manifest)
    print(path)
    return 0


def _rel(path: str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return path


def cmd_render(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.run)
    run_dir = _run_dir(args.run)
    lines: list[str] = []

    lines.append(f"# Run: {manifest.get('run_id', args.run)}")
    lines.append("")
    lines.append(f"- **Task**: {manifest.get('task', '')}")
    lines.append(f"- **Agent**: {manifest.get('agent', {}).get('product', '')} {manifest.get('agent', {}).get('model', '')}".strip())
    lines.append(f"- **Created**: {manifest.get('created_at', '')}")
    lines.append(f"- **Updated**: {manifest.get('updated_at', '')}")
    if manifest.get("prompt_ref"):
        lines.append(f"- **Prompt ref**: `{manifest['prompt_ref']}`")
    lines.append("")

    intent = manifest.get("intent", {})
    lines.append("## Intent")
    if intent.get("user_request"):
        lines.append("")
        lines.append("**User request**")
        lines.append("")
        lines.append(intent["user_request"].strip())
    if intent.get("cad_brief_path"):
        lines.append("")
        lines.append(f"**Brief**: [`{intent['cad_brief_path']}`]({intent['cad_brief_path']})")
    if intent.get("assumptions"):
        lines.append("")
        lines.append("**Assumptions**")
        for a in intent["assumptions"]:
            lines.append(f"- {a}")
    if intent.get("open_questions"):
        lines.append("")
        lines.append("**Open questions**")
        for q in intent["open_questions"]:
            lines.append(f"- {q}")
    lines.append("")

    lines.append("## Iterations")
    for it in manifest.get("iterations", []):
        lines.append("")
        lines.append(f"### Round {it.get('round')} — {it.get('phase')}")
        if it.get("started_at"):
            lines.append(f"- Started: {it['started_at']}")
        for note in it.get("notes", []):
            if note:
                lines.append(f"- Note: {note}")
        if it.get("sources_changed"):
            lines.append("- Sources changed:")
            for s in it["sources_changed"]:
                lines.append(f"  - `{_rel(s)}`")
        if it.get("steps"):
            lines.append("")
            lines.append("| # | Tool | Exit | Command / note |")
            lines.append("|---|------|------|----------------|")
            for i, step in enumerate(it["steps"], start=1):
                cmd = (step.get("cmd") or step.get("note") or "").replace("|", "\\|")
                if len(cmd) > 80:
                    cmd = cmd[:77] + "..."
                lines.append(
                    f"| {i} | {step.get('tool', '')} | {step.get('exit_code', '')} | `{cmd}` |"
                )
        if it.get("feedback"):
            lines.append("")
            lines.append("**Feedback**")
            for fb in it["feedback"]:
                kind = fb.get("kind", "note")
                path = fb.get("path", "")
                extra = ""
                if "summary" in fb and isinstance(fb["summary"], dict):
                    status = fb["summary"].get("status")
                    if status is not None:
                        extra = f" → status={status}"
                line = f"- `{kind}`"
                if path:
                    line += f" [`{path}`]({path})"
                if fb.get("note"):
                    line += f" — {fb['note']}"
                if fb.get("text"):
                    line += f" — {fb['text']}"
                line += extra
                lines.append(line)
    lines.append("")

    final = manifest.get("final", {})
    lines.append("## Final")
    lines.append("")
    lines.append(f"- **Status**: {final.get('status', 'unknown')}")
    if final.get("summary"):
        lines.append(f"- **Summary**: {final['summary']}")
    for spec in final.get("specs", []):
        lines.append(f"- Spec: `{_rel(spec)}`")
    for step in final.get("step_outputs", []):
        lines.append(f"- STEP: `{_rel(step)}`")
    val = final.get("validation")
    if isinstance(val, dict) and val:
        lines.append("- Validation:")
        for k, v in val.items():
            lines.append(f"  - {k}: {v}")
    lines.append("")

    out = run_dir / "RUN.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Record agent CAD run manifest (P0)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create a new run directory and manifest")
    p_init.add_argument("--id", required=True, help="Run id, e.g. 2026-05-17_agv-cart")
    p_init.add_argument("--task", default="", help="Short task title")
    p_init.add_argument("--agent", default="", help="cursor | claude-code | codex | ...")
    p_init.add_argument("--model", default="")
    p_init.add_argument("--prompt-ref", default="", help="e.g. chatExamples/prompts.md#C6")
    p_init.add_argument("--examples", action="store_true", help="Create under runs/examples/")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_intent = sub.add_parser("intent", help="Save intent / CAD brief")
    p_intent.add_argument("--run", required=True)
    p_intent.add_argument("--user", default="", help="Original user request")
    p_intent.add_argument("--brief-file", default="", help="Markdown brief path")
    p_intent.add_argument("--brief-json", default="", help="Structured brief JSON file")
    p_intent.add_argument("--assumption", action="append", default=[])
    p_intent.add_argument("--question", action="append", default=[])
    p_intent.set_defaults(func=cmd_intent)

    p_round = sub.add_parser("round", help="Start a new iteration round")
    p_round.add_argument("--run", required=True)
    p_round.add_argument("--phase", required=True, choices=["plan", "implement", "validate", "fix", "review"])
    p_round.add_argument("--note", default="")
    p_round.set_defaults(func=cmd_round)

    p_step = sub.add_parser("step", help="Append a command/tool step to current round")
    p_step.add_argument("--run", required=True)
    p_step.add_argument("--tool", default="Shell")
    p_step.add_argument("--cmd", default="")
    p_step.add_argument("--exit", type=int, default=0)
    p_step.add_argument("--artifact", action="append", default=[])
    p_step.add_argument("--note", default="")
    p_step.set_defaults(func=cmd_step)

    p_fb = sub.add_parser("feedback", help="Append feedback (tool output or user correction)")
    p_fb.add_argument("--run", required=True)
    p_fb.add_argument("--kind", required=True, help="constraint_report | inspect | user_correction | visual | ...")
    p_fb.add_argument("--path", default="", help="Repo-relative artifact path")
    p_fb.add_argument("--ingest-json", action="store_true", help="Summarize JSON report fields")
    p_fb.add_argument("--note", default="")
    p_fb.add_argument("--text", default="", help="Inline correction or observation")
    p_fb.set_defaults(func=cmd_feedback)

    p_src = sub.add_parser("source", help="Record source files changed in current round")
    p_src.add_argument("--run", required=True)
    p_src.add_argument("path", nargs="+")
    p_src.set_defaults(func=cmd_source)

    p_fin = sub.add_parser("finalize", help="Set final status and outputs")
    p_fin.add_argument("--run", required=True)
    p_fin.add_argument("--status", required=True, choices=["success", "partial", "failed", "in_progress"])
    p_fin.add_argument("--summary", default="")
    p_fin.add_argument("--step", action="append", default=[])
    p_fin.add_argument("--spec", action="append", default=[])
    p_fin.set_defaults(func=cmd_finalize)

    p_render = sub.add_parser("render", help="Generate RUN.md from manifest")
    p_render.add_argument("--run", required=True)
    p_render.set_defaults(func=cmd_render)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
