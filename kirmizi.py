from __future__ import annotations

import ast
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from openai import OpenAI

ROOT = Path(__file__).resolve().parent
SOURCE_FILE = ROOT / "sari_sistem.py"
CANDIDATE_FILE = ROOT / "mavi_aday.json"
HISTORY_FILE = ROOT / "history.json"
COUNTER_FILE = ROOT / "counter.txt"
APPROVAL_FILE = ROOT / "kirmizi_sonuc.json"
BASELINE_DATA_FILE = ROOT / "docs" / "data.json"
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

ALLOWED_IMPORTS = {"argparse", "json", "math", "dataclasses", "pathlib", "typing"}
FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "breakpoint", "input"}
ALLOWED_EFFECTS = {"damage", "heal", "shield", "energy"}
GAMEPLAY_SECTIONS = {"player", "progression", "actions", "enemies", "shop"}

AI_SYSTEM = """
You are KIRMIZI, the second-stage code reviewer for an autonomous game system.

Approve only changes that are demonstrably connected to real gameplay.
The browser consumes the JSON exported by sari_sistem.py; cosmetic-only changes
are not enough.

Rules:
- Never trust the candidate's claims. Inspect the baseline, candidate, and tests.
- Reject if the candidate relies on undefined values, nonexistent files/APIs,
  broken interfaces, hidden external state, or random behavior that cannot be
  tested.
- Reject if it weakens/deletes tests merely to make itself pass.
- Reject if it targets docs/UI/workflow files through code manipulation.
- Reject if exported gameplay config did not materially change.
- Reject if only title, description, version, or log text changed.
- Reject if a new action/effect cannot be executed by the current browser engine.
- Accept only when the deterministic evidence and the source agree.
- Be conservative: uncertainty about a core mechanic means reject.

Return ONLY JSON:
{
  "approve": true|false,
  "reason": "short Turkish explanation",
  "gameplay_change": true|false,
  "risk": "low|medium|high"
}
"""


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
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
    raise ValueError("AI response was not valid JSON")


