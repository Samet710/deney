from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

DOCS = ROOT / "docs"

DATA_FILE = DOCS / "data.json"

COUNTER_FILE = ROOT / "counter.txt"

HISTORY_FILE = ROOT / "history.json"


TITLE = "YELLOW // MICRO DUNGEON"


GAME_CONFIG: dict[str, Any] = {
    "title": TITLE,

    "subtitle": (
        "Autonomous turn-based dungeon game."
    ),

    "rules_version": 1,

    "player": {
        "max_hp": 100,
        "max_energy": 6,
        "starting_gold": 12,

        "base_attack": 12,
        "base_defense": 2,

        "crit_chance": 0.10,
        "crit_multiplier": 1.75,
    },

    "progression": {
        "xp_per_win": 35,
        "xp_per_loss": 8,

        "xp_to_level": 100,

        "gold_per_win": 9,

        "heal_after_battle": 18,
    },

    "actions": [
        {
            "id": "attack",

            "name": "Saldır",

            "description": (
                "Temel saldırı yap. "
                "Kritik vuruş ihtimali vardır."
            ),

            "energy": 2,

            "effects": [
                {
                    "type": "damage",
                    "amount": 1.0,
                    "stat": "attack",
                }
            ],
        },

        {
            "id": "guard",

            "name": "Savun",

            "description": (
                "Kalkan oluştur ve enerji kazan."
            ),

            "energy": 0,

            "effects": [
                {
                    "type": "shield",
                    "amount": 6,
                },
                {
                    "type": "energy",
                    "amount": 1,
                },
            ],
        },

        {
            "id": "heal",

            "name": "İyileş",

            "description": (
                "Enerji harcayarak can yenile."
            ),

            "energy": 3,

            "effects": [
                {
                    "type": "heal",
                    "amount": 20,
                }
            ],
        },
    ],

    "enemies": [
        {
            "id": "slime",
            "name": "Neon Slime",

            "hp": 54,
            "attack": 8,
            "defense": 1,

            "gold": 6,
            "xp": 24,
        },

        {
            "id": "drone",
            "name": "Rust Drone",

            "hp": 72,
            "attack": 11,
            "defense": 2,

            "gold": 9,
            "xp": 32,
        },

        {
            "id": "warden",
            "name": "Archive Warden",

            "hp": 92,
            "attack": 14,
            "defense": 3,

            "gold": 13,
            "xp": 44,
        },
    ],

    "shop": {
        "potion_cost": 8,
        "potion_heal": 24,
    },
}


@dataclass
class Player:
    hp: int
    energy: int
    gold: int

    xp: int = 0
    level: int = 1

    inventory: list[str] = field(
        default_factory=list
    )


@dataclass
class Battle:
    enemy: dict[str, Any]

    enemy_hp: int

    shield: int = 0

    turn: int = 1

    log: list[str] = field(
        default_factory=list
    )

    ended: bool = False

    result: str | None = None


