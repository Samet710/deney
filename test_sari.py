from sari_sistem import GAME_CONFIG, Game, self_test


def test_self_test():
    result = self_test()

    assert result["ok"] is True


def test_game_can_start():
    game = Game(GAME_CONFIG)

    snapshot = game.start_battle(seed=0)

    assert snapshot["battle"] is not None
    assert snapshot["battle"]["enemy_hp"] > 0


def test_attack_really_changes_enemy_hp():
    game = Game(GAME_CONFIG)

    game.start_battle(seed=0)

    before = game.battle.enemy_hp

    game.act("attack", roll=0.99)

    after = game.battle.enemy_hp

    assert after < before


def test_guard_really_creates_shield():
    game = Game(GAME_CONFIG)

    game.start_battle(seed=0)

    before = game.battle.shield

    game.act("guard", roll=0.99)

    after = game.battle.shield

    assert after > before


def test_heal_really_changes_player_hp():
    game = Game(GAME_CONFIG)

    game.start_battle(seed=0)

    game.player.hp = 50

    before = game.player.hp

    game.act("heal", roll=0.99)

    after = game.player.hp

    assert after > before

    assert after <= GAME_CONFIG["player"]["max_hp"]


def test_attack_can_finish_battle():
    config = {
        **GAME_CONFIG,
        "player": {
            **GAME_CONFIG["player"],
            "base_attack": 100,
        },
    }

    game = Game(config)

    game.start_battle(seed=0)

    game.act("attack", roll=0.99)

    assert game.battle.ended is True

    assert game.battle.result == "win"


def test_win_rewards_are_real():
    config = {
        **GAME_CONFIG,
        "player": {
            **GAME_CONFIG["player"],
            "base_attack": 100,
        },
    }

    game = Game(config)

    game.start_battle(seed=0)

    starting_gold = game.player.gold
    starting_level = game.player.level
    starting_xp = game.player.xp

    game.act("attack", roll=0.99)

    assert game.battle.result == "win"

    assert game.player.gold > starting_gold

    assert (
        game.player.xp != starting_xp
        or game.player.level > starting_level
    )


def test_level_progression_is_real():
    config = {
        **GAME_CONFIG,
        "progression": {
            **GAME_CONFIG["progression"],
            "xp_to_level": 1,
        },
        "player": {
            **GAME_CONFIG["player"],
            "base_attack": 100,
        },
    }

    game = Game(config)

    game.start_battle(seed=0)

    game.act("attack", roll=0.99)

    assert game.player.level > 1


def test_potion_costs_real_gold():
    game = Game(GAME_CONFIG)

    game.start_battle(seed=0)

    game.player.hp = 50

    before_gold = game.player.gold
    before_hp = game.player.hp

    result = game.buy_potion()

    after_gold = game.player.gold
    after_hp = game.player.hp

    assert result is True

    assert after_gold < before_gold

    assert after_hp > before_hp


def test_full_hp_potion_is_rejected():
    game = Game(GAME_CONFIG)

    game.start_battle(seed=0)

    before_gold = game.player.gold

    result = game.buy_potion()

    assert result is False

    assert game.player.gold == before_gold


def test_invalid_action_is_rejected():
    game = Game(GAME_CONFIG)

    game.start_battle(seed=0)

    try:
        game.act("this_action_does_not_exist", roll=0.99)

    except ValueError:
        return

    assert False, "Invalid action should raise ValueError"


def test_export_web_works(tmp_path, monkeypatch):
    # Sadece sari_sistem'in normal export mekanizmasının
    # bozulmadığını kontrol eder.
    import sari_sistem

    data_file = tmp_path / "data.json"

    monkeypatch.setattr(
        sari_sistem,
        "DATA_FILE",
        data_file,
    )

    monkeypatch.setattr(
        sari_sistem,
        "DOCS",
        tmp_path,
    )

    sari_sistem.export_web()

    assert data_file.exists()

    payload = __import__("json").loads(
        data_file.read_text(
            encoding="utf-8"
        )
    )

    assert "system" in payload

    assert "game" in payload

    assert "smoke_test" in payload

    assert payload["game"]["actions"]

    assert payload["game"]["enemies"]


def test_gameplay_sections_exist():
    required = {
        "player",
        "progression",
        "actions",
        "enemies",
        "shop",
    }

    assert required.issubset(
        set(GAME_CONFIG.keys())
    )


def test_actions_have_executable_effects():
    allowed = {
        "damage",
        "heal",
        "shield",
        "energy",
    }

    for action in GAME_CONFIG["actions"]:
        assert isinstance(
            action["id"],
            str,
        )

        assert action["id"]

        assert isinstance(
            action.get("effects"),
            list,
        )

        for effect in action["effects"]:
            assert effect["type"] in allowed


def test_enemies_have_required_stats():
    for enemy in GAME_CONFIG["enemies"]:
        assert enemy["hp"] > 0

        assert enemy["attack"] >= 0

        assert enemy["defense"] >= 0