def load_candidate() -> dict[str, Any]:
    value = json.loads(CANDIDATE_FILE.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("candidate must be an object")
    return value


def static_check(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]

    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    problems.append(f"forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                problems.append(f"forbidden import: {node.module}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
                problems.append(f"forbidden call: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "system", "popen", "run", "check_output",
            }:
                problems.append(f"forbidden process call: {node.func.attr}")

    required = ["GAME_CONFIG", "class Game", "def self_test", "def export_web"]
    for marker in required:
        if marker not in source:
            problems.append(f"missing required interface: {marker}")
    return problems


def export_candidate(source: str) -> tuple[bool, str, dict[str, Any] | None]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        candidate_path = tmp_path / "sari_sistem.py"
        candidate_path.write_text(source, encoding="utf-8")
        shutil.copy2(ROOT / "test_sari.py", tmp_path / "test_sari.py")
        shutil.copy2(BASELINE_DATA_FILE, tmp_path / "baseline_data.json")
        result = subprocess.run(
            [sys.executable, "test_sari.py"],
            cwd=tmp,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        if result.returncode != 0:
            return False, result.stdout[-12000:], None

        export = subprocess.run(
            [sys.executable, "sari_sistem.py", "--export-web"],
            cwd=tmp,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        output = (result.stdout + "\n--- EXPORT ---\n" + export.stdout)[-12000:]
        if export.returncode != 0:
            return False, output, None

        exported = json.loads((tmp_path / "docs" / "data.json").read_text(encoding="utf-8"))
        return True, output, exported


def validate_export(exported: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    game = exported.get("game")
    old_game = baseline.get("game")
    if not isinstance(game, dict):
        return ["exported game config missing"]
    if not isinstance(old_game, dict):
        return ["baseline game config missing"]

    changed_sections = {key for key in GAMEPLAY_SECTIONS if game.get(key) != old_game.get(key)}
    if not changed_sections:
        problems.append("no gameplay section changed")

    player = game.get("player", {})
    progression = game.get("progression", {})
    actions = game.get("actions", [])
    enemies = game.get("enemies", [])
    shop = game.get("shop", {})

    numeric_positive = {
        "player.max_hp": player.get("max_hp"),
        "player.max_energy": player.get("max_energy"),
        "player.base_attack": player.get("base_attack"),
        "progression.xp_to_level": progression.get("xp_to_level"),
    }
    for name, value in numeric_positive.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
            problems.append(f"invalid positive number: {name}={value!r}")

    if not actions:
        problems.append("actions cannot be empty")
    if not enemies:
        problems.append("enemies cannot be empty")

    ids: list[str] = []
    for action in actions:
        if not isinstance(action, dict):
            problems.append("action must be object")
            continue
        aid = action.get("id")
        if not isinstance(aid, str) or not aid:
            problems.append("action id missing")
        elif aid in ids:
            problems.append(f"duplicate action id: {aid}")
        else:
            ids.append(aid)
        for effect in action.get("effects", []):
            if effect.get("type") not in ALLOWED_EFFECTS:
                problems.append(f"unsupported effect type: {effect.get('type')}")
            amount = effect.get("amount", 0)
            if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not math.isfinite(float(amount)):
                problems.append(f"invalid effect amount: {amount!r}")

    for enemy in enemies:
        if not isinstance(enemy, dict) or not enemy.get("name"):
            problems.append("invalid enemy")
            continue
        for key in ["hp", "attack", "defense"]:
            value = enemy.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value < 0:
                problems.append(f"invalid enemy {key}: {value!r}")

    for key in ["potion_cost", "potion_heal"]:
        value = shop.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value < 0:
            problems.append(f"invalid shop {key}: {value!r}")

    return problems


def ask_ai_review(baseline_source: str, candidate: str, test_output: str, validation_problems: list[str], exported: dict[str, Any]) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "approve": False,
            "reason": "OPENAI_API_KEY yok; akıllı ikinci inceleme yapılamadı.",
            "gameplay_change": False,
            "risk": "high",
        }

    client = OpenAI()
    prompt = f"""
BASELINE SOURCE:
{baseline_source}

CANDIDATE SOURCE:
{candidate}

DETERMINISTIC TEST/EXPORT OUTPUT:
{test_output}

VALIDATION PROBLEMS:
{json.dumps(validation_problems, ensure_ascii=False)}

CANDIDATE EXPORTED GAME CONFIG:
{json.dumps(exported.get('game', {}), ensure_ascii=False, indent=2)}
"""
    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": AI_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return extract_json(response.output_text)


def read_counter() -> int:
    try:
        return max(0, int(COUNTER_FILE.read_text(encoding="utf-8").strip()))
    except (FileNotFoundError, ValueError):
        return 0


def write_counter(value: int) -> None:
    COUNTER_FILE.write_text(str(max(0, value)) + "\n", encoding="utf-8")


def append_history(event: dict[str, Any]) -> None:
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(history, list):
            history = []
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    history.append(event)
    HISTORY_FILE.write_text(
        json.dumps(history[-100:], ensure_ascii=False, indent=2), encoding="utf-8"
    )


def promote(candidate_source: str, summary: str, reason: str, ai_result: dict[str, Any]) -> None:
    backup = ROOT / "sari_sistem.previous.py"
    shutil.copy2(SOURCE_FILE, backup)
    SOURCE_FILE.write_text(candidate_source, encoding="utf-8")
    generation = read_counter() + 1
    write_counter(generation)
    append_history(
        {
            "generation": generation,
            "summary": summary,
            "reason": reason,
            "ai_review": ai_result,
            "status": "ACCEPTED",
        }
    )
    backup.unlink(missing_ok=True)


def main() -> int:
    if not CANDIDATE_FILE.exists():
        print("candidate missing", file=sys.stderr)
        return 2

    candidate = load_candidate()
    source = candidate.get("content", "")
    if candidate.get("file") != "sari_sistem.py" or not isinstance(source, str):
        print("candidate target invalid", file=sys.stderr)
        return 2

    baseline_source = SOURCE_FILE.read_text(encoding="utf-8")
    static_problems = static_check(source)
    tests_ok, test_output, exported = (False, "static check failed", None)
    if not static_problems:
        tests_ok, test_output, exported = export_candidate(source)

    baseline = json.loads(BASELINE_DATA_FILE.read_text(encoding="utf-8"))
    validation_problems = [] if exported is None else validate_export(exported, baseline)

    deterministic_ok = not static_problems and tests_ok and not validation_problems
    if deterministic_ok:
        ai_result = ask_ai_review(baseline_source, source, test_output, validation_problems, exported)
    else:
        ai_result = {
            "approve": False,
            "reason": "Deterministik kontrol kapılarından biri geçmedi.",
            "gameplay_change": False,
            "risk": "high",
        }

    ai_ok = bool(ai_result.get("approve")) and bool(ai_result.get("gameplay_change"))
    accepted = deterministic_ok and ai_ok and ai_result.get("risk") in {"low", "medium"}

    result = {
        "accepted": accepted,
        "generation_before": read_counter(),
        "summary": candidate.get("summary", ""),
        "mavi_reason": candidate.get("reason", ""),
        "static_problems": static_problems,
        "tests_ok": tests_ok,
        "gameplay_validation_problems": validation_problems,
        "test_output": test_output,
        "ai_review": ai_result,
    }

    if accepted:
        promote(source, str(candidate.get("summary", "")), str(candidate.get("reason", "")), ai_result)
        # Re-export only after promotion so Pages reflects exactly the promoted file.
        subprocess.run([sys.executable, "sari_sistem.py", "--export-web"], cwd=ROOT, check=True, timeout=30)
        result["generation_after"] = read_counter()
        result["status"] = "ACCEPTED_AND_PROMOTED"
    else:
        append_history({
            "generation": read_counter(),
            "summary": str(candidate.get("summary", "")),
            "reason": str(ai_result.get("reason", "")),
            "status": "REJECTED",
        })
        result["status"] = "REJECTED"

    APPROVAL_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"accepted": accepted, "status": result["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
