from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI, RateLimitError

ROOT = Path(__file__).resolve().parent
SOURCE_FILE = ROOT / "sari_sistem.py"
CANDIDATE_FILE = ROOT / "mavi_aday.json"

PRIMARY_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-5.6-luna").strip()
FALLBACK_MODEL = (os.getenv("MAVI_FALLBACK_MODEL") or "gpt-5.6-terra").strip()
MAX_OUTPUT_TOKENS = 12000

SYSTEM_PROMPT = """
You are MAVİ, the game-evolution engineer in an autonomous software loop.

Your only target is sari_sistem.py, the authoritative game engine.

Do NOT redesign the website and do NOT modify HTML, CSS, JavaScript, workflows,
mavi.py, or kirmizi.py.

Every accepted change must affect real gameplay or progression.

Valid examples include a battle mechanic, player stat, enemy behavior, action,
resource, reward, item, progression rule, or risk/reward mechanic.

Cosmetic-only changes are invalid.

Return ONLY valid JSON in exactly this shape:
{
  "summary": "short Turkish summary",
  "reason": "why the gameplay improvement matters",
  "file": "sari_sistem.py",
  "content": "COMPLETE replacement source code"
}

Rules:
- content must be the COMPLETE sari_sistem.py file.
- Never return a diff or patch.
- Preserve Game, Player, Battle, GAME_CONFIG.
- Preserve --self-test and --export-web.
- Keep the exporter compatible with the existing browser.
- Do not invent external files, services, APIs, or network requirements.
- Do not intentionally weaken tests.
- Do not delete working mechanics without a concrete reason.
- Make ONE small, meaningful gameplay improvement.
- Keep randomness testable through the roll argument when used.
- The code must be executable.
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

    raise ValueError("Mavi response was not valid JSON.")


def request_model(client: OpenAI, model: str, prompt: str):
    print(f"Mavi model: {model}")
    return client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        reasoning={"effort": "minimal"},
        max_output_tokens=MAX_OUTPUT_TOKENS,
        store=False,
    )


def main() -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("HATA: OPENAI_API_KEY bulunamadı.", file=sys.stderr)
        return 2

    if not SOURCE_FILE.exists():
        print(f"HATA: {SOURCE_FILE} bulunamadı.", file=sys.stderr)
        return 2

    current_source = SOURCE_FILE.read_text(encoding="utf-8")
    client = OpenAI(api_key=api_key)

    prompt = f"""
Improve the actual game engine in the current sari_sistem.py.

Make exactly ONE concrete gameplay improvement.

The complete replacement source must continue to support:
python sari_sistem.py --self-test
python sari_sistem.py --export-web

Do not change the website UI.
Do not return a diff.
Return the COMPLETE sari_sistem.py file inside the JSON content field.

CURRENT sari_sistem.py:

--- BEGIN SOURCE ---
{current_source}
--- END SOURCE ---

Return ONLY the requested JSON object.
"""

    models = [PRIMARY_MODEL]
    if FALLBACK_MODEL and FALLBACK_MODEL not in models:
        models.append(FALLBACK_MODEL)

    response = None
    last_error: Exception | None = None

    for model in models:
        try:
            response = request_model(client, model, prompt)
            break
        except RateLimitError as exc:
            last_error = exc
            print(f"Rate limit: {model}", file=sys.stderr)
            continue
        except Exception as exc:
            last_error = exc
            print(f"Mavi API hatası ({model}): {exc}", file=sys.stderr)
            return 1

    if response is None:
        print("HATA: Mavi hiçbir kullanılabilir modelden cevap alamadı.", file=sys.stderr)
        if last_error is not None:
            print(str(last_error), file=sys.stderr)
        return 1

    candidate = extract_json(response.output_text)

    if candidate.get("file") != "sari_sistem.py":
        raise ValueError("Mavi yanlış dosyayı hedefledi.")

    content = candidate.get("content")
    if not isinstance(content, str):
        raise ValueError("Mavi geçerli source code üretmedi.")

    content = content.strip()
    if len(content) < 300:
        raise ValueError("Mavi tarafından üretilen kod çok kısa.")

    payload = {
        "model": getattr(response, "model", PRIMARY_MODEL),
        "summary": str(candidate.get("summary", "")).strip(),
        "reason": str(candidate.get("reason", "")).strip(),
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
                "model": payload["model"],
                "summary": payload["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
