from __future__ import annotations

import ast
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SOURCE_FILE = ROOT / "sari_sistem.py"
CANDIDATE_FILE = ROOT / "mavi_aday.json"
HISTORY_FILE = ROOT / "history.json"
COUNTER_FILE = ROOT / "counter.txt"
APPROVAL_FILE = ROOT / "kirmizi_sonuc.json"
DOCS_DIR = ROOT / "docs"
DATA_FILE = DOCS_DIR / "data.json"

HISTORY_SCHEMA = 2
ALLOWED_IMPORTS = {
    "__future__",
    "argparse",
    "json",
    "math",
    "dataclasses",
    "pathlib",
    "typing",
}
FORBIDDEN_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "breakpoint",
    "input",
}
FORBIDDEN_PROCESS_ATTRIBUTES = {
    "system",
    "popen",
    "run",
    "check_output",
}
ALLOWED_EFFECTS = {"damage", "heal", "shield", "energy"}
GAMEPLAY_SECTIONS = {"player", "progression", "actions", "enemies", "shop"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return value


def static_check(source: str) -> list[str]:
    problems: list[str] = []

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]

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

            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in FORBIDDEN_PROCESS_ATTRIBUTES
            ):
                problems.append(f"forbidden process call: {node.func.attr}")

    required = [
        "GAME_CONFIG",
        "class Player",
        "class Battle",
        "class Game",
        "def self_test",
        "def export_web",
    ]
    for marker in required:
        if marker not in source:
            problems.append(f"missing required interface: {marker}")

    return problems


def run_python(directory: Path, args: list[str], timeout: int = 30) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, *args],
            cwd=directory,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = str(exc.stdout or "")
        return False, (output + "\nprocess timeout")[-16000:]

    output = result.stdout[-16000:]
    return result.returncode == 0, output


