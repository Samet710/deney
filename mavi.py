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


# OPENAI_MODEL boş olsa bile güvenli şekilde varsayılan modele düş.
MODEL = (os.getenv("OPENAI_MODEL") or "gpt-5.6-luna").strip()


SYSTEM_PROMPT = """
You are MAVİ, the game-evolution engineer in an autonomous software loop.

Your job is NOT to redesign the website.

Your only target is sari_sistem.py, which is the authoritative game model.

The browser loads data exported from that exact Python file, so every accepted
change must alter actual gameplay or progression, not only UI text.

Return ONLY valid JSON with exactly these keys:

{
  "summary": "short Turkish summary",
  "reason": "why the change improves the game",
  "file": "sari_sistem.py",
  "content": "complete replacement source code for sari_sistem.py"
}

Rules:

- Write a COMPLETE replacement file, not a diff.
- Do not modify docs/index.html.
- Do not modify docs/style.css.
- Do not modify docs/app.js.
- Do not modify workflow files.
- Do not modify mavi.py.
- Do not modify kirmizi.py.

- Preserve the existing CLI flags:
  --export-web
  --self-test

- Preserve:
  Game
  Player
  Battle
  GAME_CONFIG

unless there is a concrete gameplay reason to extend them.

- New mechanics must be implemented in the actual Python game engine.

- Do not create fake changes that only alter:
  text,
  descriptions,
  version numbers,
  cosmetic metadata,
  comments.

- Every gameplay feature must have a real effect on:
  player state,
  battle state,
  progression,
  actions,
  enemies,
  economy,
  rewards,
  or another executable game mechanic.

- Do not invent external files.
- Do not invent network services.
- Do not invent APIs.
- Do not require browser-only logic.

- Avoid unnecessary randomness in core rules.

- If probability is used:
  - expose the probability in GAME_CONFIG
  - make the mechanic testable
  - keep deterministic testing possible

- Never intentionally weaken tests.

- Never delete existing working mechanics merely to shorten code.

- Prefer ONE small but meaningful gameplay evolution per generation.

- The resulting source MUST be executable.

- The resulting source MUST keep:
  python sari_sistem.py --self-test

working.

- The resulting source MUST keep:
  python sari_sistem.py --export-web

working.

- The browser-compatible exported data must continue to describe the actual
  game state and mechanics.

The goal is real game evolution, not dashboard evolution.
"""


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()

    try:
        value = json.loads(text)

        if isinstance(value, dict):
            return value

    except json.JSONDecodeError:
        pass

    match = re.search(
        r"\{.*\}\s*$",
        text,
        flags=re.DOTALL,
    )

    if match:
        value = json.loads(match.group(0))

        if isinstance(value, dict):
            return value

    raise ValueError(
        "Mavi response was not valid JSON"
    )


def main() -> int:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print(
            "OPENAI_API_KEY is missing",
            file=sys.stderr,
        )
        return 2

    if not MODEL:
        print(
            "OPENAI_MODEL resolved to an empty value",
            file=sys.stderr,
        )
        return 2

    if not SOURCE_FILE.exists():
        print(
            f"Missing source file: {SOURCE_FILE}",
            file=sys.stderr,
        )
        return 2

    current = SOURCE_FILE.read_text(
        encoding="utf-8"
    )

    client = OpenAI(
        api_key=api_key
    )

    user_prompt = f"""
Here is the CURRENT sari_sistem.py source.

Improve the ACTUAL GAME.

Do NOT redesign the UI.

Do NOT create a cosmetic-only change.

Make exactly ONE concrete gameplay evolution.

The returned content must be the COMPLETE replacement
for sari_sistem.py.

--- CURRENT SOURCE START ---

{current}

--- CURRENT SOURCE END ---

Return ONLY the JSON object requested by the system instructions.
"""

    print(
        f"Mavi model: {MODEL}"
    )

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    output_text = response.output_text

    candidate = extract_json(
        output_text
    )

    if candidate.get("file") != "sari_sistem.py":
        raise ValueError(
            "Mavi attempted to target a different file"
        )

    content = candidate.get("content")

    if not isinstance(content, str):
        raise ValueError(
            "Mavi returned invalid source content"
        )

    content = content.strip()

    if len(content) < 100:
        raise ValueError(
            "Mavi returned empty/too-short source"
        )

    summary = str(
        candidate.get(
            "summary",
            ""
        )
    ).strip()

    reason = str(
        candidate.get(
            "reason",
            ""
        )
    ).strip()

    payload = {
        "model": MODEL,
        "summary": summary,
        "reason": reason,
        "file": "sari_sistem.py",
        "content": content,
    }

    CANDIDATE_FILE.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "model": MODEL,
                "summary": summary,
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
  )
