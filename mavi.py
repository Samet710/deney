from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

ROOT = Path(__file__).resolve().parent
SOURCE_FILE = ROOT / "sari_sistem.py"
CANDIDATE_FILE = ROOT / "mavi_aday.json"

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

SYSTEM_PROMPT = """
You are MAVİ, the game-evolution engineer in an autonomous software loop.

Your job is NOT to redesign the website. Your only target is sari_sistem.py,
which is the authoritative game model. The browser loads data exported from
that exact Python file, so every accepted change must alter actual gameplay
or progression, not only UI text.

Return ONLY valid JSON with these keys:
{
  "summary": "short Turkish summary",
  "reason": "why the change improves the game",
  "file": "sari_sistem.py",
  "content": "complete replacement source code for sari_sistem.py"
}

Rules:
- Write a COMPLETE replacement file, not a diff.
- Do not modify docs/index.html, docs/style.css, docs/app.js, workflow files,
  mavi.py, or kirmizi.py.
- Preserve the existing CLI flags --export-web and --self-test.
- Preserve Game, Player, Battle, GAME_CONFIG, and the exporter interfaces unless
  there is a concrete reason to extend them.
- New mechanics must be represented through the GAME_CONFIG/effect system so the
  existing browser game can actually execute them.
- Supported effect types are currently: damage, heal, shield, energy.
  You may improve the Python engine to add another effect type only when the
  browser already has a compatible interpretation. Do not add a type that the
  browser cannot execute.
- Never invent external files, environment variables, network services, or APIs.
- Do not make changes whose only visible impact is a message, version number,
  or cosmetic description.
- Avoid randomness in the core rule calculation. If you use probability, expose
  it explicitly in GAME_CONFIG and make it testable through the roll argument.
- Keep the smoke test meaningful and update it when mechanics legitimately change.
- Do not delete working mechanics just to make the file shorter.
- Do not intentionally weaken tests or assertions to get accepted.
- Prefer a small, concrete gameplay improvement over a giant rewrite.
"""


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}\s*$", text, flags=re.DOTALL)
    if match:
        value = json.loads(match.group(0))
        if isinstance(value, dict):
            return value
    raise ValueError("Mavi response was not valid JSON")


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is missing", file=sys.stderr)
        return 2

    current = SOURCE_FILE.read_text(encoding="utf-8")
    client = OpenAI()
    user_prompt = f"""
Here is the CURRENT sari_sistem.py source. Improve the ACTUAL GAME, not the UI.

--- CURRENT SOURCE ---
{current}
--- END SOURCE ---

Propose one concrete evolution. Make sure the returned full source is executable
and keeps --export-web and --self-test working.
"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    candidate = extract_json(response.output_text)

    if candidate.get("file") != "sari_sistem.py":
        raise ValueError("Mavi attempted to target a different file")
    content = candidate.get("content")
    if not isinstance(content, str) or len(content) < 100:
        raise ValueError("Mavi returned empty/invalid source")

    payload = {
        "model": MODEL,
        "summary": str(candidate.get("summary", "")),
        "reason": str(candidate.get("reason", "")),
        "file": "sari_sistem.py",
        "content": content,
    }
    CANDIDATE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "summary": payload["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
