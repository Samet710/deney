from __future__ import annotations

import ast
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

# IMPORTANT: This is an OpenRouter FREE endpoint.
# The :free suffix is checked at startup so Mavi cannot silently switch to a paid model.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAVI_MODEL = (os.getenv("OPENROUTER_MODEL") or "cohere/north-mini-code:free").strip()
MAX_OUTPUT_TOKENS = 20000

SYSTEM_PROMPT = """
You are MAVİ, the gameplay evolution engineer in an autonomous software loop.

Your ONLY code target is sari_sistem.py.

The most important rule:
A feature is NOT real merely because a new Python method exists.
Every proposed feature must be reachable through the existing exported gameplay
contract and must produce an observable gameplay/progression effect.

The browser currently executes:
- GAME_CONFIG["actions"]
- action energy cost
- action effects: damage, heal, shield, energy
- GAME_CONFIG["player"]
- GAME_CONFIG["progression"]
- GAME_CONFIG["enemies"]
- GAME_CONFIG["shop"] / potion flow
- the existing Game battle flow

Therefore:
- Prefer changing GAME_CONFIG actions/effects or logic used directly by Game.act,
  Game._apply_effects, Game._enemy_turn, Game._win_battle, or buy_potion.
- A new action is good only when it is present in GAME_CONFIG["actions"] and uses
  one or more browser-executable effects.
- DO NOT add a standalone method such as boss_savasi(), esya_satisi(),
  zindan_baskini(), or esya_birlestir() unless the existing game flow actually
  calls it. A dead method is not an evolution.
- Do not add a mechanic that the current browser cannot execute.
- Do not rely on hidden files, external services, APIs, UI edits, or future work.
- Do not change HTML, CSS, JavaScript, workflow files, mavi.py, or kirmizi.py.
- Do not change tests just to make a weak candidate pass.
- Preserve Game, Player, Battle, GAME_CONFIG, --self-test, and --export-web.
- Keep randomness deterministic through the roll argument when relevant.
- Make exactly ONE small but meaningful gameplay improvement.
- The complete source must remain executable.

Before returning the candidate, mentally trace the new/changed mechanic from a
player action or normal battle flow to a changed player/enemy/resource state.
If you cannot trace that path, do not propose it.

Return ONLY valid JSON:
{
  "summary": "short Turkish summary",
  "reason": "why this changes actual gameplay",
  "claimed_change": {
    "kind": "action|player|progression|enemy|shop|engine",
    "id": "identifier or null"
  },
  "file": "sari_sistem.py",
  "content": "COMPLETE replacement source code"
}
"""


def extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object even if the model wrapped it in a code fence."""
    text = text.strip()

    fenced = re.search(
        r"```(?:json)?\s*(\{.*\})\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        value = json.loads(fenced.group(1))
        if isinstance(value, dict):
            return value

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        value = json.loads(text[start : end + 1])
        if isinstance(value, dict):
            return value

    raise ValueError("Mavi response was not valid JSON.")


def validate_candidate_text(content: str) -> None:
    if len(content.strip()) < 500:
        raise ValueError("Mavi candidate source is too short.")

    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        raise ValueError(f"Mavi candidate has a syntax error: {exc}") from exc

    required = [
        "GAME_CONFIG",
        "class Player",
        "class Battle",
        "class Game",
        "def self_test",
        "def export_web",
    ]
    for marker in required:
        if marker not in content:
            raise ValueError(f"Mavi candidate missing required interface: {marker}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "eval",
                "exec",
                "compile",
                "__import__",
                "breakpoint",
                "input",
            }:
                raise ValueError(f"Forbidden call in candidate: {node.func.id}")


def request_model(client: OpenAI, prompt: str):
    print(f"Mavi model: {MAVI_MODEL}")
    response = client.chat.completions.create(
        model=MAVI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0.2,
    )

    if not response.choices:
        raise RuntimeError("OpenRouter boş seçim döndürdü.")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenRouter boş mesaj döndürdü.")

    return response, content


def main() -> int:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("HATA: OPENROUTER_API_KEY bulunamadı.", file=sys.stderr)
        return 2

    if not MAVI_MODEL.endswith(":free"):
        print(
            f"HATA: MAVI_MODEL ücretsiz değil: {MAVI_MODEL}",
            file=sys.stderr,
        )
        return 2

    if not SOURCE_FILE.exists():
        print(f"HATA: {SOURCE_FILE} bulunamadı.", file=sys.stderr)
        return 2

    current_source = SOURCE_FILE.read_text(encoding="utf-8")

    client = OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://samet710.github.io/deney/",
            "X-Title": "Autonom Mavi Kirmizi Sari",
        },
    )

    prompt = f"""
Improve the actual playable game in the current sari_sistem.py.

Make exactly ONE meaningful gameplay improvement.

IMPORTANT:
The returned source must make the improvement reachable through the existing
  game flow. Do not create a dead helper method and call that 'done'.

Good example:
- Add a new action to GAME_CONFIG["actions"] with a supported effect.
- Change an existing action's real damage/heal/shield/energy behavior.
- Change enemy/player/progression values when the normal battle flow makes the
  effect observable.
- Change Game logic that is actually executed by Game.act or the battle lifecycle.

Bad example:
- Add boss_savasi() but never call it.
- Add a hidden inventory system the browser never uses.
- Add only a description/title/version.
- Add a new effect type the browser does not understand.

Return the COMPLETE sari_sistem.py file in the JSON content field.

CURRENT sari_sistem.py:
--- BEGIN SOURCE ---
{current_source}
--- END SOURCE ---

Return ONLY the requested JSON object.
"""

    try:
        response, raw_text = request_model(client, prompt)
        candidate = extract_json(raw_text)

        if candidate.get("file") != "sari_sistem.py":
            raise ValueError("Mavi yanlış dosyayı hedefledi.")

        content = candidate.get("content")
        if not isinstance(content, str):
            raise ValueError("Mavi geçerli source code üretmedi.")

        content = content.strip()
        validate_candidate_text(content)

        payload = {
            "schema": 3,
            "provider": "openrouter",
            "model": getattr(response, "model", MAVI_MODEL),
            "summary": str(candidate.get("summary", "")).strip(),
            "reason": str(candidate.get("reason", "")).strip(),
            "claimed_change": (
                candidate.get("claimed_change")
                if isinstance(candidate.get("claimed_change"), dict)
                else {}
            ),
            "file": "sari_sistem.py",
            "content": content,
        }

        CANDIDATE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(
            json.dumps(
                {
                    "ok": True,
                    "provider": "openrouter",
                    "model": payload["model"],
                    "summary": payload["summary"],
                },
                ensure_ascii=False,
            )
        )
        return 0

    except Exception as exc:
        print(f"HATA: Mavi/OpenRouter isteği başarısız: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