class Game:

    def __init__(
        self,
        config: dict[str, Any] | None = None,
    ):
        self.config = (
            config
            if config is not None
            else GAME_CONFIG
        )

        player_config = self.config["player"]

        self.player = Player(
            hp=int(
                player_config["max_hp"]
            ),

            energy=int(
                player_config["max_energy"]
            ),

            gold=int(
                player_config["starting_gold"]
            ),
        )

        self.battle: Battle | None = None


    def _enemy_for_seed(
        self,
        seed: int = 0,
    ) -> dict[str, Any]:

        enemies = self.config["enemies"]

        if not enemies:
            raise ValueError(
                "No enemies configured."
            )

        return dict(
            enemies[
                seed % len(enemies)
            ]
        )


    def start_battle(
        self,
        seed: int = 0,
    ) -> dict[str, Any]:

        enemy = self._enemy_for_seed(
            seed
        )

        self.battle = Battle(
            enemy=enemy,

            enemy_hp=int(
                enemy["hp"]
            ),

            log=[
                f"{enemy['name']} ortaya çıktı."
            ],
        )

        return self.snapshot()


    def _find_action(
        self,
        action_id: str,
    ) -> dict[str, Any]:

        for action in self.config["actions"]:

            if action["id"] == action_id:
                return action

        raise ValueError(
            f"unknown action: {action_id}"
        )


    def _gain_xp(
        self,
        amount: int,
    ) -> None:

        progression = (
            self.config["progression"]
        )

        self.player.xp += max(
            0,
            int(amount),
        )

        threshold = max(
            1,
            int(
                progression[
                    "xp_to_level"
                ]
            ),
        )

        while (
            self.player.xp >= threshold
        ):

            self.player.xp -= threshold

            self.player.level += 1


    def _enemy_turn(self) -> None:

        if self.battle is None:
            raise RuntimeError(
                "battle not started"
            )

        player_config = (
            self.config["player"]
        )

        raw_damage = max(
            0,
            int(
                self.battle.enemy[
                    "attack"
                ]
            )
            - int(
                player_config[
                    "base_defense"
                ]
            ),
        )

        blocked = min(
            raw_damage,
            self.battle.shield,
        )

        damage = (
            raw_damage - blocked
        )

        self.battle.shield -= blocked

        self.player.hp = max(
            0,
            self.player.hp - damage,
        )

        if blocked:

            self.battle.log.append(
                (
                    f"{self.battle.enemy['name']} "
                    f"vurdu: {damage} hasar, "
                    f"{blocked} engellendi."
                )
            )

        else:

            self.battle.log.append(
                (
                    f"{self.battle.enemy['name']} "
                    f"vurdu: {damage} hasar."
                )
            )

        self.player.energy = min(
            int(
                player_config[
                    "max_energy"
                ]
            ),

            self.player.energy + 1,
        )

        if self.player.hp <= 0:

            self.battle.ended = True

            self.battle.result = "loss"

            self._gain_xp(
                int(
                    self.config[
                        "progression"
                    ]["xp_per_loss"]
                )
            )


    def act(
        self,
        action_id: str,
        roll: float = 0.5,
    ) -> dict[str, Any]:

        if self.battle is None:

            raise RuntimeError(
                "battle not started"
            )

        if self.battle.ended:

            return self.snapshot()

        action = self._find_action(
            action_id
        )

        energy_cost = int(
            action.get(
                "energy",
                0,
            )
        )

        if (
            self.player.energy
            < energy_cost
        ):

            self.battle.log.append(
                "Yeterli enerji yok."
            )

            return self.snapshot()

        self.player.energy -= (
            energy_cost
        )

        self._apply_effects(
            action.get(
                "effects",
                [],
            ),
            roll,
        )

        if self.battle.enemy_hp <= 0:

            self._win_battle()

            return self.snapshot()

        self._enemy_turn()

        self.battle.turn += 1

        return self.snapshot()


    def _apply_effects(
        self,
        effects: list[
            dict[str, Any]
        ],
        roll: float,
    ) -> None:

        if self.battle is None:
            raise RuntimeError(
                "battle not started"
            )

        player_config = (
            self.config["player"]
        )

        for effect in effects:

            effect_type = effect.get(
                "type"
            )

            amount = effect.get(
                "amount",
                0,
            )

            if effect_type == "damage":

                multiplier = float(
                    amount
                )

                raw_damage = (
                    float(
                        player_config[
                            "base_attack"
                        ]
                    )
                    * multiplier
                )

                crit_chance = float(
                    player_config.get(
                        "crit_chance",
                        0.0,
                    )
                )

                crit_multiplier = float(
                    player_config.get(
                        "crit_multiplier",
                        1.0,
                    )
                )

                critical = (
                    float(roll)
                    < crit_chance
                )

                if critical:

                    raw_damage *= (
                        crit_multiplier
                    )

                damage = max(
                    1,

                    int(
                        math.floor(
                            raw_damage
                        )
                    )
                    - int(
                        self.battle.enemy.get(
                            "defense",
                            0,
                        )
                    ),
                )

                self.battle.enemy_hp = max(
                    0,

                    self.battle.enemy_hp
                    - damage,
                )

                suffix = (
                    " KRİTİK!"
                    if critical
                    else ""
                )

                self.battle.log.append(
                    (
                        f"Saldırı: "
                        f"{damage} hasar."
                        f"{suffix}"
                    )
                )

            elif effect_type == "heal":

                heal_amount = max(
                    0,
                    int(amount),
                )

                before = self.player.hp

                self.player.hp = min(
                    int(
                        player_config[
                            "max_hp"
                        ]
                    ),

                    self.player.hp
                    + heal_amount,
                )

                actual = (
                    self.player.hp
                    - before
                )

                self.battle.log.append(
                    f"+{actual} can."
                )

            elif effect_type == "shield":

                shield_amount = max(
                    0,
                    int(amount),
                )

                self.battle.shield += (
                    shield_amount
                )

                self.battle.log.append(
                    (
                        f"Kalkan "
                        f"+{shield_amount}."
                    )
                )

            elif effect_type == "energy":

                max_energy = int(
                    player_config[
                        "max_energy"
                    ]
                )

                old_energy = (
                    self.player.energy
                )

                self.player.energy = min(
                    max_energy,

                    max(
                        0,

                        self.player.energy
                        + int(amount),
                    ),
                )

                actual = (
                    self.player.energy
                    - old_energy
                )

                self.battle.log.append(
                    (
                        f"Enerji "
                        f"{actual:+d}."
                    )
                )

            else:

                raise ValueError(
                    (
                        "unsupported effect "
                        f"type: {effect_type}"
                    )
                )


    def _win_battle(
        self,
    ) -> None:

        if self.battle is None:
            raise RuntimeError(
                "battle not started"
            )

        progression = (
            self.config["progression"]
        )

        enemy = self.battle.enemy

        xp = int(
            enemy.get(
                "xp",
                progression[
                    "xp_per_win"
                ],
            )
        )

        gold = int(
            enemy.get(
                "gold",
                progression[
                    "gold_per_win"
                ],
            )
        )

        self._gain_xp(xp)

        self.player.gold += gold

        self.player.hp = min(
            int(
                self.config[
                    "player"
                ]["max_hp"]
            ),

            self.player.hp
            + int(
                progression[
                    "heal_after_battle"
                ]
            ),
        )

        self.battle.ended = True

        self.battle.result = "win"

        self.battle.log.append(
            (
                f"Kazandın: "
                f"+{xp} XP, "
                f"+{gold} altın."
            )
        )


    def buy_potion(self) -> bool:

        shop = self.config["shop"]

        cost = int(
            shop["potion_cost"]
        )

        heal = int(
            shop["potion_heal"]
        )

        max_hp = int(
            self.config["player"][
                "max_hp"
            ]
        )

        if self.player.gold < cost:

            return False

        if self.player.hp >= max_hp:

            return False

        self.player.gold -= cost

        before = self.player.hp

        self.player.hp = min(
            max_hp,

            self.player.hp + heal,
        )

        actual = (
            self.player.hp
            - before
        )

        if actual <= 0:

            return False

        self.player.inventory.append(
            "potion"
        )

        return True


    def snapshot(
        self,
    ) -> dict[str, Any]:

        battle_data = None

        if self.battle is not None:

            battle_data = {
                "enemy": (
                    self.battle.enemy
                ),

                "enemy_hp": (
                    self.battle.enemy_hp
                ),

                "shield": (
                    self.battle.shield
                ),

                "turn": (
                    self.battle.turn
                ),

                "log": (
                    self.battle.log[-8:]
                ),

                "ended": (
                    self.battle.ended
                ),

                "result": (
                    self.battle.result
                ),
            }

        return {
            "player": asdict(
                self.player
            ),

            "battle": battle_data,
        }


