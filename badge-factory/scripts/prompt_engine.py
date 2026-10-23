#!/usr/bin/env python3
"""Build generation prompts for Badge Factory (portable, no API calls)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHELL = HERE.parent / "recipes" / "gen_shell.json"


def load_shell() -> dict:
    return json.loads(SHELL.read_text(encoding="utf-8"))


def build_badge_prompt(
    brief: str,
    *,
    text: str | None = None,
    rim: str | None = None,
    extra: str | None = None,
    freeform: bool = False,
) -> dict:
    """Return payload for GenerateImage / OpenAI / HTTP backends."""
    brief = (brief or "").strip()
    if len(brief.split()) < 3 and not freeform:
        raise ValueError("brief too short — need a real scene description")

    shell = load_shell()
    if freeform:
        description = brief
        if extra:
            description += f"\n\nAdditional direction: {extra}"
        return {
            "mode": "freeform",
            "description": description,
            "aspect_ratio": shell.get("aspect_ratio", "1:1"),
            "assemble": False,
            "rim": rim,
        }

    rules = "; ".join(shell["badge_hard_rules"])
    rim_bit = ""
    if rim and rim in shell.get("rim_hints", {}):
        rim_bit = f" Rim style: {shell['rim_hints'][rim]}."
    elif rim:
        rim_bit = f" Rim style: {rim}."

    text_bit = ""
    if text:
        text_bit = (
            f' Arched badge lettering exactly: "{text}" '
            "(painted into the art along the inner curve, not a flat overlay box)."
        )

    extra_bit = f" {extra.strip()}" if extra else ""

    description = (
        f"Circular print-ready metal pin badge. Scene brief: {brief}.{text_bit}{rim_bit}"
        f"{extra_bit} Hard constraints: {rules}"
    )

    return {
        "mode": "badge",
        "description": description,
        "aspect_ratio": shell.get("aspect_ratio", "1:1"),
        "assemble": bool(shell.get("assemble_default", True)),
        "rim": rim,
        "brief": brief,
        "text": text,
    }


def write_job(payload: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