def export_source(source: str) -> tuple[bool, str, dict[str, Any] | None]:
    with tempfile.TemporaryDirectory(prefix="autonom-export-") as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "sari_sistem.py").write_text(source, encoding="utf-8")

        smoke_ok, smoke_output = run_python(
            tmp,
            ["sari_sistem.py", "--self-test"],
        )
        if not smoke_ok:
            return False, smoke_output, None

        export_ok, export_output = run_python(
            tmp,
            ["sari_sistem.py", "--export-web"],
        )
        combined = (
            "=== SELF TEST ===\n"
            + smoke_output
            + "\n=== EXPORT ===\n"
            + export_output
        )
        if not export_ok:
            return False, combined[-16000:], None

        data_path = tmp / "docs" / "data.json"
        if not data_path.exists():
            return False, combined + "\nmissing docs/data.json", None

        try:
            exported = json.loads(data_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, combined + f"\ninvalid data.json: {exc}", None

        if not isinstance(exported, dict):
            return False, combined + "\nexport is not an object", None

        return True, combined[-16000:], exported


def run_behavior_probe(source: str) -> tuple[bool, str, dict[str, Any] | None]:
    harness = r'''
import importlib.util
import json
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("probe_sari", Path("sari_sistem.py").resolve())
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)

cfg = module.GAME_CONFIG


def action_probe(action_id):
    game = module.Game(cfg)
    game.start_battle(seed=0)
    game.battle.enemy["attack"] = 0
    game.battle.enemy["defense"] = 0
    game.battle.enemy_hp = 100000

    action = next(a for a in cfg["actions"] if a["id"] == action_id)
    cost = int(action.get("energy", 0))
    game.player.energy = min(int(cfg["player"]["max_energy"]), max(cost, 0))

    if any(
        e.get("type") == "heal" and float(e.get("amount", 0)) > 0
        for e in action.get("effects", [])
    ):
        game.player.hp = max(1, int(cfg["player"]["max_hp"]) // 2)

    before = {
        "hp": game.player.hp,
        "energy": game.player.energy,
        "gold": game.player.gold,
        "enemy_hp": game.battle.enemy_hp,
        "shield": game.battle.shield,
        "level": game.player.level,
        "xp": game.player.xp,
    }

    result = game.act(action_id, roll=0.99)

    after = {
        "hp": game.player.hp,
        "energy": game.player.energy,
        "gold": game.player.gold,
        "enemy_hp": game.battle.enemy_hp,
        "shield": game.battle.shield,
        "level": game.player.level,
        "xp": game.player.xp,
        "ended": bool(result["battle"]["ended"]),
        "result": result["battle"]["result"],
    }
    return {"before": before, "after": after}


def win_probe():
    game = module.Game(cfg)
    game.start_battle(seed=0)
    game.battle.enemy["attack"] = 0
    game.battle.enemy["defense"] = 0
    game.battle.enemy_hp = 1

    attack = next(a for a in cfg["actions"] if a["id"] == "attack")
    game.player.energy = int(attack.get("energy", 0))

    before = {
        "xp": game.player.xp,
        "gold": game.player.gold,
        "hp": game.player.hp,
        "level": game.player.level,
    }
    result = game.act("attack", roll=0.99)

    return {
        "before": before,
        "after": {
            "xp": game.player.xp,
            "gold": game.player.gold,
            "hp": game.player.hp,
            "level": game.player.level,
            "result": result["battle"]["result"],
        },
    }


def loss_probe():
    game = module.Game(cfg)
    game.start_battle(seed=0)
    game.battle.enemy["attack"] = 99
    game.battle.enemy["defense"] = 0
    game.player.hp = 1

    before = {"xp": game.player.xp, "level": game.player.level}
    result = game.act("attack", roll=0.99)

    return {
        "before": before,
        "after": {
            "xp": game.player.xp,
            "level": game.player.level,
            "result": result["battle"]["result"],
        },
    }


def shop_probe():
    game = module.Game(cfg)
    game.start_battle(seed=0)
    game.player.hp = max(1, int(cfg["player"]["max_hp"]) // 2)

    before = {
        "hp": game.player.hp,
        "gold": game.player.gold,
        "inventory": list(game.player.inventory),
    }
    ok = game.buy_potion()

    return {
        "ok": bool(ok),
        "before": before,
        "after": {
            "hp": game.player.hp,
            "gold": game.player.gold,
            "inventory": list(game.player.inventory),
        },
    }


probe = {
    "player": {
        "max_hp": cfg["player"].get("max_hp"),
        "max_energy": cfg["player"].get("max_energy"),
        "base_attack": cfg["player"].get("base_attack"),
        "base_defense": cfg["player"].get("base_defense"),
    },
    "progression": {
        "xp_to_level": cfg["progression"].get("xp_to_level"),
        "xp_per_win": cfg["progression"].get("xp_per_win"),
        "xp_per_loss": cfg["progression"].get("xp_per_loss"),
        "gold_per_win": cfg["progression"].get("gold_per_win"),
        "heal_after_battle": cfg["progression"].get("heal_after_battle"),
    },
    "actions": {a["id"]: action_probe(a["id"]) for a in cfg["actions"]},
    "enemies": [
        {
            "id": e.get("id"),
            "hp": e.get("hp"),
            "attack": e.get("attack"),
            "defense": e.get("defense"),
            "xp": e.get("xp"),
            "gold": e.get("gold"),
        }
        for e in cfg["enemies"]
    ],
    "shop": shop_probe(),
    "win": win_probe(),
    "loss": loss_probe(),
}

print(json.dumps(probe, ensure_ascii=False, sort_keys=True))
'''

    with tempfile.TemporaryDirectory(prefix="autonom-probe-") as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "sari_sistem.py").write_text(source, encoding="utf-8")
        (tmp / "probe.py").write_text(harness, encoding="utf-8")

        ok, output = run_python(tmp, ["probe.py"], timeout=30)
        if not ok:
            return False, output, None

        try:
            probe = json.loads(output.strip().splitlines()[-1])
        except (ValueError, json.JSONDecodeError):
            return False, output, None

        return True, output[-16000:], probe


def canonical_signature(probe: dict[str, Any]) -> dict[str, Any]:
    # Logs/descriptions are intentionally omitted. Only observable game state
    # transitions count as evolution.
    return {
        "player": probe["player"],
        "progression": probe["progression"],
        "actions": probe["actions"],
        "enemies": probe["enemies"],
        "shop": probe["shop"],
        "win": probe["win"],
        "loss": probe["loss"],
    }


