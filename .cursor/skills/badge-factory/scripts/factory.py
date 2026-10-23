#!/usr/bin/env python3
"""Unified Badge Factory CLI: prompt | generate | assemble | pipeline."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(prog="factory", description="Badge Factory")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_prompt = sub.add_parser("prompt", help="Build generation prompt only")
    p_prompt.add_argument("--brief", required=True)
    p_prompt.add_argument("--text")
    p_prompt.add_argument("--rim")
    p_prompt.add_argument("--extra")
    p_prompt.add_argument("--freeform", action="store_true")
    p_prompt.add_argument("-o", "--output", type=Path, default=Path("jobs/last_prompt.json"))

    p_gen = sub.add_parser("generate", help="Generate image (openai/http/cursor)")
    p_gen.add_argument("--brief", required=True)
    p_gen.add_argument("--text")
    p_gen.add_argument("--rim")
    p_gen.add_argument("--extra")
    p_gen.add_argument("--freeform", action="store_true")
    p_gen.add_argument("--ref", action="append", default=[])
    p_gen.add_argument("-o", "--output", type=Path, required=True)
    p_gen.add_argument("--backend", default=None)
    p_gen.add_argument("--no-assemble", action="store_true")

    p_as = sub.add_parser("assemble", help="Circle crop + optional rim")
    p_as.add_argument("input", type=Path)
    p_as.add_argument("-o", "--output", type=Path, required=True)
    p_as.add_argument("--rim")
    p_as.add_argument("--inner", type=float)

    p_pipe = sub.add_parser("pipeline", help="generate (cursor job or API) → assemble guidance")
    p_pipe.add_argument("--brief", required=True)
    p_pipe.add_argument("--text")
    p_pipe.add_argument("--rim", default="gold_wide")
    p_pipe.add_argument("--extra")
    p_pipe.add_argument("--ref", action="append", default=[])
    p_pipe.add_argument("-o", "--output", type=Path, required=True)
    p_pipe.add_argument("--backend", default="cursor")

    args = ap.parse_args()
    py = sys.executable

    if args.cmd == "prompt":
        cmd = [
            py,
            str(HERE / "generate_badge.py"),
            "--brief",
            args.brief,
            "-o",
            str(args.output),
            "--backend",
            "prompt",
        ]
        if args.text:
            cmd += ["--text", args.text]
        if args.rim:
            cmd += ["--rim", args.rim]
        if args.extra:
            cmd += ["--extra", args.extra]
        if args.freeform:
            cmd += ["--freeform"]
        raise SystemExit(run(cmd))

    if args.cmd == "generate":
        cmd = [
            py,
            str(HERE / "generate_badge.py"),
            "--brief",
            args.brief,
            "-o",
            str(args.output),
        ]
        if args.backend:
            cmd += ["--backend", args.backend]
        if args.text:
            cmd += ["--text", args.text]
        if args.rim:
            cmd += ["--rim", args.rim]
        if args.extra:
            cmd += ["--extra", args.extra]
        if args.freeform:
            cmd += ["--freeform"]
        if args.no_assemble:
            cmd += ["--no-assemble"]
        for r in args.ref:
            cmd += ["--ref", r]
        raise SystemExit(run(cmd))

    if args.cmd == "assemble":
        cmd = [py, str(HERE / "assemble_badge.py"), str(args.input), "-o", str(args.output)]
        if args.rim:
            cmd += ["--rim", args.rim]
        if args.inner is not None:
            cmd += ["--inner", str(args.inner)]
        raise SystemExit(run(cmd))

    if args.cmd == "pipeline":
        cmd = [
            py,
            str(HERE / "generate_badge.py"),
            "--brief",
            args.brief,
            "-o",
            str(args.output),
            "--backend",
            args.backend,
            "--rim",
            args.rim,
        ]
        if args.text:
            cmd += ["--text", args.text]
        if args.extra:
            cmd += ["--extra", args.extra]
        for r in args.ref:
            cmd += ["--ref", r]
        code = run(cmd)
        if code == 3:
            print(
                "\nNext (Cursor agent): GenerateImage from jobs/last_generate_job.json, "
                f"then assemble into {args.output}",
                file=sys.stderr,
            )
        raise SystemExit(code)


if __name__ == "__main__":
    main()
