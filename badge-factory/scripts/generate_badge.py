#!/usr/bin/env python3
"""Badge Factory generator: build prompt → image backend → optional assemble.

Backends:
  cursor  — write job JSON for a Cursor agent (GenerateImage tool); exit 3
  openai  — OpenAI Images API (needs OPENAI_API_KEY)
  http    — POST JSON to BADGE_GEN_URL (custom gateway)
  prompt  — only print/write the prompt job (no image)

Portable. Pillow/numpy only required when --assemble runs.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
JOBS = ROOT / "jobs"
sys.path.insert(0, str(HERE))
from prompt_engine import build_badge_prompt, write_job  # noqa: E402


def _post_json(url: str, body: dict, headers: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def backend_openai(prompt: str, out: Path, size: str = "1024x1024") -> Path:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY not set")
    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
    body = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": 1,
    }
    # gpt-image-1 returns b64; dall-e-3 may return url
    if model.startswith("dall-e"):
        body["response_format"] = "b64_json"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        result = _post_json("https://api.openai.com/v1/images/generations", body, headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI HTTP {e.code}: {detail[:800]}") from e
    item = result["data"][0]
    out.parent.mkdir(parents=True, exist_ok=True)
    if "b64_json" in item:
        out.write_bytes(base64.b64decode(item["b64_json"]))
    elif "url" in item:
        with urllib.request.urlopen(item["url"], timeout=180) as resp:
            out.write_bytes(resp.read())
    else:
        raise SystemExit(f"Unexpected OpenAI response keys: {list(item)}")
    return out


def backend_http(prompt: str, out: Path, refs: list[str] | None) -> Path:
    url = os.environ.get("BADGE_GEN_URL")
    if not url:
        raise SystemExit("BADGE_GEN_URL not set for --backend http")
    body = {"prompt": prompt, "aspect_ratio": "1:1"}
    if refs:
        body["reference_image_paths"] = refs
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("BADGE_GEN_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        result = _post_json(url, body, headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP gen {e.code}: {detail[:800]}") from e
    out.parent.mkdir(parents=True, exist_ok=True)
    if "b64_json" in result:
        out.write_bytes(base64.b64decode(result["b64_json"]))
    elif "path" in result:
        out.write_bytes(Path(result["path"]).read_bytes())
    elif "url" in result:
        with urllib.request.urlopen(result["url"], timeout=180) as resp:
            out.write_bytes(resp.read())
    else:
        raise SystemExit(f"Unexpected HTTP gen keys: {list(result)[:20]}")
    return out


def backend_cursor(payload: dict, out: Path, refs: list[str] | None) -> Path:
    job = {
        **payload,
        "output": str(out),
        "reference_image_paths": refs or [],
        "tool": "GenerateImage",
        "instructions_for_agent": (
            "Call Cursor GenerateImage with description=job['description'], "
            "aspect_ratio=job['aspect_ratio'], filename=basename(output), "
            "reference_image_paths if any. Then run: "
            f"python scripts/assemble_badge.py <generated> -o {out}"
            + (f" --rim {payload['rim']}" if payload.get("rim") and payload.get("assemble") else "")
            + " if job['assemble'] is true; otherwise copy/move generated to output."
        ),
    }
    job_path = write_job(job, JOBS / "last_generate_job.json")
    print(json.dumps({"status": "needs_cursor_agent", "job": str(job_path)}, ensure_ascii=False, indent=2))
    print(
        "\n[badge-factory] No local image model in CLI. "
        "A Cursor agent must run GenerateImage using jobs/last_generate_job.json, "
        "then assemble_badge.py. Skill badge-factory covers this.",
        file=sys.stderr,
    )
    return job_path


def maybe_assemble(src: Path, dest: Path, rim: str | None) -> Path:
    cmd = [sys.executable, str(HERE / "assemble_badge.py"), str(src), "-o", str(dest)]
    if rim:
        cmd += ["--rim", rim]
    subprocess.check_call(cmd)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a badge (or free image) via Badge Factory")
    ap.add_argument("--brief", required=True, help="Scene / user request")
    ap.add_argument("--text", default=None, help="Arched badge lettering")
    ap.add_argument("--rim", default=None, choices=["gold_wide", "rose_romantic", "olive_bronze", "gunmetal", "silver_chrome"])
    ap.add_argument("--extra", default=None, help="Extra direction")
    ap.add_argument("--freeform", action="store_true", help="Skip badge shell; generate any image as said")
    ap.add_argument("--ref", action="append", default=[], help="Reference image path (repeatable)")
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument(
        "--backend",
        choices=["cursor", "openai", "http", "prompt"],
        default=os.environ.get("BADGE_GEN_BACKEND", "cursor"),
    )
    ap.add_argument("--no-assemble", action="store_true")
    ap.add_argument("--openai-size", default=os.environ.get("OPENAI_IMAGE_SIZE", "1024x1024"))
    args = ap.parse_args()

    payload = build_badge_prompt(
        args.brief,
        text=args.text,
        rim=args.rim,
        extra=args.extra,
        freeform=args.freeform,
    )
    if args.no_assemble:
        payload["assemble"] = False

    write_job({**payload, "output": str(args.output), "refs": args.ref}, JOBS / "last_prompt.json")

    if args.backend == "prompt":
        print(payload["description"])
        print(f"\n# wrote {JOBS / 'last_prompt.json'}", file=sys.stderr)
        return

    if args.backend == "cursor":
        backend_cursor(payload, args.output, args.ref)
        sys.exit(3)

    raw = args.output.with_suffix(".raw" + args.output.suffix)
    if args.backend == "openai":
        backend_openai(payload["description"], raw, size=args.openai_size)
    elif args.backend == "http":
        backend_http(payload["description"], raw, args.ref)
    else:
        raise SystemExit(f"unknown backend {args.backend}")

    if payload.get("assemble") and not args.freeform:
        maybe_assemble(raw, args.output, args.rim)
        print(f"wrote assembled {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw.read_bytes())
        print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