def validate_config(
    exported: dict[str, Any],
    baseline_exported: dict[str, Any],
) -> list[str]:
    problems: list[str] = []

    game = exported.get("game")
    baseline_game = baseline_exported.get("game")

    if not isinstance(game, dict):
        return ["exported game config missing"]
    if not isinstance(baseline_game, dict):
        return ["baseline game config missing"]

    changed_sections = {
        key
        for key in GAMEPLAY_SECTIONS
        if game.get(key) != baseline_game.get(key)
    }

    # A source-level engine change is also allowed, provided the independent
    # behavior probe proves an observable gameplay difference.
    if not changed_sections:
        # No error here yet. The final probe comparison makes the decision.
        pass

    autonomy = game.get("autonomy", {})
    supported = autonomy.get("browser_effects", list(ALLOWED_EFFECTS))
    if not isinstance(supported, list):
        problems.append("autonomy.browser_effects must be a list")
        supported = list(ALLOWED_EFFECTS)
    supported = set(supported)

    actions = game.get("actions", [])
    if not isinstance(actions, list) or not actions:
        problems.append("actions cannot be empty")
        actions = []

    ids: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            problems.append("action must be an object")
            continue

        action_id = action.get("id")
        if not isinstance(action_id, str) or not action_id.strip():
            problems.append("action id missing")
        elif action_id in ids:
            problems.append(f"duplicate action id: {action_id}")
        else:
            ids.add(action_id)

        energy = action.get("energy", 0)
        if (
            isinstance(energy, bool)
            or not isinstance(energy, (int, float))
            or not math.isfinite(float(energy))
            or float(energy) < 0
        ):
            problems.append(f"action {action_id!r} has invalid energy cost")

        effects = action.get("effects", [])
        if not isinstance(effects, list) or not effects:
            problems.append(f"action {action_id!r} has no effects")
            continue

        positive_supported = False
        for effect in effects:
            if not isinstance(effect, dict):
                problems.append(f"action {action_id!r} has invalid effect")
                continue

            effect_type = effect.get("type")
            amount = effect.get("amount", 0)

            if effect_type not in supported or effect_type not in ALLOWED_EFFECTS:
                problems.append(
                    f"action {action_id!r} uses unsupported effect {effect_type!r}"
                )

            if (
                isinstance(amount, bool)
                or not isinstance(amount, (int, float))
                or not math.isfinite(float(amount))
            ):
                problems.append(
                    f"action {action_id!r} has invalid effect amount {amount!r}"
                )
            elif float(amount) > 0 and effect_type in supported and effect_type in ALLOWED_EFFECTS:
                positive_supported = True

        if not positive_supported:
            problems.append(
                f"action {action_id!r} has no positive browser-executable effect"
            )

    for section_name in ["player", "progression"]:
        section = game.get(section_name)
        if not isinstance(section, dict):
            problems.append(f"{section_name} must be an object")

    enemies = game.get("enemies", [])
    if not isinstance(enemies, list) or not enemies:
        problems.append("enemies cannot be empty")
    else:
        enemy_ids: set[str] = set()
        for enemy in enemies:
            if not isinstance(enemy, dict):
                problems.append("enemy must be an object")
                continue

            enemy_id = enemy.get("id")
            if not isinstance(enemy_id, str) or not enemy_id:
                problems.append("enemy id missing")
            elif enemy_id in enemy_ids:
                problems.append(f"duplicate enemy id: {enemy_id}")
            else:
                enemy_ids.add(enemy_id)

            for key in ["hp", "attack", "defense"]:
                value = enemy.get(key)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or float(value) < 0
                ):
                    problems.append(
                        f"enemy {enemy_id!r} has invalid {key}: {value!r}"
                    )

    shop = game.get("shop", {})
    if not isinstance(shop, dict):
        problems.append("shop must be an object")
    else:
        for key in ["potion_cost", "potion_heal"]:
            value = shop.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0
            ):
                problems.append(f"shop has invalid {key}: {value!r}")

    return problems


