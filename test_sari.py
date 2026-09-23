from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import sari_sistem as sari

ALLOWED_EFFECTS = {"damage", "heal", "shield", "energy"}


def test_core_gameplay() -> None:
    game = sari.Game(sari.GAME_CONFIG)
    game.start_battle(seed=0)
    before_enemy = game.battle.enemy_hp
    game.act("attack", roll=0.99)
    assert game.battle.enemy_hp < before_enemy


def test_heal_is_real() -> None:
    game = sari.Game(sari.GAME_CONFIG)
    game.start_battle(seed=0)
    game.player.hp = 40
    before_hp = game.player.hp
    game.act("heal", roll=0.99)
    assert game.player.hp > before_hp
    assert game.player.hp <= sari.GAME_CONFIG["player"]["max_hp"]


def test_guard_is_real() -> None:
    normal = sari.Game(sari.GAME_CONFIG)
    normal.start_battle(seed=1)
    normal.battle.enemy["attack"] = 11
    before = normal.player.hp
    normal.act("attack", roll=0.99)
    normal_damage = before - normal.player.hp

    guarded = sari.Game(sari.GAME_CONFIG)
    guarded.start_battle(seed=1)
    guarded.battle.enemy["attack"] = 11
    before = guarded.player.hp
    guarded.act("guard", roll=0.99)
    guarded_damage = before - guarded.player.hp

    assert guarded.battle.shield > 0
    assert guarded_damage < normal_damage


def test_win_is_real() -> None:
    game = sari.Game(sari.GAME_CONFIG)
    game.start_battle(seed=0)
    game.battle.enemy["attack"] = 0
    game.battle.enemy["defense"] = 0
    game.battle.enemy_hp = 1
    game.player.energy = 6

    before_xp = game.player.xp
    before_gold = game.player.gold
    result = game.act("attack", roll=0.99)

    assert result["battle"]["result"] == "win"
    assert game.player.xp > before_xp
    assert game.player.gold > before_gold


def test_loss_is_real() -> None:
    game = sari.Game(sari.GAME_CONFIG)
    game.start_battle(seed=0)
    game.battle.enemy["attack"] = 99
    game.player.hp = 1

    result = game.act("attack", roll=0.99)
    assert result["battle"]["result"] == "loss"


def test_potion_is_real() -> None:
    game = sari.Game(sari.GAME_CONFIG)
    game.start_battle(seed=0)
    game.player.hp = 50

    before_gold = game.player.gold
    before_hp = game.player.hp

    assert game.buy_potion() is True
    assert game.player.gold < before_gold
    assert game.player.hp > before_hp


def test_all_actions_are_browser_executable() -> None:
    seen = set()

    for action in sari.GAME_CONFIG["actions"]:
        assert isinstance(action, dict)

        action_id = action.get("id")
        assert isinstance(action_id, str) and action_id
        assert action_id not in seen
        seen.add(action_id)

        effects = action.get("effects", [])
        assert isinstance(effects, list) and effects

        assert any(
            isinstance(effect, dict)
            and effect.get("type") in ALLOWED_EFFECTS
            and isinstance(effect.get("amount"), (int, float))
            and not isinstance(effect.get("amount"), bool)
            and effect.get("amount") > 0
            for effect in effects
        )


def test_export_matches_source() -> None:
    subprocess.run(
        [sys.executable, "sari_sistem.py", "--export-web"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    data = json.loads(
        (Path(__file__).resolve().parent / "docs" / "data.json").read_text(
            encoding="utf-8"
        )
    )

    assert data["game"] == sari.public_config()
    assert data["smoke_test"]["ok"] is True


def run_all() -> list[str]:
    tests = [
        test_core_gameplay,
        test_heal_is_real,
        test_guard_is_real,
        test_win_is_real,
        test_loss_is_real,
        test_potion_is_real,
        test_all_actions_are_browser_executable,
        test_export_matches_source,
    ]

    for test in tests:
        test()

    return [test.__name__ for test in tests]


if __name__ == "__main__":
    print(json.dumps({"ok": True, "tests": run_all()}, ensure_ascii=False))