def read_generation() -> int:

    try:

        return max(
            0,

            int(
                COUNTER_FILE.read_text(
                    encoding="utf-8"
                ).strip()
            ),
        )

    except (
        FileNotFoundError,
        ValueError,
    ):

        return 0


def load_history() -> list[
    dict[str, Any]
]:

    try:

        value = json.loads(
            HISTORY_FILE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            value,
            list,
        ):

            return value

    except (
        FileNotFoundError,
        json.JSONDecodeError,
    ):

        pass

    return []


def append_history(
    event: dict[str, Any],
) -> None:

    history = load_history()

    history.append(event)

    HISTORY_FILE.write_text(
        json.dumps(
            history[-100:],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def self_test() -> dict[str, Any]:

    game = Game(
        GAME_CONFIG
    )

    game.start_battle(
        seed=0
    )

    before_hp = (
        game.battle.enemy_hp
    )

    game.act(
        "attack",
        roll=0.99,
    )

    after_hp = (
        game.battle.enemy_hp
    )

    assert (
        after_hp < before_hp
    )

    game2 = Game(
        GAME_CONFIG
    )

    game2.start_battle(
        seed=0
    )

    game2.player.hp = 50

    hp_before = (
        game2.player.hp
    )

    game2.act(
        "heal",
        roll=0.99,
    )

    assert (
        game2.player.hp > hp_before
    )

    game3 = Game(
        GAME_CONFIG
    )

    game3.start_battle(
        seed=0
    )

    game3.act(
        "guard",
        roll=0.99,
    )

    assert (
        game3.battle.shield > 0
    )

    return {
        "ok": True,

        "checks": [
            "battle starts",
            "attack changes enemy hp",
            "heal changes player hp",
            "guard creates real shield",
        ],
    }


def public_config() -> dict[
    str,
    Any,
]:

    return json.loads(
        json.dumps(
            GAME_CONFIG
        )
    )


def export_web() -> None:

    DOCS.mkdir(
        parents=True,
        exist_ok=True,
    )

    smoke = self_test()

    history = load_history()

    payload = {
        "system": {
            "title": TITLE,

            "generation": (
                read_generation()
            ),

            "status": "LIVE",

            "rules_version": (
                GAME_CONFIG.get(
                    "rules_version",
                    1,
                )
            ),

            "last_event": (
                history[-1]
                if history
                else None
            ),

            "history_tail": (
                history[-12:]
            ),
        },

        "game": public_config(),

        "smoke_test": smoke,
    }

    DATA_FILE.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--export-web",
        action="store_true",
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()

    if args.self_test:

        print(
            json.dumps(
                self_test(),
                ensure_ascii=False,
            )
        )

        return

    if args.export_web:

        export_web()

        print(
            f"web export: {DATA_FILE}"
        )

        return

    parser.error(
        "use --export-web or --self-test"
    )


if __name__ == "__main__":

    main()