def validate_new_actions(
    baseline_game: dict[str, Any],
    candidate_game: dict[str, Any],
    candidate_probe: dict[str, Any],
) -> list[str]:
    problems: list[str] = []

    old_actions = {
        a.get("id"): a
        for a in baseline_game.get("actions", [])
        if isinstance(a, dict) and isinstance(a.get("id"), str)
    }
    new_actions = {
        a.get("id"): a
        for a in candidate_game.get("actions", [])
        if isinstance(a, dict) and isinstance(a.get("id"), str)
    }

    for action_id in sorted(set(new_actions) - set(old_actions)):
        action = new_actions[action_id]
        probe = candidate_probe.get("actions", {}).get(action_id)

        if not isinstance(probe, dict):
            problems.append(f"new action {action_id!r} was not executable")
            continue

        before = probe["before"]
        after = probe["after"]
        cost = int(action.get("energy", 0))

        # Energy cost alone is never considered a feature.
        state_changed = (
            after["hp"] != before["hp"]
            or after["energy"] != max(0, before["energy"] - cost)
            or after["gold"] != before["gold"]
            or after["enemy_hp"] != before["enemy_hp"]
            or after["shield"] != before["shield"]
            or after["level"] != before["level"]
            or after["xp"] != before["xp"]
        )
        if not state_changed:
            problems.append(
                f"new action {action_id!r} exists but produced no real state change"
            )

        for effect in action.get("effects", []):
            kind = effect.get("type")
            amount = float(effect.get("amount", 0))

            if kind == "damage" and amount > 0 and not (after["enemy_hp"] < before["enemy_hp"]):
                problems.append(
                    f"new action {action_id!r} claims damage but did not damage enemy"
                )
            elif kind == "heal" and amount > 0 and not (after["hp"] > before["hp"]):
                problems.append(
                    f"new action {action_id!r} claims heal but did not heal"
                )
            elif kind == "shield" and amount > 0 and not (after["shield"] > before["shield"]):
                problems.append(
                    f"new action {action_id!r} claims shield but did not create shield"
                )
            elif kind == "energy" and amount > 0:
                baseline_after_cost = max(0, before["energy"] - cost)
                if after["energy"] <= baseline_after_cost + 1:
                    problems.append(
                        f"new action {action_id!r} claims energy gain but the gain was not observable"
                    )

    return problems


def append_history(event: dict[str, Any]) -> None:
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(history, list):
            history = []
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    history.append(event)
    HISTORY_FILE.write_text(
        json.dumps(history[-100:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_counter() -> int:
    try:
        return max(0, int(COUNTER_FILE.read_text(encoding="utf-8").strip()))
    except (FileNotFoundError, ValueError):
        return 0


def write_counter(value: int) -> None:
    COUNTER_FILE.write_text(
        str(max(0, int(value))) + "\n",
        encoding="utf-8",
    )


def restore_file(path: Path, content: str | None) -> None:
    if content is None:
        path.unlink(missing_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def promote(
    candidate_source: str,
    summary: str,
    reason: str,
    report: dict[str, Any],
) -> None:
    old_source = SOURCE_FILE.read_text(encoding="utf-8")
    old_counter = (
        COUNTER_FILE.read_text(encoding="utf-8")
        if COUNTER_FILE.exists()
        else None
    )
    old_history = (
        HISTORY_FILE.read_text(encoding="utf-8")
        if HISTORY_FILE.exists()
        else None
    )
    old_data = (
        DATA_FILE.read_text(encoding="utf-8")
        if DATA_FILE.exists()
        else None
    )

    backup = ROOT / "sari_sistem.previous.py"
    shutil.copy2(SOURCE_FILE, backup)

    generation_before = read_counter()
    generation_after = generation_before + 1

    try:
        SOURCE_FILE.write_text(candidate_source, encoding="utf-8")
        write_counter(generation_after)

        append_history(
            {
                "schema": HISTORY_SCHEMA,
                "generation": generation_after,
                "previous_generation": generation_before,
                "status": "ACCEPTED",
                "summary": summary,
                "reason": reason,
                "verification": report,
            }
        )

        export_ok, export_output = run_python(
            ROOT,
            ["sari_sistem.py", "--export-web"],
            timeout=30,
        )
        if not export_ok:
            raise RuntimeError(
                "Promoted source could not be exported:\n" + export_output
            )

    except Exception:
        SOURCE_FILE.write_text(old_source, encoding="utf-8")
        restore_file(COUNTER_FILE, old_counter)
        restore_file(HISTORY_FILE, old_history)
        restore_file(DATA_FILE, old_data)
        raise
    finally:
        backup.unlink(missing_ok=True)


def main() -> int:
    if not CANDIDATE_FILE.exists():
        print("candidate missing", file=sys.stderr)
        return 2

    if not SOURCE_FILE.exists():
        print("baseline sari_sistem.py missing", file=sys.stderr)
        return 2

    try:
        candidate = load_json(CANDIDATE_FILE)
    except Exception as exc:
        print(f"candidate JSON invalid: {exc}", file=sys.stderr)
        return 2

    source = candidate.get("content", "")
    if candidate.get("file") != "sari_sistem.py" or not isinstance(source, str):
        print("candidate target invalid", file=sys.stderr)
        return 2

    baseline_source = SOURCE_FILE.read_text(encoding="utf-8")

    static_problems = static_check(source)
    if source.strip() == baseline_source.strip():
        static_problems.append("candidate source is identical to current source")

    baseline_ok, baseline_output, baseline_export = export_source(baseline_source)
    candidate_ok, candidate_output, candidate_export = export_source(source)

    baseline_probe: dict[str, Any] | None = None
    candidate_probe: dict[str, Any] | None = None
    execution_problems: list[str] = []

    if baseline_ok:
        ok, output, probe = run_behavior_probe(baseline_source)
        baseline_output += "\n=== BASELINE BEHAVIOR ===\n" + output
        if not ok:
            execution_problems.append("baseline behavioral probe failed")
        else:
            baseline_probe = probe
    else:
        execution_problems.append("current baseline could not pass smoke/export")

    if candidate_ok:
        ok, output, probe = run_behavior_probe(source)
        candidate_output += "\n=== CANDIDATE BEHAVIOR ===\n" + output
        if not ok:
            execution_problems.append("candidate behavioral probe failed")
        else:
            candidate_probe = probe
    else:
        execution_problems.append("candidate could not pass independent smoke/export")

    validation_problems: list[str] = []
    if baseline_export is not None and candidate_export is not None:
        validation_problems.extend(
            validate_config(candidate_export, baseline_export)
        )

        if candidate_probe is not None:
            validation_problems.extend(
                validate_new_actions(
                    baseline_export["game"],
                    candidate_export["game"],
                    candidate_probe,
                )
            )

    if baseline_probe is not None and candidate_probe is not None:
        if canonical_signature(baseline_probe) == canonical_signature(candidate_probe):
            validation_problems.append(
                "candidate produced no observable difference in independent gameplay probes"
            )

    deterministic_ok = (
        not static_problems
        and not execution_problems
        and not validation_problems
        and baseline_export is not None
        and candidate_export is not None
        and baseline_probe is not None
        and candidate_probe is not None
    )

    report = {
        "schema": HISTORY_SCHEMA,
        "accepted": deterministic_ok,
        "generation_before": read_counter(),
        "summary": str(candidate.get("summary", "")).strip(),
        "mavi_reason": str(candidate.get("reason", "")).strip(),
        "claimed_change": candidate.get("claimed_change", {}),
        "static_problems": static_problems,
        "execution_problems": execution_problems,
        "gameplay_validation_problems": validation_problems,
        "baseline_behavior": baseline_probe,
        "candidate_behavior": candidate_probe,
        "baseline_output": baseline_output[-10000:],
        "candidate_output": candidate_output[-10000:],
    }

    if deterministic_ok:
        try:
            promote(
                source,
                str(candidate.get("summary", "")).strip(),
                str(candidate.get("reason", "")).strip(),
                report,
            )
            report["generation_after"] = read_counter()
            report["status"] = "ACCEPTED_AND_PROMOTED"
        except Exception as exc:
            report["accepted"] = False
            report["status"] = "REJECTED_PROMOTION_FAILED"
            report["execution_problems"].append(str(exc))
    else:
        append_history(
            {
                "schema": HISTORY_SCHEMA,
                "generation": read_counter(),
                "status": "REJECTED",
                "summary": str(candidate.get("summary", "")).strip(),
                "reason": (
                    "; ".join(
                        static_problems
                        + execution_problems
                        + validation_problems
                    )
                    or "Deterministik doğrulama geçmedi."
                )[:4000],
                "verification": report,
            }
        )
        report["status"] = "REJECTED"

    APPROVAL_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "accepted": report["accepted"],
                "status": report["status"],
                "generation": read_counter(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
